#!/usr/bin/env python

import os
import warnings

from setuptools import setup, find_packages

from textwrap import dedent

MAJOR = 0
MINOR = 3
MICRO = 3
VERSION = "{}.{}.{}".format(MAJOR, MINOR, MICRO)
DEV = False

# Correct versioning with git info if DEV
if DEV:
    import subprocess

    pipe = subprocess.Popen(
        ['git', "describe", "--always", "--match", "v[0-9]*"],
        stdout=subprocess.PIPE)
    so, err = pipe.communicate()

    if pipe.returncode != 0:
        # no git or something wrong with git (not in dir?)
        warnings.warn("WARNING: Couldn't identify git revision, using generic version string")
        VERSION += ".dev"
    else:
        git_rev = so.strip()
        git_rev = git_rev.decode('ascii') # necessary for Python >= 3

        VERSION += ".dev-{}".format(git_rev)

DESCRIPTION = "xarray interface for bpch files"
LONG_DESCRIPTION = """\
**xpbch** is a simple utility for reading the proprietary binary punch format
(bpch) outputs used in versions of GEOS-Chem earlier than v11-02. The utility
allows a user to load this data into an xarray/dask-powered workflow without
necessarily pre-processing the data using GAMAP or IDL.
"""

DISTNAME = "xbpch"
AUTHOR = "Daniel Rothenberg"
AUTHOR_EMAIL = "darothen@mit.edu"
URL = "https://github.com/darothen/xbpch"
LICENSE = "MIT"
DOWNLOAD_URL = ("https://github.com/darothen/xbpch/archive/v{}.tar.gz"
                .format(VERSION))

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Scientific/Engineering',
]

def _write_version_file():

    fn = os.path.join(os.path.dirname(__file__), DISTNAME, 'version.py')

    version_str = dedent("""
        __version__ = '{}'
        """)

    # Write version file
    with open(fn, 'w') as version_file:
        version_file.write(version_str.format(VERSION))

# Write version and install
_write_version_file()

setup(
    name = DISTNAME,
    author = AUTHOR,
    author_email = AUTHOR_EMAIL,
    maintainer = AUTHOR,
    maintainer_email = AUTHOR_EMAIL,
    description = DESCRIPTION,
    long_description = LONG_DESCRIPTION,
    license = LICENSE,
    url = URL,
    version = VERSION,
    download_url = DOWNLOAD_URL,

    packages = find_packages(),
    package_data = {},
    scripts = [
        'scripts/bpch_to_nc',
    ],

    classifiers = CLASSIFIERS
)
