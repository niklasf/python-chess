#!/usr/bin/env python3

"""Compute X-ray attacks through more valuable pieces."""

import chess


def xray_rook_attackers(board: chess.Board, color: chess.Color, square: chess.Square) -> chess.SquareSet:
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


def xray_bishop_attackers(board: chess.Board, color: chess.Color, square: chess.Square) -> chess.SquareSet:
    occupied = board.occupied
    diag_pieces = chess.BB_DIAG_MASKS[square] & occupied

    # Find the closest piece for each direction. These may block attacks.
    blockers = chess.BB_DIAG_ATTACKS[square][diag_pieces]

    # Only consider blocking pieces of the victim that are more valuable
    # than bishops.
    blockers &= board.occupied_co[not color] & (board.rooks | board.queens | board.kings)

    # Now just ignore those blocking pieces.
    occupied ^= blockers

    # And compute bishop attacks.
    diag_pieces = chess.BB_DIAG_MASKS[square] & occupied
    return chess.SquareSet(board.occupied_co[color] & board.bishops & chess.BB_DIAG_ATTACKS[square][diag_pieces])


def example() -> None:
    board = chess.Board("r3k2r/pp3p2/4p2Q/4q1p1/4P3/P2PK3/6PP/R3R3 w q - 1 2")
    print("rook x-ray, black, h3:")
    print(xray_rook_attackers(board, chess.BLACK, chess.H3))

    board = chess.Board("r1b1r1k1/pp1n1pbp/1qp3p1/B2p4/3P4/Q3PN2/PP2BPPP/R4RK1 b - - 0 1")
    print("bishop x-ray, white, d8:")
    print(xray_bishop_attackers(board, chess.WHITE, chess.D8))


if __name__ == "__main__":
    example()
