"""
Utilities and information for re-constructing GEOS-Chem horizontal and vertical
grids.
"""

import numpy as np

from xarray.core.pycompat import OrderedDict

from .common import broadcast_1d_array
from .util.gridspec import _get_model_info, prof_altitude

#: Hard-coded dimension variables to use with any Dataset read in
BASE_DIMENSIONS = OrderedDict(
    lon=dict(
        dims=['lon', ],
        attrs={
            'standard_name': 'longitude',
            'axis': 'X',
        }
    ),
    lat=dict(
        dims=['lat', ],
        attrs={
            'standard_name': 'latitude',
            'axis': 'Y',
        },
    ),
    time=dict(dims=['time', ], attrs={}),
    nv=dict(dims=['nv', ], attrs={}),
)


#: CF/COARDS recommended dimension order; non-spatiotemporal dimensions
#: should precede these.
DIM_ORDER_PRIORITY = ['time', 'lev', 'lat', 'lon']


def get_grid_spec(model_name):
    """
    Pass-through to look-up the grid specifications for a given GEOS-Chem
    configuration.

    Parameters
    ----------
    model_name : str
        Name of the model; variations in naming format are permissible, e.g.
        "GEOS5" can be requested as "GEOS-5" or "GEOS_5".

    Returns
    -------
    grid_spec : dict
        Critical grid information as items in a dictionary.

    """
    return _get_model_info(model_name)


def get_lonlat(rlon, rlat, halfpolar=True, center180=True):
    """
    Calculate longitude-latitude grid for a specified resolution and
    configuration / ordering.

    Parameters
    ----------
    rlon, rlat : float
        Resolution (in degrees) of longitude and latitude grids.
    halfpolar : bool (default=True)
        Polar grid boxes span half of rlat relative to the other grid cells.
    center180 : bool (default=True)
        Longitude grid should be centered at 180 degrees.

    """

    # Compute number of grid cells in each direction
    Nlon = int(360. / rlon)
    Nlat = int(180. / rlat) + halfpolar

    # Compute grid cell edges
    elon = np.arange(Nlon + 1) * rlon - np.array(180.)
    elon -= rlon / 2. * center180
    elat = np.arange(Nlat + 1) * rlat - np.array(90.)
    elat -= rlat / 2. * halfpolar
    elat[0] = -90.
    elat[-1] = 90.

    # Compute grid cell centers
    clon = (elon - (rlon / 2.))[1:]
    clat = np.arange(Nlat) * rlat - np.array(90.)

    # Fix grid boundaries if halfpolar
    if halfpolar:
        clat[0] = (elat[0] + elat[1]) / 2.
        clat[-1] = -clat[0]
    else:
        clat += (elat[1] - elat[0]) / 2.

    return {
        "lon_centers": clon, "lat_centers": clat,
        "lon_edges": elon, "lat_edges": elat
    }


def get_layers(grid_spec, Psurf=1013.25, Ptop=0.01, **kwargs):
    """
    Compute scalars or coordinates associated to the vertical layers.

    Parameters
    ----------
    grid_spec : dict
        Dictionary (from `get_grid_spec`) containing the information necessary
        to re-construct grid levels for a given model coordinate system.
        Surface air pressure(s) [hPa].

    Returns
    -------
    dictionary of vertical grid components, including eta (unitless),
    sigma (unitless), pressure (hPa), and altitude (km) on both layer centers
    and edges, ordered from bottom-to-top.

    Notes
    -----
    For pure sigma grids, sigma coordinates are given by the esig (edges) and
    csig (centers).

    For both pure sigma and hybrid grids, pressures at layers edges L are
    calculated as follows:

    .. math:: P_e(L) = A_p(L) + B_p(L) * (P_{surf} - C_p)

    where

    :math:`P_{surf}`, :math:`P_{top}`
        Air pressures at the surface and the top of the modeled atmosphere
        (:attr:`Psurf` and :attr:`Ptop` attributes of the :class:`CTMGrid`
        instance).
    :math:`A_p(L)`, :math:`Bp(L)`
        Specified in the grid set-up (`Ap` and `Bp` attributes) for hybrid
        grids, or respectively equals :math:`P_{top}` and :attr:`esig`
        attribute for pure sigma grids.
    :math:`Cp(L)`
        equals :math:`P_{top}` for pure sigma grids or equals 0 for hybrid
        grids.

    Pressures at grid centers are averages of pressures at grid edges:

    .. math:: P_c(L) = (P_e(L) + P_e(L+1)) / 2

    For hybrid grids, ETA coordinates of grid edges and grid centers are
    given by;

    .. math:: ETA_{e}(L) = (P_e(L) - P_{top}) / (P_{surf} - P_{top})
    .. math:: ETA_{c}(L) = (P_c(L) - P_{top}) / (P_{surf} - P_{top})

    Altitude values are fit using a 5th-degree polynomial; see
    `gridspec.prof_altitude` for more details.

    """

    Psurf = np.asarray(Psurf)
    output_ndims = Psurf.ndim + 1
    if output_ndims > 3:
        raise ValueError("`Psurf` argument must be a float or an array"
                         " with <= 2 dimensions (or None)")

    # Compute all variables: takes not much memory, fast
    # and better for code reading
    SIGe = None
    SIGc = None
    ETAe = None
    ETAc = None

    hybrid = ('hybrid' in grid_spec) and grid_spec['hybrid']
    if hybrid:
        try:
            Ap = broadcast_1d_array(grid_spec['Ap'], output_ndims)
            Bp = broadcast_1d_array(grid_spec['Bp'], output_ndims)
        except KeyError:
            raise ValueError("Impossible to compute vertical levels,"
                             " data is missing (Ap, Bp)")
        Cp = 0.
    else:
        try:
            Bp = SIGe = broadcast_1d_array(grid_spec['esig'], output_ndims)
            SIGc = broadcast_1d_array(grid_spec['csig'], output_ndims)
        except KeyError:
            raise ValueError("Impossible to compute vertical levels,"
                             " data is missing (esig, csig)")
        Ap = Cp = Ptop

    Pe = Ap + Bp * (Psurf - Cp)
    Pc = 0.5 * (Pe[0:-1] + Pe[1:])

    if hybrid:
        ETAe = (Pe - Ptop)/(Psurf - Ptop)
        ETAc = (Pc - Ptop)/(Psurf - Ptop)
    else:
        SIGe = SIGe * np.ones_like(Psurf)
        SIGc = SIGc * np.ones_like(Psurf)

    Ze = prof_altitude(Pe, **kwargs)
    Zc = prof_altitude(Pc, **kwargs)

    all_vars = {'eta_edges': ETAe,
                'eta_centers': ETAc,
                'sigma_edges': SIGe,
                'sigma_centers': SIGc,
                'pressure_edges': Pe,
                'pressure_centers': Pc,
                'altitude_edges': Ze,
                'altitude_centers': Zc}

    return all_vars