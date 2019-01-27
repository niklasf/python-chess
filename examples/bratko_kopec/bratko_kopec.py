#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Run an EPD test suite with an UCI engine."""

import asyncio
import time
import argparse
import itertools
import logging
import sys

import chess
import chess.engine
import chess.variant


async def test_epd(engine, epd, VariantBoard, movetime):
    board, epd_info = VariantBoard.from_epd(epd)
    epd_string = epd_info.get("id", board.fen())
    if "am" in epd_info:
        epd_string = "{} (avoid {})".format(epd_string, " and ".join(board.san(am) for am in epd_info["am"]))
    if "bm" in epd_info:
        epd_string = "{} (expect {})".format(epd_string, " or ".join(board.san(bm) for bm in epd_info["bm"]))

    limit = chess.engine.Limit(time=movetime)
    result = await engine.play(board, limit, game=object())

    if "am" in epd_info and result.move in epd_info["am"]:
        print("{}: {} | +0".format(epd_string, board.san(result.move)))
        return 0.0
    elif "bm" in epd_info and result.move not in epd_info["bm"]:
        print("{}: {} | +0".format(epd_string, board.san(result.move)))
        return 0.0
    else:
        print("{}: {} | +1".format(epd_string, board.san(result.move)))
        return 1.0


async def test_epd_with_fractional_scores(engine, epd, VariantBoard, movetime):
    board, epd_info = VariantBoard.from_epd(epd)
    epd_string = epd_info.get("id", board.fen())
    if "am" in epd_info:
        epd_string = "{} (avoid {})".format(epd_string, " and ".join(board.san(am) for am in epd_info["am"]))
    if "bm" in epd_info:
        epd_string = "{} (expect {})".format(epd_string, " or ".join(board.san(bm) for bm in epd_info["bm"]))

    # Start analysis.
    score = 0.0
    print("{}:".format(epd_string), end=" ", flush=True)
    analysis = await engine.analysis(board, game=object())

    with analysis:
        for step in range(0, 4):
            await asyncio.sleep(movetime / 4)

            # Assess the current principal variation.
            if "pv" in analysis.info and len(analysis.info["pv"]) >= 1:
                move = analysis.info["pv"][0]
                print(board.san(move), end=" ", flush=True)
                if "am" in epd_info and move in epd_info["am"]:
                    continue  # fail
                elif "bm" in epd_info and move not in epd_info["bm"]:
                    continue  # fail
                else:
                    score = 1.0 / (4 - step)
            else:
                print("(no pv)", end=" ", flush=True)

    # Done.
    print("| +{}".format(score))
    return score


async def main():
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description=__doc__)

    engine_group = parser.add_mutually_exclusive_group(required=True)
    engine_group.add_argument("-u", "--uci",
        help="The UCI engine under test.")
    engine_group.add_argument("-x", "--xboard",
        help="The XBoard engine under test.")

    parser.add_argument("epd", nargs="+", type=argparse.FileType("r"),
        help="EPD test suite(s).")
    parser.add_argument("-v", "--variant", default="standard",
        help="Use a non-standard chess variant.")
    parser.add_argument("-t", "--threads", default=1, type=int,
        help="Threads for use by the UCI engine.")
    parser.add_argument("-m", "--movetime", default=1.0, type=float,
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

    # Find variant.
    VariantBoard = chess.variant.find_variant(args.variant)

    # Open and configure engine.
    if args.uci:
        _, engine = await chess.engine.popen_uci(args.uci)
        if args.threads > 1:
            await engine.configure({"Threads": args.threads})
    else:
        _, engine = await chess.engine.popen_xboard(args.xboard)
        if args.threads > 1:
            await engine.configure({"cores": args.threads})

    # Run each test line.
    score = 0.0
    count = 0

    for epd in itertools.chain(*args.epd):
        # Skip comments and empty lines.
        epd = epd.strip()
        if not epd or epd.startswith("#") or epd.startswith("%"):
            print(epd.rstrip())
            continue

        # Run the actual test.
        score += await args.test_epd(engine, epd, VariantBoard, args.movetime)
        count += 1

    await engine.quit()

    print("-------------------------------")
    print("{} / {}".format(score, count))


if __name__ == "__main__":
    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())
