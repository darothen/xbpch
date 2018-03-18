"""
This module provides the capability to interpret CTM metadata according
to the 'NetCDF Climate and Forecast (CF) Metadata Conventions'

References:

    [CF]  NetCDF Climate and Forecast (CF) Metadata conventions, Version 1.6,
    December, 2011.
"""

import datetime

from xarray.core.variable import as_variable, Variable

#: CTM timestamp definitions
CTM_TIME_UNIT_STR = 'hours since 1985-01-01 00:00:00'
CTM_TIME_REF_DT = datetime.datetime(1985, 1, 1)


def tau2time(tau, reference=CTM_TIME_REF_DT):
    """
    Convert given hours since reference (default: 01.01.1985 00:00)
    into a datetime object.
    """
    return reference + datetime.timedelta(hours=tau)


def time2tau(time, reference=CTM_TIME_REF_DT):
    """
    Convert a datetime object into given hours since reference
    (default: 01.01.1985 00:00).
    """
    return (time - reference).total_seconds() / 3600.0


#: Mapping for unit names: CTM -> udunits2
UNITS_MAP_CTM2CF = (
    ('molec CO2', 'count'),
    ('molec', 'count'),
    ('atoms S', 'count'),
    ('atoms C', 'count'),
    ('ppbC', 'ppb'),        # prefix or suffix required (nb. of carbon atoms)
    ('kg C', 'kg'),         # prefix or suffix required (?)
    ('molC', 'mol'),        # prefix or suffix required ?     TODO:
    ('gC', 'g'),            # prefix or suffix required ?
    ('kg S', 'kg'),
    ('kg OH', 'kg'),
    ('kg NO3', 'kg'),
    ('kg H2O2', 'kg'),
    ('unitless', '1'),
    ('unitles', '1'),       # typo found in tracerinfo or diaginfo
    ('v/v', '1'),
    ('level', '1'),         # allowed in CF1.6 but not compatible with udunits2
    ('Eta', '1'),
    ('Fraction', '1'),
    ('fraction', '1'),
    ('ratio', '1'),
    ('factor', '1'),
    ('none', '1'),
    ('[percentage]', '%'),
    ('deg C', 'Celsius'),
    ('C', 'Celsius'),
    ('mm/da', 'mm/day'),    # typo in tracerinfo.dat 4/17/12
    ('kg/m2/', 'kg/m2'))    # ?? (tracerinfo.dat 6801 (line 1075)


def get_cfcompliant_units(units, prefix='', suffix=''):
    """
    Get equivalent units that are compatible with the udunits2 library
    (thus CF-compliant).

    Parameters
    ----------
    units : string
        A string representation of the units.
    prefix : string
        Will be added at the beginning of the returned string
        (must be a valid udunits2 expression).
    suffix : string
        Will be added at the end of the returned string
        (must be a valid udunits2 expression).

    Returns
    -------
    A string representation of the conforming units.

    References
    ----------
    The udunits2 package : http://www.unidata.ucar.edu/software/udunits/

    Notes
    -----
    This function only relies on the table stored in :attr:`UNITS_MAP_CTM2CF`.
    Therefore, the units string returned by this function is not certified to
    be compatible with udunits2.

    Examples
    --------
    >>> get_cfcompliant_units('molec/cm2')
    'count/cm2'
    >>> get_cfcompliant_units('v/v')
    '1'
    >>> get_cfcompliant_units('ppbC', prefix='3')
    '3ppb

    """
    compliant_units = units

    for gcunits, udunits in UNITS_MAP_CTM2CF:
        compliant_units = str.replace(compliant_units, gcunits, udunits)

    return prefix + compliant_units + suffix


VARNAME_MAP_CHAR = (
    ('$', 'S'),
    (':', '_'),
    ('=', '_'),
    ('-', '_'),
)
# TODO: Variables like BXHGHT_S_N(AIR) should have *(AIR) replaced with
#       just *_AIR
def get_valid_varname(varname):
    """
    Replace characters (e.g., ':', '$', '=', '-') of a variable name, which
    may cause problems when using with (CF-)netCDF based packages.

    Parameters
    ----------
    varname : string
        variable name.

    Notes
    -----
    Characters replacement is based on the table stored in
    :attr:`VARNAME_MAP_CHAR`.

    """
    vname = varname
    for s, r in VARNAME_MAP_CHAR:
        vname = vname.replace(s, r)

    return vname


def enforce_cf_variable(var, mask_and_scale=True):
    """ Given a Variable constructed from GEOS-Chem output, enforce
    CF-compliant metadata and formatting.

    Until a bug with lazily-loaded data and masking/scaling is resolved in
    xarray, you have the option to manually mask and scale the data here.

    Parameters
    ----------
    var : xarray.Variable
        A variable holding information decoded from GEOS-Chem output.
    mask_and_scale : bool
        Flag to scale and mask the data given the unit conversions provided

    Returns
    -------
    out : xarray.Variable
        The original variable processed to conform to CF standards

    .. note::

        This method borrows heavily from the ideas in ``xarray.decode_cf_variable``

    """
    var = as_variable(var)
    data = var._data  # avoid loading by accessing _data instead of data
    dims = var.dims
    attrs = var.attrs.copy()
    encoding = var.encoding.copy()
    orig_dtype = data.dtype

    # Process masking/scaling coordinates. We only expect a "scale" value
    # for the units with this output.
    if 'scale' in attrs:
        scale = attrs.pop('scale')
        attrs['scale_factor'] = scale
        encoding['scale_factor'] = scale

        # TODO: Once the xr.decode_cf bug is fixed, we won't need to manually
        #       handle masking/scaling
        if mask_and_scale:
            data = scale*data

    # Process units
    # TODO: How do we want to handle parts-per-* units? These are not part of
    #       the udunits standard, and the CF conventions suggest using units
    #       like 1e-6 for parts-per-million. But we potentially mix mass and
    #       volume/molar mixing ratios in GEOS-Chem output, so we need a way
    #       to handle that edge case.
    if 'unit' in attrs:
        unit = attrs.pop('unit')
        unit = get_cfcompliant_units(unit)
        attrs['units'] = unit

    # TODO: Once the xr.decode_cf bug is fixed, we won't need to manually
    #       handle masking/scaling
    return Variable(dims, data, attrs, encoding=encoding)
