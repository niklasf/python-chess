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
from typing import BinaryIO, TypeAlias
from collections.abc import Callable


LOGGER = logging.getLogger(__name__)

_StrPath: TypeAlias = str | os.PathLike[str]


_NOSQUARE = 64
_NOINDEX = -1

_MAX_KKINDEX = 462
_MAX_PPINDEX = 576
_MAX_PpINDEX = 24 * 48
_MAX_AAINDEX = (63 - 62) + (62 // 2 * (127 - 62)) - 1 + 1
_MAX_AAAINDEX = 64 * 21 * 31
_MAX_PPP48_INDEX = 8648
_MAX_PP48_INDEX = 1128

_MAX_KXK = _MAX_KKINDEX * 64
_MAX_kabk = _MAX_KKINDEX * 64 * 64
_MAX_kakb = _MAX_KKINDEX * 64 * 64
_MAX_kpk = 24 * 64 * 64
_MAX_kakp = 24 * 64 * 64 * 64
_MAX_kapk = 24 * 64 * 64 * 64
_MAX_kppk = _MAX_PPINDEX * 64 * 64
_MAX_kpkp = _MAX_PpINDEX * 64 * 64
_MAX_kaak = _MAX_KKINDEX * _MAX_AAINDEX
_MAX_kabkc = _MAX_KKINDEX * 64 * 64 * 64
_MAX_kabck = _MAX_KKINDEX * 64 * 64 * 64
_MAX_kaakb = _MAX_KKINDEX * _MAX_AAINDEX * 64
_MAX_kaabk = _MAX_KKINDEX * _MAX_AAINDEX * 64
_MAX_kabbk = _MAX_KKINDEX * _MAX_AAINDEX * 64
_MAX_kaaak = _MAX_KKINDEX * _MAX_AAAINDEX
_MAX_kapkb = 24 * 64 * 64 * 64 * 64
_MAX_kabkp = 24 * 64 * 64 * 64 * 64
_MAX_kabpk = 24 * 64 * 64 * 64 * 64
_MAX_kppka = _MAX_kppk * 64
_MAX_kappk = _MAX_kppk * 64
_MAX_kapkp = _MAX_kpkp * 64
_MAX_kaapk = 24 * _MAX_AAINDEX * 64 * 64
_MAX_kaakp = 24 * _MAX_AAINDEX * 64 * 64
_MAX_kppkp = 24 * _MAX_PP48_INDEX * 64 * 64
_MAX_kpppk = _MAX_PPP48_INDEX * 64 * 64

_PLYSHIFT = 3
_INFOMASK = 7

_WE_FLAG = 1
_NS_FLAG = 2
_NW_SE_FLAG = 4

_ITOSQ = [
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

_ENTRIES_PER_BLOCK = 16 * 1024

_EGTB_MAXBLOCKSIZE = 65536


def _map24_b(s: int) -> int:
    s -= 8
    return ((s & 3) + s) >> 1

def _map88(x: int) -> int:
    return x + (x & 56)

def _in_queenside(x: int) -> int:
    return (x & (1 << 2)) == 0

def _flip_we(x: int) -> int:
    return x ^ 7

def _flip_ns(x: int) -> int:
    return x ^ 56

def _flip_nw_se(x: int) -> int:
    return ((x & 7) << 3) | (x >> 3)

def _idx_is_empty(x: int) -> int:
    return x == -1


def _flip_type(x: chess.Square, y: chess.Square) -> int:
    ret = 0

    if chess.square_file(x) > chess.FILE_D:
        x = _flip_we(x)
        y = _flip_we(y)
        ret |= 1

    if chess.square_rank(x) > chess.RANK_4:
        x = _flip_ns(x)
        y = _flip_ns(y)
        ret |= 2

    rowx = chess.square_rank(x)
    colx = chess.square_file(x)

    if rowx > colx:
        x = _flip_nw_se(x)
        y = _flip_nw_se(y)
        ret |= 4

    rowy = chess.square_rank(y)
    coly = chess.square_file(y)
    if rowx == colx and rowy > coly:
        x = _flip_nw_se(x)
        y = _flip_nw_se(y)
        ret |= 4

    return ret

def _init_flipt() -> list[list[int]]:
    return [[_flip_type(j, i) for i in range(64)] for j in range(64)]

_FLIPT = _init_flipt()


def _init_pp48_idx() -> tuple[list[list[int]], list[int], list[int]]:
    MAX_I = MAX_J = 48
    idx = 0
    pp48_idx = [[-1] * MAX_J for _ in range(MAX_I)]
    pp48_sq_x = [_NOSQUARE] * _MAX_PP48_INDEX
    pp48_sq_y = [_NOSQUARE] * _MAX_PP48_INDEX

    idx = 0
    for a in range(chess.H7, chess.A2 - 1, -1):
        for b in range(a - 1, chess.A2 - 1, -1):
            i = _flip_we(_flip_ns(a)) - 8
            j = _flip_we(_flip_ns(b)) - 8

            if _idx_is_empty(pp48_idx[i][j]):
                pp48_idx[i][j] = idx
                pp48_idx[j][i] = idx
                pp48_sq_x[idx] = i
                pp48_sq_y[idx] = j
                idx += 1

    return pp48_idx, pp48_sq_x, pp48_sq_y

PP48_IDX, PP48_SQ_X, PP48_SQ_Y = _init_pp48_idx()


def _init_ppp48_idx() -> tuple[list[list[list[int]]], list[int], list[int], list[int]]:
    MAX_I = MAX_J = MAX_K = 48
    ppp48_idx = [[[-1] * MAX_I for _ in range(MAX_J)] for _ in range(MAX_K)]
    ppp48_sq_x = [_NOSQUARE] * _MAX_PPP48_INDEX
    ppp48_sq_y = [_NOSQUARE] * _MAX_PPP48_INDEX
    ppp48_sq_z = [_NOSQUARE] * _MAX_PPP48_INDEX

    idx = 0
    for x in range(48):
        for y in range(x + 1, 48):
            for z in range(y + 1, 48):
                a = _ITOSQ[x]
                b = _ITOSQ[y]
                c = _ITOSQ[z]
                if not _in_queenside(b) or not _in_queenside(c):
                    continue

                i = a - 8
                j = b - 8
                k = c - 8

                if _idx_is_empty(ppp48_idx[i][j][k]):
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

PPP48_IDX, PPP48_SQ_X, PPP48_SQ_Y, PPP48_SQ_Z = _init_ppp48_idx()


def _init_aaidx() -> tuple[list[int], list[list[int]]]:
    aaidx = [[-1] * 64 for _ in range(64)]
    aabase = [0] * _MAX_AAINDEX

    idx = 0
    for x in range(64):
        for y in range(x + 1, 64):

            if _idx_is_empty(aaidx[x][y]):
                # Still empty.
                aaidx[x][y] = idx
                aaidx[y][x] = idx
                aabase[idx] = x
                idx += 1

    return aabase, aaidx

AABASE, AAIDX = _init_aaidx()


def _init_aaa() -> tuple[list[int], list[list[int]]]:
    # Get aaa_base.
    comb = [a * (a - 1) // 2 for a in range(64)]

    accum = 0
    aaa_base = [0] * 64
    for a in range(64 - 1):
        accum += comb[a]
        aaa_base[a + 1] = accum

    # Get aaa_xyz.
    aaa_xyz = [[-1] * 3 for _ in range(_MAX_AAAINDEX)]

    idx = 0
    for z in range(64):
        for y in range(z):
            for x in range(y):
                aaa_xyz[idx][0] = x
                aaa_xyz[idx][1] = y
                aaa_xyz[idx][2] = z
                idx += 1

    return aaa_base, aaa_xyz

AAA_BASE, AAA_XYZ = _init_aaa()


def _pp_putanchorfirst(a: int, b: int) -> tuple[int, int]:
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

def _wsq_to_pidx24(pawn: int) -> int:
    sq = pawn

    sq = _flip_ns(sq)
    sq -= 8  # Down one row

    idx24 = (sq + (sq & 3)) >> 1
    return idx24

def _wsq_to_pidx48(pawn: int) -> int:
    sq = pawn

    sq = _flip_ns(sq)
    sq -= 8  # Down one row

    idx48 = sq
    return idx48

def _init_ppidx() -> tuple[list[list[int]], list[int], list[int]]:
    ppidx = [[-1] * 48 for _ in range(24)]
    pp_hi24 = [-1] * _MAX_PPINDEX
    pp_lo48 = [-1] * _MAX_PPINDEX

    idx = 0
    for a in range(chess.H7, chess.A2 - 1, -1):
        if _in_queenside(a):
            continue

        for b in range(a - 1, chess.A2 - 1, -1):
            anchor = 0
            loosen = 0

            anchor, loosen = _pp_putanchorfirst(a, b)

            if (anchor & 7) > 3:
                # Square on the kingside.
                anchor = _flip_we(anchor)
                loosen = _flip_we(loosen)

            i = _wsq_to_pidx24(anchor)
            j = _wsq_to_pidx48(loosen)

            if _idx_is_empty(ppidx[i][j]):
                ppidx[i][j] = idx
                pp_hi24[idx] = i
                pp_lo48[idx] = j
                idx += 1

    return ppidx, pp_hi24, pp_lo48

PPIDX, PP_HI24, PP_LO48 = _init_ppidx()


def _norm_kkindex(x: chess.Square, y: chess.Square) -> tuple[int, int]:
    if chess.square_file(x) > chess.FILE_D:
        x = _flip_we(x)
        y = _flip_we(y)

    if chess.square_rank(x) > chess.RANK_4:
        x = _flip_ns(x)
        y = _flip_ns(y)

    rowx = chess.square_rank(x)
    colx = chess.square_file(x)

    if rowx > colx:
        x = _flip_nw_se(x)
        y = _flip_nw_se(y)

    rowy = chess.square_rank(y)
    coly = chess.square_file(y)

    if rowx == colx and rowy > coly:
        x = _flip_nw_se(x)
        y = _flip_nw_se(y)

    return x, y

def _init_kkidx() -> tuple[list[list[int]], list[int], list[int]]:
    kkidx = [[-1] * 64 for _ in range(64)]
    bksq = [-1] * _MAX_KKINDEX
    wksq = [-1] * _MAX_KKINDEX
    idx = 0
    for x in range(64):
        for y in range(64):
            # Check if x to y is legal.
            if x != y and not chess.BB_KING_ATTACKS[x] & chess.BB_SQUARES[y]:
                # Normalize.
                i, j = _norm_kkindex(x, y)

                if _idx_is_empty(kkidx[i][j]):
                    kkidx[i][j] = idx
                    kkidx[x][y] = idx
                    bksq[idx] = i
                    wksq[idx] = j
                    idx += 1

    return kkidx, wksq, bksq

KKIDX, WKSQ, BKSQ = _init_kkidx()


def _kxk_pctoindex(c: _Request) -> int:
    BLOCK_Ax = 64

    ft = _flip_type(c.black_piece_squares[0], c.white_piece_squares[0])

    ws = c.white_piece_squares
    bs = c.black_piece_squares

    if (ft & 1) != 0:
        ws = [_flip_we(b) for b in ws]
        bs = [_flip_we(b) for b in bs]

    if (ft & 2) != 0:
        ws = [_flip_ns(b) for b in ws]
        bs = [_flip_ns(b) for b in bs]

    if (ft & 4) != 0:
        ws = [_flip_nw_se(b) for b in ws]
        bs = [_flip_nw_se(b) for b in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]

    if ki == -1:
        return _NOINDEX

    return ki * BLOCK_Ax + ws[1]

def _kapkb_pctoindex(c: _Request) -> int:
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
        return _NOINDEX

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = _flip_we(pawn)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)
        ba = _flip_we(ba)

    sq = pawn
    sq ^= 56  # flip_ns
    sq -= 8   # Down one row
    pslice = (sq + (sq & 3)) >> 1

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + ba

def _kabpk_pctoindex(c: _Request) -> int:
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
        pawn = _flip_we(pawn)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)
        wb = _flip_we(wb)

    pslice = _wsq_to_pidx24(pawn)

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + wb

def _kabkp_pctoindex(c: _Request) -> int:
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
        return _NOINDEX

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = _flip_we(pawn)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)
        wb = _flip_we(wb)

    sq = pawn
    sq -= 8  # Down one row
    pslice = (sq + (sq & 3)) >> 1

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa * BLOCK_D + wb

def _kaapk_pctoindex(c: _Request) -> int:
    BLOCK_C = _MAX_AAINDEX
    BLOCK_B = 64 * BLOCK_C
    BLOCK_A = 64 * BLOCK_B

    wk = c.white_piece_squares[0]
    wa = c.white_piece_squares[1]
    wa2 = c.white_piece_squares[2]
    pawn = c.white_piece_squares[3]
    bk = c.black_piece_squares[0]

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = _flip_we(pawn)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)
        wa2 = _flip_we(wa2)

    pslice = _wsq_to_pidx24(pawn)

    aa_combo = AAIDX[wa][wa2]

    if _idx_is_empty(aa_combo):
        return _NOINDEX

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + aa_combo

def _kaakp_pctoindex(c: _Request) -> int:
    BLOCK_C = _MAX_AAINDEX
    BLOCK_B = 64 * BLOCK_C
    BLOCK_A = 64 * BLOCK_B

    wk = c.white_piece_squares[0]
    wa = c.white_piece_squares[1]
    wa2 = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]
    pawn = c.black_piece_squares[1]

    if (pawn & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        pawn = _flip_we(pawn)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)
        wa2 = _flip_we(wa2)

    pawn = _flip_ns(pawn)
    pslice = _wsq_to_pidx24(pawn)

    aa_combo = AAIDX[wa][wa2]

    if _idx_is_empty(aa_combo):
        return _NOINDEX

    return pslice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + aa_combo

def _kapkp_pctoindex(c: _Request) -> int:
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
        anchor = _flip_we(anchor)
        loosen = _flip_we(loosen)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)

    m = _wsq_to_pidx24(anchor)
    n = loosen - 8
    pp_slice = m * 48 + n

    if _idx_is_empty(pp_slice):
        return _NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa

def _kappk_pctoindex(c: _Request) -> int:
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    wk = c.white_piece_squares[0]
    wa = c.white_piece_squares[1]
    pawn_a = c.white_piece_squares[2]
    pawn_b = c.white_piece_squares[3]
    bk = c.black_piece_squares[0]

    anchor, loosen = _pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        # Column is more than 3, i.e., e, f, g or h.
        anchor = _flip_we(anchor)
        loosen = _flip_we(loosen)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)

    i = _wsq_to_pidx24(anchor)
    j = _wsq_to_pidx48(loosen)

    pp_slice = PPIDX[i][j]

    if _idx_is_empty(pp_slice):
        return _NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + wa

def _kppka_pctoindex(c: _Request) -> int:
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    wk = c.white_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]
    ba = c.black_piece_squares[1]

    anchor, loosen = _pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        anchor = _flip_we(anchor)
        loosen = _flip_we(loosen)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        ba = _flip_we(ba)

    i = _wsq_to_pidx24(anchor)
    j = _wsq_to_pidx48(loosen)

    pp_slice = PPIDX[i][j]

    if _idx_is_empty(pp_slice):
        return _NOINDEX

    return pp_slice * BLOCK_A + wk * BLOCK_B + bk * BLOCK_C + ba

def _kabck_pctoindex(c: _Request) -> int:
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_A = 64 * 64 * 64
    BLOCK_B = 64 * 64
    BLOCK_C = 64

    ft = _FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & _WE_FLAG) != 0:
        ws = [_flip_we(i) for i in ws]
        bs = [_flip_we(i) for i in bs]

    if (ft & _NS_FLAG) != 0:
        ws = [_flip_ns(i) for i in ws]
        bs = [_flip_ns(i) for i in bs]

    if (ft & _NW_SE_FLAG) != 0:
        ws = [_flip_nw_se(i) for i in ws]
        bs = [_flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]

    if _idx_is_empty(ki):
        return _NOINDEX

    return ki * BLOCK_A + ws[1] * BLOCK_B + ws[2] * BLOCK_C + ws[3]

def _kabbk_pctoindex(c: _Request) -> int:
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * _MAX_AAINDEX

    ft = _FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & _WE_FLAG) != 0:
        ws = [_flip_we(i) for i in ws]
        bs = [_flip_we(i) for i in bs]

    if (ft & _NS_FLAG) != 0:
        ws = [_flip_ns(i) for i in ws]
        bs = [_flip_ns(i) for i in bs]

    if (ft & _NW_SE_FLAG) != 0:
        ws = [_flip_nw_se(i) for i in ws]
        bs = [_flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]
    ai = AAIDX[ws[2]][ws[3]]

    if _idx_is_empty(ki) or _idx_is_empty(ai):
        return _NOINDEX

    return ki * BLOCK_Ax + ai * BLOCK_Bx + ws[1]

def _kaabk_pctoindex(c: _Request) -> int:
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * _MAX_AAINDEX

    ft = _FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & _WE_FLAG) != 0:
        ws = [_flip_we(i) for i in ws]
        bs = [_flip_we(i) for i in bs]

    if (ft & _NS_FLAG) != 0:
        ws = [_flip_ns(i) for i in ws]
        bs = [_flip_ns(i) for i in bs]

    if (ft & _NW_SE_FLAG) != 0:
        ws = [_flip_nw_se(i) for i in ws]
        bs = [_flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]
    ai = AAIDX[ws[1]][ws[2]]

    if _idx_is_empty(ki) or _idx_is_empty(ai):
        return _NOINDEX

    return ki * BLOCK_Ax + ai * BLOCK_Bx + ws[3]

def _aaa_getsubi(x: int, y: int, z: int) -> int:
    bse = AAA_BASE[z]
    calc_idx = x + (y - 1) * y // 2 + bse
    return calc_idx

def _kaaak_pctoindex(c: _Request) -> int:
    N_WHITE = 4
    N_BLACK = 1
    BLOCK_Ax = _MAX_AAAINDEX

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    ft = _FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    if (ft & _WE_FLAG) != 0:
        ws = [_flip_we(i) for i in ws]
        bs = [_flip_we(i) for i in bs]

    if (ft & _NS_FLAG) != 0:
        ws = [_flip_ns(i) for i in ws]
        bs = [_flip_ns(i) for i in bs]

    if (ft & _NW_SE_FLAG) != 0:
        ws = [_flip_nw_se(i) for i in ws]
        bs = [_flip_nw_se(i) for i in bs]

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
        return _NOINDEX

    ai = _aaa_getsubi(ws[1], ws[2], ws[3])

    if _idx_is_empty(ki) or _idx_is_empty(ai):
        return _NOINDEX

    return ki * BLOCK_Ax + ai

def _kppkp_pctoindex(c: _Request) -> int:
    BLOCK_Ax = _MAX_PP48_INDEX * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    wk = c.white_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]
    pawn_c = c.black_piece_squares[1]

    if (pawn_c & 7) > 3:
        wk = _flip_we(wk)
        pawn_a = _flip_we(pawn_a)
        pawn_b = _flip_we(pawn_b)
        bk = _flip_we(bk)
        pawn_c = _flip_we(pawn_c)

    i = _flip_we(_flip_ns(pawn_a)) - 8
    j = _flip_we(_flip_ns(pawn_b)) - 8

    # Black pawn, so low indexes are more advanced.
    k = _map24_b(pawn_c)

    pp48_slice = PP48_IDX[i][j]

    if _idx_is_empty(pp48_slice):
        return _NOINDEX

    return k * BLOCK_Ax + pp48_slice * BLOCK_Bx + wk * BLOCK_Cx + bk

def _kaakb_pctoindex(c: _Request) -> int:
    N_WHITE = 3
    N_BLACK = 2
    BLOCK_Bx = 64
    BLOCK_Ax = BLOCK_Bx * _MAX_AAINDEX

    ft = _FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & _WE_FLAG) != 0:
        ws = [_flip_we(i) for i in ws]
        bs = [_flip_we(i) for i in bs]

    if (ft & _NS_FLAG) != 0:
        ws = [_flip_ns(i) for i in ws]
        bs = [_flip_ns(i) for i in bs]

    if (ft & _NW_SE_FLAG) != 0:
        ws = [_flip_nw_se(i) for i in ws]
        bs = [_flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]
    ai = AAIDX[ws[1]][ws[2]]

    if _idx_is_empty(ki) or _idx_is_empty(ai):
        return _NOINDEX

    return ki * BLOCK_Ax + ai * BLOCK_Bx + bs[1]

def _kabkc_pctoindex(c: _Request) -> int:
    N_WHITE = 3
    N_BLACK = 2

    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    ft = _FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & _WE_FLAG) != 0:
        ws = [_flip_we(i) for i in ws]
        bs = [_flip_we(i) for i in bs]

    if (ft & _NS_FLAG) != 0:
        ws = [_flip_ns(i) for i in ws]
        bs = [_flip_ns(i) for i in bs]

    if (ft & _NW_SE_FLAG) != 0:
        ws = [_flip_nw_se(i) for i in ws]
        bs = [_flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX [black king] [white king]

    if _idx_is_empty(ki):
        return _NOINDEX

    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + ws[2] * BLOCK_Cx + bs[1]

def _kpkp_pctoindex(c: _Request) -> int:
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.black_piece_squares[1]

    anchor = pawn_a
    loosen = pawn_b

    if (anchor & 7) > 3:
        anchor = _flip_we(anchor)
        loosen = _flip_we(loosen)
        wk = _flip_we(wk)
        bk = _flip_we(bk)

    m = _wsq_to_pidx24(anchor)
    n = loosen - 8

    pp_slice = m * 48 + n

    if _idx_is_empty(pp_slice):
        return _NOINDEX

    return pp_slice * BLOCK_Ax + wk * BLOCK_Bx + bk

def _kppk_pctoindex(c: _Request) -> int:
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64
    wk = c.white_piece_squares[0]
    pawn_a = c.white_piece_squares[1]
    pawn_b = c.white_piece_squares[2]
    bk = c.black_piece_squares[0]

    anchor, loosen = _pp_putanchorfirst(pawn_a, pawn_b)

    if (anchor & 7) > 3:
        anchor = _flip_we(anchor)
        loosen = _flip_we(loosen)
        wk = _flip_we(wk)
        bk = _flip_we(bk)

    i = _wsq_to_pidx24(anchor)
    j = _wsq_to_pidx48(loosen)

    pp_slice = PPIDX[i][j]

    if _idx_is_empty(pp_slice):
        return _NOINDEX

    return pp_slice * BLOCK_Ax + wk * BLOCK_Bx + bk

def _kapk_pctoindex(c: _Request) -> int:
    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    pawn = c.white_piece_squares[2]
    wa = c.white_piece_squares[1]
    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]

    if not (chess.A2 <= pawn < chess.A8):
        return _NOINDEX

    if (pawn & 7) > 3:
        pawn = _flip_we(pawn)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)

    sq = pawn
    sq ^= 56  # flip_ns
    sq -= 8   # Down one row
    pslice = ((sq + (sq & 3)) >> 1)

    return pslice * BLOCK_Ax + wk * BLOCK_Bx + bk * BLOCK_Cx + wa

def _kabk_pctoindex(c: _Request) -> int:
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    ft = _flip_type(c.black_piece_squares[0], c.white_piece_squares[0])

    ws = c.white_piece_squares
    bs = c.black_piece_squares

    if (ft & 1) != 0:
        ws = [_flip_we(b) for b in ws]
        bs = [_flip_we(b) for b in bs]

    if (ft & 2) != 0:
        ws = [_flip_ns(b) for b in ws]
        bs = [_flip_ns(b) for b in bs]

    if (ft & 4) != 0:
        ws = [_flip_nw_se(b) for b in ws]
        bs = [_flip_nw_se(b) for b in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]

    if _idx_is_empty(ki):
        return _NOINDEX

    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + ws[2]

def _kakp_pctoindex(c: _Request) -> int:
    BLOCK_Ax = 64 * 64 * 64
    BLOCK_Bx = 64 * 64
    BLOCK_Cx = 64

    pawn = c.black_piece_squares[1]
    wa = c.white_piece_squares[1]
    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]

    if not (chess.A2 <= pawn < chess.A8):
        return _NOINDEX

    if (pawn & 7) > 3:
        pawn = _flip_we(pawn)
        wk = _flip_we(wk)
        bk = _flip_we(bk)
        wa = _flip_we(wa)

    sq = pawn
    sq -= 8  # Down one row
    pslice = (sq + (sq & 3)) >> 1

    return pslice * BLOCK_Ax + wk * BLOCK_Bx + bk * BLOCK_Cx + wa

def _kaak_pctoindex(c: _Request) -> int:
    N_WHITE = 3
    N_BLACK = 1
    BLOCK_Ax = _MAX_AAINDEX

    ft = _FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:N_WHITE]
    bs = c.black_piece_squares[:N_BLACK]

    if (ft & _WE_FLAG) != 0:
        ws = [_flip_we(i) for i in ws]
        bs = [_flip_we(i) for i in bs]

    if (ft & _NS_FLAG) != 0:
        ws = [_flip_ns(i) for i in ws]
        bs = [_flip_ns(i) for i in bs]

    if (ft & _NW_SE_FLAG) != 0:
        ws = [_flip_nw_se(i) for i in ws]
        bs = [_flip_nw_se(i) for i in bs]

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]
    ai = AAIDX[ws[1]][ws[2]]

    if _idx_is_empty(ki) or _idx_is_empty(ai):
        return _NOINDEX

    return ki * BLOCK_Ax + ai

def _kakb_pctoindex(c: _Request) -> int:
    BLOCK_Ax = 64 * 64
    BLOCK_Bx = 64

    ft = _FLIPT[c.black_piece_squares[0]][c.white_piece_squares[0]]

    ws = c.white_piece_squares[:]
    bs = c.black_piece_squares[:]

    if (ft & 1) != 0:
        ws[0] = _flip_we(ws[0])
        ws[1] = _flip_we(ws[1])
        bs[0] = _flip_we(bs[0])
        bs[1] = _flip_we(bs[1])

    if (ft & 2) != 0:
        ws[0] = _flip_ns(ws[0])
        ws[1] = _flip_ns(ws[1])
        bs[0] = _flip_ns(bs[0])
        bs[1] = _flip_ns(bs[1])

    if (ft & 4) != 0:
        ws[0] = _flip_nw_se(ws[0])
        ws[1] = _flip_nw_se(ws[1])
        bs[0] = _flip_nw_se(bs[0])
        bs[1] = _flip_nw_se(bs[1])

    ki = KKIDX[bs[0]][ws[0]]  # KKIDX[black king][white king]

    if _idx_is_empty(ki):
        return _NOINDEX

    return ki * BLOCK_Ax + ws[1] * BLOCK_Bx + bs[1]

def _kpk_pctoindex(c: _Request) -> int:
    BLOCK_A = 64 * 64
    BLOCK_B = 64

    pawn = c.white_piece_squares[1]
    wk = c.white_piece_squares[0]
    bk = c.black_piece_squares[0]

    if not (chess.A2 <= pawn < chess.A8):
        return _NOINDEX

    if (pawn & 7) > 3:
        pawn = _flip_we(pawn)
        wk = _flip_we(wk)
        bk = _flip_we(bk)

    sq = pawn
    sq ^= 56  # flip_ns
    sq -= 8   # Down one row
    pslice = ((sq + (sq & 3)) >> 1)

    res = pslice * BLOCK_A + wk * BLOCK_B + bk
    return res

def _kpppk_pctoindex(c: _Request) -> int:
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

    if _idx_is_empty(ppp48_slice):
        wk = _flip_we(wk)
        pawn_a = _flip_we(pawn_a)
        pawn_b = _flip_we(pawn_b)
        pawn_c = _flip_we(pawn_c)
        bk = _flip_we(bk)

    i = pawn_a - 8
    j = pawn_b - 8
    k = pawn_c - 8

    ppp48_slice = PPP48_IDX[i][j][k]

    if _idx_is_empty(ppp48_slice):
        return _NOINDEX

    return ppp48_slice * BLOCK_A + wk * BLOCK_B + bk


class _EndgameKey:
    def __init__(self, maxindex: int, slice_n: int, pctoi: Callable[[_Request], int]):
        self.maxindex = maxindex
        self.slice_n = slice_n
        self.pctoi = pctoi

_EGKEY = {
    "kqk": _EndgameKey(_MAX_KXK, 1, _kxk_pctoindex),
    "krk": _EndgameKey(_MAX_KXK, 1, _kxk_pctoindex),
    "kbk": _EndgameKey(_MAX_KXK, 1, _kxk_pctoindex),
    "knk": _EndgameKey(_MAX_KXK, 1, _kxk_pctoindex),
    "kpk": _EndgameKey(_MAX_kpk, 24, _kpk_pctoindex),

    "kqkq": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),
    "kqkr": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),
    "kqkb": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),
    "kqkn": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),

    "krkr": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),
    "krkb": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),
    "krkn": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),

    "kbkb": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),
    "kbkn": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),

    "knkn": _EndgameKey(_MAX_kakb, 1, _kakb_pctoindex),

    "kqqk": _EndgameKey(_MAX_kaak, 1, _kaak_pctoindex),
    "kqrk": _EndgameKey(_MAX_kabk, 1, _kabk_pctoindex),
    "kqbk": _EndgameKey(_MAX_kabk, 1, _kabk_pctoindex),
    "kqnk": _EndgameKey(_MAX_kabk, 1, _kabk_pctoindex),

    "krrk": _EndgameKey(_MAX_kaak, 1, _kaak_pctoindex),
    "krbk": _EndgameKey(_MAX_kabk, 1, _kabk_pctoindex),
    "krnk": _EndgameKey(_MAX_kabk, 1, _kabk_pctoindex),

    "kbbk": _EndgameKey(_MAX_kaak, 1, _kaak_pctoindex),
    "kbnk": _EndgameKey(_MAX_kabk, 1, _kabk_pctoindex),

    "knnk": _EndgameKey(_MAX_kaak, 1, _kaak_pctoindex),
    "kqkp": _EndgameKey(_MAX_kakp, 24, _kakp_pctoindex),
    "krkp": _EndgameKey(_MAX_kakp, 24, _kakp_pctoindex),
    "kbkp": _EndgameKey(_MAX_kakp, 24, _kakp_pctoindex),
    "knkp": _EndgameKey(_MAX_kakp, 24, _kakp_pctoindex),

    "kqpk": _EndgameKey(_MAX_kapk, 24, _kapk_pctoindex),
    "krpk": _EndgameKey(_MAX_kapk, 24, _kapk_pctoindex),
    "kbpk": _EndgameKey(_MAX_kapk, 24, _kapk_pctoindex),
    "knpk": _EndgameKey(_MAX_kapk, 24, _kapk_pctoindex),

    "kppk": _EndgameKey(_MAX_kppk, _MAX_PPINDEX, _kppk_pctoindex),

    "kpkp": _EndgameKey(_MAX_kpkp, _MAX_PpINDEX, _kpkp_pctoindex),

    "kppkp": _EndgameKey(_MAX_kppkp, 24 * _MAX_PP48_INDEX, _kppkp_pctoindex),

    "kbbkr": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "kbbkb": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "knnkb": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "knnkn": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),

    "kqqqk": _EndgameKey(_MAX_kaaak, 1, _kaaak_pctoindex),
    "kqqrk": _EndgameKey(_MAX_kaabk, 1, _kaabk_pctoindex),
    "kqqbk": _EndgameKey(_MAX_kaabk, 1, _kaabk_pctoindex),
    "kqqnk": _EndgameKey(_MAX_kaabk, 1, _kaabk_pctoindex),
    "kqrrk": _EndgameKey(_MAX_kabbk, 1, _kabbk_pctoindex),
    "kqrbk": _EndgameKey(_MAX_kabck, 1, _kabck_pctoindex),
    "kqrnk": _EndgameKey(_MAX_kabck, 1, _kabck_pctoindex),
    "kqbbk": _EndgameKey(_MAX_kabbk, 1, _kabbk_pctoindex),
    "kqbnk": _EndgameKey(_MAX_kabck, 1, _kabck_pctoindex),
    "kqnnk": _EndgameKey(_MAX_kabbk, 1, _kabbk_pctoindex),
    "krrrk": _EndgameKey(_MAX_kaaak, 1, _kaaak_pctoindex),
    "krrbk": _EndgameKey(_MAX_kaabk, 1, _kaabk_pctoindex),
    "krrnk": _EndgameKey(_MAX_kaabk, 1, _kaabk_pctoindex),
    "krbbk": _EndgameKey(_MAX_kabbk, 1, _kabbk_pctoindex),
    "krbnk": _EndgameKey(_MAX_kabck, 1, _kabck_pctoindex),
    "krnnk": _EndgameKey(_MAX_kabbk, 1, _kabbk_pctoindex),
    "kbbbk": _EndgameKey(_MAX_kaaak, 1, _kaaak_pctoindex),
    "kbbnk": _EndgameKey(_MAX_kaabk, 1, _kaabk_pctoindex),
    "kbnnk": _EndgameKey(_MAX_kabbk, 1, _kabbk_pctoindex),
    "knnnk": _EndgameKey(_MAX_kaaak, 1, _kaaak_pctoindex),
    "kqqkq": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "kqqkr": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "kqqkb": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "kqqkn": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "kqrkq": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqrkr": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqrkb": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqrkn": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqbkq": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqbkr": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqbkb": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqbkn": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqnkq": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqnkr": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqnkb": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kqnkn": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "krrkq": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "krrkr": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "krrkb": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "krrkn": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "krbkq": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "krbkr": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "krbkb": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "krbkn": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "krnkq": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "krnkr": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "krnkb": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "krnkn": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kbbkq": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "kbbkn": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "kbnkq": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kbnkr": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kbnkb": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "kbnkn": _EndgameKey(_MAX_kabkc, 1, _kabkc_pctoindex),
    "knnkq": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),
    "knnkr": _EndgameKey(_MAX_kaakb, 1, _kaakb_pctoindex),

    "kqqpk": _EndgameKey(_MAX_kaapk, 24, _kaapk_pctoindex),
    "kqrpk": _EndgameKey(_MAX_kabpk, 24, _kabpk_pctoindex),
    "kqbpk": _EndgameKey(_MAX_kabpk, 24, _kabpk_pctoindex),
    "kqnpk": _EndgameKey(_MAX_kabpk, 24, _kabpk_pctoindex),
    "krrpk": _EndgameKey(_MAX_kaapk, 24, _kaapk_pctoindex),
    "krbpk": _EndgameKey(_MAX_kabpk, 24, _kabpk_pctoindex),
    "krnpk": _EndgameKey(_MAX_kabpk, 24, _kabpk_pctoindex),
    "kbbpk": _EndgameKey(_MAX_kaapk, 24, _kaapk_pctoindex),
    "kbnpk": _EndgameKey(_MAX_kabpk, 24, _kabpk_pctoindex),
    "knnpk": _EndgameKey(_MAX_kaapk, 24, _kaapk_pctoindex),

    "kqppk": _EndgameKey(_MAX_kappk, _MAX_PPINDEX, _kappk_pctoindex),
    "krppk": _EndgameKey(_MAX_kappk, _MAX_PPINDEX, _kappk_pctoindex),
    "kbppk": _EndgameKey(_MAX_kappk, _MAX_PPINDEX, _kappk_pctoindex),
    "knppk": _EndgameKey(_MAX_kappk, _MAX_PPINDEX, _kappk_pctoindex),

    "kqpkq": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "kqpkr": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "kqpkb": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "kqpkn": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "krpkq": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "krpkr": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "krpkb": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "krpkn": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "kbpkq": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "kbpkr": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "kbpkb": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "kbpkn": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "knpkq": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "knpkr": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "knpkb": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "knpkn": _EndgameKey(_MAX_kapkb, 24, _kapkb_pctoindex),
    "kppkq": _EndgameKey(_MAX_kppka, _MAX_PPINDEX, _kppka_pctoindex),
    "kppkr": _EndgameKey(_MAX_kppka, _MAX_PPINDEX, _kppka_pctoindex),
    "kppkb": _EndgameKey(_MAX_kppka, _MAX_PPINDEX, _kppka_pctoindex),
    "kppkn": _EndgameKey(_MAX_kppka, _MAX_PPINDEX, _kppka_pctoindex),

    "kqqkp": _EndgameKey(_MAX_kaakp, 24, _kaakp_pctoindex),
    "kqrkp": _EndgameKey(_MAX_kabkp, 24, _kabkp_pctoindex),
    "kqbkp": _EndgameKey(_MAX_kabkp, 24, _kabkp_pctoindex),
    "kqnkp": _EndgameKey(_MAX_kabkp, 24, _kabkp_pctoindex),
    "krrkp": _EndgameKey(_MAX_kaakp, 24, _kaakp_pctoindex),
    "krbkp": _EndgameKey(_MAX_kabkp, 24, _kabkp_pctoindex),
    "krnkp": _EndgameKey(_MAX_kabkp, 24, _kabkp_pctoindex),
    "kbbkp": _EndgameKey(_MAX_kaakp, 24, _kaakp_pctoindex),
    "kbnkp": _EndgameKey(_MAX_kabkp, 24, _kabkp_pctoindex),
    "knnkp": _EndgameKey(_MAX_kaakp, 24, _kaakp_pctoindex),

    "kqpkp": _EndgameKey(_MAX_kapkp, _MAX_PpINDEX, _kapkp_pctoindex),
    "krpkp": _EndgameKey(_MAX_kapkp, _MAX_PpINDEX, _kapkp_pctoindex),
    "kbpkp": _EndgameKey(_MAX_kapkp, _MAX_PpINDEX, _kapkp_pctoindex),
    "knpkp": _EndgameKey(_MAX_kapkp, _MAX_PpINDEX, _kapkp_pctoindex),

    "kpppk": _EndgameKey(_MAX_kpppk, _MAX_PPP48_INDEX, _kpppk_pctoindex),
}


def _sortlists(ws: list[int], wp: list[int]) -> tuple[list[int], list[int]]:
    z = sorted(zip(wp, ws), key=lambda x: x[0], reverse=True)
    wp2, ws2 = zip(*z)
    return list(ws2), list(wp2)

def _egtb_block_unpack(side: int, n: int, bp: bytes) -> list[int]:
    return [_dtm_unpack(side, i) for i in bp[:n]]

def _split_index(i: int) -> tuple[int, int]:
    return divmod(i, _ENTRIES_PER_BLOCK)


_tb_DRAW = 0
_tb_WMATE = 1
_tb_BMATE = 2
_tb_FORBID = 3
_tb_UNKNOWN = 7
_iDRAW = _tb_DRAW
_iWMATE = _tb_WMATE
_iBMATE = _tb_BMATE
_iFORBID = _tb_FORBID

_iDRAWt = _tb_DRAW | 4
_iWMATEt = _tb_WMATE | 4
_iBMATEt = _tb_BMATE | 4


def _opp(side: int) -> int:
    return 1 if side == 0 else 0

def _unpackdist(d: int) -> tuple[int, int]:
    return d >> _PLYSHIFT, d & _INFOMASK

