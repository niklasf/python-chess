# This file is part of the python-chess library.
# Copyright (C) 2012-2021 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

from __future__ import annotations

import collections
import math
import mmap
import os
import re
import struct
import threading
import typing

import chess

from types import TracebackType
from typing import Deque, Dict, Iterable, Iterator, List, Optional, Tuple, Type, TypeVar, Union


UINT64_BE = struct.Struct(">Q")
UINT32 = struct.Struct("<I")
UINT32_BE = struct.Struct(">I")
UINT16 = struct.Struct("<H")

TBPIECES = 7

TRIANGLE = [
    6, 0, 1, 2, 2, 1, 0, 6,
    0, 7, 3, 4, 4, 3, 7, 0,
    1, 3, 8, 5, 5, 8, 3, 1,
    2, 4, 5, 9, 9, 5, 4, 2,
    2, 4, 5, 9, 9, 5, 4, 2,
    1, 3, 8, 5, 5, 8, 3, 1,
    0, 7, 3, 4, 4, 3, 7, 0,
    6, 0, 1, 2, 2, 1, 0, 6,
]

INVTRIANGLE = [1, 2, 3, 10, 11, 19, 0, 9, 18, 27]

def offdiag(square: chess.Square) -> int:
    return chess.square_rank(square) - chess.square_file(square)

def flipdiag(square: chess.Square) -> chess.Square:
    return ((square >> 3) | (square << 3)) & 63

LOWER = [
    28,  0,  1,  2,  3,  4,  5,  6,
     0, 29,  7,  8,  9, 10, 11, 12,
     1,  7, 30, 13, 14, 15, 16, 17,
     2,  8, 13, 31, 18, 19, 20, 21,
     3,  9, 14, 18, 32, 22, 23, 24,
     4, 10, 15, 19, 22, 33, 25, 26,
     5, 11, 16, 20, 23, 25, 34, 27,
     6, 12, 17, 21, 24, 26, 27, 35,
]

DIAG = [
     0,  0,  0,  0,  0,  0,  0,  8,
     0,  1,  0,  0,  0,  0,  9,  0,
     0,  0,  2,  0,  0, 10,  0,  0,
     0,  0,  0,  3, 11,  0,  0,  0,
     0,  0,  0, 12,  4,  0,  0,  0,
     0,  0, 13,  0,  0,  5,  0,  0,
     0, 14,  0,  0,  0,  0,  6,  0,
    15,  0,  0,  0,  0,  0,  0,  7,
]

FLAP = [
    0,  0,  0,  0,  0,  0,  0, 0,
    0,  6, 12, 18, 18, 12,  6, 0,
    1,  7, 13, 19, 19, 13,  7, 1,
    2,  8, 14, 20, 20, 14,  8, 2,
    3,  9, 15, 21, 21, 15,  9, 3,
    4, 10, 16, 22, 22, 16, 10, 4,
    5, 11, 17, 23, 23, 17, 11, 5,
    0,  0,  0,  0,  0,  0,  0, 0,
]

PTWIST = [
     0,  0,  0,  0,  0,  0,  0,  0,
    47, 35, 23, 11, 10, 22, 34, 46,
    45, 33, 21,  9,  8, 20, 32, 44,
    43, 31, 19,  7,  6, 18, 30, 42,
    41, 29, 17,  5,  4, 16, 28, 40,
    39, 27, 15,  3,  2, 14, 26, 38,
    37, 25, 13,  1,  0, 12, 24, 36,
     0,  0,  0,  0,  0,  0,  0,  0,
]

INVFLAP = [
     8, 16, 24, 32, 40, 48,
     9, 17, 25, 33, 41, 49,
    10, 18, 26, 34, 42, 50,
    11, 19, 27, 35, 43, 51,
]

FILE_TO_FILE = [0, 1, 2, 3, 3, 2, 1, 0]

KK_IDX = [[
     -1,  -1,  -1,   0,   1,   2,   3,   4,
     -1,  -1,  -1,   5,   6,   7,   8,   9,
     10,  11,  12,  13,  14,  15,  16,  17,
     18,  19,  20,  21,  22,  23,  24,  25,
     26,  27,  28,  29,  30,  31,  32,  33,
     34,  35,  36,  37,  38,  39,  40,  41,
     42,  43,  44,  45,  46,  47,  48,  49,
     50,  51,  52,  53,  54,  55,  56,  57,
], [
     58,  -1,  -1,  -1,  59,  60,  61,  62,
     63,  -1,  -1,  -1,  64,  65,  66,  67,
     68,  69,  70,  71,  72,  73,  74,  75,
     76,  77,  78,  79,  80,  81,  82,  83,
     84,  85,  86,  87,  88,  89,  90,  91,
     92,  93,  94,  95,  96,  97,  98,  99,
    100, 101, 102, 103, 104, 105, 106, 107,
    108, 109, 110, 111, 112, 113, 114, 115,
], [
    116, 117,  -1,  -1,  -1, 118, 119, 120,
    121, 122,  -1,  -1,  -1, 123, 124, 125,
    126, 127, 128, 129, 130, 131, 132, 133,
    134, 135, 136, 137, 138, 139, 140, 141,
    142, 143, 144, 145, 146, 147, 148, 149,
    150, 151, 152, 153, 154, 155, 156, 157,
    158, 159, 160, 161, 162, 163, 164, 165,
    166, 167, 168, 169, 170, 171, 172, 173,
], [
    174,  -1,  -1,  -1, 175, 176, 177, 178,
    179,  -1,  -1,  -1, 180, 181, 182, 183,
    184,  -1,  -1,  -1, 185, 186, 187, 188,
    189, 190, 191, 192, 193, 194, 195, 196,
    197, 198, 199, 200, 201, 202, 203, 204,
    205, 206, 207, 208, 209, 210, 211, 212,
    213, 214, 215, 216, 217, 218, 219, 220,
    221, 222, 223, 224, 225, 226, 227, 228,
], [
    229, 230,  -1,  -1,  -1, 231, 232, 233,
    234, 235,  -1,  -1,  -1, 236, 237, 238,
    239, 240,  -1,  -1,  -1, 241, 242, 243,
    244, 245, 246, 247, 248, 249, 250, 251,
    252, 253, 254, 255, 256, 257, 258, 259,
    260, 261, 262, 263, 264, 265, 266, 267,
    268, 269, 270, 271, 272, 273, 274, 275,
    276, 277, 278, 279, 280, 281, 282, 283,
], [
    284, 285, 286, 287, 288, 289, 290, 291,
    292, 293,  -1,  -1,  -1, 294, 295, 296,
    297, 298,  -1,  -1,  -1, 299, 300, 301,
    302, 303,  -1,  -1,  -1, 304, 305, 306,
    307, 308, 309, 310, 311, 312, 313, 314,
    315, 316, 317, 318, 319, 320, 321, 322,
    323, 324, 325, 326, 327, 328, 329, 330,
    331, 332, 333, 334, 335, 336, 337, 338,
], [
     -1,  -1, 339, 340, 341, 342, 343, 344,
     -1,  -1, 345, 346, 347, 348, 349, 350,
     -1,  -1, 441, 351, 352, 353, 354, 355,
     -1,  -1,  -1, 442, 356, 357, 358, 359,
     -1,  -1,  -1,  -1, 443, 360, 361, 362,
     -1,  -1,  -1,  -1,  -1, 444, 363, 364,
     -1,  -1,  -1,  -1,  -1,  -1, 445, 365,
     -1,  -1,  -1,  -1,  -1,  -1,  -1, 446,
], [
     -1,  -1,  -1, 366, 367, 368, 369, 370,
     -1,  -1,  -1, 371, 372, 373, 374, 375,
     -1,  -1,  -1, 376, 377, 378, 379, 380,
     -1,  -1,  -1, 447, 381, 382, 383, 384,
     -1,  -1,  -1,  -1, 448, 385, 386, 387,
     -1,  -1,  -1,  -1,  -1, 449, 388, 389,
     -1,  -1,  -1,  -1,  -1,  -1, 450, 390,
     -1,  -1,  -1,  -1,  -1,  -1,  -1, 451,
], [
    452, 391, 392, 393, 394, 395, 396, 397,
     -1,  -1,  -1,  -1, 398, 399, 400, 401,
     -1,  -1,  -1,  -1, 402, 403, 404, 405,
     -1,  -1,  -1,  -1, 406, 407, 408, 409,
     -1,  -1,  -1,  -1, 453, 410, 411, 412,
     -1,  -1,  -1,  -1,  -1, 454, 413, 414,
     -1,  -1,  -1,  -1,  -1,  -1, 455, 415,
     -1,  -1,  -1,  -1,  -1,  -1,  -1, 456,
], [
    457, 416, 417, 418, 419, 420, 421, 422,
     -1, 458, 423, 424, 425, 426, 427, 428,
     -1,  -1,  -1,  -1,  -1, 429, 430, 431,
     -1,  -1,  -1,  -1,  -1, 432, 433, 434,
     -1,  -1,  -1,  -1,  -1, 435, 436, 437,
     -1,  -1,  -1,  -1,  -1, 459, 438, 439,
     -1,  -1,  -1,  -1,  -1,  -1, 460, 440,
     -1,  -1,  -1,  -1,  -1,  -1,  -1, 461,
]]

PP_IDX = [[
      0,  -1,   1,   2,   3,   4,   5,   6,
      7,   8,   9,  10,  11,  12,  13,  14,
     15,  16,  17,  18,  19,  20,  21,  22,
     23,  24,  25,  26,  27,  28,  29,  30,
     31,  32,  33,  34,  35,  36,  37,  38,
     39,  40,  41,  42,  43,  44,  45,  46,
     -1,  47,  48,  49,  50,  51,  52,  53,
     54,  55,  56,  57,  58,  59,  60,  61,
], [
     62,  -1,  -1,  63,  64,  65,  -1,  66,
     -1,  67,  68,  69,  70,  71,  72,  -1,
     73,  74,  75,  76,  77,  78,  79,  80,
     81,  82,  83,  84,  85,  86,  87,  88,
     89,  90,  91,  92,  93,  94,  95,  96,
     -1,  97,  98,  99, 100, 101, 102, 103,
     -1, 104, 105, 106, 107, 108, 109,  -1,
    110,  -1, 111, 112, 113, 114,  -1, 115,
], [
    116,  -1,  -1,  -1, 117,  -1,  -1, 118,
     -1, 119, 120, 121, 122, 123, 124,  -1,
     -1, 125, 126, 127, 128, 129, 130,  -1,
    131, 132, 133, 134, 135, 136, 137, 138,
     -1, 139, 140, 141, 142, 143, 144, 145,
     -1, 146, 147, 148, 149, 150, 151,  -1,
     -1, 152, 153, 154, 155, 156, 157,  -1,
    158,  -1,  -1, 159, 160,  -1,  -1, 161,
], [
    162,  -1,  -1,  -1,  -1,  -1,  -1, 163,
     -1, 164,  -1, 165, 166, 167, 168,  -1,
     -1, 169, 170, 171, 172, 173, 174,  -1,
     -1, 175, 176, 177, 178, 179, 180,  -1,
     -1, 181, 182, 183, 184, 185, 186,  -1,
     -1,  -1, 187, 188, 189, 190, 191,  -1,
     -1, 192, 193, 194, 195, 196, 197,  -1,
    198,  -1,  -1,  -1,  -1,  -1,  -1, 199,
], [
    200,  -1,  -1,  -1,  -1,  -1,  -1, 201,
     -1, 202,  -1,  -1, 203,  -1, 204,  -1,
     -1,  -1, 205, 206, 207, 208,  -1,  -1,
     -1, 209, 210, 211, 212, 213, 214,  -1,
     -1,  -1, 215, 216, 217, 218, 219,  -1,
     -1,  -1, 220, 221, 222, 223,  -1,  -1,
     -1, 224,  -1, 225, 226,  -1, 227,  -1,
    228,  -1,  -1,  -1,  -1,  -1,  -1, 229,
], [
    230,  -1,  -1,  -1,  -1,  -1,  -1, 231,
     -1, 232,  -1,  -1,  -1,  -1, 233,  -1,
     -1,  -1, 234,  -1, 235, 236,  -1,  -1,
     -1,  -1, 237, 238, 239, 240,  -1,  -1,
     -1,  -1,  -1, 241, 242, 243,  -1,  -1,
     -1,  -1, 244, 245, 246, 247,  -1,  -1,
     -1, 248,  -1,  -1,  -1,  -1, 249,  -1,
    250,  -1,  -1,  -1,  -1,  -1,  -1, 251,
], [
     -1,  -1,  -1,  -1,  -1,  -1,  -1, 259,
     -1, 252,  -1,  -1,  -1,  -1, 260,  -1,
     -1,  -1, 253,  -1,  -1, 261,  -1,  -1,
     -1,  -1,  -1, 254, 262,  -1,  -1,  -1,
     -1,  -1,  -1,  -1, 255,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1, 256,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1, 257,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1, 258,
], [
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1, 268,  -1,
     -1,  -1, 263,  -1,  -1, 269,  -1,  -1,
     -1,  -1,  -1, 264, 270,  -1,  -1,  -1,
     -1,  -1,  -1,  -1, 265,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1, 266,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1, 267,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
], [
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1, 274,  -1,  -1,
     -1,  -1,  -1, 271, 275,  -1,  -1,  -1,
     -1,  -1,  -1,  -1, 272,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1, 273,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
], [
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1, 277,  -1,  -1,  -1,
     -1,  -1,  -1,  -1, 276,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
     -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
]]

def test45(sq: chess.Square) -> bool:
    return bool(chess.BB_SQUARES[sq] & (chess.BB_A5 | chess.BB_A6 | chess.BB_A7 |
                                        chess.BB_B5 | chess.BB_B6 |
                                        chess.BB_C5))

MTWIST = [
    15, 63, 55, 47, 40, 48, 56, 12,
    62, 11, 39, 31, 24, 32,  8, 57,
    54, 38,  7, 23, 16,  4, 33, 49,
    46, 30, 22,  3,  0, 17, 25, 41,
    45, 29, 21,  2,  1, 18, 26, 42,
    53, 37,  6, 20, 19,  5, 34, 50,
    61, 10, 36, 28, 27, 35,  9, 58,
    14, 60, 52, 44, 43, 51, 59, 13,
]

def binom(x: int, y: int) -> int:
    try:
        return math.factorial(x) // math.factorial(y) // math.factorial(x - y)
    except ValueError:
        return 0

PAWNIDX = [[0 for _ in range(24)] for _ in range(5)]

PFACTOR = [[0 for _ in range(4)] for _ in range(5)]

for i in range(5):
    j = 0

    s = 0
    while j < 6:
        PAWNIDX[i][j] = s
        s += 1 if i == 0 else binom(PTWIST[INVFLAP[j]], i)
        j += 1
    PFACTOR[i][0] = s

    s = 0
    while j < 12:
        PAWNIDX[i][j] = s
        s += 1 if i == 0 else binom(PTWIST[INVFLAP[j]], i)
        j += 1
    PFACTOR[i][1] = s

    s = 0
    while j < 18:
        PAWNIDX[i][j] = s
        s += 1 if i == 0 else binom(PTWIST[INVFLAP[j]], i)
        j += 1
    PFACTOR[i][2] = s

    s = 0
    while j < 24:
        PAWNIDX[i][j] = s
        s += 1 if i == 0 else binom(PTWIST[INVFLAP[j]], i)
        j += 1
    PFACTOR[i][3] = s

MULTIDX = [[0 for _ in range(10)] for _ in range(5)]

MFACTOR = [0 for _ in range(5)]

for i in range(5):
    s = 0
    for j in range(10):
        MULTIDX[i][j] = s
        s += 1 if i == 0 else binom(MTWIST[INVTRIANGLE[j]], i)
    MFACTOR[i] = s

WDL_TO_MAP = [1, 3, 0, 2, 0]

PA_FLAGS = [8, 0, 0, 0, 4]

WDL_TO_DTZ = [-1, -101, 0, 101, 1]

PCHR = ["K", "Q", "R", "B", "N", "P"]

TABLENAME_REGEX = re.compile(r"^[KQRBNP]+v[KQRBNP]+\Z")


def is_tablename(name: str, *, one_king: bool = True, piece_count: Optional[int] = TBPIECES, normalized: bool = True) -> bool:
    return (
        (piece_count is None or len(name) <= piece_count + 1) and
        bool(TABLENAME_REGEX.match(name)) and
        (not normalized or normalize_tablename(name) == name) and
        (not one_king or (name != "KvK" and name.startswith("K") and "vK" in name)))


def tablenames(*, one_king: bool = True, piece_count: int = 6) -> Iterator[str]:
    first = "K" if one_king else "P"

    targets = []

    white_pieces = piece_count - 2
    black_pieces = 0
    while white_pieces >= black_pieces:
        targets.append(first + "P" * white_pieces + "v" + first + "P" * black_pieces)
        white_pieces -= 1
        black_pieces += 1

    return all_dependencies(targets, one_king=one_king)


def normalize_tablename(name: str, *, mirror: bool = False) -> str:
    w, b = name.split("v", 1)
    w = "".join(sorted(w, key=PCHR.index))
    b = "".join(sorted(b, key=PCHR.index))
    if mirror ^ ((len(w), [PCHR.index(c) for c in b]) < (len(b), [PCHR.index(c) for c in w])):
        return b + "v" + w
    else:
        return w + "v" + b


def _dependencies(target: str, *, one_king: bool = True) -> Iterator[str]:
    w, b = target.split("v", 1)

    for p in PCHR:
        if p == "K" and one_king:
            continue

        # Promotions.
        if p != "P" and "P" in w:
            yield normalize_tablename(w.replace("P", p, 1) + "v" + b)
        if p != "P" and "P" in b:
            yield normalize_tablename(w + "v" + b.replace("P", p, 1))

        # Captures.
        if p in w and len(w) > 1:
            yield normalize_tablename(w.replace(p, "", 1) + "v" + b)
        if p in b and len(b) > 1:
            yield normalize_tablename(w + "v" + b.replace(p, "", 1))


def dependencies(target: str, *, one_king: bool = True) -> Iterator[str]:
    closed = set()
    if one_king:
        closed.add("KvK")

    for dependency in _dependencies(target, one_king=one_king):
        if dependency not in closed and len(dependency) > 2:
            yield dependency
            closed.add(dependency)


def all_dependencies(targets: Iterable[str], *, one_king: bool = True) -> Iterator[str]:
    closed = set()
    if one_king:
        closed.add("KvK")

    open_list = [normalize_tablename(target) for target in targets]

    while open_list:
        name = open_list.pop()
        if name in closed:
            continue

        yield name
        closed.add(name)

        open_list.extend(_dependencies(name, one_king=one_king))


def calc_key(board: chess.BaseBoard, *, mirror: bool = False) -> str:
    w = board.occupied_co[chess.WHITE ^ mirror]
    b = board.occupied_co[chess.BLACK ^ mirror]

    return "".join([
        "K" * chess.popcount(board.kings & w),
        "Q" * chess.popcount(board.queens & w),
        "R" * chess.popcount(board.rooks & w),
        "B" * chess.popcount(board.bishops & w),
        "N" * chess.popcount(board.knights & w),
        "P" * chess.popcount(board.pawns & w),
        "v",
        "K" * chess.popcount(board.kings & b),
        "Q" * chess.popcount(board.queens & b),
        "R" * chess.popcount(board.rooks & b),
        "B" * chess.popcount(board.bishops & b),
        "N" * chess.popcount(board.knights & b),
        "P" * chess.popcount(board.pawns & b),
    ])


def recalc_key(pieces: List[chess.PieceType], *, mirror: bool = False) -> str:
    # Some endgames are stored with a different key than their filename
    # indicates: http://talkchess.com/forum/viewtopic.php?p=695509#695509

    w = 8 if mirror else 0
    b = 0 if mirror else 8

    return "".join([
        "K" * pieces.count(6 ^ w),
        "Q" * pieces.count(5 ^ w),
        "R" * pieces.count(4 ^ w),
        "B" * pieces.count(3 ^ w),
        "N" * pieces.count(2 ^ w),
        "P" * pieces.count(1 ^ w),
        "v",
        "K" * pieces.count(6 ^ b),
        "Q" * pieces.count(5 ^ b),
        "R" * pieces.count(4 ^ b),
        "B" * pieces.count(3 ^ b),
        "N" * pieces.count(2 ^ b),
        "P" * pieces.count(1 ^ b),
    ])


def subfactor(k: int, n: int) -> int:
    f = n
    l = 1

    for i in range(1, k):
        f *= n - i
        l *= i + 1

    return f // l


def dtz_before_zeroing(wdl: int) -> int:
    return ((wdl > 0) - (wdl < 0)) * (1 if abs(wdl) == 2 else 101)


class MissingTableError(KeyError):
    """Can not probe position because a required table is missing."""
    pass


class PairsData:
    indextable: int
    sizetable: int
    data: int
    offset: int
    symlen: List[int]
    sympat: int
    blocksize: int
    idxbits: int
    min_len: int
    base: List[int]


class PawnFileData:
    def __init__(self) -> None:
        self.precomp: Dict[int, PairsData] = {}
        self.factor: Dict[int, List[int]] = {}
        self.pieces: Dict[int, List[int]] = {}
        self.norm: Dict[int, List[int]] = {}


class PawnFileDataDtz:
    precomp: PairsData
    factor: List[int]
    pieces: List[int]
    norm: List[int]


TableT = TypeVar("TableT", bound="Table")

