#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2016 Daniel Dugovic <dandydand@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import chess
import chess.uci
import chess.variant
import time
import textwrap
import argparse
import itertools
import logging

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO  # Python 3


def test_epd(engine, epd, movetime):
    position = chess.variant.GiveawayBoard()
    epd_info = position.set_epd(epd)
    epd_string = "%s" % epd_info.get("id", position.fen())
    if "am" in epd_info:
        epd_string = "%s (avoid %s)" % (epd_string, " and ".join(position.san(am) for am in epd_info["am"]))
    if "bm" in epd_info:
        epd_string = "%s (expect %s)" % (epd_string, " or ".join(position.san(bm) for bm in epd_info["bm"]))

    engine.ucinewgame()
    engine.setoption({"UCI_Variant": "giveaway"})
    engine.position(position)

    enginemove, pondermove = engine.go(movetime=movetime)

    if "am" in epd_info and enginemove in epd_info["am"]:
        print("%s: %s | +0" % (epd_string, position.san(enginemove)))
        return 0.0
    elif "bm" in epd_info and not enginemove in epd_info["bm"]:
        print("%s: %s | +0" % (epd_string, position.san(enginemove)))
        return 0.0
    else:
        print("%s: %s | +1" % (epd_string, position.san(enginemove)))
        return 1.0


def test_epd_with_fractional_scores(engine, epd, movetime):
    info_handler = chess.uci.InfoHandler()
    engine.info_handlers.append(info_handler)

    position = chess.variant.GiveawayBoard()
    epd_info = position.set_epd(epd)
    epd_string = "%s" % epd_info.get("id", position.fen())
    if "am" in epd_info:
        epd_string = "%s (avoid %s)" % (epd_string, " and ".join(position.san(am) for am in epd_info["am"]))
    if "bm" in epd_info:
        epd_string = "%s (expect %s)" % (epd_string, " or ".join(position.san(bm) for bm in epd_info["bm"]))

    engine.ucinewgame()
    engine.setoption({"UCI_Variant": "giveaway"})
    engine.position(position)

    # Search in background
    search = engine.go(infinite=True, async_callback=True)

    score = 0.0

    print("%s:" % epd_string, end=" ")

    for step in range(0, 3):
        time.sleep(movetime / 4000.0)

        # Assess the current principal variation.
        with info_handler as info:
            if 1 in info["pv"] and len(info["pv"][1]) >= 1:
                move = info["pv"][1][0]
                print("(%s)" % position.san(move), end=" ")
                if "am" in epd_info and move in epd_info["am"]:
                    continue #fail
                elif "bm" in epd_info and not move in epd_info["bm"]:
                    continue #fail
                else:
                     score = 1.0 / (4 - step)
            else:
                print("(no pv)", end=" ")

    # Assess the final best move by the engine.
    time.sleep(movetime / 4000.0)
    engine.stop()
    enginemove, pondermove = search.result()
    if "am" in epd_info and enginemove in epd_info["am"]:
        pass #fail
    elif "bm" in epd_info and not enginemove in epd_info["bm"]:
        pass #fail
    else:
         score = 1.0

    print("%s | +%g" % (position.san(enginemove), score))

    engine.info_handlers.remove(info_handler)
    return score


if __name__ == "__main__":
    chessvariants_training = StringIO(textwrap.dedent("""\
        % Default giveaway variant testsuite from Chess Variants Training.
        2b5/K1p1pk2/6pb/8/8/8/8/8 b - - bm Bb7;
        rnbqkbnr/p1pppp1p/1p4p1/8/8/1P2P1P1/P1PP1P1P/RNBQKBNR b KQkq - bm b5;
        8/8/7P/8/8/8/4p3/5R2 b - - bm exf1=R;
        8/8/8/K7/8/1P3N2/P1n5/3N4 w - - bm Kb4;
        6n1/n7/8/8/5P2/8/2P5/3R4 b - - bm Nc6;
        6B1/8/7p/6k1/8/R7/7p/8 w - - bm Bd5 Be6 Bf7;
        6n1/n7/8/5p2/8/4P3/2P5/4R3 w - - bm e4;
        6n1/n7/8/5p2/4P3/8/2P5/4R3 b - - bm fxe4;
        8/P7/8/k7/P7/8/8/8 w - - bm a8=N;
        8/8/8/4b3/8/1R5R/4P3/8 w - - bm Rb2;
        8/8/p7/8/8/8/7P/8 w - - bm h3;
        8/8/8/8/1p6/7R/p7/8 b - - bm b3;
        8/5p2/7p/8/7P/8/5P2/8 w - - bm h5;
        8/P7/8/8/8/5k2/8/7b w - - bm a8=K;
        2q5/3k4/8/8/8/5K2/8/8 w - - bm Ke4;
        8/8/8/6b1/1NR5/8/8/8 w - - bm Rc1;
        8/P7/8/8/1np5/8/8/8 w - - bm a8=R;
        B2n4/pP6/1b6/8/8/8/8/8 w - - bm b8=Q;
        8/5P2/8/2r5/8/8/8/8 w - - bm f8=B;
        8/8/8/8/4k2P/8/8/1R6 w - - bm Rg1;
        8/8/8/1r1P1r2/8/8/1P3P2/8 w - - bm d6;
        8/5P2/8/8/8/2n5/p7/8 w - - bm f8=B;
        R7/8/8/4k3/8/2k2k2/8/8 b - - bm Kg2 Kg4;
        K7/8/4k3/k1k5/8/8/8/8 b - - bm Kd7;
        2r5/8/K3k3/8/4n3/3r4/8/8 b - - bm Rc4;
        rnbqkbnr/pppppppp/8/8/8/3P4/PPP1PPPP/RNBQKBNR b KQkq - bm g5;
        rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - bm b5;
        rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - bm e5;
        r2k2nr/5ppp/3bp3/8/8/8/3p2PP/5KNR w - - bm Ke2;
        rn2k3/8/p1p1P2p/2b5/8/7N/PP1N1PP1/R1B1K3 w Qq - bm Nb1;
        8/8/4R3/8/8/1P6/1NP2Pp1/5R2 b - - bm gxf1=N;
        r7/p4P2/P7/1pP5/3PP3/6b1/6B1/8 w - - bm e5;
        8/8/5b2/8/1p6/8/2P4N/3R4 w - - bm Ra1;
        8/3nPp1p/7p/8/8/8/8/8 w - - bm e8=K;
        5B2/3p1k1p/5N2/8/8/8/8/8 w - - bm Nxh7;
        8/8/7N/4n3/3k4/8/4P2K/8 w - - bm e4;
        8/8/nk6/8/P7/5Q2/8/8 w - - bm a5;
        8/8/8/1p1K2K1/8/2K1K1KK/8/2K1K1KK w - - bm Kcd3 Kc3d2 K3b2;
        8/B7/8/3p4/8/1N3P2/1K2P3/7R w - - bm Nc5;
        8/8/8/8/5k1k/3k4/8/7K b - - bm Kde3 Ke2;
        8/1b1P3k/2r5/1n2K1P1/8/8/8/8 w - - bm g6;
        3n4/8/1k6/8/8/8/8/1B6 w - - bm Be4;
        8/8/8/8/8/8/8/3K2b1 b - - bm Bd4;
        3k4/8/8/8/2NNNN2/1N6/8/8 w - - bm Ng5;
        8/8/P4P2/8/8/2B5/7p/8 b - - bm h1=Q;
        8/1K6/7N/7P/P7/8/4PP2/4b3 w - - bm Nf5;
        rnbqk3/p1pppp2/1p4pb/8/8/8/PPPPPP2/RNBQKBN1 w Qq - bm Bg2;
        rn2qbn1/p1pppQ2/8/8/P7/8/3PbP1P/RNB1K2R w - - bm Kxe2;
        6B1/8/8/8/1P6/3P4/3p1K2/6N1 b - - bm d1=B;
        rnbqkbn1/p1pppp2/1p4p1/8/6P1/8/PPPPPP1R/RNBQKBN1 b Qq - bm g5;
        rnbqkbn1/p1pppp2/1p4p1/8/6P1/1P6/P1PPPP1R/RNBQKBN1 b Qq - bm g5;
        rnbqkbn1/p1pppp2/8/1p6/6P1/8/PPPPPP1R/RNBQKBN1 b Qq - bm f5;
        rnbqkbn1/p1pppp2/8/1p6/6P1/1P6/P1PPPP1R/RNBQKBN1 b Qq - bm c6;
        rnbqkbn1/ppp1pp2/3p4/8/6P1/8/PPPPPP1R/RNBQKBN1 w Qq - bm a3;
        4k2B/5p1p/8/8/r7/8/8/8 b - - bm Ra1;
        rnb1k1n1/p1p2pp1/4p3/7r/8/4P3/P1PB1PPP/R3K1NR w KQq - bm Bc3;
        8/8/8/KK6/8/6r1/1k6/8 w - - bm Kab4;
        7K/8/3k4/5k2/8/8/8/8 b - - bm Kde6 Ke7;
        8/8/8/3R4/p7/3K4/k7/8 w - - bm Rb5;
        rnbq1bn1/p1ppp3/1p4k1/8/8/BP6/P1PPPK2/RN1Q4 b - - bm Bg7;
        8/6PP/8/8/N7/8/3p4/5r2 w - - bm g8=B;
        2R5/4P3/8/7n/8/8/pp6/8 b - - bm b1=B;
        r2k1bnr/p1pnpqpp/8/8/8/1P5N/P1PP3P/RNBK3R w - - bm Rg1;
        8/4kp2/7r/3P1P2/8/6P1/2p5/4K3 b - - bm Rh4;
        7r/1K2P3/8/8/8/8/7p/8 b - - bm Rc8;
        8/4kp2/1p1p3n/8/8/B2PP3/3P1P2/1N6 b - - bm Kd8;
        """))

    # Parse command line arguments.
    parser = argparse.ArgumentParser(description="Run an EPD test suite with an UCI engine.")
    parser.add_argument("-e", "--engine", required=True,
        help="The UCI engine under test.")
    parser.add_argument("epd", nargs="*", type=argparse.FileType("r"), default=[chessvariants_training],
        help="EPD test suites. Will default to Chess Variants Training if none given.")
    parser.add_argument("-t", "--movetime", default=1000, type=int,
        help="Time to move in milliseconds.")
    parser.add_argument("-s", "--simple", dest="test_epd", action="store_const",
        default=test_epd_with_fractional_scores,
        const=test_epd,
        help="Run in simple mode without fractional scores.")
    parser.add_argument("-d", "--debug", action="store_true",
        help="Show debug logs.")
    args = parser.parse_args()

    # Configure logger.
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)

    # Open engine.
    engine = chess.uci.popen_engine(args.engine)
    engine.uci()

    # Run each test line.
    score = 0.0
    count = 0

    for epd in itertools.chain(*args.epd):
        print(epd.rstrip())

        # Skip comments and empty lines.
        epd = epd.strip()
        if not epd or epd.startswith("#") or epd.startswith("%"):
            continue

        # Run the actual test.
        score += args.test_epd(engine, epd, args.movetime)
        count += 1

    engine.quit()

    print("-------------------------------")
    print("%g / %d" % (score, count))
