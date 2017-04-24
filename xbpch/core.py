"""
Plumbing for enabling BPCH file I/O through xarray.
"""
from __future__ import print_function, division

import os
import numpy as np
import xarray as xr
import warnings

from dask import delayed
import dask.array as da

from xarray.core.pycompat import OrderedDict
from xarray.backends.common import AbstractDataStore
from xarray.core.utils import Frozen, NDArrayMixin
from xarray.core import indexing

from . uff import FortranFile
from . grid import BASE_DIMENSIONS, CTMGrid
from . util import cf
from . util.diaginfo import get_diaginfo, get_tracerinfo

DEFAULT_DTYPE = 'f4'


def open_bpchdataset(filename, fields=[], categories=[],
                     tracerinfo_file='tracerinfo.dat',
                     diaginfo_file='diaginfo.dat',
                     endian=">",
                     memmap=True, dask=True, return_store=False):
    """ Open a GEOS-Chem BPCH file output as an xarray Dataset.

    Parameters
    ----------
    filename : string
        Path to the output file to read in.
    {tracerinfo,diaginfo}_file : string, optional
        Path to the metadata "info" .dat files which are used to decipher
        the metadata corresponding to each variable in the output dataset.
        If not provided, will look for them in the current directory or
        fall back on a generic set.
    fields : list, optional
        List of a subset of variable names to return. This can substantially
        improve read performance. Note that the field here is just the tracer
        name - not the category, e.g. 'O3' instead of 'IJ-AVG-$_O3'.
    categories : list, optional
        List a subset of variable categories to look through. This can
        substantially improve read performance.
    endian : {'=', '>', '<'}, optional
        Endianness of file on disk. By default, "big endian" (">") is assumed.
    default_dtype : numpy.dtype, optional
        Default datatype for variables encoded in file on disk (single-precision
        float by default).
    memmap : bool
        Flag indicating that data should be memory-mapped from disk instead of
        eagerly loaded into memory
    dask : bool
        Flag indicating that data reading should be deferred (delayed) to
        construct a task-graph for later execution
    return_store : bool
        Also return the underlying DataStore to the user

    Returns
    -------
    ds : xarray.Dataset
        Dataset containing the requested fields (or the entire file), with data
        contained in proxy containers for access later.
    store : xarray.AbstractDataStore
        Underlying DataStore which handles the loading and processing of
        bpch files on disk

    """

    store = BPCHDataStore(
        filename, fields=fields, categories=categories,
        tracerinfo_file=tracerinfo_file,
        diaginfo_file=diaginfo_file, endian=endian,
        use_mmap=memmap, dask_delayed=dask
    )

    ds = xr.Dataset.load_store(store)

    # Set attributes for CF conventions
    ds.attrs.update(dict(
        Conventions='CF1.6',
        source=filename,
        tracerinfo=tracerinfo_file,
        diaginfo=diaginfo_file,
        # TODO: Add a history line indicated when the file was opened
        filetype=store._bpch.filetype,
        filetitle=store._bpch.filetitle,
    ))

    # To immediately load the data from the BPCHDataProxy paylods, need
    # to execute ds.data_vars for some reason...
    if return_store:
        return ds, store
    else:
        return ds


