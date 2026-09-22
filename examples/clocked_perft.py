"""Example: clock legal-move generation and perft counting for a position.

The single most recycled hot loop in chess engines, RL-for-Universal-
Compiler-Optimization pipelines and chessy is the legal-move generator
plus the perft* node counters (the same "how many nodes can this machine
walk" benchmark the RL-for-Universal-Compiler-Optimization README measures
when tuning offline inference budgets). This example is deliberately tiny:
copy the FEN, get canonical node counts (perft values that every engine
test suite checks against), and get a real wall-clock nodes/sec figure for
this machine and this python-chess build.

Run:
    python clocked_perft.py                    # start position, depth 4
    python clocked_perft.py "<FEN>" 3          # custom position / depth

Output (one parseable line plus per-depth details):
    total_nodes_per_s=xxx  total_wall_s=yyy  total_nodes=zzz  perft=<dict>
    d1=<a>  d2=<b>  ...  dN=<z>

perft(W) is defined as the number of distinct lines of play of exactly W
plies from the given position; the well-known reference values are:
    start:  d1=20 d2=400 d3=8902 d4=197281 d5=4865609
    "KiwiPete" (k1q1...):  d1=48 d2=2039 d3=97862 d4=4085603
Those are exactly the numbers python-chess engines and UCI benches print
to prove the node counter matches the canonical test suite.
"""
import sys
import time

import chess


def perft(board, depth):
    """Return the depth-bounded node count for exactly `depth` plies."""
    if depth == 0:
        return 1
    nodes = 0
    for move in board.legal_moves:
        board.push(move)
        nodes += perft(board, depth - 1)
        board.pop()
    return nodes


def clocked_perft(fen, depth):
    """Return (perft_wall_s, total_nodes, {d: n}) with a per-depth breakdown."""
    board = chess.Board(fen)
    t0 = time.perf_counter()
    per_depth = {}
    for d in range(1, depth + 1):
        per_depth[d] = perft(board, d)
    wall = time.perf_counter() - t0
    total = sum(per_depth.values())
    return wall, total, per_depth


def main():
    fen = sys.argv[1] if len(sys.argv) > 1 else chess.STARTING_FEN
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    wall, total, per_depth = clocked_perft(fen, depth)
    nps = total / wall if wall else 0.0
    parts = ["total_nodes_per_s=%.1f" % nps,
             "total_wall_s=%.3f" % wall,
             "total_nodes=%d" % total,
             "perft=" + str(per_depth)]
    print("  ".join(parts))


if __name__ == "__main__":
    main()