def _dtm_unpack(stm: int, packed: int) -> int:
    p = packed

    if p in [_iDRAW, _iFORBID]:
        return p

    info = p & 3
    store = p >> 2

    if stm == 0:
        if info == _iWMATE:
            moves = store + 1
            plies = moves * 2 - 1
            prefx = info
        elif info == _iBMATE:
            moves = store
            plies = moves * 2
            prefx = info
        elif info == _iDRAW:
            moves = store + 1 + 63
            plies = moves * 2 - 1
            prefx = _iWMATE
        elif info == _iFORBID:
            moves = store + 63
            plies = moves * 2
            prefx = _iBMATE
        else:
            plies = 0
            prefx = 0

        ret = prefx | (plies << 3)
    else:
        if info == _iBMATE:
            moves = store + 1
            plies = moves * 2 - 1
            prefx = info
        elif info == _iWMATE:
            moves = store
            plies = moves * 2
            prefx = info
        elif info == _iDRAW:
            if store == 63:
                # Exception: no position in the 5-man TBs needs to store 63 for
                # iBMATE. It is then just used to indicate iWMATE.
                store += 1

                moves = store + 63
                plies = moves * 2
                prefx = _iWMATE
            else:
                moves = store + 1 + 63
                plies = moves * 2 - 1
                prefx = _iBMATE
        elif info == _iFORBID:
            moves = store + 63
            plies = moves * 2
            prefx = _iWMATE
        else:
            plies = 0
            prefx = 0

        ret = prefx | (plies << 3)

    return ret


class MissingTableError(KeyError):
    """Can not probe position because a required table is missing."""


class _TableBlock:
    pcache: list[int]

    def __init__(self, egkey: str, side: int, offset: int, age: int):
        self.egkey = egkey
        self.side = side
        self.offset = offset
        self.age = age


class _Request:
    egkey: str
    white_piece_squares: list[int]
    white_piece_types: list[int]
    black_piece_squares: list[int]
    black_piece_types: list[int]
    is_reversed: bool

    def __init__(self, white_squares: list[int], white_types: list[chess.PieceType], black_squares: list[int], black_types: list[chess.PieceType], side: int):
        self.white_squares, self.white_types = _sortlists(white_squares, white_types)
        self.black_squares, self.black_types = _sortlists(black_squares, black_types)
        self.realside = side
        self.side = side


@dataclasses.dataclass
class _ZipInfo:
    extraoffset: int
    totalblocks: int
    blockindex: list[int]


