# This file is part of the python-chess library.
# Copyright (C) 2015 Jean-Noël Avila <jn.avila@free.fr>
# Copyright (C) 2015-2021 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

import ctypes
import ctypes.util
import dataclasses
import fnmatch
import logging
import lzma
import os
import os.path
import struct
import typing

import chess

from types import TracebackType
from typing import BinaryIO, Callable, Dict, List, Optional, Tuple, Type, Union


LOGGER = logging.getLogger(__name__)


NOSQUARE = 64
NOINDEX = -1

MAX_KKINDEX = 462
MAX_PPINDEX = 576
MAX_PpINDEX = 24 * 48
MAX_AAINDEX = (63 - 62) + (62 // 2 * (127 - 62)) - 1 + 1
MAX_AAAINDEX = 64 * 21 * 31
MAX_PPP48_INDEX = 8648
MAX_PP48_INDEX = 1128

MAX_KXK = MAX_KKINDEX * 64
MAX_kabk = MAX_KKINDEX * 64 * 64
MAX_kakb = MAX_KKINDEX * 64 * 64
MAX_kpk = 24 * 64 * 64
MAX_kakp = 24 * 64 * 64 * 64
MAX_kapk = 24 * 64 * 64 * 64
MAX_kppk = MAX_PPINDEX * 64 * 64
MAX_kpkp = MAX_PpINDEX * 64 * 64
MAX_kaak = MAX_KKINDEX * MAX_AAINDEX
MAX_kabkc = MAX_KKINDEX * 64 * 64 * 64
MAX_kabck = MAX_KKINDEX * 64 * 64 * 64
MAX_kaakb = MAX_KKINDEX * MAX_AAINDEX * 64
MAX_kaabk = MAX_KKINDEX * MAX_AAINDEX * 64
MAX_kabbk = MAX_KKINDEX * MAX_AAINDEX * 64
MAX_kaaak = MAX_KKINDEX * MAX_AAAINDEX
MAX_kapkb = 24 * 64 * 64 * 64 * 64
MAX_kabkp = 24 * 64 * 64 * 64 * 64
MAX_kabpk = 24 * 64 * 64 * 64 * 64
MAX_kppka = MAX_kppk * 64
MAX_kappk = MAX_kppk * 64
MAX_kapkp = MAX_kpkp * 64
MAX_kaapk = 24 * MAX_AAINDEX * 64 * 64
MAX_kaakp = 24 * MAX_AAINDEX * 64 * 64
MAX_kppkp = 24 * MAX_PP48_INDEX * 64 * 64
MAX_kpppk = MAX_PPP48_INDEX * 64 * 64

PLYSHIFT = 3
INFOMASK = 7

WE_FLAG = 1
NS_FLAG = 2
NW_SE_FLAG = 4

ITOSQ = [
    chess.H7, chess.G7, chess.F7, chess.E7,
    chess.H6, chess.G6, chess.F6, chess.E6,
    chess.H5, chess.G5, chess.F5, chess.E5,
    chess.H4, chess.G4, chess.F4, chess.E4,
    chess.H3, chess.G3, chess.F3, chess.E3,
    chess.H2, chess.G2, chess.F2, chess.E2,
    chess.D7, chess.C7, chess.B7, chess.A7,
    chess.D6, chess.C6, chess.B6, chess.A6,
    chess.D5, chess.C5, chess.B5, chess.A5,
    chess.D4, chess.C4, chess.B4, chess.A4,
    chess.D3, chess.C3, chess.B3, chess.A3,
    chess.D2, chess.C2, chess.B2, chess.A2,
]

ENTRIES_PER_BLOCK = 16 * 1024

EGTB_MAXBLOCKSIZE = 65536


def map24_b(s: int) -> int:
    s -= 8
    return ((s & 3) + s) >> 1

def map88(x: int) -> int:
    return x + (x & 56)

def in_queenside(x: int) -> int:
    return (x & (1 << 2)) == 0

def flip_we(x: int) -> int:
    return x ^ 7

def flip_ns(x: int) -> int:
    return x ^ 56

def flip_nw_se(x: int) -> int:
    return ((x & 7) << 3) | (x >> 3)

def idx_is_empty(x: int) -> int:
    return x == -1


def flip_type(x: chess.Square, y: chess.Square) -> int:
    ret = 0

    if chess.square_file(x) > 3:
        x = flip_we(x)
        y = flip_we(y)
        ret |= 1

    if chess.square_rank(x) > 3:
        x = flip_ns(x)
        y = flip_ns(y)
        ret |= 2

    rowx = chess.square_rank(x)
    colx = chess.square_file(x)

    if rowx > colx:
        x = flip_nw_se(x)
        y = flip_nw_se(y)
        ret |= 4

    rowy = chess.square_rank(y)
    coly = chess.square_file(y)
    if rowx == colx and rowy > coly:
        x = flip_nw_se(x)
        y = flip_nw_se(y)
        ret |= 4

    return ret

def init_flipt() -> List[List[int]]:
    return [[flip_type(j, i) for i in range(64)] for j in range(64)]

FLIPT = init_flipt()


def init_pp48_idx() -> Tuple[List[List[int]], List[int], List[int]]:
    MAX_I = 48
    MAX_J = 48
    idx = 0
    pp48_idx = [[-1] * MAX_J for i in range(MAX_I)]
    pp48_sq_x = [NOSQUARE] * MAX_PP48_INDEX
    pp48_sq_y = [NOSQUARE] * MAX_PP48_INDEX

    idx = 0
    for a in range(chess.H7, chess.A2 - 1, -1):
        for b in range(a - 1, chess.A2 - 1, -1):
            i = flip_we(flip_ns(a)) - 8
            j = flip_we(flip_ns(b)) - 8

            if idx_is_empty(pp48_idx[i][j]):
                pp48_idx[i][j] = idx
                pp48_idx[j][i] = idx
                pp48_sq_x[idx] = i
                pp48_sq_y[idx] = j
                idx += 1

    return pp48_idx, pp48_sq_x, pp48_sq_y

PP48_IDX, PP48_SQ_X, PP48_SQ_Y = init_pp48_idx()


def init_ppp48_idx() -> Tuple[List[List[List[int]]], List[int], List[int], List[int]]:
    MAX_I = 48
    MAX_J = 48
    MAX_K = 48
    ppp48_idx = [[[-1] * MAX_I for j in range(MAX_J)] for k in range(MAX_K)]
    ppp48_sq_x = [NOSQUARE] * MAX_PPP48_INDEX
    ppp48_sq_y = [NOSQUARE] * MAX_PPP48_INDEX
    ppp48_sq_z = [NOSQUARE] * MAX_PPP48_INDEX

    idx = 0
    for x in range(48):
        for y in range(x + 1, 48):
            for z in range(y + 1, 48):
                a = ITOSQ[x]
                b = ITOSQ[y]
                c = ITOSQ[z]
                if not in_queenside(b) or not in_queenside(c):
                    continue

                i = a - 8
                j = b - 8
                k = c - 8

                if idx_is_empty(ppp48_idx[i][j][k]):
                    ppp48_idx[i][j][k] = idx
                    ppp48_idx[i][k][j] = idx
                    ppp48_idx[j][i][k] = idx
                    ppp48_idx[j][k][i] = idx
                    ppp48_idx[k][i][j] = idx
                    ppp48_idx[k][j][i] = idx
                    ppp48_sq_x[idx] = i
                    ppp48_sq_y[idx] = j
                    ppp48_sq_z[idx] = k
                    idx += 1

    return ppp48_idx, ppp48_sq_x, ppp48_sq_y, ppp48_sq_z

PPP48_IDX, PPP48_SQ_X, PPP48_SQ_Y, PPP48_SQ_Z = init_ppp48_idx()


def init_aaidx() -> Tuple[List[int], List[List[int]]]:
    aaidx = [[-1] * 64 for y in range(64)]
    aabase = [0] * MAX_AAINDEX

    idx = 0
    for x in range(64):
        for y in range(x + 1, 64):

            if idx_is_empty(aaidx[x][y]):
                # Still empty.
                aaidx[x][y] = idx
                aaidx[y][x] = idx
                aabase[idx] = x
                idx += 1

    return aabase, aaidx

AABASE, AAIDX = init_aaidx()


def init_aaa() -> Tuple[List[int], List[List[int]]]:
    # Get aaa_base.
    comb = [a * (a - 1) // 2 for a in range(64)]

    accum = 0
    aaa_base = [0] * 64
    for a in range(64 - 1):
        accum += comb[a]
        aaa_base[a + 1] = accum

    # Get aaa_xyz.
    aaa_xyz = [[-1] * 3 for idx in range(MAX_AAAINDEX)]

    idx = 0
    for z in range(64):
        for y in range(z):
            for x in range(y):
                aaa_xyz[idx][0] = x
                aaa_xyz[idx][1] = y
                aaa_xyz[idx][2] = z
                idx += 1

    return aaa_base, aaa_xyz

AAA_BASE, AAA_XYZ = init_aaa()


def pp_putanchorfirst(a: int, b: int) -> Tuple[int, int]:
    row_b = b & 56
    row_a = a & 56

    # Default.
    anchor = a
    loosen = b

    if row_b > row_a:
        anchor = b
        loosen = a
    elif row_b == row_a:
        x = a
        col = x & 7
        inv = col ^ 7
        x = (1 << col) | (1 << inv)
        x &= (x - 1)
        hi_a = x

        x = b
        col = x & 7
        inv = col ^ 7
        x = (1 << col) | (1 << inv)
        x &= (x - 1)
        hi_b = x

        if hi_b > hi_a:
            anchor = b
            loosen = a

        if hi_b < hi_a:
            anchor = a
            loosen = b

        if hi_b == hi_a:
            if a < b:
                anchor = a
                loosen = b
            else:
                anchor = b
                loosen = a

    return anchor, loosen

def wsq_to_pidx24(pawn: int) -> int:
    sq = pawn

    sq = flip_ns(sq)
    sq -= 8  # Down one row

    idx24 = (sq + (sq & 3)) >> 1
    return idx24

def wsq_to_pidx48(pawn: int) -> int:
    sq = pawn

    sq = flip_ns(sq)
    sq -= 8  # Down one row

    idx48 = sq
    return idx48

def init_ppidx() -> Tuple[List[List[int]], List[int], List[int]]:
    ppidx = [[-1] * 48 for i in range(24)]
    pp_hi24 = [-1] * MAX_PPINDEX
    pp_lo48 = [-1] * MAX_PPINDEX

    idx = 0
    for a in range(chess.H7, chess.A2 - 1, -1):
        if in_queenside(a):
            continue

        for b in range(a - 1, chess.A2 - 1, -1):
            anchor = 0
            loosen = 0

            anchor, loosen = pp_putanchorfirst(a, b)

            if (anchor & 7) > 3:
                # Square on the kingside.
                anchor = flip_we(anchor)
                loosen = flip_we(loosen)

            i = wsq_to_pidx24(anchor)
            j = wsq_to_pidx48(loosen)

            if idx_is_empty(ppidx[i][j]):
                ppidx[i][j] = idx
                pp_hi24[idx] = i
                pp_lo48[idx] = j
                idx += 1

    return ppidx, pp_hi24, pp_lo48

PPIDX, PP_HI24, PP_LO48 = init_ppidx()


def norm_kkindex(x: chess.Square, y: chess.Square) -> Tuple[int, int]:
    if chess.square_file(x) > 3:
        x = flip_we(x)
        y = flip_we(y)

    if chess.square_rank(x) > 3:
        x = flip_ns(x)
        y = flip_ns(y)

    rowx = chess.square_rank(x)
    colx = chess.square_file(x)

    if rowx > colx:
        x = flip_nw_se(x)
        y = flip_nw_se(y)

    rowy = chess.square_rank(y)
    coly = chess.square_file(y)

    if rowx == colx and rowy > coly:
        x = flip_nw_se(x)
        y = flip_nw_se(y)

    return x, y

def init_kkidx() -> Tuple[List[List[int]], List[int], List[int]]:
    kkidx = [[-1] * 64 for x in range(64)]
    bksq = [-1] * MAX_KKINDEX
    wksq = [-1] * MAX_KKINDEX
    idx = 0
    for x in range(64):
        for y in range(64):
            # Check if x to y is legal.
            if x != y and not chess.BB_KING_ATTACKS[x] & chess.BB_SQUARES[y]:
                # Normalize.
                i, j = norm_kkindex(x, y)

                if idx_is_empty(kkidx[i][j]):
                    kkidx[i][j] = idx
                    kkidx[x][y] = idx
                    bksq[idx] = i
                    wksq[idx] = j
                    idx += 1

    return kkidx, wksq, bksq

KKIDX, WKSQ, BKSQ = init_kkidx()


def kxk_pctoindex(c: Request) -> int:
    BLOCK_Ax = 64

    ft = flip_type(c.black_piece_squares[0], c.white_piece_squares[0])

    ws = c.white_piece_squares
    bs = c.black_piece_squares

    if (ft & 1) != 0:
        ws = [flip_we(b) for b in ws]
        bs = [flip_we(b) for b in bs]

    if (ft & 2) != 0:
        ws = [flip_ns(b) for b in ws]
        bs = [flip_ns(b) for b in bs]

    if (ft & 4) != 0:
        ws = [flip_nw_se(b) for b in ws]
        bs = [flip_nw_se(b) for b in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]

    if ki == -1:
        return NOINDEX

    return ki * BLOCK_Ax + ws[1]

def kapkb_pctoindex(c: Request) -> int:
    BLOCK_A = 64 * 64 * 64 * 64
    BLOCK_B = 64 * 64 * 64
    BLOCK_C = 64 * 64
    BLOCK_D = 64

    pawn = c.white_piece_squares[2]
    wa = c.white_piece_squares[1]
    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]
    ba = c.black_piece_squares[1]

    if not (chess.A2 <= pawn < chess.A8):
        return NOINDEX

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        ba = flip_we(ba)

    sq = pawn
    sq ^= 56  # flip_ns
    sq -= 8   # Down one row
    pslice = (sq + (sq & 3)) >> 1

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + ba

def kabpk_pctoindex(c: Request) -> int:
    BLOCK_A = 64 * 64 * 64 * 64
    BLOCK_B = 64 * 64 * 64
    BLOCK_C = 64 * 64
    BLOCK_D = 64

    wk = c.white_piece_squares[0]
    wa = c.white_piece_squares[1]
    wb = c.white_piece_squares[2]
    pawn = c.white_piece_squares[3]
    bk = c.black_piece_squares[0]

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        wb = flip_we(wb)

    pslice = wsq_to_pidx24(pawn)

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + wb

def kabkp_pctoindex(c: Request) -> int:
    BLOCK_A = 64 * 64 * 64 * 64
    BLOCK_B = 64 * 64 * 64
    BLOCK_C = 64 * 64
    BLOCK_D = 64

    pawn = c.black_piece_squares[1]
    wa = c.white_piece_squares[1]
    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]
    wb = c.white_piece_squares[2]

    if not (chess.A2 <= pawn < chess.A8):
        return NOINDEX

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        wb = flip_we(wb)

    sq = pawn
    sq -= 8  # Down one row
    pslice = (sq + (sq & 3)) >> 1

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + wb

def kaapk_pctoindex(c: Request) -> int:
    BLOCK_C = MAX_AAINDEX
    BLOCK_B = 64 * BLOCK_C
    BLOCK_A = 64 * BLOCK_B

    wk = c.white_piece_squares[0]
    wa = c.white_piece_squares[1]
    wa2 = c.white_piece_squares[2]
    pawn = c.white_piece_squares[3]
    bk = c.black_piece_squares[0]

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        wa2 = flip_we(wa2)

    pslice = wsq_to_pidx24(pawn)

    aa_combo = AAIDX[wa][wa2]

    if idx_is_empty(aa_combo):
        return NOINDEX

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + aa_combo

def kaakp_pctoindex(c: Request) -> int:
    BLOCK_C = MAX_AAINDEX
    BLOCK_B = 64 * BLOCK_C
    BLOCK_A = 64 * BLOCK_B

    wk = c.white_piece_squares[0]
    wa = c.white_piece_squares[1]
    wa2 = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]
    pawn = c.black_piece_squares[1]

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)
        wa2 = flip_we(wa2)

    pawn = flip_ns(pawn)
    pslice = wsq_to_pidx24(pawn)

    aa_combo = AAIDX[wa][wa2]

    if idx_is_empty(aa_combo):
        return NOINDEX

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + aa_combo

def kapkp_pctoindex(c: Request) -> int:
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    wk = c.white_piece_squares[0]
    wa = c.white_piece_squares[1]
    pawn_a = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]
    pawn_b = c.black_piece_squares[1]

    anchor = pawn_a
    loosen = pawn_b

    if (anchor & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        anchor = flip_we(anchor)
        loosen = flip_we(loosen)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)

    m = wsq_to_pidx24(anchor)
    n = loosen - 8
    pp_slice = m * 48 + n

    if idx_is_empty(pp_slice):
        return NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa

def kappk_pctoindex(c: Request) -> int:
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    wk = c.white_piece_squares[0]
    wa = c.white_piece_squares[1]
    pawn_a = c.white_piece_squares[2]
    pawn_b = c.white_piece_squares[3]
    bk = c.black_piece_squares[0]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        anchor = flip_we(anchor)
        loosen = flip_we(loosen)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)

    pp_slice = PPIDX[i][j]

    if idx_is_empty(pp_slice):
        return NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa

def kppka_pctoindex(c: Request) -> int:
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    wk = c.white_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]
    ba = c.black_piece_squares[1]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        anchor = flip_we(anchor)
        loosen = flip_we(loosen)
        wk = flip_we(wk)
        bk = flip_we(bk)
        ba = flip_we(ba)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)

    pp_slice = PPIDX[i][j]

    if idx_is_empty(pp_slice):
        return NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + ba

def kabck_pctoindex(c: Request) -> int:
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    ft = FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & WE_FLAG) != 0:
        ws = [flip_we(i) for i in ws]
        bs = [flip_we(i) for i in bs]

    if (ft & NS_FLAG) != 0:
        ws = [flip_ns(i) for i in ws]
        bs = [flip_ns(i) for i in bs]

    if (ft & NW_SE_FLAG) != 0:
        ws = [flip_nw_se(i) for i in ws]
        bs = [flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]

    if idx_is_empty(ki):
        return NOINDEX

    return ki * BLOCK_A + ws[1] * BLOCK_B + ws[2] * BLOCK_C + ws[3]

def kabbk_pctoindex(c: Request) -> int:
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * MAX_AAINDEX

    ft = FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & WE_FLAG) != 0:
        ws = [flip_we(i) for i in ws]
        bs = [flip_we(i) for i in bs]

    if (ft & NS_FLAG) != 0:
        ws = [flip_ns(i) for i in ws]
        bs = [flip_ns(i) for i in bs]

    if (ft & NW_SE_FLAG) != 0:
        ws = [flip_nw_se(i) for i in ws]
        bs = [flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]
    ai = AAIDX[ws[2]][ws[3]]

    if idx_is_empty(ki) or idx_is_empty(ai):
        return NOINDEX

    return ki * BLOCK_Ax + ai * BLOCK_Bx + ws[1]

def kaabk_pctoindex(c: Request) -> int:
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * MAX_AAINDEX

    ft = FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & WE_FLAG) != 0:
        ws = [flip_we(i) for i in ws]
        bs = [flip_we(i) for i in bs]

    if (ft & NS_FLAG) != 0:
        ws = [flip_ns(i) for i in ws]
        bs = [flip_ns(i) for i in bs]

    if (ft & NW_SE_FLAG) != 0:
        ws = [flip_nw_se(i) for i in ws]
        bs = [flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]
    ai = AAIDX[ws[1]][ws[2]]

    if idx_is_empty(ki) or idx_is_empty(ai):
        return NOINDEX

    return ki * BLOCK_Ax + ai * BLOCK_Bx + ws[3]

def aaa_getsubi(x: int, y: int, z: int) -> int:
    bse = AAA_BASE[z]
    calc_idx = x + (y - 1) * y // 2 + bse
    return calc_idx

def kaaak_pctoindex(c: Request) -> int:
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_Ax = MAX_AAAINDEX

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    ft = FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    if (ft & WE_FLAG) != 0:
        ws = [flip_we(i) for i in ws]
        bs = [flip_we(i) for i in bs]

    if (ft & NS_FLAG) != 0:
        ws = [flip_ns(i) for i in ws]
        bs = [flip_ns(i) for i in bs]

    if (ft & NW_SE_FLAG) != 0:
        ws = [flip_nw_se(i) for i in ws]
        bs = [flip_nw_se(i) for i in bs]

    if ws[2] < ws[1]:
        tmp = ws[1]
        ws[1] = ws[2]
        ws[2] = tmp
    if ws[3] < ws[2]:
        tmp = ws[2]
        ws[2] = ws[3]
        ws[3] = tmp
    if ws[2] < ws[1]:
        tmp = ws[1]
        ws[1] = ws[2]
        ws[2] = tmp

    ki = KKIDX[bs[0]][ws[0]]

    if ws[1] == ws[2] or ws[1] == ws[3] or ws[2] == ws[3]:
        return NOINDEX

    ai = aaa_getsubi(ws[1], ws[2], ws[3])

    if idx_is_empty(ki) or idx_is_empty(ai):
        return NOINDEX

    return ki * BLOCK_Ax + ai

def kppkp_pctoindex(c: Request) -> int:
    BLOCK_Ax = MAX_PP48_INDEX * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    wk = c.white_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]
    pawn_c = c.black_piece_squares[1]

    if (pawn_c & 7) > 3:
        wk = flip_we(wk)
        pawn_a = flip_we(pawn_a)
        pawn_b = flip_we(pawn_b)
        bk = flip_we(bk)
        pawn_c = flip_we(pawn_c)

    i = flip_we(flip_ns(pawn_a)) - 8
    j = flip_we(flip_ns(pawn_b)) - 8

    # Black pawn, so low indexes are more advanced.
    k = map24_b(pawn_c)

    pp48_slice = PP48_IDX[i][j]

    if idx_is_empty(pp48_slice):
        return NOINDEX

    return k * BLOCK_Ax + pp48_slice * BLOCK_Bx + wk * BLOCK_Cx + bk

def kaakb_pctoindex(c: Request) -> int:
    N_WHITE = 3
    N_BLACK = 2
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * MAX_AAINDEX

    ft = FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & WE_FLAG) != 0:
        ws = [flip_we(i) for i in ws]
        bs = [flip_we(i) for i in bs]

    if (ft & NS_FLAG) != 0:
        ws = [flip_ns(i) for i in ws]
        bs = [flip_ns(i) for i in bs]

    if (ft & NW_SE_FLAG) != 0:
        ws = [flip_nw_se(i) for i in ws]
        bs = [flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]
    ai = AAIDX[ws[1]][ws[2]]

    if idx_is_empty(ki) or idx_is_empty(ai):
        return NOINDEX

    return ki * BLOCK_Ax + ai * BLOCK_Bx + bs[1]

def kabkc_pctoindex(c: Request) -> int:
    N_WHITE = 3
    N_BLACK = 2

    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    ft = FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & WE_FLAG) != 0:
        ws = [flip_we(i) for i in ws]
        bs = [flip_we(i) for i in bs]

    if (ft & NS_FLAG) != 0:
        ws = [flip_ns(i) for i in ws]
        bs = [flip_ns(i) for i in bs]

    if (ft & NW_SE_FLAG) != 0:
        ws = [flip_nw_se(i) for i in ws]
        bs = [flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX [black king] [white king]

    if idx_is_empty(ki):
        return NOINDEX

    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + ws[2] * BLOCK_Cx + bs[1]

def kpkp_pctoindex(c: Request) -> int:
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.black_piece_squares[1]

    anchor = pawn_a
    loosen = pawn_b

    if (anchor & 7) > 3:
        anchor = flip_we(anchor)
        loosen = flip_we(loosen)
        wk = flip_we(wk)
        bk = flip_we(bk)

    m = wsq_to_pidx24(anchor)
    n = loosen - 8

    pp_slice = m * 48 + n

    if idx_is_empty(pp_slice):
        return NOINDEX

    return pp_slice * BLOCK_Ax + wk * BLOCK_Bx + bk

def kppk_pctoindex(c: Request) -> int:
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64
    wk = c.white_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        anchor = flip_we(anchor)
        loosen = flip_we(loosen)
        wk = flip_we(wk)
        bk = flip_we(bk)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)

    pp_slice = PPIDX[i][j]

    if idx_is_empty(pp_slice):
        return NOINDEX

    return pp_slice * BLOCK_Ax + wk * BLOCK_Bx + bk

def kapk_pctoindex(c: Request) -> int:
    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    pawn = c.white_piece_squares[2]
    wa = c.white_piece_squares[1]
    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]

    if not (chess.A2 <= pawn < chess.A8):
        return NOINDEX

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)

    sq = pawn
    sq ^= 56  # flip_ns
    sq -= 8   # Down one row
    pslice = ((sq + (sq & 3)) >> 1)

    return pslice * BLOCK_Ax + wk * BLOCK_Bx + bk * BLOCK_Cx + wa

def kabk_pctoindex(c: Request) -> int:
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    ft = flip_type(c.black_piece_squares[0], c.white_piece_squares[0])

    ws = c.white_piece_squares
    bs = c.black_piece_squares

    if (ft & 1) != 0:
        ws = [flip_we(b) for b in ws]
        bs = [flip_we(b) for b in bs]

    if (ft & 2) != 0:
        ws = [flip_ns(b) for b in ws]
        bs = [flip_ns(b) for b in bs]

    if (ft & 4) != 0:
        ws = [flip_nw_se(b) for b in ws]
        bs = [flip_nw_se(b) for b in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]

    if idx_is_empty(ki):
        return NOINDEX

    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + ws[2]

def kakp_pctoindex(c: Request) -> int:
    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    pawn = c.black_piece_squares[1]
    wa = c.white_piece_squares[1]
    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]

    if not (chess.A2 <= pawn < chess.A8):
        return NOINDEX

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)
        wa = flip_we(wa)

    sq = pawn
    sq -= 8  # Down one row
    pslice = (sq + (sq & 3)) >> 1

    return pslice * BLOCK_Ax + wk * BLOCK_Bx + bk * BLOCK_Cx + wa

def kaak_pctoindex(c: Request) -> int:
    N_WHITE = 3
    N_BLACK = 1
    BLOCK_Ax = MAX_AAINDEX

    ft = FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & WE_FLAG) != 0:
        ws = [flip_we(i) for i in ws]
        bs = [flip_we(i) for i in bs]

    if (ft & NS_FLAG) != 0:
        ws = [flip_ns(i) for i in ws]
        bs = [flip_ns(i) for i in bs]

    if (ft & NW_SE_FLAG) != 0:
        ws = [flip_nw_se(i) for i in ws]
        bs = [flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]
    ai = AAIDX[ws[1]][ws[2]]

    if idx_is_empty(ki) or idx_is_empty(ai):
        return NOINDEX

    return ki * BLOCK_Ax + ai

def kakb_pctoindex(c: Request) -> int:
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    ft = FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:]
    bs = c.black_piece_squares[:]

    if (ft & 1) != 0:
        ws[0] = flip_we(ws[0])
        ws[1] = flip_we(ws[1])
        bs[0] = flip_we(bs[0])
        bs[1] = flip_we(bs[1])

    if (ft & 2) != 0:
        ws[0] = flip_ns(ws[0])
        ws[1] = flip_ns(ws[1])
        bs[0] = flip_ns(bs[0])
        bs[1] = flip_ns(bs[1])

    if (ft & 4) != 0:
        ws[0] = flip_nw_se(ws[0])
        ws[1] = flip_nw_se(ws[1])
        bs[0] = flip_nw_se(bs[0])
        bs[1] = flip_nw_se(bs[1])

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]

    if idx_is_empty(ki):
        return NOINDEX

    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + bs[1]

def kpk_pctoindex(c: Request) -> int:
    BLOCK_A = 64 * 64
    BLOCK_B = 64

    pawn = c.white_piece_squares[1]
    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]

    if not (chess.A2 <= pawn < chess.A8):
        return NOINDEX

    if (pawn & 7) > 3:
        pawn = flip_we(pawn)
        wk = flip_we(wk)
        bk = flip_we(bk)

    sq = pawn
    sq ^= 56  # flip_ns
    sq -= 8   # Down one row
    pslice = ((sq + (sq & 3)) >> 1)

    res = pslice * BLOCK_A + wk * BLOCK_B + bk
    return res

def kpppk_pctoindex(c: Request) -> int:
    BLOCK_A = 64 * 64
    BLOCK_B = 64

    wk = c.white_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.white_piece_squares[2]
    pawn_c = c.white_piece_squares[3]

    bk = c.black_piece_squares[0]

    i = pawn_a - 8
    j = pawn_b - 8
    k = pawn_c - 8

    ppp48_slice = PPP48_IDX[i][j][k]

    if idx_is_empty(ppp48_slice):
        wk = flip_we(wk)
        pawn_a = flip_we(pawn_a)
        pawn_b = flip_we(pawn_b)
        pawn_c = flip_we(pawn_c)
        bk = flip_we(bk)

    i = pawn_a - 8
    j = pawn_b - 8
    k = pawn_c - 8

    ppp48_slice = PPP48_IDX[i][j][k]

    if idx_is_empty(ppp48_slice):
        return NOINDEX

    return ppp48_slice * BLOCK_A + wk * BLOCK_B + bk


class EndgameKey:
    def __init__(self, maxindex: int, slice_n: int, pctoi: Callable[[Request], int]):
        self.maxindex = maxindex
        self.slice_n = slice_n
        self.pctoi = pctoi

EGKEY = {
    "kqk": EndgameKey(MAX_KXK, 1, kxk_pctoindex),
    "krk": EndgameKey(MAX_KXK, 1, kxk_pctoindex),
    "kbk": EndgameKey(MAX_KXK, 1, kxk_pctoindex),
    "knk": EndgameKey(MAX_KXK, 1, kxk_pctoindex),
    "kpk": EndgameKey(MAX_kpk, 24, kpk_pctoindex),

    "kqkq": EndgameKey(MAX_kakb, 1, kakb_pctoindex),
    "kqkr": EndgameKey(MAX_kakb, 1, kakb_pctoindex),
    "kqkb": EndgameKey(MAX_kakb, 1, kakb_pctoindex),
    "kqkn": EndgameKey(MAX_kakb, 1, kakb_pctoindex),

    "krkr": EndgameKey(MAX_kakb, 1, kakb_pctoindex),
    "krkb": EndgameKey(MAX_kakb, 1, kakb_pctoindex),
    "krkn": EndgameKey(MAX_kakb, 1, kakb_pctoindex),

    "kbkb": EndgameKey(MAX_kakb, 1, kakb_pctoindex),
    "kbkn": EndgameKey(MAX_kakb, 1, kakb_pctoindex),

    "knkn": EndgameKey(MAX_kakb, 1, kakb_pctoindex),

    "kqqk": EndgameKey(MAX_kaak, 1, kaak_pctoindex),
    "kqrk": EndgameKey(MAX_kabk, 1, kabk_pctoindex),
    "kqbk": EndgameKey(MAX_kabk, 1, kabk_pctoindex),
    "kqnk": EndgameKey(MAX_kabk, 1, kabk_pctoindex),

    "krrk": EndgameKey(MAX_kaak, 1, kaak_pctoindex),
    "krbk": EndgameKey(MAX_kabk, 1, kabk_pctoindex),
    "krnk": EndgameKey(MAX_kabk, 1, kabk_pctoindex),

    "kbbk": EndgameKey(MAX_kaak, 1, kaak_pctoindex),
    "kbnk": EndgameKey(MAX_kabk, 1, kabk_pctoindex),

    "knnk": EndgameKey(MAX_kaak, 1, kaak_pctoindex),
    "kqkp": EndgameKey(MAX_kakp, 24, kakp_pctoindex),
    "krkp": EndgameKey(MAX_kakp, 24, kakp_pctoindex),
    "kbkp": EndgameKey(MAX_kakp, 24, kakp_pctoindex),
    "knkp": EndgameKey(MAX_kakp, 24, kakp_pctoindex),

    "kqpk": EndgameKey(MAX_kapk, 24, kapk_pctoindex),
    "krpk": EndgameKey(MAX_kapk, 24, kapk_pctoindex),
    "kbpk": EndgameKey(MAX_kapk, 24, kapk_pctoindex),
    "knpk": EndgameKey(MAX_kapk, 24, kapk_pctoindex),

    "kppk": EndgameKey(MAX_kppk, MAX_PPINDEX, kppk_pctoindex),

    "kpkp": EndgameKey(MAX_kpkp, MAX_PpINDEX, kpkp_pctoindex),

    "kppkp": EndgameKey(MAX_kppkp, 24 * MAX_PP48_INDEX, kppkp_pctoindex),

    "kbbkr": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "kbbkb": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "knnkb": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "knnkn": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),

    "kqqqk": EndgameKey(MAX_kaaak, 1, kaaak_pctoindex),
    "kqqrk": EndgameKey(MAX_kaabk, 1, kaabk_pctoindex),
    "kqqbk": EndgameKey(MAX_kaabk, 1, kaabk_pctoindex),
    "kqqnk": EndgameKey(MAX_kaabk, 1, kaabk_pctoindex),
    "kqrrk": EndgameKey(MAX_kabbk, 1, kabbk_pctoindex),
    "kqrbk": EndgameKey(MAX_kabck, 1, kabck_pctoindex),
    "kqrnk": EndgameKey(MAX_kabck, 1, kabck_pctoindex),
    "kqbbk": EndgameKey(MAX_kabbk, 1, kabbk_pctoindex),
    "kqbnk": EndgameKey(MAX_kabck, 1, kabck_pctoindex),
    "kqnnk": EndgameKey(MAX_kabbk, 1, kabbk_pctoindex),
    "krrrk": EndgameKey(MAX_kaaak, 1, kaaak_pctoindex),
    "krrbk": EndgameKey(MAX_kaabk, 1, kaabk_pctoindex),
    "krrnk": EndgameKey(MAX_kaabk, 1, kaabk_pctoindex),
    "krbbk": EndgameKey(MAX_kabbk, 1, kabbk_pctoindex),
    "krbnk": EndgameKey(MAX_kabck, 1, kabck_pctoindex),
    "krnnk": EndgameKey(MAX_kabbk, 1, kabbk_pctoindex),
    "kbbbk": EndgameKey(MAX_kaaak, 1, kaaak_pctoindex),
    "kbbnk": EndgameKey(MAX_kaabk, 1, kaabk_pctoindex),
    "kbnnk": EndgameKey(MAX_kabbk, 1, kabbk_pctoindex),
    "knnnk": EndgameKey(MAX_kaaak, 1, kaaak_pctoindex),
    "kqqkq": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "kqqkr": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "kqqkb": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "kqqkn": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "kqrkq": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqrkr": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqrkb": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqrkn": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqbkq": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqbkr": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqbkb": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqbkn": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqnkq": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqnkr": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqnkb": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqnkn": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "krrkq": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "krrkr": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "krrkb": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "krrkn": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "krbkq": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "krbkr": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "krbkb": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "krbkn": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "krnkq": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "krnkr": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "krnkb": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "krnkn": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kbbkq": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "kbbkn": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "kbnkq": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kbnkr": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kbnkb": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "kbnkn": EndgameKey(MAX_kabkc, 1, kabkc_pctoindex),
    "knnkq": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),
    "knnkr": EndgameKey(MAX_kaakb, 1, kaakb_pctoindex),

    "kqqpk": EndgameKey(MAX_kaapk, 24, kaapk_pctoindex),
    "kqrpk": EndgameKey(MAX_kabpk, 24, kabpk_pctoindex),
    "kqbpk": EndgameKey(MAX_kabpk, 24, kabpk_pctoindex),
    "kqnpk": EndgameKey(MAX_kabpk, 24, kabpk_pctoindex),
    "krrpk": EndgameKey(MAX_kaapk, 24, kaapk_pctoindex),
    "krbpk": EndgameKey(MAX_kabpk, 24, kabpk_pctoindex),
    "krnpk": EndgameKey(MAX_kabpk, 24, kabpk_pctoindex),
    "kbbpk": EndgameKey(MAX_kaapk, 24, kaapk_pctoindex),
    "kbnpk": EndgameKey(MAX_kabpk, 24, kabpk_pctoindex),
    "knnpk": EndgameKey(MAX_kaapk, 24, kaapk_pctoindex),

    "kqppk": EndgameKey(MAX_kappk, MAX_PPINDEX, kappk_pctoindex),
    "krppk": EndgameKey(MAX_kappk, MAX_PPINDEX, kappk_pctoindex),
    "kbppk": EndgameKey(MAX_kappk, MAX_PPINDEX, kappk_pctoindex),
    "knppk": EndgameKey(MAX_kappk, MAX_PPINDEX, kappk_pctoindex),

    "kqpkq": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "kqpkr": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "kqpkb": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "kqpkn": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "krpkq": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "krpkr": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "krpkb": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "krpkn": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "kbpkq": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "kbpkr": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "kbpkb": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "kbpkn": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "knpkq": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "knpkr": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "knpkb": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "knpkn": EndgameKey(MAX_kapkb, 24, kapkb_pctoindex),
    "kppkq": EndgameKey(MAX_kppka, MAX_PPINDEX, kppka_pctoindex),
    "kppkr": EndgameKey(MAX_kppka, MAX_PPINDEX, kppka_pctoindex),
    "kppkb": EndgameKey(MAX_kppka, MAX_PPINDEX, kppka_pctoindex),
    "kppkn": EndgameKey(MAX_kppka, MAX_PPINDEX, kppka_pctoindex),

    "kqqkp": EndgameKey(MAX_kaakp, 24, kaakp_pctoindex),
    "kqrkp": EndgameKey(MAX_kabkp, 24, kabkp_pctoindex),
    "kqbkp": EndgameKey(MAX_kabkp, 24, kabkp_pctoindex),
    "kqnkp": EndgameKey(MAX_kabkp, 24, kabkp_pctoindex),
    "krrkp": EndgameKey(MAX_kaakp, 24, kaakp_pctoindex),
    "krbkp": EndgameKey(MAX_kabkp, 24, kabkp_pctoindex),
    "krnkp": EndgameKey(MAX_kabkp, 24, kabkp_pctoindex),
    "kbbkp": EndgameKey(MAX_kaakp, 24, kaakp_pctoindex),
    "kbnkp": EndgameKey(MAX_kabkp, 24, kabkp_pctoindex),
    "knnkp": EndgameKey(MAX_kaakp, 24, kaakp_pctoindex),

    "kqpkp": EndgameKey(MAX_kapkp, MAX_PpINDEX, kapkp_pctoindex),
    "krpkp": EndgameKey(MAX_kapkp, MAX_PpINDEX, kapkp_pctoindex),
    "kbpkp": EndgameKey(MAX_kapkp, MAX_PpINDEX, kapkp_pctoindex),
    "knpkp": EndgameKey(MAX_kapkp, MAX_PpINDEX, kapkp_pctoindex),

    "kpppk": EndgameKey(MAX_kpppk, MAX_PPP48_INDEX, kpppk_pctoindex),
}


def sortlists(ws: List[int], wp: List[int]) -> Tuple[List[int], List[int]]:
    z = sorted(zip(wp, ws), key=lambda x: x[0], reverse=True)
    wp2, ws2 = zip(*z)
    return list(ws2), list(wp2)

def egtb_block_unpack(side: int, n: int, bp: bytes) -> List[int]:
    return [dtm_unpack(side, i) for i in bp[:n]]

def split_index(i: int) -> Tuple[int, int]:
    return divmod(i, ENTRIES_PER_BLOCK)


tb_DRAW = 0
tb_WMATE = 1
tb_BMATE = 2
tb_FORBID = 3
tb_UNKNOWN = 7
iDRAW = tb_DRAW
iWMATE = tb_WMATE
iBMATE = tb_BMATE
iFORBID = tb_FORBID

iDRAWt = tb_DRAW | 4
iWMATEt = tb_WMATE | 4
iBMATEt = tb_BMATE | 4


def removepiece(ys: List[int], yp: List[int], j: int) -> None:
    del ys[j]
    del yp[j]

def opp(side: int) -> int:
    return 1 if side == 0 else 0

def adjust_up(dist: int) -> int:
    udist = dist
    sw = udist & INFOMASK

    if sw in [iWMATE, iWMATEt, iBMATE, iBMATEt]:
        udist += (1 << PLYSHIFT)

    return udist

def bestx(side: int, a: int, b: int) -> int:
    # 0 = selectfirst
    # 1 = selectlowest
    # 2 = selecthighest
    # 3 = selectsecond
    comparison = [
        # draw, wmate, bmate, forbid
        [0, 3, 0, 0],  # draw
        [0, 1, 0, 0],  # wmate
        [3, 3, 2, 0],  # bmate
        [3, 3, 3, 0],  # forbid
    ]

    xorkey = [0, 3]

    if a == iFORBID:
        return b
    if b == iFORBID:
        return a

    retu = [a, a, b, b]

    if b < a:
        retu[1] = b
        retu[2] = a

    key = comparison[a & 3][b & 3] ^ xorkey[side]
    return retu[key]

def unpackdist(d: int) -> Tuple[int, int]:
    return d >> PLYSHIFT, d & INFOMASK

def dtm_unpack(stm: int, packed: int) -> int:
    p = packed

    if p in [iDRAW, iFORBID]:
        return p

    info = p & 3
    store = p >> 2

    if stm == 0:
        if info == iWMATE:
            moves = store + 1
            plies = moves * 2 - 1
            prefx = info
        elif info == iBMATE:
            moves = store
            plies = moves * 2
            prefx = info
        elif info == iDRAW:
            moves = store + 1 + 63
            plies = moves * 2 - 1
            prefx = iWMATE
        elif info == iFORBID:
            moves = store + 63
            plies = moves * 2
            prefx = iBMATE
        else:
            plies = 0
            prefx = 0

        ret = prefx | (plies << 3)
    else:
        if info == iBMATE:
            moves = store + 1
            plies = moves * 2 - 1
            prefx = info
        elif info == iWMATE:
            moves = store
            plies = moves * 2
            prefx = info
        elif info == iDRAW:
            if store == 63:
                # Exception: no position in the 5-man TBs needs to store 63 for
                # iBMATE. It is then just used to indicate iWMATE.
                store += 1

                moves = store + 63
                plies = moves * 2
                prefx = iWMATE
            else:
                moves = store + 1 + 63
                plies = moves * 2 - 1
                prefx = iBMATE
        elif info == iFORBID:
            moves = store + 63
            plies = moves * 2
            prefx = iWMATE
        else:
            plies = 0
            prefx = 0

        ret = prefx | (plies << 3)

    return ret


class MissingTableError(KeyError):
    """Can not probe position because a required table is missing."""


class TableBlock:
    pcache: List[int]

    def __init__(self, egkey: str, side: int, offset: int, age: int):
        self.egkey = egkey
        self.side = side
        self.offset = offset
        self.age = age


class Request:
    egkey: str
    white_piece_squares: List[int]
    white_piece_types: List[int]
    black_piece_squares: List[int]
    black_piece_types: List[int]
    is_reversed: bool

    def __init__(self, white_squares: List[int], white_types: List[chess.PieceType], black_squares: List[int], black_types: List[chess.PieceType], side: int, epsq: int):
        self.white_squares, self.white_types = sortlists(white_squares, white_types)
        self.black_squares, self.black_types = sortlists(black_squares, black_types)
        self.realside = side
        self.side = side
        self.epsq = epsq


@dataclasses.dataclass
class ZipInfo:
    extraoffset: int
    totalblocks: int
    blockindex: List[int]


class PythonTablebase:
    """Provides access to Gaviota tablebases using pure Python code."""

    def __init__(self) -> None:
        self.available_tables: Dict[str, str] = {}

        self.streams: Dict[str, BinaryIO] = {}
        self.zipinfo: Dict[str, ZipInfo] = {}

        self.block_cache: Dict[Tuple[str, int, int], TableBlock] = {}
        self.block_age = 0

    def add_directory(self, directory: str) -> None:
        """
        Adds *.gtb.cp4* tables from a directory. The relevant files are lazily
        opened when the tablebase is actually probed.
        """
        directory = os.path.abspath(directory)
        if not os.path.isdir(directory):
            raise IOError(f"not a directory: {directory!r}")

        for tbfile in fnmatch.filter(os.listdir(directory), "*.gtb.cp4"):
            self.available_tables[os.path.basename(tbfile).replace(".gtb.cp4", "")] = os.path.join(directory, tbfile)

    def probe_dtm(self, board: chess.Board) -> int:
        """
        Probes for depth to mate information.

        The absolute value is the number of half-moves until forced mate
        (or ``0`` in drawn positions). The value is positive if the
        side to move is winning, otherwise it is negative.

        In the example position, white to move will get mated in 10 half-moves:

        >>> import chess
        >>> import chess.gaviota
        >>>
        >>> with chess.gaviota.open_tablebase("data/gaviota") as tablebase:
        ...     board = chess.Board("8/8/8/8/8/8/8/K2kr3 w - - 0 1")
        ...     print(tablebase.probe_dtm(board))
        ...
        -10

        :raises: :exc:`KeyError` (or specifically
            :exc:`chess.gaviota.MissingTableError`) if the probe fails. Use
            :func:`~chess.gaviota.PythonTablebase.get_dtm()` if you prefer
            to get ``None`` instead of an exception.

            Note that probing a corrupted table file is undefined behavior.
        """
        # Can not probe positions with castling rights.
        if board.castling_rights:
            raise KeyError(f"gaviota tables do not contain positions with castling rights: {board.fen()}")

        # Supports only up to 5 pieces.
        if chess.popcount(board.occupied) > 5:
            raise KeyError(f"gaviota tables support up to 5 pieces, not {chess.popcount(board.occupied)}: {board.fen()}")

        # KvK is a draw.
        if board.occupied == board.kings:
            return 0

        # Prepare the tablebase request.
        white_squares = list(chess.SquareSet(board.occupied_co[chess.WHITE]))
        white_types = [typing.cast(chess.PieceType, board.piece_type_at(sq)) for sq in white_squares]
        black_squares = list(chess.SquareSet(board.occupied_co[chess.BLACK]))
        black_types = [typing.cast(chess.PieceType, board.piece_type_at(sq)) for sq in black_squares]
        side = 0 if (board.turn == chess.WHITE) else 1
        epsq = board.ep_square if board.ep_square else NOSQUARE
        req = Request(white_squares, white_types, black_squares, black_types, side, epsq)

        # Probe.
        dtm = self.egtb_get_dtm(req)
        ply, res = unpackdist(dtm)

        if res == iWMATE:
            # White mates in the stored position.
            if req.realside == 1:
                if req.is_reversed:
                    return ply
                else:
                    return -ply
            else:
                if req.is_reversed:
                    return -ply
                else:
                    return ply
        elif res == iBMATE:
            # Black mates in the stored position.
            if req.realside == 0:
                if req.is_reversed:
                    return ply
                else:
                    return -ply
            else:
                if req.is_reversed:
                    return -ply
                else:
                    return ply
        else:
            # Draw.
            return 0

    def get_dtm(self, board: chess.Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_dtm(board)
        except KeyError:
            return default

    def probe_wdl(self, board: chess.Board) -> int:
        """
        Probes for win/draw/loss information.

        Returns ``1`` if the side to move is winning, ``0`` if it is a draw,
        and ``-1`` if the side to move is losing.

        >>> import chess
        >>> import chess.gaviota
        >>>
        >>> with chess.gaviota.open_tablebase("data/gaviota") as tablebase:
        ...     board = chess.Board("8/4k3/8/B7/8/8/8/4K3 w - - 0 1")
        ...     print(tablebase.probe_wdl(board))
        ...
        0

        :raises: :exc:`KeyError` (or specifically
            :exc:`chess.gaviota.MissingTableError`) if the probe fails. Use
            :func:`~chess.gaviota.PythonTablebase.get_wdl()` if you prefer
            to get ``None`` instead of an exception.

            Note that probing a corrupted table file is undefined behavior.
        """
        dtm = self.probe_dtm(board)

        if dtm == 0:
            if board.is_checkmate():
                return -1
            else:
                return 0
        elif dtm > 0:
            return 1
        else:
            return -1

    def get_wdl(self, board: chess.Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_wdl(board)
        except KeyError:
            return default

    def _setup_tablebase(self, req: Request) -> BinaryIO:
        white_letters = "".join(chess.piece_symbol(i) for i in req.white_types)
        black_letters = "".join(chess.piece_symbol(i) for i in req.black_types)

        if (white_letters + black_letters) in self.available_tables:
            req.is_reversed = False
            req.egkey = white_letters + black_letters
            req.white_piece_squares = req.white_squares
            req.white_piece_types = req.white_types
            req.black_piece_squares = req.black_squares
            req.black_piece_types = req.black_types
        elif (black_letters + white_letters) in self.available_tables:
            req.is_reversed = True
            req.egkey = black_letters + white_letters
            req.white_piece_squares = [flip_ns(s) for s in req.black_squares]
            req.white_piece_types = req.black_types
            req.black_piece_squares = [flip_ns(s) for s in req.white_squares]
            req.black_piece_types = req.white_types

            req.side = opp(req.side)
            if req.epsq != NOSQUARE:
                req.epsq = flip_ns(req.epsq)
        else:
            raise MissingTableError(f"no gaviota table available for: {white_letters.upper()}v{black_letters.upper()}")

        return self._open_tablebase(req)

    def _open_tablebase(self, req: Request) -> BinaryIO:
        stream = self.streams.get(req.egkey)

        if stream is None:
            path = self.available_tables[req.egkey]
            stream = open(path, "rb+")
            self.egtb_loadindexes(req.egkey, stream)
            self.streams[req.egkey] = stream

        return stream

    def close(self) -> None:
        """Closes all loaded tables."""
        self.available_tables.clear()

        self.zipinfo.clear()

        self.block_age = 0
        self.block_cache.clear()

        while self.streams:
            _, stream = self.streams.popitem()
            stream.close()

    def egtb_get_dtm(self, req: Request) -> int:
        dtm = self._tb_probe(req)

        if req.epsq != NOSQUARE:
            capturer_a = 0
            capturer_b = 0
            xed = 0

            # Flip for move generation.
            if req.side == 0:
                xs = list(req.white_piece_squares)
                xp = list(req.white_piece_types)
                ys = list(req.black_piece_squares)
                yp = list(req.black_piece_types)
            else:
                xs = list(req.black_piece_squares)
                xp = list(req.black_piece_types)
                ys = list(req.white_piece_squares)
                yp = list(req.white_piece_types)

            # Captured pawn trick: from ep square to captured.
            xed = req.epsq ^ (1 << 3)

            # Find captured index (j).
            try:
                j = ys.index(xed)
            except ValueError:
                j = -1

            # Try first possible ep capture.
            if 0 == (0x88 & (map88(xed) + 1)):
                capturer_a = xed + 1

            # Try second possible ep capture.
            if 0 == (0x88 & (map88(xed) - 1)):
                capturer_b = xed - 1

            if (j > -1) and (ys[j] == xed):
                # Find capturers (i).
                for i in range(len(xs)):
                    if xp[i] == chess.PAWN and (xs[i] == capturer_a or xs[i] == capturer_b):
                        epscore = iFORBID

                        # Copy position.
                        xs_after = xs[:]
                        ys_after = ys[:]
                        xp_after = xp[:]
                        yp_after = yp[:]

                        # Execute capture.
                        xs_after[i] = req.epsq
                        removepiece(ys_after, yp_after, j)

                        # Flip back.
                        if req.side == 1:
                            xs_after, ys_after = ys_after, xs_after
                            xp_after, yp_after = yp_after, xp_after

                        # Make subrequest.
                        subreq = Request(xs_after, xp_after, ys_after, yp_after, opp(req.side), NOSQUARE)
                        try:
                            epscore = self._tb_probe(subreq)
                            epscore = adjust_up(epscore)

                            # Choose to ep or not.
                            dtm = bestx(req.side, epscore, dtm)
                        except IndexError:
                            break

        return dtm

    def egtb_block_getnumber(self, req: Request, idx: int) -> int:
        maxindex = EGKEY[req.egkey].maxindex

        blocks_per_side = 1 + (maxindex - 1) // ENTRIES_PER_BLOCK
        block_in_side = idx // ENTRIES_PER_BLOCK

        return req.side * blocks_per_side + block_in_side

    def egtb_block_getsize(self, req: Request, idx: int) -> int:
        blocksz = ENTRIES_PER_BLOCK
        maxindex = EGKEY[req.egkey].maxindex
        block = idx // blocksz
        offset = block * blocksz

        if (offset + blocksz) > maxindex:
            return maxindex - offset  # Last block size
        else:
            return blocksz  # Size of a normal block

    def _tb_probe(self, req: Request) -> int:
        stream = self._setup_tablebase(req)
        idx = EGKEY[req.egkey].pctoi(req)
        offset, remainder = split_index(idx)

        t = self.block_cache.get((req.egkey, offset, req.side))

        if t is None:
            t = TableBlock(req.egkey, req.side, offset, self.block_age)

            block = self.egtb_block_getnumber(req, idx)
            n = self.egtb_block_getsize(req, idx)
            z = self.egtb_block_getsize_zipped(req.egkey, block)

            self.egtb_block_park(req.egkey, block, stream)
            buffer_zipped = stream.read(z)

            if buffer_zipped[0] == 0:
                # If flag is zero, plain LZMA is following.
                buffer_zipped = buffer_zipped[2:]
            else:
                # Else LZMA86. Build a fake header.
                DICTIONARY_SIZE = 4096
                POS_STATE_BITS = 2
                NUM_LITERAL_POS_STATE_BITS = 0
                NUM_LITERAL_CONTEXT_BITS = 3
                properties = bytearray(13)
                properties[0] = (POS_STATE_BITS * 5 + NUM_LITERAL_POS_STATE_BITS) * 9 + NUM_LITERAL_CONTEXT_BITS
                for i in range(4):
                    properties[1 + i] = (DICTIONARY_SIZE >> (8 * i)) & 0xFF
                for i in range(8):
                    properties[5 + i] = (n >> (8 * i)) & 0xFF

                # Concatenate the fake header with the true LZMA stream.
                buffer_zipped = properties + buffer_zipped[15:]

            buffer_packed = lzma.LZMADecompressor().decompress(buffer_zipped)

            t.pcache = egtb_block_unpack(req.side, n, buffer_packed)

            # Update LRU block cache.
            self.block_cache[(t.egkey, t.offset, t.side)] = t
            if len(self.block_cache) > 128:
                lru_cache_key = min(self.block_cache, key=lambda cache_key: self.block_cache[cache_key].age)
                del self.block_cache[lru_cache_key]
        else:
            t.age = self.block_age

        self.block_age += 1
        dtm = t.pcache[remainder]

        return dtm

    def egtb_loadindexes(self, egkey: str, stream: BinaryIO) -> ZipInfo:
        zipinfo = self.zipinfo.get(egkey)

        if zipinfo is None:
            # Get reserved bytes, blocksize, offset.
            stream.seek(0)
            HeaderStruct = struct.Struct("<10I")
            header = HeaderStruct.unpack(stream.read(HeaderStruct.size))
            offset = header[8]

            blocks = ((offset - 40) // 4) - 1
            n_idx = blocks + 1

            IndexStruct = struct.Struct("<" + "I" * n_idx)
            p = list(IndexStruct.unpack(stream.read(IndexStruct.size)))

            zipinfo = ZipInfo(extraoffset=0, totalblocks=n_idx, blockindex=p)
            self.zipinfo[egkey] = zipinfo

        return zipinfo

    def egtb_block_getsize_zipped(self, egkey: str, block: int) -> int:
        i = self.zipinfo[egkey].blockindex[block]
        j = self.zipinfo[egkey].blockindex[block + 1]
        return j - i

    def egtb_block_park(self, egkey: str, block: int, stream: BinaryIO) -> int:
        i = self.zipinfo[egkey].blockindex[block]
        i += self.zipinfo[egkey].extraoffset
        stream.seek(i)
        return i

    def __enter__(self) -> PythonTablebase:
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.close()


class NativeTablebase:
    """
    Provides access to Gaviota tablebases via the shared library libgtb.
    Has the same interface as :class:`~chess.gaviota.PythonTablebase`.
    """

    def __init__(self, libgtb: ctypes.CDLL) -> None:
        self.paths: List[str] = []

        self.libgtb = libgtb
        self.libgtb.tb_init.restype = ctypes.c_char_p
        self.libgtb.tb_restart.restype = ctypes.c_char_p
        self.libgtb.tbpaths_getmain.restype = ctypes.c_char_p
        self.libgtb.tb_probe_hard.argtypes = [
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint)
        ]

        if self.libgtb.tb_is_initialized():
            raise RuntimeError("only one gaviota instance can be initialized at a time")

        self._tbcache_restart(1024 * 1024, 50)

    def add_directory(self, directory: str) -> None:
        if not os.path.isdir(directory):
            raise IOError(f"not a directory: {directory!r}")

        self.paths.append(directory)
        self._tb_restart()

    def _tb_restart(self) -> None:
        self.c_paths = (ctypes.c_char_p * len(self.paths))()
        self.c_paths[:] = [path.encode("utf-8") for path in self.paths]

        verbosity = ctypes.c_int(1)
        compression_scheme = ctypes.c_int(4)

        ret = self.libgtb.tb_restart(verbosity, compression_scheme, self.c_paths)
        if ret:
            LOGGER.debug(ret.decode("utf-8"))

        LOGGER.debug("Main path has been set to %r", self.libgtb.tbpaths_getmain().decode("utf-8"))

        av = self.libgtb.tb_availability()
        if av & 1:
            LOGGER.debug("Some 3-piece tables available")
        if av & 2:
            LOGGER.debug("All 3-piece tables complete")
        if av & 4:
            LOGGER.debug("Some 4-piece tables available")
        if av & 8:
            LOGGER.debug("All 4-piece tables complete")
        if av & 16:
            LOGGER.debug("Some 5-piece tables available")
        if av & 32:
            LOGGER.debug("All 5-piece tables complete")

    def _tbcache_restart(self, cache_mem: int, wdl_fraction: int) -> None:
        self.libgtb.tbcache_restart(ctypes.c_size_t(cache_mem), ctypes.c_int(wdl_fraction))

    def probe_dtm(self, board: chess.Board) -> int:
        return self._probe_hard(board)

    def probe_wdl(self, board: chess.Board) -> int:
        return self._probe_hard(board, wdl_only=True)

    def get_dtm(self, board: chess.Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_dtm(board)
        except KeyError:
            return default

    def get_wdl(self, board: chess.Board, default: Optional[int] = None) -> Optional[int]:
        try:
            return self.probe_wdl(board)
        except KeyError:
            return default

    def _probe_hard(self, board: chess.Board, wdl_only: bool = False) -> int:
        if board.is_insufficient_material():
            return 0

        if board.castling_rights:
            raise KeyError(f"gaviota tables do not contain positions with castling rights: {board.fen()}")

        if chess.popcount(board.occupied) > 5:
            raise KeyError(f"gaviota tables support up to 5 pieces, not {chess.popcount(board.occupied)}: {board.fen()}")

        stm = ctypes.c_uint(0 if board.turn == chess.WHITE else 1)
        ep_square = ctypes.c_uint(board.ep_square if board.ep_square else 64)
        castling = ctypes.c_uint(0)

        c_ws = (ctypes.c_uint * 17)()
        c_wp = (ctypes.c_ubyte * 17)()

        i = -1
        for i, square in enumerate(chess.SquareSet(board.occupied_co[chess.WHITE])):
            c_ws[i] = square
            c_wp[i] = typing.cast(chess.PieceType, board.piece_type_at(square))

        c_ws[i + 1] = 64
        c_wp[i + 1] = 0

        c_bs = (ctypes.c_uint * 17)()
        c_bp = (ctypes.c_ubyte * 17)()

        i = -1
        for i, square in enumerate(chess.SquareSet(board.occupied_co[chess.BLACK])):
            c_bs[i] = square
            c_bp[i] = typing.cast(chess.PieceType, board.piece_type_at(square))

        c_bs[i + 1] = 64
        c_bp[i + 1] = 0

        # Do a hard probe.
        info = ctypes.c_uint()
        pliestomate = ctypes.c_uint()
        if not wdl_only:
            ret = self.libgtb.tb_probe_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info), ctypes.byref(pliestomate))
            dtm = int(pliestomate.value)
        else:
            ret = self.libgtb.tb_probe_WDL_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info))
            dtm = 1

        # Probe forbidden.
        if info.value == 3:
            raise MissingTableError(f"gaviota table for {board.fen()} not available")

        # Draw.
        if ret and info.value == 0:
            return 0

        # White mates.
        if ret and info.value == 1:
            return dtm if board.turn == chess.WHITE else -dtm

        # Black mates.
        if ret and info.value == 2:
            return dtm if board.turn == chess.BLACK else -dtm

        raise KeyError(f"gaviota probe failed for {board.fen()}")

    def close(self) -> None:
        self.paths = []

        if self.libgtb.tb_is_initialized():
            self.libgtb.tbcache_done()
            self.libgtb.tb_done()

    def __enter__(self) -> NativeTablebase:
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.close()


def open_tablebase_native(directory: str, *, libgtb: Optional[str] = None, LibraryLoader: ctypes.LibraryLoader[ctypes.CDLL] = ctypes.cdll) -> NativeTablebase:
    """
    Opens a collection of tables for probing using libgtb.

    In most cases :func:`~chess.gaviota.open_tablebase()` should be used.
    Use this function only if you do not want to downgrade to pure Python
    tablebase probing.

    :raises: :exc:`RuntimeError` or :exc:`OSError` when libgtb can not be used.
    """
    libgtb = libgtb or ctypes.util.find_library("gtb") or "libgtb.so.1.0.1"
    tables = NativeTablebase(LibraryLoader.LoadLibrary(libgtb))
    tables.add_directory(directory)
    return tables


def open_tablebase(directory: str, *, libgtb: Optional[str] = None, LibraryLoader: ctypes.LibraryLoader[ctypes.CDLL] = ctypes.cdll) -> Union[NativeTablebase, PythonTablebase]:
    """
    Opens a collection of tables for probing.

    First native access via the shared library libgtb is tried. You can
    optionally provide a specific library name or a library loader.
    The shared library has global state and caches, so only one instance can
    be open at a time.

    Second, pure Python probing code is tried.
    """
    try:
        if LibraryLoader:
            return open_tablebase_native(directory, libgtb=libgtb, LibraryLoader=LibraryLoader)
    except (OSError, RuntimeError) as err:
        LOGGER.info("Falling back to pure Python tablebase: %r", err)

    tables = PythonTablebase()
    tables.add_directory(directory)
    return tables
