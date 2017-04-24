"""
Plumbing for enabling BPCH file I/O through xarray.
"""
from __future__ import print_function, division

import functools
import os
import numpy as np
import xarray as xr
import warnings

from xarray.core.pycompat import OrderedDict
from xarray.core.variable import  Variable
from xarray.backends.common import AbstractDataStore
from xarray.core.utils import Frozen, FrozenOrderedDict, NDArrayMixin
from xarray.core import indexing

from . uff import FortranFile
from . grid import BASE_DIMENSIONS, CTMGrid
from . util import cf
from . util.diaginfo import get_diaginfo, get_tracerinfo

DEFAULT_DTYPE = np.dtype('f4')


class BPCHArrayWrapper(NDArrayMixin):
    pass


class BPCHVariableWrapper(indexing.NumpyIndexingAdapter):

    def __init__(self, variable_name, datastore):
        self.datastore = datastore
        self.variable_name = variable_name

    @property
    def array(self):
        return self.datastore.ds.variables[self.variable_name].data

    @property
    def dtype(self):
        return np.dtype(self.array.dtype.kind + str(self.array.dtype.itemsize))

    def __getitem__(self, key):
        data = super(BPCHVariableWrapper, self).__getitem__(key)
        copy = self.datastore.memmap
        data = np.array(data, dtype=self.dtype, copy=copy)
        return data


class BPCHDataProxyWrapper(NDArrayMixin):
    # Mostly following the template of ScipyArrayWrapper
    # https://github.com/pydata/xarray/blob/master/xarray/backends/scipy_.py
    # and NioArrayWrapper
    # https://github.com/pydata/xarray/blob/master/xarray/backends/pynio_.py

    def __init__(self, array):
        self._array = array

    @property
    def array(self):
        data = self._array.data
        print(type(data))
        return data

    @property
    def dtype(self):
        return self._array.dtype

    def __getitem__(self, key):
        print(key)
        if key == () and self.ndim == 0:
            return self.array.get_value()
        return self.array[key]


def open_bpchdataset(filename, fields=[], categories=[],
                     tracerinfo_file='tracerinfo.dat',
                     diaginfo_file='diaginfo.dat',
                     endian=">", default_dtype=DEFAULT_DTYPE,
                     memmap=True, use_dask=True, return_store=False):
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

    Returns
    -------
    ds : xarray.Dataset
        Dataset containing the requested fields (or the entire file), with data
        contained in proxy containers for access later.

    """

    store = BPCHDataStore(
        filename, fields=fields, categories=categories,
        tracerinfo_file=tracerinfo_file,
        diaginfo_file=diaginfo_file, endian=endian, memmap=memmap
    )

    ds = xr.Dataset.load_store(store)

    # To immediately load the data from the BPCHDataProxy paylods, need
    # to execute ds.data_vars for some reason...
    if return_store:
        return ds, store
    else:
        return ds


class BPCHDataStore(AbstractDataStore):
    """ Store for reading data via pygchem.io.bpch_file. """

    def __init__(self, filename, fields=[], categories=[],
                 mode='r', endian='>', memmap=True,
                 diaginfo_file='', tracerinfo_file='',
                 maskandscale=False, fix_cf=False):

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
        pass
        self.endian = endian

        # Open a pointer to the file
        # self._fp = FortranFile(self.filename, self.mode, self.endian)

        opener = functools.partial(
            BPCHFile, filename=filename,
            mode=mode, endian=self.endian, memmap=memmap,
            diaginfo_file=diaginfo_file, tracerinfo_file=tracerinfo_file,
            maskandscale=maskandscale)

        self.ds = opener()
        self._opener = opener

        self.memmap = memmap
        self.fields = fields
        self.categories = categories

        # Create storage dicts for variables and attributes, to be used later
        # when xarray needs to access the data
        self._variables = OrderedDict()
        self._attributes = OrderedDict()
        self._attributes.update(self.ds._attributes)
        self._dimensions = [d for d in BASE_DIMENSIONS]

        # Get the list of variables in the file and load all the data:
        dim_coords = {}
        self._times = self.ds.times
        print(len(self._times))
        self._time_bnds = self.ds.time_bnds
        print(self._attributes)
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

        for vname, v in self.ds.variables.items():
            if fields and (v.attributes['name'] not in fields):
                continue
            if categories and (v.attributes['category '] not in categories):
                continue
            print("*** GOLDEN")

            # Process dimensions
            dims = ['time', 'lon', 'lat', ]
            dshape = v.shape
            if len(dshape) > 3:
                # Process the vertical coordinate. A few things can happen here:
                # 1) We have cell-centered values on the "Nlayer" grid; we can take these variables and map them to 'lev'
                # 2) We have edge value on an "Nlayer" + 1 grid; we can take these and use them with 'lev_edge'
                # 3) We have troposphere values on "Ntrop"; we can take these and use them with 'lev_trop', but we won't have coordinate information yet
                # All other cases we do not handle yet; this includes the aircraft emissions and a few other things. Note that tracer sources do not have a vertical coord to worry about!
                nlev = dshape[-1]
                grid_nlev = self.CTMGrid.Nlayers
                grid_ntrop = self.CTMGrid.Ntrop
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

            # Is the variable time-invariant? If it is, kill the time dim.
            # Here, we mean it only as one sample in the dataset.
            if dshape[0] == 1:
                del dims[0]

            # If requested, try to coerce the attributes and metadata to
            # something a bit more CF-friendly
            lookup_name = vname
            if fix_cf:
                if 'units' in v.attributes:
                    cf_units = cf.get_cfcompliant_units(
                        v.attributes['units']
                    )
                    v.attributes['units'] = cf_units
                vname = cf.get_valid_varname(vname)

            # TODO: Explore using a wrapper with an NDArrayMixin; if you don't do this, then dask won't work correctly (it won't promote the data to an array from a BPCHDataProxy). I'm not sure why.
            data = BPCHVariableWrapper(lookup_name, self)
            var = xr.Variable(dims, data, v.attributes)

            print(var)

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

        # Create the dimension variables; we have a lot of options
        # here with regards to the vertical coordinate. For now,
        # we'll just use the sigma or eta coordinates.
        # Useful CF info: http://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#_atmosphere_hybrid_sigma_pressure_coordinate
        # self._variables['Ap'] =
        # self._variables['Bp'] =
        # self._variables['altitude'] =

        ## Vertical grid
        eta_centers = self.ctm_info.eta_centers
        sigma_centers = self.ctm_info.sigma_centers

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
        print(self._variables['lon'])
        # TODO: Fix longitudes if ctm_grid.center180

        # Time dimensions
        # TODO: Time units?
        self._variables['time'] = xr.Variable(
            ['time', ], self._times,
            {'bounds': 'time_bnds', 'units': cf.CTM_TIME_UNIT_STR}
        )
        self._variables['time_bnds'] = xr.Variable(
            ['time', 'nv'], self._time_bnds,
            {'units': cf.CTM_TIME_UNIT_STR}
        )
        self._variables['nv'] = xr.Variable(['nv', ], [0, 1])

    def get_variables(self):
        return self._variables

    def get_attrs(self):
        return Frozen(self._attributes)

    def get_dimensions(self):
        return Frozen(self._dimensions)


    def close(self):
        # self._fp.close()
        self.ds.close()
        for var in list(self._variables):
            del self._variables[var]

    def __exit__(self, type, value, traceback):
        self.close()


class BPCHDataProxy(object):
    """A reference to the data payload of a single BPCH file datablock."""

    # __slots__ = ('_shape', 'dtype', 'path', 'endian', 'file_position',
    #              'scale_factor', 'fill_value', 'maskandscale', '_data')

    def __init__(self, shape, dtype, path, endian, file_position,
                 scale_factor, fill_value, maskandscale):
        self._shape = shape
        self.dtype = dtype
        self.path = path
        self.fill_value = fill_value
        self.endian = endian
        self.file_position = file_position
        self.scale_factor = scale_factor
        self.maskandscale = maskandscale
        self._data = None

    def _maybe_mask_and_scale(self, arr):
        if self.maskandscale and (self.scale_factor is not None):
            arr = self.scale_factor * arr
        return arr

    @property
    def shape(self):
        return self._shape

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def data(self):
        if self._data is None:
            self._data = self.load()
        return self._data

    def array(self):
        return self.data

    def load(self):
        with FortranFile(self.path, 'rb', self.endian) as bpch_file:
            pos = self.file_position
            bpch_file.seek(pos)
            data = np.array(bpch_file.readline('*f'))
            data = data.reshape(self._shape, order='F')
        if self.maskandscale and (self.scale_factor is not None):
            data = data * self.scale_factor
        return data

    def __getitem__(self, keys):
        return self.data[keys]

    def __repr__(self):
        fmt = '<{self.__class__.__name__} shape={self.shape}' \
              ' dtype={self.dtype!r} path={self.path!r}' \
              ' file_position={self.file_position}' \
              ' scale_factor={self.scale_factor}>'
        return fmt.format(self=self)

    def __getstate__(self):
        return {attr: getattr(self, attr) for attr in self.__slots__}

    def __setstate__(self, state):
        for key, value in list(state.items()):
            setattr(self, key, value)


class BPCHVariable(BPCHDataProxy):

    def __init__(self, data_pieces, *args, attributes=None,
                 **kwargs):
        self._data_pieces = data_pieces
        super(BPCHVariable, self).__init__(*args, **kwargs)

        if attributes is not None:
            self._attributes = attributes
        else:
            self._attributes = OrderedDict()
        for k, v in self._attributes.items():
            self.__dict__[k] = v

    def load(self):
        warnings.warn("'load' disabled on bpch_variable.")
        pass

    @property
    def shape(self):
        shape_copy = list(self._shape)
        shape_copy[0] = len(self._data_pieces)
        return tuple(shape_copy)

    @property
    def chunks(self):
        return len(self._data_pieces)

    @property
    def data(self):
        arr = np.concatenate(self._data_pieces, axis=0).view(self.dtype)
        return self._maybe_mask_and_scale(arr)

    @property
    def attributes(self):
        return self._attributes

    def __setattr__(self, key, value):
        try:
            self._attribute[key] = value
        except AttributeError:
            pass
        self.__dict__[key] = value

    def __str__(self):
        pass

    def __repr__(self):
        return """
          <{self.__class__.__name__}
          shape={self.shape} (chunks={self.chunks})
           dtype={self.dtype!r} scale_factor={self.scale_factor}>
        """.format(self=self)

    def __getitem__(self, index):
        if self.chunks == 1:
            arr = self._data_pieces[0][index]
        else:
            pass

        return self._maybe_mask_and_scale(arr)


class BPCHFile(object):
    """ A file object for BPCH data on disk """

    def __init__(self, filename, mode='rb', endian='>', memmap=False,
                 diaginfo_file='', tracerinfo_file='',
                 maskandscale=False):

        self.mode = mode
        if not mode.startswith('r'):
            raise ValueError("Currently only know how to 'r(b)'ead bpch files.")

        self.filename = filename
        self.fsize = os.path.getsize(self.filename)
        self.use_mmap = memmap
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

        # Don't necessarily need to save diag/tracer_dict yet
        self.diaginfo_df, _ = get_diaginfo(self.diaginfo_file)
        self.tracerinfo_df, _ = get_tracerinfo(self.tracerinfo_file)

        # self.dimensions = OrderedDict()
        self.variables = OrderedDict()
        self.times = []
        self.time_bnds = []

        self._attributes = OrderedDict()

        # Critical information for accessing file contents
        self.maskandscale = maskandscale
        self._header_pos = None

        if mode.startswith('r'):
            self._read()


    def close(self):
        """ Close this bpch file. """
        import weakref
        import warnings

        if not self.fp.closed:
            self.variables = OrderedDict()

            # if self._mm_buf is not None:
            #     ref = weakref.ref(self._mm_buf)
            #     self._mm_buf = None
            #     if ref() is None:
            #         self._mm.close()
            #     else:
            #         warnings.warn(
            #             "Can't close bpch_file opened with memory mapping until "
            #             "all of variables/arrays referencing its data are "
            #             "copied and/or cleaned", category=RuntimeWarning)
            # self._mm = None
            self.fp.close()
    # __del__ = close

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _read(self):
        """ Parse the file on disk and set up easy access to meta-
        and data blocks """

        self._read_metadata()
        self._read_header()
        self._read_var_data()


    def _read_metadata(self):
        """ Read the main metadata packaged within a bpch file """

        filetype = self.fp.readline().strip()
        filetitle = self.fp.readline().strip()

        self.__setattr__('filetype', filetype)
        self.__setattr__('filetitle', filetitle)


    def _read_header(self, all_info=False):

        self._header_pos = self.fp.tell()

        line = self.fp.readline('20sffii')
        modelname, res0, res1, halfpolar, center180 = line
        self._attributes.update({
            "modelname":str(modelname, 'utf-8').strip(),
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

        var_bundles = OrderedDict()
        var_attrs = OrderedDict()
        _times = []

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
                # if len(cat_df > 1):
                #     raise ValueError(
                #         "More than one category matching {} found in "
                #         "diaginfo.dat".format(
                #             category_name.strip()
                #         )
                #     )
                # Safe now to select the only row in the DataFrame
                cat = cat_df.T.squeeze()
                cat_attr = cat.to_dict()

                tracer_num = int(cat.offset) + int(number)
                diag_df = self.tracerinfo_df[
                    self.tracerinfo_df.tracer == tracer_num
                ]
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
                diag_attr = {}
                cat_attr = {}
            var_attr['unit'] = unit

            vname = diag['name']
            fullname = category_name.strip() + "_" + vname

            # parse metadata, get data or set a data proxy
            if dim2 == 1:
                data_shape = (dim0, dim1)         # 2D field
            else:
                data_shape = (dim0, dim1, dim2)
            # Add proxy time dimension to shape
            data_shape = tuple([1, ] + list(data_shape))
            origin = (dim3, dim4, dim5)
            var_attr['origin'] = origin

            pos = self.fp.tell()

            # Map or read the data
            if self.use_mmap:
                dtype = np.dtype(self.endian + 'f4')
                offset = pos + 4
                data = np.memmap(self.filename, mode='r',
                                 shape=data_shape,
                                 dtype=dtype, offset=offset, order='F')
                # print(len(data), data_shape, np.product(data_shape))
                # data.shape = data_shape
                self.fp.skipline()
            else:
                self.fp.seek(pos)
                data = np.array(self.fp.readline('*f'))
                # data = data.reshape(data_shape, order='F')
                data.shape = data_shape
            # Save the data as a "bundle" for concatenating in the final step
            if fullname in var_bundles:
                var_bundles[fullname].append(data)
            else:
                var_bundles[fullname] = [data, ]
                var_attrs[fullname] = var_attr
                n_vars += 1

            timelo, timehi = cf.tau2time(tau0), cf.tau2time(tau1)
            _times.append((timelo, timehi))

        # Copy over the data we've recorded
        self.time_bnds[:] = _times[::n_vars]
        self.times = [t[0] for t in _times[::n_vars]]

        for fullname, bundle in var_bundles.items():
            var_attr = var_attrs[fullname]
            self.variables[fullname] = BPCHVariable(
                bundle, data_shape, np.dtype('f'), self.filename, self.endian,
                file_position=None, scale_factor=var_attr['scale'],
                fill_value=np.nan, maskandscale=False, attributes=var_attr
            )