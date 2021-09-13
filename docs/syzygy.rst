Syzygy endgame tablebase probing
================================

Syzygy tablebases provide WDL\ :sub:`50` (win/draw/loss under the 50-move rule) and
DTZ\ :sub:`50`'' (distance to zeroing) information with rounding for all endgame
positions with up to 7 pieces. Positions with castling rights are not included.

.. warning::
    Ensure tablebase files match the known checksums. Maliciously crafted
    tablebase files may cause denial of service.

.. autofunction:: chess.syzygy.open_tablebase

.. autoclass:: chess.syzygy.Tablebase
    :members:
