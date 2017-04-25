
Reading BPCH Files
==================

**xbpch** provides three main utilities for reading bpch files, all of which
are provided as top-level package imports. For most purposes, you should use
``open_bpchdataset()``, however a lower-level interface, ``BPCHFile()`` is also
provided in case you would prefer manually processing the bpch contents.

See :doc:`/usage` for more details.

.. automodule:: xbpch.core
    :members: open_bpchdataset, open_mfbpchdataset

.. autoclass:: xbpch.bpch.BPCHFile
    :members:
    :private-members:
    :special-members: