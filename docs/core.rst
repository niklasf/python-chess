Core
====

Colors
------

Constants for the side to move or the color of a piece.

.. py:data:: chess.WHITE
    :annotation: = 0

.. py:data:: chess.BLACK
    :annotation: = 1

You can get the opposite color using `color ^ 1`.

Piece types
-----------

.. py:data:: chess.NONE
    :annotation: = 0

.. py:data:: chess.PAWN
.. py:data:: chess.KNIGHT
.. py:data:: chess.BISHOP
.. py:data:: chess.ROOK
.. py:data:: chess.QUEEN
.. py:data:: chess.KING

Castling rights
---------------

The castling flags

.. py:data:: chess.CASTLING_NONE
    :annotation: = 0
.. py:data:: chess.CASTLING_WHITE_KINGSIDE
.. py:data:: chess.CASTLING_BLACK_KINGSIDE
.. py:data:: chess.CASTLING_WHITE_QUEENSIDE
.. py:data:: chess.CASTLING_BLACK_QUEENSIDE

can be combined bitwise.

.. py:data:: chess.CASTLING_WHITE
    :annotation: = CASTLING_WHITE_QUEENSIDE | CASTLING_WHITE_KINGSIDE
.. py:data:: chess.CASTLING_BLACK
    :annotation: = CASTLING_BLACK_QUEENSIDE | CASTLING_BLACK_KINGSIDE
.. py:data:: chess.CASTLING
    :annotation: = CASTLING_WHITE | CASTLING_BLACK

Squares
-------

.. py:data:: chess.A1
    :annotation: = 0
.. py:data:: chess.B1
    :annotation: = 1

and so on to

.. py:data:: chess.H8
    :annotation: = 63

.. py:data:: chess.SQUARES
    :annotation: = [A1, B1, ..., G8, H8]

.. py:data:: chess.SQUARE_NAMES
    :annotation: = ['a1', 'b1', ..., 'g8', 'h8']

.. autofunction:: chess.file_index

.. py:data:: chess.FILE_NAMES
    :annotation: = ['a', 'b', ..., 'g', 'h']

.. autofunction:: chess.rank_index

Pieces
------

.. autoclass:: chess.Piece
    :members:

    .. py:attribute:: piece_type

        The piece type.

    .. py:attribute:: color

        The piece color.

Moves
-----

.. autoclass:: chess.Move
    :members:

    .. py:attribute:: from_square

        The source square.

    .. py:attribute:: to_square

        The target square.

    .. py:attribute:: promotion

        The promotion piece type.


Bitboard
--------

.. autodata:: chess.STARTING_FEN

.. autoclass:: chess.Bitboard
    :members:

    .. py:attribute:: turn

        The side to move.

    .. py:attribute:: castling_rights

        Bitmask of castling rights.

    .. py:attribute:: ep_square

        The potential en-passant square on the third or sixth rank or `0`. It
        does not matter if en-passant would actually be possible on the next
        move.

    .. py:attribute:: fullmove_number

        Counts move pairs. Starts at `1` and is incremented after every move
        of the black side.

    .. py:attribute:: halfmove_clock

        The number of half moves since the last capture or pawn move.

    .. py:attribute:: pseudo_legal_moves
        :annotation: = PseudoLegalMoveGenerator(self)

        A dynamic list of pseudo legal moves.

        Pseudo legal moves might leave or put the king in check, but are
        otherwise valid. Null moves are not pseudo legal. Castling moves are
        only included if they are completely legal.

        For performance moves are generated on the fly and only when nescessary.
        The following operations do not just generate everything but map to
        more efficient methods.

        >>> len(board.pseudo_legal_moves)
        20

        >>> bool(board.pseudo_legal_moves)
        True

        >>> move in board.pseudo_legal_moves
        True

    .. py:attribute:: legal_moves
        :annotation: = LegalMoveGenerator(self)

        A dynamic list of completely legal moves, much like the pseudo legal
        move list.
