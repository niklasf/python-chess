Polyglot opening book reading
=============================

.. autofunction:: chess.polyglot.open_reader

.. autoclass:: chess.polyglot.Entry

    .. py:attribute:: key
        :type: int

        The Zobrist hash of the position.

    .. py:attribute:: raw_move
        :type: int

        The raw binary representation of the move. Use
        :data:`~chess.polyglot.Entry.move` instead.

    .. py:attribute:: weight
        :type: int

        An integer value that can be used as the weight for this entry.

    .. py:attribute:: learn
        :type: int

        Another integer value that can be used for extra information.

    .. py:attribute:: move
        :type: chess.Move

        The :class:`~chess.Move`.

.. autoclass:: chess.polyglot.MemoryMappedReader
    :members:

.. py:data:: chess.polyglot.POLYGLOT_RANDOM_ARRAY
    :value: [0x9D39247E33776D41, ..., 0xF8D626AAAF278509]

    Array of 781 polyglot compatible pseudo random values for Zobrist hashing.

.. autofunction:: chess.polyglot.zobrist_hash
