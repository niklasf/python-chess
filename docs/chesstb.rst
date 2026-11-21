chesstb endgame tablebase probing
==================================

`chesstb <https://github.com/noobpwnftw/chesstb>`_ tablebases provide
50-move-rule-aware **WDL** (win/draw/loss, with cursed/blessed classes),
**DTZ** (distance to zeroing -- plies to the next capture, promotion or pawn
move), a **DTC** pack pricing pawn pushes separately from waiting, and a
**DTM50** pack giving both the unbounded **DTM** (depth to mate) and the exact
50-move-rule DTM at any halfmove clock. Where no pack is present, a standalone
**DTM** table answers the unbounded mate distance on its own. A rook still
holding a castling right is a dimension of the index, so a position with rights
is answered only from a table carrying them -- chesstb writes those materials
with a lowercase ``r``, as in ``KrK``.

Table files are looked up in the ``wdl/``, ``dtz/``, ``dtc/``, ``dtm/`` and
``dtm50/`` subdirectories of each search directory, or in the directory itself
where that subdirectory is absent. Each pack embeds an unbounded table and so makes it redundant -- the
DTM50 pack the standalone DTM, the DTC pack the DTZ -- and a material shipping
both is read from the pack alone.

DTZ measures the same thing as syzygy's, but encodes it differently and the two
are not interchangeable: syzygy bases its cursed band off 100, so a DTZ magnitude
carries the WDL class along with the count, whereas a chesstb DTZ is a plain
distance in every class, the class being WDL's alone.

**DTC** answers a pair at a given halfmove clock: how many pawn pushes the
winning side still owes before a conversion (a capture or a promotion), and the
plies to the next zeroing move on the line that owes them. The key is pushes
first, then plies, which is what DTZ cannot express -- it prices every push at 1
and so reads 1 almost everywhere a pawn can move. Fewer pushes cost a longer
wait, so a tighter clock forces the trade the other way, and where no budget
fits the clock the answer is a 50-move draw. Packs exist for pawnful materials;
for a pawnless one every zeroing move is already a conversion, so the answer is
DTZ's own number at nothing owed.

Probes assume a legal position -- both kings present, the side not to move not
in check, no pawn outside ranks 2-7 -- and do not validate it. Probing
anything else is undefined: it reads whatever cell the placement maps to, or
raises out of the indexer. Screen untrusted input with
:func:`chess.Board.is_valid` first. A position with standing castling rights is
looked up under its rights-bearing material whether or not that table is on
disk, so a miss there is reported as :class:`~chess.chesstb.MissingTableError`.

This is a pure-Python prober (it depends only on the standard library); no
native extension is required. Where `python-lz4
<https://pypi.org/project/lz4/>`_ is installed it is used for WDL blocks, which
is faster and releases the GIL, but nothing needs it.

.. code-block:: python

    import chess
    import chess.chesstb

    with chess.chesstb.open_tablebase("data/chesstb") as tablebase:
        board = chess.Board("8/8/8/5k2/8/8/1Q6/K7 w - - 0 1")
        print(tablebase.probe_wdl(board))    # 2  (+2 win .. -2 loss)
        print(tablebase.probe_dtz(board))    # 19 (signed distance to zeroing)
        print(tablebase.probe_dtm(board))    # 19 (signed distance to mate)
        print(tablebase.probe_dtm50(board))  # 19 (rule-true signed distance)
        print(tablebase.probe_dtc(board))    # (0, 19): (pushes, signed plies)

        board = chess.Board("8/8/8/k7/8/8/K4P2/8 w - - 0 1")
        print(tablebase.probe_dtc(board))       # (4, 23): four pushes, 23 plies
        print(tablebase.probe_dtc(board, 80))   # (5, 19): tighter clock, one push more
        print(tablebase.probe_dtc(board, 95))   # (0, 0): that clock has taken the win

.. warning::
    Maliciously crafted tablebase files may cause denial of service.

.. autofunction:: chess.chesstb.open_tablebase

.. autoclass:: chess.chesstb.Tablebase
    :members: probe_wdl, get_wdl, probe_dtz, get_dtz, probe_dtc, probe_dtm, get_dtm, probe_dtm50, probe, add_directory, close

.. autoclass:: chess.chesstb.ProbeResult
    :members:

.. autoexception:: chess.chesstb.MissingTableError
