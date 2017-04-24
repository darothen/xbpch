"""
Utilities for reading unformatted Fortran binary files

Reproduced from PyGChem

Copyright (C) 2012-2014 Gerrit Kuhlmann, Benoît Bovy
see https://github.com/benbovy/PyGChem/blob/master/LICENSE.txt for more details

"""

from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from builtins import *
from builtins import zip
from builtins import str
from past.builtins import basestring
from past.utils import old_div
import struct
import io


_FIX_ERROR = ("Pre- and suffix of line do not match. This can happen, if the"
              " `endian` is incorrect.")


class FortranFile(io.FileIO):
    """
    A class for reading and writing unformatted binary Fortran files.

    Parameters
    ----------
    filename : string
        filename
    mode : {'rb', 'wb'}
        mode of the file: 'rb' (reading binary, default) or 'wb'
        (writing binary).
    endian : {'@', '<', '>'}
        byte order, size and alignment of the data in the file.
        '@' native, '<' little-endian, and '>' big-endian (default).

    Notes
    -----
    Fortran writes data as "lines" when using the PRINT or WRITE statements.
    Each line consists of:
        - a prefix (4 byte integer gives the size of the data)
        - the real data
        - a suffix (same as prefix).

    This class can be used to read and write these "lines", in a similar
    way as reading "real lines" in a text file. A format can be given,
    while reading or writing to pack or unpack data into a binary
    format, using the 'struct' module from the Python standard library.

    See Documentation of Python's struct module for details on endians and
    format strings: https://docs.python.org/library/struct.html
    """

    def __init__(self, filename, mode='rb', endian='>'):
        self.endian = endian
        super(FortranFile, self).__init__(filename, mode)

    def _fix(self, fmt='i'):
        """
        Read pre- or suffix of line at current position with given
        format `fmt` (default 'i').
        """
        fmt = self.endian + fmt
        fix = self.read(struct.calcsize(fmt))
        if fix:
            return struct.unpack(fmt, fix)[0]
        else:
            raise EOFError

    def readline(self, fmt=None):
        """
        Return next unformatted "line". If format is given, unpack content,
        otherwise return byte string.
        """
        prefix_size = self._fix()

        if fmt is None:
            content = self.read(prefix_size)
        else:
            fmt = self.endian + fmt
            fmt = _replace_star(fmt, prefix_size)
            content = struct.unpack(fmt, self.read(prefix_size))

        try:
            suffix_size = self._fix()
        except EOFError:
            # when endian is invalid and prefix_size > total file size
            suffix_size = -1

        if prefix_size != suffix_size:
            raise IOError(_FIX_ERROR)

        return content

    def readlines(self):
        """
        Return list strings, each a line from the file.
        """
        return [line for line in self]

    def skipline(self):
        """
        Skip the next line and returns position and size of line.
        Raises IOError if pre- and suffix of line do not match.
        """
        position = self.tell()
        prefix = self._fix()
        self.seek(prefix, 1)  # skip content
        suffix = self._fix()

        if prefix != suffix:
            raise IOError(_FIX_ERROR)

        return position, prefix

    def writeline(self, fmt, *args):
        """
        Write `line` (list of objects) with given `fmt` to file. The
        `line` will be chained if object is iterable (except for
        basestrings).
        """
        fmt = self.endian + fmt
        size = struct.calcsize(fmt)

        fix = struct.pack(self.endian + 'i', size)
        line = struct.pack(fmt, *args)

        self.write(fix)
        self.write(line)
        self.write(fix)

    def writelines(self, lines, fmt):
        """
        Write `lines` with given `format`.
        """
        if isinstance(fmt, basestring):
            fmt = [fmt] * len(lines)
        for f, line in zip(fmt, lines):
            self.writeline(f, line, self.endian)

    def __iter__(self):
        return self

    def next(self, fmt=None):
        try:
            return self.readline(fmt)
        except EOFError:
            raise StopIteration


def _replace_star(fmt, size):
    """
    Replace the `*` placeholder in a format string (fmt), so that
    struct.calcsize(fmt) is equal to the given `size` using the format
    following the placeholder.

    Raises `ValueError` if number of `*` is larger than 1. If no `*`
    in `fmt`, returns `fmt` without checking its size!

    Examples
    --------
    >>> _replace_star('ii*fi', 40)
    'ii7fi'
    """
    n_stars = fmt.count('*')

    if n_stars > 1:
        raise ValueError("More than one `*` in format (%s)." % fmt)

    if n_stars:
        i = fmt.find('*')
        s = struct.calcsize(fmt.replace(fmt[i:i + 2], ''))
        n = old_div((size - s), struct.calcsize(fmt[i + 1]))

        fmt = fmt.replace('*', str(n))

    return fmt
