"""
Specification of various grid models used by GEOS-Chem (GEOS, MERRA, etc...).

`MODELS` defines the default grid set-up (dict) for several models:
    - Model names (keys) should be uppercase.
    - A model can inherit grid specifications from another model, using the
      key 'reference' (useful for model groups, similar models or
      multiple model names).
    - A model consists a family of models if the value
      of 'reference' is set to None (e.g., 'GEOS').
    - When a key is redefined (i.e., present in both a model and its inherited
      model), it overrides the specification of the inherited model.

It is more appropriate to get model names and grid specifications using
:func:`_get_supported_models` and :func:`_get_model_info`.

`CSIG_`, `ESIG_`, `Ap_` and `Bp_` can be used to compute the vertical grid
levels for the specified models.

This implementation is based on Benoit Bovy's PyGChem code, and uses his
hand-curated grid level definitions as a starting point. See PyGChem/license.txt
for more details on the provenance of this code.

"""

import re
import itertools

import numpy as np

# pre-defined sigma coordinates
CSIG_GEOS1 = np.array([
    0.993936, 0.971301, 0.929925, 0.874137, 0.807833,
    0.734480, 0.657114, 0.578390, 0.500500, 0.424750,
    0.352000, 0.283750, 0.222750, 0.172150, 0.132200,
    0.100050, 0.073000, 0.049750, 0.029000, 0.009500
])

ESIG_GEOS1 = np.array([
    1.000000, 0.987871, 0.954730, 0.905120, 0.843153,
    0.772512, 0.696448, 0.617779, 0.539000, 0.462000,
    0.387500, 0.316500, 0.251000, 0.194500, 0.149800,
    0.114600, 0.085500, 0.060500, 0.039000, 0.019000,
    0.000000
])

CSIG_GEOS_STRAT = np.array([
    0.993935, 0.971300, 0.929925, 0.875060, 0.812500,
    0.745000, 0.674500, 0.604500, 0.536500, 0.471500,
    0.410000, 0.352500, 0.301500, 0.257977, 0.220273,
    0.187044, 0.157881, 0.132807, 0.111722, 0.094035,
    0.079233, 0.066873, 0.056574, 0.044794, 0.028825,
    0.009979
])

ESIG_GEOS_STRAT = np.array([
    1.000000, 0.987871, 0.954730, 0.905120, 0.845000,
    0.780000, 0.710000, 0.639000, 0.570000, 0.503000,
    0.440000, 0.380000, 0.325000, 0.278000, 0.237954,
    0.202593, 0.171495, 0.144267, 0.121347, 0.102098,
    0.085972, 0.072493, 0.061252, 0.051896, 0.037692,
    0.019958, 0.000000
])

CSIG_GEOS_STRAT_46L = np.array([
    0.993935, 0.971300, 0.929925, 0.875060, 0.812500,
    0.745000, 0.674500, 0.604500, 0.536500, 0.471500,
    0.410000, 0.352500, 0.301500, 0.257977, 0.220273,
    0.187044, 0.157881, 0.132807, 0.111722, 0.094035,
    0.079233, 0.066873, 0.056574, 0.048012, 0.040910,
    0.034927, 0.029792, 0.025395, 0.021663, 0.018439,
    0.015571, 0.013036, 0.010808, 0.008864, 0.007181,
    0.005737, 0.004510, 0.003480, 0.002625, 0.001928,
    0.001369, 0.000929, 0.000593, 0.000344, 0.000167,
    0.000047
])

ESIG_GEOS_STRAT_46L = np.array([
    1.000000, 0.987871, 0.954730, 0.905120, 0.845000,
    0.780000, 0.710000, 0.639000, 0.570000, 0.503000,
    0.440000, 0.380000, 0.325000, 0.278000, 0.237954,
    0.202593, 0.171495, 0.144267, 0.121347, 0.102098,
    0.085972, 0.072493, 0.061252, 0.051896, 0.044128,
    0.037692, 0.032162, 0.027422, 0.023367, 0.019958,
    0.016919, 0.014223, 0.011848, 0.009767, 0.007960,
    0.006402, 0.005072, 0.003948, 0.003011, 0.002240,
    0.001616, 0.001121, 0.000737, 0.000449, 0.000239,
    0.000094, 0.000000
])

