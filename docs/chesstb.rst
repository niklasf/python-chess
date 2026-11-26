chesstb endgame tablebase probing
==================================

`chesstb <https://github.com/noobpwnftw/chesstb>`_ tablebases provide WDL
(win/draw/loss), DTZ (distance to zeroing), DTC (distance to conversion,
counting pawn pushes separately), DTM (distance to mate) and DTM50 (distance
to mate under the 50-move rule) information for endgame positions, including
positions with castling rights.

Distances are in plies, from the point of view of the side to move: positive
if it is winning, negative if it is losing, and ``0`` for a draw or a
checkmate on the board. DTC and DTM50 are probed at a halfmove clock, and are
``0`` where the 50-move rule draws.

Probes expect a legal position: check untrusted input with
:func:`chess.Board.is_valid` first.
`python-lz4 <https://pypi.org/project/lz4/>`_ is used if installed, but isn't
required.

.. warning::
    Maliciously crafted tablebase files may cause denial of service.

.. autofunction:: chess.chesstb.open_tablebase

.. autoclass:: chess.chesstb.Tablebase
    :members:

.. autoclass:: chess.chesstb.ProbeResult
    :members:

.. autoexception:: chess.chesstb.MissingTableError
