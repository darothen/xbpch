
from collections import namedtuple
from warnings import warn

import os
import pandas as pd

from .. common import C_MOLECULAR_WEIGHT

#: Info for parsing diagnostic records
diag_rec = namedtuple("diag_rec",
                      ["name", "width", "type", "default", "read_only", "desc"])
diag_recs = [
    diag_rec('offset', 8, int, 0, True,
             "Offset (constant to add to tracer numbers in order to"
             " distinguish between diff categories, as stored in"
             " tracerinfo.dat)"),
    diag_rec("-0", 1, str, ' ', True, None),
    diag_rec('name', 40, str, None, True, "Name of the category"),
    diag_rec('description', 100, str, None, True, "Description of category"),
    diag_rec("-1", 1, str, ' ', True, None)
]

#: Info for parsing tracer records
tracer_rec = diag_rec
tracer_recs = [
    tracer_rec('name', 8, str, None, True, "Tracer name"),
    tracer_rec("-0", 1, str, ' ', True, None),
    tracer_rec('full_name', 30, str, None, True, "Full tracer name"),
    tracer_rec('molwt', 10, float, 1., True, "Molecular weight (kg/mole)"),
    tracer_rec('C', 3, int, 1, True, "# moles C/moles tracer for HCs"),
    tracer_rec('tracer', 9, int, None, True, "Tracer number"),
    tracer_rec('scale', 10, float, 1e9, True, "Standard scale factor to convert to"
                                              " given units"),
    tracer_rec("-1", 1, str, ' ', True, None),
    tracer_rec('unit', 40, str, 'ppbv', True, "Unit string"),
]

def get_diaginfo(diaginfo_file):
    """
    Read an output's diaginfo.dat file and parse into a DataFrame for
    use in selecting and parsing categories.

    Parameters
    ----------
    diaginfo_file : str
        Path to diaginfo.dat

    Returns
    -------
    DataFrame containing the category information.

    """

    widths = [rec.width for rec in diag_recs]
    col_names = [rec.name for rec in diag_recs]
    dtypes = [rec.type for rec in diag_recs]
    usecols = [name for name in col_names if not name.startswith('-')]

    diag_df = pd.read_fwf(diaginfo_file, widths=widths, names=col_names,
                          dtypes=dtypes, comment="#", header=None,
                          usecols=usecols)
    diag_desc = {diag.name: diag.desc for diag in diag_recs
                 if not diag.name.startswith('-')}

    return diag_df, diag_desc


def get_tracerinfo(tracerinfo_file):
    """
    Read an output's tracerinfo.dat file and parse into a DataFrame for
    use in selecting and parsing categories.

    Parameters
    ----------
    tracerinfo_file : str
        Path to tracerinfo.dat

    Returns
    -------
    DataFrame containing the tracer information.

    """

    widths = [rec.width for rec in tracer_recs]
    col_names = [rec.name for rec in tracer_recs]
    dtypes = [rec.type for rec in tracer_recs]
    usecols = [name for name in col_names if not name.startswith('-')]

    tracer_df = pd.read_fwf(tracerinfo_file, widths=widths, names=col_names,
                            dtypes=dtypes, comment="#", header=None,
                            usecols=usecols)

    # Check an edge case related to a bug in GEOS-Chem v12.0.3 which 
    # erroneously dropped short/long tracer names in certain tracerinfo.dat outputs.
    # What we do here is figure out which rows were erroneously processed (they'll 
    # have NaNs in them) and raise a warning if there are any
    na_free = tracer_df.dropna(subset=['tracer', 'scale'])
    only_na = tracer_df[~tracer_df.index.isin(na_free.index)]
    if len(only_na) > 0:
        warn("At least one row in {} wasn't decoded correctly; we strongly"
             " recommend you manually check that file to see that all"
             " tracers are properly recorded."
             .format(tracerinfo_file)) 

    tracer_desc = {tracer.name: tracer.desc for tracer in tracer_recs
                   if not tracer.name.startswith('-')}

    # Process some of the information about which variables are hydrocarbons
    # and chemical tracers versus other diagnostics.
    def _assign_hydrocarbon(row):
        if row['C'] != 1:
            row['hydrocarbon'] = True
            row['molwt'] = C_MOLECULAR_WEIGHT
        else:
            row['hydrocarbon'] = False
        return row

    tracer_df = (
        tracer_df
            .apply(_assign_hydrocarbon, axis=1)
            .assign(chemical=lambda x: x['molwt'].astype(bool))
    )

    return tracer_df, tracer_desc