"""
API for reading BPCH files via xarray

"""
from __future__ import print_function, division

from glob import glob
import os
import numpy as np
import xarray as xr
import warnings

import dask.array as da

from xarray.core.pycompat import OrderedDict, basestring
from xarray.backends.common import AbstractDataStore
from xarray.core.utils import Frozen

from . bpch import BPCHFile
from . common import get_timestamp
from . grid import BASE_DIMENSIONS, CTMGrid
from . util import cf
from . version import __version__ as ver


def open_bpchdataset(filename, fields=[], categories=[],
                     tracerinfo_file='tracerinfo.dat',
                     diaginfo_file='diaginfo.dat',
                     endian=">", decode_cf=True,
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
    decode_cf : bool
        Enforce CF conventions for variable names, units, and other metadata
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
    # Record what the file object underlying the store which we culled this
    # Dataset from is so that we can clean it up later
    ds._file_obj = store._bpch

    # Handle CF corrections
    if decode_cf:
        decoded_vars = OrderedDict()
        rename_dict = {}
        for v in ds:
            cf_name = cf.get_valid_varname(v)
            rename_dict[v] = cf_name
            new_var = cf.enforce_cf_variable(ds[v])
            decoded_vars[cf_name] = new_var
        ds = xr.Dataset(decoded_vars, attrs=ds.attrs.copy())

        # ds.rename(rename_dict, inplace=True)

        # TODO: There's a bug with xr.decode_cf which eagerly loads data.
        #       Re-enable this once that bug is fixed
        # Note that we do not need to decode the times because we explicitly
        # kept track of them as we parsed the data.
        # ds = xr.decode_cf(ds, decode_times=False)

    # Set attributes for CF conventions
    ts = get_timestamp()
    ds.attrs.update(dict(
        Conventions='CF1.6',
        source=filename,
        tracerinfo=tracerinfo_file,
        diaginfo=diaginfo_file,
        filetype=store._bpch.filetype,
        filetitle=store._bpch.filetitle,
        history=(
            "{}: Processed/loaded by xbpch-{} from {}"
            .format(ts, ver, filename)
        ),
    ))

    # To immediately load the data from the BPCHDataProxy paylods, need
    # to execute ds.data_vars for some reason...
    if return_store:
        return ds, store
    else:
        return ds


def open_mfbpchdataset(paths, concat_dim='time', compat='no_conflicts',
                       preprocess=None, lock=None, **kwargs):
    """ Open multiple bpch files as a single dataset.

    You must have dask installed for this to work, as this greatly
    simplifies issues relating to multi-file I/O.

    Also, please note that this is not a very performant routine. I/O is still
    limited by the fact that we need to manually scan/read through each bpch
    file so that we can figure out what its contents are, since that metadata
    isn't saved anywhere. So this routine will actually sequentially load
    Datasets for each bpch file, then concatenate them along the "time" axis.
    You may wish to simply process each file individually, coerce to NetCDF,
    and then ingest through xarray as normal.

    Parameters
    ----------
    paths : list of strs
        Filenames to load; order doesn't matter as they will be
        lexicographically sorted before we read in the data
    concat_dim : str, default='time'
        Dimension to concatenate Datasets over. We default to "time" since this
        is how GEOS-Chem splits output files
    compat : str (optional)
        String indicating how to compare variables of the same name for
        potential conflicts when merging:

        - 'broadcast_equals': all values must be equal when variables are
          broadcast against each other to ensure common dimensions.
        - 'equals': all values and dimensions must be the same.
        - 'identical': all values, dimensions and attributes must be the
          same.
        - 'no_conflicts': only values which are not null in both datasets
          must be equal. The returned dataset then contains the combination
          of all non-null values.
    preprocess : callable (optional)
        A pre-processing function to apply to each Dataset prior to
        concatenation
    lock : False, True, or threading.Lock (optional)
        Passed to :py:func:`dask.array.from_array`. By default, xarray
        employs a per-variable lock when reading data from NetCDF files,
        but this model has not yet been extended or implemented for bpch files
        and so this is not actually used. However, it is likely necessary
        before dask's multi-threaded backend can be used
    **kwargs : optional
        Additional arguments to pass to :py:func:`xbpch.open_bpchdataset`.
    
    """

    from xarray.backends.api import _MultiFileCloser

    # TODO: Include file locks?

    # Check for dask
    dask = kwargs.pop('dask', False)
    if not dask:
        raise ValueError("Reading multiple files without dask is not supported")
    kwargs['dask'] = True

    # Add th

    if isinstance(paths, basestring):
        paths = sorted(glob(paths))
    if not paths:
        raise IOError("No paths to files were passed into open_mfbpchdataset")

    datasets = [open_bpchdataset(filename, **kwargs)
                for filename in paths]
    bpch_objs = [ds._file_obj for ds in datasets]

    if preprocess is not None:
        datasets = [preprocess(ds) for ds in datasets]

    # Concatenate over time
    combined = xr.auto_combine(datasets, compat=compat, concat_dim=concat_dim)

    combined._file_obj = _MultiFileCloser(bpch_objs)
    combined.attrs = datasets[0].attrs
    ts = get_timestamp()
    fns_str = " ".join(paths)
    combined.attrs['history'] = (
        "{}: Processed/loaded by xbpch-{} from {}"
        .format(ts, ver, fns_str)
    )


    return combined


class BPCHDataStore(AbstractDataStore):
    """ Store for reading data from binary punch files.

    Note that this is intended as a backend only; to open and read a given
    bpch file, use :meth:`open_bpchdataset`.

    Examples of other extensions using the core DataStore API can be found at:

    - https://github.com/pydata/xarray/blob/master/xarray/conventions.py
    - https://github.com/xgcm/xmitgcm/blob/master/xmitgcm/mds_store.py

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

        # Parse the binary file and prepare to add variables to the DataStore
        self._bpch._read_var_data()

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
            dict(dims=['lon', ], attrs={
                'axis': 'X', 'long_name': 'longitude coordinate',
                'standard_name': 'longitude'
            })
        )
        self._dimensions.append(
            dict(dims=['lat', ], attrs={
                'axis': 'y', 'long_name': 'latitude coordinate',
                'standard_name': 'latitude'
            })
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

        # Detect if we're on a nested grid; in that case, we'll have a displaced
        # origin set in the variable attributes we previously read
        ref_key = list(self._bpch.var_attrs.keys())[0]
        ref_attrs = self._bpch.var_attrs[ref_key]
        self.is_nested = (ref_attrs['origin'] != (1, 1, 1))

        lon_centers = self.ctm_info.lon_centers
        lat_centers = self.ctm_info.lat_centers

        if self.is_nested:
            ix, iy, _ = ref_attrs['origin']
            nx, ny, *_ = ref_attrs['original_shape']
            # Correct i{x,y} for IDL->Python indexing (1-indexed -> 0-indexed)
            ix -= 1
            iy -= 1
            lon_centers = lon_centers[ix:ix+nx]
            lat_centers = lat_centers[iy:iy+ny]

        self._variables['lon'] = xr.Variable(
            ['lon'], lon_centers,
            {'long_name': 'longitude', 'units': 'degrees_east'}
        )
        self._variables['lat'] = xr.Variable(
            ['lat'], lat_centers,
            {'long_name': 'latitude', 'units': 'degrees_north'}
        )
        # TODO: Fix longitudes if ctm_grid.center180

        # Add variables from the parsed BPCH file to our DataStore
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
            if data.shape[0] == 1:
                dims = dims[1:]
                data = data.squeeze()

            # Create a variable containing this data
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
