xbpch: xarray interface for bpch files
======================================

**xpbch** is a simple utility for reading the proprietary
`binary punch format (bpch) outputs <http://wiki.seas.harvard.edu/geos-chem/index.php/GEOS-Chem_Output_Files#Binary_Punch_File_Format)>` used in versions
of GEOS-Chem_ earlier than v11-02. The utility allows a user to load this
data into an xarray_- and dask_-powered workflow without necessarily
pre-processing the data using GAMAP_ or IDL.

This package is maintained as part of a broader, community effort to
tackle `big data problems in geoscience <https://pangeo-data.github.io/)>`.


Installation
------------

Requirements
^^^^^^^^^^^^

**xbpch** is only intended for use with Python 3, although with some
modifications it  would likely work with Python 2.7 (`Pull Requests are
welcome! <https://github.com/darothen/xbpch/pulls>`). As the package
description implies, it requires up-to-date copies of xarray_
(>= version 0.9) and [dask] (>= version 0.14). The best way to install
these packages is by using the conda_ package management system, or
the `Anaconda Python distribution <https://www.continuum.io/downloads>`.

To install the dependencies for **xbpch** using conda, execute from a
terminal:

    $ conda install xarray dask

In the future, **xbpch** will be available on both pip and and conda,
but for now it must be installed directly from source. To do this, you
can either clone the source directory and install:

    $ git clone https://github.com/darothen/xbpch.git
    $ cd xbpch
    $ python setup.py install

or, you can install via pip directly from git:

    $ pip install git+https://github.com/darothen/xbpch.git

Quick Start
-----------

If you're already familiar with loading and manipulating data with
xarray_, then it's easy to dive right into **xbpch**. Navigate to a
directory on disk which contains your ``.bpch`` output, as well as
``tracerinfo.dat`` and ``diaginfo.dat``, and execute from a Python
interpeter:

:: code-block:: python

    from xbpch import open_bpchdataset
    fn = "my_geos_chem_output.bpch"
    ds = open_bpchdataset(fn)

After a few seconds (depending on your hard-drive speed) you should be
able to interact with ``ds`` just as you would any *xarray.Dataset*
object.

Caveats and Future Notes
------------------------

**xbpch** should work for most simple workflows, especially if you need
a quick-and-dirty way to ingest legacy GEOS-Chem_ output. It is **not**
tested against the majority of output grids, including data for the Hg
model or nested models. Grid information (at least for the vertical) is
hard-coded and may not be accurate for the most recent versions of
GEOS-Chem_.

Most importantly, **xbpch** does not yet solve the problem of manually
scanning bpch files before producing a dataset on disk. Because the bpch
format does not encode metadata about *what its contents actually are*,
we must manually process this from any output file we wish to load. For
the time being, we do **not** short-circuit this process because we
cannot necessarily predict file position offsets in the bpch files we
read. In the future, I hope to come up with an elegant solution for
solving this problem.

Acknowledgments
---------------

This utility packages together a few pre-existing but toolkits which
have been floating around the Python-GEOS-Chem community. In particular,
I would like to acknowledge the following pieces of software which I have
built this utility around:

- `PyGChem <https://github.com/benbovy/PyGChem>` by
  `Benoit Bovy <https://github.com/benbovy>`
- `gchem <https://github.com/gkuhl/gchem>` by
  `Gerrit Kuhlmann <https://github.com/gkuhl>`

License
-------

Copyright (c) 2017 `Daniel Rothenberg`_

This work is licensed_ under a permissive MIT License. I acknowledge
important contributions from Benoît Bovy, Gerrit Kuhlmann, and Christoph
Keller in the form of prior work which helped create the foundation for
this package.

Contact
-------

`Daniel Rothenberg`_ - darothen@mit.edu

.. _`Daniel Rothenberg`: http://github.com/darothen
.. _conda: http://conda.pydata.org/docs/
.. _dask: http://dask.pydata.org/
.. _GAMAP: http://acmg.seas.harvard.edu/gamap/
.. _licensed: LICENSE
.. _GEOS-Chem: http://www.geos-chem.org
.. _xarray: http://xarray.pydata.org/