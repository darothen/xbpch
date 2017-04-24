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


class CTMGrid(object):
    """
    Set-up the grid of a CTM (2)3D model.

    Parameters
    ----------
    model_name : string
        Name of the model. If it is one of the supported models,
        (see :class:`CTMGrid`.supported_models), it is better to use
        :class:`CTMGrid`.from_model or :class:`CTMGrid`.copy_from_model
        to set-up the grid with appropriate parameter values.
    resolution : (float, float)
        Horizontal grid resolution (lon, lat) or (DI, DJ) [degrees]
        (default: (5, 4))
    halfpolar : bool
        Indicates whether polar grid boxes span half (True) or same (False)
        latitude as all other boxes (default: True)
    center180 : bool
        True if lon grid is centered at 180 degrees (default: True)
    hybrid : bool
        indicates whether the model is a sigma-pressure hybrid (True) or
        pure sigma (False) level model (default: True).
    Nlayers : int or None
        Number of vertical model layers. This number must correspond to the
        number of layers in the model output files and is used in
        conjunction with Ptop to convert sigma levels into pressure
        altitudes. Set value to None if the model has no vertical
        layer (2D) (default: None).
    Ntrop : int or None
        Number of layers in the troposphere (default: None)
    Psurf : float
        Average surface pressure [hPa] (default: 1013.15)
    Ptop : float
        Pressure at model top [hPa] (default: 0.01)
    description : string
        Model grid description
    model_family : string
        Model family (e.g., 'GEOS' for 'GEOS5')

    Other Parameters
    ----------------
    Ap, Bp : 1-d array_like
        Parameters for computing ETA coordinates of the vertical grid
        levels, if hybrid (Ap [hPa] ; Bp [unitless]).
    csig, esig : 1-d array_like
        Pre-defined sigma coordinates the centers and the bottom edges of
        the vertical grid, if pure sigma.

    Attributes
    ----------
    Attributes are the same than the parameters above, except `model_name`
    which becomes :attr:`model`.

    """

    def __init__(self, model_name, resolution=(5, 4), halfpolar=True,
                 center180=True, hybrid=True, Nlayers=None, Ntrop=None,
                 Psurf=1013.25, Ptop=0.01, description='', model_family='',
                 **kwargs):

        self.model = model_name
        self.description = description
        self.model_family = model_family
        self.resolution = resolution
        self.halfpolar = bool(halfpolar)
        self.center180 = bool(center180)
        self.hybrid = bool(hybrid)
        self.Ap = None
        self.Bp = None
        self.esig = None
        self.csig = None
        try:
            self.Nlayers = int(Nlayers)
            self.Ntrop = int(Ntrop)
        except TypeError:
            self.Nlayers = Nlayers
            self.Ntrop = Ntrop
        self.Psurf = Psurf
        self.Ptop = Ptop

        self._lonlat_edges = None
        self._lonlat_centers = None
        self._eta_edges = None
        self._eta_centers = None
        self._sigma_edges = None
        self._sigma_centers = None
        self._pressure_edges = None
        self._pressure_centers = None
        self._altitude_edges = None
        self._altitude_centers = None

        for k, v in kwargs.items():
            self.__setattr__(k, v)

        # Pre-compute grid info / coordinates
        layers = self.get_layers()
        for k, v in layers.items():
            self.__setattr__(k, v)
        lonlats = self.get_lonlat()
        for k, v in lonlats.items():
            self.__setattr__(k, v)


    @classmethod
    def from_model(cls, model_name, **kwargs):
        """
        Define a grid using the specifications of a given model.

        Parameters
        ----------
        model_name : string
            Name the model (see :func:`get_supported_models` for available
            model names).
            Supports multiple formats (e.g., 'GEOS5', 'GEOS-5' or 'GEOS_5').
        **kwargs : string
            Parameters that override the model  or default grid
          settings (See Other Parameters below).

        Returns
        -------
        A :class:`CTMGrid` object.

        Other Parameters
        ----------------
        resolution : (float, float)
            Horizontal grid resolution (lon, lat) or (DI, DJ) [degrees]
        Psurf : float
            Average surface pressure [hPa] (default: 1013.15)

        Notes
        -----
        Regridded vertical models may have several valid names (e.g.,
        'GEOS5_47L' and 'GEOS5_REDUCED' refer to the same model).

        """
        settings = _get_model_info(model_name)
        model = settings.pop('model_name')
        for k, v in list(kwargs.items()):
            if k in ('resolution', 'Psurf'):
                settings[k] = v

        return cls(model, **settings)

    @classmethod
    def copy_from_model(cls, model_name, reference, **kwargs):
        """
        Set-up a user-defined grid using specifications of a reference
        grid model.

        Parameters
        ----------
        model_name : string
            name of the user-defined grid model.
        reference : string or :class:`CTMGrid` instance
            Name of the reference model (see :func:`get_supported_models`),
            or a :class:`CTMGrid` object from which grid set-up is copied.
        **kwargs
            Any set-up parameter which will override the settings of the
            reference model (see :class:`CTMGrid` parameters).

        Returns
        -------
        A :class:`CTMGrid` object.

        """
        if isinstance(reference, cls):
            settings = reference.__dict__.copy()
            settings.pop('model')
        else:
            settings = _get_model_info(reference)
            settings.pop('model_name')

        settings.update(kwargs)
        settings['reference'] = reference

        return cls(model_name, **settings)


    def get_layers(self, Psurf=1013.25, Ptop=0.01, **kwargs):
        """
        Compute scalars or coordinates associated to the vertical layers.

        Parameters
        ----------
        grid_spec : CTMGrid object
            CTMGrid containing the information necessary to re-construct grid
            levels for a given model coordinate system.

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

        if self.hybrid:
            try:
                Ap = broadcast_1d_array(self.Ap, output_ndims)
                Bp = broadcast_1d_array(self.Bp, output_ndims)
            except KeyError:
                raise ValueError("Impossible to compute vertical levels,"
                                 " data is missing (Ap, Bp)")
            Cp = 0.
        else:
            try:
                Bp = SIGe = broadcast_1d_array(self.esig, output_ndims)
                SIGc = broadcast_1d_array(self.csig, output_ndims)
            except KeyError:
                raise ValueError("Impossible to compute vertical levels,"
                                 " data is missing (esig, csig)")
            Ap = Cp = Ptop

        Pe = Ap + Bp * (Psurf - Cp)
        Pc = 0.5 * (Pe[0:-1] + Pe[1:])

        if self.hybrid:
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


    def get_lonlat(self):
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

        rlon, rlat = self.resolution

        # Compute number of grid cells in each direction
        Nlon = int(360. / rlon)
        Nlat = int(180. / rlat) + self.halfpolar

        # Compute grid cell edges
        elon = np.arange(Nlon + 1) * rlon - np.array(180.)
        elon -= rlon / 2. * self.center180
        elat = np.arange(Nlat + 1) * rlat - np.array(90.)
        elat -= rlat / 2. * self.halfpolar
        elat[0] = -90.
        elat[-1] = 90.

        # Compute grid cell centers
        clon = (elon - (rlon / 2.))[1:]
        clat = np.arange(Nlat) * rlat - np.array(90.)

        # Fix grid boundaries if halfpolar
        if self.halfpolar:
            clat[0] = (elat[0] + elat[1]) / 2.
            clat[-1] = -clat[0]
        else:
            clat += (elat[1] - elat[0]) / 2.

        return {
            "lon_centers": clon, "lat_centers": clat,
            "lon_edges": elon, "lat_edges": elat
        }


def get_grid_spec(model_name):
    """
    Pass-through to look-up the grid specifications for a given GEOS-Chem
    configuration.

    Parameters
    ----------
    model_name : str
        Name of the model; variations in naming format are permissible, e.g.
        "GEOS5" can be requested as "GEOS-5" or "GEOS_5".
    resolution : tuple of floats
        Longitude x latitude resolution of the model.

    Returns
    -------
    grid_spec : dict
        Critical grid information as items in a dictionary.

    """
    return _get_model_info(model_name)