class BPCHDataStore(AbstractDataStore):
    """ Store for reading data from binary punch files.

    Note that this is intended as a backend only; to open and read a given
    bpch file, use :meth:`open_bpchdataset`.

    """

    def __init__(self, filename, fields=[], categories=[], fix_cf=False,
                 mode='r', endian='>',
                 diaginfo_file='', tracerinfo_file='',
                 use_mmap=False, dask_delayed=False):

        # Track the metadata accompanying this dataset.
        dir_path = os.path.abspath(os.path.dirname(filename))
        if not dir_path:
            dir_path = os.getcwd()
        if not tracerinfo_file:
            tracerinfo_file = os.path.join(dir_path, 'tracerinfo.dat')
            if not os.path.exists(tracerinfo_file):
                tracerinfo_file = ''
        self.tracerinfo_file = tracerinfo_file
        if not diaginfo_file:
            diaginfo_file = os.path.join(dir_path, 'diaginfo.dat')
            if not os.path.exists(diaginfo_file):
                diaginfo_file = ''
        self.diaginfo_file = diaginfo_file

        self.filename = filename
        self.fsize = os.path.getsize(self.filename)
        self.mode = mode
        if not mode.startswith('r'):
            raise ValueError("Currently only know how to 'r(b)'ead bpch files.")

        # Check endianness flag
        if endian not in ['>', '<', '=']:
            raise ValueError("Invalid byte order (endian={})".format(endian))
        self.endian = endian

        # Open the raw output file, but don't yet read all the data
        self._mmap = use_mmap
        self._dask = dask_delayed
        self._bpch = BPCHFile(self.filename, self.mode, self.endian,
                              tracerinfo_file=tracerinfo_file,
                              diaginfo_file=diaginfo_file,
                              eager=False, use_mmap=self._mmap,
                              dask_delayed=self._dask)
        self.fields = fields
        self.categories = categories

        # Peek into the raw output file and read the header and metadata
        # so that we can get a head start at building the output grid
        self._bpch._read_metadata()
        self._bpch._read_header()

        # Create storage dicts for variables and attributes, to be used later
        # when xarray needs to access the data
        self._variables = OrderedDict()
        self._attributes = OrderedDict()
        self._attributes.update(self._bpch._attributes)
        self._dimensions = [d for d in BASE_DIMENSIONS]

        # Begin constructing the coordinate dimensions shared by the
        # output dataset variables
        dim_coords = {}
        self.ctm_info = CTMGrid.from_model(
            self._attributes['modelname'], resolution=self._attributes['res']
        )

        # Add vertical dimensions
        self._dimensions.append(
            dict(dims=['lev', ], attrs={'axis': 'Z'})
        )
        self._dimensions.append(
            dict(dims=['lev_trop', ], attrs={'axis': 'Z'})
        )
        self._dimensions.append(
            dict(dims=['lev_edge', ], attrs={'axis': 'Z'})
        )
        eta_centers = self.ctm_info.eta_centers
        sigma_centers = self.ctm_info.sigma_centers

        # Add time dimensions
        self._dimensions.append(
            dict(dims=['time', ], attrs={'axis': 'T', 'long_name': 'time',
                                         'standard_name': 'time'})
        )

        # Add lat/lon dimensions
        self._dimensions.append(
            dict(dims=['lon', ], attrs={'axis': 'X', 'long_name': 'longitude'})
        )
        self._dimensions.append(
            dict(dims=['lat', ], attrs={'axis': 'y', 'long_name': 'latitude'})
        )

        if eta_centers is not None:
            lev_vals = eta_centers
            lev_attrs = {
                'standard_name': 'atmosphere_hybrid_sigma_pressure_coordinate',
                'axis': 'Z'
            }
        else:
            lev_vals = sigma_centers
            lev_attrs = {
                'standard_name': 'atmosphere_hybrid_sigma_pressure_coordinate',
                'axis': 'Z'
            }
        self._variables['lev'] = xr.Variable(['lev', ], lev_vals, lev_attrs)

        ## Latitude / Longitude
        # TODO: Add lon/lat bounds
        self._variables['lon'] = xr.Variable(
            ['lon'], self.ctm_info.lon_centers,
            {'long_name': 'longitude', 'units': 'degrees_east'}
        )
        self._variables['lat'] = xr.Variable(
            ['lat'], self.ctm_info.lat_centers,
            {'long_name': 'latitude', 'units': 'degrees_north'}
        )
        # TODO: Fix longitudes if ctm_grid.center180


        # Parse the binary file and prepare to add variables to the DataStore
        self._bpch._read_var_data()
        for vname in list(self._bpch.var_data.keys()):

            var_data = self._bpch.var_data[vname]
            var_attr = self._bpch.var_attrs[vname]

            if fields and (var_attr['name'] not in fields):
                continue
            if categories and (var_attr['category'] not in categories):
                continue

            # Process dimensions
            dims = ['time', 'lon', 'lat', ]
            dshape = var_attr['original_shape']
            if len(dshape) == 3:
                # Process the vertical coordinate. A few things can happen here:
                # 1) We have cell-centered values on the "Nlayer" grid; we can take these variables and map them to 'lev'
                # 2) We have edge value on an "Nlayer" + 1 grid; we can take these and use them with 'lev_edge'
                # 3) We have troposphere values on "Ntrop"; we can take these and use them with 'lev_trop', but we won't have coordinate information yet
                # All other cases we do not handle yet; this includes the aircraft emissions and a few other things. Note that tracer sources do not have a vertical coord to worry about!
                nlev = dshape[-1]
                grid_nlev = self.ctm_info.Nlayers
                grid_ntrop = self.ctm_info.Ntrop
                try:
                    if nlev == grid_nlev:
                        dims.append('lev')
                    elif nlev == grid_nlev + 1:
                        dims.append('lev_edge')
                    elif nlev == grid_ntrop:
                        dims.append('lev_trop')
                    else:
                        continue
                except AttributeError:
                    warnings.warn("Couldn't resolve grid_spec vertical layout")
                    continue

            # xarray Variables are thin wrappers for numpy.ndarrays, or really
            # any object that extends the ndarray interface. A critical part of
            # the original ndarray interface is that the underlying data has to
            # be contiguous in memory. We can enforce this to happen by
            # concatenating each bundle in the variable data bundles we read
            # from the bpch file
            data = self._concat([v.data for v in var_data])

            # Is the variable time-invariant? If it is, kill the time dim.
            # Here, we mean it only as one sample in the dataset.
            # if dshape[0] == 1:
            #     del dims[0]

            # If requested, try to coerce the attributes and metadata to
            # something a bit more CF-friendly
            lookup_name = vname
            if fix_cf:
                if 'unit' in var_attr:
                    cf_units = cf.get_cfcompliant_units(
                        var_attr['unit']
                    )
                    var_attr['unit'] = cf_units
                vname = cf.get_valid_varname(vname)

            # TODO: Explore using a wrapper with an NDArrayMixin; if you don't do this, then dask won't work correctly (it won't promote the data to an array from a BPCHDataProxy). I'm not sure why.
            # data = BPCHVariableWrapper(lookup_name, self)
            var = xr.Variable(dims, data, var_attr)

            # Shuffle dims for CF/COARDS compliance if requested
            # TODO: For this to work, we have to force a load of the data.
            #       Is there a way to re-write BPCHDataProxy so that that's not
            #       necessary?
            #       Actually, we can't even force a load becase var.data is a
            #       numpy.ndarray. Weird.
            # if fix_dims:
            #     target_dims = [d for d in DIM_ORDER_PRIORITY if d in dims]
            #     var = var.transpose(*target_dims)

            self._variables[vname] = var

            # Try to add a time dimension
            # TODO: Time units?
            if (len(var_data) > 1) and 'time' not in self._variables:
                time_bnds = np.asarray([v.time for v in var_data])
                times = time_bnds[:, 0]

                self._variables['time'] = xr.Variable(
                    ['time', ], times,
                    {'bounds': 'time_bnds', 'units': cf.CTM_TIME_UNIT_STR}
                )
                self._variables['time_bnds'] = xr.Variable(
                    ['time', 'nv'], time_bnds,
                    {'units': cf.CTM_TIME_UNIT_STR}
                )
                self._variables['nv'] = xr.Variable(['nv', ], [0, 1])

        # Create the dimension variables; we have a lot of options
        # here with regards to the vertical coordinate. For now,
        # we'll just use the sigma or eta coordinates.
        # Useful CF info: http://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#_atmosphere_hybrid_sigma_pressure_coordinate
        # self._variables['Ap'] =
        # self._variables['Bp'] =
        # self._variables['altitude'] =

        # Time dimensions
        # self._times = self.ds.times
        # self._time_bnds = self.ds.time_bnds


    def _concat(self, *args, **kwargs):
        if self._dask:
            return da.concatenate(*args, **kwargs)
        else:
            return np.concatenate(*args, **kwargs)

    def get_variables(self):
        return self._variables

    def get_attrs(self):
        return Frozen(self._attributes)

    def get_dimensions(self):
        return Frozen(self._dimensions)


    def close(self):
        self._bpch.close()
        for var in list(self._variables):
            del self._variables[var]

    def __exit__(self, type, value, traceback):
        self.close()


