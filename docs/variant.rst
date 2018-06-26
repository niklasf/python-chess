Variants
========

python-chess supports several chess variants.

>>> import chess.variant
>>>
>>> board = chess.variant.GiveawayBoard()

>>> # General information about the variants
>>> type(board).uci_variant
'giveaway'
>>> type(board).starting_fen
'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1'

See :func:`chess.Board.is_variant_end()`, :func:`~chess.Board.is_variant_win()`
:func:`~chess.Board.is_variant_draw()` :func:`~chess.Board.is_variant_loss()`
for special variant end conditions and results.

================ ========================================= ============= ============
Variant          Board class                               UCI           Syzygy
================ ========================================= ============= ============
Standard         :class:`chess.Board`                      chess         .rtbw, .rtbz
Suicide          :class:`chess.variant.SuicideBoard`       suicide       .stbw, .stbz
Giveaway         :class:`chess.variant.GiveawayBoard`      giveaway      .gtbw, .gtbz
Atomic           :class:`chess.variant.AtomicBoard`        atomic        .atbw, .atbz
King of the Hill :class:`chess.variant.KingOfTheHillBoard` kingofthehill
Racing Kings     :class:`chess.variant.RacingKingsBoard`   racingkings
Horde            :class:`chess.variant.HordeBoard`         horde
Three-check      :class:`chess.variant.ThreeCheckBoard`    3check
Crazyhouse       :class:`chess.variant.CrazyhouseBoard`    crazyhouse
================ ========================================= ============= ============

.. autofunction:: chess.variant.find_variant

Chess960
--------

Chess960 is orthogonal to all other variants.

>>> chess.Board(chess960=True)
Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', chess960=True)

See :func:`chess.BaseBoard.set_chess960_pos()`,
:func:`~chess.BaseBoard.chess960_pos()`, and
:func:`~chess.BaseBoard.from_chess960_pos()` for dealing with Chess960 starting
positions.

UCI
---

`Multi-Variant Stockfish`_ and other engines have an ``UCI_Variant`` option.
This is automatically managed.

>>> import chess.uci
>>> import chess.variant
>>>
>>> engine = chess.uci.popen_engine("stockfish")
>>> engine.uci()
>>>
>>> board = chess.variant.RacingKingsBoard()
>>> engine.position(board)

Syzygy
------

Syzygy tablebases are available for suicide, giveaway and atomic chess.

>>> import chess.syzygy
>>> import chess.variant
>>>
>>> tables = chess.syzygy.open_tablebase("data/syzygy", VariantBoard=chess.variant.AtomicBoard)


.. _Multi-Variant Stockfish: https://github.com/ddugovic/Stockfish