CSIG_GEOS2 = np.array([
    9.985475e-01, 9.942475e-01, 9.871500e-01, 9.772000e-01,
    9.642500e-01, 9.481150e-01, 9.285650e-01, 9.053219e-01,
    8.781569e-01, 8.469350e-01, 8.116350e-01, 7.724569e-01,
    7.299198e-01, 6.847475e-01, 6.377244e-01, 5.896341e-01,
    5.412270e-01, 4.932176e-01, 4.462150e-01, 4.007400e-01,
    3.572600e-01, 3.161750e-01, 2.779150e-01, 2.429000e-01,
    2.114000e-01, 1.834250e-01, 1.587150e-01, 1.369425e-01,
    1.178165e-01, 1.010651e-01, 8.644427e-02, 7.372377e-02,
    6.269240e-02, 5.314686e-02, 4.489815e-02, 3.779315e-02,
    3.171021e-02, 2.329529e-02, 1.512403e-02, 9.817761e-03,
    6.371968e-03, 4.134332e-03, 2.681253e-03, 1.737650e-03,
    1.124892e-03, 7.269780e-04, 6.706442e-05
])

ESIG_GEOS2 = np.array([
    1.000000e+00, 9.970951e-01, 9.914000e-01, 9.829000e-01,
    9.715000e-01, 9.570000e-01, 9.392300e-01, 9.179000e-01,
    8.927438e-01, 8.635700e-01, 8.303000e-01, 7.929700e-01,
    7.519437e-01, 7.078959e-01, 6.615992e-01, 6.138495e-01,
    5.654188e-01, 5.170351e-01, 4.694000e-01, 4.230300e-01,
    3.784500e-01, 3.360700e-01, 2.962800e-01, 2.595500e-01,
    2.262500e-01, 1.965500e-01, 1.703000e-01, 1.471300e-01,
    1.267550e-01, 1.088781e-01, 9.325208e-02, 7.963646e-02,
    6.781108e-02, 5.757372e-02, 4.872000e-02, 4.107631e-02,
    3.451000e-02, 2.891042e-02, 1.877039e-02, 1.218564e-02,
    7.909625e-03, 5.132859e-03, 3.329678e-03, 2.158725e-03,
    1.398330e-03, 9.045439e-04, 5.838880e-04, 0.000000e+00
])

CSIG_GEOS2_70L = np.array([
    0.998548, 0.994248, 0.987150, 0.977200, 0.964250,
    0.948115, 0.928565, 0.905322, 0.878157, 0.846935,
    0.811635, 0.772457, 0.729920, 0.684748, 0.637724,
    0.589634, 0.541227, 0.493218, 0.446215, 0.400740,
    0.357260, 0.316175, 0.277915, 0.242900, 0.211400,
    0.183425, 0.158715, 0.136943, 0.117817, 0.101065,
    0.086444, 0.073724, 0.062692, 0.053147, 0.044898,
    0.037793, 0.031710, 0.026527, 0.022123, 0.018394,
    0.015247, 0.012600, 0.010381, 0.008526, 0.006982,
    0.005699, 0.004638, 0.003763, 0.003043, 0.002453,
    0.001971, 0.001579, 0.001261, 0.001003, 0.000795,
    0.000628, 0.000494, 0.000386, 0.000300, 0.000232,
    0.000179, 0.000136, 0.000103, 0.000077, 0.000057,
    0.000041, 0.000028, 0.000018, 0.000010, 0.000003
])

ESIG_GEOS2_70L = np.array([
    1.000000, 0.997095, 0.991400, 0.982900, 0.971500,
    0.957000, 0.939230, 0.917900, 0.892744, 0.863570,
    0.830300, 0.792970, 0.751944, 0.707896, 0.661599,
    0.613850, 0.565419, 0.517035, 0.469400, 0.423030,
    0.378450, 0.336070, 0.296280, 0.259550, 0.226250,
    0.196550, 0.170300, 0.147130, 0.126755, 0.108878,
    0.093252, 0.079636, 0.067811, 0.057574, 0.048720,
    0.041076, 0.034510, 0.028910, 0.024144, 0.020102,
    0.016686, 0.013808, 0.011392, 0.009370, 0.007683,
    0.006280, 0.005118, 0.004158, 0.003367, 0.002719,
    0.002188, 0.001755, 0.001403, 0.001118, 0.000888,
    0.000702, 0.000553, 0.000434, 0.000338, 0.000262,
    0.000202, 0.000155, 0.000118, 0.000089, 0.000066,
    0.000048, 0.000034, 0.000023, 0.000014, 0.000006,
    0.000000
])

