# xbpch: xarray interface for bpch files

**xpbch** is a simple utility for reading the proprietary [binary punch format (bpch) outputs](http://wiki.seas.harvard.edu/geos-chem/index.php/GEOS-Chem_Output_Files#Binary_Punch_File_Format) used in versions of GEOS-Chem earlier than v11-02. The utility allows a user to load this data into an [xarray]/[dask]-powered workflow without necessarily pre-processing the data using [GAMAP] or IDL.

This package is maintained as part of a broader, community effort to tackle [big data problems in geoscience](https://pangeo-data.github.io/).

[dask]: http://dask.pydata.org/
[xarray]: http://xarray.pydata.org/
[GAMAP]: http://acmg.seas.harvard.edu/gamap/

## Acknowledgments

This utility packages together a few pre-existing but toolkits which have been floating around the Python-GEOS-Chem community. In particular, I would like to acknowledge the following pieces of software which I have build this utility around:

- [PyGChem](https://github.com/benbovy/PyGChem) by [Benoit Bovy](https://github.com/benbovy)
- [gchem](https://github.com/gkuhl/gchem) by [Gerrit Kuhlmann](https://github.com/gkuhl)

## License

Copyright (c) 2017 Daniel Rothenberg

This work is [licensed](LICENSE) under a permissive MIT License. I acknowledge important contributions from Benoît Bovy, Gerrit Kuhlmann, and Christoph Keller).

## Contact

[Daniel Rothenberg](http://github.com/darothen) - darothen@mit.edu