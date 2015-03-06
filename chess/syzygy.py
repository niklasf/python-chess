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
print BINOMIAL


def subfactor(k, n):
    f = n
    l = 1
    i = 1
    while i < k:
        f += n - i
        l *= i + 1
        i += 1

    return f // l


class WdlTable(object):
    def __init__(self, filename):
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
        self.tb_size = {}

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

        print "Pieces: ", self.pieces
        print "Norm: ", self.norm
        print "Factor: ", self.factor

        # back to init_table_wdl
        data_ptr += self.num + 1
        data_ptr += (data_ptr & 0x01)
        print data_ptr

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
        print "idx: ", self.encode_piece(bside, p)

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
                idx = 6 * 63 * 62 + DIAG[pos[0]] * 28 * 62 + LOWER[pos[1]] + 62 + pos[2] - j
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

    def close(self):
        self.data.close()
        self.f.close()


ZOBRIST = {
    chess.WHITE: {
        chess.PAWN: [
            0x83610FB1CD7C6A5,
            0xA37F944BE9DFC323,
            0xF6ABBE2515A93CBB,
            0x14D5CE796D3EA21,
            0x46762749C86B2BE7,
            0xAF8F7E5E5ED8DAB6,
            0x650F5E0808E360FA,
            0x92392E42419E33D7,
            0x3F00957BF619FABD,
            0x277059F962B2AD51,
            0xD5E6B582D55F02F8,
            0x6A8FC1E493122621,
            0xB93875281E1A9E10,
            0xFDCCFE46FD5C65B6,
            0x8FE7670648261096,
            0xFAF02033D4A8E4BE,
        ],
        chess.KNIGHT: [
            0x7ADFD3D554658027,
            0xFD774B1530CF1356,
            0xFBEBE15B01385C83,
            0x62D679429588CB4,
            0x6752115C2C5326E8,
            0x51B42635F0CDC9AA,
            0xAE93C5295995B5F8,
            0xD7B0BCD44364A6C6,
            0x3B5FF8AAA4B255A9,
            0x6C7F1261A536649A,
            0xE8AA5791CC441371,
            0xD86B5875C7DCB86D,
            0x9A46CFD78ED9B762,
            0xA0E117135D96DF38,
            0x9478EA3E9293FB5A,
            0x3A733F03155429C,
        ],
        chess.BISHOP: [
            0x28DFAD0A205B2E9C,
            0x3465686005390915,
            0x3B90F6E1F6C56840,
            0xE4109F19E9FA7F95,
            0x11D46F28D3DACE84,
            0xFE2BB5B257BE494F,
            0x7C2967E1B1ED0B95,
            0xE43B4A381A3A37CF,
            0x695059D5FFE6FBBF,
            0xB2F9E81B811A7170,
            0xCF46E879C65FE0AD,
            0xB9F97CD8A4D78595,
            0xC02A516DB8AE144F,
            0xAD435686FB04E9EC,
            0xF82BBB6F352A3960,
            0xE6E42DC57D2DF3E0,
        ],
        chess.ROOK: [
            0x351B3CB6FA0AFB17,
            0xF3FA5057957E9F1F,
            0x3CAF5F931167C3A4,
            0x49D1915FD8EC1F,
            0x8415B4CDB479775D,
            0xE8C4292086C4105C,
            0xA8BCE7AEE1239B7D,
            0xFE39B02A48D2A9E0,
            0xC739FE5DCD4457D3,
            0x1403DB8FB3519890,
            0xE8B28DB23FF09313,
            0xBB5D403967D07997,
            0xAC490676033EFF75,
            0x16A04FA30D1BF9D3,
            0x997217E09587296C,
            0xF3117E27351004E4,
        ],
        chess.QUEEN: [
            0xC3E6CBC2D58D54E2,
            0xC9D65764E662A03,
            0x35398CF17F55E546,
            0x36298D8994EF782F,
            0x74A1686641906112,
            0x932E26C31E2A841C,
            0x742E57797E804B64,
            0x8CD96F04C93BCD46,
            0x8EAA7A1FB167256E,
            0xB2B979D48293CED2,
            0x148AFC7B1AD4A2E2,
            0xD6011DBA4F25674B,
            0xDE9B1153C122B489,
            0x971F14A615BEA388,
            0x634B1F6B0B3AFB58,
            0xD4AABC1364BB0003,
        ],
        chess.KING: [
            0xEFF5EEB2A2B20B32,
            0x48BB703400DB90C5,
            0xADEE028408E7E3E8,
            0x659A2E1B59C31F32,
            0xEE8881A63B2D62B5,
            0xBD6D5581989BDD88,
            0x6D531BDD223994F9,
            0x776495A7D3403463,
            0x33C8A19C4C5CC49E,
            0xC69CFCEDFE47CA25,
            0xE8071DFA94C0413F,
            0xD91E6C71A4A8A576,
            0xD484D7E096B2D4D7,
            0x7BFF7A4A384D89B,
            0x8C45618188FA0EEE,
            0x30326012537C059,
        ],
    },
    chess.BLACK: {
        chess.PAWN: [
            0xA38152E5792C41DD,
            0x262270C3737300B1,
            0x33B1082FF0C8E331,
            0x8EEA7C34ADAE9A6D,
            0x95230505C46B9A3D,
            0xDE8F0350047FB7A6,
            0xF41592EC09662620,
            0x5F7DAA8E72708B86,
            0x7C6FE7D5A169624,
            0x5BF5AE615CD3BF25,
            0x250EEE0284FD0950,
            0x3B673E349479CBEE,
            0x145F4ED31313BFC4,
            0x69C026F532C3D433,
            0xB946085D9A96DAF2,
            0x8CB2F1089FE5C7BD,
        ],
        chess.KNIGHT: [
            0xCF1C140354D90D8D,
            0xFF011F11A27E1DB5,
            0x2F81119B6645BEF5,
            0xD3A5F1BCC336EF9A,
            0xD09C41011C888AB4,
            0xD6342E300E40C410,
            0x577EB38E32439A91,
            0xB16FFD8E6EDE433F,
            0x88201E51DBCA9B91,
            0x87C7B999DC878B73,
            0xFBB96E76D739CAF2,
            0xFFC91F5554E883F7,
            0xFBDB1BB1163963E1,
            0xB033E55A5BFF12E9,
            0x19BDBBE311BBFE5A,
            0xB28C6C7C5F400188,
        ],
        chess.BISHOP: [
            0x3011C4D28635DBDF,
            0x13B174F3EEFDC297,
            0x41C1AA861DC79560,
            0x96FFF72F157413D6,
            0x546E8E8EC8773076,
            0xD5B58B684D1A5399,
            0x8BDB03E3E6D29838,
            0x421C53655BBC1521,
            0x1C920A8701F626CF,
            0xE172BFB282E929B1,
            0xAE27D629BADB1B6D,
            0x4738EC83A85F112A,
            0xB7566E63C52F73FF,
            0x6FB5E187FBD0757E,
            0xC52FC3ED8FF08176,
            0xD03BB85163751086,
        ],
        chess.ROOK: [
            0x1C6A15E74C484818,
            0x394ECC7315C776B3,
            0x8B338C025467AF83,
            0x755DF72E74E28C2C,
            0x96102C2F4721596,
            0xDA324813D5F5165C,
            0x13A72CF0F2F0C8C4,
            0xFE8772410008712A,
            0x3B640EFBB53B4127,
            0x69779F11FC633452,
            0x75DE90B625FDA51D,
            0x4B9C82EE1E1CB305,
            0x6EACE48F276BE344,
            0x32D00FCEB789EC71,
            0xF1FAA8B8A4ADDD4A,
            0x6B2DD36FBF2E5EC4,
        ],
        chess.QUEEN: [
            0x68085E26DBE3AD56,
            0x9A9D46582A40120B,
            0x8AA6ABBD2CAD7D96,
            0x5527A24035773ED8,
            0xC79805AF15FA519C,
            0xA9A03E8FB9F60885,
            0x82F999D825DB04E0,
            0x49DB5F367E106034,
            0x83FBFC6A4AA8F161,
            0xC1DAEDBAA5D01451,
            0x7D938E607492DFE8,
            0x622135DE5B37F9C1,
            0x6946D729CE3A1019,
            0xB19A3DFDD10D34A8,
            0xBFF22FD4F4268351,
            0xC329A8B2C951B7FF,
        ],
        chess.KING: [
            0xABAB879CD5585F2F,
            0xFDB8A69BC4052DD5,
            0xA097AF8B98AE5653,
            0xA7262BE7FA75D97B,
            0xDA8F8AE4C5526FBA,
            0xAC8D445DC93990B3,
            0x311E44664EA37966,
            0x72358B3B76D6E28B,
            0xFD84B139D74DA2AD,
            0xFBAD215CCD898848,
            0x8C7A00A136A05FFD,
            0x7709E685C945EE73,
            0xEB32EFD0627AECC1,
            0x3E6F41983F953CD8,
            0x46EBF3BD647CC189,
            0x21E91003E0E722B7,
        ],
    },
}


def calc_key(board, mirror=False):
    key = 0

    for color in chess.COLORS:
        mirrored_color = color ^ 1 if mirror else color

        for pop in range(chess.pop_count(board.pawns & board.occupied_co[color])):
                key ^= ZOBRIST[mirrored_color][chess.PAWN][pop]

        for pop in range(chess.pop_count(board.knights & board.occupied_co[color])):
                key ^= ZOBRIST[mirrored_color][chess.KNIGHT][pop]

        for pop in range(chess.pop_count(board.bishops & board.occupied_co[color])):
                key ^= ZOBRIST[mirrored_color][chess.BISHOP][pop]

        for pop in range(chess.pop_count(board.rooks & board.occupied_co[color])):
                key ^= ZOBRIST[mirrored_color][chess.ROOK][pop]

        for pop in range(chess.pop_count(board.queens & board.occupied_co[color])):
                key ^= ZOBRIST[mirrored_color][chess.QUEEN][pop]

        for pop in range(chess.pop_count(board.kings & board.occupied_co[color])):
                key ^= ZOBRIST[mirrored_color][chess.KING][pop]

    return key