class Table:
    size: List[int]

    def __init__(self, path: str, *, variant: Type[chess.Board] = chess.Board) -> None:
        self.path = path
        self.variant = variant

        self.write_lock = threading.RLock()
        self.initialized = False
        self.fd: Optional[int] = None
        self.data: Optional[mmap.mmap] = None

        self.read_condition = threading.Condition()
        self.read_count = 0

        tablename, _ = os.path.splitext(os.path.basename(path))
        self.key = normalize_tablename(tablename)
        self.mirrored_key = normalize_tablename(tablename, mirror=True)
        self.symmetric = self.key == self.mirrored_key

        # Leave the v out of the tablename to get the number of pieces.
        self.num = len(tablename) - 1

        self.has_pawns = "P" in tablename

        black_part, white_part = tablename.split("v")
        if self.has_pawns:
            self.pawns = [white_part.count("P"), black_part.count("P")]
            if self.pawns[1] > 0 and (self.pawns[0] == 0 or self.pawns[1] < self.pawns[0]):
                self.pawns[0], self.pawns[1] = self.pawns[1], self.pawns[0]
        else:
            j = 0
            for piece_type in PCHR:
                if black_part.count(piece_type) == 1:
                    j += 1
                if white_part.count(piece_type) == 1:
                    j += 1
            if j >= 3:
                self.enc_type = 0
            elif j == 2:
                self.enc_type = 2
            else:  # only for suicide
                j = 16
                for _ in range(16):
                    for piece_type in PCHR:
                        if 1 < black_part.count(piece_type) < j:
                            j = black_part.count(piece_type)
                        if 1 < white_part.count(piece_type) < j:
                            j = white_part.count(piece_type)
                        self.enc_type = 1 + j

    def init_mmap(self) -> None:
        with self.write_lock:
            # Open fd.
            if self.fd is None:
                self.fd = os.open(self.path, os.O_RDONLY | os.O_BINARY if hasattr(os, "O_BINARY") else os.O_RDONLY)

            # Open mmap.
            if self.data is None:
                data = mmap.mmap(self.fd, 0, access=mmap.ACCESS_READ)
                if data.size() % 64 != 16:
                    raise IOError(f"invalid file size: ensure {self.path!r} is a valid syzygy tablebase file")
                self.data = data

                try:
                    # Python 3.8
                    self.data.madvise(mmap.MADV_RANDOM)
                except AttributeError:
                    pass

    def check_magic(self, magic: Optional[bytes], pawnless_magic: Optional[bytes]) -> None:
        assert self.data

        valid_magics = [magic, self.has_pawns and pawnless_magic]
        if self.data[:min(4, len(self.data))] not in valid_magics:
            raise IOError(f"invalid magic header: ensure {self.path!r} is a valid syzygy tablebase file")

    def setup_pairs(self, data_ptr: int, tb_size: int, size_idx: int, wdl: int) -> PairsData:
        assert self.data

        d = PairsData()

        self._flags = self.data[data_ptr]
        if self.data[data_ptr] & 0x80:
            d.idxbits = 0
            if wdl:
                d.min_len = self.data[data_ptr + 1]
            else:
                # http://www.talkchess.com/forum/viewtopic.php?p=698093#698093
                d.min_len = 1 if self.variant.captures_compulsory else 0
            self._next = data_ptr + 2
            self.size[size_idx + 0] = 0
            self.size[size_idx + 1] = 0
            self.size[size_idx + 2] = 0
            return d

        d.blocksize = self.data[data_ptr + 1]
        d.idxbits = self.data[data_ptr + 2]

        real_num_blocks = self.read_uint32(data_ptr + 4)
        num_blocks = real_num_blocks + self.data[data_ptr + 3]
        max_len = self.data[data_ptr + 8]
        min_len = self.data[data_ptr + 9]
        h = max_len - min_len + 1
        num_syms = self.read_uint16(data_ptr + 10 + 2 * h)

        d.offset = data_ptr + 10
        d.symlen = [0 for _ in range(h * 8 + num_syms)]
        d.sympat = data_ptr + 12 + 2 * h
        d.min_len = min_len

        self._next = data_ptr + 12 + 2 * h + 3 * num_syms + (num_syms & 1)

        num_indices = (tb_size + (1 << d.idxbits) - 1) >> d.idxbits
        self.size[size_idx + 0] = 6 * num_indices
        self.size[size_idx + 1] = 2 * num_blocks
        self.size[size_idx + 2] = (1 << d.blocksize) * real_num_blocks

        tmp = [0 for _ in range(num_syms)]
        for i in range(num_syms):
            if not tmp[i]:
                self.calc_symlen(d, i, tmp)

        d.base = [0 for _ in range(h)]
        d.base[h - 1] = 0
        for i in range(h - 2, -1, -1):
            d.base[i] = (d.base[i + 1] + self.read_uint16(d.offset + i * 2) - self.read_uint16(d.offset + i * 2 + 2)) // 2
        for i in range(h):
            d.base[i] <<= 64 - (min_len + i)

        d.offset -= 2 * d.min_len

        return d

    def set_norm_piece(self, norm: List[int], pieces: List[int]) -> None:
        if self.enc_type == 0:
            norm[0] = 3
        elif self.enc_type == 2:
            norm[0] = 2
        else:
            norm[0] = self.enc_type - 1

        i = norm[0]
        while i < self.num:
            j = i
            while j < self.num and pieces[j] == pieces[i]:
                norm[i] += 1
                j += 1
            i += norm[i]

    def calc_factors_piece(self, factor: List[int], order: int, norm: List[int]) -> int:
        if not self.variant.connected_kings:
            PIVFAC = [31332, 28056, 462]
        else:
            PIVFAC = [31332, 0, 518, 278]

        n = 64 - norm[0]

        f = 1
        i = norm[0]
        k = 0
        while i < self.num or k == order:
            if k == order:
                factor[0] = f
                if self.enc_type < 4:
                    f *= PIVFAC[self.enc_type]
                else:
                    f *= MFACTOR[self.enc_type - 2]
            else:
                factor[i] = f
                f *= subfactor(norm[i], n)
                n -= norm[i]
                i += norm[i]
            k += 1

        return f

    def calc_factors_pawn(self, factor: List[int], order: int, order2: int, norm: List[int], f: int) -> int:
        i = norm[0]
        if order2 < 0x0f:
            i += norm[i]
        n = 64 - i

        fac = 1
        k = 0
        while i < self.num or k in [order, order2]:
            if k == order:
                factor[0] = fac
                fac *= PFACTOR[norm[0] - 1][f]
            elif k == order2:
                factor[norm[0]] = fac
                fac *= subfactor(norm[norm[0]], 48 - norm[0])
            else:
                factor[i] = fac
                fac *= subfactor(norm[i], n)
                n -= norm[i]
                i += norm[i]
            k += 1

        return fac

    def set_norm_pawn(self, norm: List[int], pieces: List[int]) -> None:
        norm[0] = self.pawns[0]
        if self.pawns[1]:
            norm[self.pawns[0]] = self.pawns[1]

        i = self.pawns[0] + self.pawns[1]
        while i < self.num:
            j = i
            while j < self.num and pieces[j] == pieces[i]:
                norm[i] += 1
                j += 1
            i += norm[i]

    def calc_symlen(self, d: PairsData, s: int, tmp: List[int]) -> None:
        assert self.data

        w = d.sympat + 3 * s
        s2 = (self.data[w + 2] << 4) | (self.data[w + 1] >> 4)
        if s2 == 0x0fff:
            d.symlen[s] = 0
        else:
            s1 = ((self.data[w + 1] & 0xf) << 8) | self.data[w]
            if not tmp[s1]:
                self.calc_symlen(d, s1, tmp)
            if not tmp[s2]:
                self.calc_symlen(d, s2, tmp)
            d.symlen[s] = d.symlen[s1] + d.symlen[s2] + 1
        tmp[s] = 1

    def pawn_file(self, pos: List[chess.Square]) -> int:
        for i in range(1, self.pawns[0]):
            if FLAP[pos[0]] > FLAP[pos[i]]:
                pos[0], pos[i] = pos[i], pos[0]

        return FILE_TO_FILE[pos[0] & 0x07]

    def encode_piece(self, norm: List[int], pos: List[chess.Square], factor: List[int]) -> int:
        n = self.num

        if self.enc_type < 3:
            if pos[0] & 0x04:
                for i in range(n):
                    pos[i] ^= 0x07

            if pos[0] & 0x20:
                for i in range(n):
                    pos[i] ^= 0x38

            for i in range(n):
                if offdiag(pos[i]):
                    break
            if i < (3 if self.enc_type == 0 else 2) and offdiag(pos[i]) > 0:
                for i in range(n):
                    pos[i] = flipdiag(pos[i])

        if self.enc_type == 0:  # 111
            i = int(pos[1] > pos[0])
            j = int(pos[2] > pos[0]) + int(pos[2] > pos[1])

            if offdiag(pos[0]):
                idx = TRIANGLE[pos[0]] * 63 * 62 + (pos[1] - i) * 62 + (pos[2] - j)
            elif offdiag(pos[1]):
                idx = 6 * 63 * 62 + DIAG[pos[0]] * 28 * 62 + LOWER[pos[1]] * 62 + pos[2] - j
            elif offdiag(pos[2]):
                idx = 6 * 63 * 62 + 4 * 28 * 62 + (DIAG[pos[0]]) * 7 * 28 + (DIAG[pos[1]] - i) * 28 + LOWER[pos[2]]
            else:
                idx = 6 * 63 * 62 + 4 * 28 * 62 + 4 * 7 * 28 + (DIAG[pos[0]] * 7 * 6) + (DIAG[pos[1]] - i) * 6 + (DIAG[pos[2]] - j)
            i = 3
        elif self.enc_type == 2:  # K2
            if not self.variant.connected_kings:
                idx = KK_IDX[TRIANGLE[pos[0]]][pos[1]]
            else:
                i = pos[1] > pos[0]

                if offdiag(pos[0]):
                    idx = TRIANGLE[pos[0]] * 63 + (pos[1] - i)
                elif offdiag(pos[1]):
                    idx = 6 * 63 + DIAG[pos[0]] * 28 + LOWER[pos[1]]
                else:
                    idx = 6 * 63 + 4 * 28 + (DIAG[pos[0]]) * 7 + (DIAG[pos[1]] - i)

            i = 2
        elif self.enc_type == 3:  # 2, e.g. KKvK
            if TRIANGLE[pos[0]] > TRIANGLE[pos[1]]:
                pos[0], pos[1] = pos[1], pos[0]
            if pos[0] & 0x04:
                for i in range(n):
                    pos[i] ^= 0x07
            if pos[0] & 0x20:
                for i in range(n):
                    pos[i] ^= 0x38
            if offdiag(pos[0]) > 0 or (offdiag(pos[0]) == 0 and offdiag(pos[1]) > 0):
                for i in range(n):
                    pos[i] = flipdiag(pos[i])
            if test45(pos[1]) and TRIANGLE[pos[0]] == TRIANGLE[pos[1]]:
                pos[0], pos[1] = pos[1], pos[0]
                for i in range(n):
                    pos[i] = flipdiag(pos[i] ^ 0x38)
            idx = PP_IDX[TRIANGLE[pos[0]]][pos[1]]
            i = 2
        else:  # 3 and higher, e.g. KKKvK and KKKKvK
            for i in range(1, norm[0]):
                if TRIANGLE[pos[0]] > TRIANGLE[pos[i]]:
                    pos[0], pos[i] = pos[i], pos[0]
            if pos[0] & 0x04:
                for i in range(n):
                    pos[i] ^= 0x07
            if pos[0] & 0x20:
                for i in range(n):
                    pos[i] ^= 0x38
            if offdiag(pos[0]) > 0:
                for i in range(n):
                    pos[i] = flipdiag(pos[i])
            for i in range(1, norm[0]):
                for j in range(i + 1, norm[0]):
                    if MTWIST[pos[i]] > MTWIST[pos[j]]:
                        pos[i], pos[j] = pos[j], pos[i]

            idx = MULTIDX[norm[0] - 1][TRIANGLE[pos[0]]]
            i = 1
            while i < norm[0]:
                idx += binom(MTWIST[pos[i]], i)
                i += 1

        idx *= factor[0]

        while i < n:
            t = norm[i]

            for j in range(i, i + t):
                for k in range(j + 1, i + t):
                    # Swap.
                    if pos[j] > pos[k]:
                        pos[j], pos[k] = pos[k], pos[j]

            s = 0

            for m in range(i, i + t):
                p = pos[m]
                j = 0
                for l in range(i):
                    j += int(p > pos[l])
                s += binom(p - j, m - i + 1)

            idx += s * factor[i]
            i += t

        return idx

    def encode_pawn(self, norm: List[int], pos: List[chess.Square], factor: List[int]) -> int:
        n = self.num

        if pos[0] & 0x04:
            for i in range(n):
                pos[i] ^= 0x07

        for i in range(1, self.pawns[0]):
            for j in range(i + 1, self.pawns[0]):
                if PTWIST[pos[i]] < PTWIST[pos[j]]:
                    pos[i], pos[j] = pos[j], pos[i]

        t = self.pawns[0] - 1
        idx = PAWNIDX[t][FLAP[pos[0]]]
        for i in range(t, 0, -1):
            idx += binom(PTWIST[pos[i]], t - i + 1)
        idx *= factor[0]

        # Remaining pawns.
        i = self.pawns[0]
        t = i + self.pawns[1]
        if t > i:
            for j in range(i, t):
                for k in range(j + 1, t):
                    if pos[j] > pos[k]:
                        pos[j], pos[k] = pos[k], pos[j]
            s = 0
            for m in range(i, t):
                p = pos[m]
                j = 0
                for k in range(i):
                    j += int(p > pos[k])
                s += binom(p - j - 8, m - i + 1)
            idx += s * factor[i]
            i = t

        while i < n:
            t = norm[i]
            for j in range(i, i + t):
                for k in range(j + 1, i + t):
                    if pos[j] > pos[k]:
                        pos[j], pos[k] = pos[k], pos[j]

            s = 0
            for m in range(i, i + t):
                p = pos[m]
                j = 0
                for k in range(i):
                    j += int(p > pos[k])
                s += binom(p - j, m - i + 1)

            idx += s * factor[i]
            i += t

        return idx

    def decompress_pairs(self, d: PairsData, idx: int) -> int:
        assert self.data

        if not d.idxbits:
            return d.min_len

        mainidx = idx >> d.idxbits
        litidx = (idx & (1 << d.idxbits) - 1) - (1 << (d.idxbits - 1))
        block = self.read_uint32(d.indextable + 6 * mainidx)

        idx_offset = self.read_uint16(d.indextable + 6 * mainidx + 4)
        litidx += idx_offset

        if litidx < 0:
            while litidx < 0:
                block -= 1
                litidx += self.read_uint16(d.sizetable + 2 * block) + 1
        else:
            while litidx > self.read_uint16(d.sizetable + 2 * block):
                litidx -= self.read_uint16(d.sizetable + 2 * block) + 1
                block += 1

        ptr = d.data + (block << d.blocksize)

        m = d.min_len
        base_idx = -m
        symlen_idx = 0

        code = self.read_uint64_be(ptr)

        ptr += 2 * 4
        bitcnt = 0  # Number of empty bits in code
        while True:
            l = m
            while code < d.base[base_idx + l]:
                l += 1
            sym = self.read_uint16(d.offset + l * 2)
            sym += (code - d.base[base_idx + l]) >> (64 - l)
            if litidx < d.symlen[symlen_idx + sym] + 1:
                break
            litidx -= d.symlen[symlen_idx + sym] + 1
            code <<= l
            bitcnt += l
            if bitcnt >= 32:
                bitcnt -= 32
                code |= self.read_uint32_be(ptr) << bitcnt
                ptr += 4

            # Cut off at 64bit.
            code &= 0xffffffffffffffff

        sympat = d.sympat
        while d.symlen[symlen_idx + sym]:
            w = sympat + 3 * sym
            s1 = ((self.data[w + 1] & 0xf) << 8) | self.data[w]
            if litidx < d.symlen[symlen_idx + s1] + 1:
                sym = s1
            else:
                litidx -= d.symlen[symlen_idx + s1] + 1
                sym = (self.data[w + 2] << 4) | (self.data[w + 1] >> 4)

        w = sympat + 3 * sym
        if isinstance(self, DtzTable):
            return ((self.data[w + 1] & 0x0f) << 8) | self.data[w]
        else:
            return self.data[w]

    def read_uint64_be(self, data_ptr: int) -> int:
        return UINT64_BE.unpack_from(self.data, data_ptr)[0]  # type: ignore

    def read_uint32(self, data_ptr: int) -> int:
        return UINT32.unpack_from(self.data, data_ptr)[0]  # type: ignore

    def read_uint32_be(self, data_ptr: int) -> int:
        return UINT32_BE.unpack_from(self.data, data_ptr)[0]  # type: ignore

    def read_uint16(self, data_ptr: int) -> int:
        return UINT16.unpack_from(self.data, data_ptr)[0]  # type: ignore

    def close(self) -> None:
        with self.write_lock:
            with self.read_condition:
                while self.read_count > 0:
                    self.read_condition.wait()

                if self.data is not None:
                    self.data.close()
                    self.data = None

                if self.fd is not None:
                    os.close(self.fd)
                    self.fd = None

    def __enter__(self: TableT) -> TableT:
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.close()


class WdlTable(Table):
    _next: int
    _flags: int

    def init_table_wdl(self) -> None:
        with self.write_lock:
            self.init_mmap()
            assert self.data

            if self.initialized:
                return

            self.check_magic(self.variant.tbw_magic, self.variant.pawnless_tbw_magic)

            self.tb_size = [0 for _ in range(8)]
            self.size = [0 for _ in range(8 * 3)]

            # Used if there are only pieces.
            self.precomp: Dict[int, PairsData] = {}
            self.pieces: Dict[int, List[int]] = {}
            self.factor = [[0 for _ in range(TBPIECES)] for _ in range(2)]
            self.norm = [[0 for _ in range(self.num)] for _ in range(2)]

            # Used if there are pawns.
            self.files = [PawnFileData() for _ in range(4)]

            split = self.data[4] & 0x01
            files = 4 if self.data[4] & 0x02 else 1

            data_ptr = 5

            if not self.has_pawns:
                self.setup_pieces_piece(data_ptr)
                data_ptr += self.num + 1
                data_ptr += data_ptr & 0x01

                self.precomp[0] = self.setup_pairs(data_ptr, self.tb_size[0], 0, True)
                data_ptr = self._next
                if split:
                    self.precomp[1] = self.setup_pairs(data_ptr, self.tb_size[1], 3, True)
                    data_ptr = self._next

                self.precomp[0].indextable = data_ptr
                data_ptr += self.size[0]
                if split:
                    self.precomp[1].indextable = data_ptr
                    data_ptr += self.size[3]

                self.precomp[0].sizetable = data_ptr
                data_ptr += self.size[1]
                if split:
                    self.precomp[1].sizetable = data_ptr
                    data_ptr += self.size[4]

                data_ptr = (data_ptr + 0x3f) & ~0x3f
                self.precomp[0].data = data_ptr
                data_ptr += self.size[2]
                if split:
                    data_ptr = (data_ptr + 0x3f) & ~0x3f
                    self.precomp[1].data = data_ptr

                self.key = recalc_key(self.pieces[0])
                self.mirrored_key = recalc_key(self.pieces[0], mirror=True)
            else:
                s = 1 + int(self.pawns[1] > 0)
                for f in range(4):
                    self.setup_pieces_pawn(data_ptr, 2 * f, f)
                    data_ptr += self.num + s
                data_ptr += data_ptr & 0x01

                for f in range(files):
                    self.files[f].precomp[0] = self.setup_pairs(data_ptr, self.tb_size[2 * f], 6 * f, True)
                    data_ptr = self._next
                    if split:
                        self.files[f].precomp[1] = self.setup_pairs(data_ptr, self.tb_size[2 * f + 1], 6 * f + 3, True)
                        data_ptr = self._next

                for f in range(files):
                    self.files[f].precomp[0].indextable = data_ptr
                    data_ptr += self.size[6 * f]
                    if split:
                        self.files[f].precomp[1].indextable = data_ptr
                        data_ptr += self.size[6 * f + 3]

                for f in range(files):
                    self.files[f].precomp[0].sizetable = data_ptr
                    data_ptr += self.size[6 * f + 1]
                    if split:
                        self.files[f].precomp[1].sizetable = data_ptr
                        data_ptr += self.size[6 * f + 4]

                for f in range(files):
                    data_ptr = (data_ptr + 0x3f) & ~0x3f
                    self.files[f].precomp[0].data = data_ptr
                    data_ptr += self.size[6 * f + 2]
                    if split:
                        data_ptr = (data_ptr + 0x3f) & ~0x3f
                        self.files[f].precomp[1].data = data_ptr
                        data_ptr += self.size[6 * f + 5]

            self.initialized = True

    def setup_pieces_pawn(self, p_data: int, p_tb_size: int, f: int) -> None:
        assert self.data

        j = 1 + int(self.pawns[1] > 0)
        order = self.data[p_data] & 0x0f
        order2 = self.data[p_data + 1] & 0x0f if self.pawns[1] else 0x0f
        self.files[f].pieces[0] = [self.data[p_data + i + j] & 0x0f for i in range(self.num)]
        self.files[f].norm[0] = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm[0], self.files[f].pieces[0])
        self.files[f].factor[0] = [0 for _ in range(TBPIECES)]
        self.tb_size[p_tb_size] = self.calc_factors_pawn(self.files[f].factor[0], order, order2, self.files[f].norm[0], f)

        order = self.data[p_data] >> 4
        order2 = self.data[p_data + 1] >> 4 if self.pawns[1] else 0x0f
        self.files[f].pieces[1] = [self.data[p_data + i + j] >> 4 for i in range(self.num)]
        self.files[f].norm[1] = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm[1], self.files[f].pieces[1])
        self.files[f].factor[1] = [0 for _ in range(TBPIECES)]
        self.tb_size[p_tb_size + 1] = self.calc_factors_pawn(self.files[f].factor[1], order, order2, self.files[f].norm[1], f)

    def setup_pieces_piece(self, p_data: int) -> None:
        assert self.data

        self.pieces[0] = [self.data[p_data + i + 1] & 0x0f for i in range(self.num)]
        order = self.data[p_data] & 0x0f
        self.set_norm_piece(self.norm[0], self.pieces[0])
        self.tb_size[0] = self.calc_factors_piece(self.factor[0], order, self.norm[0])

        self.pieces[1] = [self.data[p_data + i + 1] >> 4 for i in range(self.num)]
        order = self.data[p_data] >> 4
        self.set_norm_piece(self.norm[1], self.pieces[1])
        self.tb_size[1] = self.calc_factors_piece(self.factor[1], order, self.norm[1])

    def probe_wdl_table(self, board: chess.Board) -> int:
        try:
            with self.read_condition:
                self.read_count += 1
            return self._probe_wdl_table(board)
        finally:
            with self.read_condition:
                self.read_count -= 1
                self.read_condition.notify()

    def _probe_wdl_table(self, board: chess.Board) -> int:
        self.init_table_wdl()

        key = calc_key(board)

        if not self.symmetric:
            if key != self.key:
                cmirror = 8
                mirror = 0x38
                bside = int(board.turn == chess.WHITE)
            else:
                cmirror = mirror = 0
                bside = int(board.turn != chess.WHITE)
        else:
            cmirror = 0 if board.turn == chess.WHITE else 8
            mirror = 0 if board.turn == chess.WHITE else 0x38
            bside = 0

        if not self.has_pawns:
            p = [0 for _ in range(TBPIECES)]
            i = 0
            while i < self.num:
                piece_type = self.pieces[bside][i] & 0x07
                color = (self.pieces[bside][i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

                for square in chess.scan_forward(bb):
                    p[i] = square
                    i += 1

            idx = self.encode_piece(self.norm[bside], p, self.factor[bside])
            res = self.decompress_pairs(self.precomp[bside], idx)
        else:
            p = [0 for _ in range(TBPIECES)]
            i = 0
            k = self.files[0].pieces[0][0] ^ cmirror
            color = k >> 3
            piece_type = k & 0x07
            bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

            for square in chess.scan_forward(bb):
                p[i] = square ^ mirror
                i += 1

            f = self.pawn_file(p)
            pc = self.files[f].pieces[bside]
            while i < self.num:
                color = (pc[i] ^ cmirror) >> 3
                piece_type = pc[i] & 0x07
                bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

                for square in chess.scan_forward(bb):
                    p[i] = square ^ mirror
                    i += 1

            idx = self.encode_pawn(self.files[f].norm[bside], p, self.files[f].factor[bside])
            res = self.decompress_pairs(self.files[f].precomp[bside], idx)

        return res - 2


class DtzTable(Table):

    def init_table_dtz(self) -> None:
        with self.write_lock:
            self.init_mmap()
            assert self.data

            if self.initialized:
                return

            self.check_magic(self.variant.tbz_magic, self.variant.pawnless_tbz_magic)

            self.factor = [0 for _ in range(TBPIECES)]
            self.norm = [0 for _ in range(self.num)]
            self.tb_size = [0, 0, 0, 0]
            self.size = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            self.files = [PawnFileDataDtz() for f in range(4)]

            files = 4 if self.data[4] & 0x02 else 1

            p_data = 5

            if not self.has_pawns:
                self.map_idx = [[0, 0, 0, 0]]

                self.setup_pieces_piece_dtz(p_data, 0)
                p_data += self.num + 1
                p_data += p_data & 0x01

                self.precomp = self.setup_pairs(p_data, self.tb_size[0], 0, False)
                self.flags: Union[int, List[int]] = self._flags
                p_data = self._next
                self.p_map = p_data
                if self.flags & 2:
                    if not self.flags & 16:
                        for i in range(4):
                            self.map_idx[0][i] = p_data + 1 - self.p_map
                            p_data += 1 + self.data[p_data]
                    else:
                        for i in range(4):
                            self.map_idx[0][i] = (p_data + 2 - self.p_map) // 2
                            p_data += 2 + 2 * self.read_uint16(p_data)
                p_data += p_data & 0x01

                self.precomp.indextable = p_data
                p_data += self.size[0]

                self.precomp.sizetable = p_data
                p_data += self.size[1]

                p_data = (p_data + 0x3f) & ~0x3f
                self.precomp.data = p_data
                p_data += self.size[2]

                self.key = recalc_key(self.pieces)
                self.mirrored_key = recalc_key(self.pieces, mirror=True)
            else:
                s = 1 + int(self.pawns[1] > 0)
                for f in range(4):
                    self.setup_pieces_pawn_dtz(p_data, f, f)
                    p_data += self.num + s
                p_data += p_data & 0x01

                self.flags = []
                for f in range(files):
                    self.files[f].precomp = self.setup_pairs(p_data, self.tb_size[f], 3 * f, False)
                    p_data = self._next
                    self.flags.append(self._flags)

                self.map_idx = []
                self.p_map = p_data
                for f in range(files):
                    self.map_idx.append([])
                    if self.flags[f] & 2:
                        if not self.flags[f] & 16:
                            for _ in range(4):
                                self.map_idx[-1].append(p_data + 1 - self.p_map)
                                p_data += 1 + self.data[p_data]
                        else:
                            p_data += p_data & 0x01
                            for _ in range(4):
                                self.map_idx[-1].append((p_data + 2 - self.p_map) // 2)
                                p_data += 2 + 2 * self.read_uint16(p_data)
                p_data += p_data & 0x01

                for f in range(files):
                    self.files[f].precomp.indextable = p_data
                    p_data += self.size[3 * f]

                for f in range(files):
                    self.files[f].precomp.sizetable = p_data
                    p_data += self.size[3 * f + 1]

                for f in range(files):
                    p_data = (p_data + 0x3f) & ~0x3f
                    self.files[f].precomp.data = p_data
                    p_data += self.size[3 * f + 2]

            self.initialized = True

    def probe_dtz_table(self, board: chess.Board, wdl: int) -> Tuple[int, int]:
        try:
            with self.read_condition:
                self.read_count += 1
            return self._probe_dtz_table(board, wdl)
        finally:
            with self.read_condition:
                self.read_count -= 1
                self.read_condition.notify()

    def _probe_dtz_table(self, board: chess.Board, wdl: int) -> Tuple[int, int]:
        self.init_table_dtz()
        assert self.data

        key = calc_key(board)

        if not self.symmetric:
            if key != self.key:
                cmirror = 8
                mirror = 0x38
                bside = int(board.turn == chess.WHITE)
            else:
                cmirror = mirror = 0
                bside = int(board.turn != chess.WHITE)
        else:
            cmirror = 0 if board.turn == chess.WHITE else 8
            mirror = 0 if board.turn == chess.WHITE else 0x38
            bside = 0

        if not self.has_pawns:
            assert isinstance(self.flags, int)

            if (self.flags & 1) != bside and not self.symmetric:
                return 0, -1

            pc = self.pieces
            p = [0 for _ in range(TBPIECES)]
            i = 0
            while i < self.num:
                piece_type = pc[i] & 0x07
                color = (pc[i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

                for square in chess.scan_forward(bb):
                    p[i] = square
                    i += 1

            idx = self.encode_piece(self.norm, p, self.factor)
            res = self.decompress_pairs(self.precomp, idx)

            if self.flags & 2:
                if not self.flags & 16:
                    res = self.data[self.p_map + self.map_idx[0][WDL_TO_MAP[wdl + 2]] + res]
                else:
                    res = self.read_uint16(self.p_map + 2 * (self.map_idx[0][WDL_TO_MAP[wdl + 2]] + res))

            if (not (self.flags & PA_FLAGS[wdl + 2])) or (wdl & 1):
                res *= 2
        else:
            assert isinstance(self.flags, list)

            k = self.files[0].pieces[0] ^ cmirror
            piece_type = k & 0x07
            color = k >> 3
            bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

            i = 0
            p = [0 for _ in range(TBPIECES)]
            for square in chess.scan_forward(bb):
                p[i] = square ^ mirror
                i += 1
            f = self.pawn_file(p)
            if self.flags[f] & 1 != bside:
                return 0, -1

            pc = self.files[f].pieces
            while i < self.num:
                piece_type = pc[i] & 0x07
                color = (pc[i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

                for square in chess.scan_forward(bb):
                    p[i] = square ^ mirror
                    i += 1

            idx = self.encode_pawn(self.files[f].norm, p, self.files[f].factor)
            res = self.decompress_pairs(self.files[f].precomp, idx)

            if self.flags[f] & 2:
                if not self.flags[f] & 16:
                    res = self.data[self.p_map + self.map_idx[f][WDL_TO_MAP[wdl + 2]] + res]
                else:
                    res = self.read_uint16(self.p_map + 2 * (self.map_idx[f][WDL_TO_MAP[wdl + 2]] + res))

            if (not (self.flags[f] & PA_FLAGS[wdl + 2])) or (wdl & 1):
                res *= 2

        return res, 1

    def setup_pieces_piece_dtz(self, p_data: int, p_tb_size: int) -> None:
        assert self.data

        self.pieces = [self.data[p_data + i + 1] & 0x0f for i in range(self.num)]
        order = self.data[p_data] & 0x0f
        self.set_norm_piece(self.norm, self.pieces)
        self.tb_size[p_tb_size] = self.calc_factors_piece(self.factor, order, self.norm)

    def setup_pieces_pawn_dtz(self, p_data: int, p_tb_size: int, f: int) -> None:
        assert self.data

        j = 1 + int(self.pawns[1] > 0)
        order = self.data[p_data] & 0x0f
        order2 = self.data[p_data + 1] & 0x0f if self.pawns[1] else 0x0f
        self.files[f].pieces = [self.data[p_data + i + j] & 0x0f for i in range(self.num)]

        self.files[f].norm = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm, self.files[f].pieces)

        self.files[f].factor = [0 for _ in range(TBPIECES)]
        self.tb_size[p_tb_size] = self.calc_factors_pawn(self.files[f].factor, order, order2, self.files[f].norm, f)


class Tablebase:
    """
    Manages a collection of tablebase files for probing.

    If *max_fds* is not ``None``, will at most use *max_fds* open file
    descriptors at any given time. The least recently used tables are closed,
    if necessary.
    """
    def __init__(self, *, max_fds: Optional[int] = 128, VariantBoard: Type[chess.Board] = chess.Board) -> None:
        self.variant = VariantBoard

        self.max_fds = max_fds
        self.lru: Deque[Table] = collections.deque()
        self.lru_lock = threading.Lock()

        self.wdl: Dict[str, Table] = {}
        self.dtz: Dict[str, Table] = {}

    def _bump_lru(self, table: Table) -> None:
        if self.max_fds is None:
            return

        with self.lru_lock:
            try:
                self.lru.remove(table)
                self.lru.appendleft(table)
            except ValueError:
                self.lru.appendleft(table)

                if len(self.lru) > self.max_fds:
                    self.lru.pop().close()

    def _open_table(self, hashtable: Dict[str, Table], Table: Type[Table], path: str) -> int:
        table = Table(path, variant=self.variant)

        if table.key in hashtable:
            hashtable[table.key].close()

        hashtable[table.key] = table
        hashtable[table.mirrored_key] = table
        return 1

    def add_directory(self, directory: str, *, load_wdl: bool = True, load_dtz: bool = True) -> int:
        """
        Adds tables from a directory.

        By default, all available tables with the correct file names
        (e.g., WDL files like ``KQvKN.rtbw`` and DTZ files like ``KRBvK.rtbz``)
        are added.

        The relevant files are lazily opened when the tablebase is actually
        probed.

        Returns the number of table files that were found.
        """
        num = 0
        directory = os.path.abspath(directory)

        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            tablename, ext = os.path.splitext(filename)

            if is_tablename(tablename, one_king=self.variant.one_king) and os.path.isfile(path):
                if load_wdl:
                    if ext == self.variant.tbw_suffix:
                        num += self._open_table(self.wdl, WdlTable, path)
                    elif "P" not in tablename and ext == self.variant.pawnless_tbw_suffix:
                        num += self._open_table(self.wdl, WdlTable, path)

                if load_dtz:
                    if ext == self.variant.tbz_suffix:
                        num += self._open_table(self.dtz, DtzTable, path)
                    elif "P" not in tablename and ext == self.variant.pawnless_tbz_suffix:
                        num += self._open_table(self.dtz, DtzTable, path)

        return num

    def probe_wdl_table(self, board: chess.Board) -> int:
        # Test for variant end.
        if board.is_variant_win():
            return 2
        elif board.is_variant_draw():
            return 0
        elif board.is_variant_loss():
            return -2

        # Test for KvK.
        if self.variant.one_king and board.kings == board.occupied:
            return 0

        key = calc_key(board)
        try:
            table = typing.cast(WdlTable, self.wdl[key])
        except KeyError:
            raise MissingTableError(f"did not find wdl table {key}")

        self._bump_lru(table)

        return table.probe_wdl_table(board)

    def probe_ab(self, board: chess.Board, alpha: int, beta: int, threats: bool = False) -> Tuple[int, int]:
        if self.variant.captures_compulsory:
            if board.is_variant_win():
                return 2, 2
            elif board.is_variant_loss():
                return -2, 2
            elif board.is_variant_draw():
                return 0, 2

            return self.sprobe_ab(board, alpha, beta, threats)

        # Generate non-ep captures.
        for move in board.generate_legal_moves(to_mask=board.occupied_co[not board.turn]):
            board.push(move)
            try:
                v_plus, _ = self.probe_ab(board, -beta, -alpha)
                v = -v_plus
            finally:
                board.pop()

            if v > alpha:
                if v >= beta:
                    return v, 2
                alpha = v

        v = self.probe_wdl_table(board)

        if alpha >= v:
            return alpha, 1 + int(alpha > 0)
        else:
            return v, 1

    def sprobe_ab(self, board: chess.Board, alpha: int, beta: int, threats: bool = False) -> Tuple[int, int]:
        if chess.popcount(board.occupied_co[not board.turn]) > 1:
            v, captures_found = self.sprobe_capts(board, alpha, beta)
            if captures_found:
                return v, 2
        else:
            if any(board.generate_legal_captures()):
                return -2, 2

        threats_found = False

        if threats or chess.popcount(board.occupied) >= 6:
            for threat in board.generate_legal_moves(~board.pawns):
                board.push(threat)
                try:
                    v_plus, captures_found = self.sprobe_capts(board, -beta, -alpha)
                    v = -v_plus
                finally:
                    board.pop()

                if captures_found and v > alpha:
                    threats_found = True
                    alpha = v
                    if alpha >= beta:
                        return v, 3

        v = self.probe_wdl_table(board)
        if v > alpha:
            return v, 1
        else:
            return alpha, 3 if threats_found else 1

    def sprobe_capts(self, board: chess.Board, alpha: int, beta: int) -> Tuple[int, int]:
        captures_found = False

        for move in board.generate_legal_captures():
            captures_found = True

            board.push(move)
            try:
                v_plus, _ = self.sprobe_ab(board, -beta, -alpha)
                v = -v_plus
            finally:
                board.pop()

            alpha = max(v, alpha)

            if alpha >= beta:
                break

        return alpha, captures_found

    def probe_wdl(self, board: chess.Board) -> int:
        """
        Probes WDL tables for win/draw/loss information under the 50-move rule,
        assuming the position has been reached directly after a capture or
        pawn move.

        Probing is thread-safe when done with different *board* objects and
        if *board* objects are not modified during probing.

        Returns ``2`` if the side to move is winning, ``0`` if the position is
        a draw and ``-2`` if the side to move is losing.

        Returns ``1`` in case of a cursed win and ``-1`` in case of a blessed
        loss. Mate can be forced but the position can be drawn due to the
        fifty-move rule.

        >>> import chess
        >>> import chess.syzygy
        >>>
        >>> with chess.syzygy.open_tablebase("data/syzygy/regular") as tablebase:
        ...     board = chess.Board("8/2K5/4B3/3N4/8/8/4k3/8 b - - 0 1")
        ...     print(tablebase.probe_wdl(board))
        ...
        -2

        :raises: :exc:`KeyError` (or specifically
            :exc:`chess.syzygy.MissingTableError`) if the position could not
            be found in the tablebase. Use
            :func:`~chess.syzygy.Tablebase.get_wdl()` if you prefer to get
            ``None`` instead of an exception.

            Note that probing corrupted table files is undefined behavior.
        """
        # Positions with castling rights are not in the tablebase.
        if board.castling_rights:
            raise KeyError(f"syzygy tables do not contain positions with castling rights: {board.fen()}")

        # Validate piece count.
        if chess.popcount(board.occupied) > TBPIECES:
            raise KeyError(f"syzygy tables support up to {TBPIECES} pieces, not {chess.popcount(board.occupied)}: {board.fen()}")

        # Probe.
        v, _ = self.probe_ab(board, -2, 2)

        # If en passant is not possible, we are done.
        if not board.ep_square or self.variant.captures_compulsory:
            return v

        # Now handle en passant.
        v1 = -3

        # Look at all legal en passant captures.
        for move in board.generate_legal_ep():
            board.push(move)
            try:
                v0_plus, _ = self.probe_ab(board, -2, 2)
                v0 = -v0_plus
            finally:
                board.pop()

            if v0 > v1:
                v1 = v0

        if v1 > -3:
            if v1 >= v:
                v = v1
            elif v == 0:
                # If there is not at least one legal non-en-passant move we are
                # forced to play the losing en passant cature.
                if all(board.is_en_passant(move) for move in board.generate_legal_moves()):
                    v = v1

        return v

    def get_wdl(self, board: chess.Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_wdl(board)
        except KeyError:
            return default

    def probe_dtz_table(self, board: chess.Board, wdl: int) -> Tuple[int, int]:
        key = calc_key(board)
        try:
            table = typing.cast(DtzTable, self.dtz[key])
        except KeyError:
            raise MissingTableError(f"did not find dtz table {key}")

        self._bump_lru(table)

        return table.probe_dtz_table(board, wdl)

    def probe_dtz_no_ep(self, board: chess.Board) -> int:
        wdl, success = self.probe_ab(board, -2, 2, threats=True)

        if wdl == 0:
            return 0

        if success == 2 or not board.occupied_co[board.turn] & ~board.pawns:
            return dtz_before_zeroing(wdl)

        if wdl > 0:
            # The position is a win or a cursed win by a threat move.
            if success == 3:
                return 2 if wdl == 2 else 102

            # Generate all legal non-capturing pawn moves.
            for move in board.generate_legal_moves(board.pawns, ~board.occupied):
                if board.is_capture(move):
                    # En passant.
                    continue

                board.push(move)
                try:
                    v = -self.probe_wdl(board)
                finally:
                    board.pop()

                if v == wdl:
                    return 1 if v == 2 else 101

        dtz, success = self.probe_dtz_table(board, wdl)
        if success >= 0:
            return dtz_before_zeroing(wdl) + (dtz if wdl > 0 else -dtz)

        if wdl > 0:
            best = 0xffff

            for move in board.generate_legal_moves(~board.pawns, ~board.occupied):
                board.push(move)
                try:
                    v = -self.probe_dtz(board)

                    if v == 1 and board.is_checkmate():
                        best = 1
                    elif v > 0 and v + 1 < best:
                        best = v + 1
                finally:
                    board.pop()

            return best
        else:
            best = -1

            for move in board.generate_legal_moves():
                board.push(move)

                try:
                    if board.halfmove_clock == 0:
                        if wdl == -2:
                            v = -1
                        else:
                            v, success = self.probe_ab(board, 1, 2, threats=True)
                            v = 0 if v == 2 else -101
                    else:
                        v = -self.probe_dtz(board) - 1
                finally:
                    board.pop()

                if v < best:
                    best = v

            return best

    def probe_dtz(self, board: chess.Board) -> int:
        """
        Probes DTZ tables for
        `DTZ50'' information with rounding <https://syzygy-tables.info/metrics#dtz>`_.

        Minmaxing the DTZ50'' values guarantees winning a won position
        (and drawing a drawn position), because it makes progress keeping the
        win in hand.
        However, the lines are not always the most straightforward ways to win.
        Engines like Stockfish calculate themselves, checking with DTZ, but
        only play according to DTZ if they can not manage on their own.

        Returns a positive value if the side to move is winning, ``0`` if the
        position is a draw, and a negative value if the side to move is losing.
        More precisely:

        +-----+------------------+--------------------------------------------+
        | WDL | DTZ              |                                            |
        +=====+==================+============================================+
        |  -2 | -100 <= n <= -1  | Unconditional loss (assuming 50-move       |
        |     |                  | counter is zero), where a zeroing move can |
        |     |                  | be forced in -n plies.                     |
        +-----+------------------+--------------------------------------------+
        |  -1 |         n < -100 | Loss, but draw under the 50-move rule.     |
        |     |                  | A zeroing move can be forced in -n plies   |
        |     |                  | or -n - 100 plies (if a later phase is     |
        |     |                  | responsible for the blessed loss).         |
        +-----+------------------+--------------------------------------------+
        |   0 |         0        | Draw.                                      |
        +-----+------------------+--------------------------------------------+
        |   1 |   100 < n        | Win, but draw under the 50-move rule.      |
        |     |                  | A zeroing move can be forced in n plies or |
        |     |                  | n - 100 plies (if a later phase is         |
        |     |                  | responsible for the cursed win).           |
        +-----+------------------+--------------------------------------------+
        |   2 |    1 <= n <= 100 | Unconditional win (assuming 50-move        |
        |     |                  | counter is zero), where a zeroing move can |
        |     |                  | be forced in n plies.                      |
        +-----+------------------+--------------------------------------------+

        The return value can be off by one: a return value -n can mean a
        losing zeroing move in in n + 1 plies and a return value +n can mean a
        winning zeroing move in n + 1 plies.
        This implies some primary tablebase lines may waste up to 1 ply.
        Rounding is never used for endgame phases where it would change the
        game theoretical outcome.

        This means users need to be careful in positions that are nearly drawn
        under the 50-move rule! Carelessly wasting 1 more ply by not following
        the tablebase recommendation, for a total of 2 wasted plies, may
        change the outcome of the game.

        >>> import chess
        >>> import chess.syzygy
        >>>
        >>> with chess.syzygy.open_tablebase("data/syzygy/regular") as tablebase:
        ...     board = chess.Board("8/2K5/4B3/3N4/8/8/4k3/8 b - - 0 1")
        ...     print(tablebase.probe_dtz(board))
        ...
        -53

        Probing is thread-safe when done with different *board* objects and
        if *board* objects are not modified during probing.

        Both DTZ and WDL tables are required in order to probe for DTZ.

        :raises: :exc:`KeyError` (or specifically
            :exc:`chess.syzygy.MissingTableError`) if the position could not
            be found in the tablebase. Use
            :func:`~chess.syzygy.Tablebase.get_dtz()` if you prefer to get
            ``None`` instead of an exception.

            Note that probing corrupted table files is undefined behavior.
        """
        v = self.probe_dtz_no_ep(board)

        if not board.ep_square or self.variant.captures_compulsory:
            return v

        v1 = -3

        # Generate all en passant moves.
        for move in board.generate_legal_ep():
            board.push(move)
            try:
                v0_plus, _ = self.probe_ab(board, -2, 2)
                v0 = -v0_plus
            finally:
                board.pop()

            if v0 > v1:
                v1 = v0

        if v1 > -3:
            v1 = WDL_TO_DTZ[v1 + 2]
            if v < -100:
                if v1 >= 0:
                    v = v1
            elif v < 0:
                if v1 >= 0 or v1 < -100:
                    v = v1
            elif v > 100:
                if v1 > 0:
                    v = v1
            elif v > 0:
                if v1 == 1:
                    v = v1
            elif v1 >= 0:
                v = v1
            else:
                if all(board.is_en_passant(move) for move in board.generate_legal_moves()):
                    v = v1

        return v

    def get_dtz(self, board: chess.Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_dtz(board)
        except KeyError:
            return default

    def close(self) -> None:
        """Closes all loaded tables."""
        while self.wdl:
            _, wdl = self.wdl.popitem()
            wdl.close()

        while self.dtz:
            _, dtz = self.dtz.popitem()
            dtz.close()

        self.lru.clear()

    def __enter__(self) -> Tablebase:
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.close()


def open_tablebase(directory: str, *, load_wdl: bool = True, load_dtz: bool = True, max_fds: Optional[int] = 128, VariantBoard: Type[chess.Board] = chess.Board) -> Tablebase:
    """
    Opens a collection of tables for probing. See
    :class:`~chess.syzygy.Tablebase`.

    .. note::

        Generally probing requires tablebase files for the specific
        material composition, **as well as** material compositions transitively
        reachable by captures and promotions.
        This is important because 6-piece and 5-piece (let alone 7-piece) files
        are often distributed separately, but are both required for 6-piece
        positions. Use :func:`~chess.syzygy.Tablebase.add_directory()` to load
        tables from additional directories.
    """
    tables = Tablebase(max_fds=max_fds, VariantBoard=VariantBoard)
    tables.add_directory(directory, load_wdl=load_wdl, load_dtz=load_dtz)
    return tables
