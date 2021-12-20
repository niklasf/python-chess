#!/usr/bin/env python3

"""Run an EPD test suite with a UCI engine."""

import asyncio
import argparse
import itertools
import logging
import sys
import typing

from typing import List, Tuple, Type

import chess
import chess.engine
import chess.variant


def parse_epd(epd: str, VariantBoard: Type[chess.Board]) -> Tuple[chess.Board, str, List[chess.Move], List[chess.Move]]:
    board, epd_info = VariantBoard.from_epd(epd)

    description = str(epd_info.get("id", board.fen()))

    if "am" in epd_info:
        am = typing.cast(List[chess.Move], epd_info["am"])
        description = "{} (avoid {})".format(description, " and ".join(board.san(m) for m in am))
    else:
        am = []

    if "bm" in epd_info:
        bm = typing.cast(List[chess.Move], epd_info["bm"])
        description = "{} (expect {})".format(description, " or ".join(board.san(m) for m in bm))
    else:
        bm = []

    return board, description, am, bm


async def test_epd(engine: chess.engine.Protocol, epd: str, VariantBoard: Type[chess.Board], movetime: float) -> float:
    board, description, am, bm = parse_epd(epd, VariantBoard)

    limit = chess.engine.Limit(time=movetime)
    result = await engine.play(board, limit, game=object())

    if not result.move:
        print(f"{description}: -- | +0")
        return 0.0
    elif result.move in am:
        print(f"{description}: {board.san(result.move)} | +0")
        return 0.0
    elif bm and result.move not in bm:
        print(f"{description}: {board.san(result.move)} | +0")
        return 0.0
    else:
        print(f"{description}: {board.san(result.move)} | +1")
        return 1.0


async def test_epd_with_fractional_scores(engine: chess.engine.Protocol, epd: str, VariantBoard: Type[chess.Board], movetime: float) -> float:
    board, description, am, bm = parse_epd(epd, VariantBoard)

    # Start analysis.
    score = 0.0
    print(f"{description}:", end=" ", flush=True)
    analysis = await engine.analysis(board, game=object())

    with analysis:
        for step in range(0, 4):
            await asyncio.sleep(movetime / 4)

            # Assess the current principal variation.
            if "pv" in analysis.info and len(analysis.info["pv"]) >= 1:
                move = analysis.info["pv"][0]
                print(board.san(move), end=" ", flush=True)
                if move in am:
                    continue  # fail
                elif bm and move not in bm:
                    continue  # fail
                else:
                    score = 1.0 / (4 - step)
            else:
                print("(no pv)", end=" ", flush=True)

    # Done.
    print(f"| +{score}")
    return score


async def main() -> None:
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
        help="Time to move in seconds.")
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
    engine: chess.engine.Protocol
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
    print(f"{score} / {count}")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())