class BPCHDataBundle(object):
    """ A single slice of a single variable inside a bpch file, and all
    of its critical accompanying metadata. """

    __slots__ = ('_shape', 'dtype', 'endian', 'filename', 'file_position',
                 'time', 'metadata', '_data', '_mmap', '_dask')

    def __init__(self, shape,  endian, filename, file_position, time,
                 metadata, dtype=None, use_mmap=False, dask_delayed=False):
        self._shape = shape
        self.dtype = dtype
        self.endian = endian
        self.filename = filename
        self.file_position = file_position
        self.time = time
        self.metadata = metadata

        if dtype is None:
            self.dtype = np.dtype(self.endian + DEFAULT_DTYPE)
        else:
            self.dtype = dtype

        self._data = None
        self._mmap = use_mmap
        self._dask = dask_delayed

    @property
    def shape(self):
        return self._shape

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def array(self):
        return self.data

    @property
    def data(self):
        if self._data is None:
            self._data = self._read()
        return self._data

    def _read(self):
        """ Helper function to load the data referenced by this bundle. """
        if self._dask:
            d = da.from_delayed(
                delayed(read_from_bpch, )(
                    self.filename, self.file_position, self.shape,
                    self.dtype, self.endian, use_mmap=self._mmap
                ),
                self.shape, self.dtype
            )
        else:
            d = read_from_bpch(
                    self.filename, self.file_position, self.shape,
                    self.dtype, self.endian, use_mmap=self._mmap
            )

        return d


