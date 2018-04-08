Syzygy endgame tablebase probing
================================

Syzygy tablebases provide **WDL** (win/draw/loss) and **DTZ** (distance to
zero) information for all endgame positions with up to 6 (and experimentally 7)
pieces. Positions with castling rights are not included.

.. autofunction:: chess.syzygy.open_tablebases

.. autoclass:: chess.syzygy.Tablebases
    :members:
