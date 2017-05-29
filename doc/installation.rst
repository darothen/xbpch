
Installation
============

Requirements
------------

**xbpch** is written in pure Python (version >= 3.5) , and leans on two important
libraries:

1. xarray_ (version >= 0.9): a pandas-like toolkit for working with
labeled, *n*-dimensional data

2. dask_ (version >= 0.14): a library for performing out-of-core,
parallel computations on both tabular and array-like datasets

The easiest way to install these libraries is to use the conda_
package manager::

    $ conda install xarray dask

conda_ can be obtained as part of the Anaconda_ Python distribution
from Continuum IO, although you do not need all of the packages it
provides in order to use **xbpch**.


Installation via conda
----------------------

A conda_ package is not yet available for **xbpch**, but will be soon.


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