class PythonTablebase:
    """Provides access to Gaviota tablebases using pure Python code."""

    def __init__(self) -> None:
        self._available_tables: dict[str, str] = {}

        self._streams: dict[str, BinaryIO] = {}
        self._zipinfo: dict[str, _ZipInfo] = {}

        self._block_cache: dict[tuple[str, int, int], _TableBlock] = {}
        self._block_age = 0

    def add_directory(self, directory: _StrPath) -> None:
        """
        Adds *.gtb.cp4* tables from a directory. The relevant files are lazily
        opened when the tablebase is actually probed.
        """
        directory = os.path.abspath(os.fspath(directory))
        if not os.path.isdir(directory):
            raise IOError(f"not a directory: {directory!r}")

        for tbfile in fnmatch.filter(os.listdir(directory), "*.gtb.cp4"):
            self._available_tables[os.path.basename(tbfile).replace(".gtb.cp4", "")] = os.path.join(directory, tbfile)

    def probe_dtm(self, board: chess.Board) -> int:
        """
        Probes for depth to mate information.

        The absolute value is the number of half-moves until forced mate
        (or ``0`` in drawn or checkmated positions). The value is positive if
        the side to move is winning, otherwise it is negative or 0.

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
        if board.piece_count() > 5:
            raise KeyError(f"gaviota tables support up to 5 pieces, not {board.piece_count()}: {board.fen()}")

        # KvK is a draw.
        if board.occupied == board.kings:
            return 0

        # Resolve en passant.
        dtm = self._probe_dtm_no_ep(board)
        for move in board.generate_legal_ep():
            try:
                board.push(move)

                if board.is_checkmate():
                    child_dtm = 1
                else:
                    child_dtm = -self._probe_dtm_no_ep(board)
                    if child_dtm > 0:
                        child_dtm += 1
                    elif child_dtm < 0:
                        child_dtm -= 1

                dtm = min(dtm, child_dtm) if dtm * child_dtm > 0 else max(dtm, child_dtm)
            finally:
                board.pop()
        return dtm

    def _probe_dtm_no_ep(self, board: chess.Board) -> int:
        # Prepare the tablebase request.
        white_squares = list(chess.SquareSet(board.occupied_co[chess.WHITE]))
        white_types = [typing.cast(chess.PieceType, board.piece_type_at(sq)) for sq in white_squares]
        black_squares = list(chess.SquareSet(board.occupied_co[chess.BLACK]))
        black_types = [typing.cast(chess.PieceType, board.piece_type_at(sq)) for sq in black_squares]
        side = 0 if (board.turn == chess.WHITE) else 1
        req = _Request(white_squares, white_types, black_squares, black_types, side)

        # Probe.
        dtm = self._tb_probe(req)
        ply, res = _unpackdist(dtm)

        if res == _iWMATE:
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
        elif res == _iBMATE:
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

    def get_dtm(self, board: chess.Board, default: int | None = None) -> int | None:
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

    def get_wdl(self, board: chess.Board, default: int | None = None) -> int | None:
        try:
            return self.probe_wdl(board)
        except KeyError:
            return default

    def _setup_tablebase(self, req: _Request) -> BinaryIO:
        white_letters = "".join(chess.piece_symbol(i) for i in req.white_types)
        black_letters = "".join(chess.piece_symbol(i) for i in req.black_types)

        if (white_letters + black_letters) in self._available_tables:
            req.is_reversed = False
            req.egkey = white_letters + black_letters
            req.white_piece_squares = req.white_squares
            req.white_piece_types = req.white_types
            req.black_piece_squares = req.black_squares
            req.black_piece_types = req.black_types
        elif (black_letters + white_letters) in self._available_tables:
            req.is_reversed = True
            req.egkey = black_letters + white_letters
            req.white_piece_squares = [_flip_ns(s) for s in req.black_squares]
            req.white_piece_types = req.black_types
            req.black_piece_squares = [_flip_ns(s) for s in req.white_squares]
            req.black_piece_types = req.white_types
            req.side = _opp(req.side)
        else:
            raise MissingTableError(f"no gaviota table available for: {white_letters.upper()}v{black_letters.upper()}")

        return self._open_tablebase(req)

    def _open_tablebase(self, req: _Request) -> BinaryIO:
        stream = self._streams.get(req.egkey)

        if stream is None:
            path = self._available_tables[req.egkey]
            stream = open(path, "rb")
            self._egtb_loadindexes(req.egkey, stream)
            self._streams[req.egkey] = stream

        return stream

    def close(self) -> None:
        """Closes all loaded tables."""
        self._available_tables.clear()

        self._zipinfo.clear()

        self._block_age = 0
        self._block_cache.clear()

        while self._streams:
            _, stream = self._streams.popitem()
            stream.close()

    def _egtb_block_getnumber(self, req: _Request, idx: int) -> int:
        maxindex = _EGKEY[req.egkey].maxindex

        blocks_per_side = 1 + (maxindex - 1) // _ENTRIES_PER_BLOCK
        block_in_side = idx // _ENTRIES_PER_BLOCK

        return req.side * blocks_per_side + block_in_side

    def _egtb_block_getsize(self, req: _Request, idx: int) -> int:
        blocksz = _ENTRIES_PER_BLOCK
        maxindex = _EGKEY[req.egkey].maxindex
        block = idx // blocksz
        offset = block * blocksz

        if (offset + blocksz) > maxindex:
            return maxindex - offset  # Last block size
        else:
            return blocksz  # Size of a normal block

    def _tb_probe(self, req: _Request) -> int:
        stream = self._setup_tablebase(req)
        idx = _EGKEY[req.egkey].pctoi(req)
        offset, remainder = _split_index(idx)

        t = self._block_cache.get((req.egkey, offset, req.side))

        if t is None:
            t = _TableBlock(req.egkey, req.side, offset, self._block_age)

            block = self._egtb_block_getnumber(req, idx)
            n = self._egtb_block_getsize(req, idx)
            z = self._egtb_block_getsize_zipped(req.egkey, block)

            self._egtb_block_park(req.egkey, block, stream)
            buffer_zipped: bytearray | bytes = stream.read(z)

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

            t.pcache = _egtb_block_unpack(req.side, n, buffer_packed)

            # Update LRU block cache.
            self._block_cache[(t.egkey, t.offset, t.side)] = t
            if len(self._block_cache) > 128:
                lru_cache_key = min(self._block_cache, key=lambda cache_key: self._block_cache[cache_key].age)
                del self._block_cache[lru_cache_key]
        else:
            t.age = self._block_age

        self._block_age += 1
        dtm = t.pcache[remainder]

        return dtm

    def _egtb_loadindexes(self, egkey: str, stream: BinaryIO) -> _ZipInfo:
        zipinfo = self._zipinfo.get(egkey)

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

            zipinfo = _ZipInfo(extraoffset=0, totalblocks=n_idx, blockindex=p)
            self._zipinfo[egkey] = zipinfo

        return zipinfo

    def _egtb_block_getsize_zipped(self, egkey: str, block: int) -> int:
        i = self._zipinfo[egkey].blockindex[block]
        j = self._zipinfo[egkey].blockindex[block + 1]
        return j - i

    def _egtb_block_park(self, egkey: str, block: int, stream: BinaryIO) -> int:
        i = self._zipinfo[egkey].blockindex[block]
        i += self._zipinfo[egkey].extraoffset
        stream.seek(i)
        return i

    def __enter__(self) -> PythonTablebase:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        self.close()


class NativeTablebase:
    """
    Provides access to Gaviota tablebases via the shared library libgtb.
    Has the same interface as :class:`~chess.gaviota.PythonTablebase`.
    """

    def __init__(self, libgtb: ctypes.CDLL) -> None:
        self._paths: list[str] = []

        self._libgtb = libgtb
        self._libgtb.tb_init.restype = ctypes.c_char_p
        self._libgtb.tb_restart.restype = ctypes.c_char_p
        self._libgtb.tbpaths_getmain.restype = ctypes.c_char_p
        self._libgtb.tb_probe_hard.argtypes = [
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

        if self._libgtb.tb_is_initialized():
            raise RuntimeError("only one gaviota instance can be initialized at a time")

        self._tbcache_restart(1024 * 1024, 50)

    def add_directory(self, directory: _StrPath) -> None:
        directory = os.fspath(directory)
        if not os.path.isdir(directory):
            raise IOError(f"not a directory: {directory!r}")

        self._paths.append(directory)
        self._tb_restart()

    def _tb_restart(self) -> None:
        self._c_paths = (ctypes.c_char_p * len(self._paths))()
        self._c_paths[:] = [path.encode("utf-8") for path in self._paths]

        verbosity = ctypes.c_int(1)
        compression_scheme = ctypes.c_int(4)

        ret = self._libgtb.tb_restart(verbosity, compression_scheme, self._c_paths)
        if ret:
            LOGGER.debug(ret.decode("utf-8"))

        LOGGER.debug("Main path has been set to %r", self._libgtb.tbpaths_getmain().decode("utf-8"))

        av = self._libgtb.tb_availability()
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
        self._libgtb.tbcache_restart(ctypes.c_size_t(cache_mem), ctypes.c_int(wdl_fraction))

    def probe_dtm(self, board: chess.Board) -> int:
        return self._probe_hard(board)

    def probe_wdl(self, board: chess.Board) -> int:
        return self._probe_hard(board, wdl_only=True)

    def get_dtm(self, board: chess.Board, default: int | None = None) -> int | None:
        try:
            return self.probe_dtm(board)
        except KeyError:
            return default

    def get_wdl(self, board: chess.Board, default: int | None = None) -> int | None:
        try:
            return self.probe_wdl(board)
        except KeyError:
            return default

    def _probe_hard(self, board: chess.Board, wdl_only: bool = False) -> int:
        if board.is_insufficient_material():
            return 0

        if board.castling_rights:
            raise KeyError(f"gaviota tables do not contain positions with castling rights: {board.fen()}")

        if board.piece_count() > 5:
            raise KeyError(f"gaviota tables support up to 5 pieces, not {board.piece_count()}: {board.fen()}")

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
            ret = self._libgtb.tb_probe_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info), ctypes.byref(pliestomate))
            dtm = int(pliestomate.value)
        else:
            ret = self._libgtb.tb_probe_WDL_hard(stm, ep_square, castling, c_ws, c_bs, c_wp, c_bp, ctypes.byref(info))
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
        self._paths = []

        if self._libgtb.tb_is_initialized():
            self._libgtb.tbcache_done()
            self._libgtb.tb_done()

    def __enter__(self) -> NativeTablebase:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        self.close()


def open_tablebase_native(directory: _StrPath, *, libgtb: str | None = None, LibraryLoader: ctypes.LibraryLoader[ctypes.CDLL] = ctypes.cdll) -> NativeTablebase:
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


def open_tablebase(directory: _StrPath, *, libgtb: str | None = None, LibraryLoader: ctypes.LibraryLoader[ctypes.CDLL] = ctypes.cdll) -> NativeTablebase | PythonTablebase:
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
