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

import chess
import mmap
import os
import struct


WDL_MAGIC = [0x71, 0xE8, 0x23, 0x5D]

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


def subfactor(k, n):
    f = n
    l = 1
    i = 1
    while i < k:
        f += n - i
        l *= i + 1
        i += 1

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


class WdlTable(object):
    def __init__(self, filename):
        self.uint32 = struct.Struct("<I")
        self.ushort = struct.Struct("<H")

        # init_tb
        # TODO: Set properties dynamically
        self.symmetric = False # tbcore.cpp l. 224
        self.has_pawns = False
        self.num = 4
        self.has_pawns = False
        self.enc_type = 0
        self.pieces = {}
        self.norm = {}
        self.factor = {}
        self.tb_size = [0 for _ in range(8)]
        self.size = [0 for _ in range(8 * 3)]
        self.precomp = {}
        self._next = None
        self._flags = None

        # init_table_wdl
        self.f = open(filename, "r+b")
        self.data = mmap.mmap(self.f.fileno(), 0)

        assert "\x71" == self.data[0]
        assert "\xe8" == self.data[1]
        assert "\x23" == self.data[2]
        assert "\x5d" == self.data[3]

        split = ord(self.data[4]) & 0x01
        assert split == 1 # TODO: Might have different values for other tables
        files = 4 if ord(self.data[4]) & 0x02 else 1
        assert files == 1 # TODO: Might have different values for other tables

        data_ptr = 5

        # setup_pieces_piece
        self.pieces[chess.WHITE] = [ord(self.data[data_ptr + i + 1]) & 0x0f for i in range(self.num)]
        order = ord(self.data[data_ptr]) & 0x0f
        self.set_norm_piece(chess.WHITE)
        self.calc_factors_piece(chess.WHITE, order)

        self.pieces[chess.BLACK] = [ord(self.data[data_ptr + i + 1]) >> 4 for i in range(self.num)]
        order = ord(self.data[data_ptr]) >> 4
        self.set_norm_piece(chess.BLACK)
        self.calc_factors_piece(chess.BLACK, order)

        # back to init_table_wdl
        data_ptr += self.num + 1
        data_ptr += (data_ptr & 0x01)

        self.precomp[chess.WHITE] = self.setup_pairs(data_ptr, self.tb_size[0], 0)
        if split:
            self.precomp[chess.BLACK] = self.setup_pairs(data_ptr, self.tb_size[1], 3)
            data_ptr = self._next
        else:
            self.precomp[chess.BLACK] = None

        self.precomp[chess.WHITE].indextable = data_ptr
        data_ptr += self.size[0]
        if split:
            self.precomp[chess.BLACK].indextable = data_ptr
            data_ptr += self.size[3]

        self.precomp[chess.WHITE].sizetable = data_ptr
        data_ptr += self.size[1]
        if split:
            self.precomp[chess.BLACK].sizetable = data_ptr
            data_ptr += self.size[4]

        data_ptr = (data_ptr + 0x3f) & ~0x3f

        self.precomp[chess.WHITE].data = data_ptr
        data_ptr += self.size[2]
        if split:
            data_ptr = (data_ptr + 0x3f) & ~0x3f
            self.precomp[chess.BLACK].data = data_ptr

    def set_norm_piece(self, color):
        self.norm[color] = [0, 0, 0, 0, 0, 0]

        if self.enc_type == 0:
            self.norm[color][0] = 3
        elif self.enc_type == 2:
            self.norm[color][0] = 2
        else:
            self.norm[color][0] = self.enc_type - 1

        i = self.norm[color][0]
        while i < self.num:
            j = i
            while j < self.num and self.pieces[color][j] == self.pieces[color][i]:
                self.norm[color][i] += 1
                j += 1
            i += self.norm[color][i]

    def calc_factors_piece(self, color, order):
        self.factor[color] = [0, 0, 0, 0, 0, 0]

        PIVFAC = [31332, 28056, 462]

        n = 64 - self.norm[color][0]

        f = 1
        i = self.norm[color][0]
        k = 0
        while i < self.num or k == order:
            if k == order:
                self.factor[color][0] = f
                f *= PIVFAC[self.enc_type]
            else:
                self.factor[color][i] = f
                f *= subfactor(self.norm[color][i], n)
                n -= self.norm[color][i]
                i += self.norm[color][i]
            k += 1

        self.tb_size[color] = f

    def probe(self, board):
        # TODO: Test for KvK

        if self.symmetric:
            cmirror = 0 if board.turn == WHITE else 8
            mirror = 0 if board.turn == WHITE else 0x38
            bside = 0
        else:
            # TODO: Or maybe the inverse
            cmirror = mirror = 0
            bside = board.turn

        p = self.p(board, bside, cmirror)
        idx = self.encode_piece(bside, p)
        return self.decompress_pairs(bside, idx)

    def p(self, board, bside, cmirror):
        p = [0, 0, 0, 0, 0, 0]

        i = 0
        while i < self.num:
            piece_type = self.pieces[bside][i] & 0x07
            color = (self.pieces[bside][i] ^ cmirror) >> 3

            if piece_type == chess.PAWN:
                bb = board.pawns
            elif piece_type == chess.KNIGHT:
                bb = board.knights
            elif piece_type == chess.BISHOP:
                bb = board.bishops
            elif piece_type == chess.ROOK:
                bb = board.rooks
            elif piece_type == chess.QUEEN:
                bb = board.queens
            elif piece_type == chess.KING:
                bb = board.kings

            bb = bb & board.occupied_co[color]

            square = chess.bit_scan(bb)
            while square != -1 and square is not None:
                p[i] = square
                i += 1

                square = chess.bit_scan(bb, square + 1)

        return p

    def encode_piece(self, color, pos):
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
        else:
            # TODO: other enc types
            assert False

        idx *= self.factor[color][0]

        while i < n:
            t = self.norm[color][i]

            j = i
            while j < i + t:
                k = j + 1
                while k < i + t:
                    # Swap.
                    if pos[j] > pos[k]:
                        pos[j], pos[k] = pos[k], pos[j]
                    k += 1
                j += 1

            s = 0

            m = i
            while m < i + t:
                p = pos[m]
                l = 0
                j = 0
                while l < i:
                    j += int(p > pos[l])
                    l += 1
                s += BINOMIAL[m - i][p - j]
                m += 1

            idx += s * self.factor[color][i]
            i += t

        return idx

    def decompress_pairs(self, bside, idx):
        d = self.precomp[bside]

        if not d.idxbits:
            return d.min_len

        mainidx = idx >> d.idxbits
        litidx = (idx & (1 << d.idxbits) - 1) - (1 << (d.idxbits - 1))

        return

    def setup_pairs(self, data_ptr, tb_size, size_idx):
        d = PairsData()

        if ord(self.data[data_ptr]) & 0x80:
            # TODO
            assert False

        d.blocksize = ord(self.data[data_ptr + 1])
        d.idxbits = ord(self.data[data_ptr + 2])

        real_num_blocks = self.read_uint32(data_ptr + 4)
        num_blocks = real_num_blocks + ord(self.data[data_ptr + 3])
        max_len = ord(self.data[data_ptr + 8])
        min_len = ord(self.data[data_ptr + 9])
        h = max_len - min_len + 1
        num_syms = self.read_ushort(data_ptr + 10 + 2 * h)

        d.offset = data_ptr + 10
        d.symlen = [0 for _ in range(h * 8)]
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
        i = h - 2
        while i >= 0:
            d.base[i] = (d.base[i + 1] + self.read_ushort(d.offset + i) - self.read_ushort(d.offset +i + 1)) // 2
            i -= 1
        i = 0
        while i < h:
            d.base[i] <<= 64 - (min_len + i)
            i += 1

        d.offset -= d.min_len

        return d

    def calc_symlen(self, d, s, tmp):
        w = d.sympat + 3 * s
        s2 = (ord(self.data[w + 2]) << 4) | (ord(self.data[w + 1]) >> 4)
        if s2 == 0x0fff:
            d.symlen[s] = 0
        else:
            s1 = ((ord(self.data[w + 1]) & 0xf) << 8) | ord(self.data[w])
            if not tmp[s1]:
                self.calc_symlen(d, s1, tmp)
            if not tmp[s2]:
                self.calc_symlen(d, s2, tmp)
            d.symlen[s] = d.symlen[s1] + d.symlen[s2] + 1
        tmp[s] = 1

    def read_uint32(self, data_ptr):
        return self.uint32.unpack_from(self.data, data_ptr)[0]

    def read_ushort(self, data_ptr):
        return self.ushort.unpack_from(self.data, data_ptr)[0]

    def close(self):
        self.data.close()
        self.f.close()