def read_from_bpch(filename, file_position, shape, dtype, endian,
                   use_mmap=False):
    """ Read a chunk of data from a bpch output file.

    Parameters
    ----------
    filename : str
        Path to file on disk containing the  data
    file_position : int
        Position (bytes) where desired data chunk begins
    shape : tuple of ints
        Resultant (n-dimensional) shape of requested data; the chunk
        will be read sequentially from disk and then re-shaped
    dtype : dtype
        Dtype of data; for best results, pass a dtype which includes
        an endian indicator, e.g. `dtype = np.dtype('>f4')`
    endian : str
        Endianness of data; should be consistent with `dtype`
    use_mmap : bool
        Memory map the chunk of data to the file on disk, else read
        immediately

    Returns
    -------
    Array with shpae `shape` and dtype `dtype` containing the requested
    chunk of data from `filename`.

    """
    offset = file_position + 4
    if use_mmap:
        d = np.memmap(filename, dtype=dtype, mode='r', shape=shape,
                      offset=offset, order='F')
    else:
        with FortranFile(filename, 'rb', endian) as ff:
            ff.seek(file_position)
            d = np.array(ff.readline('*f'))
            d = d.reshape(shape, order='F')

    # As a sanity check, *be sure* that the resulting data block has the
    # correct shape, and fail early if it doesn't.
    if (d.shape != shape):
        raise IOError("Data chunk read from {} does not have the right shape,"
                      " (expected {} but got {})"
                      .format(filename, shape, d.shape))

    return d


