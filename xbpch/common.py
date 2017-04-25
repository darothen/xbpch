
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