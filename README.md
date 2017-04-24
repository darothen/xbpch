# xbpch: xarray interface for bpch files

**xpbch** is a simple utility for reading the proprietary [binary punch format (bpch) outputs](http://wiki.seas.harvard.edu/geos-chem/index.php/GEOS-Chem_Output_Files#Binary_Punch_File_Format) used in versions of GEOS-Chem earlier than v11-02. The utility allows a user to load this data into an [xarray]/[dask]-powered workflow without necessarily pre-processing the data using [GAMAP] or IDL.

This package is maintained as part of a broader, community effort to tackle [big data problems in geoscience](https://pangeo-data.github.io/).

[dask]: http://dask.pydata.org/
[xarray]: http://xarray.pydata.org/
[GAMAP]: http://acmg.seas.harvard.edu/gamap/

## Installation

### Requirements

**xbpch** is only intended for use with Python 3, although with some modifications it  would likely work with Python 2.7 ([Pull Requests are welcome!](https://github.com/darothen/xbpch/pulls)). As the package description implies, it requires up-to-date copies of [xarray] (>= version 0.9) and [dask] (>= version 0.14). The best way to install these packages is by using the [conda](http://conda.pydata.org/docs/) package management system, or the [Anaconda Python distribution](https://www.continuum.io/downloads).

 To install the dependencies for **xbpch** using conda, execute from a terminal:

  ``` shell
  $ conda install xarray dask
  ```

 In the future, **xbpch** will be available on both pip and and conda, but for now it must be installed directly from source. To do this, you can either clone the source directory and install:

 ``` shell
 $ git clone https://github.com/darothen/xbpch.git
 $ cd xbpch
 $ python setup.py install
 ```

or, you can install via pip directly from git:

``` shell
$ pip install git+https://github.com/darothen/xbpch.git
```

## Quick Start

If you're already familiar with loading and manipulating data with [xarray], then it's easy to dive right into **xbpch**. Navigate to a directory on disk which contains your `.bpch` output, as well as `tracerinfo.dat` and `diaginfo.dat`, and execute from a Python interpter:

``` python
>>> from xbpch import open_bpchdataset
>>> fn = "my_geos_chem_output.bpch"
>>> ds = open_bpchdataset(fn)
```

After a few seconds (depending on your hard-drive speed) you should be able to interact with `ds` just as you would any *xarray.Dataset* object.

## Caveats and Future Notes

**xbpch** should be most simple workflows, especially if you need a quick-and-dirty way to ingest legacy GEOS-Chem output. It is **not** tested against the majority of output grids, including data for the Hg model or nested models. Grid information (at least for the vertical) is hard-coded and may not be accurate for the most recent versions of GEOS-Chem.

Most importantly, **xbpch** does not yet solve the problem of manually scanning bpch files before producing a dataset on disk. Because the bpch format does not encode metadata about *what its contents actually are*, we must manually process this from any output file we wish to load. For the time being, we do **not** short-circuit this process because we cannot necessarily predict file position offsets in the bpch files we read. In the future, I hope to come up with an elegant solution for solving this problem.

## Acknowledgments

This utility packages together a few pre-existing but toolkits which have been floating around the Python-GEOS-Chem community. In particular, I would like to acknowledge the following pieces of software which I have build this utility around:

- [PyGChem](https://github.com/benbovy/PyGChem) by [Benoit Bovy](https://github.com/benbovy)
- [gchem](https://github.com/gkuhl/gchem) by [Gerrit Kuhlmann](https://github.com/gkuhl)

## License

Copyright (c) 2017 Daniel Rothenberg

This work is [licensed](LICENSE) under a permissive MIT License. I acknowledge important contributions from Benoît Bovy, Gerrit Kuhlmann, and Christoph Keller).

## Contact

[Daniel Rothenberg](http://github.com/darothen) - darothen@mit.edu