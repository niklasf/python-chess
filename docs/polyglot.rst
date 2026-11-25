Polyglot opening books
======================

.. autofunction:: chess.polyglot.open_reader

.. autoclass:: chess.polyglot.Entry
    :members:


.. autoclass:: chess.polyglot.MemoryMappedReader
    :members:

.. autofunction:: chess.polyglot.make_entry

.. autofunction:: chess.polyglot.write_book

.. py:data:: chess.polyglot.POLYGLOT_RANDOM_ARRAY
    :value: [0x9D39247E33776D41, ..., 0xF8D626AAAF278509]

    Array of 781 polyglot compatible pseudo random values for Zobrist hashing.

.. autofunction:: chess.polyglot.zobrist_hash
