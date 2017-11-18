Core
====

Colors
------

Constants for the side to move or the color of a piece.

.. py:data:: chess.WHITE
    :annotation: = True

.. py:data:: chess.BLACK
    :annotation: = False

You can get the opposite color using `not color`.

Piece types
-----------

.. py:data:: chess.PAWN
    :annotation: = 1
.. py:data:: chess.KNIGHT
    :annotation: = 2
.. py:data:: chess.BISHOP
    :annotation: = 3
.. py:data:: chess.ROOK
    :annotation: = 4
.. py:data:: chess.QUEEN
    :annotation: = 5
.. py:data:: chess.KING
    :annotation: = 6

Squares
-------

.. py:data:: chess.A1
    :annotation: = 0
.. py:data:: chess.B1
    :annotation: = 1

and so on to

.. py:data:: chess.G8
    :annotation: = 62
.. py:data:: chess.H8
    :annotation: = 63

.. py:data:: chess.SQUARES
    :annotation: = [chess.A1, chess.B1, ..., chess.G8, chess.H8]

.. py:data:: chess.SQUARE_NAMES
    :annotation: = ['a1', 'b1', ..., 'g8', 'h8']

.. py:data:: chess.FILE_NAMES
    :annotation: = ['a', 'b', ..., 'g', 'h']

.. py:data:: chess.RANK_NAMES
    :annotation: = ['1', '2', ..., '7', '8']

.. autofunction:: chess.square

.. autofunction:: chess.square_file

.. autofunction:: chess.square_rank

.. autofunction:: chess.square_distance

.. autofunction:: chess.square_mirror

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

        The promotion piece type or ``Ǹone``.

    .. py:attribute:: drop

        The drop piece type or ``None``.

Board
-----

.. autodata:: chess.STARTING_FEN

.. autodata:: chess.STARTING_BOARD_FEN

.. autoclass:: chess.Board
    :members:

    .. py:attribute:: turn

        The side to move.

    .. py:attribute:: castling_rights

        Bitmask of the rooks with castling rights.

        To test for specific squares:

        >>> import chess
        >>>
        >>> board = chess.Board()
        >>> bool(board.castling_rights & chess.BB_H1) # White can castle with the h1 rook
        True

        To add a specific square:

        >>> board.castling_rights |= chess.BB_A1

        Use :func:`~chess.Board.set_castling_fen()` to set multiple castling
        rights. Also see :func:`~chess.Board.has_castling_rights()`,
        :func:`~chess.Board.has_kingside_castling_rights()`,
        :func:`~chess.Board.has_queenside_castling_rights()`,
        :func:`~chess.Board.has_chess960_castling_rights()`,
        :func:`~chess.Board.clean_castling_rights()`.

    .. py:attribute:: ep_square

        The potential en passant square on the third or sixth rank or ``None``.

        Use :func:`~chess.Board.has_legal_en_passant()` to test if en passant
        capturing would actually be possible on the next move.

    .. py:attribute:: fullmove_number

        Counts move pairs. Starts at `1` and is incremented after every move
        of the black side.

    .. py:attribute:: halfmove_clock

        The number of half-moves since the last capture or pawn move.

    .. py:attribute:: promoted

        A bitmask of pieces that have been promoted.

    .. py:attribute:: chess960

        Whether the board is in Chess960 mode. In Chess960 castling moves are
        represented as king moves to the corresponding rook square.

    .. py:attribute:: legal_moves
        :annotation: = LegalMoveGenerator(self)

        A dynamic list of legal moves.

        >>> import chess
        >>>
        >>> board = chess.Board()
        >>> board.legal_moves.count()
        20
        >>> bool(board.legal_moves)
        True
        >>> move = chess.Move.from_uci("g1f3")
        >>> move in board.legal_moves
        True

        Wraps :func:`~chess.Board.generate_legal_moves()` and
        :func:`~chess.Board.is_legal()`.

    .. py:attribute:: pseudo_legal_moves
        :annotation: = PseudoLegalMoveGenerator(self)

        A dynamic list of pseudo legal moves, much like the legal move list.

        Pseudo legal moves might leave or put the king in check, but are
        otherwise valid. Null moves are not pseudo legal. Castling moves are
        only included if they are completely legal.

        Wraps :func:`~chess.Board.generate_pseudo_legal_moves()` and
        :func:`~chess.Board.is_pseudo_legal()`.

    .. py:attribute:: move_stack

        The move stack. Use :func:`Board.push() <chess.Board.push()>`,
        :func:`Board.pop() <chess.Board.pop()>`,
        :func:`Board.peek() <chess.Board.peek()>` and
        :func:`Board.clear_stack() <chess.Board.clear_stack()>` for
        manipulation.

.. autoclass:: chess.BaseBoard
    :members:

Square sets
-----------

.. autoclass:: chess.SquareSet
    :members:

Common integer masks are:

.. py:data:: chess.BB_VOID
    :annotation: = 0
.. py:data:: chess.BB_ALL
    :annotation: = 0xFFFFFFFFFFFFFFFF

Single squares:

.. py:data:: chess.BB_SQUARES
    :annotation: = [chess.BB_A1, chess.BB_B1, ..., chess.BB_G8, chess.BB_H8]

Ranks and files:

.. py:data:: chess.BB_RANKS
    :annotation: = [chess.BB_RANK_1, ..., chess.BB_RANK_8]


.. py:data:: chess.BB_FILES
    :annotation: = [chess.BB_FILE_A, ..., chess.BB_FILE_H]

Other masks:

.. py:data:: chess.BB_LIGHT_SQUARES
    :annotation: = 0x55AA55AA55AA55AA
.. py:data:: chess.BB_DARK_SQUARES
    :annotation: = 0xAA55AA55AA55AA55

.. py:data:: chess.BB_BACKRANKS
    :annotation: = chess.BB_RANK_1 | chess.BB_RANK_8

.. py:data:: chess.BB_CORNERS
    :annotation: = chess.BB_A1 | chess.BB_H1 | chess.BB_A8 | chess.BB_H8
