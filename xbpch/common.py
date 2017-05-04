
from datetime import datetime

import numpy as np

# physical or chemical constants
C_MOLECULAR_WEIGHT = 12e-3    # molecular weight of C atoms (kg/mole)

def broadcast_1d_array(arr, ndim, axis=1):
    """
    Broadcast 1-d array `arr` to `ndim` dimensions on the first axis
    (`axis`=0) or on the last axis (`axis`=1).

    Useful for 'outer' calculations involving 1-d arrays that are related to
    different axes on a multidimensional grid.
    """
    ext_arr = arr
    for i in range(ndim - 1):
        ext_arr = np.expand_dims(ext_arr, axis=axis)
    return ext_arr


def get_timestamp(time=True, date=True, fmt=None):
    """ Return the current timestamp in machine local time.

    Parameters:
    -----------
    time, date : Boolean
        Flag to include the time or date components, respectively,
        in the output.
    fmt : str, optional
        If passed, will override the time/date choice and use as
        the format string passed to `strftime`.
    """

    time_format = "%H:%M:%S"
    date_format = "%m-%d-%Y"

    if fmt is None:
        if time and date:
            fmt = time_format + " " + date_format
        elif time:
            fmt = time_format
        elif date:
            fmt = date_format
        else:
            raise ValueError("One of `date` or `time` must be True!")

    return datetime.now().strftime(fmt)


def fix_attr_encoding(ds):
    """ This is a temporary hot-fix to handle the way metadata is encoded
    when we read data directly from bpch files. It removes the 'scale_factor'
    and 'units' attributes we encode with the data we ingest, converts the
    'hydrocarbon' and 'chemical' attribute to a binary integer instead of a
    boolean, and removes the 'units' attribute from the "time" dimension since
    that too is implicitly encoded.

    In future versions of this library, when upstream issues in decoding
    data wrapped in dask arrays is fixed, this won't be necessary and will be
    removed.

    """

    def _maybe_del_attr(da, attr):
        """ Possibly delete an attribute on a DataArray if it's present """
        if attr in da.attrs:
            del da.attrs[attr]
        return da

    def _maybe_decode_attr(da, attr):
        # TODO: Fix this so that bools get written as attributes just fine
        """ Possibly coerce an attribute on a DataArray to an easier type
        to write to disk. """
        # bool -> int
        if (attr in da.attrs) and (type(da.attrs[attr] == bool)):
            da.attrs[attr] = int(da.attrs[attr])
        return da

    for v in ds.data_vars:
        da = ds[v]
        da = _maybe_del_attr(da, 'scale_factor')
        da = _maybe_del_attr(da, 'units')
        da = _maybe_decode_attr(da, 'hydrocarbon')
        da = _maybe_decode_attr(da, 'chemical')
    # Also delete attributes on time.
    times = ds.time
    times = _maybe_del_attr(times, 'units')

    return ds
