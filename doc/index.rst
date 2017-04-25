
xbpch
=====

|rtd|

**xpbch** is a simple utility for reading the proprietary
`binary punch format (bpch) outputs <http://wiki.seas.harvard.edu/geos-chem/index.php/GEOS-Chem_Output_Files#Binary_Punch_File_Format>`_
used in versions of GEOS-Chem_ earlier than v11-02. The utility
allows a user to load this data into an xarray_- and
dask_-powered workflow without necessarily pre-processing the
data using GAMAP or IDL. This opens the door to out-of-core
and parallel processing of GEOS-Chem_ output.

.. toctree::
    :maxdepth: 2

    installation
    quick_start

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

.. |rtd| image:: https://readthedocs.org/projects/xbpch/badge/?version=latest
   :target: http://xbpch.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status