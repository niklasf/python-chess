#!/usr/bin/env python

from __future__ import print_function

import chess
import chess.gaviota

tables = chess.gaviota.open_tablebases("data/gaviota", LibraryLoader=None)

with open("data/endgame-dm.epd") as epds:
    for line, epd in enumerate(epds):
        # Skip empty lines and comments.
        epd = epd.strip()
        if not epd or epd.startswith("#"):
            continue

        # Parse EPD.
        board, extra = chess.Board.from_epd(epd)

        # Skip 6 piece endgames.
        if chess.pop_count(board.occupied) > 5:
            continue

        expected = extra["dm"] * 2
        if expected > 0:
            expected -= 1

        # Check DTM.
        probe = tables.probe_dtm(board)
        dtm = probe.dtm
        print(board.epd(line=line, dtm=expected, got=dtm))
        assert expected == dtm