CSIG_GEOS3 = np.array([
    0.998548,    0.994148,    0.986350,    0.974300,
    0.956950,    0.933150,    0.901750,    0.861500,
    0.811000,    0.750600,    0.682900,    0.610850,
    0.537050,    0.463900,    0.393650,    0.328275,
    0.269500,    0.218295,    0.174820,    0.138840,
    0.109790,    0.0866900,   0.0684150,   0.0539800,
    0.0425750,   0.0335700,   0.0264650,   0.0208550,
    0.0164300,   0.0129425,   0.0101900,   0.00800750,
    0.00627000,  0.00489000,  0.00379000,  0.00291500,
    0.00221500,  0.00167000,  0.00125000,  0.000912500,
    0.000652500, 0.000455000, 0.00030750,  0.000200000,
    0.000123500, 6.97500e-05, 3.25900e-05, 8.84000e-06
])

ESIG_GEOS3 = np.array([
    1.000000,    0.997095,    0.991200,    0.981500,
    0.967100,    0.946800,    0.919500,    0.884000,
    0.839000,    0.783000,    0.718200,    0.647600,
    0.574100,    0.500000,    0.427800,    0.359500,
    0.297050,    0.241950,    0.194640,    0.155000,
    0.122680,    0.0969000,   0.0764800,   0.0603500,
    0.0476100,   0.0375400,   0.0296000,   0.0233300,
    0.0183800,   0.0144800,   0.0114050,   0.00897500,
    0.00704000,  0.00550000,  0.00428000,  0.00330000,
    0.00253000,  0.00190000,  0.00144000,  0.00106000,
    0.000765000, 0.000540000, 0.000370000, 0.000245000,
    0.000155000, 9.20000e-05, 4.75000e-05, 1.76800e-05,
    0.00000
])

CSIG_GEOS3_30L = np.array([
    0.998548,    0.994148,    0.986350,    0.974300,
    0.956950,    0.933150,    0.901750,    0.861500,
    0.811000,    0.750600,    0.682900,    0.610850,
    0.537050,    0.463900,    0.393650,    0.328275,
    0.269500,    0.218295,    0.174820,    0.138840,
    0.109790,    0.0866900,   0.0620450,   0.0386050,
    0.0239900,   0.0127100,   0.00478500,  0.00164750,
    0.000460000, 7.75000e-05
])

ESIG_GEOS3_30L = np.array([
    1.000000,    0.997095,    0.991200,    0.981500,
    0.967100,    0.946800,    0.919500,    0.884000,
    0.839000,    0.783000,    0.718200,    0.647600,
    0.574100,    0.500000,    0.427800,    0.359500,
    0.297050,    0.241950,    0.194640,    0.155000,
    0.122680,    0.0969000,   0.0764800,   0.0476100,
    0.0296000,   0.0183800,   0.00704000,  0.00253000,
    0.000765000, 0.000155000, 0.00000
])

# pre-defined parameter values for computing ETA vertical levels:
# A [hPa] ; B [unitless]
Ap_GEOS4 = np.array([
    0.000000,      0.000000,      12.704939,     35.465965,
    66.098427,     101.671654,    138.744400,    173.403183,
    198.737839,    215.417526,    223.884689,    224.362869,
    216.864929,    201.192093,    176.929993,    150.393005,
    127.837006,    108.663429,    92.365662,     78.512299,
    66.603378,     56.387939,     47.643932,     40.175419,
    33.809956,     28.367815,     23.730362,     19.791553,
    16.457071,     13.643393,     11.276889,     9.292943,
    7.619839,      6.216800,      5.046805,      4.076567,
    3.276433,      2.620212,      2.084972,      1.650792,
    1.300508,      1.019442,      0.795134,      0.616779,
    0.475806,      0.365041,      0.278526,      0.211349,
    0.159495,      0.119703,      0.089345,      0.066000,
    0.047585,      0.032700,      0.020000,      0.010000
])