class BPCHFile(object):
    """ A file object for BPCH data on disk """

    def __init__(self, filename, mode='rb', endian='>',
                 diaginfo_file='', tracerinfo_file='', eager=False,
                 use_mmap=False, dask_delayed=False):

        self.mode = mode
        if not mode.startswith('r'):
            raise ValueError("Currently only know how to 'r(b)'ead bpch files.")

        self.filename = filename
        self.fsize = os.path.getsize(self.filename)
        self.endian = endian

        # Open a pointer to the file
        self.fp = FortranFile(self.filename, self.mode, self.endian)

        dir_path = os.path.abspath(os.path.dirname(filename))
        if not dir_path:
            dir_path = os.getcwd()
        if not tracerinfo_file:
            tracerinfo_file = os.path.join(dir_path, "tracerinfo.dat")
            if not os.path.exists(tracerinfo_file):
                tracerinfo_file = ''
        self.tracerinfo_file = tracerinfo_file
        if not diaginfo_file:
            diaginfo_file = os.path.join(dir_path, "diaginfo.dat")
            if not os.path.exists(diaginfo_file):
                diaginfo_file = ''
        self.diaginfo_file = diaginfo_file

        # Container to record file metadata
        self._attributes = OrderedDict()

        # Don't necessarily need to save diag/tracer_dict yet
        self.diaginfo_df, _ = get_diaginfo(self.diaginfo_file)
        self.tracerinfo_df, _ = get_tracerinfo(self.tracerinfo_file)

        # Container for bundles contained in the output file.
        self.var_data = []
        self.var_attrs = []

        # Critical information for accessing file contents
        self._header_pos = None

        # Data loading strategy
        self.use_mmap = use_mmap
        self.dask_delayed = dask_delayed

        # Control eager versus deferring reading
        self.eager = eager
        if (mode.startswith('r') and self.eager):
            self._read()



    def close(self):
        """ Close this bpch file. """

        if not self.fp.closed:
            for v in list(self.var_data):
                del self.var_data[v]

            self.fp.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _read(self):
        """ Parse the entire bpch file on disk and set up easy access to meta-
        and data blocks. """

        self._read_metadata()
        self._read_header()
        self._read_var_data()


    def _read_metadata(self):
        """ Read the main metadata packaged within a bpch file, indicating
        the output filetype and its title. """

        filetype = self.fp.readline().strip()
        filetitle = self.fp.readline().strip()

        self.__setattr__('filetype', filetype)
        self.__setattr__('filetitle', filetitle)


    def _read_header(self, all_info=False):
        """ Process the header information for a bpch file, which includes
        the data model name and the grid resolution / specifications. """

        self._header_pos = self.fp.tell()

        line = self.fp.readline('20sffii')
        modelname, res0, res1, halfpolar, center180 = line
        self._attributes.update({
            "modelname": str(modelname, 'utf-8').strip(),
            "halfpolar": halfpolar,
            "center180": center180,
            "res": (res0, res1)
        })
        self.__setattr__('modelname', modelname)
        self.__setattr__('res', (res0, res1))
        self.__setattr__('halfpolar', halfpolar)
        self.__setattr__('center180', center180)

        # Re-wind the file
        self.fp.seek(self._header_pos)


    def _read_var_data(self):
        """ Iterate over the block of this bpch file and return handlers
        in the form of `BPCHDataBundle`s for access to the data contained
        therein. """

        var_bundles = OrderedDict()
        var_attrs = OrderedDict()

        n_vars = 0

        while self.fp.tell() < self.fsize:

            var_attr = OrderedDict()

            # read first and second header lines
            line = self.fp.readline('20sffii')
            modelname, res0, res1, halfpolar, center180 = line

            line = self.fp.readline('40si40sdd40s7i')
            category_name, number, unit, tau0, tau1, reserved = line[:6]
            dim0, dim1, dim2, dim3, dim4, dim5, skip = line[6:]
            var_attr['number'] = number

            # Decode byte-strings to utf-8
            category_name = str(category_name, 'utf-8')
            var_attr['category'] = category_name.strip()
            unit = str(unit, 'utf-8')

            # get additional metadata from tracerinfo / diaginfo
            try:
                cat_df = self.diaginfo_df[
                    self.diaginfo_df.name == category_name.strip()
                ]
                # TODO: Safer logic for handling case where more than one
                #       tracer metadata match was made
                # if len(cat_df > 1):
                #     raise ValueError(
                #         "More than one category matching {} found in "
                #         "diaginfo.dat".format(
                #             category_name.strip()
                #         )
                #     )
                # Safe now to select the only row in the DataFrame
                cat = cat_df.T.squeeze()

                tracer_num = int(cat.offset) + int(number)
                diag_df = self.tracerinfo_df[
                    self.tracerinfo_df.tracer == tracer_num
                ]
                # TODO: Safer logic for handling case where more than one
                #       tracer metadata match was made
                # if len(diag_df > 1):
                #     raise ValueError(
                #         "More than one tracer matching {:d} found in "
                #         "tracerinfo.dat".format(tracer_num)
                #     )
                # Safe now to select only row in the DataFrame
                diag = diag_df.T.squeeze()
                diag_attr = diag.to_dict()

                if not unit.strip():  # unit may be empty in bpch
                    unit = diag_attr['unit']  # but not in tracerinfo
                var_attr.update(diag_attr)
            except:
                diag = {'name': '', 'scale': 1}
                var_attr.update(diag)
            var_attr['unit'] = unit

            vname = diag['name']
            fullname = category_name.strip() + "_" + vname

            # parse metadata, get data or set a data proxy
            if dim2 == 1:
                data_shape = (dim0, dim1)         # 2D field
            else:
                data_shape = (dim0, dim1, dim2)
            var_attr['original_shape'] = data_shape

            # Add proxy time dimension to shape
            data_shape = tuple([1, ] + list(data_shape))
            origin = (dim3, dim4, dim5)
            var_attr['origin'] = origin

            timelo, timehi = cf.tau2time(tau0), cf.tau2time(tau1)

            pos = self.fp.tell()
            # Note that we don't pass a dtype, and assume everything is
            # single-fp floats with the correct endian, as hard-coded
            var_bundle = BPCHDataBundle(
                data_shape, self.endian, self.filename, pos, [timelo, timehi],
                metadata=var_attr,
                use_mmap=self.use_mmap, dask_delayed=self.dask_delayed
            )
            self.fp.skipline()

            # Save the data as a "bundle" for concatenating in the final step
            if fullname in var_bundles:
                var_bundles[fullname].append(var_bundle)
            else:
                var_bundles[fullname] = [var_bundle, ]
                var_attrs[fullname] = var_attr
                n_vars += 1

        self.var_data = var_bundles
        self.var_attrs = var_attrs