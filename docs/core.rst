Core
====

Colors
------

Constants for the side to move or the color of a piece.

.. py:data:: chess.WHITE
    :type: chess.Color
    :value: True

.. py:data:: chess.BLACK
    :type: chess.Color
    :value: False

You can get the opposite *color* using ``not color``.

Piece types
-----------

.. py:data:: chess.PAWN
    :type: chess.PieceType
    :value: 1
.. py:data:: chess.KNIGHT
    :type: chess.PieceType
    :value: 2
.. py:data:: chess.BISHOP
    :type: chess.PieceType
    :value: 3
.. py:data:: chess.ROOK
    :type: chess.PieceType
    :value: 4
.. py:data:: chess.QUEEN
    :type: chess.PieceType
    :value: 5
.. py:data:: chess.KING
    :type: chess.PieceType
    :value: 6

.. autofunction:: chess.piece_symbol

.. autofunction:: chess.piece_name

Squares
-------

.. py:data:: chess.A1
    :type: chess.Square
    :value: 0
.. py:data:: chess.B1
    :type: chess.Square
    :value: 1

and so on to

.. py:data:: chess.G8
    :type: chess.Square
    :value: 62
.. py:data:: chess.H8
    :type: chess.Square
    :value: 63

.. py:data:: chess.SQUARES
    :value: [chess.A1, chess.B1, ..., chess.G8, chess.H8]

.. py:data:: chess.SQUARE_NAMES
    :value: ['a1', 'b1', ..., 'g8', 'h8']

.. py:data:: chess.FILE_NAMES
    :value: ['a', 'b', ..., 'g', 'h']

.. py:data:: chess.RANK_NAMES
    :value: ['1', '2', ..., '7', '8']

.. autofunction:: chess.parse_square

.. autofunction:: chess.square_name

.. autofunction:: chess.square

.. autofunction:: chess.square_file

.. autofunction:: chess.square_rank

.. autofunction:: chess.square_distance

.. autofunction:: chess.square_manhattan_distance

.. autofunction:: chess.square_knight_distance

.. autofunction:: chess.square_mirror

Pieces
------

.. autoclass:: chess.Piece
    :members:

Moves
-----

.. autoclass:: chess.Move
    :members:

Board
-----

.. autodata:: chess.STARTING_FEN

.. autodata:: chess.STARTING_BOARD_FEN

.. autoclass:: chess.Board
    :members:
    :exclude-members: set_piece_at, remove_piece_at, reset_board, set_board_fen, set_piece_map, set_chess960_pos, apply_transform

.. autoclass:: chess.BaseBoard
    :members:

Outcome
-------

.. autoclass:: chess.Outcome
    :members:

.. autoclass:: chess.Termination
    :members:

Square sets
-----------

.. autoclass:: chess.SquareSet
    :members:

Common integer masks are:

.. py:data:: chess.BB_EMPTY
    :type: chess.Bitboard
    :value: 0
.. py:data:: chess.BB_ALL
    :type: chess.Bitboard
    :value: 0xFFFF_FFFF_FFFF_FFFF

Single squares:

.. py:data:: chess.BB_SQUARES
    :value: [chess.BB_A1, chess.BB_B1, ..., chess.BB_G8, chess.BB_H8]

Ranks and files:

.. py:data:: chess.BB_RANKS
    :value: [chess.BB_RANK_1, ..., chess.BB_RANK_8]


.. py:data:: chess.BB_FILES
    :value: [chess.BB_FILE_A, ..., chess.BB_FILE_H]

Other masks:

.. py:data:: chess.BB_LIGHT_SQUARES
    :type: chess.Bitboard
    :value: 0x55AA_55AA_55AA_55AA
.. py:data:: chess.BB_DARK_SQUARES
    :type: chess.Bitboard
    :value: 0xAA55_AA55_AA55_AA55

.. py:data:: chess.BB_BACKRANKS
    :value: chess.BB_RANK_1 | chess.BB_RANK_8

.. py:data:: chess.BB_CORNERS
    :value: chess.BB_A1 | chess.BB_H1 | chess.BB_A8 | chess.BB_H8
.. py:data:: chess.BB_CENTER
    :value: chess.BB_D4 | chess.BB_E4 | chess.BB_D5 | chess.BB_E5
