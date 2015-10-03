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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

__author__ = "Niklas Fiekas"

__email__ = "niklas.fiekas@tu-clausthal.de"

__version__ = "0.12.0"


import copy
import re
import sys

try:
    import backport_collections as collections
except ImportError:
    import collections

COLORS = [WHITE, BLACK] = [True, False]

PIECE_TYPES = [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING] = range(1, 7)

PIECE_SYMBOLS = ["", "p", "n", "b", "r", "q", "k"]

UNICODE_PIECE_SYMBOLS = {
    "R": u"♖", "r": u"♜",
    "N": u"♘", "n": u"♞",
    "B": u"♗", "b": u"♝",
    "Q": u"♕", "q": u"♛",
    "K": u"♔", "k": u"♚",
    "P": u"♙", "p": u"♟",
}

FILE_NAMES = ["a", "b", "c", "d", "e", "f", "g", "h"]

RANK_NAMES = ["1", "2", "3", "4", "5", "6", "7", "8"]

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
"""The FEN of the standard chess starting position."""

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
    """Gets the file index of square where ``0`` is the a file."""
    return square & 7

def rank_index(square):
    """Gets the rank index of the square where ``0`` is the first rank."""
    return square >> 3

def square(file_index, rank_index):
    """Gets a square number by file and rank index."""
    return rank_index * 8 + file_index


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

for square_index, mask in enumerate(BB_SQUARES):
    if (file_index(square_index) + rank_index(square_index)) % 2:
        BB_LIGHT_SQUARES |= mask
    else:
        BB_DARK_SQUARES |= mask

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

FILE_MASK = {}
FILE_MASK[0] = 0

for square_index, mask in enumerate(BB_SQUARES):
    FILE_MASK[mask] = BB_FILES[file_index(square_index)]

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

RANK_MASK = {}
RANK_MASK[0] = 0

for square_index, mask in enumerate(BB_SQUARES):
    RANK_MASK[mask] = BB_RANKS[rank_index(square_index)]

DIAG_MASK_NW = {}
DIAG_MASK_NW[0] = 0

for i in range(8):
    DIAG_MASK_NW[1 << i] = 0
    for j in range(i + 1):
        DIAG_MASK_NW[1 << i] |= 1 << (i + 7 * j)
    for j in range(i + 1):
        DIAG_MASK_NW[1 << (i + 7 * j)] = DIAG_MASK_NW[1 << i]

for i in range(63, 55, -1):
    DIAG_MASK_NW[1 << i] = 0
    for j in range(64 - i):
        DIAG_MASK_NW[1 << i] |= 1 << (i - 7 * j)
    for j in range(64 - i):
        DIAG_MASK_NW[1 << (i - 7 * j)] = DIAG_MASK_NW[1 << i]

DIAG_MASK_NE = {}
DIAG_MASK_NE[0] = 0

for i in range(7, -1, -1):
    DIAG_MASK_NE[1 << i] = 0
    for j in range(8 - i):
        DIAG_MASK_NE[1 << i] |= 1 << (i + 9 * j)
    for j in range(8 - i):
        DIAG_MASK_NE[1 << (i + 9 * j)] = DIAG_MASK_NE[1 << i]

for i in range(56, 64):
    DIAG_MASK_NE[1 << i] = 0
    for j in range(i - 55):
        DIAG_MASK_NE[1 << i] |= 1 << (i - 9 * j)
    for j in range(i - 55):
        DIAG_MASK_NE[1 << (i - 9 * j)] = DIAG_MASK_NE[1 << i]

try:
    from gmpy2 import popcount as pop_count
    from gmpy2 import bit_scan1 as bit_scan
except ImportError:
    try:
        from gmpy import popcount as pop_count
        from gmpy import scan1 as bit_scan
    except ImportError:
        def pop_count(b):
            return bin(b).count("1")

        def bit_scan(b, n=0):
            string = bin(b)
            l = len(string)
            r = string.rfind("1", 0, l - n)
            if r == -1:
                return -1
            else:
                return l - r - 1

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


BB_KNIGHT_ATTACKS = []
KNIGHT_MOVES = {}
KNIGHT_MOVES[0] = 0

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
    KNIGHT_MOVES[bb_square] = mask & BB_ALL

BB_KING_ATTACKS = []
KING_MOVES = {}
KING_MOVES[0] = 0

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
    KING_MOVES[bb_square] = mask & BB_ALL

def _attack_table(square_list):
    attack_table = {}
    attack_table[0] = {}
    attack_table[0][0] = 0

    for i in range(len(square_list)):
        list_size = len(square_list[i])

        for current_position in range(list_size):
            current_bb = square_list[i][current_position]
            attack_table[current_bb] = {}

            for occupation in range(1 << list_size):
                moves = 0

                # Loop over squares to the right of the mover.
                for newsquare in range(current_position + 1, list_size):
                    moves |= square_list[i][newsquare]
                    if (1 << newsquare) & occupation:
                        break

                # Loop over squares to the left of the mover.
                for newsquare in range(current_position - 1, -1, -1):
                    moves |= square_list[i][newsquare]
                    if (1 << newsquare) & occupation:
                        break

                # Convert occupation to a bitboard number.
                temp_bb = 0
                while occupation:
                    lowest = occupation & -occupation
                    temp_bb |= square_list[i][BB_SQUARES.index(lowest)]
                    occupation = occupation & (occupation - 1)

                attack_table[current_bb][temp_bb] = moves

    return attack_table

DIAG_ATTACKS_NE = _attack_table([
                                [BB_H1],
                            [BB_H2, BB_G1],
                        [BB_H3, BB_G2, BB_F1],
                    [BB_H4, BB_G3, BB_F2, BB_E1],
                [BB_H5, BB_G4, BB_F3, BB_E2, BB_D1],
            [BB_H6, BB_G5, BB_F4, BB_E3, BB_D2, BB_C1],
        [BB_H7, BB_G6, BB_F5, BB_E4, BB_D3, BB_C2, BB_B1],
    [BB_H8, BB_G7, BB_F6, BB_E5, BB_D4, BB_C3, BB_B2, BB_A1],
        [BB_G8, BB_F7, BB_E6, BB_D5, BB_C4, BB_B3, BB_A2],
            [BB_F8, BB_E7, BB_D6, BB_C5, BB_B4, BB_A3],
                [BB_E8, BB_D7, BB_C6, BB_B5, BB_A4],
                    [BB_D8, BB_C7, BB_B6, BB_A5],
                        [BB_C8, BB_B7, BB_A6],
                            [BB_B8, BB_A7],
                                [BB_A8],
])

DIAG_ATTACKS_NW = _attack_table([
                                [BB_A1],
                            [BB_B1, BB_A2],
                        [BB_C1, BB_B2, BB_A3],
                    [BB_D1, BB_C2, BB_B3, BB_A4],
                [BB_E1, BB_D2, BB_C3, BB_B4, BB_A5],
            [BB_F1, BB_E2, BB_D3, BB_C4, BB_B5, BB_A6],
        [BB_G1, BB_F2, BB_E3, BB_D4, BB_C5, BB_B6, BB_A7],
    [BB_H1, BB_G2, BB_F3, BB_E4, BB_D5, BB_C6, BB_B7, BB_A8],
        [BB_H2, BB_G3, BB_F4, BB_E5, BB_D6, BB_C7, BB_B8],
            [BB_H3, BB_G4, BB_F5, BB_E6, BB_D7, BB_C8],
                [BB_H4, BB_G5, BB_F6, BB_E7, BB_D8],
                    [BB_H5, BB_G6, BB_F7, BB_E8],
                        [BB_H6, BB_G7, BB_F8],
                            [BB_H7, BB_G8],
                                [BB_H8],
])

FILE_ATTACKS = _attack_table([
    [BB_A1, BB_A2, BB_A3, BB_A4, BB_A5, BB_A6, BB_A7, BB_A8],
    [BB_B1, BB_B2, BB_B3, BB_B4, BB_B5, BB_B6, BB_B7, BB_B8],
    [BB_C1, BB_C2, BB_C3, BB_C4, BB_C5, BB_C6, BB_C7, BB_C8],
    [BB_D1, BB_D2, BB_D3, BB_D4, BB_D5, BB_D6, BB_D7, BB_D8],
    [BB_E1, BB_E2, BB_E3, BB_E4, BB_E5, BB_E6, BB_E7, BB_E8],
    [BB_F1, BB_F2, BB_F3, BB_F4, BB_F5, BB_F6, BB_F7, BB_F8],
    [BB_G1, BB_G2, BB_G3, BB_G4, BB_G5, BB_G6, BB_G7, BB_G8],
    [BB_H1, BB_H2, BB_H3, BB_H4, BB_H5, BB_H6, BB_H7, BB_H8],
])

RANK_ATTACKS = _attack_table([
    [BB_A1, BB_B1, BB_C1, BB_D1, BB_E1, BB_F1, BB_G1, BB_H1],
    [BB_A2, BB_B2, BB_C2, BB_D2, BB_E2, BB_F2, BB_G2, BB_H2],
    [BB_A3, BB_B3, BB_C3, BB_D3, BB_E3, BB_F3, BB_G3, BB_H3],
    [BB_A4, BB_B4, BB_C4, BB_D4, BB_E4, BB_F4, BB_G4, BB_H4],
    [BB_A5, BB_B5, BB_C5, BB_D5, BB_E5, BB_F5, BB_G5, BB_H5],
    [BB_A6, BB_B6, BB_C6, BB_D6, BB_E6, BB_F6, BB_G6, BB_H6],
    [BB_A7, BB_B7, BB_C7, BB_D7, BB_E7, BB_F7, BB_G7, BB_H7],
    [BB_A8, BB_B8, BB_C8, BB_D8, BB_E8, BB_F8, BB_G8, BB_H8],
])


SAN_REGEX = re.compile("^([NBKRQ])?([a-h])?([1-8])?x?([a-h][1-8])(=?[nbrqNBRQ])?(\\+|#)?$")

FEN_CASTLING_REGEX = re.compile("^-|[KQABCDEFGH]{0,2}[kqabcdefgh]{0,2}$")


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
        Gets the symbol ``P``, ``N``, ``B``, ``R``, ``Q`` or ``K`` for white
        pieces or the lower-case variants for the black pieces.
        """
        if self.color == WHITE:
            return PIECE_SYMBOLS[self.piece_type].upper()
        else:
            return PIECE_SYMBOLS[self.piece_type]

    def unicode_symbol(self, invert_color=False):
        """
        Gets the unicode character for the piece.
        """
        if not invert_color:
            return UNICODE_PIECE_SYMBOLS[self.symbol()]
        else:
            return UNICODE_PIECE_SYMBOLS[self.symbol().swapcase()]

    def __hash__(self):
        return hash(self.piece_type * (self.color + 1))

    def __repr__(self):
        return "Piece.from_symbol('{0}')".format(self.symbol())

    def __str__(self):
        return self.symbol()

    def __unicode__(self, invert_color=False):
        return self.unicode_symbol(invert_color)

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

        Raises :exc:`ValueError` if the symbol is invalid.
        """
        if symbol.islower():
            return cls(PIECE_SYMBOLS.index(symbol), BLACK)
        else:
            return cls(PIECE_SYMBOLS.index(symbol.lower()), WHITE)


class Move(object):
    """
    Represents a move from a square to a square and possibly the promotion
    piece type.

    Null moves are supported.
    """

    def __init__(self, from_square, to_square, promotion=None):
        self.from_square = from_square
        self.to_square = to_square
        self.promotion = promotion

    def uci(self):
        """
        Gets an UCI string for the move.

        For example a move from A7 to A8 would be ``a7a8`` or ``a7a8q`` if it
        is a promotion to a queen.

        The UCI representatin of null moves is ``0000``.
        """
        if self.promotion:
            return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square] + PIECE_SYMBOLS[self.promotion]
        elif self:
            return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square]
        else:
            return "0000"

    def __bool__(self):
        return bool(self.from_square or self.to_square or self.promotion)

    __nonzero__ = __bool__

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
        if self.promotion:
            return hash(self.to_square ^ self.from_square << 6 ^ self.promotion << 12)
        else:
            return hash(self.to_square ^ self.from_square << 6)

    @classmethod
    def from_uci(cls, uci):
        """
        Parses an UCI string.

        Raises :exc:`ValueError` if the UCI string is invalid.
        """
        if uci == "0000":
            return cls.null()
        elif len(uci) == 4:
            return cls(SQUARE_NAMES.index(uci[0:2]), SQUARE_NAMES.index(uci[2:4]))
        elif len(uci) == 5:
            promotion = PIECE_SYMBOLS.index(uci[4])
            return cls(SQUARE_NAMES.index(uci[0:2]), SQUARE_NAMES.index(uci[2:4]), promotion)
        else:
            raise ValueError("expected uci string to be of length 4 or 5: {0}".format(repr(uci)))

    @classmethod
    def null(cls):
        """
        Gets a null move.

        A null move just passes the turn to the other side (and possibly
        forfeits en passant capturing). Null moves evaluate to ``False`` in
        boolean contexts.

        >>> bool(chess.Move.null())
        False
        """
        return cls(0, 0, None)


class Board(object):
    """
    A board and additional information representing a position.

    Provides move generation, validation, parsing, attack generation,
    game end detection, move counters and the capability to make and unmake
    moves.

    The board is initialized to the starting position, unless otherwise
    specified in the optional *fen* argument. If *fen* is ``None`` an empty
    board is created.

    Optionally supports *chess960*. In Chess960 castling moves are encoded
    by a king move to the corresponding rook square.
    """

    def __init__(self, fen=STARTING_FEN, chess960=False):
        self.chess960 = chess960

        self.pseudo_legal_moves = PseudoLegalMoveGenerator(self)
        self.legal_moves = LegalMoveGenerator(self)

        self.occupied_co = [BB_VOID, BB_VOID]

        self.attacks_valid = False
        self.attacks_from = collections.defaultdict(int)
        self.attacks_to = collections.defaultdict(int)
        self.attacks_valid_stack = collections.deque()
        self.attacks_from_stack = collections.deque()
        self.attacks_to_stack = collections.deque()

        self.halfmove_clock_stack = collections.deque()
        self.captured_piece_stack = collections.deque()
        self.castling_right_stack = collections.deque()
        self.ep_square_stack = collections.deque()
        self.move_stack = collections.deque()

        self.transpositions = collections.Counter()

        if fen is None:
            self.clear()
        elif fen == STARTING_FEN:
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

        self.occupied_co[WHITE] = BB_RANK_1 | BB_RANK_2
        self.occupied_co[BLACK] = BB_RANK_7 | BB_RANK_8

        self.occupied = BB_RANK_1 | BB_RANK_2 | BB_RANK_7 | BB_RANK_8

        self.ep_square = 0
        self.castling_rights = BB_A1 | BB_H1 | BB_A8 | BB_H8
        self.turn = WHITE
        self.fullmove_number = 1
        self.halfmove_clock = 0

        self.incremental_zobrist_hash = self.board_zobrist_hash(POLYGLOT_RANDOM_ARRAY)

        self.halfmove_clock_stack.clear()
        self.captured_piece_stack.clear()
        self.castling_right_stack.clear()
        self.ep_square_stack.clear()
        self.move_stack.clear()

        self.transpositions.clear()
        self.transpositions.update((self.zobrist_hash(), ))

        self.attacks_valid = False
        self.clear_stack()

    def clear(self):
        """
        Clears the board.

        Resets move stacks and move counters. The side to move is white. There
        are no rooks or kings, so castling rights are removed.

        In order to be in a valid :func:`~chess.Board.status()` at least kings
        need to be put on the board.
        """
        self.pawns = BB_VOID
        self.knights = BB_VOID
        self.bishops = BB_VOID
        self.rooks = BB_VOID
        self.queens = BB_VOID
        self.kings = BB_VOID

        self.occupied_co[WHITE] = BB_VOID
        self.occupied_co[BLACK] = BB_VOID
        self.occupied = BB_VOID

        self.ep_square = 0
        self.castling_rights = BB_VOID
        self.turn = WHITE
        self.fullmove_number = 1
        self.halfmove_clock = 0

        self.incremental_zobrist_hash = self.board_zobrist_hash(POLYGLOT_RANDOM_ARRAY)

        self.attacks_valid = False
        self.clear_stack()

    def clear_stack(self):
        """Clears the move stack and transposition table."""
        self.halfmove_clock_stack.clear()
        self.captured_piece_stack.clear()
        self.castling_right_stack.clear()
        self.ep_square_stack.clear()
        self.move_stack.clear()

        self.transpositions.clear()
        self.transpositions.update((self.zobrist_hash(), ))

        self.attacks_valid_stack.clear()
        self.attacks_from_stack.clear()
        self.attacks_to_stack.clear()

    def pieces_mask(self, piece_type, color):
        if piece_type == PAWN:
            bb = self.pawns
        elif piece_type == KNIGHT:
            bb = self.knights
        elif piece_type == BISHOP:
            bb = self.bishops
        elif piece_type == ROOK:
            bb = self.rooks
        elif piece_type == QUEEN:
            bb = self.queens
        elif piece_type == KING:
            bb = self.kings

        return bb & self.occupied_co[color]

    def pieces(self, piece_type, color):
        """
        Gets pieces of the given type and color.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.pieces_mask(piece_type, color))

    def piece_at(self, square):
        """Gets the :class:`piece <chess.Piece>` at the given square."""
        piece_type = self.piece_type_at(square)
        if piece_type:
            mask = BB_SQUARES[square]
            color = bool(self.occupied_co[WHITE] & mask)
            return Piece(piece_type, color)

    def piece_type_at(self, square):
        """Gets the piece type at the given square."""
        mask = BB_SQUARES[square]

        if self.pawns & mask:
            return PAWN
        elif self.knights & mask:
            return KNIGHT
        elif self.bishops & mask:
            return BISHOP
        elif self.rooks & mask:
            return ROOK
        elif self.queens & mask:
            return QUEEN
        elif self.kings & mask:
            return KING
        else:
            return None

    def _remove_piece_at(self, square):
        mask = BB_SQUARES[square]
        if not self.occupied & mask:
            return

        piece_type = self.piece_type_at(square)

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

        color = bool(self.occupied_co[WHITE] & mask)

        self.occupied ^= mask
        self.occupied_co[color] ^= mask

        # Update incremental zobrist hash.
        if color == BLACK:
            piece_index = (piece_type - 1) * 2
        else:
            piece_index = (piece_type - 1) * 2 + 1
        self.incremental_zobrist_hash ^= POLYGLOT_RANDOM_ARRAY[64 * piece_index + 8 * rank_index(square) + file_index(square)]

    def remove_piece_at(self, square):
        """Removes a piece from the given square if present."""
        self._remove_piece_at(square)
        self.clear_stack()
        self.attacks_valid = False

    def _set_piece_at(self, square, piece_type, color):
        self._remove_piece_at(square)

        mask = BB_SQUARES[square]

        if piece_type == PAWN:
            self.pawns |= mask
        elif piece_type == KNIGHT:
            self.knights |= mask
        elif piece_type == BISHOP:
            self.bishops |= mask
        elif piece_type == ROOK:
            self.rooks |= mask
        elif piece_type == QUEEN:
            self.queens |= mask
        elif piece_type == KING:
            self.kings |= mask

        self.occupied ^= mask
        self.occupied_co[color] ^= mask

        # Update incremental zobrist hash.
        if color == BLACK:
            piece_index = (piece_type - 1) * 2
        else:
            piece_index = (piece_type - 1) * 2 + 1
        self.incremental_zobrist_hash ^= POLYGLOT_RANDOM_ARRAY[64 * piece_index + 8 * rank_index(square) + file_index(square)]

    def set_piece_at(self, square, piece):
        """Sets a piece at the given square. An existing piece is replaced."""
        self._set_piece_at(square, piece.piece_type, piece.color)
        self.clear_stack()
        self.attacks_valid = False

    def generate_pseudo_legal_moves(self, castling=True, pawns=True, knights=True, bishops=True, rooks=True, queens=True, king=True):
        self.generate_attacks()

        our_pieces = self.occupied_co[self.turn]
        their_pieces = self.occupied_co[not self.turn]

        # Selective move generation.
        selected_pieces = BB_VOID
        if knights:
            selected_pieces |= self.knights
        if bishops:
            selected_pieces |= self.bishops
        if rooks:
            selected_pieces |= self.rooks
        if queens:
            selected_pieces |= self.queens
        if king:
            selected_pieces |= self.kings

        # Generate piece moves.
        non_pawns = our_pieces & selected_pieces
        while non_pawns:
            from_square = non_pawns & -non_pawns
            from_square_index = bit_scan(from_square)

            moves = self.attacks_from[from_square] & ~our_pieces
            while moves:
                to_square = moves & -moves
                yield Move(from_square_index, bit_scan(to_square))
                moves = moves & (moves - 1)

            non_pawns = non_pawns & (non_pawns - 1)

        # Generate castling moves.
        if castling:
            for move in self.generate_castling_moves():
                yield move

        # The remaining moves are all pawn moves.
        if not pawns:
            return

        # Generate pawn captures.
        pawns = self.pawns & our_pieces
        if self.turn == WHITE:
            right_captures = pawns << 9 & their_pieces & ~BB_FILE_A & BB_ALL
            left_captures = pawns << 7 & their_pieces & ~BB_FILE_H & BB_ALL
        else:
            right_captures = pawns >> 7 & their_pieces & ~BB_FILE_A
            left_captures = pawns >> 9 & their_pieces & ~BB_FILE_H

        # Yield right captures.
        while right_captures:
            to_square = right_captures & -right_captures
            to_square_index = bit_scan(to_square)

            if self.turn == WHITE:
                from_square = to_square >> 9
            else:
                from_square = to_square << 7
            from_square_index = bit_scan(from_square)

            if BB_RANK_1 & to_square or BB_RANK_8 & to_square:
                yield Move(from_square_index, to_square_index, QUEEN)
                yield Move(from_square_index, to_square_index, ROOK)
                yield Move(from_square_index, to_square_index, BISHOP)
                yield Move(from_square_index, to_square_index, KNIGHT)
            else:
                yield Move(from_square_index, to_square_index)

            right_captures = right_captures & (right_captures - 1)

        # Yield left captures.
        while left_captures:
            to_square = left_captures & -left_captures
            to_square_index = bit_scan(to_square)

            if self.turn == WHITE:
                from_square = to_square >> 7
            else:
                from_square = to_square << 9
            from_square_index = bit_scan(from_square)

            if BB_RANK_1 & to_square or BB_RANK_8 & to_square:
                yield Move(from_square_index, to_square_index, QUEEN)
                yield Move(from_square_index, to_square_index, ROOK)
                yield Move(from_square_index, to_square_index, BISHOP)
                yield Move(from_square_index, to_square_index, KNIGHT)
            else:
                yield Move(from_square_index, to_square_index)

            left_captures = left_captures & (left_captures - 1)

        # Generate en passant captures.
        ep_square_mask = BB_SQUARES[self.ep_square] if self.ep_square else BB_VOID
        if ep_square_mask:
            if self.turn == WHITE:
                capturing_pawns = pawns & BB_RANK_5
            else:
                capturing_pawns = pawns & BB_RANK_4

            # Left side capture.
            if ep_square_mask & ~BB_FILE_A:
                left_file = FILE_MASK[ep_square_mask] >> 1
                capturing_pawn = capturing_pawns & left_file
                if capturing_pawn:
                    yield Move(bit_scan(capturing_pawn), self.ep_square)

            # Right side capture.
            if ep_square_mask & ~BB_FILE_H:
                right_file = FILE_MASK[ep_square_mask] << 1
                capturing_pawn = capturing_pawns & right_file
                if capturing_pawn:
                    yield Move(bit_scan(capturing_pawn), self.ep_square)

        # Prepare pawn advance generation.
        if self.turn == WHITE:
            single_moves = pawns << 8 & ~self.occupied
            double_moves = single_moves << 8 & ~self.occupied & BB_RANK_4
        else:
            single_moves = pawns >> 8 & ~self.occupied
            double_moves = single_moves >> 8 & ~self.occupied & BB_RANK_5

        # Generate single pawn moves.
        while single_moves:
            to_square = single_moves & -single_moves
            to_square_index = bit_scan(to_square)

            if self.turn == WHITE:
                from_square = to_square >> 8
            else:
                from_square = to_square << 8
            from_square_index = bit_scan(from_square)

            if BB_RANK_1 & to_square or BB_RANK_8 & to_square:
                yield Move(from_square_index, to_square_index, QUEEN)
                yield Move(from_square_index, to_square_index, ROOK)
                yield Move(from_square_index, to_square_index, BISHOP)
                yield Move(from_square_index, to_square_index, KNIGHT)
            else:
                yield Move(from_square_index, to_square_index)

            single_moves = single_moves & (single_moves - 1)

        # Generate double pawn moves.
        while double_moves:
            to_square = double_moves & -double_moves
            to_square_index = bit_scan(to_square)

            if self.turn == WHITE:
                from_square = to_square >> 16
            else:
                from_square = to_square << 16
            from_square_index = bit_scan(from_square)

            yield Move(from_square_index, to_square_index)

            double_moves = double_moves & (double_moves - 1)

    def attacker_mask(self, color, square):
        self.generate_attacks()
        return self.attacks_to[BB_SQUARES[square]] & self.occupied_co[color]

    def is_attacked_by(self, color, square):
        """
        Checks if the given side attacks the given square.

        Pinned pieces still count as attackers. Pawns that can be captured
        en passant are attacked.
        """
        return bool(self.attacker_mask(color, square))

    def attackers(self, color, square):
        """
        Gets a set of attackers of the given color for the given square.

        Pinned pieces still count as attackers. Pawns that can be captured
        en passant are attacked.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.attacker_mask(color, square))

    def attacks_mask(self, square):
        self.generate_attacks()
        return self.attacks_from[BB_SQUARES[square]]

    def attacks(self, square):
        """
        Gets a set of attacked squares from a given square.

        There will be no attacks if the square is empty. Pinned pieces are
        still attacking other squares. Pawns will attack pawns they could
        capture en passant.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.attacks_mask(square))

    def pin_mask(self, color, square):
        return self._pinned(color, BB_SQUARES[square])

    def pin(self, color, square):
        """
        Detects pins of the given square to the king of the given color.

        Returns a :class:`set of squares <chess.SquareSet>` that mask the rank,
        file or diagonal of the pin. If there is no pin, then a mask of the
        entire board is returned.
        """
        return SquareSet(self.pin_mask(color, square))

    def is_pinned(self, color, square):
        """
        Detects if the given square is pinned to the king of the given color.
        """
        return self.pin_mask(color, square) != BB_ALL

    def is_check(self):
        """Returns if the current side to move is in check."""
        king_square = bit_scan(self.kings & self.occupied_co[self.turn])
        if king_square is None or king_square == -1:
            return False

        return self.is_attacked_by(not self.turn, king_square)

    def is_into_check(self, move):
        """
        Checks if the given move would leave the king in check or put it into
        check. The move must be at least pseudo legal.
        """
        from_square_mask = BB_SQUARES[move.from_square]
        to_square_mask = BB_SQUARES[move.to_square]

        # If already in check, look if it is an evasion.
        if self.is_check():
            return move not in self.generate_evasions(
                castling=False,
                pawns=from_square_mask & self.pawns,
                knights=from_square_mask & self.knights,
                bishops=from_square_mask & self.bishops,
                rooks=from_square_mask & self.rooks,
                queens=from_square_mask & self.queens,
                king=from_square_mask & self.kings)

        # We are assuming pseudo legality, so castling moves are always legal.
        if self.is_castling(move):
            return False

        # Detect uncovered check.
        if not self._pinned(self.turn, from_square_mask) & to_square_mask:
            return True

        # Detect king moves into check.
        if from_square_mask & self.kings:
            return self.attacks_to[to_square_mask] & self.occupied_co[not self.turn]

        return False

    def was_into_check(self):
        """
        Checks if the king of the other side is attacked. Such a position is not
        valid and could only be reached by an illegal move.
        """
        king_square = bit_scan(self.kings & self.occupied_co[not self.turn])
        if king_square is None or king_square == -1:
            return False

        return self.is_attacked_by(self.turn, king_square)

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

        # Only pawns can promote and only on the backrank.
        if move.promotion:
            if piece != PAWN:
                return False

            if self.turn == WHITE and rank_index(move.to_square) != 7:
                return False
            elif self.turn == BLACK and rank_index(move.to_square) != 0:
                return False

        # Handle castling.
        if piece == KING:
            if move in self.generate_castling_moves():
                return True

        # Destination square can not be occupied.
        if self.occupied_co[self.turn] & to_mask:
            return False

        # Handle pawn moves.
        if piece == PAWN:
            return move in self.generate_pseudo_legal_moves(castling=False, pawns=True, knights=False, bishops=False, rooks=False, queens=False, king=False)

        # Handle all other pieces.
        self.generate_attacks()
        return bool(self.attacks_from[from_mask] & to_mask)

    def is_legal(self, move):
        return self.is_pseudo_legal(move) and not self.is_into_check(move)

    def is_game_over(self):
        """
        Checks if the game is over due to checkmate, stalemate, insufficient
        mating material, the seventyfive-move rule or fivefold repetition.
        """
        # Seventyfive-move rule.
        if self.halfmove_clock >= 150:
            return True

        # Insufficient material.
        if self.is_insufficient_material():
            return True

        # Stalemate or checkmate.
        if not any(self.generate_legal_moves()):
            return True

        # Fivefold repetition.
        if self.is_fivefold_repetition():
            return True

        return False

    def is_checkmate(self):
        """Checks if the current position is a checkmate."""
        if not self.is_check():
            return False

        return not any(self.generate_legal_moves())

    def is_stalemate(self):
        """Checks if the current position is a stalemate."""
        if self.is_check():
            return False

        return not any(self.generate_legal_moves())

    def is_insufficient_material(self):
        """Checks for a draw due to insufficient mating material."""
        # Enough material to mate.
        if self.pawns or self.rooks or self.queens:
            return False

        # A single knight or a single bishop.
        if pop_count(self.occupied) <= 3:
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
            if any(self.generate_legal_moves()):
                return True

        return False

    def is_fivefold_repetition(self):
        """
        Since the first of July 2014 a game is automatically drawn (without
        a claim by one of the players) if a position occurs for the fifth time
        on consecutive alternating moves.
        """
        zobrist_hash = self.zobrist_hash()

        # A minimum amount of moves must have been played and the position
        # in question must have appeared at least five times.
        if len(self.move_stack) < 16 or self.transpositions[zobrist_hash] < 5:
            return False

        switchyard = collections.deque()

        for _ in range(4):
            # Go back two full moves, each.
            for _ in range(4):
                switchyard.append(self.pop())

            # Check the position was the same before.
            if self.zobrist_hash() != zobrist_hash:
                while switchyard:
                    self.push(switchyard.pop())

                return False

        while switchyard:
            self.push(switchyard.pop())

        return True

    def can_claim_draw(self):
        """
        Checks if the side to move can claim a draw by the fifty-move rule or
        by threefold repetition.
        """
        return self.can_claim_fifty_moves() or self.can_claim_threefold_repetition()

    def can_claim_fifty_moves(self):
        """
        Draw by the fifty-move rule can be claimed once the clock of halfmoves
        since the last capture or pawn move becomes equal or greater to 100
        and the side to move still has a legal move they can make.
        """
        # Fifty-move rule.
        if self.halfmove_clock >= 100:
            if any(self.generate_legal_moves()):
                return True

        return False

    def can_claim_threefold_repetition(self):
        """
        Draw by threefold repetition can be claimed if the position on the
        board occured for the third time or if such a repetition is reached
        with one of the possible legal moves.
        """
        # Threefold repetition occured.
        if self.transpositions[self.zobrist_hash()] >= 3:
            return True

        # The next legal move is a threefold repetition.
        for move in self.generate_legal_moves():
            self.push(move)

            if self.transpositions[self.zobrist_hash()] >= 3:
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
        move = self._to_chess960(move)

        # Increment fullmove number.
        if self.turn == BLACK:
            self.fullmove_number += 1

        # Remember game state.
        captured_piece = self.piece_at(move.to_square) if move else None
        self.halfmove_clock_stack.append(self.halfmove_clock)
        self.castling_right_stack.append(self.castling_rights)
        self.captured_piece_stack.append(captured_piece)
        self.ep_square_stack.append(self.ep_square)
        self.move_stack.append(move)

        # Remember attacks.
        self.attacks_valid_stack.append(self.attacks_valid)
        self.attacks_from_stack.append(self.attacks_from)
        self.attacks_to_stack.append(self.attacks_to)

        # On a null move simply swap turns and reset the en passant square.
        if not move:
            self.turn = not self.turn
            self.halfmove_clock += 1

            # Invalidate en passant attacks.
            if self.ep_square:
                self.attacks_valid = False
            self.ep_square = 0
            return

        # Update half move counter.
        piece_type = self.piece_type_at(move.from_square)
        if piece_type == PAWN or (captured_piece and captured_piece.color != self.turn):
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # Promotion.
        if move.promotion:
            piece_type = move.promotion

        # Remove piece from original square.
        self._remove_piece_at(move.from_square)

        # Handle special pawn moves.
        self.ep_square = 0
        if piece_type == PAWN:
            diff = abs(move.to_square - move.from_square)

            # Remove pawns captured en passant.
            if diff in [7, 9] and not self.occupied & BB_SQUARES[move.to_square]:
                if self.turn == WHITE:
                    self._remove_piece_at(move.to_square - 8)
                else:
                    self._remove_piece_at(move.to_square + 8)

            # Set en passant square.
            if diff == 16:
                if self.turn == WHITE:
                    self.ep_square = move.to_square - 8
                else:
                    self.ep_square = move.to_square + 8

        # Update castling rights.
        self.castling_rights &= ~BB_SQUARES[move.to_square]
        self.castling_rights &= ~BB_SQUARES[move.from_square]
        if piece_type == KING:
            if self.turn == WHITE:
                self.castling_rights &= ~BB_RANK_1
            else:
                self.castling_rights &= ~BB_RANK_8

        # Castling.
        castling = piece_type == KING and captured_piece and captured_piece.color == self.turn
        if castling:
            a_side = file_index(move.to_square) < file_index(move.from_square)

            self._remove_piece_at(move.from_square)
            self._remove_piece_at(move.to_square)

            if a_side:
                self._set_piece_at(C1 if self.turn == WHITE else C8, KING, self.turn)
                self._set_piece_at(D1 if self.turn == WHITE else D8, ROOK, self.turn)
            else:
                self._set_piece_at(G1 if self.turn == WHITE else G8, KING, self.turn)
                self._set_piece_at(F1 if self.turn == WHITE else F8, ROOK, self.turn)

        # Put piece on target square.
        if not castling:
            self._set_piece_at(move.to_square, piece_type, self.turn)

        # Swap turn.
        self.turn = not self.turn

        # Update transposition table.
        self.transpositions.update((self.zobrist_hash(), ))

        # Invalidate attacks.
        self.attacks_valid = False

    def pop(self):
        """
        Restores the previous position and returns the last move from the stack.
        """
        stack_move = self.move_stack.pop()
        move = self._to_chess960(stack_move)

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

        # Restore attacks.
        try:
            self.attacks_valid = self.attacks_valid_stack.pop()
            self.attacks_from = self.attacks_from_stack.pop()
            self.attacks_to = self.attacks_to_stack.pop()
        except IndexError:
            self.attacks_valid = False

        # On a null move simply swap the turn.
        if not move:
            self.turn = not self.turn
            return move

        # Remove the rook after castling and restore the king. Castling is
        # encoded as capturing our own rook.
        castling = captured_piece and captured_piece.color != self.turn
        if castling:
            a_side = file_index(move.to_square) < file_index(move.from_square)

            if a_side:
                self._remove_piece_at(C1 if self.turn == BLACK else C8)
                self._remove_piece_at(D1 if self.turn == BLACK else D8)
            else:
                self._remove_piece_at(G1 if self.turn == BLACK else G8)
                self._remove_piece_at(F1 if self.turn == BLACK else F8)

            self._set_piece_at(move.from_square, KING, not self.turn)

        piece = PAWN if move.promotion else self.piece_type_at(move.to_square)

        # Restore target square.
        if captured_piece:
            self._set_piece_at(move.to_square, captured_piece.piece_type, captured_piece.color)
        else:
            self._remove_piece_at(move.to_square)

            # Restore captured pawn after en passant.
            if piece == PAWN and abs(move.from_square - move.to_square) in (7, 9):
                if self.turn == WHITE:
                    self._set_piece_at(move.to_square + 8, PAWN, WHITE)
                else:
                    self._set_piece_at(move.to_square - 8, PAWN, BLACK)

        # Restore the source square.
        if not castling:
            self._set_piece_at(move.from_square, piece, not self.turn)

        # Swap turn.
        self.turn = not self.turn

        return stack_move

    def peek(self):
        """Gets the last move from the move stack."""
        return self.move_stack[-1]

    def board_fen(self):
        builder = []
        empty = 0

        for square in SQUARES_180:
            piece = self.piece_at(square)

            if not piece:
                empty += 1
            else:
                if empty:
                    builder.append(str(empty))
                    empty = 0
                builder.append(piece.symbol())

            if BB_SQUARES[square] & BB_FILE_H:
                if empty:
                    builder.append(str(empty))
                    empty = 0

                if square != H1:
                    builder.append("/")

        return "".join(builder)

    def castling_shredder_fen(self):
        if not self.castling_rights:
            return "-"

        builder = []

        black_castling_rights = self.castling_rights & BB_RANK_8
        while black_castling_rights:
            mask = black_castling_rights & -black_castling_rights
            builder.append(FILE_NAMES[file_index(bit_scan(mask))])
            black_castling_rights = black_castling_rights & (black_castling_rights - 1)

        white_castling_rights = self.castling_rights & BB_RANK_1
        while white_castling_rights:
            mask = white_castling_rights & -white_castling_rights
            builder.append(FILE_NAMES[file_index(bit_scan(mask))].upper())
            white_castling_rights = white_castling_rights & (white_castling_rights - 1)

        builder.reverse()

        return "".join(builder)

    def castling_xfen(self):
        builder = []

        for color in [BLACK, WHITE]:
            king_mask = self.kings & self.occupied_co[color]
            if not king_mask:
                continue

            king_file = file_index(bit_scan(king_mask))
            backrank = BB_RANK_1 if color == WHITE else BB_RANK_8

            castling_rights = self.castling_rights & backrank
            while castling_rights:
                rook = castling_rights & -castling_rights
                rook_file = file_index(bit_scan(rook))

                a_side = rook_file < king_file

                shredder = False
                other_rooks = self.occupied_co[color] & self.rooks & backrank & ~rook
                while other_rooks:
                    other_rook = other_rooks & -other_rooks
                    if (file_index(bit_scan(other_rook)) < rook_file) == a_side:
                        shredder = True
                        break
                    other_rooks = other_rooks & (other_rooks - 1)

                if shredder:
                    ch = FILE_NAMES[rook_file]
                else:
                    ch = "q" if a_side else "k"

                builder.append(ch.upper() if color == WHITE else ch)

                castling_rights = castling_rights & (castling_rights - 1)

        if builder:
            builder.reverse()
            return "".join(builder)
        else:
            return "-"

    def has_legal_en_passant(self):
        """Checks if there is a legal en passant capture."""
        return self.ep_square and any(self.is_en_passant(move) for move in self.generate_legal_moves(castling=False, pawns=True, knights=False, bishops=False, rooks=False, queens=False, king=False))

    def fen(self):
        """
        Gets the FEN representation of the position.

        A FEN string (e.g.
        ``rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1``) consists
        of the position part (:func:`~chess.Board.board_fen()`), the turn,
        the castling part (:func:`~chess.Board.castling_xfen()`), a relevant
        en passant square (:data:`~chess.Board.ep_square`,
        :func:`~chess.Board.has_legal_en_passant()`), the halfmove clock
        and the fullmove number.
        """
        fen = []
        fen.append(self.board_fen())
        fen.append("w" if self.turn == WHITE else "b")
        fen.append(self.castling_xfen())
        fen.append(SQUARE_NAMES[self.ep_square] if self.has_legal_en_passant() else "-")
        fen.append(str(self.halfmove_clock))
        fen.append(str(self.fullmove_number))
        return " ".join(fen)

    def shredder_fen(self):
        """
        Gets the Shredder FEN representation of the position.

        Castling rights are encoded by the file of the rook. The starting
        castling rights in normal chess are HAha.

        Use :func:`~chess.Board.castling_shredder_fen()` to get just the
        castling part.
        """
        fen = []
        fen.append(self.board_fen())
        fen.append("w" if self.turn == WHITE else "b")
        fen.append(self.castling_shredder_fen())
        fen.append(SQUARE_NAMES[self.ep_square] if self.has_legal_en_passant() else "-")
        fen.append(str(self.halfmove_clock))
        fen.append(str(self.fullmove_number))
        return " ".join(fen)

    def set_fen(self, fen):
        """
        Parses a FEN and sets the position from it.

        Rasies :exc:`ValueError` if the FEN string is invalid.
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

        # Check that the en passant part is valid.
        if parts[3] != "-":
            if parts[1] == "w":
                if rank_index(SQUARE_NAMES.index(parts[3])) != 5:
                    raise ValueError("expected ep square to be on sixth rank: {0}".format(repr(fen)))
            else:
                if rank_index(SQUARE_NAMES.index(parts[3])) != 2:
                    raise ValueError("expected ep square to be on third rank: {0}".format(repr(fen)))

        # Check that the half move part is valid.
        if int(parts[4]) < 0:
            raise ValueError("halfmove clock can not be negative: {0}".format(repr(fen)))

        # Check that the fullmove number part is valid.
        # 0 is allowed for compability but later replaced with 1.
        if int(parts[5]) < 0:
            raise ValueError("fullmove number must be positive: {0}".format(repr(fen)))

        # Clear board and invalidate attacks.
        self.clear()

        # Put pieces on the board.
        square_index = 0
        for c in parts[0]:
            if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                square_index += int(c)
            elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                piece = Piece.from_symbol(c)
                self._set_piece_at(SQUARES_180[square_index], piece.piece_type, piece.color)
                square_index += 1

        # Set the turn.
        if parts[1] == "w":
            self.turn = WHITE
        else:
            self.turn = BLACK

        # Set castling flags.
        self.castling_rights = BB_VOID
        for flag in parts[2]:
            if flag == "-":
                break

            color = WHITE if flag.isupper() else BLACK
            flag = flag.lower()
            backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
            rooks = self.occupied_co[color] & self.rooks & backrank

            if flag == "q":
                # Select the leftmost rook.
                self.castling_rights |= (rooks & -rooks)
            elif flag == "k":
                # Select the rightmost rook.
                mask = BB_VOID
                while rooks:
                    mask = (rooks & -rooks)
                    rooks = rooks & (rooks - 1)
                self.castling_rights |= mask
            else:
                self.castling_rights |= BB_FILES[FILE_NAMES.index(flag)] & backrank

        # Set the en passant square.
        if parts[3] == "-":
            self.ep_square = 0
        else:
            self.ep_square = SQUARE_NAMES.index(parts[3])

        # Set the mover counters.
        self.halfmove_clock = int(parts[4])
        self.fullmove_number = int(parts[5]) or 1

        # Reset the transposition table.
        self.transpositions.clear()
        self.transpositions.update((self.zobrist_hash(), ))

    def epd(self, **operations):
        """
        Gets an EPD representation of the current position.

        EPD operations can be given as keyword arguments. Supported operands
        are strings, integers, floats and moves and lists of moves and None.
        All other operands are converted to strings.

        A list of moves for *pv* will be interpreted as a variation. All other
        move lists are interpreted as a set of moves in the current position.

        *hmvc* and *fmvc* are not included by default. You can use:

        >>> board.epd(hmvc=board.halfmove_clock, fmvc=board.fullmove_number)
        'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - hmvc 0; fmvc 1;'
        """
        epd = []

        # Position part.
        epd.append(self.board_fen())
        epd.append(" ")

        # Side to move.
        epd.append("w" if self.turn == WHITE else "b")
        epd.append(" ")

        # Castling rights.
        epd.append(self.castling_xfen())
        epd.append(" ")

        # En passant square.
        epd.append(SQUARE_NAMES[self.ep_square] if self.has_legal_en_passant() else "-")

        # Append operations.
        for opcode, operand in operations.items():
            epd.append(" ")
            epd.append(opcode)

            # Value is empty.
            if operand is None:
                epd.append(";")
                continue

            # Value is a move.
            if hasattr(operand, "from_square") and hasattr(operand, "to_square") and hasattr(operand, "promotion"):
                # Append SAN for moves.
                epd.append(" ")
                epd.append(self.san(operand))
                epd.append(";")
                continue

            # Value is numeric.
            if isinstance(operand, (int, float)):
                # Append integer or float.
                epd.append(" ")
                epd.append(str(operand))
                epd.append(";")
                continue

            # Value is a set of moves or a variation.
            if hasattr(operand, "__iter__"):
                position = Board(self.shredder_fen()) if opcode == "pv" else self
                iterator = operand.__iter__()
                first_move = next(iterator)
                if hasattr(first_move, "from_square") and hasattr(first_move, "to_square") and hasattr(first_move, "promotion"):
                    epd.append(" ")
                    epd.append(position.san(first_move))
                    if opcode == "pv":
                        position.push(first_move)

                    for move in iterator:
                        epd.append(" ")
                        epd.append(position.san(move))
                        if opcode == "pv":
                            position.push(move)

                    epd.append(";")
                    continue

            # Append as escaped string.
            epd.append(" \"")
            epd.append(str(operand).replace("\r", "").replace("\n", " ").replace("\\", "\\\\").replace(";", "\\s"))
            epd.append("\";")

        return "".join(epd)

    def set_epd(self, epd):
        """
        Parses the given EPD string and uses it to set the position.

        If present the ``hmvc`` and the ``fmvn`` are used to set the half move
        clock and the fullmove number. Otherwise ``0`` and ``1`` are used.

        Returns a dictionary of parsed operations. Values can be strings,
        integers, floats or move objects.

        Raises :exc:`ValueError` if the EPD string is invalid.
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
                            # A string operand.
                            operations[opcode] = operand
                        else:
                            try:
                                # An integer.
                                operations[opcode] = int(operand)
                            except ValueError:
                                try:
                                    # A float.
                                    operations[opcode] = float(operand)
                                except ValueError:
                                    if position is None:
                                        position = type(self)(" ".join(parts + ["0", "1"]))

                                    if opcode == "pv":
                                        # A variation.
                                        operations[opcode] = []
                                        for token in operand.split():
                                            move = position.parse_san(token)
                                            operations[opcode].append(move)
                                            position.push(move)

                                        # Reset the position.
                                        while position.move_stack:
                                            position.pop()
                                    elif opcode in ("bm", "am"):
                                        # A set of moves.
                                        operations[opcode] = [position.parse_san(token) for token in operand.split()]
                                    else:
                                        # A single move.
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

        # Look ahead for check or checkmate.
        self.push(move)
        is_check = self.is_check()
        is_checkmate = is_check and self.is_checkmate()
        self.pop()

        # Castling.
        if self.is_castling(move):
            if file_index(move.to_square) < file_index(move.from_square):
                san = "O-O-O"
            else:
                san = "O-O"

            if is_checkmate:
                return san + "#"
            elif is_check:
                return san + "+"
            else:
                return san

        piece = self.piece_type_at(move.from_square)

        if piece == PAWN:
            san = ""
        else:
            # Get ambigous move candidates.
            if piece == KNIGHT:
                san = "N"
                candidates = self.generate_legal_moves(castling=False, pawns=False, knights=True, bishops=False, rooks=False, queens=False, king=False)
            elif piece == BISHOP:
                san = "B"
                candidates = self.generate_legal_moves(castling=False, pawns=False, knights=False, bishops=True, rooks=False, queens=False, king=False)
            elif piece == ROOK:
                san = "R"
                candidates = self.generate_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=True, queens=False, king=False)
            elif piece == QUEEN:
                san = "Q"
                candidates = self.generate_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=False, queens=True, king=False)
            elif piece == KING:
                san = "K"
                candidates = self.generate_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=False, queens=False, king=True)
            else:
                # Not possible with a legal move.
                assert self.is_legal(move)

            # Filter relevant candidates: Not excatly the current move, but
            # to the same square.
            others = BB_VOID
            for candidate in candidates:
                if candidate.to_square == move.to_square and candidate.from_square != move.from_square:
                    others |= BB_SQUARES[candidate.from_square]

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
                    san += RANK_NAMES[rank_index(move.from_square)]

        # Captures.
        if self.is_capture(move):
            if piece == PAWN:
                san += FILE_NAMES[file_index(move.from_square)]
            san += "x"

        # Destination square.
        san += SQUARE_NAMES[move.to_square]

        # Promotion.
        if move.promotion:
            san += "=" + PIECE_SYMBOLS[move.promotion].upper()

        # Add check or checkmate suffix
        if is_checkmate:
            san += "#"
        elif is_check:
            san += "+"

        return san

    def parse_san(self, san):
        """
        Uses the current position as the context to parse a move in standard
        algebraic notation and return the corresponding move object.

        The returned move is guaranteed to be either legal or a null move.

        Raises :exc:`ValueError` if the SAN is invalid or ambiguous.
        """
        # Null moves.
        if san == "--":
            return Move.null()

        # Castling.
        try:
            if san in ("O-O", "O-O+", "O-O#"):
                return next(move for move in self.generate_castling_moves() if self.is_kingside_castling(move))
            elif san in ("O-O-O", "O-O-O+", "O-O-O#"):
                return next(move for move in self.generate_castling_moves() if self.is_queenside_castling(move))
        except StopIteration:
            raise ValueError("illegal san: {0} in {1}".format(repr(san), self.fen()))

        # Match normal moves.
        match = SAN_REGEX.match(san)
        if not match:
            raise ValueError("invalid san: {0}".format(repr(san)))

        # Get target square.
        to_square = SQUARE_NAMES.index(match.group(4))

        # Get the promotion type.
        if not match.group(5):
            promotion = None
        else:
            promotion = PIECE_SYMBOLS.index(match.group(5)[-1].lower())

        # Filter by piece type.
        if match.group(1) == "N":
            moves = self.generate_legal_moves(castling=False, pawns=False, knights=True, bishops=False, rooks=False, queens=False, king=False)
        elif match.group(1) == "B":
            moves = self.generate_legal_moves(castling=False, pawns=False, knights=False, bishops=True, rooks=False, queens=False, king=False)
        elif match.group(1) == "K":
            moves = self.generate_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=False, queens=False, king=True)
        elif match.group(1) == "R":
            moves = self.generate_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=True, queens=False, king=False)
        elif match.group(1) == "Q":
            moves = self.generate_legal_moves(castling=False, pawns=False, knights=False, bishops=False, rooks=False, queens=True, king=False)
        else:
            moves = self.generate_legal_moves(castling=False, pawns=True, knights=False, bishops=False, rooks=False, queens=False, king=False)

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

            if matched_move:
                raise ValueError("ambiguous san: {0} in {1}".format(repr(san), self.fen()))

            matched_move = move

        if not matched_move:
            raise ValueError("illegal san: {0} in {1}".format(repr(san), self.fen()))

        return matched_move

    def push_san(self, san):
        """
        Parses a move in standard algebraic notation, makes the move and puts
        it on the the move stack.

        Raises :exc:`ValueError` if neither legal nor a null move.

        Returns the move.
        """
        move = self.parse_san(san)
        self.push(move)
        return move

    def uci(self, move, chess960=None):
        """
        Gets the UCI notation of the move.

        *chess960* defaults to the mode of the board. Pass ``True`` to force
        *UCI_Chess960* mode.
        """
        board_chess960 = self.chess960
        if chess960 is not None:
            self.chess960 = chess960

        move = self._to_chess960(move)
        move = uci = self._from_chess960(move.from_square, move.to_square, move.promotion)

        self.chess960 = board_chess960
        return move.uci()

    def parse_uci(self, uci):
        """
        Parses the given move in UCI notation.

        Supports both UCI_Chess960 and standard UCI notation.

        The returned move is guaranteed to be either legal or a null move.

        Raises :exc:`ValueError` if the move is invalid or illegal in the
        current position (but not a null move).
        """
        move = Move.from_uci(uci)

        if not move:
            return move

        move = self._to_chess960(move)
        move = self._from_chess960(move.from_square, move.to_square, move.promotion)

        if not self.is_legal(move):
            raise ValueError("illegal uci: {0} in {1}".format(repr(uci), self.fen()))

        return move

    def push_uci(self, uci):
        """
        Parses a move in UCI notation and puts it on the move stack.

        Raises :exc:`ValueError` if the move is invalid or illegal in the
        current position (but not a null move).

        Returns the move.
        """
        move = self.parse_uci(uci)
        self.push(move)
        return move

    def is_en_passant(self, move):
        """Checks if the given pseudo-legal move is an en passant capture."""
        diff = abs(move.to_square - move.from_square)

        if diff not in (7, 9):
            return False

        if not self.pawns & BB_SQUARES[move.from_square]:
            return False

        if self.occupied & BB_SQUARES[move.to_square]:
            return False

        return True

    def is_capture(self, move):
        """Checks if the given pseudo-legal move is a capture."""
        return BB_SQUARES[move.to_square] & self.occupied_co[not self.turn] or self.is_en_passant(move)

    def is_castling(self, move):
        """Checks if the given pseudo-legal move is a castling move."""
        if BB_SQUARES[move.to_square] & self.occupied_co[self.turn] & self.rooks:
            return True

        diff = file_index(move.from_square) - file_index(move.to_square)
        if abs(diff) > 1 and self.piece_type_at(move.from_square) == KING:
            return True

        return False

    def is_kingside_castling(self, move):
        """
        Checks if the given pseudo-legal move is a kingside castling move.
        """
        return self.is_castling(move) and file_index(move.to_square) > file_index(move.from_square)

    def is_queenside_castling(self, move):
        """
        Checks if the given pseudo-legal move is a queenside castling move.
        """
        return self.is_castling(move) and file_index(move.to_square) < file_index(move.from_square)

    def has_castling_rights(self, color):
        """Checks if the given side has castling rights."""
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
        return bool(self.castling_rights & backrank)

    def has_kingside_castling_rights(self, color):
        """
        Checks if the given side has kingside (that is h-side in Chess960)
        castling rights.
        """
        king_mask = self.kings & self.occupied_co[color]
        if not king_mask:
            return False

        king_file = file_index(bit_scan(king_mask))
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8

        castling_rights = self.castling_rights & backrank
        while castling_rights:
            rook = castling_rights & -castling_rights
            rook_file = file_index(bit_scan(rook))

            if rook_file > king_file:
                return True

            castling_rights = castling_rights & (castling_rights - 1)

        return False

    def has_queenside_castling_rights(self, color):
        """
        Checks if the given side has queenside (that is a-side in Chess960)
        castling rights.
        """
        king_mask = self.kings & self.occupied_co[color]
        if not king_mask:
            return False

        king_file = file_index(bit_scan(king_mask))
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8

        castling_rights = self.castling_rights & backrank
        while castling_rights:
            rook = castling_rights & -castling_rights
            rook_file = file_index(bit_scan(rook))

            if rook_file < king_file:
                return True

            castling_rights = castling_rights & (castling_rights - 1)

        return False

    def has_chess960_castling_rights(self):
        """
        Checks if there are castling rights that are only possible in Chess960.
        """
        # Standard chess castling rights can only be on the standard
        # starting rook squares.
        if self.castling_rights & ~(BB_A1 | BB_A8 | BB_H1 | BB_H8):
            return True

        # If there are any castling rights in standard chess, the king must be
        # on e1 or e8.
        if self.has_castling_rights(WHITE) and not self.occupied_co[WHITE] & self.kings & BB_E1:
            return True
        if self.has_castling_rights(BLACK) and not self.occupied_co[BLACK] & self.kings & BB_E8:
            return True

        return False

    def status(self):
        """
        Gets a bitmask of possible problems with the position.

        Move making, generation and validation are only guaranteed to work on
        a completely valid board.

        :data:`~chess.STATUS_VALID` for a completely valid board.

        Otherwise bitwise combinations of:
        :data:`~chess.STATUS_NO_WHITE_KING`,
        :data:`~chess.STATUS_NO_BLACK_KING`,
        :data:`~chess.STATUS_TOO_MANY_KINGS`,
        :data:`~chess.STATUS_TOO_MANY_WHITE_PAWNS`,
        :data:`~chess.STATUS_TOO_MANY_BLACK_PAWNS`,
        :data:`~chess.STATUS_PAWNS_ON_BACKRANK`,
        :data:`~chess.STATUS_TOO_MANY_WHITE_PIECES`,
        :data:`~chess.STATUS_TOO_MANY_BLACK_PIECES`,
        :data:`~chess.STATUS_BAD_CASTLING_RIGHTS`,
        :data:`~chess.STATUS_INVALID_EP_SQUARE`,
        :data:`~chess.STATUS_OPPOSITE_CHECK`.
        """
        errors = STATUS_VALID

        # There must be exactly one king of each color.
        if not self.occupied_co[WHITE] & self.kings:
            errors |= STATUS_NO_WHITE_KING
        if not self.occupied_co[BLACK] & self.kings:
            errors |= STATUS_NO_BLACK_KING
        if pop_count(self.occupied & self.kings) > 2:
            errors |= STATUS_TOO_MANY_KINGS

        # There can not be more than 16 pieces of any color.
        if pop_count(self.occupied_co[WHITE]) > 16:
            errors |= STATUS_TOO_MANY_WHITE_PIECES
        if pop_count(self.occupied_co[BLACK]) > 16:
            errors |= STATUS_TOO_MANY_BLACK_PIECES

        # There can not be more than eight pawns of any color.
        if pop_count(self.occupied_co[WHITE] & self.pawns) > 8:
            errors |= STATUS_TOO_MANY_WHITE_PAWNS
        if pop_count(self.occupied_co[BLACK] & self.pawns) > 8:
            errors |= STATUS_TOO_MANY_BLACK_PAWNS

        # Pawns can not be on the backrank.
        if self.pawns & (BB_RANK_1 | BB_RANK_8):
            errors |= STATUS_PAWNS_ON_BACKRANK

        if self.castling_rights:
            white_castling_rights = self.castling_rights & BB_RANK_1
            black_castling_rights = self.castling_rights & BB_RANK_8

            if self.chess960:
                # Can only castle on the backrank.
                if self.castling_rights & ~(BB_RANK_1 | BB_RANK_8):
                    errors |= STATUS_BAD_CASTLING_RIGHTS

                # The king must be on the backrank.
                if white_castling_rights and not self.occupied_co[WHITE] & self.kings & BB_RANK_1:
                    errors |= STATUS_BAD_CASTLING_RIGHTS
                if black_castling_rights and not self.occupied_co[BLACK] & self.kings & BB_RANK_8:
                    errors |= STATUS_BAD_CASTLING_RIGHTS
            elif self.has_chess960_castling_rights():
                errors |= STATUS_BAD_CASTLING_RIGHTS

            # There must be rooks to castle with.
            if white_castling_rights & ~(self.occupied_co[WHITE] & self.rooks):
                errors |= STATUS_BAD_CASTLING_RIGHTS
            if black_castling_rights & ~(self.occupied_co[BLACK] & self.rooks):
                errors |= STATUS_BAD_CASTLING_RIGHTS

            # There are only two ways of castling: a-side and h-side.
            if pop_count(white_castling_rights) > 2:
                errors |= STATUS_BAD_CASTLING_RIGHTS
            if pop_count(black_castling_rights) > 2:
                errors |= STATUS_BAD_CASTLING_RIGHTS

            # The king must be between rooks with castling rights.
            if pop_count(white_castling_rights) == 2:
                king = bit_scan(self.occupied_co[WHITE] & self.kings)
                a_side = bit_scan(white_castling_rights)
                h_side = bit_scan(white_castling_rights, a_side + 1)
                if not (a_side < king < h_side):
                    errors |= STATUS_BAD_CASTLING_RIGHTS
            if pop_count(black_castling_rights) == 2:
                king = bit_scan(self.occupied_co[BLACK] & self.kings)
                a_side = bit_scan(black_castling_rights)
                h_side = bit_scan(black_castling_rights, a_side + 1)
                if not (a_side < king < h_side):
                    errors |= STATUS_BAD_CASTLING_RIGHTS

        if self.ep_square:
            if self.turn == WHITE:
                ep_rank = 5
                pawn_mask = shift_down(BB_SQUARES[self.ep_square])
                seventh_rank_mask = shift_up(BB_SQUARES[self.ep_square])
            else:
                ep_rank = 2
                pawn_mask = shift_up(BB_SQUARES[self.ep_square])
                seventh_rank_mask = shift_down(BB_SQUARES[self.ep_square])

            # The en passant square must be on the third or sixth rank.
            if rank_index(self.ep_square) != ep_rank:
                errors |= STATUS_INVALID_EP_SQUARE

            # The last move must have been a double pawn push, so there must
            # be a pawn of the correct color on the fourth or fifth rank.
            if not self.pawns & self.occupied_co[not self.turn] & pawn_mask:
                errors |= STATUS_INVALID_EP_SQUARE

            # And the en passant square must be empty.
            if self.occupied & BB_SQUARES[self.ep_square]:
                errors |= STATUS_INVALID_EP_SQUARE

            # And the second rank must be empty.
            if self.occupied & seventh_rank_mask:
                errors |= STATUS_INVALID_EP_SQUARE

        if not errors & (STATUS_NO_WHITE_KING | STATUS_NO_BLACK_KING | STATUS_TOO_MANY_KINGS):
            if self.was_into_check():
                errors |= STATUS_OPPOSITE_CHECK

        return errors

    def is_valid(self):
        """
        Checks if the board is valid.

        Move making, generation and validation are only guaranteed to work on
        a completely valid board.

        See :func:`~chess.Board.status()` for details.
        """
        return self.status() == STATUS_VALID

    def generate_attacks(self):
        if self.attacks_valid:
            return

        self.attacks_from = collections.defaultdict(int)
        self.attacks_to = collections.defaultdict(int)

        # Produce piece attacks.
        non_pawns = self.occupied & ~self.pawns
        queens_or_rooks = self.queens | self.rooks
        queens_or_bishops = self.queens | self.bishops

        while non_pawns:
            from_square = non_pawns & -non_pawns
            rank_pieces = RANK_MASK[from_square & queens_or_rooks] & self.occupied
            file_pieces = FILE_MASK[from_square & queens_or_rooks] & self.occupied
            ne_pieces = DIAG_MASK_NE[from_square & queens_or_bishops] & self.occupied
            nw_pieces = DIAG_MASK_NW[from_square & queens_or_bishops] & self.occupied

            moves = (KING_MOVES[from_square & self.kings] |
                     KNIGHT_MOVES[from_square & self.knights] |
                     RANK_ATTACKS[from_square & queens_or_rooks][rank_pieces] |
                     FILE_ATTACKS[from_square & queens_or_rooks][file_pieces] |
                     DIAG_ATTACKS_NE[from_square & queens_or_bishops][ne_pieces] |
                     DIAG_ATTACKS_NW[from_square & queens_or_bishops][nw_pieces])

            while moves:
                to_square = moves & -moves
                self.attacks_from[from_square] |= to_square
                self.attacks_to[to_square] |= from_square
                moves = moves & (moves - 1)

            non_pawns = non_pawns & (non_pawns - 1)

        # Produce pawn attacks.
        for white_to_move in [False, True]:
            if white_to_move:
                pawns = self.pawns & self.occupied_co[WHITE]
                right_captures = pawns << 9 & ~BB_FILE_A & BB_ALL
                left_captures = pawns << 7 & ~BB_FILE_H & BB_ALL
            else:
                pawns = self.pawns & self.occupied_co[BLACK]
                right_captures = pawns >> 7 & ~BB_FILE_A
                left_captures = pawns >> 9 & ~BB_FILE_H

            while right_captures:
                to_square = right_captures & -right_captures

                if white_to_move:
                    from_square = to_square >> 9
                else:
                    from_square = to_square << 7

                self.attacks_from[from_square] |= to_square
                self.attacks_to[to_square] |= from_square

                right_captures = right_captures & (right_captures - 1)

            while left_captures:
                to_square = left_captures & -left_captures

                if white_to_move:
                    from_square = to_square >> 7
                else:
                    from_square = to_square << 9

                self.attacks_from[from_square] |= to_square
                self.attacks_to[to_square] |= from_square

                left_captures = left_captures & (left_captures - 1)

        # Produce en passant attacks. Here we are actually targeting the
        # pawn, not the en passant square.
        if self.ep_square:
            if self.turn == WHITE:
                capturing_pawns = self.pawns & self.occupied_co[WHITE] & BB_RANK_5
            else:
                capturing_pawns = self.pawns & self.occupied_co[BLACK] & BB_RANK_4

            ep_square_mask = BB_SQUARES[self.ep_square]
            double_pawn = ep_square_mask << 8 if self.turn == BLACK else ep_square_mask >> 8

            # Left side capture.
            if ep_square_mask & ~BB_FILE_A:
                left_file = FILE_MASK[ep_square_mask] >> 1
                capturing_pawn = capturing_pawns & left_file
                if capturing_pawn:
                    self.attacks_from[capturing_pawn] |= double_pawn
                    self.attacks_to[double_pawn] |= capturing_pawn

            # Right side capture.
            if ep_square_mask & ~BB_FILE_H:
                right_file = FILE_MASK[ep_square_mask] << 1
                capturing_pawn = capturing_pawns & right_file
                if capturing_pawn:
                    self.attacks_from[capturing_pawn] |= double_pawn
                    self.attacks_to[double_pawn] |= capturing_pawn

        # Attacks are now valid.
        self.attacks_valid = True

    def _pinned(self, color, square_mask):
        self.generate_attacks()

        if color == WHITE:
            king = self.kings & self.occupied_co[WHITE]
            other_pieces = self.occupied_co[BLACK]
        else:
            king = self.kings & self.occupied_co[BLACK]
            other_pieces = self.occupied_co[WHITE]
        sliders = (self.rooks | self.bishops | self.queens) & other_pieces

        mask = BB_ALL

        for direction_masks, attack_table in [(FILE_MASK, FILE_ATTACKS),
                                              (RANK_MASK, RANK_ATTACKS),
                                              (DIAG_MASK_NW, DIAG_ATTACKS_NW),
                                              (DIAG_MASK_NE, DIAG_ATTACKS_NE)]:
            if direction_masks[square_mask] & direction_masks[king] & self.attacks_to[square_mask] & other_pieces:
                attackers = direction_masks[king] & self.attacks_to[square_mask] & sliders
                while attackers:
                    attacker = attackers & -attackers

                    pieces = direction_masks[king] & self.occupied & ~square_mask
                    if attack_table[attacker][pieces] & king:
                        mask = direction_masks[king]

                    attackers = attackers & (attackers - 1)

                break

        return mask

    def generate_legal_moves(self, castling=True, pawns=True, knights=True, bishops=True, rooks=True, queens=True, king=True):
        if self.is_check():
            return self.generate_evasions(castling=castling, pawns=pawns, knights=knights, bishops=bishops, rooks=rooks, queens=queens, king=king)
        else:
            return self.generate_non_evasions(castling=castling, pawns=pawns, knights=knights, bishops=bishops, rooks=rooks, queens=queens, king=king)

    def generate_non_evasions(self, castling=True, pawns=True, knights=True, bishops=True, rooks=True, queens=True, king=True):
        self.generate_attacks()

        our_pieces = self.occupied_co[self.turn]
        their_pieces = self.occupied_co[not self.turn]

        # Selective move generation.
        selected_pieces = BB_VOID
        if knights:
            selected_pieces |= self.knights
        if bishops:
            selected_pieces |= self.bishops
        if rooks:
            selected_pieces |= self.rooks
        if queens:
            selected_pieces |= self.queens
        if king:
            selected_pieces |= self.kings

        # Generate piece moves.
        non_pawns = our_pieces & selected_pieces
        while non_pawns:
            from_square = non_pawns & -non_pawns
            from_square_index = bit_scan(from_square)

            mask = self._pinned(self.turn, from_square)
            moves = self.attacks_from[from_square] & ~our_pieces & mask
            while moves:
                to_square = moves & -moves

                if from_square & self.kings and self.attacks_to[to_square] & their_pieces:
                    # Do not move the king into check.
                    pass
                else:
                    yield Move(from_square_index, bit_scan(to_square))

                moves = moves & (moves - 1)

            non_pawns = non_pawns & (non_pawns - 1)

        # Generate castling moves. Since we are generating non-evasions we
        # already know that we are not in check.
        if castling:
            for move in self.generate_castling_moves():
                yield move

        # The remaining moves are all pawn moves.
        if not pawns:
            return

        # Generate pawn captures.
        pawns = self.pawns & our_pieces
        if self.turn == WHITE:
            right_captures = pawns << 9 & their_pieces & ~BB_FILE_A & BB_ALL
            left_captures = pawns << 7 & their_pieces & ~BB_FILE_H & BB_ALL
        else:
            right_captures = pawns >> 7 & their_pieces & ~BB_FILE_A
            left_captures = pawns >> 9 & their_pieces & ~BB_FILE_H

        # Yield right captures.
        while right_captures:
            to_square = right_captures & -right_captures
            to_square_index = bit_scan(to_square)

            if self.turn == WHITE:
                from_square = to_square >> 9
            else:
                from_square = to_square << 7
            from_square_index = bit_scan(from_square)

            mask = self._pinned(self.turn, from_square)
            if mask & to_square:
                if BB_RANK_1 & to_square or BB_RANK_8 & to_square:
                    yield Move(from_square_index, to_square_index, QUEEN)
                    yield Move(from_square_index, to_square_index, ROOK)
                    yield Move(from_square_index, to_square_index, BISHOP)
                    yield Move(from_square_index, to_square_index, KNIGHT)
                else:
                    yield Move(from_square_index, to_square_index)

            right_captures = right_captures & (right_captures - 1)

        # Yield left captures.
        while left_captures:
            to_square = left_captures & -left_captures
            to_square_index = bit_scan(to_square)

            if self.turn == WHITE:
                from_square = to_square >> 7
            else:
                from_square = to_square << 9
            from_square_index = bit_scan(from_square)

            mask = self._pinned(self.turn, from_square)
            if mask & to_square:
                if BB_RANK_1 & to_square or BB_RANK_8 & to_square:
                    yield Move(from_square_index, to_square_index, QUEEN)
                    yield Move(from_square_index, to_square_index, ROOK)
                    yield Move(from_square_index, to_square_index, BISHOP)
                    yield Move(from_square_index, to_square_index, KNIGHT)
                else:
                    yield Move(from_square_index, to_square_index)

            left_captures = left_captures & (left_captures - 1)

        # Generate en passant captures.
        ep_square_mask = BB_SQUARES[self.ep_square] if self.ep_square else BB_VOID
        if ep_square_mask:
            if self.turn == WHITE:
                capturing_pawns = pawns & BB_RANK_5
            else:
                capturing_pawns = pawns & BB_RANK_4

            # Left side capture.
            if ep_square_mask & ~BB_FILE_A:
                left_file = FILE_MASK[ep_square_mask] >> 1
                capturing_pawn = capturing_pawns & left_file
                if capturing_pawn:
                    mask = self._pinned(self.turn, capturing_pawn)
                    if mask & ep_square_mask:
                        yield Move(bit_scan(capturing_pawn), self.ep_square)

            # Right side capture.
            if ep_square_mask & ~BB_FILE_H:
                right_file = FILE_MASK[ep_square_mask] << 1
                capturing_pawn = capturing_pawns & right_file
                if capturing_pawn:
                    mask = self._pinned(self.turn, capturing_pawn)
                    if mask & ep_square_mask:
                        yield Move(bit_scan(capturing_pawn), self.ep_square)

        # Prepare pawn advance generation.
        if self.turn == WHITE:
            single_moves = pawns << 8 & ~self.occupied
            double_moves = single_moves << 8 & ~self.occupied & BB_RANK_4
        else:
            single_moves = pawns >> 8 & ~self.occupied
            double_moves = single_moves >> 8 & ~self.occupied & BB_RANK_5

        # Generate single pawn moves.
        while single_moves:
            to_square = single_moves & -single_moves
            to_square_index = bit_scan(to_square)

            if self.turn == WHITE:
                from_square = to_square >> 8
            else:
                from_square = to_square << 8
            from_square_index = bit_scan(from_square)

            mask = self._pinned(self.turn, from_square)
            if mask & to_square:
                if BB_RANK_1 & to_square or BB_RANK_8 & to_square:
                    yield Move(from_square_index, to_square_index, QUEEN)
                    yield Move(from_square_index, to_square_index, ROOK)
                    yield Move(from_square_index, to_square_index, BISHOP)
                    yield Move(from_square_index, to_square_index, KNIGHT)
                else:
                    yield Move(from_square_index, to_square_index)

            single_moves = single_moves & (single_moves - 1)

        # Generate double pawn moves.
        while double_moves:
            to_square = double_moves & -double_moves
            to_square_index = bit_scan(to_square)

            if self.turn == WHITE:
                from_square = to_square >> 16
            else:
                from_square = to_square << 16
            from_square_index = bit_scan(from_square)

            mask = self._pinned(self.turn, from_square)
            if mask & to_square:
                yield Move(from_square_index, to_square_index)

            double_moves = double_moves & (double_moves - 1)

    def generate_castling_moves(self):
        if self.is_check():
            return

        king = self.occupied_co[self.turn] & self.kings
        king_file_index = file_index(bit_scan(king))
        backrank = BB_RANK_1 if self.turn == WHITE else BB_RANK_8

        bb_a = BB_FILE_A & backrank
        bb_c = BB_FILE_C & backrank
        bb_d = BB_FILE_D & backrank
        bb_f = BB_FILE_F & backrank
        bb_g = BB_FILE_G & backrank

        candidates = self.castling_rights & backrank
        while candidates:
            rook = candidates & -candidates
            rook_file_index = file_index(bit_scan(rook))

            a_side = rook_file_index < king_file_index

            # In the special case where we castle queenside and our rook
            # shielded us from an attack from a1 or a8, castling would be
            # into check.
            if a_side and rook & BB_FILE_B and self.occupied_co[not self.turn] & (self.queens | self.rooks) & bb_a:
                candidates = candidates & (candidates - 1)
                continue

            empty_for_rook = BB_VOID
            empty_for_king = BB_VOID

            if a_side:
                if not rook & bb_d:
                    empty_for_rook = (
                        RANK_ATTACKS[rook][rook | bb_d] &
                        RANK_ATTACKS[bb_d][bb_d | rook])
                    empty_for_rook |= bb_d

                if not king & bb_c:
                    empty_for_king = (
                        RANK_ATTACKS[king][king | bb_c] &
                        RANK_ATTACKS[bb_c][bb_c | king])
                    empty_for_king |= bb_c
            else:
                if not rook & bb_f:
                    empty_for_rook = (
                        RANK_ATTACKS[rook][rook | bb_f] &
                        RANK_ATTACKS[bb_f][bb_f | rook])
                    empty_for_rook |= bb_f

                if not king & bb_g:
                    empty_for_king = (
                        RANK_ATTACKS[king][king | bb_g] &
                        RANK_ATTACKS[bb_g][bb_g | king])
                    empty_for_king |= bb_g

            empty_for_rook &= ~king
            empty_for_rook &= ~rook

            empty_for_king &= ~king
            not_attacked_for_king = empty_for_king
            empty_for_king &= ~rook

            if not self.occupied & (empty_for_king | empty_for_rook):
                none_attacked = True
                while not_attacked_for_king:
                    test_attack = not_attacked_for_king & -not_attacked_for_king
                    if self.attacks_to[test_attack] & self.occupied_co[not self.turn]:
                        none_attacked = False
                        break
                    not_attacked_for_king = not_attacked_for_king & (not_attacked_for_king - 1)

                if none_attacked:
                    yield self._from_chess960(bit_scan(king), bit_scan(rook))

            candidates = candidates & (candidates - 1)

    def generate_evasions(self, castling=True, pawns=True, knights=True, bishops=True, rooks=True, queens=True, king=True):
        self.generate_attacks()

        # Selective move generation.
        selected_pieces = BB_VOID
        if pawns:
            selected_pieces |= self.pawns
        if knights:
            selected_pieces |= self.knights
        if bishops:
            selected_pieces |= self.bishops
        if rooks:
            selected_pieces |= self.rooks
        if queens:
            selected_pieces |= self.queens
        if king:
            selected_pieces |= self.kings

        # Prepare basic information.
        our_pieces = self.occupied_co[self.turn]
        their_pieces = self.occupied_co[not self.turn]
        our_king = self.kings & our_pieces

        our_pawns = self.pawns & our_pieces
        en_passant_mask = BB_SQUARES[self.ep_square] if self.ep_square else 0
        double_pawn_mask = BB_VOID
        en_passant_capturers = BB_VOID

        if self.turn == WHITE:
            forward_pawns = our_pawns << 8 & BB_ALL
            double_forward_pawns = (our_pawns & BB_RANK_2) << 16 & BB_ALL

            if en_passant_mask:
                double_pawn_mask = en_passant_mask >> 8

            # Capture torward the right.
            if en_passant_mask & ~BB_FILE_A:
                en_passant_capturers |= our_pawns & BB_RANK_5 & FILE_MASK[en_passant_mask] >> 1

            # Capture toward the left.
            if en_passant_mask & ~BB_FILE_H:
                en_passant_capturers |= our_pawns & BB_RANK_5 & FILE_MASK[en_passant_mask] << 1
        else:
            forward_pawns = our_pawns >> 8
            double_forward_pawns = (our_pawns & BB_RANK_7) >> 16

            if en_passant_mask:
                double_pawn_mask = en_passant_mask << 8

            # Capture torward the right.
            if en_passant_mask & ~BB_FILE_A:
                en_passant_capturers |= our_pawns & BB_RANK_4 & FILE_MASK[en_passant_mask] >> 1

            # Capture toward the left.
            if en_passant_mask & ~BB_FILE_H:
                en_passant_capturers |= our_pawns & BB_RANK_4 & FILE_MASK[en_passant_mask] << 1

        # Look up all pieces giving check.
        king_attackers = self.attacks_to[our_king] & their_pieces
        king_attackers_index = bit_scan(king_attackers)
        assert king_attackers
        num_attackers = pop_count(king_attackers)

        if num_attackers == 1:
            # There is one attacker, so it can be captured. If there are more
            # than one attackers we can not capture both at the same time,
            # so the king would have to be moved.
            attacker_attackers = self.attacks_to[king_attackers] & our_pieces & selected_pieces & ~our_king
            while attacker_attackers:
                attacker = attacker_attackers & -attacker_attackers
                attacker_index = bit_scan(attacker)

                mask = self._pinned(self.turn, attacker)
                if king_attackers & mask:
                    if king_attackers & double_pawn_mask and attacker & en_passant_capturers:
                        # Capture the attacking pawn en passant.
                        yield Move(attacker_index, self.ep_square)
                    elif attacker & our_pawns and king_attackers & (BB_RANK_8 | BB_RANK_1):
                        # Capture the attacker with a pawn and promote.
                        yield Move(attacker_index, king_attackers_index, QUEEN)
                        yield Move(attacker_index, king_attackers_index, ROOK)
                        yield Move(attacker_index, king_attackers_index, BISHOP)
                        yield Move(attacker_index, king_attackers_index, KNIGHT)
                    else:
                        yield Move(attacker_index, king_attackers_index)

                attacker_attackers = attacker_attackers & (attacker_attackers - 1)


        # Eliminate the sliding moves where we are still in check by the same
        # piece.
        attackers = king_attackers
        king_rank_mask = RANK_MASK[our_king]
        king_file_mask = FILE_MASK[our_king]
        king_diag_ne = DIAG_MASK_NE[our_king]
        king_diag_nw = DIAG_MASK_NW[our_king]
        attacker_masks = 0
        while attackers:
            attacker = attackers & -attackers

            if attacker & (self.queens | self.rooks | self.bishops):
                if king_rank_mask == RANK_MASK[attacker]:
                    attacker_masks |= king_rank_mask
                if king_file_mask == FILE_MASK[attacker]:
                    attacker_masks |= king_file_mask
                if king_diag_ne == DIAG_MASK_NE[attacker]:
                    attacker_masks |= king_diag_ne
                if king_diag_nw == DIAG_MASK_NW[attacker]:
                    attacker_masks |= king_diag_nw

            attackers = attackers & (attackers - 1)

        if king:
            # Move the king. Capturing other pieces or even the attacker is
            # allowed.
            moves = KING_MOVES[our_king] & ~our_pieces
            while moves:
                to_square = moves & -moves
                to_square_index = bit_scan(to_square)

                attacked_square = self.attacks_to[to_square] & their_pieces

                capture_attacker = to_square & attacker_masks & king_attackers
                any_capture = to_square & ~attacker_masks

                if to_square & their_pieces and not attacked_square and (capture_attacker or any_capture):
                    yield Move(bit_scan(our_king), to_square_index)
                elif to_square and not attacked_square and not (to_square & attacker_masks):
                    yield Move(bit_scan(our_king), to_square_index)

                moves = moves & (moves - 1)

        # Block the check.
        if num_attackers == 1:
            # Determine empty squares between the attacker and the king in
            # order to block the check.
            if king_rank_mask == RANK_MASK[king_attackers]:
                rank_pieces = king_rank_mask & self.occupied
                moves = RANK_ATTACKS[our_king][rank_pieces] & ~self.occupied & RANK_ATTACKS[king_attackers][rank_pieces]
            elif king_file_mask == FILE_MASK[king_attackers]:
                file_pieces = king_file_mask & self.occupied
                moves = FILE_ATTACKS[our_king][file_pieces] & ~self.occupied & FILE_ATTACKS[king_attackers][file_pieces]
            elif king_diag_ne == DIAG_MASK_NE[king_attackers]:
                ne_pieces = king_diag_ne & self.occupied
                moves = DIAG_ATTACKS_NE[our_king][ne_pieces] & ~self.occupied & DIAG_ATTACKS_NE[king_attackers][ne_pieces]
            elif king_diag_nw == DIAG_MASK_NW[king_attackers]:
                nw_pieces = king_diag_nw & self.occupied
                moves = DIAG_ATTACKS_NW[our_king][nw_pieces] & ~self.occupied & DIAG_ATTACKS_NW[king_attackers][nw_pieces]
            else:
                moves = 0

            # Try moving all pieces (except pawns and the king) to the empty
            # squares.
            while moves:
                empty_square = moves & -moves
                empty_square_index = bit_scan(empty_square)

                blockers = self.attacks_to[empty_square] & ~our_pawns & ~our_king & ~their_pieces & selected_pieces
                while blockers:
                    blocker = blockers & -blockers

                    mask = self._pinned(self.turn, blocker)
                    if mask & empty_square:
                        yield Move(bit_scan(blocker), empty_square_index)

                    blockers = blockers & (blockers - 1)

                # The following is all about handling pawns.
                if not pawns:
                    moves = moves & (moves - 1)
                    continue

                # Generate pawn advances to the empty square.
                blocking_pawn = empty_square & forward_pawns
                if blocking_pawn:
                    if self.turn == WHITE:
                        from_square = blocking_pawn >> 8
                    else:
                        from_square = blocking_pawn << 8
                    from_square_index = bit_scan(from_square)

                    mask = self._pinned(self.turn, from_square)
                    if mask & empty_square:
                        if empty_square & BB_RANK_1 or empty_square & BB_RANK_8:
                            yield Move(from_square_index, empty_square_index, QUEEN)
                            yield Move(from_square_index, empty_square_index, ROOK)
                            yield Move(from_square_index, empty_square_index, BISHOP)
                            yield Move(from_square_index, empty_square_index, KNIGHT)
                        else:
                            yield Move(from_square_index, empty_square_index)
                else:
                    # Generate double pawn advances to the empty square.
                    # Make sure the square inbetween is not occupied.
                    blocking_pawn = empty_square & double_forward_pawns
                    if blocking_pawn:
                        if self.turn == WHITE:
                            mask = self._pinned(self.turn, blocking_pawn >> 16)
                            if mask & empty_square and (empty_square >> 8) & ~self.occupied:
                                yield Move(bit_scan(blocking_pawn >> 16), empty_square_index)
                        else:
                            mask = self._pinned(self.turn, blocking_pawn << 16)
                            if mask & empty_square and (empty_square << 8) & ~self.occupied:
                                yield Move(bit_scan(blocking_pawn << 16), empty_square_index)

                moves = moves & (moves - 1)

    def _from_chess960(self, from_square, to_square, promotion=None):
        if not self.chess960 and from_square in [E1, E8] and to_square in [A1, H1, A8, H8] and self.piece_type_at(from_square) == KING:
            if from_square == E1:
                if to_square == H1:
                    return Move(E1, G1)
                elif to_square == A1:
                    return Move(E1, C1)
            elif from_square == E8:
                if to_square == H8:
                    return Move(E8, G8)
                elif to_square == A8:
                    return Move(E8, C8)

        return Move(from_square, to_square, promotion)

    def _to_chess960(self, move):
        if move.from_square in [E1, E8] and move.to_square in [C1, G1, C8, G8] and self.piece_type_at(move.from_square) == KING and self.piece_type_at(move.to_square) != ROOK:
            if move.from_square == E1:
                if move.to_square == G1:
                    return Move(E1, H1)
                elif move.to_square == C1:
                    return Move(E1, A1)
            elif move.from_square == E8:
                if move.to_square == G8:
                    return Move(E8, H8)
                elif move.to_square == C8:
                    return Move(E8, A8)

        return move

    def __repr__(self):
        if not self.chess960:
            return "Board('{0}')".format(self.fen())
        else:
            return "Board('{0}', chess960=True)".format(self.fen())

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

    def __unicode__(self, invert_color=False, borders=False):
        builder = []
        for rank_index in range(7, -1, -1):
            if borders:
                builder.append("  ")
                builder.append("-" * 17)
                builder.append("\n")

                builder.append(RANK_NAMES[rank_index])
                builder.append(" ")

            for file_index in range(8):
                square_index = square(file_index, rank_index)

                if borders:
                    builder.append("|")
                elif file_index > 0:
                    builder.append(" ")

                piece = self.piece_at(square_index)

                if piece:
                    builder.append(piece.unicode_symbol(invert_color=invert_color))
                else:
                    builder.append(".")

            if borders:
                builder.append("|")

            if borders or rank_index > 0:
                builder.append("\n")

        if borders:
            builder.append("  ")
            builder.append("-" * 17)
            builder.append("\n")
            builder.append("   a b c d e f g h")

        return "".join(builder)

    def __html__(self):
        """
        Returns a html-version of the board.
        Can be displayed in e.g. an IPython notebook using
        IPython.display.HTML(board.__html__())
        """
        tr = '<tr style="vertical-align:bottom;">'
        string = '<table style="text-align:center;\
                                border-spacing:0pt;\
                                font-family:\'Arial Unicode MS\';\
                                border-collapse:collapse;\
                                border-color:black;\
                                border-style:solid;\
                                border-width:0pt 0pt 0pt 0pt">'
        for rank in range(8,0,-1):
            string += tr
            string += '<td style="vertical-align:middle;\
                                  width:12pt">%d</td>' % rank
            for i,file_ in enumerate('a b c d e f g h'.split()):
                square = SQUARE_NAMES.index('%s%d' % (file_,rank))
                piece = self.piece_at(square)
                char = piece.unicode_symbol() if piece else ''
                if (i+rank) % 2 == 0:
                    string += '<td style="width:28pt;\
                                          height:28pt;\
                                          border-collapse:collapse;\
                                          border-color:black;\
                                          border-style:solid;\
                                          border-width:0pt 0pt 0pt 0pt">\
                                          <span style="font-size:250%%;">\
                                          %s</span></td>' % char
                else:
                    string += '<td style="background:silver;">\
                               <span style="font-size:250%%;">\
                               %s</span></td>' % char
            string += '</tr>'
        string += '<tr><td></td>'
        for file_ in 'a b c d e f g h'.split():
            string += '<td style="text-align:center">%s</td>' % file_
        string += '</tr></table>'
        return string

    def __eq__(self, board):
        return not self.__ne__(board)

    def __ne__(self, board):
        try:
            if self.chess960 != board.chess960:
                return True
            if self.occupied != board.occupied:
                return True
            if self.occupied_co[WHITE] != board.occupied_co[WHITE]:
                return True
            if self.pawns != board.pawns:
                return True
            if self.knights != board.knights:
                return True
            if self.bishops != board.bishops:
                return True
            if self.rooks != board.rooks:
                return True
            if self.queens != board.queens:
                return True
            if self.kings != board.kings:
                return True
            if self.ep_square != board.ep_square:
                return True
            if self.castling_rights != board.castling_rights:
                return True
            if self.turn != board.turn:
                return True
            if self.fullmove_number != board.fullmove_number:
                return True
            if self.halfmove_clock != board.halfmove_clock:
                return True
        except AttributeError:
            return True

        return False

    def zobrist_hash(self, array=None):
        """
        Returns a Zobrist hash of the current position.

        A zobrist hash is an exclusive or of pseudo random values picked from
        an array. Which values are picked is decided by features of the
        position, such as piece positions, castling rights and en passant
        squares. For this implementation an array of 781 values is required.

        The default behaviour is to use values from
        :data:`~chess.POLYGLOT_RANDOM_ARRAY`, which makes for hashes compatible
        with polyglot opening books.
        """
        # Hash in the board setup.
        zobrist_hash = self.board_zobrist_hash(array)

        # Default random array is polyglot compatible.
        if array is None:
            array = POLYGLOT_RANDOM_ARRAY

        # Hash in the castling flags.
        if self.has_kingside_castling_rights(WHITE):
            zobrist_hash ^= array[768]
        if self.has_queenside_castling_rights(WHITE):
            zobrist_hash ^= array[768 + 1]
        if self.has_kingside_castling_rights(BLACK):
            zobrist_hash ^= array[768 + 2]
        if self.has_queenside_castling_rights(BLACK):
            zobrist_hash ^= array[768 + 3]

        # Hash in the en passant file.
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
        square = bit_scan(squares)
        while square != -1 and square is not None:
            piece_index = (self.piece_type_at(square) - 1) * 2
            zobrist_hash ^= array[64 * piece_index + 8 * rank_index(square) + file_index(square)]
            square = bit_scan(squares, square + 1)

        squares = self.occupied_co[WHITE]
        square = bit_scan(squares)
        while square != -1 and square is not None:
            piece_index = (self.piece_type_at(square) - 1) * 2 + 1
            zobrist_hash ^= array[64 * piece_index + 8 * rank_index(square) + file_index(square)]
            square = bit_scan(squares, square + 1)

        return zobrist_hash

    def copy(self):
        """Creates a copy of the board."""
        board = type(self)(None)
        board.chess960 = self.chess960

        board.pawns = self.pawns
        board.knights = self.knights
        board.bishops = self.bishops
        board.rooks = self.rooks
        board.queens = self.queens
        board.kings = self.kings

        board.occupied_co[WHITE] = self.occupied_co[WHITE]
        board.occupied_co[BLACK] = self.occupied_co[BLACK]

        board.occupied = self.occupied

        board.ep_square = self.ep_square
        board.castling_rights = self.castling_rights
        board.turn = self.turn
        board.fullmove_number = self.fullmove_number
        board.halfmove_clock = self.halfmove_clock

        board.halfmove_clock_stack = copy.copy(self.halfmove_clock_stack)
        board.captured_piece_stack = copy.copy(self.captured_piece_stack)
        board.castling_right_stack = copy.copy(self.castling_right_stack)
        board.ep_square_stack = copy.copy(self.ep_square_stack)
        board.move_stack = copy.copy(self.move_stack)

        board.incremental_zobrist_hash = self.incremental_zobrist_hash
        board.transpositions = copy.copy(self.transpositions)

        board.attacks_valid = False

        return board

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        board = self.copy()
        memo[id(self)] = board
        return board

    @classmethod
    def empty(cls, chess960=False):
        """Creates a new empty board. Also see :func:`~chess.Board.clear()`."""
        return cls(None, chess960=chess960)

    @classmethod
    def from_epd(cls, epd, chess960=False):
        """
        Creates a new board from an EPD string. See
        :func:`~chess.Board.set_epd()`.

        Returns the board and the dictionary of parsed operations as a tuple.
        """
        board = cls.empty(chess960=chess960)
        return board, board.set_epd(epd)


class PseudoLegalMoveGenerator(object):

    def __init__(self, board):
        self.board = board

    def __bool__(self):
        return any(self.board.generate_pseudo_legal_moves())

    __nonzero__ = __bool__

    def __len__(self):
        return sum(1 for _ in self.board.generate_pseudo_legal_moves())

    def __iter__(self):
        return self.board.generate_pseudo_legal_moves()

    def __contains__(self, move):
        return self.board.is_pseudo_legal(move)

    def __repr__(self):
        builder = []

        for move in self:
            if self.board.is_legal(move):
                builder.append(self.board.san(move))
            else:
                builder.append(self.board.uci(move))

        sans = ", ".join(builder)

        return "<PeusdoLegalMoveGenerator at {0} ({1})>".format(hex(id(self)), sans)


class LegalMoveGenerator(object):

    def __init__(self, board):
        self.board = board

    def __bool__(self):
        return any(self.board.generate_legal_moves())

    __nonzero__ = __bool__

    def __len__(self):
        return sum(1 for _ in self.board.generate_legal_moves())

    def __iter__(self):
        return self.board.generate_legal_moves()

    def __contains__(self, move):
        return self.board.is_legal(move)

    def __repr__(self):
        sans = ", ".join(self.board.san(move) for move in self)
        return "<LegalMoveGenerator at {0} ({1})>".format(hex(id(self)), sans)


class SquareSet(object):
    """
    A set of squares.

    >>> squares = chess.SquareSet(chess.BB_B1 | chess.BB_G1)
    >>> squares
    SquareSet(0b1000010)

    >>> print(squares)
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . 1 . . . . 1 .

    >>> len(squares)
    2

    >>> bool(squares)
    True

    >>> chess.B1 in squares
    True

    >>> for square in squares:
    ...     # 1 -- chess.B1
    ...     # 6 -- chess.G1
    ...     print(square)
    ...
    1
    6

    >>> list(squares)
    [1, 6]

    Square sets are internally represented by 64 bit integer masks of the
    included squares. Bitwise operations can be used to compute unions,
    intersections and shifts.

    >>> int(squares)
    66

    Also supports common set operations like
    :func:`~chess.SquareSet.issubset()`, :func:`~chess.SquareSet.issuperset()`,
    :func:`~chess.SquareSet.union()`, :func:`~chess.SquareSet.intersection()`,
    :func:`~chess.SquareSet.difference()`,
    :func:`~chess.SquareSet.symmetric_difference()` and
    :func:`~chess.SquareSet.copy()` as well as
    :func:`~chess.SquareSet.update()`,
    :func:`~chess.SquareSet.intersection_update()`,
    :func:`~chess.SquareSet.difference_update()`,
    :func:`~chess.SquareSet.symmetric_difference_update()` and
    :func:`~chess.SquareSet.clear()`.

    :warning: Square sets can be used as dictionary keys, but do not modify
        them when doing this.
    """

    def __init__(self, mask=BB_VOID):
        self.mask = mask

    def issubset(self, other):
        return not bool(~self & other)

    def issuperset(self, other):
        return not bool(self & ~other)

    def union(self, other):
        return self | other

    def intersection(self, other):
        return self & other

    def difference(self, other):
        return self & ~other

    def symmetric_difference(self, other):
        return self ^ other

    def copy(self):
        return type(self)(self.mask)

    def update(self, other):
        self |= other

    def intersection_update(self, other):
        self &= other

    def difference_update(self, other):
        self &= ~other

    def symmetric_difference_update(self, other):
        self ^= other

    def add(self, square):
        """Add a square to the set."""
        self |= BB_SQUARES[square]

    def remove(self, square):
        """
        Remove a square from the set.

        Raises :exc:`KeyError` if the given square was not in the set.
        """
        mask = BB_SQUARES[square]
        if self.mask & mask:
            self.mask ^= mask
        else:
            raise KeyError(square)

    def discard(self, square):
        """Discards a square from the set."""
        self &= ~BB_SQUARES[square]

    def pop(self):
        """
        Removes a square from the set and returns it.

        Raises :exc:`KeyError` on an empty set.
        """
        if not self.mask:
            raise KeyError("pop from empty set")

        square_mask = self.mask & -self.mask
        self.mask = self.mask & (self.mask - 1)
        return bit_scan(square_mask)

    def clear(self):
        self.mask = BB_VOID

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
            return True

    def __len__(self):
        return pop_count(self.mask)

    def __iter__(self):
        square = bit_scan(self.mask)
        while square != -1 and square is not None:
            yield square
            square = bit_scan(self.mask, square + 1)

    def __reversed__(self):
        string = bin(self.mask)
        l = len(string)
        r = string.find("1", 0)
        while r != -1:
            yield l - r - 1
            r = string.find("1", r + 1)

    def __contains__(self, square):
        return bool(BB_SQUARES[square] & self.mask)

    def __lshift__(self, shift):
        return type(self)((self.mask << shift) & BB_ALL)

    def __rshift__(self, shift):
        return type(self)(self.mask >> shift)

    def __and__(self, other):
        try:
            return type(self)(self.mask & other.mask)
        except AttributeError:
            return type(self)(self.mask & other)

    def __xor__(self, other):
        try:
            return type(self)((self.mask ^ other.mask) & BB_ALL)
        except AttributeError:
            return type(self)((self.mask ^ other) & BB_ALL)

    def __or__(self, other):
        try:
            return type(self)((self.mask | other.mask) & BB_ALL)
        except AttributeError:
            return type(self)((self.mask | other) & BB_ALL)

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
        return type(self)(~self.mask & BB_ALL)

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
        return hash(self.mask)