Bp_GEOS4 = np.array([
    1.000000,      0.985110,      0.943290,      0.867830,
    0.764920,      0.642710,      0.510460,      0.378440,
    0.270330,      0.183300,      0.115030,      0.063720,
    0.028010,      0.006960,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000
])

Ap_GEOS4_REDUCED = np.array([
    0.000000,      0.000000,      12.704939,     35.465965,
    66.098427,     101.671654,    138.744400,    173.403183,
    198.737839,    215.417526,    223.884689,    224.362869,
    216.864929,    201.192093,    176.929993,    150.393005,
    127.837006,    108.663429,    92.365662,     78.512299,
    56.387939,     40.175419,     28.367815,     19.791553,
    9.292943,      4.076567,      1.650792,      0.616779,
    0.211349,      0.066000,      0.010000])

Bp_GEOS4_REDUCED = np.array([
    1.000000,      0.985110,      0.943290,      0.867830,
    0.764920,      0.642710,      0.510460,      0.378440,
    0.270330,      0.183300,      0.115030,      0.063720,
    0.028010,      0.006960,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000,      0.000000,
    0.000000,      0.000000,      0.000000
])

Ap_GEOS5 = np.array([
    0.00000000e+00,   4.80482600e-02,   6.59375200e+00,
    1.31348000e+01,   1.96131100e+01,   2.60920100e+01,
    3.25708100e+01,   3.89820100e+01,   4.53390100e+01,
    5.16961100e+01,   5.80532100e+01,   6.43626400e+01,
    7.06219800e+01,   7.88342200e+01,   8.90999200e+01,
    9.93652100e+01,   1.09181700e+02,   1.18958600e+02,
    1.28695900e+02,   1.42910000e+02,   1.56260000e+02,
    1.69609000e+02,   1.81619000e+02,   1.93097000e+02,
    2.03259000e+02,   2.12150000e+02,   2.18776000e+02,
    2.23898000e+02,   2.24363000e+02,   2.16865000e+02,
    2.01192000e+02,   1.76930000e+02,   1.50393000e+02,
    1.27837000e+02,   1.08663000e+02,   9.23657200e+01,
    7.85123100e+01,   6.66034100e+01,   5.63879100e+01,
    4.76439100e+01,   4.01754100e+01,   3.38100100e+01,
    2.83678100e+01,   2.37304100e+01,   1.97916000e+01,
    1.64571000e+01,   1.36434000e+01,   1.12769000e+01,
    9.29294200e+00,   7.61984200e+00,   6.21680100e+00,
    5.04680100e+00,   4.07657100e+00,   3.27643100e+00,
    2.62021100e+00,   2.08497000e+00,   1.65079000e+00,
    1.30051000e+00,   1.01944000e+00,   7.95134100e-01,
    6.16779100e-01,   4.75806100e-01,   3.65041100e-01,
    2.78526100e-01,   2.11349000e-01,   1.59495000e-01,
    1.19703000e-01,   8.93450200e-02,   6.60000100e-02,
    4.75850100e-02,   3.27000000e-02,   2.00000000e-02,
    1.00000000e-02
])

Bp_GEOS5 = np.array([
    1.00000000e+00,   9.84952000e-01,   9.63406000e-01,
    9.41865000e-01,   9.20387000e-01,   8.98908000e-01,
    8.77429000e-01,   8.56018000e-01,   8.34660900e-01,
    8.13303900e-01,   7.91946900e-01,   7.70637500e-01,
    7.49378200e-01,   7.21166000e-01,   6.85899900e-01,
    6.50634900e-01,   6.15818400e-01,   5.81041500e-01,
    5.46304200e-01,   4.94590200e-01,   4.43740200e-01,
    3.92891100e-01,   3.43381100e-01,   2.94403100e-01,
    2.46741100e-01,   2.00350100e-01,   1.56224100e-01,
    1.13602100e-01,   6.37200600e-02,   2.80100400e-02,
    6.96002500e-03,   8.17541300e-09,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00
])

