xbpch: xarray interface for bpch files
======================================

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
`binary punch format (bpch) outputs <http://wiki.seas.harvard.edu/geos-chem/index.php/GEOS-Chem_Output_Files#Binary_Punch_File_Format)>`_ used in versions
of GEOS-Chem_ earlier than v11-02. The utility allows a user to load this
data into an xarray_- and dask_-powered workflow without necessarily
pre-processing the data using GAMAP_ or IDL.

This package is maintained as part of a broader, community effort to
tackle `big data problems in geoscience <https://pangeo-data.github.io/>`_.

What's the Deal?
----------------

The `contemporary scientific Python software stack <https://speakerdeck.com/jakevdp/the-state-of-the-stack-scipy-2015-keynote>`_
provides free, powerful tools for nearly all of your data processing, analysis,
and visualization needs. These tools are `well supported <https://www.numfocus.org/>`_
by a large community of heavily invested users and developers from academia,
government, and industry. They are also developed (mostly) as part of community-based,
open-source, and user-driven projects.

For nearly any application you might have in the geosciences, you can start using
this powerful, free software stack *today* with minimal friction. However,
one friction point that has tripped up adoption by GEOS-Chem users is that it
is difficult to work with legacy bpch-format diagnostics files. **xbpch**
solves this problem by providing a convenient and performant way to read
these files into a modern Python-based analysis or workflow.

Furthermore, **xbpch** is 100% future-proof. In two years, when your GEOS-Chem
simulations are writing NetCDF diagnostics, you won't need to change more than a
single line of code in any of your scripts using **xbpch**. All you'll need to do
is swap out **xbpch**'s function for reading data and instead defer to it's parent
package (xarray). It will *literally* take less than 10 keystrokes to make this
change in your code. Plus - you'll be backwards compatible with any legacy
output you need to analyze.

So give **xbpch** a try, and let me know what issues you run in to! If we solve
them once today, they'll be solved in perpetuity, which means more time for you
to do science and less time to worry about processing data.


Installation
------------

Requirements
^^^^^^^^^^^^

**xbpch** is only intended for use with Python 3, although with some
modifications it  would likely work with Python 2.7 (`Pull Requests are
welcome! <https://github.com/darothen/xbpch/pulls>`_). As the package
description implies, it requires up-to-date copies of xarray_
(>= version 0.9) and dask_ (>= version 0.14). The best way to install
these packages is by using the conda_ package management system, or
the `Anaconda Python distribution <https://www.continuum.io/downloads>`_.

To install **xbpch** and its dependencies using conda, execute from a terminal::

    $ conda install -c conda-forge xbpch xarray dask

Alternatively, you can install **xbpch** `from PyPI <https://pypi.python
.org/pypi/xbpch/>`_::

    $ pip install xbpch

You can also install **xbpch** from its source. To do this, you
can either clone the source directory and manually install::

    $ git clone https://github.com/darothen/xbpch.git
    $ cd xbpch
    $ python setup.py install

or, you can install via pip directly from git::

    $ pip install git+https://github.com/darothen/xbpch.git

Quick Start
-----------

If you're already familiar with loading and manipulating data with
xarray_, then it's easy to dive right into **xbpch**. Navigate to a
directory on disk which contains your ``.bpch`` output, as well as
``tracerinfo.dat`` and ``diaginfo.dat``, and execute from a Python
interpeter:

.. code:: python

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

This utility packages together a few pre-existing toolkits which
have been floating around the Python-GEOS-Chem community. In particular,
I would like to acknowledge the following pieces of software which I have
built this utility around:

- `PyGChem <https://github.com/benbovy/PyGChem>`_ by
  `Benoit Bovy <https://github.com/benbovy>`_
- `gchem <https://github.com/gkuhl/gchem>`_ by
  `Gerrit Kuhlmann <https://github.com/gkuhl>`_

Furthermore, the strategies used to load and process binary output on disk
through xarray_\'s ``DataStore`` API is heavily inspired by `Ryan
Abernathey's <https://github.com/rabernat>`_ package `xmitgcm
<https://github.com/rabernat/xmitgcm>`_. 

  
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


