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

import chess
import mmap
import os
import struct
import sys
import threading


UINT64_BE = struct.Struct(">Q")
UINT32 = struct.Struct("<I")
UINT32_BE = struct.Struct(">I")
USHORT = struct.Struct("<H")

WDL_MAGIC = [0x71, 0xE8, 0x23, 0x5D]
DTZ_MAGIC = [0xD7, 0x66, 0x0C, 0xA5]

OFFDIAG = [
    0, -1, -1, -1, -1, -1, -1, -1,
    1,  0, -1, -1, -1, -1, -1, -1,
    1,  1,  0, -1, -1, -1, -1, -1,
    1,  1,  1,  0, -1, -1, -1, -1,
    1,  1,  1,  1,  0, -1, -1, -1,
    1,  1,  1,  1,  1,  0, -1, -1,
    1,  1,  1,  1,  1,  1,  0, -1,
    1,  1,  1,  1,  1,  1,  1,  0,
]

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

FLIPDIAG = [
     0,  8, 16, 24, 32, 40, 48, 56,
     1,  9, 17, 25, 33, 41, 49, 57,
     2, 10, 18, 26, 34, 42, 50, 58,
     3, 11, 19, 27, 35, 43, 51, 59,
     4, 12, 20, 28, 36, 44, 52, 60,
     5, 13, 21, 29, 37, 45, 53, 61,
     6, 14, 22, 30, 38, 46, 54, 62,
     7, 15, 23, 31, 39, 47, 55, 63,
]

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
     0, 0,   0,  0,  0,  0,  0,  0,
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

FILE_TO_FILE = [ 0, 1, 2, 3, 3, 2, 1, 0 ]

KK_IDX = [ [
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
] ]

