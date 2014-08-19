# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

__author__ = "Niklas Fiekas"

__email__ = "niklas.fiekas@tu-clausthal.de"

__version__ = "0.4.0"

import collections
import re


COLORS = [ WHITE, BLACK ] = range(2)

PIECE_TYPES = [ NONE, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING ] = range(7)

PIECE_SYMBOLS = [ "", "p", "n", "b", "r", "q", "k" ]

FILE_NAMES = [ "a", "b", "c", "d", "e", "f", "g", "h" ]

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
"""The FEN notation of the standard chess starting position."""

STATUS_VALID = 0
STATUS_NO_WHITE_KING = 1
STATUS_NO_BLACK_KING = 2
STATUS_TOO_MANY_KINGS = 4
STATUS_TOO_MANY_WHITE_PAWNS = 8
STATUS_TOO_MANY_BLACK_PAWNS = 16
STATUS_PAWNS_ON_BACKRANK = 32
STATUS_TOO_MANY_WHITE_PIECES = 64
STATUS_TOO_MANY_BLACK_PIECES = 128
STATUS_BAD_CASTLING_RIGHTS = 256
STATUS_INVALID_EP_SQUARE = 512
STATUS_OPPOSITE_CHECK = 1024

SAN_REGEX = re.compile("^([NBKRQ])?([a-h])?([1-8])?x?([a-h][1-8])(=[nbrqNBRQ])?(\\+|#)?$")

FEN_CASTLING_REGEX = re.compile("^(KQ?k?q?|Qk?q?|kq?|q|-)$")

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
    """Gets the file index of square where `0` is the a file."""
    return square & 7

def rank_index(square):
    """Gets the rank index of the square where `0` is the first rank."""
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
        mask |= BB_SQUARES_L90[square]

    return mask

def r45(b):
    mask = BB_VOID

    while b:
        square, b = next_bit(b)
        mask |= BB_SQUARES_R45[square]

    return mask

def l45(b):
    mask = BB_VOID

    while b:
        square, b = next_bit(b)
        mask |= BB_SQUARES_L45[square]

    return mask

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


POLYGLOT_RANDOM_ARRAY = [
    0x9D39247E33776D41, 0x2AF7398005AAA5C7, 0x44DB015024623547, 0x9C15F73E62A76AE2,
    0x75834465489C0C89, 0x3290AC3A203001BF, 0x0FBBAD1F61042279, 0xE83A908FF2FB60CA,
    0x0D7E765D58755C10, 0x1A083822CEAFE02D, 0x9605D5F0E25EC3B0, 0xD021FF5CD13A2ED5,
    0x40BDF15D4A672E32, 0x011355146FD56395, 0x5DB4832046F3D9E5, 0x239F8B2D7FF719CC,
    0x05D1A1AE85B49AA1, 0x679F848F6E8FC971, 0x7449BBFF801FED0B, 0x7D11CDB1C3B7ADF0,
    0x82C7709E781EB7CC, 0xF3218F1C9510786C, 0x331478F3AF51BBE6, 0x4BB38DE5E7219443,
    0xAA649C6EBCFD50FC, 0x8DBD98A352AFD40B, 0x87D2074B81D79217, 0x19F3C751D3E92AE1,
    0xB4AB30F062B19ABF, 0x7B0500AC42047AC4, 0xC9452CA81A09D85D, 0x24AA6C514DA27500,
    0x4C9F34427501B447, 0x14A68FD73C910841, 0xA71B9B83461CBD93, 0x03488B95B0F1850F,
    0x637B2B34FF93C040, 0x09D1BC9A3DD90A94, 0x3575668334A1DD3B, 0x735E2B97A4C45A23,
    0x18727070F1BD400B, 0x1FCBACD259BF02E7, 0xD310A7C2CE9B6555, 0xBF983FE0FE5D8244,
    0x9F74D14F7454A824, 0x51EBDC4AB9BA3035, 0x5C82C505DB9AB0FA, 0xFCF7FE8A3430B241,
    0x3253A729B9BA3DDE, 0x8C74C368081B3075, 0xB9BC6C87167C33E7, 0x7EF48F2B83024E20,
    0x11D505D4C351BD7F, 0x6568FCA92C76A243, 0x4DE0B0F40F32A7B8, 0x96D693460CC37E5D,
    0x42E240CB63689F2F, 0x6D2BDCDAE2919661, 0x42880B0236E4D951, 0x5F0F4A5898171BB6,
    0x39F890F579F92F88, 0x93C5B5F47356388B, 0x63DC359D8D231B78, 0xEC16CA8AEA98AD76,
    0x5355F900C2A82DC7, 0x07FB9F855A997142, 0x5093417AA8A7ED5E, 0x7BCBC38DA25A7F3C,
    0x19FC8A768CF4B6D4, 0x637A7780DECFC0D9, 0x8249A47AEE0E41F7, 0x79AD695501E7D1E8,
    0x14ACBAF4777D5776, 0xF145B6BECCDEA195, 0xDABF2AC8201752FC, 0x24C3C94DF9C8D3F6,
    0xBB6E2924F03912EA, 0x0CE26C0B95C980D9, 0xA49CD132BFBF7CC4, 0xE99D662AF4243939,
    0x27E6AD7891165C3F, 0x8535F040B9744FF1, 0x54B3F4FA5F40D873, 0x72B12C32127FED2B,
    0xEE954D3C7B411F47, 0x9A85AC909A24EAA1, 0x70AC4CD9F04F21F5, 0xF9B89D3E99A075C2,
    0x87B3E2B2B5C907B1, 0xA366E5B8C54F48B8, 0xAE4A9346CC3F7CF2, 0x1920C04D47267BBD,
    0x87BF02C6B49E2AE9, 0x092237AC237F3859, 0xFF07F64EF8ED14D0, 0x8DE8DCA9F03CC54E,
    0x9C1633264DB49C89, 0xB3F22C3D0B0B38ED, 0x390E5FB44D01144B, 0x5BFEA5B4712768E9,
    0x1E1032911FA78984, 0x9A74ACB964E78CB3, 0x4F80F7A035DAFB04, 0x6304D09A0B3738C4,
    0x2171E64683023A08, 0x5B9B63EB9CEFF80C, 0x506AACF489889342, 0x1881AFC9A3A701D6,
    0x6503080440750644, 0xDFD395339CDBF4A7, 0xEF927DBCF00C20F2, 0x7B32F7D1E03680EC,
    0xB9FD7620E7316243, 0x05A7E8A57DB91B77, 0xB5889C6E15630A75, 0x4A750A09CE9573F7,
    0xCF464CEC899A2F8A, 0xF538639CE705B824, 0x3C79A0FF5580EF7F, 0xEDE6C87F8477609D,
    0x799E81F05BC93F31, 0x86536B8CF3428A8C, 0x97D7374C60087B73, 0xA246637CFF328532,
    0x043FCAE60CC0EBA0, 0x920E449535DD359E, 0x70EB093B15B290CC, 0x73A1921916591CBD,
    0x56436C9FE1A1AA8D, 0xEFAC4B70633B8F81, 0xBB215798D45DF7AF, 0x45F20042F24F1768,
    0x930F80F4E8EB7462, 0xFF6712FFCFD75EA1, 0xAE623FD67468AA70, 0xDD2C5BC84BC8D8FC,
    0x7EED120D54CF2DD9, 0x22FE545401165F1C, 0xC91800E98FB99929, 0x808BD68E6AC10365,
    0xDEC468145B7605F6, 0x1BEDE3A3AEF53302, 0x43539603D6C55602, 0xAA969B5C691CCB7A,
    0xA87832D392EFEE56, 0x65942C7B3C7E11AE, 0xDED2D633CAD004F6, 0x21F08570F420E565,
    0xB415938D7DA94E3C, 0x91B859E59ECB6350, 0x10CFF333E0ED804A, 0x28AED140BE0BB7DD,
    0xC5CC1D89724FA456, 0x5648F680F11A2741, 0x2D255069F0B7DAB3, 0x9BC5A38EF729ABD4,
    0xEF2F054308F6A2BC, 0xAF2042F5CC5C2858, 0x480412BAB7F5BE2A, 0xAEF3AF4A563DFE43,
    0x19AFE59AE451497F, 0x52593803DFF1E840, 0xF4F076E65F2CE6F0, 0x11379625747D5AF3,
    0xBCE5D2248682C115, 0x9DA4243DE836994F, 0x066F70B33FE09017, 0x4DC4DE189B671A1C,
    0x51039AB7712457C3, 0xC07A3F80C31FB4B4, 0xB46EE9C5E64A6E7C, 0xB3819A42ABE61C87,
    0x21A007933A522A20, 0x2DF16F761598AA4F, 0x763C4A1371B368FD, 0xF793C46702E086A0,
    0xD7288E012AEB8D31, 0xDE336A2A4BC1C44B, 0x0BF692B38D079F23, 0x2C604A7A177326B3,
    0x4850E73E03EB6064, 0xCFC447F1E53C8E1B, 0xB05CA3F564268D99, 0x9AE182C8BC9474E8,
    0xA4FC4BD4FC5558CA, 0xE755178D58FC4E76, 0x69B97DB1A4C03DFE, 0xF9B5B7C4ACC67C96,
    0xFC6A82D64B8655FB, 0x9C684CB6C4D24417, 0x8EC97D2917456ED0, 0x6703DF9D2924E97E,
    0xC547F57E42A7444E, 0x78E37644E7CAD29E, 0xFE9A44E9362F05FA, 0x08BD35CC38336615,
    0x9315E5EB3A129ACE, 0x94061B871E04DF75, 0xDF1D9F9D784BA010, 0x3BBA57B68871B59D,
    0xD2B7ADEEDED1F73F, 0xF7A255D83BC373F8, 0xD7F4F2448C0CEB81, 0xD95BE88CD210FFA7,
    0x336F52F8FF4728E7, 0xA74049DAC312AC71, 0xA2F61BB6E437FDB5, 0x4F2A5CB07F6A35B3,
    0x87D380BDA5BF7859, 0x16B9F7E06C453A21, 0x7BA2484C8A0FD54E, 0xF3A678CAD9A2E38C,
    0x39B0BF7DDE437BA2, 0xFCAF55C1BF8A4424, 0x18FCF680573FA594, 0x4C0563B89F495AC3,
    0x40E087931A00930D, 0x8CFFA9412EB642C1, 0x68CA39053261169F, 0x7A1EE967D27579E2,
    0x9D1D60E5076F5B6F, 0x3810E399B6F65BA2, 0x32095B6D4AB5F9B1, 0x35CAB62109DD038A,
    0xA90B24499FCFAFB1, 0x77A225A07CC2C6BD, 0x513E5E634C70E331, 0x4361C0CA3F692F12,
    0xD941ACA44B20A45B, 0x528F7C8602C5807B, 0x52AB92BEB9613989, 0x9D1DFA2EFC557F73,
    0x722FF175F572C348, 0x1D1260A51107FE97, 0x7A249A57EC0C9BA2, 0x04208FE9E8F7F2D6,
    0x5A110C6058B920A0, 0x0CD9A497658A5698, 0x56FD23C8F9715A4C, 0x284C847B9D887AAE,
    0x04FEABFBBDB619CB, 0x742E1E651C60BA83, 0x9A9632E65904AD3C, 0x881B82A13B51B9E2,
    0x506E6744CD974924, 0xB0183DB56FFC6A79, 0x0ED9B915C66ED37E, 0x5E11E86D5873D484,
    0xF678647E3519AC6E, 0x1B85D488D0F20CC5, 0xDAB9FE6525D89021, 0x0D151D86ADB73615,
    0xA865A54EDCC0F019, 0x93C42566AEF98FFB, 0x99E7AFEABE000731, 0x48CBFF086DDF285A,
    0x7F9B6AF1EBF78BAF, 0x58627E1A149BBA21, 0x2CD16E2ABD791E33, 0xD363EFF5F0977996,
    0x0CE2A38C344A6EED, 0x1A804AADB9CFA741, 0x907F30421D78C5DE, 0x501F65EDB3034D07,
    0x37624AE5A48FA6E9, 0x957BAF61700CFF4E, 0x3A6C27934E31188A, 0xD49503536ABCA345,
    0x088E049589C432E0, 0xF943AEE7FEBF21B8, 0x6C3B8E3E336139D3, 0x364F6FFA464EE52E,
    0xD60F6DCEDC314222, 0x56963B0DCA418FC0, 0x16F50EDF91E513AF, 0xEF1955914B609F93,
    0x565601C0364E3228, 0xECB53939887E8175, 0xBAC7A9A18531294B, 0xB344C470397BBA52,
    0x65D34954DAF3CEBD, 0xB4B81B3FA97511E2, 0xB422061193D6F6A7, 0x071582401C38434D,
    0x7A13F18BBEDC4FF5, 0xBC4097B116C524D2, 0x59B97885E2F2EA28, 0x99170A5DC3115544,
    0x6F423357E7C6A9F9, 0x325928EE6E6F8794, 0xD0E4366228B03343, 0x565C31F7DE89EA27,
    0x30F5611484119414, 0xD873DB391292ED4F, 0x7BD94E1D8E17DEBC, 0xC7D9F16864A76E94,
    0x947AE053EE56E63C, 0xC8C93882F9475F5F, 0x3A9BF55BA91F81CA, 0xD9A11FBB3D9808E4,
    0x0FD22063EDC29FCA, 0xB3F256D8ACA0B0B9, 0xB03031A8B4516E84, 0x35DD37D5871448AF,
    0xE9F6082B05542E4E, 0xEBFAFA33D7254B59, 0x9255ABB50D532280, 0xB9AB4CE57F2D34F3,
    0x693501D628297551, 0xC62C58F97DD949BF, 0xCD454F8F19C5126A, 0xBBE83F4ECC2BDECB,
    0xDC842B7E2819E230, 0xBA89142E007503B8, 0xA3BC941D0A5061CB, 0xE9F6760E32CD8021,
    0x09C7E552BC76492F, 0x852F54934DA55CC9, 0x8107FCCF064FCF56, 0x098954D51FFF6580,
    0x23B70EDB1955C4BF, 0xC330DE426430F69D, 0x4715ED43E8A45C0A, 0xA8D7E4DAB780A08D,
    0x0572B974F03CE0BB, 0xB57D2E985E1419C7, 0xE8D9ECBE2CF3D73F, 0x2FE4B17170E59750,
    0x11317BA87905E790, 0x7FBF21EC8A1F45EC, 0x1725CABFCB045B00, 0x964E915CD5E2B207,
    0x3E2B8BCBF016D66D, 0xBE7444E39328A0AC, 0xF85B2B4FBCDE44B7, 0x49353FEA39BA63B1,
    0x1DD01AAFCD53486A, 0x1FCA8A92FD719F85, 0xFC7C95D827357AFA, 0x18A6A990C8B35EBD,
    0xCCCB7005C6B9C28D, 0x3BDBB92C43B17F26, 0xAA70B5B4F89695A2, 0xE94C39A54A98307F,
    0xB7A0B174CFF6F36E, 0xD4DBA84729AF48AD, 0x2E18BC1AD9704A68, 0x2DE0966DAF2F8B1C,
    0xB9C11D5B1E43A07E, 0x64972D68DEE33360, 0x94628D38D0C20584, 0xDBC0D2B6AB90A559,
    0xD2733C4335C6A72F, 0x7E75D99D94A70F4D, 0x6CED1983376FA72B, 0x97FCAACBF030BC24,
    0x7B77497B32503B12, 0x8547EDDFB81CCB94, 0x79999CDFF70902CB, 0xCFFE1939438E9B24,
    0x829626E3892D95D7, 0x92FAE24291F2B3F1, 0x63E22C147B9C3403, 0xC678B6D860284A1C,
    0x5873888850659AE7, 0x0981DCD296A8736D, 0x9F65789A6509A440, 0x9FF38FED72E9052F,
    0xE479EE5B9930578C, 0xE7F28ECD2D49EECD, 0x56C074A581EA17FE, 0x5544F7D774B14AEF,
    0x7B3F0195FC6F290F, 0x12153635B2C0CF57, 0x7F5126DBBA5E0CA7, 0x7A76956C3EAFB413,
    0x3D5774A11D31AB39, 0x8A1B083821F40CB4, 0x7B4A38E32537DF62, 0x950113646D1D6E03,
    0x4DA8979A0041E8A9, 0x3BC36E078F7515D7, 0x5D0A12F27AD310D1, 0x7F9D1A2E1EBE1327,
    0xDA3A361B1C5157B1, 0xDCDD7D20903D0C25, 0x36833336D068F707, 0xCE68341F79893389,
    0xAB9090168DD05F34, 0x43954B3252DC25E5, 0xB438C2B67F98E5E9, 0x10DCD78E3851A492,
    0xDBC27AB5447822BF, 0x9B3CDB65F82CA382, 0xB67B7896167B4C84, 0xBFCED1B0048EAC50,
    0xA9119B60369FFEBD, 0x1FFF7AC80904BF45, 0xAC12FB171817EEE7, 0xAF08DA9177DDA93D,
    0x1B0CAB936E65C744, 0xB559EB1D04E5E932, 0xC37B45B3F8D6F2BA, 0xC3A9DC228CAAC9E9,
    0xF3B8B6675A6507FF, 0x9FC477DE4ED681DA, 0x67378D8ECCEF96CB, 0x6DD856D94D259236,
    0xA319CE15B0B4DB31, 0x073973751F12DD5E, 0x8A8E849EB32781A5, 0xE1925C71285279F5,
    0x74C04BF1790C0EFE, 0x4DDA48153C94938A, 0x9D266D6A1CC0542C, 0x7440FB816508C4FE,
    0x13328503DF48229F, 0xD6BF7BAEE43CAC40, 0x4838D65F6EF6748F, 0x1E152328F3318DEA,
    0x8F8419A348F296BF, 0x72C8834A5957B511, 0xD7A023A73260B45C, 0x94EBC8ABCFB56DAE,
    0x9FC10D0F989993E0, 0xDE68A2355B93CAE6, 0xA44CFE79AE538BBE, 0x9D1D84FCCE371425,
    0x51D2B1AB2DDFB636, 0x2FD7E4B9E72CD38C, 0x65CA5B96B7552210, 0xDD69A0D8AB3B546D,
    0x604D51B25FBF70E2, 0x73AA8A564FB7AC9E, 0x1A8C1E992B941148, 0xAAC40A2703D9BEA0,
    0x764DBEAE7FA4F3A6, 0x1E99B96E70A9BE8B, 0x2C5E9DEB57EF4743, 0x3A938FEE32D29981,
    0x26E6DB8FFDF5ADFE, 0x469356C504EC9F9D, 0xC8763C5B08D1908C, 0x3F6C6AF859D80055,
    0x7F7CC39420A3A545, 0x9BFB227EBDF4C5CE, 0x89039D79D6FC5C5C, 0x8FE88B57305E2AB6,
    0xA09E8C8C35AB96DE, 0xFA7E393983325753, 0xD6B6D0ECC617C699, 0xDFEA21EA9E7557E3,
    0xB67C1FA481680AF8, 0xCA1E3785A9E724E5, 0x1CFC8BED0D681639, 0xD18D8549D140CAEA,
    0x4ED0FE7E9DC91335, 0xE4DBF0634473F5D2, 0x1761F93A44D5AEFE, 0x53898E4C3910DA55,
    0x734DE8181F6EC39A, 0x2680B122BAA28D97, 0x298AF231C85BAFAB, 0x7983EED3740847D5,
    0x66C1A2A1A60CD889, 0x9E17E49642A3E4C1, 0xEDB454E7BADC0805, 0x50B704CAB602C329,
    0x4CC317FB9CDDD023, 0x66B4835D9EAFEA22, 0x219B97E26FFC81BD, 0x261E4E4C0A333A9D,
    0x1FE2CCA76517DB90, 0xD7504DFA8816EDBB, 0xB9571FA04DC089C8, 0x1DDC0325259B27DE,
    0xCF3F4688801EB9AA, 0xF4F5D05C10CAB243, 0x38B6525C21A42B0E, 0x36F60E2BA4FA6800,
    0xEB3593803173E0CE, 0x9C4CD6257C5A3603, 0xAF0C317D32ADAA8A, 0x258E5A80C7204C4B,
    0x8B889D624D44885D, 0xF4D14597E660F855, 0xD4347F66EC8941C3, 0xE699ED85B0DFB40D,
    0x2472F6207C2D0484, 0xC2A1E7B5B459AEB5, 0xAB4F6451CC1D45EC, 0x63767572AE3D6174,
    0xA59E0BD101731A28, 0x116D0016CB948F09, 0x2CF9C8CA052F6E9F, 0x0B090A7560A968E3,
    0xABEEDDB2DDE06FF1, 0x58EFC10B06A2068D, 0xC6E57A78FBD986E0, 0x2EAB8CA63CE802D7,
    0x14A195640116F336, 0x7C0828DD624EC390, 0xD74BBE77E6116AC7, 0x804456AF10F5FB53,
    0xEBE9EA2ADF4321C7, 0x03219A39EE587A30, 0x49787FEF17AF9924, 0xA1E9300CD8520548,
    0x5B45E522E4B1B4EF, 0xB49C3B3995091A36, 0xD4490AD526F14431, 0x12A8F216AF9418C2,
    0x001F837CC7350524, 0x1877B51E57A764D5, 0xA2853B80F17F58EE, 0x993E1DE72D36D310,
    0xB3598080CE64A656, 0x252F59CF0D9F04BB, 0xD23C8E176D113600, 0x1BDA0492E7E4586E,
    0x21E0BD5026C619BF, 0x3B097ADAF088F94E, 0x8D14DEDB30BE846E, 0xF95CFFA23AF5F6F4,
    0x3871700761B3F743, 0xCA672B91E9E4FA16, 0x64C8E531BFF53B55, 0x241260ED4AD1E87D,
    0x106C09B972D2E822, 0x7FBA195410E5CA30, 0x7884D9BC6CB569D8, 0x0647DFEDCD894A29,
    0x63573FF03E224774, 0x4FC8E9560F91B123, 0x1DB956E450275779, 0xB8D91274B9E9D4FB,
    0xA2EBEE47E2FBFCE1, 0xD9F1F30CCD97FB09, 0xEFED53D75FD64E6B, 0x2E6D02C36017F67F,
    0xA9AA4D20DB084E9B, 0xB64BE8D8B25396C1, 0x70CB6AF7C2D5BCF0, 0x98F076A4F7A2322E,
    0xBF84470805E69B5F, 0x94C3251F06F90CF3, 0x3E003E616A6591E9, 0xB925A6CD0421AFF3,
    0x61BDD1307C66E300, 0xBF8D5108E27E0D48, 0x240AB57A8B888B20, 0xFC87614BAF287E07,
    0xEF02CDD06FFDB432, 0xA1082C0466DF6C0A, 0x8215E577001332C8, 0xD39BB9C3A48DB6CF,
    0x2738259634305C14, 0x61CF4F94C97DF93D, 0x1B6BACA2AE4E125B, 0x758F450C88572E0B,
    0x959F587D507A8359, 0xB063E962E045F54D, 0x60E8ED72C0DFF5D1, 0x7B64978555326F9F,
    0xFD080D236DA814BA, 0x8C90FD9B083F4558, 0x106F72FE81E2C590, 0x7976033A39F7D952,
    0xA4EC0132764CA04B, 0x733EA705FAE4FA77, 0xB4D8F77BC3E56167, 0x9E21F4F903B33FD9,
    0x9D765E419FB69F6D, 0xD30C088BA61EA5EF, 0x5D94337FBFAF7F5B, 0x1A4E4822EB4D7A59,
    0x6FFE73E81B637FB3, 0xDDF957BC36D8B9CA, 0x64D0E29EEA8838B3, 0x08DD9BDFD96B9F63,
    0x087E79E5A57D1D13, 0xE328E230E3E2B3FB, 0x1C2559E30F0946BE, 0x720BF5F26F4D2EAA,
    0xB0774D261CC609DB, 0x443F64EC5A371195, 0x4112CF68649A260E, 0xD813F2FAB7F5C5CA,
    0x660D3257380841EE, 0x59AC2C7873F910A3, 0xE846963877671A17, 0x93B633ABFA3469F8,
    0xC0C0F5A60EF4CDCF, 0xCAF21ECD4377B28C, 0x57277707199B8175, 0x506C11B9D90E8B1D,
    0xD83CC2687A19255F, 0x4A29C6465A314CD1, 0xED2DF21216235097, 0xB5635C95FF7296E2,
    0x22AF003AB672E811, 0x52E762596BF68235, 0x9AEBA33AC6ECC6B0, 0x944F6DE09134DFB6,
    0x6C47BEC883A7DE39, 0x6AD047C430A12104, 0xA5B1CFDBA0AB4067, 0x7C45D833AFF07862,
    0x5092EF950A16DA0B, 0x9338E69C052B8E7B, 0x455A4B4CFE30E3F5, 0x6B02E63195AD0CF8,
    0x6B17B224BAD6BF27, 0xD1E0CCD25BB9C169, 0xDE0C89A556B9AE70, 0x50065E535A213CF6,
    0x9C1169FA2777B874, 0x78EDEFD694AF1EED, 0x6DC93D9526A50E68, 0xEE97F453F06791ED,
    0x32AB0EDB696703D3, 0x3A6853C7E70757A7, 0x31865CED6120F37D, 0x67FEF95D92607890,
    0x1F2B1D1F15F6DC9C, 0xB69E38A8965C6B65, 0xAA9119FF184CCCF4, 0xF43C732873F24C13,
    0xFB4A3D794A9A80D2, 0x3550C2321FD6109C, 0x371F77E76BB8417E, 0x6BFA9AAE5EC05779,
    0xCD04F3FF001A4778, 0xE3273522064480CA, 0x9F91508BFFCFC14A, 0x049A7F41061A9E60,
    0xFCB6BE43A9F2FE9B, 0x08DE8A1C7797DA9B, 0x8F9887E6078735A1, 0xB5B4071DBFC73A66,
    0x230E343DFBA08D33, 0x43ED7F5A0FAE657D, 0x3A88A0FBBCB05C63, 0x21874B8B4D2DBC4F,
    0x1BDEA12E35F6A8C9, 0x53C065C6C8E63528, 0xE34A1D250E7A8D6B, 0xD6B04D3B7651DD7E,
    0x5E90277E7CB39E2D, 0x2C046F22062DC67D, 0xB10BB459132D0A26, 0x3FA9DDFB67E2F199,
    0x0E09B88E1914F7AF, 0x10E8B35AF3EEAB37, 0x9EEDECA8E272B933, 0xD4C718BC4AE8AE5F,
    0x81536D601170FC20, 0x91B534F885818A06, 0xEC8177F83F900978, 0x190E714FADA5156E,
    0xB592BF39B0364963, 0x89C350C893AE7DC1, 0xAC042E70F8B383F2, 0xB49B52E587A1EE60,
    0xFB152FE3FF26DA89, 0x3E666E6F69AE2C15, 0x3B544EBE544C19F9, 0xE805A1E290CF2456,
    0x24B33C9D7ED25117, 0xE74733427B72F0C1, 0x0A804D18B7097475, 0x57E3306D881EDB4F,
    0x4AE7D6A36EB5DBCB, 0x2D8D5432157064C8, 0xD1E649DE1E7F268B, 0x8A328A1CEDFE552C,
    0x07A3AEC79624C7DA, 0x84547DDC3E203C94, 0x990A98FD5071D263, 0x1A4FF12616EEFC89,
    0xF6F7FD1431714200, 0x30C05B1BA332F41C, 0x8D2636B81555A786, 0x46C9FEB55D120902,
    0xCCEC0A73B49C9921, 0x4E9D2827355FC492, 0x19EBB029435DCB0F, 0x4659D2B743848A2C,
    0x963EF2C96B33BE31, 0x74F85198B05A2E7D, 0x5A0F544DD2B1FB18, 0x03727073C2E134B1,
    0xC7F6AA2DE59AEA61, 0x352787BAA0D7C22F, 0x9853EAB63B5E0B35, 0xABBDCDD7ED5C0860,
    0xCF05DAF5AC8D77B0, 0x49CAD48CEBF4A71E, 0x7A4C10EC2158C4A6, 0xD9E92AA246BF719E,
    0x13AE978D09FE5557, 0x730499AF921549FF, 0x4E4B705B92903BA4, 0xFF577222C14F0A3A,
    0x55B6344CF97AAFAE, 0xB862225B055B6960, 0xCAC09AFBDDD2CDB4, 0xDAF8E9829FE96B5F,
    0xB5FDFC5D3132C498, 0x310CB380DB6F7503, 0xE87FBB46217A360E, 0x2102AE466EBB1148,
    0xF8549E1A3AA5E00D, 0x07A69AFDCC42261A, 0xC4C118BFE78FEAAE, 0xF9F4892ED96BD438,
    0x1AF3DBE25D8F45DA, 0xF5B4B0B0D2DEEEB4, 0x962ACEEFA82E1C84, 0x046E3ECAAF453CE9,
    0xF05D129681949A4C, 0x964781CE734B3C84, 0x9C2ED44081CE5FBD, 0x522E23F3925E319E,
    0x177E00F9FC32F791, 0x2BC60A63A6F3B3F2, 0x222BBFAE61725606, 0x486289DDCC3D6780,
    0x7DC7785B8EFDFC80, 0x8AF38731C02BA980, 0x1FAB64EA29A2DDF7, 0xE4D9429322CD065A,
    0x9DA058C67844F20C, 0x24C0E332B70019B0, 0x233003B5A6CFE6AD, 0xD586BD01C5C217F6,
    0x5E5637885F29BC2B, 0x7EBA726D8C94094B, 0x0A56A5F0BFE39272, 0xD79476A84EE20D06,
    0x9E4C1269BAA4BF37, 0x17EFEE45B0DEE640, 0x1D95B0A5FCF90BC6, 0x93CBE0B699C2585D,
    0x65FA4F227A2B6D79, 0xD5F9E858292504D5, 0xC2B5A03F71471A6F, 0x59300222B4561E00,
    0xCE2F8642CA0712DC, 0x7CA9723FBB2E8988, 0x2785338347F2BA08, 0xC61BB3A141E50E8C,
    0x150F361DAB9DEC26, 0x9F6A419D382595F4, 0x64A53DC924FE7AC9, 0x142DE49FFF7A7C3D,
    0x0C335248857FA9E7, 0x0A9C32D5EAE45305, 0xE6C42178C4BBB92E, 0x71F1CE2490D20B07,
    0xF1BCC3D275AFE51A, 0xE728E8C83C334074, 0x96FBF83A12884624, 0x81A1549FD6573DA5,
    0x5FA7867CAF35E149, 0x56986E2EF3ED091B, 0x917F1DD5F8886C61, 0xD20D8C88C8FFE65F,
    0x31D71DCE64B2C310, 0xF165B587DF898190, 0xA57E6339DD2CF3A0, 0x1EF6E6DBB1961EC9,
    0x70CC73D90BC26E24, 0xE21A6B35DF0C3AD7, 0x003A93D8B2806962, 0x1C99DED33CB890A1,
    0xCF3145DE0ADD4289, 0xD0E4427A5514FB72, 0x77C621CC9FB3A483, 0x67A34DAC4356550B,
    0xF8D626AAAF278509
]


class Piece(object):
    """A piece with type and color."""

    def __init__(self, piece_type, color):
        self.piece_type = piece_type
        self.color = color

    def symbol(self):
        """
        Gets the symbol `P`, `N`, `B`, `R`, `Q` or `K` for white pieces or the
        lower-case variants for the black pieces.
        """
        if self.color == WHITE:
            return PIECE_SYMBOLS[self.piece_type].upper()
        else:
            return PIECE_SYMBOLS[self.piece_type]

    def __hash__(self):
        return self.piece_type * (self.color + 1)

    def __repr__(self):
        return "Piece.from_symbol('{0}')".format(self.symbol())

    def __str__(self):
        return self.symbol()

    def __eq__(self, other):
        try:
            return self.piece_type == other.piece_type and self.color == other.color
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_symbol(cls, symbol):
        """
        Creates a piece instance from a piece symbol.

        Raises `ValueError` if the symbol is invalid.
        """
        if symbol.lower() == symbol:
            return cls(PIECE_SYMBOLS.index(symbol), BLACK)
        else:
            return cls(PIECE_SYMBOLS.index(symbol.lower()), WHITE)


class Move(object):
    """
    Represents a move from a square to a square and possibly the promotion piece
    type.

    Castling moves are identified only by the movement of the king.

    Null moves are supported.
    """

    def __init__(self, from_square, to_square, promotion=NONE):
        self.from_square = from_square
        self.to_square = to_square
        self.promotion = promotion

    def uci(self):
        """
        Gets an UCI string for the move.

        For example a move from A7 to A8 would be `a7a8` or `a7a8q` if it is
        a promotion to a queen. The UCI representatin of null moves is `0000`.
        """
        if self:
            return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square] + PIECE_SYMBOLS[self.promotion]
        else:
            return "0000"

    def __bool__(self):
        return bool(self.from_square or self.to_square or self.promotion)

    def __nonzero__(self):
        return self.from_square or self.to_square or self.promotion

    def __eq__(self, other):
        try:
            return self.from_square == other.from_square and self.to_square == other.to_square and self.promotion == other.promotion
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "Move.from_uci('{0}')".format(self.uci())

    def __str__(self):
        return self.uci()

    def __hash__(self):
        return self.to_square | self.from_square << 6 | self.promotion << 12

    @classmethod
    def from_uci(cls, uci):
        """
        Parses an UCI string.

        Raises `ValueError` if the UCI string is invalid.
        """
        if uci == "0000":
            return cls.null()
        elif len(uci) == 4:
            return cls(SQUARE_NAMES.index(uci[0:2]), SQUARE_NAMES.index(uci[2:4]))
        elif len(uci) == 5:
            promotion = PIECE_SYMBOLS.index(uci[4])
            return cls(SQUARE_NAMES.index(uci[0:2]), SQUARE_NAMES.index(uci[2:4]), promotion)
        else:
            raise ValueError("expected uci string to be of length 4 or 5")

    @classmethod
    def null(cls):
        """
        Gets a null move.

        A null move just passes the turn to the other side (and possibly
        forfeits en-passant capturing). Null moves evaluate to `False` in
        boolean contexts.

        >>> bool(chess.Move.null())
        False
        """
        return cls(0, 0, NONE)


class Bitboard(object):
    """
    A bitboard and additional information representing a position.

    Provides move generation, validation, parsing, attack generation,
    game end detection, move counters and the capability to make and unmake
    moves.

    The bitboard is initialized to the starting position, unless otherwise
    specified in the optional `fen` argument.
    """

    def __init__(self, fen=None):
        self.pseudo_legal_moves = PseudoLegalMoveGenerator(self)
        self.legal_moves = LegalMoveGenerator(self)

        if fen is None:
            self.reset()
        else:
            self.set_fen(fen)

    def reset(self):
        """Restores the starting position."""
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

        self.king_squares = [ E1, E8 ]
        self.pieces = [ NONE for i in range(64) ]

        for i in range(64):
            mask = BB_SQUARES[i]
            if mask & self.pawns:
                self.pieces[i] = PAWN
            elif mask & self.knights:
                self.pieces[i] = KNIGHT
            elif mask & self.bishops:
                self.pieces[i] = BISHOP
            elif mask & self.rooks:
                self.pieces[i] = ROOK
            elif mask & self.queens:
                self.pieces[i] = QUEEN
            elif mask & self.kings:
                self.pieces[i] = KING

        self.ep_square = 0
        self.castling_rights = CASTLING
        self.turn = WHITE
        self.fullmove_number = 1
        self.halfmove_clock = 0

        for i in range(64):
            if BB_SQUARES[i] & self.occupied:
                self.occupied_l90 |= BB_SQUARES_L90[i]
                self.occupied_r45 |= BB_SQUARES_R45[i]
                self.occupied_l45 |= BB_SQUARES_L45[i]

        self.halfmove_clock_stack = collections.deque()
        self.captured_piece_stack = collections.deque()
        self.castling_right_stack = collections.deque()
        self.ep_square_stack = collections.deque()
        self.move_stack = collections.deque()
        self.incremental_zobrist_hash = self.board_zobrist_hash(POLYGLOT_RANDOM_ARRAY)
        self.transpositions = collections.Counter((self.zobrist_hash(), ))

    def clear(self):
        """
        Clears the board.

        Resets move stacks and move counters. The side to move is white. There
        are no rooks or kings, so castling is not allowed.

        In order to be in a valid `status()` at least kings need to be put on
        the board. This is required for move generation and validation to work
        properly.
        """
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
        self.pieces = [ NONE for i in range(64) ]

        self.halfmove_clock_stack = collections.deque()
        self.captured_piece_stack = collections.deque()
        self.castling_right_stack = collections.deque()
        self.ep_square_stack = collections.deque()
        self.move_stack = collections.deque()

        self.ep_square = 0
        self.castling_rights = CASTLING_NONE
        self.turn = WHITE
        self.fullmove_number = 1
        self.halfmove_clock = 0
        self.incremental_zobrist_hash = self.board_zobrist_hash(POLYGLOT_RANDOM_ARRAY)
        self.transpositions = collections.Counter((self.zobrist_hash(), ))

    def piece_at(self, square):
        """Gets the piece at the given square."""
        mask = BB_SQUARES[square]
        color = int(bool(self.occupied_co[BLACK] & mask))

        piece_type = self.piece_type_at(square)
        if piece_type:
            return Piece(piece_type, color)

    def piece_type_at(self, square):
        """Gets the piece type at the given square."""
        return self.pieces[square]

    def remove_piece_at(self, square):
        """Removes a piece from the given square if present."""
        piece_type = self.pieces[square]

        if piece_type == NONE:
            return

        mask = BB_SQUARES[square]

        if piece_type == PAWN:
            self.pawns ^= mask
        elif piece_type == KNIGHT:
            self.knights ^= mask
        elif piece_type == BISHOP:
            self.bishops ^= mask
        elif piece_type == ROOK:
            self.rooks ^= mask
        elif piece_type == QUEEN:
            self.queens ^= mask
        else:
            self.kings ^= mask

        color = int(bool(self.occupied_co[BLACK] & mask))

        self.pieces[square] = NONE
        self.occupied ^= mask
        self.occupied_co[color] ^= mask
        self.occupied_l90 ^= BB_SQUARES[SQUARES_L90[square]]
        self.occupied_r45 ^= BB_SQUARES[SQUARES_R45[square]]
        self.occupied_l45 ^= BB_SQUARES[SQUARES_L45[square]]

        # Update incremental zobrist hash.
        if color == BLACK:
            piece_index = (piece_type - 1) * 2
        else:
            piece_index = (piece_type - 1) * 2 + 1
        self.incremental_zobrist_hash ^= POLYGLOT_RANDOM_ARRAY[64 * piece_index + 8 * rank_index(square) + file_index(square)]


    def set_piece_at(self, square, piece):
        """Sets a piece at the given square. An existing piece is replaced."""
        self.remove_piece_at(square)

        self.pieces[square] = piece.piece_type

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

        # Update incremental zorbist hash.
        if piece.color == BLACK:
            piece_index = (piece.piece_type - 1) * 2
        else:
            piece_index = (piece.piece_type - 1) * 2 + 1
        self.incremental_zobrist_hash ^= POLYGLOT_RANDOM_ARRAY[64 * piece_index + 8 * rank_index(square) + file_index(square)]


    def generate_pseudo_legal_moves(self, castling=True, pawns=True, knights=True, bishops=True, rooks=True, queens=True, king=True):
        if self.turn == WHITE:
            if castling:
                # Castling short.
                if self.castling_rights & CASTLING_WHITE_KINGSIDE and not (BB_F1 | BB_G1) & self.occupied:
                    if not self.is_attacked_by(BLACK, E1) and not self.is_attacked_by(BLACK, F1) and not self.is_attacked_by(BLACK, G1):
                        yield Move(E1, G1)

                # Castling long.
                if self.castling_rights & CASTLING_WHITE_QUEENSIDE and not (BB_B1 | BB_C1 | BB_D1) & self.occupied:
                    if not self.is_attacked_by(BLACK, C1) and not self.is_attacked_by(BLACK, D1) and not self.is_attacked_by(BLACK, E1):
                        yield Move(E1, C1)

            if pawns:
                # En-passant moves.
                movers = self.pawns & self.occupied_co[WHITE]
                if self.ep_square:
                    moves = BB_PAWN_ATTACKS[BLACK][self.ep_square] & movers
                    while moves:
                        from_square, moves = next_bit(moves)
                        yield Move(from_square, self.ep_square)

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
            if castling:
                # Castling short.
                if self.castling_rights & CASTLING_BLACK_KINGSIDE and not (BB_F8 | BB_G8) & self.occupied:
                    if not self.is_attacked_by(WHITE, E8) and not self.is_attacked_by(WHITE, F8) and not self.is_attacked_by(WHITE, G8):
                        yield Move(E8, G8)

                # Castling long.
                if self.castling_rights & CASTLING_BLACK_QUEENSIDE and not (BB_B8 | BB_C8 | BB_D8) & self.occupied:
                    if not self.is_attacked_by(WHITE, C8) and not self.is_attacked_by(WHITE, D8) and not self.is_attacked_by(WHITE, E8):
                        yield Move(E8, C8)

            if pawns:
                # En-passant moves.
                movers = self.pawns & self.occupied_co[BLACK]
                if self.ep_square:
                    moves = BB_PAWN_ATTACKS[WHITE][self.ep_square] & movers
                    while moves:
                        from_square, moves = next_bit(moves)
                        yield Move(from_square, self.ep_square)

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

        if knights:
            # Knight moves.
            movers = self.knights & self.occupied_co[self.turn]
            while movers:
                from_square, movers = next_bit(movers)
                moves = self.knight_attacks_from(from_square) & ~self.occupied_co[self.turn]
                while moves:
                    to_square, moves = next_bit(moves)
                    yield Move(from_square, to_square)

        if bishops:
            # Bishop moves.
            movers = self.bishops & self.occupied_co[self.turn]
            while movers:
                from_square, movers = next_bit(movers)
                moves = self.bishop_attacks_from(from_square) & ~self.occupied_co[self.turn]
                while moves:
                    to_square, moves = next_bit(moves)
                    yield Move(from_square, to_square)

        if rooks:
            # Rook moves.
            movers = self.rooks & self.occupied_co[self.turn]
            while movers:
                from_square, movers = next_bit(movers)
                moves = self.rook_attacks_from(from_square) & ~self.occupied_co[self.turn]
                while moves:
                    to_square, moves = next_bit(moves)
                    yield Move(from_square, to_square)

        if queens:
            # Queen moves.
            movers = self.queens & self.occupied_co[self.turn]
            while movers:
                from_square, movers = next_bit(movers)
                moves = self.queen_attacks_from(from_square) & ~self.occupied_co[self.turn]
                while moves:
                    to_square, moves = next_bit(moves)
                    yield Move(from_square, to_square)

        if king:
            # King moves.
            from_square = self.king_squares[self.turn]
            moves = self.king_attacks_from(from_square) & ~self.occupied_co[self.turn]
            while moves:
                to_square, moves = next_bit(moves)
                yield Move(from_square, to_square)

    def pseudo_legal_move_count(self):
        # In a way duplicates generate_pseudo_legal_moves() in order to use
        # population counts instead of counting actually yielded moves.
        count = 0

        if self.turn == WHITE:
            # Castling short.
            if self.castling_rights & CASTLING_WHITE_KINGSIDE and not (BB_F1 | BB_G1) & self.occupied:
                if not self.is_attacked_by(BLACK, E1) and not self.is_attacked_by(BLACK, F1) and not self.is_attacked_by(BLACK, G1):
                    count += 1

            # Castling long.
            if self.castling_rights & CASTLING_WHITE_QUEENSIDE and not (BB_B1 | BB_C1 | BB_D1) & self.occupied:
                if not self.is_attacked_by(BLACK, C1) and not self.is_attacked_by(BLACK, D1) and not self.is_attacked_by(BLACK, E1):
                    count += 1

            # En-passant moves.
            movers = self.pawns & self.occupied_co[WHITE]
            if self.ep_square:
                moves = BB_PAWN_ATTACKS[BLACK][self.ep_square] & movers
                count += sparse_pop_count(moves)

            # Pawn captures.
            moves = shift_up_right(movers) & self.occupied_co[BLACK]
            while moves:
                to_square, moves = next_bit(moves)
                if rank_index(to_square) != 7:
                    count += 1
                else:
                    count += 4

            moves = shift_up_left(movers) & self.occupied_co[BLACK]
            while moves:
                to_square, moves = next_bit(moves)
                if rank_index(to_square) != 7:
                    count += 1
                else:
                    count += 4

            # Pawns one forward.
            moves = shift_up(movers) & ~self.occupied
            movers = moves
            while moves:
                to_square, moves = next_bit(moves)
                if rank_index(to_square) != 7:
                    count += 1
                else:
                    count += 4

            # Pawns two forward.
            moves = shift_up(movers) & BB_RANK_4 & ~self.occupied
            count += pop_count(moves)
        else:
            # Castling short.
            if self.castling_rights & CASTLING_BLACK_KINGSIDE and not (BB_F8 | BB_G8) & self.occupied:
                if not self.is_attacked_by(WHITE, E8) and not self.is_attacked_by(WHITE, F8) and not self.is_attacked_by(WHITE, G8):
                    count += 1

            # Castling long.
            if self.castling_rights & CASTLING_BLACK_QUEENSIDE and not (BB_B8 | BB_C8 | BB_D8) & self.occupied:
                if not self.is_attacked_by(WHITE, C8) and not self.is_attacked_by(WHITE, D8) and not self.is_attacked_by(WHITE, E8):
                    count += 1

            # En-passant moves.
            movers = self.pawns & self.occupied_co[BLACK]
            if self.ep_square:
                moves = BB_PAWN_ATTACKS[WHITE][self.ep_square] & movers
                count += sparse_pop_count(moves)

            # Pawn captures.
            moves = shift_down_left(movers) & self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)
                if rank_index(to_square) != 0:
                    count += 1
                else:
                    count += 4

            moves = shift_down_right(movers) & self.occupied_co[WHITE]
            while moves:
                to_square, moves = next_bit(moves)
                if rank_index(to_square) != 0:
                    count += 1
                else:
                    count += 4

            # Pawns one forward.
            moves = shift_down(movers) & ~self.occupied
            movers = moves
            while moves:
                to_square, moves = next_bit(moves)
                if rank_index(to_square) != 0:
                    count += 1
                else:
                    count += 4

            # Pawns two forward.
            moves = shift_down(movers) & BB_RANK_5 & ~self.occupied
            count += pop_count(moves)

        # Knight moves.
        movers = self.knights & self.occupied_co[self.turn]
        while movers:
            from_square, movers = next_bit(movers)
            moves = self.knight_attacks_from(from_square) & ~self.occupied_co[self.turn]
            count += pop_count(moves)

        # Bishop moves.
        movers = self.bishops & self.occupied_co[self.turn]
        while movers:
            from_square, movers = next_bit(movers)
            moves = self.bishop_attacks_from(from_square) & ~self.occupied_co[self.turn]
            count += pop_count(moves)

        # Rook moves.
        movers = self.rooks & self.occupied_co[self.turn]
        while movers:
            from_square, movers = next_bit(movers)
            moves = self.rook_attacks_from(from_square) & ~self.occupied_co[self.turn]
            count += pop_count(moves)

        # Queen moves.
        movers = self.queens & self.occupied_co[self.turn]
        while movers:
            from_square, movers = next_bit(movers)
            moves = self.queen_attacks_from(from_square) & ~self.occupied_co[self.turn]
            count += pop_count(moves)

        # King moves.
        from_square = self.king_squares[self.turn]
        moves = self.king_attacks_from(from_square) & ~self.occupied_co[self.turn]
        count += pop_count(moves)

        return count

    def is_attacked_by(self, color, square):
        """
        Checks if the given side attacks the given square. Pinned pieces still
        count as attackers.
        """
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

    def attacker_mask(self, color, square):
        attackers = BB_PAWN_ATTACKS[color ^ 1][square] & self.pawns
        attackers |= self.knight_attacks_from(square) & self.knights
        attackers |= self.bishop_attacks_from(square) & (self.bishops | self.queens)
        attackers |= self.rook_attacks_from(square) & (self.rooks | self.queens)
        attackers |= self.king_attacks_from(square) & self.kings
        return attackers & self.occupied_co[color]

    def attackers(self, color, square):
        """
        Gets a set of attackers of the given color for the given square.

        Returns a set of squares.
        """
        return SquareSet(self.attacker_mask(color, square))

    def is_check(self):
        """Checks if the current side to move is in check."""
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
        """
        Checks if the given move would move would leave the king in check or
        put it into check.
        """
        self.push(move)
        is_check = self.was_into_check()
        self.pop()
        return is_check

    def was_into_check(self):
        """
        Checks if the king of the other side is attacked. Such a position is not
        valid and could only be reached by an illegal move.
        """
        return self.is_attacked_by(self.turn, self.king_squares[self.turn ^ 1])

    def generate_legal_moves(self, castling=True, pawns=True, knights=True, bishops=True, rooks=True, queens=True, king=True):
        return (move for move in self.generate_pseudo_legal_moves(castling, pawns, knights, bishops, rooks, queens, king) if not self.is_into_check(move))

    def is_pseudo_legal(self, move):
        # Null moves are not pseudo legal.
        if not move:
            return False

        # Source square must not be vacant.
        piece = self.piece_type_at(move.from_square)
        if not piece:
            return False

        # Get square masks.
        from_mask = BB_SQUARES[move.from_square]
        to_mask = BB_SQUARES[move.to_square]

        # Check turn.
        if not self.occupied_co[self.turn] & from_mask:
            return False

        # Destination square can not be occupied.
        if self.occupied_co[self.turn] & to_mask:
            return False

        # Only pawns can promote and only on the backrank.
        if move.promotion:
            if piece != PAWN:
                return False

            if self.turn == WHITE and rank_index(move.to_square) != 7:
                return False
            elif self.turn == BLACK and rank_index(move.to_square) != 0:
                return False

        # Handle moves by piece type.
        if piece == KING:
            # Castling.
            if self.turn == WHITE and move.from_square == E1:
                if move.to_square == G1 and self.castling_rights & CASTLING_WHITE_KINGSIDE and not (BB_F1 | BB_G1) & self.occupied:
                    if not self.is_attacked_by(BLACK, E1) and not self.is_attacked_by(BLACK, F1) and not self.is_attacked_by(BLACK, G1):
                        return True
                elif move.to_square == C1 and self.castling_rights & CASTLING_WHITE_QUEENSIDE and not (BB_B1 | BB_C1 | BB_D1) & self.occupied:
                    if not self.is_attacked_by(BLACK, E1) and not self.is_attacked_by(BLACK, D1) and not self.is_attacked_by(BLACK, C1):
                        return True
            elif self.turn == BLACK and move.from_square == E8:
                if move.to_square == G8 and self.castling_rights & CASTLING_BLACK_KINGSIDE and not (BB_F8 | BB_G8) & self.occupied:
                    if not self.is_attacked_by(WHITE, E8) and not self.is_attacked_by(WHITE, F8) and not self.is_attacked_by(WHITE, G8):
                        return True
                elif move.to_square == C8 and self.castling_rights & CASTLING_BLACK_QUEENSIDE and not (BB_B8 | BB_C8 | BB_D8) & self.occupied:
                    if not self.is_attacked_by(WHITE, E8) and not self.is_attacked_by(WHITE, D8) and not self.is_attacked_by(WHITE, C8):
                        return True

            return bool(self.king_attacks_from(move.from_square) & to_mask)
        elif piece == PAWN:
            # Require promotion type if on promotion rank.
            if not move.promotion:
                if self.turn == WHITE and rank_index(move.to_square) == 7:
                    return False
                if self.turn == BLACK and rank_index(move.to_square) == 0:
                    return False

            return bool(self.pawn_moves_from(move.from_square) & to_mask)
        elif piece == QUEEN:
            return bool(self.queen_attacks_from(move.from_square) & to_mask)
        elif piece == ROOK:
            return bool(self.rook_attacks_from(move.from_square) & to_mask)
        elif piece == BISHOP:
            return bool(self.bishop_attacks_from(move.from_square) & to_mask)
        elif piece == KNIGHT:
            return bool(self.knight_attacks_from(move.from_square) & to_mask)

    def is_legal(self, move):
        return self.is_pseudo_legal(move) and not self.is_into_check(move)

    def is_game_over(self):
        """
        Checks if the game is over due to checkmate, stalemate, insufficient
        mating material, the seventyfive-move rule or fivefold repitition.
        """
        # Seventyfive-move rule.
        if self.halfmove_clock >= 150:
            return True

        # Insufficient material.
        if self.is_insufficient_material():
            return True

        # Stalemate or checkmate.
        try:
            next(self.generate_legal_moves().__iter__())
        except StopIteration:
            return True

        # Fivefold repitition.
        if self.transpositions[self.zobrist_hash()] >= 5:
            return True

        return False

    def is_checkmate(self):
        """Checks if the current position is a checkmate."""
        if not self.is_check():
            return False

        try:
            next(self.generate_legal_moves().__iter__())
            return False
        except StopIteration:
            return True

    def is_stalemate(self):
        """Checks if the current position is a stalemate."""
        if self.is_check():
            return False

        try:
            next(self.generate_legal_moves().__iter__())
            return False
        except StopIteration:
            return True

    def is_insufficient_material(self):
        """Checks for a draw due to insufficient mating material."""
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

    def is_seventyfive_moves(self):
        """
        Since the first of July 2014 a game is automatically drawn (without
        a claim by one of the players) if the half move clock since a capture
        or pawn move is equal to or grather than 150. Other means to end a game
        take precedence.
        """
        if self.halfmove_clock >= 150:
            try:
                next(self.generate_legal_moves().__iter__())
                return True
            except StopIteration:
                pass

        return False

    def is_fivefold_repitition(self):
        """
        Since the first of July 2014 a game is automatically drawn (without
        a claim by one of the players) if a position occurs for the fifth time.
        """
        return self.transpositions[self.zobrist_hash()] >= 5

    def can_claim_draw(self):
        """
        Checks if the side to move can claim a draw by the fifty-move rule or
        by threefold repitition.
        """
        return self.can_claim_fifty_moves() or self.can_claim_threefold_repitition()

    def can_claim_fifty_moves(self):
        """
        Draw by the fifty-move rule can be claimed once the clock of halfmoves
        since the last capture or pawn move becomes equal or greater to 100
        and the side to move still has a legal move they can make.
        """
        # Fifty-move rule.
        if self.halfmove_clock >= 100:
            try:
                next(self.generate_legal_moves().__iter__())
                return True
            except StopIteration:
                pass

        return False

    def can_claim_threefold_repitition(self):
        """
        Draw by threefold repitition can be claimed if the position on the
        board occured for the third time or if such a repitition is reached
        with one of the possible legal moves.
        """
        # Threefold repitition occured.
        if self.transpositions[self.zobrist_hash()] >= 3:
            return True

        # The next legal move is a threefold repitition.
        for move in self.generate_pseudo_legal_moves():
            self.push(move)

            if not self.was_into_check() and self.transpositions[self.zobrist_hash()] >= 3:
                self.pop()
                return True

            self.pop()

        return False

    def push(self, move):
        """
        Updates the position with the given move and puts it onto a stack.

        Null moves just increment the move counters, switch turns and forfeit
        en passant capturing.

        No validation is performed. For performance moves are assumed to be at
        least pseudo legal. Otherwise there is no guarantee that the previous
        board state can be restored. To check it yourself you can use:

        >>> move in board.pseudo_legal_moves
        True
        """
        # Increment fullmove number.
        if self.turn == BLACK:
            self.fullmove_number += 1

        # Remember game state.
        captured_piece = self.piece_type_at(move.to_square) if move else NONE
        self.halfmove_clock_stack.append(self.halfmove_clock)
        self.castling_right_stack.append(self.castling_rights)
        self.captured_piece_stack.append(captured_piece)
        self.ep_square_stack.append(self.ep_square)
        self.move_stack.append(move)

        # On a null move simply swap turns.
        if not move:
            self.turn ^= 1
            self.ep_square = 0
            self.halfmove_clock += 1
            return

        # Update half move counter.
        piece_type = self.piece_type_at(move.from_square)
        if piece_type == PAWN or captured_piece:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # Promotion.
        if move.promotion:
            piece_type = move.promotion

        # Remove piece from target square.
        self.remove_piece_at(move.from_square)

        # Handle special pawn moves.
        self.ep_square = 0
        if piece_type == PAWN:
            diff = abs(move.to_square - move.from_square)

            # Remove pawns captured en-passant.
            if (diff == 7 or diff == 9) and not self.occupied & BB_SQUARES[move.to_square]:
                if self.turn == WHITE:
                    self.remove_piece_at(move.to_square - 8)
                else:
                    self.remove_piece_at(move.to_square + 8)

            # Set en-passant square.
            if diff == 16:
                if self.turn == WHITE:
                    self.ep_square = move.to_square - 8
                else:
                    self.ep_square = move.to_square + 8

        # Castling rights.
        if move.from_square == E1:
            self.castling_rights &= ~CASTLING_WHITE
        elif move.from_square == E8:
            self.castling_rights &= ~CASTLING_BLACK
        elif move.from_square == A1 or move.to_square == A1:
            self.castling_rights &= ~CASTLING_WHITE_QUEENSIDE
        elif move.from_square == A8 or move.to_square == A8:
            self.castling_rights &= ~CASTLING_BLACK_QUEENSIDE
        elif move.from_square == H1 or move.to_square == H1:
            self.castling_rights &= ~CASTLING_WHITE_KINGSIDE
        elif move.from_square == H8 or move.to_square == H8:
            self.castling_rights &= ~CASTLING_BLACK_KINGSIDE

        # Castling.
        if piece_type == KING:
            if move.from_square == E1 and move.to_square == G1:
                self.set_piece_at(F1, Piece(ROOK, WHITE))
                self.remove_piece_at(H1)
            elif move.from_square == E1 and move.to_square == C1:
                self.set_piece_at(D1, Piece(ROOK, WHITE))
                self.remove_piece_at(A1)
            elif move.from_square == E8 and move.to_square == G8:
                self.set_piece_at(F8, Piece(ROOK, BLACK))
                self.remove_piece_at(H8)
            elif move.from_square == E8 and move.to_square == C8:
                self.set_piece_at(D8, Piece(ROOK, BLACK))
                self.remove_piece_at(A8)

        # Put piece on target square.
        self.set_piece_at(move.to_square, Piece(piece_type, self.turn))

        # Swap turn.
        self.turn ^= 1

        # Update transposition table.
        self.transpositions.update((self.zobrist_hash(), ))

    def pop(self):
        """
        Restores the previous position and returns the last move from the stack.
        """
        move = self.move_stack.pop()

        # Update transposition table.
        self.transpositions.subtract((self.zobrist_hash(), ))

        # Decrement fullmove number.
        if self.turn == WHITE:
            self.fullmove_number -= 1

        # Restore state.
        self.halfmove_clock = self.halfmove_clock_stack.pop()
        self.castling_rights = self.castling_right_stack.pop()
        self.ep_square = self.ep_square_stack.pop()
        captured_piece = self.captured_piece_stack.pop()
        captured_piece_color = self.turn

        # On a null move simply swap the turn.
        if not move:
            self.turn ^= 1
            return move

        # Restore the source square.
        piece = PAWN if move.promotion else self.piece_type_at(move.to_square)
        self.set_piece_at(move.from_square, Piece(piece, self.turn ^ 1))

        # Restore target square.
        if captured_piece:
            self.set_piece_at(move.to_square, Piece(captured_piece, captured_piece_color))
        else:
            self.remove_piece_at(move.to_square)

            # Restore captured pawn after en-passant.
            if piece == PAWN and abs(move.from_square - move.to_square) in (7, 9):
                if self.turn == WHITE:
                    self.set_piece_at(move.to_square + 8, Piece(PAWN, WHITE))
                else:
                    self.set_piece_at(move.to_square - 8, Piece(PAWN, BLACK))

        # Restore rook position after castling.
        if piece == KING:
            if move.from_square == E1 and move.to_square == G1:
                self.remove_piece_at(F1)
                self.set_piece_at(H1, Piece(ROOK, WHITE))
            elif move.from_square == E1 and move.to_square == C1:
                self.remove_piece_at(D1)
                self.set_piece_at(A1, Piece(ROOK, WHITE))
            elif move.from_square == E8 and move.to_square == G8:
                self.remove_piece_at(F8)
                self.set_piece_at(H8, Piece(ROOK, BLACK))
            elif move.from_square == E8 and move.to_square == C8:
                self.remove_piece_at(D8)
                self.set_piece_at(A8, Piece(ROOK, BLACK))

        # Swap turn.
        self.turn ^= 1

        return move

    def peek(self):
        """Gets the last move from the move stack."""
        return self.move_stack[-1]

    def set_epd(self, epd):
        """
        Parses the given EPD string and uses it to set the position.

        If present the `hmvc` and the `fmvn` are used to set the half move
        clock and the fullmove number. Otherwise `0` and `1` are used.

        Returns a dictionary of parsed operations. Values can be strings,
        integers, floats or move objects.

        Raises `ValueError` if the EPD string is invalid.
        """
        # Split into 4 or 5 parts.
        parts = epd.strip().rstrip(";").split(None, 4)
        if len(parts) < 4:
            raise ValueError("epd should consist of at least 4 parts: {0}".format(repr(epd)))

        operations = {}

        # Parse the operations.
        if len(parts) > 4:
            operation_part = parts.pop()
            operation_part += ";"

            opcode = ""
            operand = ""
            in_operand = False
            in_quotes = False
            escape = False

            position = None

            for c in operation_part:
                if not in_operand:
                    if c == ";":
                        operations[opcode] = None
                        opcode = ""
                    elif c == " ":
                        if opcode:
                            in_operand = True
                    else:
                        opcode += c
                else:
                    if c == "\"":
                        if not operand and not in_quotes:
                            in_quotes = True
                        elif escape:
                            operand += c
                    elif c == "\\":
                        if escape:
                            operand += c
                        else:
                            escape = True
                    elif c == "s":
                        if escape:
                            operand += ";"
                        else:
                            operand += c
                    elif c == ";":
                        if escape:
                            operand += "\\"

                        if in_quotes:
                            operations[opcode] = operand
                        else:
                            try:
                                operations[opcode] = int(operand)
                            except ValueError:
                                try:
                                    operations[opcode] = float(operand)
                                except ValueError:
                                    if position is None:
                                        position = self.__class__(" ".join(parts + ["0", "1"]))

                                    operations[opcode] = position.parse_san(operand)

                        opcode = ""
                        operand = ""
                        in_operand = False
                        in_quotes = False
                        escape = False
                    else:
                        operand += c

        # Create a full FEN and parse it.
        parts.append(str(operations["hmvc"]) if "hmvc" in operations else "0")
        parts.append(str(operations["fmvn"]) if "fmvn" in operations else "1")
        self.set_fen(" ".join(parts))

        return operations

    def epd(self, **operations):
        """
        Gets an EPD representation of the current position.

        EPD operations can be given as keyword arguments. Supported operands
        are strings, integers, floats and moves. All other operands are
        converted to strings.

        `hmvc` and `fmvc` are *not* included by default. You can use:

        >>> board.epd(hmvc=board.halfmove_clock, fmvc=board.fullmove_number)
        'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - hmvc 0; fmvc 1;'
        """
        epd = []
        empty = 0

        # Position part.
        for square in SQUARES_180:
            piece = self.piece_at(square)

            if not piece:
                empty += 1
            else:
                if empty:
                    epd.append(str(empty))
                    empty = 0
                epd.append(piece.symbol())

            if BB_SQUARES[square] & BB_FILE_H:
                if empty:
                    epd.append(str(empty))
                    empty = 0

                if square != H1:
                    epd.append("/")

        epd.append(" ")

        # Side to move.
        if self.turn == WHITE:
            epd.append("w")
        else:
            epd.append("b")

        epd.append(" ")

        # Castling rights.
        if not self.castling_rights:
            epd.append("-")
        else:
            if self.castling_rights & CASTLING_WHITE_KINGSIDE:
                epd.append("K")
            if self.castling_rights & CASTLING_WHITE_QUEENSIDE:
                epd.append("Q")
            if self.castling_rights & CASTLING_BLACK_KINGSIDE:
                epd.append("k")
            if self.castling_rights & CASTLING_BLACK_QUEENSIDE:
                epd.append("q")

        epd.append(" ")

        # En-passant square.
        if self.ep_square:
            epd.append(SQUARE_NAMES[self.ep_square])
        else:
            epd.append("-")

        # Append operations.
        for opcode, operand in operations.items():
            epd.append(" ")
            epd.append(opcode)

            if hasattr(operand, "from_square") and hasattr(operand, "to_square"):
                # Append SAN for moves.
                epd.append(" ")
                epd.append(self.san(operand))
            elif isinstance(operand, (int, float)):
                # Append integer or float.
                epd.append(" ")
                epd.append(str(operand))
            elif operand is not None:
                # Append as escaped string.
                epd.append(" \"")
                epd.append(str(operand).replace("\r", "").replace("\n", " ").replace("\\", "\\\\").replace(";", "\\s"))
                epd.append("\"")

            epd.append(";")

        return "".join(epd)

    def set_fen(self, fen):
        """
        Parses a FEN and sets the position from it.

        Rasies `ValueError` if the FEN string is invalid.
        """
        # Ensure there are six parts.
        parts = fen.split()
        if len(parts) != 6:
            raise ValueError("fen string should consist of 6 parts: {0}".format(repr(fen)))

        # Ensure the board part is valid.
        rows = parts[0].split("/")
        if len(rows) != 8:
            raise ValueError("expected 8 rows in position part of fen: {0}".format(repr(fen)))

        # Validate each row.
        for row in rows:
            field_sum = 0
            previous_was_digit = False

            for c in row:
                if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                    if previous_was_digit:
                        raise ValueError("two subsequent digits in position part of fen: {0}".format(repr(fen)))
                    field_sum += int(c)
                    previous_was_digit = True
                elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                    field_sum += 1
                    previous_was_digit = False
                else:
                    raise ValueError("invalid character in position part of fen: {0}".format(repr(fen)))

            if field_sum != 8:
                raise ValueError("expected 8 columns per row in position part of fen: {0}".format(repr(fen)))

        # Check that the turn part is valid.
        if not parts[1] in ["w", "b"]:
            raise ValueError("expected 'w' or 'b' for turn part of fen: {0}".format(repr(fen)))

        # Check that the castling part is valid.
        if not FEN_CASTLING_REGEX.match(parts[2]):
            raise ValueError("invalid castling part in fen: {0}".format(repr(fen)))

        # Check that the en-passant part is valid.
        if parts[3] != "-":
            if parts[1] == "w":
                if rank_index(SQUARE_NAMES.index(parts[3])) != 5:
                    raise ValueError("expected en-passant square to be on sixth rank: {0}".format(repr(fen)))
            else:
                if rank_index(SQUARE_NAMES.index(parts[3])) != 2:
                    raise ValueError("expected en-passant square to be on third rank: {0}".format(repr(fen)))

        # Check that the half move part is valid.
        if int(parts[4]) < 0:
            raise ValueError("halfmove clock can not be negative: {0}".format(repr(fen)))

        # Check that the fullmove number part is valid.
        # 0 is allowed for compability but later replaced with 1.
        if int(parts[5]) < 0:
            raise ValueError("fullmove number must be positive: {0}".format(repr(fen)))

        # Clear board.
        self.clear()

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
        self.halfmove_clock = int(parts[4])
        self.fullmove_number = int(parts[5]) or 1

        # Reset the transposition table.
        self.transpositions = collections.Counter((self.zobrist_hash(), ))

    def fen(self):
        """Gets the FEN representation of the position."""
        fen = []

        # Position, turn, castling and en passant.
        fen.append(self.epd())

        # Half moves.
        fen.append(" ")
        fen.append(str(self.halfmove_clock))

        # Ply.
        fen.append(" ")
        fen.append(str(self.fullmove_number))

        return "".join(fen)

    def parse_san(self, san):
        """
        Uses the current position as the context to parse a move in standard
        algebraic notation and return the corresponding move object.

        The returned move is guaranteed to be either legal or a null move.

        Raises `ValueError` if the SAN is invalid or ambigous.
        """
        # Null moves.
        if san == "--":
            return Move.null()

        # Castling.
        if san in ("O-O", "O-O+", "O-O#"):
            move = Move(E1, G1) if self.turn == WHITE else Move(E8, G8)
            if self.kings & self.occupied_co[self.turn] & BB_SQUARES[move.from_square] and self.is_legal(move):
                return move
            else:
                raise ValueError("illegal san: {0}".format(repr(san)))
        elif san in ("O-O-O", "O-O-O+", "O-O-O#"):
            move = Move(E1, C1) if self.turn == WHITE else Move(E8, C8)
            if self.kings & self.occupied_co[self.turn] & BB_SQUARES[move.from_square] and self.is_legal(move):
                return move
            else:
                raise ValueError("illegal san: {0}".format(repr(san)))

        # Match normal moves.
        match = SAN_REGEX.match(san)
        if not match:
            raise ValueError("invalid san: {0}".format(repr(san)))

        # Get target square.
        to_square = SQUARE_NAMES.index(match.group(4))

        # Get the promotion type.
        if not match.group(5):
            promotion = NONE
        else:
            promotion = PIECE_SYMBOLS.index(match.group(5)[1].lower())

        # Filter by piece type.
        if match.group(1) == "N":
            moves = self.generate_pseudo_legal_moves(castling=False, pawns=False, knights=True, bishops=False, rooks=False, queens=False, king=False)
        elif match.group(1) == "B":
            moves = self.generate_pseudo_legal_moves(castling=False, pawns=False, knights=False, bishops=True, rooks=False, queens=False, king=False)
        elif match.group(1) == "K":
            moves = self.generate_pseudo_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=False, queens=False, king=True)
        elif match.group(1) == "R":
            moves = self.generate_pseudo_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=True, queens=False, king=False)
        elif match.group(1) == "Q":
            moves = self.generate_pseudo_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=False, queens=True, king=False)
        else:
            moves = self.generate_pseudo_legal_moves(castling=False, pawns=True, knights=False, bishops=False, rooks=False, queens=False, king=False)

        # Filter by source file.
        from_mask = BB_ALL
        if match.group(2):
            from_mask &= BB_FILES[FILE_NAMES.index(match.group(2))]

        # Filter by source rank.
        if match.group(3):
            from_mask &= BB_RANKS[int(match.group(3)) - 1]

        # Match legal moves.
        matched_move = None
        for move in moves:
            if move.to_square != to_square:
                continue

            if move.promotion != promotion:
                continue

            if not BB_SQUARES[move.from_square] & from_mask:
                continue

            if self.is_into_check(move):
                continue

            if matched_move:
                raise ValueError("ambiguous san: {0}".format(repr(san)))

            matched_move = move

        if not matched_move:
            raise ValueError("illegal san: {0}".format(repr(san)))

        return matched_move

    def push_san(self, san):
        """
        Parses a move in standard algebraic notation, makes the move and puts
        it on the the move stack.

        Raises `ValueError` if neither legal nor a null move.

        Returns the move.
        """
        move = self.parse_san(san)
        self.push(move)
        return move

    def san(self, move):
        """
        Gets the standard algebraic notation of the given move in the context of
        the current position.

        There is no validation. It is only guaranteed to work if the move is
        legal or a null move.
        """

        if not move:
            # Null move.
            return "--"

        piece = self.piece_type_at(move.from_square)
        en_passant = False

        # Castling.
        if piece == KING:
            if move.from_square == E1:
                if move.to_square == G1:
                    return "O-O"
                elif move.to_square == C1:
                    return "O-O-O"
            elif move.from_square == E8:
                if move.to_square == G8:
                    return "O-O"
                elif move.to_square == C8:
                    return "O-O-O"

        if piece == PAWN:
            san = ""

            # Detect en-passant.
            if not BB_SQUARES[move.to_square] & self.occupied:
                en_passant = abs(move.from_square - move.to_square) in (7, 9)
        else:
            # Get ambigous move candidates.
            if piece == KNIGHT:
                san = "N"
                others = self.knights & self.knight_attacks_from(move.to_square)
            elif piece == BISHOP:
                san = "B"
                others = self.bishops & self.bishop_attacks_from(move.to_square)
            elif piece == ROOK:
                san = "R"
                others = self.rooks & self.rook_attacks_from(move.to_square)
            elif piece == QUEEN:
                san = "Q"
                others = self.queens & self.queen_attacks_from(move.to_square)
            elif piece == KING:
                san = "K"
                others = self.kings & self.king_attacks_from(move.to_square)

            others &= ~BB_SQUARES[move.from_square]
            others &= self.occupied_co[self.turn]

            # Remove illegal candidates.
            squares = others
            while squares:
                square, squares = next_bit(squares)

                if self.is_into_check(Move(square, move.to_square)):
                    others &= ~BB_SQUARES[square]

            # Disambiguate.
            if others:
                row, column = False, False

                if others & BB_RANKS[rank_index(move.from_square)]:
                    column = True

                if others & BB_FILES[file_index(move.from_square)]:
                    row = True
                else:
                    column = True

                if column:
                    san += FILE_NAMES[file_index(move.from_square)]
                if row:
                    san += str(rank_index(move.from_square) + 1)

        # Captures.
        if BB_SQUARES[move.to_square] & self.occupied or en_passant:
            if piece == PAWN:
                san += FILE_NAMES[file_index(move.from_square)]
            san += "x"

        # Destination square.
        san += SQUARE_NAMES[move.to_square]

        # Promotion.
        if move.promotion:
            san += "=" + PIECE_SYMBOLS[move.promotion].upper()

        # Look ahead for check or checkmate.
        self.push(move)
        if self.is_check():
            if self.is_checkmate():
                san += "#"
            else:
                san += "+"
        self.pop()

        return san

    def status(self):
        """
        Gets a bitmask of possible problems with the position.
        Move making, generation and validation are only guaranteed to work on
        a completely valid board.
        """
        errors = STATUS_VALID

        if not self.occupied_co[WHITE] & self.kings:
            errors |= STATUS_NO_WHITE_KING
        if not self.occupied_co[BLACK] & self.kings:
            errors |= STATUS_NO_BLACK_KING
        if sparse_pop_count(self.occupied & self.kings) > 2:
            errors |= STATUS_TOO_MANY_KINGS

        if pop_count(self.occupied_co[WHITE] & self.pawns) > 8:
            errors |= STATUS_TOO_MANY_WHITE_PAWNS
        if pop_count(self.occupied_co[BLACK] & self.pawns) > 8:
            errors |= STATUS_TOO_MANY_BLACK_PAWNS

        if self.pawns & (BB_RANK_1 | BB_RANK_8):
            errors |= STATUS_PAWNS_ON_BACKRANK

        if pop_count(self.occupied_co[WHITE]) > 16:
            errors |= STATUS_TOO_MANY_WHITE_PIECES
        if pop_count(self.occupied_co[BLACK]) > 16:
            errors |= STATUS_TOO_MANY_BLACK_PIECES

        if self.castling_rights & CASTLING_WHITE:
            if not self.king_squares[WHITE] == E1:
                errors |= STATUS_BAD_CASTLING_RIGHTS

            if self.castling_rights & CASTLING_WHITE_QUEENSIDE:
                if not BB_A1 & self.occupied_co[WHITE] & self.rooks:
                    errors |= STATUS_BAD_CASTLING_RIGHTS
            if self.castling_rights & CASTLING_WHITE_KINGSIDE:
                if not BB_H1 & self.occupied_co[WHITE] & self.rooks:
                    errors |= STATUS_BAD_CASTLING_RIGHTS

        if self.castling_rights & CASTLING_BLACK:
            if not self.king_squares[BLACK] == E8:
                errors |= STATUS_BAD_CASTLING_RIGHTS

            if self.castling_rights & CASTLING_BLACK_QUEENSIDE:
                if not BB_A8 & self.occupied_co[BLACK] & self.rooks:
                    errors |= STATUS_BAD_CASTLING_RIGHTS
            if self.castling_rights & CASTLING_BLACK_KINGSIDE:
                if not BB_H8 & self.occupied_co[BLACK] & self.rooks:
                    errors |= STATUS_BAD_CASTLING_RIGHTS

        if self.ep_square:
            if self.turn == WHITE:
                ep_rank = 5
                pawn_mask = shift_down(BB_SQUARES[self.ep_square])
            else:
                ep_rank = 2
                pawn_mask = shift_up(BB_SQUARES[self.ep_square])

            # The en-passant square must be on the third or sixth rank.
            if rank_index(self.ep_square) != ep_rank:
                errors |= STATUS_INVALID_EP_SQUARE

            # The last move must have been a double pawn push, so there must
            # be a pawn of the correct color on the fourth or fifth rank.
            if not self.pawns & self.occupied_co[self.turn ^ 1] & pawn_mask:
                errors |= STATUS_INVALID_EP_SQUARE

        if not errors & (STATUS_NO_WHITE_KING | STATUS_NO_BLACK_KING | STATUS_TOO_MANY_KINGS):
            if self.was_into_check():
                errors |= STATUS_OPPOSITE_CHECK

        return errors

    def __repr__(self):
        return "Bitboard('{0}')".format(self.fen())

    def __str__(self):
        builder = []

        for square in SQUARES_180:
            piece = self.piece_at(square)

            if piece:
                builder.append(piece.symbol())
            else:
                builder.append(".")

            if BB_SQUARES[square] & BB_FILE_H:
                if square != H1:
                    builder.append("\n")
            else:
                builder.append(" ")

        return "".join(builder)

    def __eq__(self, bitboard):
        return not self.__ne__(bitboard)

    def __ne__(self, bitboard):
        try:
            if self.occupied != bitboard.occupied:
                return True
            if self.occupied_co[WHITE] != bitboard.occupied_co[WHITE]:
                return True
            if self.pawns != bitboard.pawns:
                return True
            if self.knights != bitboard.knights:
                return True
            if self.bishops != bitboard.bishops:
                return True
            if self.rooks != bitboard.rooks:
                return True
            if self.queens != bitboard.queens:
                return True
            if self.kings != bitboard.kings:
                return True
            if self.ep_square != bitboard.ep_square:
                return True
            if self.castling_rights != bitboard.castling_rights:
                return True
            if self.turn != bitboard.turn:
                return True
            if self.fullmove_number != bitboard.fullmove_number:
                return True
            if self.halfmove_clock != bitboard.halfmove_clock:
                return True
        except AttributeError:
            return True

        return False

    def zobrist_hash(self, array=None):
        """
        Returns a Zobrist hash of the current position.

        A zobrist hash is an exclusive or of pseudo random values picked from
        an array. Which values are picked is decided by features of the
        position, such as piece positions, castling rights and en-passant
        squares. For this implementation an array of 781 values is required.

        The default behaviour is to use values from `POLYGLOT_RANDOM_ARRAY`,
        which makes for hashes compatible with polyglot opening books.
        """
        # Hash in the board setup.
        zobrist_hash = self.board_zobrist_hash(array)

        # Default random array is polyglot compatible.
        if array is None:
            array = POLYGLOT_RANDOM_ARRAY

        # Hash in the castling flags.
        if self.castling_rights & CASTLING_WHITE_KINGSIDE:
            zobrist_hash ^= array[768]
        if self.castling_rights & CASTLING_WHITE_QUEENSIDE:
            zobrist_hash ^= array[768 + 1]
        if self.castling_rights & CASTLING_BLACK_KINGSIDE:
            zobrist_hash ^= array[768 + 2]
        if self.castling_rights & CASTLING_BLACK_QUEENSIDE:
            zobrist_hash ^= array[768 + 3]

        # Hash in the en-passant file.
        if self.ep_square:
            # But only if theres actually a pawn ready to capture it. Legality
            # of the potential capture is irrelevant.
            if self.turn == WHITE:
                ep_mask = shift_down(BB_SQUARES[self.ep_square])
            else:
                ep_mask = shift_up(BB_SQUARES[self.ep_square])
            ep_mask = shift_left(ep_mask) | shift_right(ep_mask)

            if ep_mask & self.pawns & self.occupied_co[self.turn]:
                zobrist_hash ^= array[772 + file_index(self.ep_square)]

        # Hash in the turn.
        if self.turn == WHITE:
            zobrist_hash ^= array[780]

        return zobrist_hash

    def board_zobrist_hash(self, array=None):
        if array is None:
            return self.incremental_zobrist_hash

        zobrist_hash = 0

        squares = self.occupied_co[BLACK]
        while squares:
            square, squares = next_bit(squares)
            piece_index = (self.piece_type_at(square) - 1) * 2
            zobrist_hash ^= array[64 * piece_index + 8 * rank_index(square) + file_index(square)]

        squares = self.occupied_co[WHITE]
        while squares:
            square, squares = next_bit(squares)
            piece_index = (self.piece_type_at(square) - 1) * 2 + 1
            zobrist_hash ^= array[64 * piece_index + 8 * rank_index(square) + file_index(square)]

        return zobrist_hash


class PseudoLegalMoveGenerator(object):

    def __init__(self, bitboard):
        self.bitboard = bitboard

    def __bool__(self):
        try:
            next(self.bitboard.generate_pseudo_legal_moves())
            return True
        except StopIteration:
            return False

    __nonzero__ = __bool__

    def __len__(self):
        return self.bitboard.pseudo_legal_move_count()

    def __iter__(self):
        return self.bitboard.generate_pseudo_legal_moves()

    def __contains__(self, move):
        return self.bitboard.is_pseudo_legal(move)


class LegalMoveGenerator(object):

    def __init__(self, bitboard):
        self.bitboard = bitboard

    def __bool__(self):
        try:
            next(self.bitboard.generate_legal_moves())
            return True
        except StopIteration:
            return False

    __nonzero__ = __bool__

    def __len__(self):
        count = 0

        for move in self.bitboard.generate_legal_moves():
            count += 1

        return count

    def __iter__(self):
        return self.bitboard.generate_legal_moves()

    def __contains__(self, move):
        return self.bitboard.is_legal(move)


class SquareSet(object):

    def __init__(self, mask):
        self.mask = mask

    def __bool__(self):
        return bool(self.mask)

    __nonzero__ = __bool__

    def __eq__(self, other):
        try:
            return int(self) == int(other)
        except ValueError:
            return False

    def __ne__(self, other):
        try:
            return int(self) != int(other)
        except ValueError:
            return False

    def __len__(self):
        return pop_count(self.mask)

    def __iter__(self):
        squares = self.mask
        while squares:
            square, squares = next_bit(squares)
            yield square

    def __contains__(self, square):
        return bool(BB_SQUARES[square] & self.mask)

    def __lshift__(self, shift):
        return self.__class__((self.mask << shift) & BB_ALL)

    def __rshift__(self, shift):
        return self.__class__(self.mask >> shift)

    def __and__(self, other):
        try:
            return self.__class__(self.mask & other.mask)
        except AttributeError:
            return self.__class__(self.mask & other)

    def __xor__(self, other):
        try:
            return self.__class__((self.mask ^ other.mask) & BB_ALL)
        except AttributeError:
            return self.__class__((self.mask ^ other) & BB_ALL)

    def __or__(self, other):
        try:
            return self.__class__((self.mask | other.mask) & BB_ALL)
        except AttributeError:
            return self.__class__((self.mask | other) & BB_ALL)

    def __ilshift__(self, shift):
        self.mask = (self.mask << shift & BB_ALL)
        return self

    def __irshift__(self, shift):
        self.mask >>= shift
        return self

    def __iand__(self, other):
        try:
            self.mask &= other.mask
        except AttributeError:
            self.mask &= other
        return self

    def __ixor__(self, other):
        try:
            self.mask = (self.mask ^ other.mask) & BB_ALL
        except AttributeError:
            self.mask = (self.mask ^ other) & BB_ALL
        return self

    def __ior__(self, other):
        try:
            self.mask = (self.mask | other.mask) & BB_ALL
        except AttributeError:
            self.mask = (self.mask | other) & BB_ALL
        return self

    def __invert__(self):
        return self.__class__(~self.mask & BB_ALL)

    def __oct__(self):
        return oct(self.mask)

    def __hex__(self):
        return hex(self.mask)

    def __int__(self):
        return self.mask

    def __index__(self):
        return self.mask

    def __repr__(self):
        return "SquareSet({0})".format(bin(self.mask))

    def __str__(self):
        builder = []

        for square in SQUARES_180:
            mask = BB_SQUARES[square]

            if self.mask & mask:
                builder.append("1")
            else:
                builder.append(".")

            if mask & BB_FILE_H:
                if square != H1:
                    builder.append("\n")
            else:
                builder.append(" ")

        return "".join(builder)

    def __hash__(self):
        return self.mask
