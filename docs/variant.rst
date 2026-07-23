Variants
========

python-chess supports several chess variants.

>>> import chess.variant
>>>
>>> board = chess.variant.GiveawayBoard()

>>> # General information about the variants.
>>> type(board).uci_variant
'giveaway'
>>> type(board).xboard_variant
'giveaway'
>>> type(board).starting_fen
'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1'

================ ========================================= ============= ============
Variant          Board class                               UCI/XBoard    Syzygy
================ ========================================= ============= ============
Standard         :class:`chess.Board`                      chess/normal  .rtbw, .rtbz
Suicide          :class:`chess.variant.SuicideBoard`       suicide       .stbw, .stbz
Giveaway         :class:`chess.variant.GiveawayBoard`      giveaway      .gtbw, .gtbz
Antichess        :class:`chess.variant.AntichessBoard`     antichess     .gtbw, .gtbz
Atomic           :class:`chess.variant.AtomicBoard`        atomic        .atbw, .atbz
King of the Hill :class:`chess.variant.KingOfTheHillBoard` kingofthehill
Racing Kings     :class:`chess.variant.RacingKingsBoard`   racingkings
Horde            :class:`chess.variant.HordeBoard`         horde
Three-check      :class:`chess.variant.ThreeCheckBoard`    3check
Crazyhouse       :class:`chess.variant.CrazyhouseBoard`    crazyhouse
Duck Chess       :class:`chess.variant.DuckChessBoard`     duck
================ ========================================= ============= ============

.. autofunction:: chess.variant.find_variant

Game end
--------

See :func:`chess.Board.is_variant_end()`, :func:`~chess.Board.is_variant_win()`,
:func:`~chess.Board.is_variant_draw()`,
or :func:`~chess.Board.is_variant_loss()` for special variant end conditions
and results.

Note that if all of them return ``False``, the game may still be over and
decided by standard conditions like :func:`~chess.Board.is_checkmate()`,
:func:`~chess.Board.is_stalemate()`,
:func:`~chess.Board.is_insufficient_material()`, move counters, repetitions,
and legitimate claims.

Chess960
--------

Chess960 is orthogonal to all other variants.

>>> chess.Board(chess960=True)
Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', chess960=True)

See :func:`chess.BaseBoard.set_chess960_pos()`,
:func:`~chess.BaseBoard.chess960_pos()`, and
:func:`~chess.BaseBoard.from_chess960_pos()` for dealing with Chess960 starting
positions.

Crazyhouse
----------

.. autoclass:: chess.variant.CrazyhousePocket
    :members:

.. autoclass:: chess.variant.CrazyhouseBoard
    :members: legal_drop_squares

    .. py:attribute:: pockets
       :value: [chess.variant.CrazyhousePocket(), chess.variant.CrazyhousePocket()]

        Pockets for each color. For example, ``board.pockets[chess.WHITE]``
        are the pocket pieces available to White.

Three-check
-----------

.. autoclass:: chess.variant.ThreeCheckBoard

    .. py:attribute:: remaining_checks
       :value: [3, 3]

        Remaining checks until victory for each color. For example,
        ``board.remaining_checks[chess.WHITE] == 0`` implies that White has won.

Duck Chess
----------

A single "duck" occupies one square on the board at all times (after the
first move) and blocks movement onto or through that square for both
sides. After making a normal move, a player must also relocate the duck
before the turn passes to the opponent. There is no check, checkmate, or
draw by repetition or the fifty-move rule in this variant: a game ends
only when a king is captured.

>>> board = chess.variant.DuckChessBoard()
>>> board.push_san("e4")
>>> board.push_san("@d4")

.. autoclass:: chess.variant.DuckChessBoard
    :members: generate_duck_placements

    .. py:attribute:: duck_square
       :value: None

        The square currently occupied by the duck, or ``None`` if the duck
        has not been placed yet.

    .. py:attribute:: duck_phase
       :value: False

        ``True`` if a duck placement is currently pending, i.e. a normal
        move was just made and the same player still needs to place the
        duck before the turn passes.

UCI/XBoard
----------

`Multi-Variant Stockfish`_ and other engines have an ``UCI_Variant`` option.
XBoard engines may declare support for ``variants``.
This is automatically managed.

>>> import chess.engine
>>>
>>> engine = chess.engine.SimpleEngine.popen_uci("stockfish-mv")
>>>
>>> board = chess.variant.RacingKingsBoard()
>>> result = engine.play(board, chess.engine.Limit(time=1.0))

Syzygy
------

Syzygy tablebases are available for suicide, giveaway and atomic chess.

>>> import chess.syzygy
>>> import chess.variant
>>>
>>> tables = chess.syzygy.open_tablebase("data/syzygy", VariantBoard=chess.variant.AtomicBoard)


.. _Multi-Variant Stockfish: https://github.com/ddugovic/Stockfish