BINOMIAL = []
for i in range(5):
    BINOMIAL.append([])
    for j in range(64):
        f = j
        l = 1
        for k in range(1, i + 1):
            f *= j - k
            l *= k + 1
        BINOMIAL[i].append(f // l)

PAWNIDX = [ [ 0 for _ in range(24) ] for _ in range(5) ]

PFACTOR = [ [ 0 for _ in range(4) ] for _ in range(5) ]

for i in range(5):
    j = 0

    s = 0
    while j < 6:
        PAWNIDX[i][j] = s
        s += 1 if i == 0 else BINOMIAL[i - 1][PTWIST[INVFLAP[j]]]
        j += 1
    PFACTOR[i][0] = s

    s = 0
    while j < 12:
        PAWNIDX[i][j] = s
        s += 1 if i == 0 else BINOMIAL[i - 1][PTWIST[INVFLAP[j]]]
        j += 1
    PFACTOR[i][1] = s

    s = 0
    while j < 18:
        PAWNIDX[i][j] = s
        s += 1 if i == 0 else BINOMIAL[i - 1][PTWIST[INVFLAP[j]]]
        j += 1
    PFACTOR[i][2] = s

    s = 0
    while j < 24:
        PAWNIDX[i][j] = s
        s += 1 if i == 0 else BINOMIAL[i - 1][PTWIST[INVFLAP[j]]]
        j += 1
    PFACTOR[i][3] = s

WDL_TO_MAP = [1, 3, 0, 2, 0]

PA_FLAGS = [8, 0, 0, 0, 4]

WDL_TO_DTZ = [-1, -101, 0, 101, 1]

PCHR = ["K", "Q", "R", "B", "N", "P"]


def filenames():
    for i in range(1, 6):
        yield "K%cvK" % (PCHR[i], )

    for i in range(1, 6):
        for j in range(i, 6):
            yield "K%cvK%c" % (PCHR[i], PCHR[j])

    for i in range(1, 6):
        for j in range(i, 6):
            yield "K%c%cvK" % (PCHR[i], PCHR[j])

    for i in range(1, 6):
        for j in range(i, 6):
            for k in range(1, 6):
                yield "K%c%cvK%c" % (PCHR[i], PCHR[j], PCHR[k])

    for i in range(1, 6):
        for j in range(i, 6):
            for k in range(j, 6):
                yield "K%c%c%cvK" % (PCHR[i], PCHR[j], PCHR[k])

    for i in range(1, 6):
        for j in range(i, 6):
            for k in range(i, 6):
                for l in range(j if i == k else k, 6):
                    yield "K%c%cvK%c%c" % (PCHR[i], PCHR[j], PCHR[k], PCHR[l])

    for i in range(1, 6):
        for j in range(i, 6):
            for k in range(j, 6):
                for l in range(1, 6):
                    yield "K%c%c%cvK%c" % (PCHR[i], PCHR[j], PCHR[k], PCHR[l])

    for i in range(1, 6):
        for j in range(i, 6):
            for k in range(j, 6):
                for l in range(k, 6):
                    yield "K%c%c%c%cvK" % (PCHR[i], PCHR[j], PCHR[k], PCHR[l])


def calc_key(board, mirror=False):
    key = 0

    for color in chess.COLORS:
        mirrored_color = color ^ mirror

        for i in range(chess.pop_count(board.pawns & board.occupied_co[color])):
            key ^= chess.POLYGLOT_RANDOM_ARRAY[mirrored_color * 6 * 16 + 5 * 16 + i]
        for i in range(chess.pop_count(board.knights & board.occupied_co[color])):
            key ^= chess.POLYGLOT_RANDOM_ARRAY[mirrored_color * 6 * 16 + 4 * 16 + i]
        for i in range(chess.pop_count(board.bishops & board.occupied_co[color])):
            key ^= chess.POLYGLOT_RANDOM_ARRAY[mirrored_color * 6 * 16 + 3 * 16 + i]
        for i in range(chess.pop_count(board.rooks & board.occupied_co[color])):
            key ^= chess.POLYGLOT_RANDOM_ARRAY[mirrored_color * 6 * 16 + 2 * 16 + i]
        for i in range(chess.pop_count(board.queens & board.occupied_co[color])):
            key ^= chess.POLYGLOT_RANDOM_ARRAY[mirrored_color * 6 * 16 + 1 * 16 + i]
        for i in range(chess.pop_count(board.kings & board.occupied_co[color])):
            key ^= chess.POLYGLOT_RANDOM_ARRAY[mirrored_color * 6 * 16 + 0 * 16 + i]

    return key


def calc_key_from_filename(filename, mirror=False):
    white, black = filename.split("v")

    color = chess.WHITE ^ mirror

    key = 0

    for piece_index, piece in enumerate(PCHR):
        for i in range(white.count(piece)):
            key ^= chess.POLYGLOT_RANDOM_ARRAY[color * 6 * 16 + piece_index * 16 + i]

    color = not color

    for piece_index, piece in enumerate(PCHR):
        for i in range(black.count(piece)):
            key ^= chess.POLYGLOT_RANDOM_ARRAY[color * 6 * 16 + piece_index * 16 + i]

    return key


def subfactor(k, n):
    f = n
    l = 1

    for i in range(1, k):
        f *= n - i
        l *= i + 1

    return f // l


class PairsData(object):
    def __init__(self):
        self.indextable = None
        self.sizetable = None
        self.data = None
        self.offset = None
        self.symlen = None
        self.sympat = None
        self.blocksize = None
        self.idxbits = None
        self.min_len = None
        self.base = None


class PawnFileData(object):
    def __init__(self):
        self.precomp = {}
        self.factor = {}
        self.pieces = {}
        self.norm = {}


class PawnFileDataDtz(object):
    def __init__(self):
        self.precomp = None
        self.factor = None
        self.pieces = None
        self.norm = None


class Table(object):

    def __init__(self, directory, filename, suffix):
        self.directory = directory
        self.filename = filename
        self.suffix = suffix

        self.fd = os.open(os.path.join(directory, filename) + suffix, os.O_RDONLY | os.O_BINARY if hasattr(os, "O_BINARY") else os.O_RDONLY)
        self.data = mmap.mmap(self.fd, 0, access=mmap.ACCESS_READ)

        if sys.version_info >= (3, ):
            self.read_ubyte = self.data.__getitem__
        else:
            def read_ubyte(data_ptr):
                return ord(self.data[data_ptr])

            self.read_ubyte = read_ubyte

        self.key = calc_key_from_filename(filename)
        self.mirrored_key = calc_key_from_filename(filename, True)
        self.symmetric = self.key == self.mirrored_key

        # Leave the v out of the filename to get the number of pieces.
        self.num = len(filename) - 1

        self.has_pawns = "P" in filename

        black_part, white_part = filename.split("v")
        if self.has_pawns:
            self.pawns = {}
            self.pawns[0] = white_part.count("P")
            self.pawns[1] = black_part.count("P")
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
            else:
                # Each player will always have a king, unless we're playing
                # suicide chess.
                # TODO: Could be implemented.
                assert False

    def setup_pairs(self, data_ptr, tb_size, size_idx, wdl):
        d = PairsData()

        self._flags = self.read_ubyte(data_ptr)
        if self.read_ubyte(data_ptr) & 0x80:
            d.idxbits = 0
            if wdl:
                d.min_len = self.read_ubyte(data_ptr + 1)
            else:
                d.min_len = 0
            self._next = data_ptr + 2
            self.size[size_idx + 0] = 0
            self.size[size_idx + 1] = 0
            self.size[size_idx + 2] = 0
            return d

        d.blocksize = self.read_ubyte(data_ptr + 1)
        d.idxbits = self.read_ubyte(data_ptr + 2)

        real_num_blocks = self.read_uint32(data_ptr + 4)
        num_blocks = real_num_blocks + self.read_ubyte(data_ptr + 3)
        max_len = self.read_ubyte(data_ptr + 8)
        min_len = self.read_ubyte(data_ptr + 9)
        h = max_len - min_len + 1
        num_syms = self.read_ushort(data_ptr + 10 + 2 * h)

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
            d.base[i] = (d.base[i + 1] + self.read_ushort(d.offset + i * 2) - self.read_ushort(d.offset + i * 2 + 2)) // 2
        for i in range(h):
            d.base[i] <<= 64 - (min_len + i)

        d.offset -= 2 * d.min_len

        return d

    def set_norm_piece(self, norm, pieces):
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

    def calc_factors_piece(self, factor, order, norm):
        PIVFAC = [31332, 28056, 462]

        n = 64 - norm[0]

        f = 1
        i = norm[0]
        k = 0
        while i < self.num or k == order:
            if k == order:
                factor[0] = f
                f *= PIVFAC[self.enc_type]
            else:
                factor[i] = f
                f *= subfactor(norm[i], n)
                n -= norm[i]
                i += norm[i]
            k += 1

        return f

    def calc_factors_pawn(self, factor, order, order2, norm, f):
        i = norm[0]
        if order2 < 0x0f:
            i += norm[i]
        n = 64 - i

        fac = 1
        k = 0
        while i < self.num or k == order or k == order2:
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

    def set_norm_pawn(self, norm, pieces):
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

    def calc_symlen(self, d, s, tmp):
        w = d.sympat + 3 * s
        s2 = (self.read_ubyte(w + 2) << 4) | (self.read_ubyte(w + 1) >> 4)
        if s2 == 0x0fff:
            d.symlen[s] = 0
        else:
            s1 = ((self.read_ubyte(w + 1) & 0xf) << 8) | self.read_ubyte(w)
            if not tmp[s1]:
                self.calc_symlen(d, s1, tmp)
            if not tmp[s2]:
                self.calc_symlen(d, s2, tmp)
            d.symlen[s] = d.symlen[s1] + d.symlen[s2] + 1
        tmp[s] = 1

    def pawn_file(self, pos):
        for i in range(1, self.pawns[0]):
            if FLAP[pos[0]] > FLAP[pos[i]]:
                pos[0], pos[i] = pos[i], pos[0]

        return FILE_TO_FILE[pos[0] & 0x07]

    def encode_piece(self, norm, pos, factor):
        n = self.num

        if pos[0] & 0x04:
            for i in range(n):
                pos[i] ^= 0x07

        if pos[0] & 0x20:
            for i in range(n):
                pos[i] ^= 0x38

        for i in range(n):
            if OFFDIAG[pos[i]]:
                break

        if i < (3 if self.enc_type == 0 else 2) and OFFDIAG[pos[i]] > 0:
            for i in range(n):
                pos[i] = FLIPDIAG[pos[i]]

        if self.enc_type == 0: # 111
            i = int(pos[1] > pos[0])
            j = int(pos[2] > pos[0]) + int(pos[2] > pos[1])

            if OFFDIAG[pos[0]]:
                idx = TRIANGLE[pos[0]] * 63 * 62 + (pos[1] - i) * 62 + (pos[2] - j)
            elif OFFDIAG[pos[1]]:
                idx = 6 * 63 * 62 + DIAG[pos[0]] * 28 * 62 + LOWER[pos[1]] * 62 + pos[2] - j
            elif OFFDIAG[pos[2]]:
                idx = 6 * 63 * 62 + 4 * 28 * 62 + (DIAG[pos[0]]) * 7 * 28 + (DIAG[pos[1]] - i) * 28 + LOWER[pos[2]]
            else:
                idx = 6 * 63 * 62 + 4 * 28 * 62 + 4 * 7 * 28 + (DIAG[pos[0]] * 7 * 6) + (DIAG[pos[1]] - i) * 6 + (DIAG[pos[2]] - j)
            i = 3
        elif self.enc_type == 1: # K3
            j = int(pos[2] > pos[0]) + int(pos[2] > pos[1])

            idx = KK_IDX[TRIANGLE[pos[0]]][pos[1]]
            if idx < 441:
                idx = idx + 441 * (pos[2] - j)
            else:
                idx = 441 * 62 + (idx - 441) + 21 * LOWER[pos[2]]
                if not OFFDIAG[pos[2]]:
                    idx -= j * 21
            i = 3
        else: # K2
            idx = KK_IDX[TRIANGLE[pos[0]]][pos[1]]
            i = 2

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
                s += BINOMIAL[m - i][p - j]

            idx += s * factor[i]
            i += t

        return idx

    def encode_pawn(self, norm, pos, factor):
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
            idx += BINOMIAL[t - i][PTWIST[pos[i]]]
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
                s += BINOMIAL[m - i][p - j - 8]
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
                s += BINOMIAL[m - i][p - j]

            idx += s * factor[i]
            i += t

        return idx

    def decompress_pairs(self, d, idx):
        if not d.idxbits:
            return d.min_len

        mainidx = idx >> d.idxbits
        litidx = (idx & (1 << d.idxbits) - 1) - (1 << (d.idxbits - 1))
        block = self.read_uint32(d.indextable + 6 * mainidx)

        idx_offset = self.read_ushort(d.indextable + 6 * mainidx + 4)
        litidx += idx_offset

        if litidx < 0:
            while litidx < 0:
                block -= 1
                litidx += self.read_ushort(d.sizetable + 2 * block) + 1
        else:
            while litidx > self.read_ushort(d.sizetable + 2 * block):
                litidx -= self.read_ushort(d.sizetable + 2 * block) + 1
                block += 1

        ptr = d.data + (block << d.blocksize)

        m = d.min_len
        base_idx = -m
        symlen_idx = 0

        code = self.read_uint64_be(ptr)

        ptr += 2 * 4
        bitcnt = 0 # Number of empty bits in code
        while True:
            l = m
            while code < d.base[base_idx + l]:
                l += 1
            sym = self.read_ushort(d.offset + l * 2)
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
            s1 = ((self.read_ubyte(w + 1) & 0xf) << 8) | self.read_ubyte(w)
            if litidx < d.symlen[symlen_idx + s1] + 1:
                sym = s1
            else:
                litidx -= d.symlen[symlen_idx + s1] + 1
                sym = (self.read_ubyte(w + 2) << 4) | (self.read_ubyte(w + 1) >> 4)

        return self.read_ubyte(sympat + 3 * sym)

    def read_uint64_be(self, data_ptr):
        return UINT64_BE.unpack_from(self.data, data_ptr)[0]

    def read_uint32(self, data_ptr):
        return UINT32.unpack_from(self.data, data_ptr)[0]

    def read_uint32_be(self, data_ptr):
        return UINT32_BE.unpack_from(self.data, data_ptr)[0]

    def read_ushort(self, data_ptr):
        return USHORT.unpack_from(self.data, data_ptr)[0]

    def close(self):
        self.data.close()

        try:
            os.close(self.fd)
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["fd"]
        del state["data"]
        del state["read_ubyte"]
        del state["lock"]
        return state

    def __setstate__(self, state):
        self.__init__(self.directory, self.filename, self.suffix)
        self.__dict__.update(state)


class WdlTable(Table):

    def __init__(self, directory, filename, suffix=".rtbw"):
        super(WdlTable, self).__init__(directory, filename, suffix)
        self.initialized = False
        self.lock = threading.Lock()

    def init_table_wdl(self):
        if self.initialized:
            return

        with self.lock:
            if self.initialized:
                return

            assert WDL_MAGIC[0] == self.read_ubyte(0)
            assert WDL_MAGIC[1] == self.read_ubyte(1)
            assert WDL_MAGIC[2] == self.read_ubyte(2)
            assert WDL_MAGIC[3] == self.read_ubyte(3)

            self.tb_size = [0 for _ in range(8)]
            self.size = [0 for _ in range(8 * 3)]

            # Used if there are only pieces.
            self.precomp = {}
            self.pieces = {}

            self.factor = {}
            self.factor[0] = [0, 0, 0, 0, 0, 0] # White
            self.factor[1] = [0, 0, 0, 0, 0, 0] # Black

            self.norm = {}
            self.norm[0] = [0 for _ in range(self.num)] # White
            self.norm[1] = [0 for _ in range(self.num)] # Black

            # Used if there are pawns.
            self.files = [PawnFileData() for _ in range(4)]

            self._next = None
            self._flags = None
            self.flags = None

            split = self.read_ubyte(4) & 0x01
            files = 4 if self.read_ubyte(4) & 0x02 else 1

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
                else:
                    self.precomp[1] = None

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
                    else:
                        self.files[f].precomp[1] = None

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

    def setup_pieces_pawn(self, p_data, p_tb_size, f):
        j = 1 + int(self.pawns[1] > 0)
        order = self.read_ubyte(p_data) & 0x0f
        order2 = self.read_ubyte(p_data + 1) & 0x0f if self.pawns[1] else 0x0f
        self.files[f].pieces[0] = [self.read_ubyte(p_data + i + j) & 0x0f for i in range(self.num)]
        self.files[f].norm[0] = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm[0], self.files[f].pieces[0])
        self.files[f].factor[0] = [0, 0, 0, 0, 0, 0]
        self.tb_size[p_tb_size] = self.calc_factors_pawn(self.files[f].factor[0], order, order2, self.files[f].norm[0], f)

        order = self.read_ubyte(p_data) >> 4
        order2 = self.read_ubyte(p_data + 1) >> 4 if self.pawns[1] else 0x0f
        self.files[f].pieces[1] = [self.read_ubyte(p_data + i + j) >> 4 for i in range(self.num)]
        self.files[f].norm[1] = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm[1], self.files[f].pieces[1])
        self.files[f].factor[1] = [0, 0, 0, 0, 0, 0]
        self.tb_size[p_tb_size + 1] = self.calc_factors_pawn(self.files[f].factor[1], order, order2, self.files[f].norm[1], f)

    def setup_pieces_piece(self, p_data):
        self.pieces[0] = [self.read_ubyte(p_data + i + 1) & 0x0f for i in range(self.num)]
        order = self.read_ubyte(p_data) & 0x0f
        self.set_norm_piece(self.norm[0], self.pieces[0])
        self.tb_size[0] = self.calc_factors_piece(self.factor[0], order, self.norm[0])

        self.pieces[1] = [self.read_ubyte(p_data + i + 1) >> 4 for i in range(self.num)]
        order = self.read_ubyte(p_data) >> 4
        self.set_norm_piece(self.norm[1], self.pieces[1])
        self.tb_size[1] = self.calc_factors_piece(self.factor[1], order, self.norm[1])

    def probe_wdl_table(self, board):
        self.init_table_wdl()

        key = calc_key(board)

        if self.symmetric:
            cmirror = 0 if board.turn == chess.WHITE else 8
            mirror = 0 if board.turn == chess.WHITE else 0x38
            bside = 0
        else:
            if key != self.key:
                cmirror = 8
                mirror = 0x38
                bside = int(board.turn == chess.WHITE)
            else:
                cmirror = mirror = 0
                bside = int(board.turn != chess.WHITE)

        if not self.has_pawns:
            p = [0, 0, 0, 0, 0, 0]
            i = 0
            while i < self.num:
                piece_type = self.pieces[bside][i] & 0x07
                color = (self.pieces[bside][i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

                square = chess.bit_scan(bb)
                while square != -1 and square is not None:
                    p[i] = square
                    i += 1
                    square = chess.bit_scan(bb, square + 1)

            idx = self.encode_piece(self.norm[bside], p, self.factor[bside])
            res = self.decompress_pairs(self.precomp[bside], idx)
        else:
            p = [0, 0, 0, 0, 0, 0]
            i = 0
            k = self.files[0].pieces[0][0] ^ cmirror
            color = k >> 3
            piece_type = k & 0x07
            bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

            square = chess.bit_scan(bb)
            while square != -1 and square is not None:
                p[i] = square ^ mirror
                i += 1
                square = chess.bit_scan(bb, square + 1)

            f = self.pawn_file(p)
            pc = self.files[f].pieces[bside]
            while i < self.num:
                color = (pc[i] ^ cmirror) >> 3
                piece_type = pc[i] & 0x07
                bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

                square = chess.bit_scan(bb)
                while square != -1 and square is not None:
                    p[i] = square ^ mirror
                    i += 1
                    square = chess.bit_scan(bb, square + 1)

            idx = self.encode_pawn(self.files[f].norm[bside], p, self.files[f].factor[bside])
            res = self.decompress_pairs(self.files[f].precomp[bside], idx)

        return res - 2


class DtzTable(Table):

    def __init__(self, directory, filename, suffix=".rtbz"):
        super(DtzTable, self).__init__(directory, filename, suffix)
        self.initialized = False
        self.lock = threading.Lock()

    def init_table_dtz(self):
        if self.initialized:
            return

        with self.lock:
            if self.initialized:
                return

            assert DTZ_MAGIC[0] == self.read_ubyte(0)
            assert DTZ_MAGIC[1] == self.read_ubyte(1)
            assert DTZ_MAGIC[2] == self.read_ubyte(2)
            assert DTZ_MAGIC[3] == self.read_ubyte(3)

            self.factor = [0, 0, 0, 0, 0, 0]
            self.norm = [0 for _ in range(self.num)]
            self.tb_size = [0, 0, 0, 0]
            self.size = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            self.files = [PawnFileDataDtz() for f in range(4)]

            files = 4 if self.read_ubyte(4) & 0x02 else 1

            p_data = 5

            if not self.has_pawns:
                self.map_idx = [0, 0, 0, 0]

                self.setup_pieces_piece_dtz(p_data, 0)
                p_data += self.num + 1
                p_data += p_data & 0x01

                self.precomp = self.setup_pairs(p_data, self.tb_size[0], 0, False)
                self.flags = self._flags
                p_data = self._next
                self.p_map = p_data
                if self.flags & 2:
                    for i in range(4):
                        self.map_idx[i] = p_data + 1 - self.p_map
                        p_data += 1 + self.read_ubyte(p_data)
                    p_data += p_data & 0x01

                self.precomp.indextable = p_data
                p_data += self.size[0]

                self.precomp.sizetable = p_data
                p_data += self.size[1]

                p_data = (p_data + 0x3f) & ~0x3f
                self.precomp.data = p_data
                p_data += self.size[2]
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
                        for i in range(4):
                            self.map_idx[-1].append(p_data + 1 - self.p_map)
                            p_data += 1 + self.read_ubyte(p_data)
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

    def probe_dtz_table(self, board, wdl):
        self.init_table_dtz()

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
            if (self.flags & 1) != bside and not self.symmetric:
                return 0, -1

            pc = self.pieces
            p = [0, 0, 0, 0, 0, 0]
            i = 0
            while i < self.num:
                piece_type = pc[i] & 0x07
                color = (pc[i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

                square = chess.bit_scan(bb)
                while square != -1 and square is not None:
                    p[i] = square
                    i += 1
                    square = chess.bit_scan(bb, square + 1)

            idx = self.encode_piece(self.norm, p, self.factor)
            res = self.decompress_pairs(self.precomp, idx)

            if self.flags & 2:
                res = self.read_ubyte(self.p_map + self.map_idx[WDL_TO_MAP[wdl + 2]] + res)

            if (not (self.flags & PA_FLAGS[wdl + 2])) or (wdl & 1):
                res *= 2
        else:
            k = self.files[0].pieces[0] ^ cmirror
            piece_type = k & 0x07
            color = k >> 3
            bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

            i = 0
            p = [0, 0, 0, 0, 0, 0]
            square = chess.bit_scan(bb)
            while square != -1 and square is not None:
                p[i] = square ^ mirror
                i += 1
                square = chess.bit_scan(bb, square + 1)
            f = self.pawn_file(p)
            if self.flags[f] & 1 != bside:
                return 0, -1

            pc = self.files[f].pieces
            while i < self.num:
                piece_type = pc[i] & 0x07
                color = (pc[i] ^ cmirror) >> 3
                bb = board.pieces_mask(piece_type, chess.WHITE if color == 0 else chess.BLACK)

                square = chess.bit_scan(bb)
                while square != -1 and square is not None:
                    p[i] = square ^ mirror
                    i += 1
                    square = chess.bit_scan(bb, square + 1)

            idx = self.encode_pawn(self.files[f].norm, p, self.files[f].factor)
            res = self.decompress_pairs(self.files[f].precomp, idx)

            if self.flags[f] & 2:
                res = self.read_ubyte(self.p_map + self.map_idx[f][WDL_TO_MAP[wdl + 2]] + res)

            if (not (self.flags[f] & PA_FLAGS[wdl + 2])) or (wdl & 1):
                res *= 2

        return res, 1

    def setup_pieces_piece_dtz(self, p_data, p_tb_size):
        self.pieces = [self.read_ubyte(p_data + i + 1) & 0x0f for i in range(self.num)]
        order = self.read_ubyte(p_data) & 0x0f
        self.set_norm_piece(self.norm, self.pieces)
        self.tb_size[p_tb_size] = self.calc_factors_piece(self.factor, order, self.norm)

    def setup_pieces_pawn_dtz(self, p_data, p_tb_size, f):
        j = 1 + int(self.pawns[1] > 0)
        order = self.read_ubyte(p_data) & 0x0f
        order2 = self.read_ubyte(p_data + 1) & 0x0f if self.pawns[1] else 0x0f
        self.files[f].pieces = [self.read_ubyte(p_data + i + j) & 0x0f for i in range(self.num)]

        self.files[f].norm = [0 for _ in range(self.num)]
        self.set_norm_pawn(self.files[f].norm, self.files[f].pieces)

        self.files[f].factor = [0, 0, 0, 0, 0, 0]
        self.tb_size[p_tb_size] = self.calc_factors_pawn(self.files[f].factor, order, order2, self.files[f].norm, f)


class Tablebases(object):
    """
    Manages a collection of tablebase files for probing.

    Syzygy tables come in files like *KQvKN.rtbw* or *KRBvK.rtbz*, one WDL
    (*.rtbw*) and DTZ (*.rtbz*) file for each material composition.

    Directly loads tables from *directory*. See
    :func:`~chess.syzygy.Tablebases.open_directory`.
    """
    def __init__(self, directory=None, load_wdl=True, load_dtz=True):
        self.wdl = {}
        self.dtz = {}

        if directory:
            self.open_directory(directory, load_wdl, load_dtz)

    def open_directory(self, directory, load_wdl=True, load_dtz=True):
        """
        Loads tables from a directory.

        By default all available tables with the correct file names
        (e.g. *KQvKN.rtbw* or *KRBvK.rtbz*) are loaded.

        Returns the number of successfully openened and loaded tablebase files.
        """
        num = 0

        for filename in filenames():
            if load_wdl and os.path.isfile(os.path.join(directory, filename) + ".rtbw"):
                wdl_table = WdlTable(directory, filename)
                if wdl_table.key in self.wdl:
                    self.wdl[wdl_table.key].close()

                self.wdl[wdl_table.key] = wdl_table
                self.wdl[wdl_table.mirrored_key] = wdl_table

                num += 1

            if load_dtz and os.path.isfile(os.path.join(directory, filename) + ".rtbz"):
                dtz_table = DtzTable(directory, filename)
                if dtz_table.key in self.dtz:
                    self.dtz[dtz_table.key].close()

                self.dtz[dtz_table.key] = dtz_table
                self.dtz[dtz_table.mirrored_key] = dtz_table

                num += 1

        return num

    def probe_wdl_table(self, board):
        # Test for KvK.
        if board.kings == board.occupied:
            return 0

        key = calc_key(board)
        if key not in self.wdl:
            return None

        return self.wdl[key].probe_wdl_table(board)

    def probe_ab(self, board, alpha, beta):
        for move in board.generate_legal_moves():
            # Only look at non-ep captures.
            if not board.piece_type_at(move.to_square):
                continue

            # Do the move.
            board.push(move)

            v_plus, success = self.probe_ab(board, -beta, -alpha)
            board.pop()

            if v_plus is None or not success:
                return None, 0

            v = -v_plus

            if v > alpha:
                if v >= beta:
                    return v, 2
                alpha = v

        v = self.probe_wdl_table(board)
        if v is None:
            return None, 0

        if alpha >= v:
            return alpha, 1 + int(alpha > 0)
        else:
            return v, 1

    def probe_wdl(self, board):
        """
        Probes WDL tables for win/draw/loss-information.

        Probing is thread-safe when done with different *board* objects and
        if *board* objects are not modified during probing.

        Returns ``None`` if the position was not found in any of the loaded
        tables.

        Returns ``2`` if the side to move is winning, ``0`` if the position is
        a draw and ``-2`` if the side to move is losing.

        Returns ``1`` in case of a cursed win and ``-1`` in case of a blessed
        loss. Mate can be forced but the position can be drawn due to the
        fifty-move rule.

        >>> with chess.syzygy.open_tablebases("data/syzygy") as tablebases:
        ...     tablebases.probe_wdl(chess.Board("8/2K5/4B3/3N4/8/8/4k3/8 b - - 0 1"))
        ...
        -2
        """
        # Positions with castling rights are not in the tablebase.
        if board.castling_rights:
            return None

        # Probe.
        v, success = self.probe_ab(board, -2, 2)
        if v is None or not success:
            return None

        # If en passant is not possible, we are done.
        if not board.ep_square:
            return v

        # Now handle en passant.
        v1 = -3

        # Look at least at all legal en passant captures.
        for move in board.generate_legal_moves(castling=False, pawns=True, knights=False, bishops=False, rooks=False, queens=False, king=False):
            # Filter out non-en-passant moves.
            if not board.is_en_passant(move):
                continue

            # Do the move.
            board.push(move)

            v0_plus, success = self.probe_ab(board, -2, 2)
            board.pop()

            if v0_plus is None or not success:
                return None

            v0 = -v0_plus

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

    def probe_dtz_table(self, board, wdl):
        key = calc_key(board)

        if key not in self.dtz:
            return None, 0

        return self.dtz[key].probe_dtz_table(board, wdl)

    def probe_dtz_no_ep(self, board):
        wdl, success = self.probe_ab(board, -2, 2)
        if wdl is None or not success:
            return None

        if wdl == 0:
            return 0

        if success == 2:
            return 1 if wdl == 2 else 101

        if wdl > 0:
            # Generate all legal non-capturing pawn moves.
            for move in board.generate_legal_moves(castling=False, pawns=True, knights=False, bishops=False, rooks=False, queens=False, king=False):
                if board.is_capture(move):
                    continue

                board.push(move)

                v_plus, success = self.probe_ab(board, -2, -wdl + 1)
                board.pop()

                if v_plus is None or not success:
                    return None

                v = -v_plus

                if v == wdl:
                    return 1 if v == 2 else 101

        dtz, success = self.probe_dtz_table(board, wdl)
        dtz += 1

        if success >= 0:
            if wdl & 1:
                dtz += 100
            return dtz if wdl >= 0 else -dtz

        if wdl > 0:
            best = 0xffff

            for move in board.generate_legal_moves(pawns=False):
                if board.piece_type_at(move.to_square):
                    continue

                board.push(move)

                v_plus = self.probe_dtz(board)
                board.pop()

                if v_plus is None:
                    return None

                v = -v_plus

                if v > 0 and v + 1 < best:
                    best = v + 1

            return best
        else:
            best = -1

            for move in board.generate_legal_moves():
                board.push(move)

                if board.halfmove_clock == 0:
                    if wdl == -2:
                        v = -1
                    else:
                        v, success = self.probe_ab(board, 1, 2)
                        if v is None or not success:
                            board.pop()
                            return None

                        v = 0 if v == 2 else -101
                else:
                    v_plus_one = self.probe_dtz(board)
                    if v_plus_one is None:
                        board.pop()
                        return None

                    v = -v_plus_one - 1

                board.pop()

                if v < best:
                    best = v

            return best

    def probe_dtz(self, board):
        """
        Probes DTZ tables for distance to zero information.

        Probing is thread-safe when done with different *board* objects and
        if *board* objects are not modified during probing.

        Return ``None`` if the position was not found in any of the loaded
        tables. Both DTZ and WDL tables are required in order to probe for DTZ
        values.

        Returns a positive value if the side to move is winning, ``0`` if the
        position is a draw and a negative value if the side to move is losing.

        A non-zero distance to zero means the number of halfmoves until the
        next pawn move or capture can be forced, keeping a won position.
        Minmaxing the DTZ values guarantees winning a won position (and drawing
        a drawn position), because it makes progress keeping the win in hand.
        However the lines are not always the most straightforward ways to win.
        Engines like Stockfish calculate themselves, checking with DTZ, but only
        play according to DTZ if they can not manage on their own.

        >>> with chess.syzygy.open_tablebases("data/syzygy") as tablebases:
        ...     tablebases.probe_dtz(chess.Board("8/2K5/4B3/3N4/8/8/4k3/8 b - - 0 1"))
        ...
        -53
        """
        v = self.probe_dtz_no_ep(board)
        if v is None:
            return None

        if not board.ep_square:
            return v

        v1 = -3

        for move in board.generate_legal_moves(castling=False, pawns=True, knights=False, bishops=False, rooks=False, queens=False, king=False):
            # Filter out non-en-passant moves.
            if not board.is_en_passant(move):
                continue

            board.push(move)

            v0_plus, success = self.probe_ab(board, -2, 2)
            board.pop()

            if v0_plus is None or not success:
                return None

            v0 = -v0_plus

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

    def close(self):
        """Closes all loaded tables."""
        while self.wdl:
            _, wdl = self.wdl.popitem()
            wdl.close()

        while self.dtz:
            _, dtz = self.dtz.popitem()
            dtz.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def open_tablebases(directory=None, load_wdl=True, load_dtz=True):
    """
    Opens a collection of tablebases for probing. See
    :class:`~chess.syzygy.Tablebases`."""
    return Tablebases(directory, load_wdl, load_dtz)
