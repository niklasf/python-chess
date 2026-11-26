CTG opening book reading
========================

Reads CTG opening books of standard chess or Chess960. A book consists of
``.ctg``, ``.cto`` and ``.ctb`` files next to each other, with ``-960``
after each extension for Chess960.

Books store promotions as queen promotions. Chess960 books contain no
castling moves, and no book contains moves of a fourth queen, rook, bishop or
knight.

.. autofunction:: chess.ctg.open_reader

.. autoclass:: chess.ctg.Entry
    :members:

.. autoclass:: chess.ctg.MemoryMappedReader
    :members:
