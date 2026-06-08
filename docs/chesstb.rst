chesstb endgame tablebase probing
==================================

`chesstb <https://github.com/noobpwnftw/chesstb>`_ tablebases provide
50-move-rule-aware **WDL** (win/draw/loss, with cursed/blessed classes),
**DTC** (distance to conversion -- plies to the next zeroing move), and a
**DTM50** pack giving both the unbounded **DTM** (depth to mate) and the exact
50-move-rule DTM at any halfmove clock. Positions with castling rights are not
included.

This is a pure-Python prober (it depends only on the standard library); no
native extension is required.

.. code-block:: python

    import chess
    import chess.chesstb

    with chess.chesstb.open_tablebase("data/chesstb") as tablebase:
        board = chess.Board("8/8/8/5k2/8/8/1Q6/K7 w - - 0 1")
        print(tablebase.probe_wdl(board))    # 2  (+2 win .. -2 loss)
        print(tablebase.probe_dtz(board))    # 19 (signed distance to conversion)
        print(tablebase.probe_dtm(board))    # 19 (signed distance to mate)
        print(tablebase.probe_dtm50(board))  # (2, 19): rule-true (wdl, plies)

.. warning::
    Maliciously crafted tablebase files may cause denial of service.

.. autofunction:: chess.chesstb.open_tablebase

.. autoclass:: chess.chesstb.Tablebase
    :members: probe_wdl, get_wdl, probe_dtz, get_dtz, probe_dtm, get_dtm, probe_dtm50, probe, add_directory, close

.. autoclass:: chess.chesstb.ProbeResult
    :members:

.. autoexception:: chess.chesstb.MissingTableError
