"""Benchmark legal-move generation for a single chess position.

Unlike examples/perft/perft.py, this script takes a FEN directly instead of
reading a perft-suite file. It reports a timed node count for each depth and
checks the known start-position counts against a small canonical reference table.

Examples:
    python clocked_perft.py
    python clocked_perft.py "<FEN>" 3

The start-position reference counts are d1=20, d2=400, d3=8902, d4=197281,
and d5=4865609.
"""

import argparse
import time

import chess


STARTPOS_PERFT = {
    1: 20,
    2: 400,
    3: 8902,
    4: 197281,
    5: 4865609,
}


def perft(depth: int, board: chess.Board) -> int:
    """Return the number of legal move sequences exactly depth plies long."""
    if depth <= 0:
        return 1
    if depth == 1:
        return board.legal_moves.count()

    nodes = 0
    for move in board.legal_moves:
        board.push(move)
        nodes += perft(depth - 1, board)
        board.pop()
    return nodes


def positive_depth(value: str) -> int:
    """Parse a positive integer depth for argparse."""
    try:
        depth = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("depth must be a positive integer") from exc

    if depth < 1:
        raise argparse.ArgumentTypeError("depth must be at least 1")
    return depth


def clocked_perft(
    board: chess.Board, max_depth: int
) -> list[tuple[int, int, float]]:
    """Return per-depth (depth, node_count, elapsed_seconds) measurements."""
    results = []
    for depth in range(1, max_depth + 1):
        start = time.perf_counter()
        nodes = perft(depth, board)
        elapsed = time.perf_counter() - start
        results.append((depth, nodes, elapsed))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fen",
        nargs="?",
        default=chess.STARTING_FEN,
        help="FEN of the position (default: start position)",
    )
    parser.add_argument(
        "depth",
        nargs="?",
        type=positive_depth,
        default=4,
        help="maximum depth to measure (default: 4)",
    )
    args = parser.parse_args()

    board = chess.Board(args.fen)
    results = clocked_perft(board, args.depth)
    is_start_position = args.fen == chess.STARTING_FEN

    total_nodes = 0
    total_wall_s = 0.0
    for depth, nodes, elapsed in results:
        total_nodes += nodes
        total_wall_s += elapsed
        nps = nodes / elapsed if elapsed else float("inf")
        row = (
            f"depth={depth}  nodes={nodes}  wall_s={elapsed:.6f}  "
            f"nodes_per_s={nps:.1f}"
        )

        expected = STARTPOS_PERFT.get(depth) if is_start_position else None
        if expected is not None:
            row += f"  reference_nodes={expected}  reference_match={nodes == expected}"
        print(row)

    total_nps = total_nodes / total_wall_s if total_wall_s else float("inf")
    print(
        f"total_nodes={total_nodes}  total_wall_s={total_wall_s:.6f}  "
        f"total_nodes_per_s={total_nps:.1f}"
    )


if __name__ == "__main__":
    main()
