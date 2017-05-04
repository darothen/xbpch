.. _quick start:

Quick Start
===========

Assuming you're already familiar with xarray_, it's easy to dive right in to
begin reading bpch data. If you don't have any GEOS-Chem_ data handy to test
with, I've archived
`a sample dataset here <https://figshare.com/articles/Sample_ND49_Dataset/4905755>`_
here consisting of 14 days of hourly, ND49 output - good for diagnosing
surface air quality statistics.

Download the data and extract it to some directory::

    $ wget https://ndownloader.figshare.com/files/8251094
    $ tar -xvzf sample_nd49.tar.gz

You should now see 14 ``bpch`` files in your directory, and two ``.dat`` files.

The whole point of **xbpch** is to read these data files natively into an
`xarray.Dataset <http://xarray.pydata.org/en/stable/data-structures.html#dataset>`_.
You can do this with the :py:func:`xbpch.open_bpchdataset` method:

.. ipython:: python
    :verbatim:

    import xbpch
    fn = "ND49_20060102_ref_e2006_m2010.bpch"
    ds = xbpch.open_bpchdataset(fn)

If we print the dataset back out, we'll get a familiar representation:

.. parsed-literal::

    <xarray.Dataset>
    Dimensions:          (lat: 91, lev: 47, lon: 144, nv: 2, time: 24)
    Coordinates:
      * lev              (lev) float64 0.9925 0.9775 0.9624 0.9473 0.9322 0.9171 ...
      * lon              (lon) float64 -180.0 -177.5 -175.0 -172.5 -170.0 -167.5 ...
      * lat              (lat) float64 -89.5 -88.0 -86.0 -84.0 -82.0 -80.0 -78.0 ...
      * time             (time) datetime64[ns] 2006-01-01T01:00:00 ...
      * nv               (nv) int64 0 1
    Data variables:
        IJ_AVG_S_NO      (time, lon, lat) float32 1.16601e-12 1.1599e-12 ...
        time_bnds        (time, nv) datetime64[ns] 2006-01-01T01:00:00 ...
        IJ_AVG_S_O3      (time, lon, lat) float32 9.25816e-09 9.25042e-09 ...
        IJ_AVG_S_SO4     (time, lon, lat) float32 1.41706e-10 1.4142e-10 ...
        IJ_AVG_S_NH4     (time, lon, lat) float32 1.16908e-11 1.16658e-11 ...
        IJ_AVG_S_NIT     (time, lon, lat) float32 9.99837e-31 9.99897e-31 ...
        IJ_AVG_S_BCPI    (time, lon, lat) float32 2.46206e-12 2.45698e-12 ...
        IJ_AVG_S_OCPI    (time, lon, lat) float32 2.65303e-11 2.6476e-11 ...
        IJ_AVG_S_BCPO    (time, lon, lat) float32 4.19881e-19 4.18213e-19 ...
        IJ_AVG_S_OCPO    (time, lon, lat) float32 2.49109e-22 2.53752e-22 ...
        IJ_AVG_S_DST1    (time, lon, lat) float32 7.11484e-12 7.10209e-12 ...
        IJ_AVG_S_DST2    (time, lon, lat) float32 1.55181e-11 1.54779e-11 ...
        IJ_AVG_S_SALA    (time, lon, lat) float32 3.70387e-11 3.69923e-11 ...
        OD_MAP_S_AOD     (time, lon, lat) float32 0.292372 0.325568 0.358368 ...
        OD_MAP_S_DSTAOD  (time, lon, lat) float32 0.0 0.0 0.0 0.0 0.0 0.0 0.0 ...
    Attributes:
        modelname:    GEOS5_47L
        halfpolar:    1
        res:          (2.5, 2.0)
        center180:    1
        tracerinfo:   tracerinfo.dat
        diaginfo:     diaginfo.dat
        filetitle:    b'GEOS-CHEM DIAG49 instantaneous timeseries'
        source:       ND49_20060101_ref_e2006_m2010.bpch
        filetype:     b'CTM bin 02'
        Conventions:  CF1.6

You can then proceed to process the data using the conventional routines
you'd use in any xarray_-powered workflow.

In the sample dataset highlighted here, the 14 days of hourly output are
split across 14 files - one for each day's worth of data. **xbpch**
provides a second method, :py:func:`xbpch.open_mfbpchdataset`, for reading in
multiple-file datasets like these, and automatically concatenating them
on the *time* record dimension:

.. ipython:: python
    :verbatim:

    import xbpch

    from glob import glob

    # List all the bpch files in the current directory
    fns = glob("ND49_*.bpch")
    
    # Helper function to extract spatial mean O3 from each file
    def _preprocess(ds):
        return ds[['IJ_AVG_S_O3', ]].mean(['lon', 'lat'])
        
    ds = xbpch.open_mfbpchdataset(
        fns, preprocess=_preprocess, dask=True, memmap=True
    )

Again, printing yields the expected results:

.. parsed-literal::

    <xarray.Dataset>
    Dimensions:      (time: 336)
    Coordinates:
      * time         (time) datetime64[ns] 2006-01-01T01:00:00 ...
    Data variables:
        IJ_AVG_S_O3  (time) float32 2.5524e-08 2.55541e-08 2.55588e-08 ...

Finally, if you don't want to drop into a Python interpreter but just want
to quickly convert your binary data to NetCDF, you can run the utility
script `bpch_to_nc` which is shipped with this library::

    $ bpch_to_nc /path/to/my/data.bpch /path/to/my/output.nc

    Reading in file(s)...

    Decoding variables...

    Writing to /path/to/my/output.nc ...
    syncing
    [####################################] | 100% Completed | 52.1s

.. _GEOS-Chem: http://www.geos-chem.org
.. _dask: http://dask.pydata.org
.. _xarray: http://xarray.pydata.org