Ap_GEOS5_REDUCED = np.array([
    0.00000000e+00,   4.80482600e-02,   6.59375200e+00,
    1.31348000e+01,   1.96131100e+01,   2.60920100e+01,
    3.25708100e+01,   3.89820100e+01,   4.53390100e+01,
    5.16961100e+01,   5.80532100e+01,   6.43626400e+01,
    7.06219800e+01,   7.88342200e+01,   8.90999200e+01,
    9.93652100e+01,   1.09181700e+02,   1.18958600e+02,
    1.28695900e+02,   1.42910000e+02,   1.56260000e+02,
    1.69609000e+02,   1.81619000e+02,   1.93097000e+02,
    2.03259000e+02,   2.12150000e+02,   2.18776000e+02,
    2.23898000e+02,   2.24363000e+02,   2.16865000e+02,
    2.01192000e+02,   1.76930000e+02,   1.50393000e+02,
    1.27837000e+02,   1.08663000e+02,   9.23657200e+01,
    7.85123100e+01,   5.63879100e+01,   4.01754100e+01,
    2.83678100e+01,   1.97916000e+01,   9.29294200e+00,
    4.07657100e+00,   1.65079000e+00,   6.16779100e-01,
    2.11349000e-01,   6.60000100e-02,   1.00000000e-02
])

Bp_GEOS5_REDUCED = np.array([
    1.00000000e+00,   9.84952000e-01,   9.63406000e-01,
    9.41865000e-01,   9.20387000e-01,   8.98908000e-01,
    8.77429000e-01,   8.56018000e-01,   8.34660900e-01,
    8.13303900e-01,   7.91946900e-01,   7.70637500e-01,
    7.49378200e-01,   7.21166000e-01,   6.85899900e-01,
    6.50634900e-01,   6.15818400e-01,   5.81041500e-01,
    5.46304200e-01,   4.94590200e-01,   4.43740200e-01,
    3.92891100e-01,   3.43381100e-01,   2.94403100e-01,
    2.46741100e-01,   2.00350100e-01,   1.56224100e-01,
    1.13602100e-01,   6.37200600e-02,   2.80100400e-02,
    6.96002500e-03,   8.17541300e-09,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00,
    0.00000000e+00,   0.00000000e+00,   0.00000000e+00
])


