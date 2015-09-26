#!/usr/bin/env python

from __future__ import print_function

import chess
#import chess.gaviota
import chess.gaviota_native

#tables = chess.gaviota.open_tablebases("data/gaviota")
tables = chess.gaviota_native.PythonTableBase("data/gaviota")

def swap_colors(fen):
    parts = fen.split()
    turn = "w" if fen[1] == "b" else "b"
    return " ".join([parts[0].swapcase(), turn] + parts[2:])

def mirror_vertical(fen):
    parts = fen.split()
    position_parts = "/".join(reversed(parts[0].split("/")))
    return " ".join([position_parts] + parts[1:])

with open("data/long-endgames.epd") as epds:
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

        expected = extra["dm"] * 2 - 1

        # Check DTM.
        probe = tables.probe_dtm(board)
        dtm = probe.dtm
        print(board.epd(line=line, dtm=expected, got=dtm))
        assert expected == dtm

        # Check DTM with mirrored board.
        board = chess.Board(mirror_vertical(swap_colors(board.fen())))
        probe = tables.probe_dtm(board)
        dtm = probe.dtm
        print(board.epd(line=line, dtm=expected, got=dtm))
        assert expected == dtm
