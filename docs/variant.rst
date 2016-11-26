Variant support (experimental)
==============================

================ ========================================= ============= ============
Variant          Board class                               UCI           Syzygy
================ ========================================= ============= ============
Standard         :class:`chess.Board`                      chess         .rtbw, .rtbz
Suicide          :class:`chess.variant.SuicideBoard`       suicide
Giveaway         :class:`chess.variant.GiveawayBoard`      giveaway
Atomic           :class:`chess.variant.AtomicBoard`        atomic        .atbw, .atbz
King of the Hill :class:`chess.variant.KingOfTheHillBoard` kingofthehill
================ ========================================= ============= ============

.. autofunction:: chess.variant.find_variant

>>> board = chess.variant.GiveawayBoard()
>>> type(board).uci_variant
'giveaway'
>>> type(board).starting_fen
'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1'

UCI module
----------

Stockfish and other engines allow you to switch variants by setting the
``UCI_Variant`` option.

>>> engine.setoption({"UCI_Variant": "atomic"})

Syzygy module
-------------

Syzygy tablebases are available for suicide, giveaway and atomic chess.

>>> tables = chess.syzygy.open_tablebases("data/syzygy", VariantBoard=chess.variant.AtomicBoard)
