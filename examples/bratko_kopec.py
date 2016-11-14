#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2015 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
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
    position = chess.Board()
    epd_info = position.set_epd(epd)
    epd_string = "%s" % epd_info.get("id", position.fen())
    if "am" in epd_info:
        epd_string = "%s (avoid %s)" % (epd_string, " and ".join(position.san(am) for am in epd_info["am"]))
    if "bm" in epd_info:
        epd_string = "%s (expect %s)" % (epd_string, " or ".join(position.san(bm) for bm in epd_info["bm"]))

    engine.ucinewgame()
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

    position = chess.Board()
    epd_info = position.set_epd(epd)
    epd_string = "%s" % epd_info.get("id", position.fen())
    if "am" in epd_info:
        epd_string = "%s (avoid %s)" % (epd_string, " and ".join(position.san(am) for am in epd_info["am"]))
    if "bm" in epd_info:
        epd_string = "%s (expect %s)" % (epd_string, " or ".join(position.san(bm) for bm in epd_info["bm"]))

    engine.ucinewgame()
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
    bratko_kopec = StringIO(textwrap.dedent("""\
        % Default Bratko-Kopec testsuite.
        1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id "BK.01";
        3r1k2/4npp1/1ppr3p/p6P/P2PPPP1/1NR5/5K2/2R5 w - - bm d5; id "BK.02";
        2q1rr1k/3bbnnp/p2p1pp1/2pPp3/PpP1P1P1/1P2BNNP/2BQ1PRK/7R b - - bm f5; id "BK.03";
        rnbqkb1r/p3pppp/1p6/2ppP3/3N4/2P5/PPP1QPPP/R1B1KB1R w KQkq - bm e6; id "BK.04";
        r1b2rk1/2q1b1pp/p2ppn2/1p6/3QP3/1BN1B3/PPP3PP/R4RK1 w - - bm Nd5 a4; id "BK.05";
        2r3k1/pppR1pp1/4p3/4P1P1/5P2/1P4K1/P1P5/8 w - - bm g6; id "BK.06";
        1nk1r1r1/pp2n1pp/4p3/q2pPp1N/b1pP1P2/B1P2R2/2P1B1PP/R2Q2K1 w - - bm Nf6; id "BK.07";
        4b3/p3kp2/6p1/3pP2p/2pP1P2/4K1P1/P3N2P/8 w - - bm f5; id "BK.08";
        2kr1bnr/pbpq4/2n1pp2/3p3p/3P1P1B/2N2N1Q/PPP3PP/2KR1B1R w - - bm f5; id "BK.09";
        3rr1k1/pp3pp1/1qn2np1/8/3p4/PP1R1P2/2P1NQPP/R1B3K1 b - - bm Ne5; id "BK.10";
        2r1nrk1/p2q1ppp/bp1p4/n1pPp3/P1P1P3/2PBB1N1/4QPPP/R4RK1 w - - bm f4; id "BK.11";
        r3r1k1/ppqb1ppp/8/4p1NQ/8/2P5/PP3PPP/R3R1K1 b - - bm Bf5; id "BK.12";
        r2q1rk1/4bppp/p2p4/2pP4/3pP3/3Q4/PP1B1PPP/R3R1K1 w - - bm b4; id "BK.13";
        rnb2r1k/pp2p2p/2pp2p1/q2P1p2/8/1Pb2NP1/PB2PPBP/R2Q1RK1 w - - bm Qd2 Qe1; id "BK.14";
        2r3k1/1p2q1pp/2b1pr2/p1pp4/6Q1/1P1PP1R1/P1PN2PP/5RK1 w - - bm Qxg7+; id "BK.15";
        r1bqkb1r/4npp1/p1p4p/1p1pP1B1/8/1B6/PPPN1PPP/R2Q1RK1 w kq - bm Ne4; id "BK.16";
        r2q1rk1/1ppnbppp/p2p1nb1/3Pp3/2P1P1P1/2N2N1P/PPB1QP2/R1B2RK1 b - - bm h5; id "BK.17";
        r1bq1rk1/pp2ppbp/2np2p1/2n5/P3PP2/N1P2N2/1PB3PP/R1B1QRK1 b - - bm Nb3; id "BK.18";
        3rr3/2pq2pk/p2p1pnp/8/2QBPP2/1P6/P5PP/4RRK1 b - - bm Rxe4; id "BK.19";
        r4k2/pb2bp1r/1p1qp2p/3pNp2/3P1P2/2N3P1/PPP1Q2P/2KRR3 w - - bm g4; id "BK.20";
        3rn2k/ppb2rpp/2ppqp2/5N2/2P1P3/1P5Q/PB3PPP/3RR1K1 w - - bm Nh6; id "BK.21";
        2r2rk1/1bqnbpp1/1p1ppn1p/pP6/N1P1P3/P2B1N1P/1B2QPP1/R2R2K1 b - - bm Bxe4; id "BK.22";
        r1bqk2r/pp2bppp/2p5/3pP3/P2Q1P2/2N1B3/1PP3PP/R4RK1 b kq - bm f6; id "BK.23";
        r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - bm f4; id "BK.24";
        """))

    # Parse command line arguments.
    parser = argparse.ArgumentParser(description="Run an EPD test suite with an UCI engine.")
    parser.add_argument("-e", "--engine", required=True,
        help="The UCI engine under test.")
    parser.add_argument("epd", nargs="*", type=argparse.FileType("r"), default=[bratko_kopec],
        help="EPD test suites. Will default to Bratko-Kopec if none given.")
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
