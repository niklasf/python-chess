Gaviota endgame tablebase probing (experimental)
================================================

This module is experimental and does not yet come with a pure Python fallback.
Instead you have to build and install a shared library:
https://github.com/michiguel/Gaviota-Tablebases

Gaviota tablebases provide **WDL** (win/draw/loss) and **DTM** (depth to mate)
information for all endgame positions with up to 5 pieces. Positions with
castling rights are not included.

.. autofunction:: chess.gaviota.open_tablebases

.. autoclass:: chess.gaviota.NativeTablebases
    :members:
