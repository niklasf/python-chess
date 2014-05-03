#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = "Niklas Fiekas"

__email__ = "niklas.fiekas@tu-clausthal.de"

__version__ = "0.1.0"

import collections
import sys
import random
import time



COLORS = [ WHITE, BLACK ] = range(2)

PIECE_TYPES = [ NONE, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING ] = range(7)

PIECE_SYMBOLS = [ "", "p", "n", "b", "r", "q", "k" ]

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

SQUARES = [
    A1, B1, C1, D1, E1, F1, G1, H1,
    A2, B2, C2, D2, E2, F2, G2, H2,
    A3, B3, C3, D3, E3, F3, G3, H3,
    A4, B4, C4, D4, E4, F4, G4, H4,
    A5, B5, C5, D5, E5, F5, G5, H5,
    A6, B6, C6, D6, E6, F6, G6, H6,
    A7, B7, C7, D7, E7, F7, G7, H7,
    A8, B8, C8, D8, E8, F8, G8, H8 ] = range(64)

SQUARES_180 = [
    A8, B8, C8, D8, E8, F8, G8, H8,
    A7, B7, C7, D7, E7, F7, G7, H7,
    A6, B6, C6, D6, E6, F6, G6, H6,
    A5, B5, C5, D5, E5, F5, G5, H5,
    A4, B4, C4, D4, E4, F4, G4, H4,
    A3, B3, C3, D3, E3, F3, G3, H3,
    A2, B2, C2, D2, E2, F2, G2, H2,
    A1, B1, C1, D1, E1, F1, G1, H1 ]

SQUARES_L90 = [
    H1, H2, H3, H4, H5, H6, H7, H8,
    G1, G2, G3, G4, G5, G6, G7, G8,
    F1, F2, F3, F4, F5, F6, F7, F8,
    E1, E2, E3, E4, E5, E6, E7, E8,
    D1, D2, D3, D4, D5, D6, D7, D8,
    C1, C2, C3, C4, C5, C6, C7, C8,
    B1, B2, B3, B4, B5, B6, B7, B8,
    A1, A2, A3, A4, A5, A6, A7, A8 ]

SQUARES_R45 = [
    A1, B8, C7, D6, E5, F4, G3, H2,
    A2, B1, C8, D7, E6, F5, G4, H3,
    A3, B2, C1, D8, E7, F6, G5, H4,
    A4, B3, C2, D1, E8, F7, G6, H5,
    A5, B4, C3, D2, E1, F8, G7, H6,
    A6, B5, C4, D3, E2, F1, G8, H7,
    A7, B6, C5, D4, E3, F2, G1, H8,
    A8, B7, C6, D5, E4, F3, G2, H1 ]

SQUARES_L45 = [
    A2, B3, C4, D5, E6, F7, G8, H1,
    A3, B4, C5, D6, E7, F8, G1, H2,
    A4, B5, C6, D7, E8, F1, G2, H3,
    A5, B6, C7, D8, E1, F2, G3, H4,
    A6, B7, C8, D1, E2, F3, G4, H5,
    A7, B8, C1, D2, E3, F4, G5, H6,
    A8, B1, C2, D3, E4, F5, G6, H7,
    A1, B2, C3, D4, E5, F6, G7, H8 ]

SQUARE_NAMES = [
    "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1",
    "a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2",
    "a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3",
    "a4", "b4", "c4", "d4", "e4", "f4", "g4", "h4",
    "a5", "b5", "c5", "d5", "e5", "f5", "g5", "h5",
    "a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6",
    "a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7",
    "a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8" ]

def file_index(square):
    return square & 7

def rank_index(square):
    return square >> 3

CASTLING_NONE = 0
CASTLING_WHITE_KINGSIDE = 1
CASTLING_BLACK_KINGSIDE = 2
CASTLING_WHITE_QUEENSIDE = 4
CASTLING_BLACK_QUEENSIDE = 8
CASTLING_WHITE = CASTLING_WHITE_KINGSIDE | CASTLING_WHITE_QUEENSIDE
CASTLING_BLACK = CASTLING_BLACK_KINGSIDE | CASTLING_BLACK_QUEENSIDE
CASTLING = CASTLING_WHITE | CASTLING_BLACK


BB_VOID = 0b0000000000000000000000000000000000000000000000000000000000000000

BB_ALL = 0b1111111111111111111111111111111111111111111111111111111111111111

BB_SQUARES = [
    BB_A1, BB_B1, BB_C1, BB_D1, BB_E1, BB_F1, BB_G1, BB_H1,
    BB_A2, BB_B2, BB_C2, BB_D2, BB_E2, BB_F2, BB_G2, BB_H2,
    BB_A3, BB_B3, BB_C3, BB_D3, BB_E3, BB_F3, BB_G3, BB_H3,
    BB_A4, BB_B4, BB_C4, BB_D4, BB_E4, BB_F4, BB_G4, BB_H4,
    BB_A5, BB_B5, BB_C5, BB_D5, BB_E5, BB_F5, BB_G5, BB_H5,
    BB_A6, BB_B6, BB_C6, BB_D6, BB_E6, BB_F6, BB_G6, BB_H6,
    BB_A7, BB_B7, BB_C7, BB_D7, BB_E7, BB_F7, BB_G7, BB_H7,
    BB_A8, BB_B8, BB_C8, BB_D8, BB_E8, BB_F8, BB_G8, BB_H8
] = [ 1 << i for i in SQUARES ]

BB_LIGHT_SQUARES = BB_DARK_SQUARES = BB_VOID

for square, mask in enumerate(BB_SQUARES):
    if (file_index(square) + rank_index(square)) % 2:
        BB_LIGHT_SQUARES |= mask
    else:
        BB_DARK_SQUARES |= mask

BB_SQUARES_L90 = [ BB_SQUARES[SQUARES_L90[square]] for square in SQUARES ]

BB_SQUARES_L45 = [ BB_SQUARES[SQUARES_L45[square]] for square in SQUARES ]

BB_SQUARES_R45 = [ BB_SQUARES[SQUARES_R45[square]] for square in SQUARES ]

BB_FILES = [
    BB_FILE_A,
    BB_FILE_B,
    BB_FILE_C,
    BB_FILE_D,
    BB_FILE_E,
    BB_FILE_F,
    BB_FILE_G,
    BB_FILE_H
] = [
    BB_A1 | BB_A2 | BB_A3 | BB_A4 | BB_A5 | BB_A6 | BB_A7 | BB_A8,
    BB_B1 | BB_B2 | BB_B3 | BB_B4 | BB_B5 | BB_B6 | BB_B7 | BB_B8,
    BB_C1 | BB_C2 | BB_C3 | BB_C4 | BB_C5 | BB_C6 | BB_C7 | BB_C8,
    BB_D1 | BB_D2 | BB_D3 | BB_D4 | BB_D5 | BB_D6 | BB_D7 | BB_D8,
    BB_E1 | BB_E2 | BB_E3 | BB_E4 | BB_E5 | BB_E6 | BB_E7 | BB_E8,
    BB_F1 | BB_F2 | BB_F3 | BB_F4 | BB_F5 | BB_F6 | BB_F7 | BB_F8,
    BB_G1 | BB_G2 | BB_G3 | BB_G4 | BB_G5 | BB_G6 | BB_G7 | BB_G8,
    BB_H1 | BB_H2 | BB_H3 | BB_H4 | BB_H5 | BB_H6 | BB_H7 | BB_H8
]

BB_RANKS = [
    BB_RANK_1,
    BB_RANK_2,
    BB_RANK_3,
    BB_RANK_4,
    BB_RANK_5,
    BB_RANK_6,
    BB_RANK_7,
    BB_RANK_8
] = [
    BB_A1 | BB_B1 | BB_C1 | BB_D1 | BB_E1 | BB_F1 | BB_G1 | BB_H1,
    BB_A2 | BB_B2 | BB_C2 | BB_D2 | BB_E2 | BB_F2 | BB_G2 | BB_H2,
    BB_A3 | BB_B3 | BB_C3 | BB_D3 | BB_E3 | BB_F3 | BB_G3 | BB_H3,
    BB_A4 | BB_B4 | BB_C4 | BB_D4 | BB_E4 | BB_F4 | BB_G4 | BB_H4,
    BB_A5 | BB_B5 | BB_C5 | BB_D5 | BB_E5 | BB_F5 | BB_G5 | BB_H5,
    BB_A6 | BB_B6 | BB_C6 | BB_D6 | BB_E6 | BB_F6 | BB_G6 | BB_H6,
    BB_A7 | BB_B7 | BB_C7 | BB_D7 | BB_E7 | BB_F7 | BB_G7 | BB_H7,
    BB_A8 | BB_B8 | BB_C8 | BB_D8 | BB_E8 | BB_F8 | BB_G8 | BB_H8
]

def shift_down(b):
    return b >> 8

def shift_2_down(b):
    return b >> 16

def shift_up(b):
    return (b << 8) & BB_ALL

def shift_2_up(b):
    return (b << 16) & BB_ALL

def shift_right(b):
    return (b << 1) & ~BB_FILE_A

def shift_2_right(b):
    return (b << 2) & ~BB_FILE_A & ~BB_FILE_B

def shift_left(b):
    return (b >> 1) & ~BB_FILE_H

def shift_2_left(b):
    return (b >> 2) & ~BB_FILE_G & ~BB_FILE_H

def shift_up_left(b):
    return (b << 7) & ~BB_FILE_H

def shift_up_right(b):
    return (b << 9) & ~BB_FILE_A

def shift_down_left(b):
    return (b >> 9) & ~BB_FILE_H

def shift_down_right(b):
    return (b >> 7) & ~BB_FILE_A

def l90(b):
    mask = BB_VOID

    while b:
        square, b = next_bit(b)
        mask |= SQUARES_L90[square]

    mask

def r45(b):
    mask = BB_VOID

    while b:
        square, b = next_bit(b)
        mask |= SQUARES_R45[square]

    return mask

def l45(b):
    mask = BB_VOID

    while b:
        square, b = next_bit(b)
        mask |= SQUARES_L45[square]

BB_KNIGHT_ATTACKS = []

for bb_square in BB_SQUARES:
    mask = BB_VOID
    mask |= shift_left(shift_2_up(bb_square))
    mask |= shift_right(shift_2_up(bb_square))
    mask |= shift_left(shift_2_down(bb_square))
    mask |= shift_right(shift_2_down(bb_square))
    mask |= shift_2_left(shift_up(bb_square))
    mask |= shift_2_right(shift_up(bb_square))
    mask |= shift_2_left(shift_down(bb_square))
    mask |= shift_2_right(shift_down(bb_square))
    BB_KNIGHT_ATTACKS.append(mask & BB_ALL)

BB_KING_ATTACKS = []

for bb_square in BB_SQUARES:
    mask = BB_VOID
    mask |= shift_left(bb_square)
    mask |= shift_right(bb_square)
    mask |= shift_up(bb_square)
    mask |= shift_down(bb_square)
    mask |= shift_up_left(bb_square)
    mask |= shift_up_right(bb_square)
    mask |= shift_down_left(bb_square)
    mask |= shift_down_right(bb_square)
    BB_KING_ATTACKS.append(mask & BB_ALL)

BB_RANK_ATTACKS = [ [ BB_VOID for i in range(64) ] for k in range(64) ]

BB_FILE_ATTACKS = [ [ BB_VOID for i in range(64) ] for k in range(64) ]

for square in SQUARES:
    for bitrow in range(0, 64):
        f = file_index(square) + 1
        q = square + 1
        while f < 8:
            BB_RANK_ATTACKS[square][bitrow] |= BB_SQUARES[q]
            if (1 << f) & (bitrow << 1):
                break
            q += 1
            f += 1

        f = file_index(square) - 1
        q = square - 1
        while f >= 0:
            BB_RANK_ATTACKS[square][bitrow] |= BB_SQUARES[q]
            if (1 << f) & (bitrow << 1):
                break
            q -= 1
            f -= 1

        r = rank_index(square) + 1
        q = square + 8
        while r < 8:
            BB_FILE_ATTACKS[square][bitrow] |= BB_SQUARES[q]
            if (1 << (7 - r)) & (bitrow << 1):
                break
            q += 8
            r += 1

        r = rank_index(square) - 1
        q = square - 8
        while r >= 0:
            BB_FILE_ATTACKS[square][bitrow] |= BB_SQUARES[q]
            if (1 << (7 - r)) & (bitrow << 1):
                break
            q -= 8
            r -= 1

BB_SHIFT_R45 = [
    1, 58, 51, 44, 37, 30, 23, 16,
    9, 1, 58, 51, 44, 37, 30, 23,
    17, 9, 1, 58, 51, 44, 37, 30,
    25, 17, 9, 1, 58, 51, 44, 37,
    33, 25, 17, 9, 1, 58, 51, 44,
    41, 33, 25, 17, 9, 1, 58, 51,
    49, 41, 33, 25, 17, 9, 1, 58,
    57, 49, 41, 33, 25, 17, 9, 1 ]

BB_SHIFT_L45 = [
    9, 17, 25, 33, 41, 49, 57, 1,
    17, 25, 33, 41, 49, 57, 1, 10,
    25, 33, 41, 49, 57, 1, 10, 19,
    33, 41, 49, 57, 1, 10, 19, 28,
    41, 49, 57, 1, 10, 19, 28, 37,
    49, 57, 1, 10, 19, 28, 37, 46,
    57, 1, 10, 19, 28, 37, 46, 55,
    1, 10, 19, 28, 37, 46, 55, 64 ]

BB_L45_ATTACKS = [ [ BB_VOID for i in range(64) ] for k in range(64) ]

BB_R45_ATTACKS = [ [ BB_VOID for i in range(64) ] for k in range(64) ]

for s in SQUARES:
    for b in range(0, 64):
        mask = BB_VOID

        q = s
        while file_index(q) > 0 and rank_index(q) < 7:
            q += 7
            mask |= BB_SQUARES[q]
            if b & (BB_SQUARES_L45[q] >> BB_SHIFT_L45[s]):
                break

        q = s
        while file_index(q) < 7 and rank_index(q) > 0:
            q -= 7
            mask |= BB_SQUARES[q]
            if b & (BB_SQUARES_L45[q] >> BB_SHIFT_L45[s]):
                break

        BB_L45_ATTACKS[s][b] = mask

        mask = BB_VOID

        q = s
        while file_index(q) < 7 and rank_index(q) < 7:
            q += 9
            mask |= BB_SQUARES[q]
            if b & (BB_SQUARES_R45[q] >> BB_SHIFT_R45[s]):
                break

        q = s
        while file_index(q) > 0 and rank_index(q) > 0:
            q -= 9
            mask |= BB_SQUARES[q]
            if b & (BB_SQUARES_R45[q] >> BB_SHIFT_R45[s]):
                break

        BB_R45_ATTACKS[s][b] = mask

BB_PAWN_ATTACKS = [
    [ shift_up_left(s) | shift_up_right(s) for s in BB_SQUARES ],
    [ shift_down_left(s) | shift_down_right(s) for s in BB_SQUARES ]
]

BB_PAWN_F1 = [
    [ shift_up(s) for s in BB_SQUARES ],
    [ shift_down(s) for s in BB_SQUARES ]
]

BB_PAWN_F2 = [
    [ shift_2_up(s) for s in BB_SQUARES ],
    [ shift_2_down(s) for s in BB_SQUARES ]
]

BB_PAWN_ALL = [
    [ BB_PAWN_ATTACKS[0][i] | BB_PAWN_F1[0][i] | BB_PAWN_F2[0][i] for i in SQUARES ],
    [ BB_PAWN_ATTACKS[1][i] | BB_PAWN_F1[1][i] | BB_PAWN_F2[1][i] for i in SQUARES ]
]

def next_bit(b):
    x = b & -b
    b ^= x

    r = 0

    if not x & 0xffffffff:
        x >>= 32
        r |= 32

    if not x & 0xffff:
        x >>= 16
        r |= 16

    if not x & 0xff:
        x >>= 8
        r |= 8

    if not x & 0xf:
        x >>= 4
        r |= 4

    if not x & 0x3:
        x >>= 2
        r |= 2

    if not x & 0x1:
        r |= 1

    return r, b


def sparse_pop_count(b):
    count = 0

    while b:
        count += 1
        b &= b - 1

    return count

BYTE_POP_COUNT = [ sparse_pop_count(i) for i in range(256) ]

def pop_count(b):
    return (BYTE_POP_COUNT[  b        & 0xff ] +
            BYTE_POP_COUNT[ (b >>  8) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 16) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 24) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 32) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 40) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 48) & 0xff ] +
            BYTE_POP_COUNT[ (b >> 56) & 0xff ])


class Piece:

    def __init__(self, piece_type, color):
        self.piece_type = piece_type
        self.color = color

    def symbol(self):
        if self.color == WHITE:
            return PIECE_SYMBOLS[self.piece_type].upper()
        else:
            return PIECE_SYMBOLS[self.piece_type]

    def __hash__(self):
        return self.piece_type * (self.color + 1)

    def __repr__(self):
        return "Piece.from_symbol('{0}')".format(self.symbol())

    def __eq__(self, other):
        return self.piece_type == other.piece_type and self.color == other.color

    def __neq__(self, other):
        return self.__eq__(other)

    @classmethod
    def from_symbol(cls, symbol):
        if symbol.lower() == symbol:
            return cls(PIECE_SYMBOLS.index(symbol), BLACK)
        else:
            return cls(PIECE_SYMBOLS.index(symbol.lower()), WHITE)


class Move:

    def __init__(self, from_square, to_square, promotion=NONE):
        self.from_square = from_square
        self.to_square = to_square
        self.promotion = promotion

    def uci(self):
        return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square] + PIECE_SYMBOLS[self.promotion]

    def __eq__(self, other):
        return self.from_square == other.from_square and self.to_square == other.to_square and self.promotion == other.promotion

    def __neq__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "Move.from_uci('{0}')".format(self.uci())

    def __hash__(self):
        return self.to_square | self.from_square << 6 | self.promotion << 12

    @classmethod
    def from_uci(cls, uci):
        if len(uci) == 4:
            return cls(SQUARE_NAMES.index(uci[0:2]), SQUARE_NAMES.index(uci[2:4]))
        elif len(uci) == 5:
            promotion = PIECE_SYMBOLS.index(uci[4])
            return cls(SQUARE_NAMES.index(uci[0:2]), SQUARE_NAMES.index(uci[2:4]), promotion)
        else:
            raise ValueError("Expected UCI string to be of length 4 or 5.")


class Bitboard:

    def __init__(self, fen=None):
        if fen is None:
            self.reset()
        else:
            self.set_fen(fen)

    def reset(self):
        self.pawns = BB_RANK_2 | BB_RANK_7
        self.knights = BB_B1 | BB_G1 | BB_B8 | BB_G8
        self.bishops = BB_C1 | BB_F1 | BB_C8 | BB_F8
        self.rooks = BB_A1 | BB_H1 | BB_A8 | BB_H8
        self.queens = BB_D1 | BB_D8
        self.kings = BB_E1 | BB_E8

        self.occupied_co = [ BB_RANK_1 | BB_RANK_2, BB_RANK_7 | BB_RANK_8 ]
        self.occupied = BB_RANK_1 | BB_RANK_2 | BB_RANK_7 | BB_RANK_8

        self.occupied_l90 = BB_VOID
        self.occupied_l45 = BB_VOID
        self.occupied_r45 = BB_VOID

        self.pieces = [ ]
        self.king_squares = [ E1, E8 ]

        self.ep_square = 0
        self.castling_rights = CASTLING

        self.turn = WHITE
        self.ply = 1
        self.half_moves = 0

        for i in range(64):
            if BB_SQUARES[i] & self.occupied:
                self.occupied_l90 |= BB_SQUARES_L90[i]
                self.occupied_r45 |= BB_SQUARES_R45[i]
                self.occupied_l45 |= BB_SQUARES_L45[i]

        self.half_move_stack = collections.deque()
        self.captured_piece_stack = collections.deque()
        self.castling_right_stack = collections.deque()
        self.ep_square_stack = collections.deque()
        self.move_stack = collections.deque()

    def piece_at(self, square):
        mask = BB_SQUARES[square]
        color = int(bool(self.occupied_co[BLACK] & mask))

        if mask & self.pawns:
            return Piece(PAWN, color)
        elif mask & self.knights:
            return Piece(KNIGHT, color)
        elif mask & self.bishops:
            return Piece(BISHOP, color)
        elif mask & self.rooks:
            return Piece(ROOK, color)
        elif mask & self.queens:
            return Piece(QUEEN, color)
        elif mask & self.kings:
            return Piece(KING, color)

    def piece_type_at(self, square):
        mask = BB_SQUARES[square]

        if mask & self.pawns:
            return PAWN
        elif mask & self.knights:
            return KNIGHT
        elif mask & self.bishops:
            return BISHOP
        elif mask & self.rooks:
            return ROOK
        elif mask & self.queens:
            return QUEEN
        elif mask & self.kings:
            return KING
        else:
            return NONE

    def remove_piece_at(self, square):
        mask = BB_SQUARES[square]

        if not self.occupied & mask:
            return

        self.pawns &= ~mask
        self.knights &= ~mask
        self.bishops &= ~mask
        self.rooks &= ~mask
        self.queens &= ~mask
        self.kings &= ~mask

        color = int(bool(self.occupied_co[BLACK] & mask))

        self.occupied ^= mask
        self.occupied_co[color] ^= mask
        self.occupied_l90 ^= BB_SQUARES[SQUARES_L90[square]]
        self.occupied_r45 ^= BB_SQUARES[SQUARES_R45[square]]
        self.occupied_l45 ^= BB_SQUARES[SQUARES_L45[square]]

    def set_piece_at(self, square, piece):
        self.remove_piece_at(square)

        mask = BB_SQUARES[square]

        if piece.piece_type == PAWN:
            self.pawns |= mask
        elif piece.piece_type == KNIGHT:
            self.knights |= mask
        elif piece.piece_type == BISHOP:
            self.bishops |= mask
        elif piece.piece_type == ROOK:
            self.rooks |= mask
        elif piece.piece_type == QUEEN:
            self.queens |= mask
        elif piece.piece_type == KING:
            self.kings |= mask
            self.king_squares[piece.color] = square

        self.occupied ^= mask
        self.occupied_co[piece.color] ^= mask
        self.occupied_l90 ^= BB_SQUARES[SQUARES_L90[square]]
        self.occupied_r45 ^= BB_SQUARES[SQUARES_R45[square]]
        self.occupied_l45 ^= BB_SQUARES[SQUARES_L45[square]]

    def generate_pseudo_legal_moves(self):
        if self.turn == WHITE:
            # Castling short.
            #if self.castling_rights | CASTLING_WHITE_KINGSIDE and not (F1 | G1) & self.occupied:
            #    if not self.is_attacked_by(BLACK, E1) and not self.is_attacked_by(BLACK, F1) and not self.is_attacked_by(BLACK, G1):
            #        pass
            #        yield Move(E1, G1)

            # Castling long.
            #if self.castling_rights | CASTLING_WHITE_QUEENSIDE and not (B1 | C1 | D1) & self.occupied:
            #    if not self.is_attacked_by(BLACK, C1) and not self.is_attacked_by(BLACK, D1) and not self.is_attacked_by(BLACK, E1):
            #        yield Move(E1, C1)

            # En passant moves.
            movers = self.pawns & self.occupied_co[WHITE]
            #if self.ep_square:
            #    moves = BB_PAWN_ATTACKS[BLACK][self.ep_square] & movers
            #    while moves:
            #        from_square, moves = next_bit(moves)
            #        yield Move(from_square, self.ep_square)

            # Pawn captures.
            moves = shift_up_right(movers) & self.occupied_co[BLACK]
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square - 9
                if rank_index(to_square) != 7:
                    yield Move(from_square, to_square)
                else:
                    yield Move(from_square, to_square, QUEEN)
                    yield Move(from_square, to_square, KNIGHT)
                    yield Move(from_square, to_square, ROOK)
                    yield Move(from_square, to_square, BISHOP)

            moves = shift_up_left(movers) & self.occupied_co[BLACK]
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square - 7
                if rank_index(to_square) != 7:
                    yield Move(from_square, to_square)
                else:
                    yield Move(from_square, to_square, QUEEN)
                    yield Move(from_square, to_square, KNIGHT)
                    yield Move(from_square, to_square, ROOK)
                    yield Move(from_square, to_square, BISHOP)

            # Pawns one forward.
            moves = shift_up(movers) & ~self.occupied
            movers = moves
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square - 8
                if rank_index(to_square) != 7:
                    yield Move(from_square, to_square)
                else:
                    yield Move(from_square, to_square, QUEEN)
                    yield Move(from_square, to_square, KNIGHT)
                    yield Move(from_square, to_square, ROOK)
                    yield Move(from_square, to_square, BISHOP)

            # Pawns two forward.
            moves = shift_up(movers) & BB_RANK_4 & ~self.occupied
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square - 16
                yield Move(from_square, to_square)
        else:
            # Castling short.
            #if self.castling_rights | CASTLING_BLACK_KINGSIDE and not (F8 | G8) & self.occupied:
            #    if not self.is_attacked_by(WHITE, E8) and not self.is_attacked_by(WHITE, F8) and not self.is_attacked_by(WHITE, G8):
            #        yield Move(E8, F8)

            # Castling long.
            #if self.castling_rights | CASTLING_BLACK_QUEENSIDE and not (B8 | C8 | D8) & self.occupied:
            #    if not self.is_attacked_by(WHITE, C8) and not self.is_attacked_by(WHITE, D8) and not self.is_attacked_by(WHITE, E8):
            #        yield Move(E8, C8)

            # En passant moves.
            movers = self.pawns & self.occupied_co[BLACK]
            #if self.ep_square:
            #    moves = BB_PAWN_ATTACKS[WHITE][self.ep_square] & movers
            #    while moves:
            #        from_square, moves = next_bit(moves)
            #        yield Move(from_square, self.ep_square)

            # Pawn captures.
            moves = shift_down_left(movers) & self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square + 9
                if rank_index(to_square) != 0:
                    yield Move(from_square, to_square)
                else:
                    yield Move(from_square, to_square, QUEEN)
                    yield Move(from_square, to_square, KNIGHT)
                    yield Move(from_square, to_square, ROOK)
                    yield Move(from_square, to_square, BISHOP)

            moves = shift_down_right(movers) & self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square + 7
                if rank_index(to_square) != 0:
                    yield Move(from_square, to_square)
                else:
                    yield Move(from_square, to_square, QUEEN)
                    yield Move(from_square, to_square, KNIGHT)
                    yield Move(from_square, to_square, ROOK)
                    yield Move(from_square, to_square, BISHOP)

            # Pawns one forward.
            moves = shift_down(movers) & ~self.occupied
            movers = moves
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square + 8
                if rank_index(to_square) != 0:
                    yield Move(from_square, to_square)
                else:
                    yield Move(from_square, to_square, QUEEN)
                    yield Move(from_square, to_square, KNIGHT)
                    yield Move(from_square, to_square, ROOK)
                    yield Move(from_square, to_square, BISHOP)

            # Pawns two forward.
            moves = shift_down(movers) & BB_RANK_5 & ~self.occupied
            while moves:
                to_square, moves = next_bit(moves)
                from_square = to_square + 16
                yield Move(from_square, to_square)

        # Knight moves.
        movers = self.knights & self.occupied_co[self.turn]
        while movers:
            from_square, movers = next_bit(movers)
            moves = self.knight_attacks_from(from_square) & ~self.occupied_co[self.turn]
            while moves:
                to_square, moves = next_bit(moves)
                yield Move(from_square, to_square)

        # Bishop moves.
        movers = self.bishops & self.occupied_co[self.turn]
        while movers:
            from_square, movers = next_bit(movers)
            moves = self.bishop_attacks_from(from_square) & ~self.occupied_co[self.turn]
            while moves:
                to_square, moves = next_bit(moves)
                yield Move(from_square, to_square)

        # Rook moves.
        movers = self.rooks & self.occupied_co[self.turn]
        while movers:
            from_square, movers = next_bit(movers)
            moves = self.rook_attacks_from(from_square) & ~self.occupied_co[self.turn]
            while moves:
                to_square, moves = next_bit(moves)
                yield Move(from_square, to_square)

        # Queen moves.
        movers = self.queens & self.occupied_co[self.turn]
        while movers:
            from_square, movers = next_bit(movers)
            moves = self.queen_attacks_from(from_square) & ~self.occupied_co[self.turn]
            while moves:
                to_square, moves = next_bit(moves)
                yield Move(from_square, to_square)

        # King moves.
        from_square = self.king_squares[self.turn]
        moves = self.king_attacks_from(from_square) & ~self.occupied_co[self.turn]
        while moves:
            to_square, moves = next_bit(moves)
            yield Move(from_square, to_square)

    def is_attacked_by(self, color, square):
        if BB_PAWN_ATTACKS[color ^ 1][square] & (self.pawns | self.bishops) & self.occupied_co[color]:
            return True

        if self.knight_attacks_from(square) & self.knights & self.occupied_co[color]:
            return True

        if self.bishop_attacks_from(square) & (self.bishops | self.queens) & self.occupied_co[color]:
            return True

        if self.rook_attacks_from(square) & (self.rooks | self.queens) & self.occupied_co[color]:
            return True

        if self.king_attacks_from(square) & (self.kings | self.queens) & self.occupied_co[color]:
            return True

        return False

    def is_check(self):
        return self.is_attacked_by(self.turn ^ 1, self.king_squares[self.turn])

    def pawn_moves_from(self, square):
        targets = BB_PAWN_F1[self.turn][square] & ~self.occupied

        if targets:
            targets |= BB_PAWN_F2[self.turn][square] & ~self.occupied

        if not self.ep_square:
            targets |= BB_PAWN_ATTACKS[self.turn][square] & self.occupied_co[self.turn ^ 1]
        else:
            targets |= BB_PAWN_ATTACKS[self.turn][square] & (self.occupied_co[self.turn ^ 1] | BB_SQUARES[square])

        return targets

    def knight_attacks_from(self, square):
        return BB_KNIGHT_ATTACKS[square]

    def king_attacks_from(self, square):
        return BB_KING_ATTACKS[square]

    def rook_attacks_from(self, square):
        return (BB_RANK_ATTACKS[square][(self.occupied >> ((square & ~7) + 1)) & 63] |
                BB_FILE_ATTACKS[square][(self.occupied_l90 >> (((square & 7) << 3) + 1)) & 63])

    def bishop_attacks_from(self, square):
        return (BB_R45_ATTACKS[square][(self.occupied_r45 >> BB_SHIFT_R45[square]) & 63] |
                BB_L45_ATTACKS[square][(self.occupied_l45 >> BB_SHIFT_L45[square]) & 63])

    def queen_attacks_from(self, square):
        return self.rook_attacks_from(square) | self.bishop_attacks_from(square)

    def is_into_check(self, move):
        # TODO: Consider optimizing.
        self.push(move)
        is_check = self.was_into_check()
        self.pop()

    def was_into_check(self):
        return self.is_attacked_by(self.turn, self.king_squares[self.turn ^ 1])

    def is_not_into_check(self, move):
        return not self.is_into_check(move)

    def generate_moves(self):
        return filter(self.is_not_into_check, self.generate_pseudo_legal_moves())

    def is_checkmate(self):
        if not self.is_check():
            return False

        try:
            next(self.generate_moves().__iter__())
            return False
        except StopIteration:
            return True

    def is_stalemate(self):
        if self.is_check():
            return False

        try:
            next(self.generate_moves().__iter__())
            return False
        except StopIteration:
            return True

    def is_insufficient_material(self):
        # Enough material to mate.
        if self.pawns or self.rooks or self.queens:
            return False

        # A single knight or a single bishop.
        if sparse_pop_count(self.occupied) <= 3:
            return True

        # More than a single knight.
        if self.knights:
            return False

        # All bishops on the same color.
        if self.bishops & BB_DARK_SQUARES == 0:
            return True
        elif self.bishops & BB_LIGHT_SQUARES == 0:
            return True
        else:
            return False

    def push(self, move):
        # Increment ply.
        if self.turn == BLACK:
            self.ply += 1

        # Remember game state.
        captured_piece = self.piece_type_at(move.to_square)
        self.half_move_stack.append(self.half_moves)
        self.castling_right_stack.append(self.castling_rights)
        self.captured_piece_stack.append(captured_piece)
        self.ep_square_stack.append(self.ep_square)
        self.move_stack.append(move)

        # Update half move counter.
        piece_type = self.piece_type_at(move.from_square)
        if piece_type == PAWN or captured_piece:
            self.half_moves = 0
        else:
            self.half_moves += 1

        # Promotion.
        if move.promotion:
            piece_type = move.promotion

        # Remove piece from target square.
        self.remove_piece_at(move.from_square)

        # Set en passant square.
        # TODO: Only set if indeed possible.
        if piece_type == PAWN and abs(move.to_square - move.from_square) == 16:
            self.ep_square = move.from_square + int((move.to_square - move.from_square) / 2)
        else:
            self.ep_square = 0

        # TODO: Do castling.

        # Put piece on target square.
        self.set_piece_at(move.to_square, Piece(piece_type, self.turn))

        # Swap turn.
        self.turn ^= 1

    def pop(self):
        move = self.move_stack.pop()

        # Decrement ply.
        if self.turn == WHITE:
            self.ply -= 1

        # Restore state.
        self.half_moves = self.half_move_stack.pop()
        self.castling_rights = self.castling_right_stack.pop()
        self.ep_square = self.ep_square_stack.pop()
        captured_piece = self.captured_piece_stack.pop()
        captured_piece_color = self.turn

        # Restore the source square.
        piece = PAWN if move.promotion else self.piece_type_at(move.to_square)
        self.set_piece_at(move.from_square, Piece(piece, self.turn ^ 1))

        # Restore target square.
        if captured_piece:
            self.set_piece_at(move.to_square, Piece(captured_piece, captured_piece_color))
        else:
            self.remove_piece_at(move.to_square)

        # TODO: Restore captured pawn after en passant.

        # TODO: Restore rook position after castling.

        # Swap turn.
        self.turn ^= 1

        return move

    def set_fen(self, fen):
        # Ensure there are six parts.
        parts = fen.split()
        if len(parts) != 6:
            raise ValueError("A FEN string should consist of 6 parts.")

        # Ensure the board part is valid.
        rows = parts[0].split("/")
        if len(rows) != 8:
            raise ValueError("Expected 8 rows in position part of FEN.")

        # Validate each row.
        for row in rows:
            field_sum = 0
            previous_was_digit = False

            for c in row:
                if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                    if previous_was_digit:
                        raise ValueError("Two subsequent digits in position part of FEN.")
                    field_sum += int(c)
                    previous_was_digit = True
                elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                    field_sum += 1
                    previous_was_digit = False
                else:
                    raise ValueError("Invalid character in position part of FEN.")

            if field_sum != 8:
                raise ValueError("Expected 8 columns per row in position part of FEN.")

        # Check that the turn part is valid.
        if not parts[1] in ["w", "b"]:
            raise ValueError("Expected w or b for turn part of FEN.")

        # TODO: Check that the castling part is valid.

        # TODO: Check that the en-passant part is valid.

        # TODO: Check that the half move part is valid.

        # TODO: Check that the ply part is valid.

        # Clear board.
        self.pawns = BB_VOID
        self.knights = BB_VOID
        self.bishops = BB_VOID
        self.rooks = BB_VOID
        self.queens = BB_VOID
        self.kings = BB_VOID
        self.occupied_co = [ BB_VOID, BB_VOID ]
        self.occupied = BB_VOID
        self.occupied_l90 = BB_VOID
        self.occupied_r45 = BB_VOID
        self.occupied_l45 = BB_VOID
        self.king_squares = [ E1, E8 ]
        self.half_move_stack = collections.deque()
        self.captured_piece_stack = collections.deque()
        self.castling_right_stack = collections.deque()
        self.ep_square_stack = collections.deque()
        self.move_stack = collections.deque()

        # Put pieces on the board.
        square_index = 0
        for c in parts[0]:
            if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                square_index += int(c)
            elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                self.set_piece_at(SQUARES_180[square_index], Piece.from_symbol(c))
                square_index += 1

        # Set the turn.
        if parts[1] == "w":
            self.turn = WHITE
        else:
            self.turn = BLACK

        # Set castling flags.
        self.castling_rights = CASTLING_NONE
        if "K" in parts[2]:
            self.castling_rights |= CASTLING_WHITE_KINGSIDE
        if "Q" in parts[2]:
            self.castling_rights |= CASTLING_WHITE_QUEENSIDE
        if "k" in parts[2]:
            self.castling_rights |= CASTLING_BLACK_KINGSIDE
        if "q" in parts[2]:
            self.castling_rights |= CASTLING_BLACK_QUEENSIDE

        # Set the en-passant square.
        if parts[3] == "-":
            self.ep_square = 0
        else:
            self.ep_square = SQUARE_NAMES.index(parts[3])

        # Set the mover counters.
        self.half_moves = int(parts[4])
        self.ply = int(parts[5])

    def fen(self):
        fen = []
        empty = 0

        # Position part.
        for square in SQUARES_180:
            piece = self.piece_at(square)

            if not piece:
                empty += 1
            else:
                if empty:
                    fen.append(str(empty))
                    empty = 0
                fen.append(piece.symbol())

            if BB_SQUARES[square] & BB_FILE_H:
                if empty:
                    fen.append(str(empty))
                    empty = 0

                if square != H1:
                    fen.append("/")

        fen.append(" ")

        # Side to move.
        if self.turn == WHITE:
            fen.append("w")
        else:
            fen.append("b")

        fen.append(" ")

        # Castling rights.
        if not self.castling_rights:
            fen.append("-")
        else:
            if self.castling_rights & CASTLING_WHITE_KINGSIDE:
                fen.append("K")
            if self.castling_rights & CASTLING_WHITE_QUEENSIDE:
                fen.append("Q")
            if self.castling_rights & CASTLING_BLACK_KINGSIDE:
                fen.append("k")
            if self.castling_rights & CASTLING_BLACK_QUEENSIDE:
                fen.append("q")

        fen.append(" ")

        # En passant square.
        if self.ep_square:
            fen.append(SQUARE_NAMES[self.ep_square])
        else:
            fen.append("-")

        fen.append(" ")

        # Half moves.
        fen.append(str(self.half_moves))

        fen.append(" ")

        # Ply.
        fen.append(str(self.ply))

        return "".join(fen)

    # TODO: SAN parsing

    # TODO: SAN creation

    # TODO: Validate position

    # TODO: Validate move


def print_bitboard(bitboard):
    PIECE_CHARS = [
        [ " ", u"\u2659", u"\u2658", u"\u2657", u"\u2656", u"\u2655", u"\u2654" ],
        [ " ", u"\u265F", u"\u265e", u"\u265d", u"\u265c", u"\u265b", u"\u265a" ]
    ]

    SEQ_DARK_SQUARE = "\033[0;30;46m"
    SEQ_LIGHT_SQUARE = "\033[0;30m"
    SEQ_END = "\033[0m"

    for square in SQUARES_180:
        if BB_SQUARES[square] & BB_FILE_A:
            for border in range(square, square + 8):
                if BB_SQUARES[border] & BB_DARK_SQUARES:
                    sys.stdout.write(SEQ_DARK_SQUARE)
                else:
                    sys.stdout.write(SEQ_LIGHT_SQUARE)

                sys.stdout.write("    ")
                sys.stdout.write(SEQ_END)

            sys.stdout.write("\n")

        if BB_SQUARES[square] & BB_DARK_SQUARES:
            sys.stdout.write("\033[0;30;46m")
        else:
            sys.stdout.write("\033[0;30m")

        piece = bitboard.piece_at(square)
        if piece:
            sys.stdout.write(" ")
            sys.stdout.write(PIECE_CHARS[piece.color][piece.piece_type])
            sys.stdout.write("  ")
        else:
            sys.stdout.write("    ")

        sys.stdout.write("\033[0m")

        if BB_SQUARES[square] & BB_FILE_H:
            sys.stdout.write("\n")

    sys.stdout.flush()


def minimax_value(bitboard, depth, eval_fn):
    if bitboard.half_moves >= 50:
        return 0

    if depth == 0:
        if bitboard.is_stalemate():
            return 0
        elif bitboard.is_checkmate():
            return -1000

        return (1 - bitboard.turn * 2) * eval_fn(bitboard)

    best = None

    for move in bitboard.generate_pseudo_legal_moves():
        bitboard.push(move)

        if not bitboard.was_into_check():
            value = -1 * minimax_value(bitboard, depth - 1, eval_fn)
            if best is None or value > best:
                best = value

        bitboard.pop()

    if best is None:
        if not bitboard.is_check():
            return 0
        else:
            return -1000

    else:
        return best

def minimax(bitboard, depth, eval_fn):
    best = None

    for move in bitboard.generate_pseudo_legal_moves():
        bitboard.push(move)

        if not bitboard.was_into_check():
            value = -1 * minimax_value(bitboard, depth, eval_fn)
            if best is None or value > best[0]:
                best = (value, move)

        bitboard.pop()

    return best

def alphabeta_value(bitboard, depth, alpha, beta, eval_fn):
    if bitboard.half_moves >= 50:
        return 0

    if depth == 0:
        if bitboard.is_stalemate():
            return 0
        elif bitboard.is_checkmate():
            return -1000

        return (1 - bitboard.turn * 2) * eval_fn(bitboard)

    found_legal_move = False

    for move in bitboard.generate_pseudo_legal_moves():
        bitboard.push(move)

        if not bitboard.was_into_check():
            found_legal_move = True

            opp_alpha = None if beta is None else -1 * beta
            opp_beta = None if alpha is None else -1 * alpha

            value = -1 * alphabeta_value(bitboard, depth - 1, opp_alpha, opp_beta, eval_fn)

            if alpha is None or value > alpha:
                alpha = value

            if (alpha is not None) and (beta is not None) and alpha >= beta:
                bitboard.pop()
                return beta

        bitboard.pop()

    if not found_legal_move:
        if not bitboard.is_check():
            return 0
        else:
            return -1000
    else:
        return alpha

def alphabeta(bitboard, depth, eval_fn):
    best = None

    for move in bitboard.generate_pseudo_legal_moves():
        bitboard.push(move)

        if not bitboard.was_into_check():
            opp_beta = None if best is None else -1 * best[0]

            value = -1 * alphabeta_value(bitboard, depth, None, opp_beta, eval_fn)
            if best is None or value > best[0]:
                best = value, move

        bitboard.pop()

    return best

def material_evaluator(bitboard):
    value = 0.0

    value += pop_count(bitboard.pawns & bitboard.occupied_co[WHITE])
    value -= pop_count(bitboard.pawns & bitboard.occupied_co[BLACK])

    value += 3.0 * sparse_pop_count(bitboard.knights & bitboard.occupied_co[WHITE])
    value -= 3.0 * sparse_pop_count(bitboard.knights & bitboard.occupied_co[BLACK])

    value += 3.1 * sparse_pop_count(bitboard.bishops & bitboard.occupied_co[WHITE])
    value -= 3.1 * sparse_pop_count(bitboard.bishops & bitboard.occupied_co[BLACK])

    value += 5.0 * sparse_pop_count(bitboard.rooks & bitboard.occupied_co[WHITE])
    value -= 5.0 * sparse_pop_count(bitboard.rooks & bitboard.occupied_co[BLACK])

    value += 9.0 * sparse_pop_count(bitboard.queens & bitboard.occupied_co[WHITE])
    value -= 9.0 * sparse_pop_count(bitboard.queens & bitboard.occupied_co[BLACK])

    return value

def mobility_evaluator(bitboard):
    value = 0.0

    turn = bitboard.turn

    bitboard.turn = WHITE
    value += 0.02 * len(list(bitboard.generate_pseudo_legal_moves()))

    bitboard.turn = BLACK
    value -= 0.02 * len(list(bitboard.generate_pseudo_legal_moves()))

    bitboard.turn = turn

    return value


if __name__ == "__main__":
    sys.stdout.write("python-chess {0} by {1}\n".format(__version__, __author__))

    f = open("log.txt", "a")

    position = Bitboard()

    while True:
        line = sys.stdin.readline()
        f.write(line)
        f.flush()
        line = line.strip()
        if not line:
            continue

        if line == "uci":
            sys.stdout.write("id name python-chess {0}\n".format(__version__))
            sys.stdout.write("id author {0}\n".format(__author__))
            sys.stdout.write("uciok\n")
            sys.stdout.flush()
        elif line == "isready":
            sys.stdout.write("readyok\n")
            sys.stdout.flush()
        elif line == "quit":
            sys.exit(0)
        else:
            parts = line.split().__iter__()
            command = next(parts)

            if command == "position":
                part = next(parts)
                if part == "startpos":
                    position.reset()
                else:
                    position.set_fen(" ".join([part, next(parts), next(parts), next(parts), next(parts), next(parts)]))

                for move in parts:
                    position.push(Move.from_uci(move))
            else:
                sys.stderr.write("Unknown command: {0}\n".format(line))
                sys.stderr.flush()