MODELS = {
    'GEOS': {'reference': None,
             'description': 'GEOS model family',
             'resolution': (5, 4),
             'Ptop': 1e-2,
             'halfpolar': True,
             'center180': True},
    'GENERIC': {'reference': None,
                'description': 'GENERIC grids',
                'resolution': (1, 1),
                'Nlayers': None,
                'Ntrop': None,
                'Ptop': 1e-2,
                'halfpolar': False,
                'center180': False,
                'hybrid': False},
    'GEOS1': {'reference': 'GEOS',
              'description': 'GEOS-1 pure sigma',
              'Nlayers': 20,
              'Ntrop': 16,
              'hybrid': False,
              'csig': CSIG_GEOS1,
              'esig': ESIG_GEOS1},
    'GEOS_STRAT': {'reference': 'GEOS',
                   'description': 'GEOS-STRAT pure sigma vertically'
                                  ' regridded',
                   'Nlayers': 26,
                   'Ntrop': 19,
                   'Ptop': 1e-4,
                   'hybrid': False,
                   'csig': CSIG_GEOS_STRAT,
                   'esig': ESIG_GEOS_STRAT},
    'GEOS_STRAT_46L': {'reference': 'GEOS_STRAT',
                       'description': 'GEOS-STRAT pure sigma'
                                      ' original resolution',
                       'Nlayers': 46,
                       'csig': CSIG_GEOS_STRAT_46L,
                       'esig': ESIG_GEOS_STRAT_46L},
    'GEOS2': {'reference': 'GEOS',
              'description': 'GEOS-2 pure sigma',
              'Nlayers': 47,
              'Ntrop': 32,
              'hybrid': False,
              'csig': CSIG_GEOS2,
              'esig': ESIG_GEOS2},
    'GEOS2_70L': {'reference': 'GEOS2',
                  'description': 'GEOS-2 pure sigma'
                                 ' original resolution',
                  'Nlayers': 70,
                  'csig': CSIG_GEOS2_70L,
                  'esig': ESIG_GEOS2_70L},
    'GEOS3': {'reference': 'GEOS',
              'description': 'GEOS-3 pure sigma',
              'Nlayers': 48,
              'Ntrop': 20,
              'hybrid': False,
              'csig': CSIG_GEOS3,
              'esig': ESIG_GEOS3},
    'GEOS3_30L': {'reference': 'GEOS3',
                  'description': 'GEOS-3 pure sigma reduced',
                  'Nlayers': 30,
                  'csig': CSIG_GEOS3_30L,
                  'esig': ESIG_GEOS3_30L},
    'GEOS3_REDUCED': {'reference': 'GEOS3_30L'},
    'GEOS4': {'reference': 'GEOS',
              'description': 'GEOS-4 hybrid',
              'Nlayers': 55,
              'Ntrop': 17,
              'hybrid': True,
              'Ap': Ap_GEOS4,
              'Bp': Bp_GEOS4},
    'FVDAS': {'reference': 'GEOS4'},
    'GEOS4_30L': {'reference': 'GEOS4',
                  'description': 'GEOS-4 hybrid reduced',
                  'Nlayers': 30,
                  'Ap': Ap_GEOS4_REDUCED,
                  'Bp': Bp_GEOS4_REDUCED},
    'GEOS4_REDUCED': {'reference': 'GEOS4_30L'},
    'GEOS5': {'reference': 'GEOS',
              'description': 'GEOS-5.2.0 hybrid',
              'Nlayers': 72,
              'Ntrop': 38,
              'hybrid': True,
              'Ap': Ap_GEOS5,
              'Bp': Bp_GEOS5},
    'GEOS5_NATIVE': {'reference': 'GEOS5'},
    'GEOS5_47L': {'reference': 'GEOS5',
                  'description': 'GEOS-5.2.0 hybrid reduced',
                  'Nlayers': 47,
                  'Ap': Ap_GEOS5_REDUCED,
                  'Bp': Bp_GEOS5_REDUCED},
    'GEOS5_REDUCED': {'reference': 'GEOS5_47L'},
    'GEOS57': {'reference': 'GEOS5',
               'description': 'GEOS-5.7.x hybrid'},
    'GEOS57_NATIVE': {'reference': 'GEOS57'},
    'GEOS57_47L': {'reference': 'GEOS5_47L',
                   'description': 'GEOS-5.7.x hybrid reduced'},
    'GEOS57_REDUCED': {'reference': 'GEOS57_47L'},
    'GEOSFP': {'reference': 'GEOS57',
               'description': 'GEOS-5.11.x (FP) hybrid'},
    'GEOSFP_NATIVE': {'reference': 'GEOSFP'},
    'GEOSFP_47L': {'reference': 'GEOS57_47L',
                   'description': 'GEOS-5.11.x (FP) hybrid reduced'},
    'GEOSFP_REDUCED': {'reference': 'GEOSFP_47L'},
    'MERRA': {'reference': 'GEOS5',
              'description': 'MERRA hybrid'},
    'MERRA_NATIVE': {'reference': 'MERRA'},
    'MERRA_47L': {'reference': 'GEOS5_47L',
                  'description': 'MERRA hybrid reduced'},
    'MERRA_REDUCED': {'reference': 'MERRA_47L'},
    'MERRA2': {'reference': 'GEOSFP',
              'description': 'MERRA2 hybrid'},
    'MERRA2_47L': {'reference': 'GEOS5_47L'},
}


