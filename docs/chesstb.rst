chesstb endgame tablebase probing
==================================

`chesstb <https://github.com/noobpwnftw/chesstb>`_ tablebases provide WDL
(win/draw/loss, with cursed and blessed results under the 50-move rule), DTZ
(distance to zeroing), DTC (pawn pushes still owed before a conversion, then
plies to the next zeroing move), DTM (distance to mate) and DTM50 (distance to
mate under the 50-move rule). Positions with castling rights have their own
tables, named with a lowercase ``r`` for each rook holding a right, as in
``KrK``.

A chesstb DTZ is a plain distance in every WDL class; unlike Syzygy's, it
doesn't encode the base shift for cursed and blessed results.

Tables are looked up in the ``wdl``, ``dtz``, ``dtc``, ``dtm`` and ``dtm50``
subdirectories of each directory, or in the directory itself. Probes expect a
legal position and don't validate it: check untrusted input with
:func:`chess.Board.is_valid` first. `python-lz4 <https://pypi.org/project/lz4/>`_
is used if installed, but isn't required.

.. warning::
    Maliciously crafted tablebase files may cause denial of service.

.. autofunction:: chess.chesstb.open_tablebase

.. autoclass:: chess.chesstb.Tablebase
    :members: probe_wdl, get_wdl, probe_dtz, get_dtz, probe_dtc, probe_dtm, get_dtm, probe_dtm50, probe, add_directory, close

.. autoclass:: chess.chesstb.ProbeResult
    :members:

.. autoexception:: chess.chesstb.MissingTableError
