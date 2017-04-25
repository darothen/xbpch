
try:
    from . version import __version__
except:
    pass

from . bpch import BPCHFile
from . core import open_bpchdataset, open_mfbpchdataset