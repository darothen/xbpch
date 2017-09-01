"""
Utility classes and tools for handling data contained in bpch files

"""

from dask import delayed
import dask.array as da
import numpy as np
import os

from xarray.core.pycompat import OrderedDict

from . uff import FortranFile
from . util import cf
from . util.diaginfo import get_diaginfo, get_tracerinfo

#: Default datatype for legacy bpch output
DEFAULT_DTYPE = 'f4'

class BPCHDataBundle(object):
    """ A single slice of a single variable inside a bpch file, and all
    of its critical accompanying metadata. """

    __slots__ = ('_shape', 'dtype', 'endian', 'filename', 'file_position',
                 'time', 'metadata', '_data', '_mmap', '_dask')

    def __init__(self, shape,  endian, filename, file_position, time,
                 metadata, data=None, dtype=None,
                 use_mmap=False, dask_delayed=False):
        self._shape = shape
        self.dtype = dtype
        self.endian = endian
        self.filename = filename
        self.file_position = file_position
        self.time = time
        self.metadata = metadata

        if dtype is None:
            self.dtype = np.dtype(self.endian + DEFAULT_DTYPE)
        else:
            self.dtype = dtype

        # Note that data is initially prescribed as None, but we keep a hook
        # here so that we can inject payloads at load time, if we want
        # (for instance, to avoid reading/memmapping through a file)
        self._data = data
        self._mmap = use_mmap
        self._dask = dask_delayed

    @property
    def shape(self):
        return self._shape

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def array(self):
        return self.data

    @property
    def data(self):
        if self._data is None:
            self._data = self._read()
        return self._data

    def _read(self):
        """ Helper function to load the data referenced by this bundle. """
        if self._dask:
            d = da.from_delayed(
                delayed(read_from_bpch, )(
                    self.filename, self.file_position, self.shape,
                    self.dtype, self.endian, use_mmap=self._mmap
                ),
                self.shape, self.dtype
            )
        else:
            d = read_from_bpch(
                    self.filename, self.file_position, self.shape,
                    self.dtype, self.endian, use_mmap=self._mmap
            )

        return d


class BPCHFile(object):
    """ A file object for representing BPCH data on disk

    Attributes
    ----------
    fp : FortranFile
        A pointer to the open unformatted Fortran binary output (the original
        bpch file)
    var_data, var_attrs : dict
        Containers of `BPCHDataBundle`s and dicts, respectively, holding
        the accessor functions to the raw bpch data and their associated
        metadata

    """

    def __init__(self, filename, mode='rb', endian='>',
                 diaginfo_file='', tracerinfo_file='', eager=False,
                 use_mmap=False, dask_delayed=False):
        """ Load a BPCHFile

        Parameters
        ----------
        filename : str
            Path to the bpch file on disk
        mode : str
            Mode string to pass to the file opener; this is currently fixed to
            "rb" and all other values will be rejected
        endian : str {">", "<", ":"}
            Endian-ness of the Fortran output file
        {tracerinfo, diaginfo}_file : str
            Path to the tracerinfo.dat and diaginfo.dat files containing
            metadata pertaining to the output in the bpch file being read.
        eager : bool
            Flag to immediately read variable data; if "False", then nothing
            will be read from the file and you'll need to do so manually
        use_mmap : bool
            Use memory-mapping to read data from file
        dask_delayed : bool
            Use dask to create delayed references to the data-reading functions
        """

        self.mode = mode
        if not mode.startswith('r'):
            raise ValueError("Currently only know how to 'r(b)'ead bpch files.")

        self.filename = filename
        self.fsize = os.path.getsize(self.filename)
        self.endian = endian

        # Open a pointer to the file
        self.fp = FortranFile(self.filename, self.mode, self.endian)

        dir_path = os.path.abspath(os.path.dirname(filename))
        if not dir_path:
            dir_path = os.getcwd()
        if not tracerinfo_file:
            tracerinfo_file = os.path.join(dir_path, "tracerinfo.dat")
            if not os.path.exists(tracerinfo_file):
                tracerinfo_file = ''
        self.tracerinfo_file = tracerinfo_file
        if not diaginfo_file:
            diaginfo_file = os.path.join(dir_path, "diaginfo.dat")
            if not os.path.exists(diaginfo_file):
                diaginfo_file = ''
        self.diaginfo_file = diaginfo_file

        # Container to record file metadata
        self._attributes = OrderedDict()

        # Don't necessarily need to save diag/tracer_dict yet
        self.diaginfo_df, _ = get_diaginfo(self.diaginfo_file)
        self.tracerinfo_df, _ = get_tracerinfo(self.tracerinfo_file)

        # Container for bundles contained in the output file.
        self.var_data = {}
        self.var_attrs = {}

        # Critical information for accessing file contents
        self._header_pos = None

        # Data loading strategy
        self.use_mmap = use_mmap
        self.dask_delayed = dask_delayed

        # Control eager versus deferring reading
        self.eager = eager
        if (mode.startswith('r') and self.eager):
            self._read()

    def close(self):
        """ Close this bpch file.

        """

        if not self.fp.closed:
            for v in list(self.var_data):
                del self.var_data[v]

            self.fp.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _read(self):
        """ Parse the entire bpch file on disk and set up easy access to meta-
        and data blocks.

        """

        self._read_metadata()
        self._read_header()
        self._read_var_data()

    def _read_metadata(self):
        """ Read the main metadata packaged within a bpch file, indicating
        the output filetype and its title.

        """

        filetype = self.fp.readline().strip()
        filetitle = self.fp.readline().strip()
        # Decode to UTF string, if possible
        try:
            filetype = str(filetype, 'utf-8')
            filetitle = str(filetitle, 'utf-8')
        except:
            # TODO: Handle this edge-case of converting file metadata more elegantly.
            pass

        self.__setattr__('filetype', filetype)
        self.__setattr__('filetitle', filetitle)

    def _read_header(self):
        """ Process the header information (data model / grid spec) """

        self._header_pos = self.fp.tell()

        line = self.fp.readline('20sffii')
        modelname, res0, res1, halfpolar, center180 = line
        self._attributes.update({
            "modelname": str(modelname, 'utf-8').strip(),
            "halfpolar": halfpolar,
            "center180": center180,
            "res": (res0, res1)
        })
        self.__setattr__('modelname', modelname)
        self.__setattr__('res', (res0, res1))
        self.__setattr__('halfpolar', halfpolar)
        self.__setattr__('center180', center180)

        # Re-wind the file
        self.fp.seek(self._header_pos)


    def _read_var_data(self):
        """ Iterate over the block of this bpch file and return handlers
        in the form of `BPCHDataBundle`s for access to the data contained
        therein.

        """

        var_bundles = OrderedDict()
        var_attrs = OrderedDict()

        n_vars = 0

        while self.fp.tell() < self.fsize:

            var_attr = OrderedDict()

            # read first and second header lines
            line = self.fp.readline('20sffii')
            modelname, res0, res1, halfpolar, center180 = line

            line = self.fp.readline('40si40sdd40s7i')
            category_name, number, unit, tau0, tau1, reserved = line[:6]
            dim0, dim1, dim2, dim3, dim4, dim5, skip = line[6:]
            var_attr['number'] = number

            # Decode byte-strings to utf-8
            category_name = str(category_name, 'utf-8')
            var_attr['category'] = category_name.strip()
            unit = str(unit, 'utf-8')

            # get additional metadata from tracerinfo / diaginfo
            try:
                cat_df = self.diaginfo_df[
                    self.diaginfo_df.name == category_name.strip()
                ]
                # TODO: Safer logic for handling case where more than one
                #       tracer metadata match was made
                # if len(cat_df > 1):
                #     raise ValueError(
                #         "More than one category matching {} found in "
                #         "diaginfo.dat".format(
                #             category_name.strip()
                #         )
                #     )
                # Safe now to select the only row in the DataFrame
                cat = cat_df.T.squeeze()

                tracer_num = int(cat.offset) + int(number)
                diag_df = self.tracerinfo_df[
                    self.tracerinfo_df.tracer == tracer_num
                ]
                # TODO: Safer logic for handling case where more than one
                #       tracer metadata match was made
                # if len(diag_df > 1):
                #     raise ValueError(
                #         "More than one tracer matching {:d} found in "
                #         "tracerinfo.dat".format(tracer_num)
                #     )
                # Safe now to select only row in the DataFrame
                diag = diag_df.T.squeeze()
                diag_attr = diag.to_dict()

                if not unit.strip():  # unit may be empty in bpch
                    unit = diag_attr['unit']  # but not in tracerinfo
                var_attr.update(diag_attr)
            except:
                diag = {'name': '', 'scale': 1}
                var_attr.update(diag)
            var_attr['unit'] = unit

            vname = diag['name']
            fullname = category_name.strip() + "_" + vname

            # parse metadata, get data or set a data proxy
            if dim2 == 1:
                data_shape = (dim0, dim1)         # 2D field
            else:
                data_shape = (dim0, dim1, dim2)
            var_attr['original_shape'] = data_shape

            # Add proxy time dimension to shape
            data_shape = tuple([1, ] + list(data_shape))
            origin = (dim3, dim4, dim5)
            var_attr['origin'] = origin

            timelo, timehi = cf.tau2time(tau0), cf.tau2time(tau1)

            pos = self.fp.tell()
            # Note that we don't pass a dtype, and assume everything is
            # single-fp floats with the correct endian, as hard-coded
            var_bundle = BPCHDataBundle(
                data_shape, self.endian, self.filename, pos, [timelo, timehi],
                metadata=var_attr,
                use_mmap=self.use_mmap, dask_delayed=self.dask_delayed
            )
            self.fp.skipline()

            # Save the data as a "bundle" for concatenating in the final step
            if fullname in var_bundles:
                var_bundles[fullname].append(var_bundle)
            else:
                var_bundles[fullname] = [var_bundle, ]
                var_attrs[fullname] = var_attr
                n_vars += 1

        self.var_data = var_bundles
        self.var_attrs = var_attrs


def read_from_bpch(filename, file_position, shape, dtype, endian,
                   use_mmap=False):
    """ Read a chunk of data from a bpch output file.

    Parameters
    ----------
    filename : str
        Path to file on disk containing the  data
    file_position : int
        Position (bytes) where desired data chunk begins
    shape : tuple of ints
        Resultant (n-dimensional) shape of requested data; the chunk
        will be read sequentially from disk and then re-shaped
    dtype : dtype
        Dtype of data; for best results, pass a dtype which includes
        an endian indicator, e.g. `dtype = np.dtype('>f4')`
    endian : str
        Endianness of data; should be consistent with `dtype`
    use_mmap : bool
        Memory map the chunk of data to the file on disk, else read
        immediately

    Returns
    -------
    Array with shape `shape` and dtype `dtype` containing the requested
    chunk of data from `filename`.

    """
    offset = file_position + 4
    if use_mmap:
        d = np.memmap(filename, dtype=dtype, mode='r', shape=shape,
                      offset=offset, order='F')
    else:
        with FortranFile(filename, 'rb', endian) as ff:
            ff.seek(file_position)
            d = np.array(ff.readline('*f'))
            d = d.reshape(shape, order='F')

    # As a sanity check, *be sure* that the resulting data block has the
    # correct shape, and fail early if it doesn't.
    if (d.shape != shape):
        raise IOError("Data chunk read from {} does not have the right shape,"
                      " (expected {} but got {})"
                      .format(filename, shape, d.shape))

    return d