def prof_altitude(pressure, p_coef=(-0.028389, -0.0493698, 0.485718, 0.278656,
                                    -17.5703, 48.0926)):
    """
    Return altitude for given pressure.

    This function evaluates a polynomial at log10(pressure) values.

    Parameters
    ----------
    pressure : array-like
        pressure values [hPa].
    p_coef : array-like
        coefficients of the polynomial (default values are for the US
        Standard Atmosphere).

    Returns
    -------
    altitude : array-like
        altitude values [km] (same shape than the pressure input array).

    See Also
    --------
    prof_pressure : Returns pressure for
        given altitude.
    prof_temperature : Returns air temperature for
        given altitude.

    Notes
    -----
    Default coefficient values represent a 5th degree polynomial which had
    been fitted to USSA data from 0-100 km. Accuracy is on the order of 1% for
    0-100 km and 0.5% below 30 km. This function, with default values, may thus
    produce bad results with pressure less than about 3e-4 hPa.

    Examples
    --------
    >>> prof_altitude([1000, 800, 600])
    array([ 0.1065092 ,  1.95627858,  4.2060627 ])

    """
    pressure = np.asarray(pressure)
    altitude = np.polyval(p_coef, np.log10(pressure.flatten()))
    return altitude.reshape(pressure.shape)


def prof_pressure(altitude, z_coef=(1.94170e-9, -5.14580e-7, 4.57018e-5,
                                    -1.55620e-3, -4.61994e-2, 2.99955)):
    """
    Return pressure for given altitude.

    This function evaluates a polynomial at altitudes values.

    Parameters
    ----------
    altitude : array-like
        altitude values [km].
    z_coef : array-like
        coefficients of the polynomial (default values are for the US
        Standard Atmosphere).

    Returns
    -------
    pressure : array-like
        pressure values [hPa] (same shape than the altitude input array).

    See Also
    --------
    prof_altitude : Returns altitude for
        given pressure.
    prof_temperature : Returns air temperature for
        given altitude.

    Notes
    -----
    Default coefficient values represent a 5th degree polynomial which had
    been fitted to USA data from 0-100 km. Accuracy is on the order of 1% for
    0-100 km and 0.5% below 30 km. This function, with default values, may thus
    produce bad results with altitude > 100 km.

    Examples
    --------
    >>> prof_pressure([0, 10, 20])
    array([ 998.96437334,  264.658697  ,   55.28114631])

    """
    altitude = np.asarray(altitude)
    pressure = np.power(10, np.polyval(z_coef, altitude.flatten()))
    return pressure.reshape(altitude.shape)


def _get_supported_models():
    """
    Returns a tuple of the names of the models for which grid specifications
    are available.
    """
    return tuple(MODELS.keys())


def _find_references(model_name, references=None):
    """
    Iterate over model references for `model_name`
    and return a list of parent model specifications (including those of
    `model_name`, ordered from parent to child).
    """
    references = references or []
    references.append(model_name)

    ref = MODELS[model_name].get('reference')
    if ref is not None:
        _find_references(ref, references)

    parent_models = [m for m in references]
    parent_models.reverse()

    return parent_models


def _get_model_info(model_name):
    """
    Get the grid specifications for a given model.

    Parameters
    ----------
    model_name : string
        Name of the model. Supports multiple formats
        (e.g., 'GEOS5', 'GEOS-5' or 'GEOS_5').

    Returns
    -------
    specifications : dict
        Grid specifications as a dictionary.

    Raises
    ------
    ValueError
        If the model is not supported (see `models`) or if the given
        `model_name` corresponds to several entries in the list of
        supported models.

    """
    # trying to get as much as possible a valid model name from the given
    # `model_name`, using regular expressions.
    split_name = re.split(r'[\-_\s]', model_name.strip().upper())
    sep_chars = ('', ' ', '-', '_')
    gen_seps = itertools.combinations_with_replacement(
        sep_chars, len(split_name) - 1
    )
    test_names = ("".join((n for n in itertools.chain(*list(zip(split_name,
                                                           s + ('',))))))
                  for s in gen_seps)
    match_names = list([name for name in test_names if name
                        in _get_supported_models()])

    if not len(match_names):
        raise ValueError("Model '{0}' is not supported".format(model_name))
    elif len(match_names) > 1:
        raise ValueError("Multiple matched models for given model name '{0}'"
                         .format(model_name))

    valid_model_name = match_names[0]
    parent_models = _find_references(valid_model_name)

    model_spec = dict()
    for m in parent_models:
        model_spec.update(MODELS[m])
    model_spec.pop('reference')
    model_spec['model_family'] = parent_models[0]
    model_spec['model_name'] = valid_model_name

    return model_spec
