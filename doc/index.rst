
xbpch
=====

.. image:: https://badge.fury.io/py/xbpch.svg
    :target: https://badge.fury.io/py/xbpch
    :alt: PyPI version
.. image:: https://readthedocs.org/projects/xbpch/badge/?version=latest
    :target: http://xbpch.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
.. image:: https://zenodo.org/badge/89022822.svg
    :target: https://zenodo.org/badge/latestdoi/89022822
    :alt: Zenodo DOI

**xpbch** is a simple utility for reading the proprietary
`binary punch format (bpch) outputs <http://wiki.seas.harvard.edu/geos-chem/index.php/GEOS-Chem_Output_Files#Binary_Punch_File_Format>`_
used in versions of GEOS-Chem_ earlier than v11-02. The utility allows a user
to load this data into an xarray_- and dask_-powered workflow without
necessarily pre-processing the data using GAMAP or IDL. This opens the door
to out-of-core and parallel processing of GEOS-Chem_ output.

.. toctree::
    :maxdepth: 2

    installation
    quick_start
    usage
    reading

Recent Updates
--------------

**v0.3.2 (March 18, 2018)**

- Clean-up for xarray v0.10.2 compatibility
- Tweak to more reliably infer and unpack 3D field shape (from Jenny Fisher)


.. _dask: http://dask.pydata.org
.. _xarray: http://xarray.pydata.org
.. _GEOS-Chem: http://www.geos-chem.org

License
-------

Copyright (c) 2017 Daniel Rothenberg

This work is licensed_ under a permissive MIT License.
I acknowledge important contributions from Benoît Bovy,
Gerrit Kuhlmann, and Christoph Keller.

.. _licensed: http://github.com/darothen/xbpch/master/LICENSE
