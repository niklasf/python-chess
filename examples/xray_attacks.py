#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Compute X-Ray attacks through more valuable pieces."""

import chess


def xray_rook_attackers(board, color, square):
    occupied = board.occupied
    rank_pieces = chess.BB_RANK_MASKS[square] & occupied
    file_pieces = chess.BB_FILE_MASKS[square] & occupied

    # Find the closest piece for each direction. These may block attacks.
    blockers = chess.BB_RANK_ATTACKS[square][rank_pieces] | chess.BB_FILE_ATTACKS[square][file_pieces]

    # Only consider blocking pieces of the victim that are more valuable
    # than rooks.
    blockers &= board.occupied_co[not color] & (board.queens | board.kings)

    # Now just ignore those blocking pieces.
    occupied ^= blockers

    # And compute rook attacks.
    rank_pieces = chess.BB_RANK_MASKS[square] & occupied
    file_pieces = chess.BB_FILE_MASKS[square] & occupied
    return chess.SquareSet(board.occupied_co[color] & board.rooks & (
        chess.BB_RANK_ATTACKS[square][rank_pieces] |
        chess.BB_FILE_ATTACKS[square][file_pieces]))


def example():
    board = chess.Board("r3k2r/pp3p2/4p2Q/4q1p1/4P3/P2PK3/6PP/R3R3 w q - 1 2")
    print(xray_rook_attackers(board, chess.BLACK, chess.H3))


if __name__ == "__main__":
    example()
