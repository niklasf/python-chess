Core
====

Colors
------

Constants for the side to move or the color of a piece.

.. py:data:: chess.WHITE
.. py:data:: chess.BLACK

You can get the opposite color using `color ^ 1`.

Piece types
-----------

.. py:data:: chess.NONE
.. py:data:: chess.PAWN
.. py:data:: chess.KNIGHT
.. py:data:: chess.BISHOP
.. py:data:: chess.ROOK
.. py:data:: chess.QUEEN
.. py:data:: chess.KING

Castling rights
---------------

The castling flags

.. py:data:: CASTLING_NONE
.. py:data:: CASTLING_WHITE_KINGSIDE
.. py:data:: CASTLING_BLACK_KINGSIDE
.. py:data:: CASTLING_WHITE_QUEENSIDE
.. py:data:: CASTLING_BLACK_QUEENSIDE

can be combined bitwise.

.. py:data:: CASTLING_WHITE
.. py:data:: CASTLING_BLACK
.. py:data:: CASTLING

Squares
-------

.. py:data:: chess.A1

and so on to

.. py:data:: chess.H8

.. autofunction:: chess.file_index
.. autofunction:: chess.rank_index

Pieces
------

.. autoclass:: chess.Piece
    :members:

Moves
-----

.. autoclass:: chess.Move
    :members:

Bitboard
--------

.. autodata:: chess.STARTING_FEN

.. autoclass:: chess.Bitboard
    :members:
