# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2015 Jean-Noël Avila <jn.avila@free.fr>
# Copyright (C) 2015 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
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


import ctypes
import ctypes.util
import os.path
import logging
import chess
import os
import struct

try:
    from enum import Enum
except ImportError:
    from enum34 import Enum

try:
    import lzma
except ImportError:
    from backports import lzma

try:
    import backport_collections as collections
except ImportError:
    import collections


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

ENTRIES_PER_BLOCK = 16 * 1024;

EGTB_MAXBLOCKSIZE = 65536

MateResult = Enum("MateResult", "WhiteToMate BlackToMate Draw Unknown")

class ProbeResultType(object):
    def __init__(self):
        self.found = False
        self.stm = MateResult.Unknown
        self.error = ""
        self.ply = 0
        self.dtm = 0


class currentConf(object):
    def __init__(self):
        self.whitePieceTypes = None
        self.blackPieceTypes = None
        self.whitePieceSquares = []
        self.blackPieceSquares = []
        self.Reversed = False

def map24_b(s):
    s = s - 8
    return ((s & 3) + s) >> 1

def in_queenside(x):
    return (x & (1 << 2)) == 0

def init_ppp48_idx():
    MAX_I = 48
    MAX_J = 48
    MAX_K = 48
    ppp48_idx = [[[-1]* MAX_I for j in range(MAX_J)] for k in range(MAX_K)]
    # default is noindex
    ppp48_sq_x = [NOSQUARE] * MAX_PPP48_INDEX
    ppp48_sq_y = [NOSQUARE] * MAX_PPP48_INDEX
    ppp48_sq_z = [NOSQUARE] * MAX_PPP48_INDEX
    idx = 0
    for x in range(48):
        for y in range(x+1,48):
            for z in range(y+1,48):
                a = ITOSQ[x]
                b = ITOSQ[y]
                c = ITOSQ[z]
                if (not in_queenside(b)) or (not in_queenside(c)):
                    continue

                i = a - 8
                j = b - 8
                k = c - 8

                if (IDX_is_empty(ppp48_idx[i][j][k])):
                    ppp48_idx[i][j][k] = idx
                    ppp48_idx[i][k][j] = idx
                    ppp48_idx[j][i][k] = idx
                    ppp48_idx[j][k][i] = idx
                    ppp48_idx[k][i][j] = idx
                    ppp48_idx[k][j][i] = idx
                    ppp48_sq_x[idx] = i
                    ppp48_sq_y[idx] = j
                    ppp48_sq_z[idx] = k
                    idx = idx + 1
    return ppp48_idx, ppp48_sq_x,ppp48_sq_y, ppp48_sq_z

def kapkb_pctoindex(c):
    BLOCK_A = 64 * 64 * 64 * 64
    BLOCK_B = 64 * 64 * 64
    BLOCK_C = 64 * 64
    BLOCK_D = 64

    pawn = c.whitePieceSquares[2]
    wa = c.whitePieceSquares[1]
    wk = c.whitePieceSquares[0]
    bk = c.blackPieceSquares[0]
    ba = c.blackPieceSquares[1]

    if (not(chess.A2 <= pawn and pawn < chess.A8)):
        return NOINDEX

    if ((pawn & 7) > 3):
        # column is more than 3. e.g. = e,f,g, or h
        pawn = flipWE(pawn)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)
        ba = flipWE(ba)

    sq = pawn
    sq ^= 56 # flipNS
    sq -= 8  # down one row
    pslice = ((sq + (sq & 3)) >> 1)

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + ba;

def kabpk_pctoindex(c):
    BLOCK_A = 64 * 64 * 64 * 64
    BLOCK_B = 64 * 64 * 64
    BLOCK_C = 64 * 64
    BLOCK_D = 64;

    wk = c.whitePieceSquares[0]
    wa = c.whitePieceSquares[1]
    wb = c.whitePieceSquares[2]
    pawn = c.whitePieceSquares[3]
    bk = c.blackPieceSquares[0]

    if ((pawn & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h */
        pawn = flipWE(pawn)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)
        wb = flipWE(wb)

    pslice = wsq_to_pidx24(pawn)

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + wb


def kabkp_pctoindex(c):
    BLOCK_A = 64 * 64 * 64 * 64
    BLOCK_B = 64 * 64 * 64
    BLOCK_C = 64 * 64
    BLOCK_D = 64

    pawn = c.blackPieceSquares[1]
    wa = c.whitePieceSquares[1]
    wk = c.whitePieceSquares[0]
    bk = c.blackPieceSquares[0]
    wb = c.whitePieceSquares[2]

    if (not (chess.A2 <= pawn and pawn < chess.A8)):
                return NOINDEX

    if ((pawn & 7) > 3):
        # column is more than 3. e.g. = e,f,g, or h
        pawn = flipWE(pawn)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)
        wb = flipWE(wb)

    sq = pawn
    # sq ^= 070;
    # do not flipNS
    sq -= 8;   # down one row
    pslice = ((sq + (sq & 3)) >> 1)

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + wb

def kaapk_pctoindex(c):
    BLOCK_C = MAX_AAINDEX
    BLOCK_B = 64 * BLOCK_C
    BLOCK_A = 64 * BLOCK_B

    wk = c.whitePieceSquares[0]
    wa = c.whitePieceSquares[1]
    wa2 = c.whitePieceSquares[2]
    pawn = c.whitePieceSquares[3]
    bk = c.blackPieceSquares[0]

    if ((pawn & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h */
        pawn = flipWE(pawn)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)
        wa2 = flipWE(wa2)

    pslice = wsq_to_pidx24(pawn)

    aa_combo = aaidx[wa][wa2]

    if (IDX_is_empty(aa_combo)):
                return NOINDEX

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + aa_combo

def kaakp_pctoindex(c):
    BLOCK_C = MAX_AAINDEX
    BLOCK_B = 64 * BLOCK_C
    BLOCK_A = 64 * BLOCK_B

    wk = c.whitePieceSquares[0]
    wa = c.whitePieceSquares[1]
    wa2 = c.whitePieceSquares[2]
    bk = c.blackPieceSquares[0]
    pawn = c.blackPieceSquares[1]

    if ((pawn & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        pawn = flipWE(pawn)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)
        wa2 = flipWE(wa2)

    pawn = flipNS(pawn)
    pslice = wsq_to_pidx24(pawn)

    aa_combo = aaidx[wa][wa2]

    if (IDX_is_empty(aa_combo)):
                return NOINDEX

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + aa_combo

def kapkp_pctoindex(c):
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    wk = c.whitePieceSquares[0]
    wa = c.whitePieceSquares[1]
    pawn_a = c.whitePieceSquares[2]
    bk = c.blackPieceSquares[0]
    pawn_b = c.blackPieceSquares[1]

    anchor = pawn_a
    loosen = pawn_b

    if ((anchor & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        anchor = flipWE(anchor)
        loosen = flipWE(loosen)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)

    m = wsq_to_pidx24(anchor)
    n = loosen - 8
    pp_slice = m * 48 + n

    if (IDX_is_empty(pp_slice)):
                return NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa

def kappk_pctoindex(c):
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    wk = c.whitePieceSquares[0]
    wa = c.whitePieceSquares[1]
    pawn_a = c.whitePieceSquares[2]
    pawn_b = c.whitePieceSquares[3]
    bk = c.blackPieceSquares[0]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if ((anchor & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        anchor = flipWE(anchor)
        loosen = flipWE(loosen)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)

    pp_slice = ppidx[i][j]

    if (IDX_is_empty(pp_slice)):
                return NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa

def kppka_pctoindex(c):
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    wk = c.whitePieceSquares[0]
    pawn_a = c.whitePieceSquares[1]
    pawn_b = c.whitePieceSquares[2]
    bk = c.blackPieceSquares[0]
    ba = c.blackPieceSquares[1]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if ((anchor & 7) > 3):
        # column is more than 3. e.g. = e,f,g, or h
        anchor = flipWE(anchor)
        loosen = flipWE(loosen)
        wk = flipWE(wk)
        bk = flipWE(bk)
        ba = flipWE(ba)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)

    pp_slice = ppidx[i][j]

    if (IDX_is_empty(pp_slice)):
                return NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + ba

def kabck_pctoindex(c):
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    ft = flipt[c.blackPieceSquares[0]][c.whitePieceSquares[0]]

    ws = list(c.whitePieceSquares[:N_WHITE])
    bs = list(c.blackPieceSquares[:N_BLACK])

    if ((ft & WE_FLAG) != 0):
        ws = [flipWE(i) for i in ws]
        bs = [flipWE(i) for i in bs]

    if ((ft & NS_FLAG) != 0):
        ws = [flipNS(i) for i in ws]
        bs = [flipNS(i) for i in bs]

    if ((ft & NW_SE_FLAG) != 0):
        ws = [flipNW_SE(i) for i in ws]
        bs = [flipNW_SE(i) for i in bs]

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]

    if (IDX_is_empty(ki)):
                return NOINDEX
    return ki * BLOCK_A + ws[1] * BLOCK_B + ws[2] * BLOCK_C + ws[3]

def kabbk_pctoindex(c):
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * MAX_AAINDEX

    ft = flipt[c.blackPieceSquares[0]][c.whitePieceSquares[0]]

    ws = list(c.whitePieceSquares[:N_WHITE])
    bs = list(c.blackPieceSquares[:N_BLACK])

    if ((ft & WE_FLAG) != 0):
        ws = [flipWE(i) for i in ws]
        bs = [flipWE(i) for i in bs]

    if ((ft & NS_FLAG) != 0):
        ws = [flipNS(i) for i in ws]
        bs = [flipNS(i) for i in bs]

    if ((ft & NW_SE_FLAG) != 0):
        ws = [flipNW_SE(i) for i in ws]
        bs = [flipNW_SE(i) for i in bs]

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]
    ai = aaidx[ws[2]][ws[3]]

    if (IDX_is_empty(ki) or IDX_is_empty(ai)):
       return NOINDEX
    return ki * BLOCK_Ax + ai * BLOCK_Bx + ws[1]

def kaabk_pctoindex(c):
    N_WHITE = 4;
    N_BLACK = 1;
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * MAX_AAINDEX

    ft = flipt[c.blackPieceSquares[0]][c.whitePieceSquares[0]]

    ws = list(c.whitePieceSquares[:N_WHITE])
    bs = list(c.blackPieceSquares[:N_BLACK])

    if ((ft & WE_FLAG) != 0):
        ws = [flipWE(i) for i in ws]
        bs = [flipWE(i) for i in bs]

    if ((ft & NS_FLAG) != 0):
        ws = [flipNS(i) for i in ws]
        bs = [flipNS(i) for i in bs]

    if ((ft & NW_SE_FLAG) != 0):
        ws = [flipNW_SE(i) for i in ws]
        bs = [flipNW_SE(i) for i in bs]

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]
    ai = aaidx[ws[1]][ws[2]]

    if (IDX_is_empty(ki) or IDX_is_empty(ai)):
                return NOINDEX
    return ki * BLOCK_Ax + ai * BLOCK_Bx + ws[3]

def init_pp48_idx():
    # returns pp48_idx[][], pp48_sq_x[], pp48_sq_y[]
    MAX_I = 48;
    MAX_J = 48;
    idx = 0

    # default is noindex
    pp48_idx = [[-1]*MAX_J for i in range(MAX_I)]
    pp48_sq_x = [NOSQUARE] * MAX_PP48_INDEX
    pp48_sq_y = [NOSQUARE] * MAX_PP48_INDEX

    idx = 0;
    for a in range(chess.H7, chess.A2-1, -1):
        for b in range(a - 1, chess.A2 - 1, -1):
            i = flipWE(flipNS(a)) - 8
            j = flipWE(flipNS(b)) - 8

            if (IDX_is_empty(pp48_idx[i][j])):
                pp48_idx[i][j] = idx
                pp48_idx[j][i] = idx
                pp48_sq_x[idx] = i
                pp48_sq_y[idx] = j
                idx+=1
    return pp48_idx, pp48_sq_x, pp48_sq_y, idx

def kaaak_pctoindex(c):
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_Ax = MAX_AAAINDEX

    ws = list(c.whitePieceSquares[:N_WHITE])
    bs = list(c.blackPieceSquares[:N_BLACK])

    ft = flipt[c.blackPieceSquares[0]][c.whitePieceSquares[0]]

    if ((ft & WE_FLAG) != 0):
        ws = [flipWE(i) for i in ws]
        bs = [flipWE(i) for i in bs]

    if ((ft & NS_FLAG) != 0):
        ws = [flipNS(i) for i in ws]
        bs = [flipNS(i) for i in bs]

    if ((ft & NW_SE_FLAG) != 0):
        ws = [flipNW_SE(i) for i in ws]
        bs = [flipNW_SE(i) for i in bs]

    if (ws[2] < ws[1]):
        tmp = ws[1]
        ws[1] = ws[2]
        ws[2] = tmp
    if (ws[3] < ws[2]):
        tmp = ws[2]
        ws[2] = ws[3]
        ws[3] = tmp
    if (ws[2] < ws[1]):
        tmp = ws[1]
        ws[1] = ws[2]
        ws[2] = tmp

    ki = kkidx[bs[0]][ws[0]]

    if (ws[1] == ws[2] or ws[1] == ws[3] or ws[2] == ws[3]):
                return NOINDEX

    ai = aaa_getsubi(ws[1], ws[2], ws[3])

    if (IDX_is_empty(ki) or IDX_is_empty(ai)):
                return NOINDEX
    return ki * BLOCK_Ax + ai

def aaa_getsubi(x, y, z):
    bse = aaa_base[z];
    calc_idx = x + (y - 1) * y / 2 + bse
    return int(calc_idx)

def init_aaa():
    # getting aaa_base
    comb = [ a * (a - 1) / 2 for a in range(64)];
    comb[0] = 0;

    accum = 0;
    aaa_base= [0]*64
    for a in range(64 - 1):
        accum = accum + comb[a]
        aaa_base[a + 1] = accum
    # end getting aaa_base

    # initialize aaa_xyz [][]
    aaa_xyz = [[-1] *3 for idx in range(MAX_AAAINDEX)]

    idx = 0;
    for z in range(64):
        for y in range(z):
             for x  in range(y):
                aaa_xyz[idx][0] = x
                aaa_xyz[idx][1] = y
                aaa_xyz[idx][2] = z
                idx+=1
    return aaa_base, aaa_xyz

def kppkp_pctoindex(c):
    BLOCK_Ax = MAX_PP48_INDEX * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    wk = c.whitePieceSquares[0]
    pawn_a = c.whitePieceSquares[1]
    pawn_b = c.whitePieceSquares[2]
    bk = c.blackPieceSquares[0]
    pawn_c = c.blackPieceSquares[1]

    if ((pawn_c & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        wk = flipWE(wk)
        pawn_a = flipWE(pawn_a)
        pawn_b = flipWE(pawn_b)
        bk = flipWE(bk)
        pawn_c = flipWE(pawn_c)

    i = flipWE(flipNS(pawn_a)) - 8
    j = flipWE(flipNS(pawn_b)) - 8
    k = map24_b(pawn_c) # black pawn, so low indexes mean more advanced 0 == A2

    pp48_slice = pp48_idx[i][j]

    if (IDX_is_empty(pp48_slice)):
                return NOINDEX

    return k * BLOCK_Ax + pp48_slice * BLOCK_Bx + wk * BLOCK_Cx + bk

def kaakb_pctoindex(c):
    N_WHITE = 3
    N_BLACK = 2
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * MAX_AAINDEX

    ft = flipt[c.blackPieceSquares[0]][c.whitePieceSquares[0]]

    ws = list(c.whitePieceSquares[:N_WHITE])
    bs = list(c.blackPieceSquares[:N_BLACK])

    if ((ft & WE_FLAG) != 0):
        ws = [flipWE(i) for i in ws]
        bs = [flipWE(i) for i in bs]

    if ((ft & NS_FLAG) != 0):
        ws = [flipNS(i) for i in ws]
        bs = [flipNS(i) for i in bs]

    if ((ft & NW_SE_FLAG) != 0):
        ws = [flipNW_SE(i) for i in ws]
        bs = [flipNW_SE(i) for i in bs]

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]
    ai = aaidx[ws[1]][ws[2]]

    if (IDX_is_empty(ki) or IDX_is_empty(ai)):
                return NOINDEX
    return ki * BLOCK_Ax + ai * BLOCK_Bx + bs[1]

def kabkc_pctoindex(c):
    N_WHITE = 3
    N_BLACK = 2

    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    ft = flipt[c.blackPieceSquares[0]][c.whitePieceSquares[0]]

    ws = list(c.whitePieceSquares[:N_WHITE])
    bs = list(c.blackPieceSquares[:N_BLACK])

    if ((ft & WE_FLAG) != 0):
        ws = [flipWE(i) for i in ws]
        bs = [flipWE(i) for i in bs]

    if ((ft & NS_FLAG) != 0):
        ws = [flipNS(i) for i in ws]
        bs = [flipNS(i) for i in bs]

    if ((ft & NW_SE_FLAG) != 0):
        ws = [flipNW_SE(i) for i in ws]
        bs = [flipNW_SE(i) for i in bs]

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]

    if (IDX_is_empty(ki)):
                return NOINDEX
    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + ws[2] * BLOCK_Cx + bs[1]

def kpkp_pctoindex(c):
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    wk = c.whitePieceSquares[0]
    bk = c.blackPieceSquares[0]
    pawn_a = c.whitePieceSquares[1];
    pawn_b = c.blackPieceSquares[1];
    #pp_putanchorfirst (pawn_a, pawn_b, &anchor, &loosen);
    anchor = pawn_a;
    loosen = pawn_b;

    if ((anchor & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        anchor = flipWE(anchor)
        loosen = flipWE(loosen)
        wk = flipWE(wk)
        bk = flipWE(bk)

    m = wsq_to_pidx24(anchor)
    n = loosen - 8

    pp_slice = m * 48 + n

    if (IDX_is_empty(pp_slice)):
                return NOINDEX

    return (pp_slice * BLOCK_Ax + wk * BLOCK_Bx + bk)

def pp_putanchorfirst(a, b):
    row_b = b & 56;
    row_a = a & 56;

    # default
    anchor = a;
    loosen = b;
    if (row_b > row_a):
        anchor = b;
        loosen = a;
    elif (row_b == row_a):
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

            if (hi_b > hi_a):
                anchor = b
                loosen = a

            if (hi_b < hi_a):
                anchor = a
                loosen = b

            if (hi_b == hi_a):
                if (a < b):
                    anchor = a
                    loosen = b
                else:
                    anchor = b
                    loosen = a

    return anchor, loosen

def wsq_to_pidx24(pawn):
    sq = pawn
    # input can be only queen side, pawn valid
    sq ^= 56 # flipNS
    sq -= 8   # down one row
    idx24 = (sq + (sq & 3)) >> 1
    return idx24

def wsq_to_pidx48(pawn):
    sq = pawn
    sq ^= 56; # flipNS
    sq -= 8;   # down one row
    idx48 = sq;
    return idx48

def kppk_pctoindex(c):
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64
    wk = c.whitePieceSquares[0]
    pawn_a = c.whitePieceSquares[1]
    pawn_b = c.whitePieceSquares[2]
    bk = c.blackPieceSquares[0]

    anchor, loosen = pp_putanchorfirst(pawn_a, pawn_b)

    if ((anchor & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        anchor = flipWE(anchor)
        loosen = flipWE(loosen)
        wk = flipWE(wk)
        bk = flipWE(bk)

    i = wsq_to_pidx24(anchor)
    j = wsq_to_pidx48(loosen)

    pp_slice = ppidx[i][j]

    if (IDX_is_empty(pp_slice)):
                return NOINDEX

    return pp_slice * BLOCK_Ax + wk * BLOCK_Bx + bk

def kapk_pctoindex(c):
    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    pawn = c.whitePieceSquares[2]
    wa = c.whitePieceSquares[1]
    wk = c.whitePieceSquares[0]
    bk = c.blackPieceSquares[0]

    if (not (chess.A2 <= pawn and pawn < chess.A8)):
                return NOINDEX

    if ((pawn & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        pawn = flipWE(pawn)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)

    sq = pawn
    sq ^= 56 # flipNS
    sq -= 8   # down one row
    pslice = ((sq + (sq & 3)) >> 1)

    return pslice * BLOCK_Ax + wk * BLOCK_Bx + bk * BLOCK_Cx + wa

def kabk_pctoindex(c):
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    ft = flip_type(c.blackPieceSquares[0], c.whitePieceSquares[0]);

    ws = list(c.whitePieceSquares)
    bs = list(c.blackPieceSquares)

    if ((ft & 1) != 0):
        ws = [flipWE(b) for b in ws]
        bs = [flipWE(b) for b in bs]

    if ((ft & 2) != 0):
        ws = [flipNS(b) for b in ws]
        bs = [flipNS(b) for b in bs]

    if ((ft & 4) != 0):
        ws = [flipNW_SE(b) for b in ws]
        bs = [flipNW_SE(b) for b in bs]

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]

    if (IDX_is_empty(ki)):
                return NOINDEX
    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + ws[2]

def kakp_pctoindex(c):
    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    pawn = c.blackPieceSquares[1]
    wa = c.whitePieceSquares[1]
    wk = c.whitePieceSquares[0]
    bk = c.blackPieceSquares[0]

    if (not (chess.A2 <= pawn and pawn < chess.A8)):
                return NOINDEX

    if ((pawn & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        pawn = flipWE(pawn)
        wk = flipWE(wk)
        bk = flipWE(bk)
        wa = flipWE(wa)

    sq = pawn;
    #sq ^= 070;
    # flipNS
    sq -= 8   # down one row
    pslice = ((sq + (sq & 3)) >> 1)

    return pslice * BLOCK_Ax + wk * BLOCK_Bx + bk * BLOCK_Cx + wa

def init_aaidx():
    # modifies aabase[], aaidx[][]
    # default is noindex
    aaidx = [[-1]*64 for y in range(64)]
    aabase = [0]*MAX_AAINDEX

    idx = 0
    for x in range(64):
        for y in range(x + 1, 64):

            if (IDX_is_empty(aaidx[x][y])):
                #still empty
                aaidx[x][y] = idx
                aaidx[y][x] = idx
                aabase[idx] = x
                idx+=1
    return aabase, aaidx

def kaak_pctoindex(c):
    N_WHITE = 3
    N_BLACK = 1
    BLOCK_Ax = MAX_AAINDEX

    ft = flipt[c.blackPieceSquares[0]][c.whitePieceSquares[0]]

    ws = list(c.whitePieceSquares[:N_WHITE])
    bs = list(c.blackPieceSquares[:N_BLACK])

    if ((ft & WE_FLAG) != 0):
        ws = [flipWE(i) for i in ws]
        bs = [flipWE(i) for i in bs]

    if ((ft & NS_FLAG) != 0):
        ws = [flipNS(i) for i in ws]
        bs = [flipNS(i) for i in bs]

    if ((ft & NW_SE_FLAG) != 0):
        ws = [flipNW_SE(i) for i in ws]
        bs = [flipNW_SE(i) for i in bs]

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]
    ai = aaidx[ws[1]][ws[2]]

    if (IDX_is_empty(ki) or IDX_is_empty(ai)):
                return NOINDEX
    return ki * BLOCK_Ax + ai

def kakb_pctoindex(c):
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    ft = flipt[c.blackPieceSquares[0]][c.whitePieceSquares[0]]

    ws = list(c.whitePieceSquares)
    bs = list(c.blackPieceSquares)

    if ((ft & 1) != 0):
        ws[0] = flipWE(ws[0])
        ws[1] = flipWE(ws[1])
        bs[0] = flipWE(bs[0])
        bs[1] = flipWE(bs[1])

    if ((ft & 2) != 0):
        ws[0] = flipNS(ws[0])
        ws[1] = flipNS(ws[1])
        bs[0] = flipNS(bs[0])
        bs[1] = flipNS(bs[1])

    if ((ft & 4) != 0):
        ws[0] = flipNW_SE(ws[0])
        ws[1] = flipNW_SE(ws[1])
        bs[0] = flipNW_SE(bs[0])
        bs[1] = flipNW_SE(bs[1])

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]

    if (IDX_is_empty(ki)):
                return NOINDEX

    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + bs[1]

def kpk_pctoindex(c):
    BLOCK_A = 64 * 64
    BLOCK_B = 64

    pawn = c.whitePieceSquares[1]
    wk = c.whitePieceSquares[0]
    bk = c.blackPieceSquares[0]

    if ( not (chess.A2 <= pawn and pawn < chess.A8)):
                return NOINDEX

    if ((pawn & 7) > 3):
        #column is more than 3. e.g. = e,f,g, or h
        pawn = flipWE(pawn)
        wk = flipWE(wk)
        bk = flipWE(bk)

    sq = pawn
    sq ^= 56 # flipNS
    sq -= 8  # down one row
    pslice = ((sq + (sq & 3)) >> 1)

    res = pslice * BLOCK_A + wk * BLOCK_B + bk
    return res

def kpppk_pctoindex(c):
    BLOCK_A = 64 * 64
    BLOCK_B = 64

    wk = c.whitePieceSquares[0]
    pawn_a = c.whitePieceSquares[1]
    pawn_b = c.whitePieceSquares[2]
    pawn_c = c.whitePieceSquares[3]

    bk = c.blackPieceSquares[0]

    i = pawn_a - 8
    j = pawn_b - 8
    k = pawn_c - 8

    ppp48_slice = ppp48_idx[i][j][k]

    if (IDX_is_empty(ppp48_slice)):
        wk = flipWE(wk)
        pawn_a = flipWE(pawn_a)
        pawn_b = flipWE(pawn_b)
        pawn_c = flipWE(pawn_c)
        bk = flipWE(bk)

    i = pawn_a - 8
    j = pawn_b - 8
    k = pawn_c - 8

    ppp48_slice = ppp48_idx[i][j][k]

    if (IDX_is_empty(ppp48_slice)):
        return NOINDEX

    return ppp48_slice * BLOCK_A + wk * BLOCK_B + bk

def init_flipt():
    return [[flip_type(j,i) for i in range(64)] for j in range(64)]


def init_ppidx():
    # returns ppidx[][], pp_hi24[], pp_lo48[]
    # default is noindex
    ppidx = [[-1] *48 for i in range(24)]
    pp_hi24 = [-1] * MAX_PPINDEX
    pp_lo48 = [-1] * MAX_PPINDEX

    idx = 0;
    for a in range(chess.H7,chess.A2-1,-1):
        if ((a & 7) < 4): # square in the queen side */:
            continue
        for b in range(a - 1, chess.A2 - 1, -1):
            anchor = 0
            loosen = 0

            anchor, loosen = pp_putanchorfirst(a, b)

            if ((anchor & 7) > 3):
                #square in the king side
                anchor = flipWE(anchor)
                loosen = flipWE(loosen)

            i = wsq_to_pidx24(anchor)
            j = wsq_to_pidx48(loosen)

            if (IDX_is_empty(ppidx[i][j])):
                ppidx[i][j] = idx
                pp_hi24[idx] = i
                pp_lo48[idx] = j
                idx+=1
    return ppidx, pp_hi24, pp_lo48, idx

def list_sq_flipNS(s):
    return [ i ^ 56 for i in s]

def sortlists(ws, wp):
    # input is sorted
    z = sorted(zip(wp, ws), key=lambda x : x[0], reverse=True)
    wp2, ws2 = zip(*z)
    return list(ws2), list(wp2)

class ZIPINFO:
    extraoffset = 0
    totalblocks = 0
    blockindex = []

# keep: keys are appended
Zipinfo = { }

def egtb_loadindexes(currentFilename, currentStream):
    # Get Reserved bytes, blocksize, offset
    currentStream.seek(0)
    HeaderStruct=struct.Struct("<10I")
    Header = HeaderStruct.unpack(currentStream.read(HeaderStruct.size))

    #blocksize = Header[2]
    #tailblocksize1 = Header[4]
    #tailblocksize2 = Header[6]
    offset = Header[8]

    blocks = int((offset - 40) / 4) - 1
    n_idx = blocks + 1

    # Input of Indexes
    indexStruct=struct.Struct("<" + "I"*n_idx)
    p=indexStruct.unpack(currentStream.read(indexStruct.size))

    if (not currentFilename in Zipinfo):
        Zipinfo[currentFilename] = ZIPINFO()

    Zipinfo[currentFilename].extraoffset = 0
    Zipinfo[currentFilename].totalblocks = n_idx
    Zipinfo[currentFilename].blockindex = p

    return True

def egtb_block_getsize_zipped(currentFilename, block):
    i = Zipinfo[currentFilename].blockindex[block]
    j = Zipinfo[currentFilename].blockindex[block + 1]
    return j - i

def egtb_block_park(currentFilename,block, currentStream):
    i = Zipinfo[currentFilename].blockindex[block]
    i += Zipinfo[currentFilename].extraoffset
    currentStream.seek(i)
    return i


def egtb_block_unpack(side, n, bp):
    try:
        return [dtm_unpack(side, i) for i in bp[:n]]
    except:
        return [dtm_unpack(side, ord(i)) for i in bp[:n]]


def split_index(i):
    return divmod(i, ENTRIES_PER_BLOCK)

class TableBlock:
    def __init__(self, currentFilename, stm, o,  age):
        self.key = currentFilename
        self.side = stm
        self.offset = o
        self.age = age
        self.pcache = []


blockCache = {}

def map88(x):
        return x + (x & 56)

def unmap88(x):
        return x + (x & 7) >> 1

def removepiece(ys, yp, j):
    del ys[j]
    del yp[j]
    return ys,  yp

LZMA_PROPS_SIZE = 5
LZMA86_SIZE_OFFSET = (1 + LZMA_PROPS_SIZE)
LZMA86_HEADER_SIZE = (LZMA86_SIZE_OFFSET + 8)

def Opp(side):
    if (side == 0):
        return 1
    return 0

def adjust_up(dist):
    udist = dist
    sw = (udist & INFOMASK)

    if ((sw == iWMATE) or (sw == iWMATEt) or (sw == iBMATE) or (sw == iBMATEt)):
        udist += (1 << PLYSHIFT)

    return udist


def bestx(side, a, b):
    comparison = [    #draw, wmate, bmate, forbid
                                [0,         3,         0,        0],        # draw
                                [0,         1,         0,        0],        # wmate
                                [3,         3,         2,        0],        # bmate
                                [3,         3,         3,        0]]        # forbid
    # 0 = selectfirst
    # 1 = selectlowest
    # 2 = selecthighest
    # 3 = selectsecond

    xorkey = [0, 3]
    ret = iFORBID

    if (a == iFORBID):
        return b
    if (b == iFORBID):
        return a
    retu = [a, a, b, b]
    '''
    retu[0] = a; # first parameter
    retu[1] = a; # the lowest by default
    retu[2] = b; # highest by default
    retu[3] = b; # second parameter
    '''
    if (b < a):
        retu[1] = b
        retu[2] = a

    key = comparison[a & 3][b & 3] ^ xorkey[side]
    ret = retu[key]

    return ret


def unpackdist(d):
    return d >> PLYSHIFT, d & INFOMASK

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
iUNKNOWN = tb_UNKNOWN

iUNKNBIT = (1 << 2)

def dtm_unpack(stm, packed):
    p = packed

    if (iDRAW == p or iFORBID == p):
        return p

    info = p & 3
    store = p >> 2

    if (stm == 0):
        if (info == iWMATE):
            moves = store + 1
            plies = moves * 2 - 1
            prefx = info
        elif (info == iBMATE):
            moves = store
            plies = moves * 2
            prefx = info
        elif (info == iDRAW):
            moves = store + 1 + 63
            plies = moves * 2 - 1
            prefx = iWMATE
        elif (info == iFORBID):
            moves = store + 63
            plies = moves * 2
            prefx = iBMATE
        else:
            plies = 0
            prefx = 0

        ret = (prefx | (plies << 3))
    else:
        if (info == iBMATE):
            moves = store + 1
            plies = moves * 2 - 1
            prefx = info
        elif (info == iWMATE):
            moves = store
            plies = moves * 2
            prefx = info
        elif (info == iDRAW):
            if (store == 63):
                # exception: no position in the 5-man
                #    TBs needs to store 63 for iBMATE
                #    it is then used to indicate iWMATE
                #    when just overflows
                store+=1

                moves = store + 63
                plies = moves * 2
                prefx = iWMATE
            else:
                moves = store + 1 + 63
                plies = moves * 2 - 1
                prefx = iBMATE
        elif (info == iFORBID):
            moves = store + 63
            plies = moves * 2
            prefx = iWMATE
        else:
            plies = 0
            prefx = 0
        ret = (prefx | (plies << 3))
    return ret

def flipWE(x):
    return x ^ 7
def flipNS(x):
    return x ^ 56
def flipNW_SE(x):
    return ((x & 7) << 3) | (x >> 3)

BLOCK_Ax = 64
def getcol(x):
    return x & 7
def getrow(x):
    return x >> 3
def flip_type(x, y):
    ret = 0

    if (getcol(x) > 3):
        x = flipWE(x) # x = x ^ 07
        y = flipWE(y)
        ret |= 1
    if (getrow(x) > 3):
        x = flipNS(x) # x = x ^ 070
        y = flipNS(y)
        ret |= 2
    rowx = getrow(x)
    colx = getcol(x)
    if (rowx > colx):
        x = flipNW_SE(x) # x = ((x&7)<<3) | (x>>3)
        y = flipNW_SE(y)
        ret |= 4
    rowy = getrow(y)
    coly = getcol(y)
    if (rowx == colx and rowy > coly):
        x = flipNW_SE(x)
        y = flipNW_SE(y)
        ret |= 4
    return ret

def IDX_is_empty(x):
    return (x==-1)

kkidx = [[] for i in range(64)]

WHITES = (1 << 6)
BLACKS = (1 << 7)

NOPIECE = 0
PAWN = 1
KNIGHT = 2
BISHOP = 3
ROOK = 4
QUEEN = 5
KING = 6

wK = (KING | WHITES)
wP = (PAWN | WHITES)
wN = (KNIGHT | WHITES)
wB = (BISHOP | WHITES)
wR = (ROOK | WHITES)
wQ = (QUEEN | WHITES)

#Blacks
bK = (KING | BLACKS)
bP = (PAWN | BLACKS)
bN = (KNIGHT | BLACKS)
bB = (BISHOP | BLACKS)
bR = (ROOK | BLACKS)
bQ = (QUEEN | BLACKS)

def norm_kkindex(x, y):
    if (getcol(x) > 3):
        x = flipWE(x) # x = x ^ 07
        y = flipWE(y)
    if (getrow(x) > 3):
        x = flipNS(x) # x = x ^ 070
        y = flipNS(y)
    rowx = getrow(x)
    colx = getcol(x)
    if (rowx > colx):
        x = flipNW_SE(x) # x = ((x&7)<<3) | (x>>3)
        y = flipNW_SE(y)
    rowy = getrow(y)
    coly = getcol(y)
    if (rowx == colx) and (rowy > coly):
        x = flipNW_SE(x)
        y = flipNW_SE(y)

    return x, y

bstep = [ 17, 15, -15, -17, 0 ]
rstep = [ 1, 16, -1, -16, 0 ]
nstep = [ 18, 33, 31, 14, -18, -33, -31, -14, 0 ]
kstep = [ 1, 17, 16, 15, -1, -17, -16, -15, 0 ]

psteparr = [None, None, # NOPIECE & PAWN
           nstep, bstep, rstep, kstep, kstep] # same for Q & K

pslider = [False, False,
           False,  True,  True,  True, False
]

def tolist_rev(occ, input_piece, sq, thelist):
        # reversible moves from pieces. Output is a list of squares


    from_ = map88(sq)

    pc = input_piece & (PAWN | KNIGHT | BISHOP | ROOK | QUEEN | KING)

    steparr = psteparr[pc]
    slider = pslider[pc]

    if (slider):
        for step in steparr:
            if step == 0:
                break
            s = from_ + step
            while (0 == (s & 0x88)):
                us = unmap88(s)
                if (0 != (0x1 & (occ >> us))):
                    break
                thelist.append(us)
                s += step

    else:
        for step in steparr:
            if step == 0:
                break
            s = from_ + step
            if (0 == (s & 0x88)):
                us = unmap88(s)
                if (0 == (0x1 & (occ >> us))):
                    thelist.append(us)

def reach_init():
    stp_a = [ 15, -15 ]
    stp_b = [ 17, -17 ]
    Reach = [[-1]*64 for q in range(7)]

    for pc in range(KNIGHT, KING+1):
        for sq in range(64):
            bb = 0
            buflist = []
            tolist_rev(0, pc, sq, buflist)
            thelist = list(buflist)
            for li in thelist:
                bb |= 1 << li
                Reach[pc][sq] = bb

    for side in range(2):
        index = 1 ^ side
        STEP_A = stp_a[side]
        STEP_B = stp_b[side]
        for sq in range(64):
            sq88 = map88(sq)
            bb = 0

            thelist = list()

            s = sq88 + STEP_A
            if (0 == (s & 0x88)):
                us = unmap88(s)
                thelist.append(us)
            s = sq88 + STEP_B
            if (0 == (s & 0x88)):
                us = unmap88(s)
                thelist.append(us)

            for li in thelist:
                bb |= 1 << li
            Reach[index][sq] = bb

    return Reach

def BB_ISBITON(bb, bit):
        return (0 != (((bb) >> (bit)) & (1)))

def mapx88(x):
        return ((x & 56) << 1) | (x & 7)


def init_kkidx():
    # returns kkidx[][], wksq[], bksq[]

    # default is noindex
    kkidx = [[-1]*64 for x in range(64)]
    bksq = [-1]*MAX_KKINDEX
    wksq = [-1]*MAX_KKINDEX
    idx = 0
    for x in range(64):
        for y in range(64):
            # is x,y legal?
            if (not possible_attack(x, y, wK)) and (x != y):
                # normalize
                    # i <-- x; j <-- y
                i, j = norm_kkindex(x, y)

                if (kkidx[i][j] == -1):
                    #still empty
                    kkidx[i][j] = idx
                    kkidx[x][y] = idx
                    bksq[idx] = i
                    wksq[idx] = j
                    idx+=1

    return kkidx, wksq, bksq

def kxk_pctoindex(c):
    ft = flip_type(c.blackPieceSquares[0], c.whitePieceSquares[0])

    ws = list(c.whitePieceSquares)
    bs = list(c.blackPieceSquares)

    if ((ft & 1) != 0):
        ws = [flipWE(b) for b in ws]
        bs = [flipWE(b) for b in bs]

    if ((ft & 2) != 0):
        ws = [flipNS(b) for b in ws]
        bs = [flipNS(b) for b in bs]

    if ((ft & 4) != 0):
        ws = [flipNW_SE(b) for b in ws]
        bs = [flipNW_SE(b) for b in bs]

    ki = kkidx[bs[0]][ws[0]] # kkidx [black king] [white king]

    if (ki == -1):
        return NOINDEX

    return ki * BLOCK_Ax + ws[1]

Endgamekey = collections.namedtuple("Endgamekey", ["maxindex", "slice_n", "pctoi"])

EGKEY = {
    "kqk": Endgamekey(MAX_KXK, 1, kxk_pctoindex),
    "krk": Endgamekey(MAX_KXK, 1, kxk_pctoindex),
    "kbk": Endgamekey(MAX_KXK, 1, kxk_pctoindex),
    "knk": Endgamekey(MAX_KXK, 1, kxk_pctoindex),
    "kpk": Endgamekey(MAX_kpk, 24, kpk_pctoindex),

    "kqkq": Endgamekey(MAX_kakb, 1, kakb_pctoindex),
    "kqkr": Endgamekey(MAX_kakb, 1, kakb_pctoindex),
    "kqkb": Endgamekey(MAX_kakb, 1, kakb_pctoindex),
    "kqkn": Endgamekey(MAX_kakb, 1, kakb_pctoindex),

    "krkr": Endgamekey(MAX_kakb, 1,  kakb_pctoindex),
    "krkb": Endgamekey(MAX_kakb, 1, kakb_pctoindex),
    "krkn": Endgamekey(MAX_kakb, 1, kakb_pctoindex),

    "kbkb": Endgamekey(MAX_kakb, 1,  kakb_pctoindex),
    "kbkn": Endgamekey(MAX_kakb, 1, kakb_pctoindex),

    "knkn": Endgamekey(MAX_kakb, 1, kakb_pctoindex),

    "kqqk": Endgamekey(MAX_kaak, 1, kaak_pctoindex),
    "kqrk": Endgamekey(MAX_kabk, 1,  kabk_pctoindex),
    "kqbk": Endgamekey(MAX_kabk, 1,  kabk_pctoindex),
    "kqnk": Endgamekey(MAX_kabk, 1,  kabk_pctoindex),

    "krrk": Endgamekey(MAX_kaak, 1,  kaak_pctoindex),
    "krbk": Endgamekey(MAX_kabk, 1, kabk_pctoindex),
    "krnk": Endgamekey(MAX_kabk, 1,  kabk_pctoindex),

    "kbbk": Endgamekey(MAX_kaak, 1,  kaak_pctoindex),
    "kbnk": Endgamekey(MAX_kabk, 1,  kabk_pctoindex),

    "knnk": Endgamekey(MAX_kaak, 1,  kaak_pctoindex),
    "kqkp": Endgamekey(MAX_kakp, 24, kakp_pctoindex),
    "krkp": Endgamekey(MAX_kakp, 24, kakp_pctoindex),
    "kbkp": Endgamekey(MAX_kakp, 24, kakp_pctoindex),
    "knkp": Endgamekey(MAX_kakp, 24, kakp_pctoindex),

    "kqpk": Endgamekey(MAX_kapk, 24, kapk_pctoindex),
    "krpk": Endgamekey(MAX_kapk, 24, kapk_pctoindex),
    "kbpk": Endgamekey(MAX_kapk, 24, kapk_pctoindex),
    "knpk": Endgamekey(MAX_kapk, 24, kapk_pctoindex),

    "kppk": Endgamekey(MAX_kppk, MAX_PPINDEX , kppk_pctoindex),

    "kpkp": Endgamekey(MAX_kpkp, MAX_PpINDEX , kpkp_pctoindex),

    "kppkp": Endgamekey(MAX_kppkp, 24*MAX_PP48_INDEX, kppkp_pctoindex) ,

    "kbbkr": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex) ,
    "kbbkb": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex) ,
    "knnkb": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex) ,
    "knnkn": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex) ,

    "kqqqk": Endgamekey(MAX_kaaak, 1, kaaak_pctoindex),
    "kqqrk": Endgamekey(MAX_kaabk, 1, kaabk_pctoindex),
    "kqqbk": Endgamekey(MAX_kaabk, 1, kaabk_pctoindex),
    "kqqnk": Endgamekey(MAX_kaabk, 1, kaabk_pctoindex),
    "kqrrk": Endgamekey(MAX_kabbk, 1, kabbk_pctoindex),
    "kqrbk": Endgamekey(MAX_kabck, 1, kabck_pctoindex),
    "kqrnk": Endgamekey(MAX_kabck, 1, kabck_pctoindex),
    "kqbbk": Endgamekey(MAX_kabbk, 1, kabbk_pctoindex),
    "kqbnk": Endgamekey(MAX_kabck, 1, kabck_pctoindex),
    "kqnnk": Endgamekey(MAX_kabbk, 1, kabbk_pctoindex),
    "krrrk": Endgamekey(MAX_kaaak, 1, kaaak_pctoindex),
    "krrbk": Endgamekey(MAX_kaabk, 1, kaabk_pctoindex),
    "krrnk": Endgamekey(MAX_kaabk, 1, kaabk_pctoindex),
    "krbbk": Endgamekey(MAX_kabbk, 1, kabbk_pctoindex),
    "krbnk": Endgamekey(MAX_kabck, 1, kabck_pctoindex),
    "krnnk": Endgamekey(MAX_kabbk, 1, kabbk_pctoindex),
    "kbbbk": Endgamekey(MAX_kaaak, 1, kaaak_pctoindex),
    "kbbnk": Endgamekey(MAX_kaabk, 1, kaabk_pctoindex),
    "kbnnk": Endgamekey(MAX_kabbk, 1, kabbk_pctoindex),
    "knnnk": Endgamekey(MAX_kaaak, 1, kaaak_pctoindex),
    "kqqkq": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "kqqkr": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "kqqkb": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "kqqkn": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "kqrkq": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqrkr": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqrkb": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqrkn": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqbkq": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqbkr": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqbkb": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqbkn": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqnkq": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqnkr": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqnkb": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kqnkn": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "krrkq": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "krrkr": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "krrkb": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "krrkn": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "krbkq": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "krbkr": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "krbkb": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "krbkn": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "krnkq": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "krnkr": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "krnkb": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "krnkn": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kbbkq": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "kbbkn": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "kbnkq": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kbnkr": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kbnkb": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "kbnkn": Endgamekey(MAX_kabkc, 1, kabkc_pctoindex),
    "knnkq": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),
    "knnkr": Endgamekey(MAX_kaakb, 1, kaakb_pctoindex),

    "kqqpk": Endgamekey(MAX_kaapk, 24, kaapk_pctoindex),
    "kqrpk": Endgamekey(MAX_kabpk, 24, kabpk_pctoindex),
    "kqbpk": Endgamekey(MAX_kabpk, 24, kabpk_pctoindex),
    "kqnpk": Endgamekey(MAX_kabpk, 24, kabpk_pctoindex),
    "krrpk": Endgamekey(MAX_kaapk, 24, kaapk_pctoindex),
    "krbpk": Endgamekey(MAX_kabpk, 24, kabpk_pctoindex),
    "krnpk": Endgamekey(MAX_kabpk, 24, kabpk_pctoindex),
    "kbbpk": Endgamekey(MAX_kaapk, 24, kaapk_pctoindex),
    "kbnpk": Endgamekey(MAX_kabpk, 24, kabpk_pctoindex),
    "knnpk": Endgamekey(MAX_kaapk, 24, kaapk_pctoindex),

    "kqppk": Endgamekey(MAX_kappk, MAX_PPINDEX, kappk_pctoindex),
    "krppk": Endgamekey(MAX_kappk, MAX_PPINDEX, kappk_pctoindex),
    "kbppk": Endgamekey(MAX_kappk, MAX_PPINDEX, kappk_pctoindex),
    "knppk": Endgamekey(MAX_kappk, MAX_PPINDEX, kappk_pctoindex),

    "kqpkq": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "kqpkr": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "kqpkb": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "kqpkn": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "krpkq": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "krpkr": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "krpkb": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "krpkn": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "kbpkq": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "kbpkr": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "kbpkb": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "kbpkn": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "knpkq": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "knpkr": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "knpkb": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "knpkn": Endgamekey(MAX_kapkb, 24, kapkb_pctoindex),
    "kppkq": Endgamekey(MAX_kppka, MAX_PPINDEX, kppka_pctoindex),
    "kppkr": Endgamekey(MAX_kppka, MAX_PPINDEX, kppka_pctoindex),
    "kppkb": Endgamekey(MAX_kppka, MAX_PPINDEX, kppka_pctoindex),
    "kppkn": Endgamekey(MAX_kppka, MAX_PPINDEX, kppka_pctoindex),

    "kqqkp": Endgamekey(MAX_kaakp, 24, kaakp_pctoindex),
    "kqrkp": Endgamekey(MAX_kabkp, 24, kabkp_pctoindex),
    "kqbkp": Endgamekey(MAX_kabkp, 24, kabkp_pctoindex),
    "kqnkp": Endgamekey(MAX_kabkp, 24, kabkp_pctoindex),
    "krrkp": Endgamekey(MAX_kaakp, 24, kaakp_pctoindex),
    "krbkp": Endgamekey(MAX_kabkp, 24, kabkp_pctoindex),
    "krnkp": Endgamekey(MAX_kabkp, 24, kabkp_pctoindex),
    "kbbkp": Endgamekey(MAX_kaakp, 24, kaakp_pctoindex),
    "kbnkp": Endgamekey(MAX_kabkp, 24, kabkp_pctoindex),
    "knnkp": Endgamekey(MAX_kaakp, 24, kaakp_pctoindex),

    "kqpkp": Endgamekey(MAX_kapkp, MAX_PpINDEX, kapkp_pctoindex),
    "krpkp": Endgamekey(MAX_kapkp, MAX_PpINDEX, kapkp_pctoindex),
    "kbpkp": Endgamekey(MAX_kapkp, MAX_PpINDEX, kapkp_pctoindex),
    "knpkp": Endgamekey(MAX_kapkp, MAX_PpINDEX, kapkp_pctoindex),

    "kpppk": Endgamekey(MAX_kpppk, MAX_PPP48_INDEX, kpppk_pctoindex),
}

# inits

Reach = reach_init()
flipt = init_flipt()
aabase, aaidx = init_aaidx()
aaa_base, aaa_xyz = init_aaa()
pp48_idx, pp48_sq_x, pp48_sq_y, _ = init_pp48_idx()
ppidx, pp_hi24, pp_lo48, _ = init_ppidx()
ppp48_idx, ppp48_sq_x,ppp48_sq_y, ppp48_sq_z = init_ppp48_idx()

def attack_maps_init():
    attmsk = [0] * 256
    attmsk[wP] = 1 << 0
    attmsk[bP] = 1 << 1

    attmsk[KNIGHT] = 1 << 2
    attmsk[wN] = 1 << 2
    attmsk[bN] = 1 << 2

    attmsk[BISHOP] = 1 << 3
    attmsk[wB] = 1 << 3
    attmsk[bB] = 1 << 3

    attmsk[ROOK] = 1 << 4
    attmsk[wR] = 1 << 4
    attmsk[bR] = 1 << 4

    attmsk[QUEEN] = 1 << 5
    attmsk[wQ] = 1 << 5
    attmsk[bQ] = 1 << 5

    attmsk[KING] = 1 << 6
    attmsk[wK] = 1 << 6
    attmsk[bK] = 1 << 6

    attmap = [[0]*64 for i in range(64)]
    for to_ in range(64):
        for from_ in range(64):
            m = 0
            rook = Reach[ROOK][from_]
            bishop = Reach[BISHOP][from_]
            queen = Reach[QUEEN][from_]
            knight = Reach[KNIGHT][from_]
            king = Reach[KING][from_]

            if (BB_ISBITON(knight, to_)):
              m |= attmsk[wN]
            if (BB_ISBITON(king, to_)):
              m |= attmsk[wK]
            if (BB_ISBITON(rook, to_)):
              m |= attmsk[wR]
            if (BB_ISBITON(bishop, to_)):
              m |= attmsk[wB]
            if (BB_ISBITON(queen, to_)):
              m |= attmsk[wQ]

            to88 = mapx88(to_)
            fr88 = mapx88(from_)
            diff = to88 - fr88

            if (diff == 17 or diff == 15):
              m |= attmsk[wP]
            if (diff == -17 or diff == -15):
              m |= attmsk[bP]

            attmap[to_][from_] = m

    return attmsk, attmap

attmsk, attmap = attack_maps_init()

def possible_attack(from_, to_, piece):
    return (0 != (attmap[to_][from_] & attmsk[piece]))

kkidx, wksq, bksq = init_kkidx()

def a8toa1_init():
    a8toa1 = {}
    for i in range(64):
         strow = (i % 8)
         stcol = 7 - (i / 8)
         newId = (stcol * 8) + strow
         a8toa1[i] = newId
    return a8toa1

a8toa1 = a8toa1_init()

class PythonTablebases(object):
    """ Provide access to Gaviota tablebases via full python code."""

    def __init__(self,directory):
        self.validTables = []
        self.LoadTableDescriptions(directory)
        self.egtb_root_path = directory
        self.whiteSquares = None
        self.blackSquares = None
        self.whiteTypes   = None
        self.blackTypes   = None
        self.realside = None
        self.currentFilename = ""
        self.currentStream = None
        self.whitePieceSquares = None
        self.whitePieceTypes   = None
        self.blackPieceSquares = None
        self.blackPieceTypes   = None
        self.newFile = None
        self.block_age = 0

    def LoadTableDescriptions(self, egtb_path):
        if not os.path.isdir(egtb_path):
            raise IOError("not a tablebase directory: {0}".format(repr(egtb_path)))
        files = os.listdir(egtb_path)
        for afile in files:
            tokes = afile.split(os.sep)
            if (len(tokes) > 0):
                fn = tokes[-1]
                if (fn.find(".gtb.cp4") != -1):
                    self.validTables.append(fn.replace(".gtb.cp4", ""))

    def probe_dtm(self, board):
        """
        Probes for depth to mate information.

        Returns ``None`` if the position was not found in any of the tables.

        Otherwise the absolute value is the number of half moves until
        forced mate. The value is positive if the side to move is winning,
        otherwise it is negative.

        In the example position white to move will get mated in 10 half moves:

        >>> with chess.gaviota.open_tablebases("data/gaviota") as tablebases:
        ...     tablebases.probe_dtm(chess.Board("8/8/8/8/8/8/8/K2kr3 w - - 0 1"))
        ...
        -10
        """
        white = [(square,  board.piece_type_at(square), ) for square in chess.SquareSet(board.occupied_co[chess.WHITE])]
        self.whiteSquares,  self.whiteTypes = zip(*white)
        black = [(square, board.piece_type_at(square), ) for square in chess.SquareSet(board.occupied_co[chess.BLACK])]
        self.blackSquares,  self.blackTypes = zip(*black)
        side = 0 if (board.turn == chess.WHITE) else 1
        self.realside = side
        self.epsq = board.ep_square if board.ep_square else NOSQUARE
        return self._Probe(side,  self.epsq)


    def _Probe(self,  realside,  epsq):
        probeResult = ProbeResultType()

        if ((len(self.blackSquares)== 1) and (len(self.whiteSquares) == 1)):
            probeResult.found = True
            probeResult.stm = MateResult.Draw
            probeResult.error = "With only 2 kings, Draw is assumed"
            return probeResult

        if ((len(self.blackSquares) + len(self.whiteSquares)) > 5):
            probeResult.error = "Max 5 man tables are supported"
            probeResult.found = False
            return probeResult

        side = realside

        ret,  side,  epsq = self.SetupEGTB(side,  epsq)
        if not ret:
            probeResult.found = False
            probeResult.error = "Could not find EGTB file: " + self.newFile
            return probeResult

        is_dtm, dtm = self.egtb_get_dtm(side, epsq)
        if (is_dtm):
            probeResult.found = True
            probeResult.stm = MateResult.Unknown
            ply,  res = unpackdist(dtm)

            ret = 0

            if (res == iWMATE):
                if (self.Reversed):
                    probeResult.stm = MateResult.BlackToMate
                else:
                    probeResult.stm = MateResult.WhiteToMate
            elif (res == iBMATE):
                if (self.Reversed):
                    probeResult.stm = MateResult.WhiteToMate
                else:
                    probeResult.stm = MateResult.BlackToMate
            elif (res == iDRAW):
                probeResult.stm = MateResult.Draw

            if (self.realside == 0):
                if (probeResult.stm == MateResult.BlackToMate):
                    ret = -ply
                elif (probeResult.stm == MateResult.WhiteToMate):
                    ret = ply
            else:
                if (probeResult.stm == MateResult.WhiteToMate):
                    ret = -ply
                elif (probeResult.stm == MateResult.BlackToMate):
                    ret = ply

            probeResult.dtm = ret
            probeResult.ply = ply
        else:
            probeResult.found = False

        return probeResult

    def SetupEGTB(self,  side,  epsq):
        self.whiteSquares, self.whiteTypes = sortlists(self.whiteSquares, self.whiteTypes)
        self.blackSquares, self.blackTypes = sortlists(self.blackSquares, self.blackTypes)

        fenType = [ " ", "p", "n", "b", "r", "q", "k" ]
        blackLetters = ""
        whiteLetters = ""

        '''
        whiteScore = 0
        foreach (int i in whiteTypes)
            whiteScore += i;
            whiteLetters += new String(fenType[i], 1);
        '''
        # unused
        # whiteScore = sum(whiteTypes)
        whiteLetters = "".join([fenType[i] for i in self.whiteTypes])

        '''
        blackScore = 0
        foreach (int i in blackTypes)
            blackScore += i;
            blackLetters += new String(fenType[i], 1);
        '''
        # unused
        # blackScore = sum(blackTypes)
        blackLetters = "".join([fenType[i] for i in self.blackTypes])

        self.newFile = ""
        if ((whiteLetters+blackLetters) in self.validTables):
            self.whitePieceSquares = self.whiteSquares
            self.whitePieceTypes   = self.whiteTypes
            self.blackPieceSquares = self.blackSquares
            self.blackPieceTypes   = self.blackTypes
            self.newFile = whiteLetters + blackLetters
            self.Reversed = False
        elif ((blackLetters + whiteLetters) in self.validTables):
            self.whitePieceSquares = self.blackSquares
            self.whitePieceTypes = self.blackTypes
            self.blackPieceSquares = self.whiteSquares
            self.blackPieceTypes = self.whiteTypes
            self.newFile = blackLetters + whiteLetters
            self.Reversed = True

            self.whitePieceSquares = list_sq_flipNS(self.whitePieceSquares)
            self.blackPieceSquares = list_sq_flipNS(self.blackPieceSquares)

            side = Opp(side)
            if (epsq != NOSQUARE):
                epsq ^= 56
        else:
            self.newFile = whiteLetters + blackLetters
            return False,  side,  epsq
        self.OpenEndgameTableBase(self.newFile)
        return True,  side,  epsq

    def OpenEndgameTableBase(self, pieces):
        if self.currentFilename ==pieces:
            return
        tablePath = self.egtb_root_path +os.sep + pieces + ".gtb.cp4"
        if (self.currentStream is not None):
            self.currentStream.close()
        if (os.path.isfile(tablePath)):
            self.currentFilename = pieces
            self.currentStream = open(tablePath,'rb')
            egtb_loadindexes(self.currentFilename, self.currentStream)
            self.currentPctoi = EGKEY[self.currentFilename].pctoi

    def egtb_get_dtm(self, side, epsq):
        ok, dtm  = self.tb_probe_(side, epsq)

        if (ok):
            if (epsq != NOSQUARE):
                capturer_a = 0
                capturer_b = 0
                xed = 0
                okcall = True

                old_whitePieceSquares = list(self.whitePieceSquares)
                old_blackPieceSquares = list(self.blackPieceSquares)
                old_whitePieceType = list(self.whitePieceTypes)
                old_blackPieceType = list(self.blackPieceTypes)

                if (side == 0):
                    xs = list(self.whitePieceSquares)
                    xp = list(self.whitePieceTypes)
                    ys = list(self.blackPieceSquares)
                    yp = list(self.blackPieceTypes)
                else:
                    xs = list(self.blackPieceSquares)
                    xp = list(self.blackPieceTypes)
                    ys = list(self.whitePieceSquares)
                    yp = list(self.whitePieceTypes)

                # captured pawn, trick: from epsquare to captured
                xed = epsq ^ (1 << 3)

                # find index captured (j)
                try:
                    j = ys.index(xed)
                except:
                    j = -1
                # try first possible ep capture
                if (0 == (0x88 & (map88(xed) + 1))):
                    capturer_a = xed + 1
                # try second possible ep capture
                if (0 == (0x88 & (map88(xed) - 1))):
                    capturer_b = xed - 1

                if ((j > -1) and (ys[j] == xed)):
                    # xsl = xs.Count
                    # find capturers (i)
                    for i in range(len(xs)): # (i = 0; (i < xsl) && okcall i++)
                        if (xp[i] == PAWN and (xs[i] == capturer_a or xs[i] == capturer_b) and okcall):
                            epscore = iFORBID

                            # execute capture
                            xs[i] = epsq
                            ys, yp = removepiece(ys, yp, j)

                            newdtm = 0

                            self.whiteSquares = list(xs)
                            self.whiteTypes = list(xp)
                            self.blackSquares = list(ys)
                            self.blackTypes = list(yp)

                            # changing currentFile to kpk for ex. we lost a piece so new file is regq
                            # make sure to change back when done
                            ret,  _,  _ = self.SetupEGTB(side,  NOSQUARE)
                            if not ret:
                                okcall = False
                            else:
                                okcall, newdtm  = self.tb_probe_(Opp(side), NOSQUARE)

                            self.whitePieceSquares = old_whitePieceSquares
                            self.whitePieceTypes   = old_whitePieceType
                            self.blackPieceSquares = old_blackPieceSquares
                            self.blackPieceTypes   = old_blackPieceType

                            if (okcall):
                                epscore = newdtm
                                epscore = adjust_up(epscore)

                                # chooses to ep or not
                                dtm = bestx(side, epscore, dtm)
                            else:
                                break
        return ok, dtm

    def egtb_block_getnumber(self, side, idx):
        max = EGKEY[self.currentFilename].maxindex

        blocks_per_side = 1 + (max - 1) // ENTRIES_PER_BLOCK
        block_in_side = idx // ENTRIES_PER_BLOCK

        return side * blocks_per_side + block_in_side

    def egtb_block_getsize(self, idx):
        blocksz = ENTRIES_PER_BLOCK
        maxindex = EGKEY[self.currentFilename].maxindex
        block = idx // blocksz
        offset = block * blocksz

        if (offset + blocksz) > maxindex:
            return maxindex - offset # last block size
        else:
            return blocksz # size of a normal block

    def tb_probe_(self, side, epsq):
        c = currentConf()
        c.whitePieceSquares = self.whitePieceSquares
        c.whitePieceTypes   = self.whitePieceTypes
        c.blackPieceSquares = self.blackPieceSquares
        c.blackPieceTypes   = self.blackPieceTypes
        idx = self.currentPctoi(c)
        offset, remainder = split_index(idx)

        t =blockCache.get((self.currentFilename, offset, side,))
        if t is None:
            t = TableBlock(self.currentFilename, side, offset,  self.block_age)

            block = self.egtb_block_getnumber(side, idx)
            n = self.egtb_block_getsize(idx)
            z = egtb_block_getsize_zipped(self.currentFilename, block)

            egtb_block_park(self.currentFilename,block, self.currentStream)

            Buffer_zipped = self.currentStream.read(z)
            if Buffer_zipped[0]==0:
                # if flag is zero, plain LZMA is following
                Buffer_zipped = Buffer_zipped[2:]
            else:
                # else LZMA86, we have to build a fake header
                _dictionarySize = 4096
                _posStateBits = 2
                _numLiteralPosStateBits = 0
                _numLiteralContextBits = 3
                properties =[0]*13
                properties[0] = ((_posStateBits * 5 + _numLiteralPosStateBits) * 9 + _numLiteralContextBits);
                for i in range(4):
                    properties[1 + i] = ((_dictionarySize >> (8 * i)) & 0xFF)
                for i in range(8):
                    properties[5 + i] = ((n >> (8 * i)) & 0xFF)
                #concatenate the fake header with the true LZMA stream
                Buffer_zipped = bytes(properties) + Buffer_zipped[15:]

            Buffer_packed = lzma.LZMADecompressor().decompress(Buffer_zipped)

            t.pcache = egtb_block_unpack(side, n, Buffer_packed)

            blockCache[(t.key, t.offset, t.side)] = t
            if (len(blockCache) > 256):
                lru = sorted(blockCache.values(), key=lambda x: x.age)[0]
                del blockCache[(lru.key,  lru.offset,  lru.side, )]
        else:
            t.age = self.block_age

        self.block_age +=1
        dtm = t.pcache[remainder]

        return True, dtm


class NativeTablebases(object):
    """Provides access to Gaviota tablebases via the shared library libgtb."""

    def __init__(self, directory, libgtb):
        self.libgtb = libgtb
        self.libgtb.tb_init.restype = ctypes.c_char_p
        self.libgtb.tb_restart.restype = ctypes.c_char_p
        self.libgtb.tbpaths_getmain.restype = ctypes.c_char_p
        self.libgtb.tb_probe_hard.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]

        if self.libgtb.tb_is_initialized():
            raise RuntimeError("only one gaviota instance can be initialized at a time")

        self.paths = []
        if directory is not None:
            self.open_directory(directory)

        self._tbcache_restart(1024 * 1024, 50)

    def open_directory(self, directory):
        """Loads *.gtb.cp4* tables from a directory."""
        if not os.path.isdir(directory):
            raise IOError("not a tablebase directory: {0}".format(repr(directory)))

        self.paths.append(directory)
        self._tb_restart()

    def _tb_restart(self):
        self.c_paths = (ctypes.c_char_p * len(self.paths))()
        self.c_paths[:] = [path.encode("utf-8") for path in self.paths]

        verbosity = ctypes.c_int(1)
        compression_scheme = ctypes.c_int(4)

        ret = self.libgtb.tb_restart(verbosity, compression_scheme, self.c_paths)
        if ret:
            LOGGER.debug(ret.decode("utf-8"))

        LOGGER.debug("Main path has been set to %s", self.libgtb.tbpaths_getmain().decode("utf-8"))

        av = self.libgtb.tb_availability()
        if av & 1:
            LOGGER.debug("Some 3 piece tablebases available")
        if av & 2:
            LOGGER.debug("All 3 piece tablebases complete")
        if av & 4:
            LOGGER.debug("Some 4 piece tablebases available")
        if av & 8:
            LOGGER.debug("All 4 piece tablebases complete")
        if av & 16:
            LOGGER.debug("Some 5 piece tablebases available")
        if av & 32:
            LOGGER.debug("All 5 piece tablebases complete")

    def _tbcache_restart(self, cache_mem, wdl_fraction):
        self.libgtb.tbcache_restart(ctypes.c_size_t(cache_mem), ctypes.c_int(wdl_fraction))

    def probe_dtm(self, board):
        """
        Probes for depth to mate information.

        Returns ``None`` if the position was not found in any of the tables.

        Otherwise the absolute value is the number of half moves until
        forced mate. The value is positive if the side to move is winning,
        otherwise it is negative.

        In the example position white to move will get mated in 10 half moves:

        >>> with chess.gaviota.open_tablebases("data/gaviota") as tablebases:
        ...     tablebases.probe_dtm(chess.Board("8/8/8/8/8/8/8/K2kr3 w - - 0 1"))
        ...
        -10
        """
        return self._probe_hard(board)

    def probe_wdl(self, board):
        """
        Probes for win/draw/loss-information.

        Returns ``None`` if the position was not found in any of the tables.

        Returns ``1`` if the side to move is winning, ``0`` if it is a draw,
        and ``-1`` if the side to move is losing.

        >>> with chess.gaviota.open_tablebases("data/gaviota") as tablebases:
        ...     tablebases.probe_wdl(chess.Board("4k3/8/B7/8/8/8/4K3 w - 0 1"))
        ...
        0
        """
        return self._probe_hard(board, wdl_only=True)

    def _probe_hard(self, board, wdl_only=False):
        if chess.pop_count(board.occupied_co[chess.WHITE]) > 16:
            return None
        if chess.pop_count(board.occupied_co[chess.BLACK]) > 16:
            return None

        if board.is_insufficient_material():
            return 0

        if board.castling_rights:
            return None

        stm = ctypes.c_uint(0 if board.turn == chess.WHITE else 1)
        ep_square = ctypes.c_uint(board.ep_square if board.ep_square else 64)
        castling = ctypes.c_uint(0)

        c_ws = (ctypes.c_uint * 17)()
        c_wp = (ctypes.c_ubyte * 17)()

        i = -1
        for i, square in enumerate(chess.SquareSet(board.occupied_co[chess.WHITE])):
            c_ws[i] = square
            c_wp[i] = board.piece_type_at(square)

        c_ws[i + 1] = 64
        c_wp[i + 1] = 0

        c_bs = (ctypes.c_uint * 17)()
        c_bp = (ctypes.c_ubyte * 17)()

        i = -1
        for i, square in enumerate(chess.SquareSet(board.occupied_co[chess.BLACK])):
            c_bs[i] = square
            c_bp[i] = board.piece_type_at(square)

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
            LOGGER.warning("Tablebase for %s marked as forbidden", board.fen())
            return None

        # Probe failed or unknown.
        if not ret or info.value == 7:
            return None

        # Draw.
        if info.value == 0:
            return 0

        # White mates.
        if info.value == 1:
            return dtm if board.turn == chess.WHITE else -dtm

        # Black mates.
        if info.value == 2:
            return dtm if board.turn == chess.BLACK else -dtm

    def close(self):
        """Closes all loaded tables and clears all caches."""
        if self.libgtb.tb_is_initialized():
            self.libgtb.tbcache_done()
            self.libgtb.tb_done()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def open_native_tablebases(directory, libgtb=None, LibraryLoader=ctypes.cdll):
    libgtb = libgtb or ctypes.util.find_library("gtb") or "libgtb.so.1.0.1"
    return NativeTablebases(directory, LibraryLoader.LoadLibrary(libgtb))


def open_tablebases(directory=None, libgtb=None, LibraryLoader=ctypes.cdll):
    """
    Opens a collection of tablebases for probing.

    First native access via the shared library libgtb is tried. You can
    optionally provide a specific library name or a library loader.
    The shared library has global state and caches, so only one instance can
    be open at a time.

    Second pure Python probing code is tried.
    """
    try:
        if LibraryLoader:
            return open_native_tablebases(directory, libgtb, LibraryLoader)
    except (OSError, RuntimeError) as err:
        LOGGER.info("Falling back to pure Python tablebases: %r", err)

    return PythonTablebases(directory)
