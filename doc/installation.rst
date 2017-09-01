
Installation
============

Requirements
------------

**xbpch** is written in pure Python (version >= 3.5), and leans on two important
libraries:

1. xarray_ (version >= 0.9): a pandas-like toolkit for working with
labeled, *n*-dimensional data

2. dask_ (version >= 0.14): a library for performing out-of-core,
parallel computations on both tabular and array-like datasets

The easiest way to install these libraries is to use the conda_
package manager::

    $ conda install -c conda-forge xarray dask

conda_ can be obtained as part of the Anaconda_ Python distribution
from Continuum IO, although you do not need all of the packages it
provides in order to use **xbpch**. Note that we recommend installing the latest
versions from community-maintained `conda-forge <https://conda-forge.org/>`_
collection, since these usually contain bug-fixes and additional features.

.. note::

    Basic support for Python 2.7 is available in **xbpch** but it has not been
    tested, since the evolutionary GCPy package will only support Python 3. If,
    for some reason, you must use Python 2.7 and encounter problems, please
    reach out to us and we may be able to fix them.


Installation via conda
----------------------

The preferred way to install **xbpch** is also via conda_::

    $ conda install -c conda-forge xbpch


Installation via pip
--------------------

**xbpch** is available on `PyPI <https://pypi.python.org/pypi/xbpch/>`_, and
can be installed using setuptools::

    $ pip install xbpch

Installation from source
------------------------

If you're developing or contributing to **xbpch**, you may wish
instead to install directly from a local copy of the source code. To do so,
you must first clone the the master repository (or a fork) and install locally
via pip::

    $ git clone https://github.com/darothen/xbpch.git
    $ cd xbpch
    $ python setup.py install

You will need to substitute in the path to your preferred repository/mirror
of the source code.

Note that you can also install directly from the source using setuptools::

    $ pip install git+https://github.com/darothen/xbpch.git

.. _Anaconda: https://www.continuum.io/downloads
.. _conda: http://conda.pydata.org
.. _dask: http://dask.pydata.org
.. _xarray: http://xarray.pydata.org