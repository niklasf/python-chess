"""Pure-Python prober for the *chesstb* endgame tablebase format
(WDL ``.lzw`` / DTZ ``.lzdtz`` / DTC ``.lzdtc`` / DTM ``.lzdtm``
/ DTM50 ``.lzdtm50``).

Upstream: https://github.com/noobpwnftw/chesstb

Shaped like :mod:`chess.syzygy`: a :class:`Tablebase` opens a directory of
table files and answers WDL / DTZ / DTC / DTM / DTM50 queries.

Every ``probe_*`` distance is signed from the side to move: ``+N`` toward a win,
``-N`` toward a loss, ``0`` for no decisive result -- a draw, a clock that has
taken the win, or a mate already on the board. :meth:`Tablebase.probe` keeps
every class field explicit for callers wanting the class outright.

A :class:`Tablebase` is safe to share between threads and probe concurrently.
"""
from __future__ import annotations

import array
import collections
import contextlib
import importlib
import lzma
import mmap
import os
import struct
import sys
import threading
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Tuple, Type, Union

import chess

try:
    _lz4_block: Any = importlib.import_module("lz4.block")
except ImportError:
    _lz4_block = None

__all__ = ["Tablebase", "ProbeResult", "MissingTableError", "open_tablebase"]

#: :attr:`PieceConfig.cache_key`. A 'p' or 'r' material shares its plain
#: twin's ``min_key``, so the marks join the key.
CacheKey = Tuple[int, bool, int]

#: One material's key: see :func:`full_material_key`.
MaterialKey = Tuple[int, bool, int]
# The uint32 table header reserves its low two bits for the table number.
_PACKED_MATERIAL_KEY_MASK = 0x3FFFFFFF


def side_index(color: chess.Color) -> int:
    """0 for white, 1 for black, as the table format orders them."""
    return 0 if color == chess.WHITE else 1


# --- Square transforms (src/probe/position_index.cpp) ---

def apply_transform(bb: int, t: int) -> int:
    """Symmetry transform mask on every square of a bitboard: 1 mirrors the
    files, 2 the ranks, 4 then the a1-h8 diagonal."""
    if t & 1:
        bb = chess.flip_horizontal(bb)
    if t & 2:
        bb = chess.flip_vertical(bb)
    if t & 4:
        bb = chess.flip_diagonal(bb)
    return bb


SYM_NONE = 0
SYM_FILE_MIRROR = 1
SYM_DIHEDRAL_8 = 2

# White king squares of the slices: files a-d under the file mirror, the
# a1-d1-d4 triangle under all eight symmetries.
_ANCHOR_FILE_MIRROR = 0x0F0F0F0F0F0F0F0F
_ANCHOR_TRIANGLE = 0x00000000080C0E0F
_MAIN_DIAG = 0x8040201008040201
_ABOVE_DIAG = 0x7F3F1F0F07030100

# --- Binomials C(n, k), n <= 64, k <= 7 ---
_BINOM = [[0] * 8 for _ in range(65)]
for _k in range(65):
    _BINOM[_k][0] = 1
    for _n in range(1, 8):
        _BINOM[_k][_n] = 0 if _n > _k else _BINOM[_k - 1][_n - 1] + _BINOM[_k - 1][_n]


def binom(n: int, k: int) -> int:
    if k < 0 or k > 7 or n < 0 or n > 64:
        return 0
    return _BINOM[n][k]


_MAT_WEIGHT = {  # (color, type) -> base-9 digit weight, P..Q for white then black; kings 0
    (c, t): 0 if t == chess.KING else 9 ** (t - chess.PAWN + (0 if c == chess.WHITE else 5))
    for c in chess.COLORS for t in chess.PIECE_TYPES
}


def full_material_key(pieces: List[Tuple[chess.Color, chess.PieceType]], has_pair: bool = False,
                      castling_rights: Tuple[int, int] = (0, 0)) -> MaterialKey:
    """The base-9 count word, then the pair flag and rights code as
    tiebreaks. KRKr and KrKR differ only in the code, so compare these whole.
    Rooks holding a right count in the word, so KrK orders ahead of KKr; the
    pair's pawns don't, as one of each color can't tip it."""
    w, b = castling_rights
    word = (sum(_MAT_WEIGHT[(c, t)] for c, t in pieces)
            + w * _MAT_WEIGHT[(chess.WHITE, chess.ROOK)] + b * _MAT_WEIGHT[(chess.BLACK, chess.ROOK)])
    return (word, has_pair, w * 3 + b)


# --- Piece_Config (src/chess/piece_config.h): white is the stronger side ---
_STRENGTH = {chess.QUEEN: 900, chess.ROOK: 500, chess.BISHOP: 330, chess.KNIGHT: 320,
             chess.PAWN: 100, chess.KING: 0}
_TYPE_ORDER = {chess.KING: 0, chess.QUEEN: 1, chess.ROOK: 2, chess.BISHOP: 3, chess.KNIGHT: 4, chess.PAWN: 5}


def _composition_key(pieces: List[Tuple[chess.Color, chess.PieceType]],
                     color: chess.Color) -> List[int]:
    """Piece counts for `color` by type: the side-ordering tiebreak when
    strengths are equal."""
    counts = [0] * 7
    for c, t in pieces:
        if c == color:
            counts[t] += 1
    return counts


class PieceConfig:
    """Canonical material. `pieces` lists the (color, type) of the free men,
    white's first. `has_pair` marks an opposing pawn pair ('p'), indexed
    jointly and left out of `pieces`."""

    __slots__ = ("pieces", "has_pair", "castling_rights", "base_key", "mirr_key",
                 "mirrored", "has_castling", "castling_code", "min_key",
                 "cache_key", "num_pieces", "is_bare_kings")

    def __init__(self, pieces: List[Tuple[chess.Color, chess.PieceType]],
                 has_pair: bool = False, castling_rights: Tuple[int, int] = (0, 0)):
        wr, br = castling_rights
        ws = sum(_STRENGTH[t] for c, t in pieces if c == chess.WHITE)
        bs = sum(_STRENGTH[t] for c, t in pieces if c == chess.BLACK)
        ws += wr * _STRENGTH[chess.ROOK]
        bs += br * _STRENGTH[chess.ROOK]
        swap = bs > ws
        if bs == ws:
            wkey = _composition_key(pieces, chess.WHITE)
            bkey = _composition_key(pieces, chess.BLACK)
            wkey[chess.ROOK] += wr
            bkey[chess.ROOK] += br
            # Counts compared from KING down to PAWN.
            if wkey != bkey:
                swap = bkey[::-1] > wkey[::-1]
            else:
                # Same men both sides: order by which side's rook kept its right.
                swap = wr > br
        if swap:
            pieces = [(not c, t) for c, t in pieces]
            wr, br = br, wr
        pieces = sorted(pieces, key=lambda ct: (side_index(ct[0]), _TYPE_ORDER[ct[1]]))
        # Exactly `literal != base_key`: a self-mirror material never swaps.
        self.mirrored = swap
        self.pieces = pieces
        self.has_pair = has_pair
        self.castling_rights = (wr, br)
        self.base_key = full_material_key(pieces, has_pair, (wr, br))
        self.mirr_key = full_material_key(
            [(not c, t) for c, t in pieces], has_pair, (br, wr))
        self.has_castling = wr + br > 0
        # Tiebreak below `min_key`: KRKr and KrKR differ only here. Fewer white
        # rights sort first, as white's slots weigh less in the key.
        self.castling_code = wr * 3 + br
        # The 30-bit count word alone, as the on-disk header carries it.
        self.min_key = min(self.base_key, self.mirr_key)[0]
        self.cache_key: CacheKey = (self.min_key, has_pair, self.castling_code)
        self.num_pieces = len(pieces)
        # `num_pieces` counts free men only (KpKp has 2), so test bare kings here.
        self.is_bare_kings = (self.num_pieces <= 2 and not has_pair
                              and not self.has_castling)

    def name(self) -> str:
        s = []
        seen_white_king = False
        # Castling rooks are not in `pieces`: write them where they would sort,
        # by (side index, type order).
        written = [0, 0]

        def write_castling_before(order: Tuple[int, int]) -> None:
            for i in (side_index(chess.WHITE), side_index(chess.BLACK)):
                if written[i] == self.castling_rights[i]:
                    continue
                if (i, _TYPE_ORDER[chess.ROOK]) >= order:
                    continue
                s.append("r" * (self.castling_rights[i] - written[i]))
                written[i] = self.castling_rights[i]

        for c, t in self.pieces:
            write_castling_before((side_index(c), _TYPE_ORDER[t]))
            if t == chess.KING:
                if seen_white_king and self.has_pair:
                    s.append("p")
                seen_white_king = True
            s.append(chess.piece_symbol(t).upper())
        write_castling_before((side_index(chess.BLACK) + 1, 0))
        if self.has_pair:
            s.append("p")
        return "".join(s)


_PIECE_CONFIG_CACHE: Dict[Tuple[Tuple[Tuple[chess.Color, chess.PieceType], ...], bool,
                                Tuple[int, int]],
                          PieceConfig] = {}


def piece_config(pieces: List[Tuple[chess.Color, chess.PieceType]], has_pair: bool = False,
                 castling_rights: Tuple[int, int] = (0, 0)) -> PieceConfig:
    """A shared :class:`PieceConfig` for this material. Immutable and cheap,
    so a racing build needs no lock."""
    key = (tuple(sorted(pieces)), has_pair, castling_rights)
    cfg = _PIECE_CONFIG_CACHE.get(key)
    if cfg is None:
        cfg = PieceConfig(pieces, has_pair, castling_rights)
        _PIECE_CONFIG_CACHE[key] = cfg
    return cfg


def _material_from_board(board: chess.Board, excluded: int = 0
                         ) -> List[Tuple[chess.Color, chess.PieceType]]:
    """The men on `board` as (color, piece type), squares in `excluded` left
    out."""
    keep = ~excluded
    out = []
    for color in (chess.WHITE, chess.BLACK):
        for pc_type in chess.PIECE_TYPES:
            n = chess.popcount(board.pieces_mask(pc_type, color) & keep)
            if n:
                out.extend([(color, pc_type)] * n)
    return out


def _piece_config_from_board(board: chess.Board, rooks: int,
                             pair: Optional[Tuple[int, int]]) -> Tuple["PieceConfig", bool]:
    """(PieceConfig, mirrored?) of the table for the board's material, less the
    `rooks` holding a right and the opposing `pair` squares, as marks;
    mirrored if colors had to swap to put the stronger side on white."""
    excluded = rooks if pair is None else rooks | chess.BB_SQUARES[pair[0]] | chess.BB_SQUARES[pair[1]]
    rights = (chess.popcount(rooks & board.occupied_co[chess.WHITE]),
              chess.popcount(rooks & board.occupied_co[chess.BLACK]))
    cfg = piece_config(_material_from_board(board, excluded), pair is not None, rights)
    return cfg, cfg.mirrored


# --- Piece_Class enum (src/chess/piece_config.h) ---
(BLACK_KINGS, BLACK_KNIGHTS, BLACK_BISHOPS, BLACK_ROOKS, BLACK_QUEENS, BLACK_PAWNS,
 WHITE_KINGS, WHITE_KNIGHTS, WHITE_BISHOPS, WHITE_ROOKS, WHITE_QUEENS, WHITE_PAWNS) = range(12)
PIECE_CLASS_NB = 12

_PTCLASS = {chess.KING: 0, chess.KNIGHT: 1, chess.BISHOP: 2, chess.ROOK: 3, chess.QUEEN: 4, chess.PAWN: 5}


def make_piece_class(color: chess.Color, ptype: int) -> int:
    base = WHITE_KINGS if color == chess.WHITE else BLACK_KINGS
    return base + _PTCLASS[ptype]


def class_to_piece(pcl: int) -> Tuple[chess.Color, int]:
    color = chess.WHITE if pcl >= WHITE_KINGS else chess.BLACK
    off = pcl - (WHITE_KINGS if color == chess.WHITE else BLACK_KINGS)
    inv = {0: chess.KING, 1: chess.KNIGHT, 2: chess.BISHOP, 3: chess.ROOK, 4: chess.QUEEN, 5: chess.PAWN}
    return color, inv[off]


class PieceGroup:
    def __init__(self, ptype: int, count: int):
        self.count = count
        # The legal squares run on from the first: a2..h7 for pawns.
        self.first = chess.A2 if ptype == chess.PAWN else chess.A1
        self.num_legal = chess.H7 - chess.A2 + 1 if ptype == chess.PAWN else 64
        self.table_size = binom(self.num_legal, count)

    def index_of(self, bb: int) -> int:
        """Colex rank of the pieces on bitboard ``bb``."""
        rank = 0
        for k, sq in enumerate(chess.scan_forward(bb), 1):
            rank += _BINOM[sq - self.first][k]
        return rank

    def squares(self, idx: int) -> int:
        """The pieces of placement `idx`, as a bitboard."""
        pos = [0] * self.count
        rank = idx
        hi = self.num_legal
        for k in range(self.count, 0, -1):
            p = hi - 1
            while binom(p, k) > rank:
                p -= 1
            pos[k - 1] = p
            rank -= binom(p, k)
            hi = p
        bb = 0
        for p in pos:
            bb |= chess.BB_SQUARES[self.first + p]
        return bb


# --- King_Slice_Manager (src/egtb/king_slice_manager.cpp) ---
class KingSliceManager:
    def __init__(self, sym: int):
        self.sym = sym
        n_trans = 8 if sym == SYM_DIHEDRAL_8 else 2
        anchors = _ANCHOR_TRIANGLE if sym == SYM_DIHEDRAL_8 else _ANCHOR_FILE_MIRROR
        SLICE_NONE = -1
        # Per (wk, bk): slice id, the apply_transform bits to reach it (0: none),
        # and whether the diagonal stabilizer decides.
        self.pair: List[List[int]] = [[SLICE_NONE, 0, 0] for _ in range(64 * 64)]
        self.num_slices = 0

        for wk in range(64):
            if not anchors & chess.BB_SQUARES[wk]:
                continue
            for bk in range(64):
                if bk == wk or chess.BB_KING_ATTACKS[wk] & chess.BB_SQUARES[bk]:
                    continue
                if (sym == SYM_DIHEDRAL_8 and _MAIN_DIAG & chess.BB_SQUARES[wk]
                        and _ABOVE_DIAG & chess.BB_SQUARES[bk]):
                    continue
                sid = self.num_slices
                self.num_slices += 1
                stab = 1 if (sym == SYM_DIHEDRAL_8 and _MAIN_DIAG & chess.BB_SQUARES[wk]
                             and _MAIN_DIAG & chess.BB_SQUARES[bk]) else 0
                self.pair[wk * 64 + bk] = [sid, 0, stab]

        for wk in range(64):
            for bk in range(64):
                e = self.pair[wk * 64 + bk]
                if e[0] != SLICE_NONE:
                    continue
                if wk == bk or chess.BB_KING_ATTACKS[wk] & chess.BB_SQUARES[bk]:
                    continue
                for t in range(n_trans):
                    wk_t = chess.lsb(apply_transform(chess.BB_SQUARES[wk], t))
                    bk_t = chess.lsb(apply_transform(chess.BB_SQUARES[bk], t))
                    look = self.pair[wk_t * 64 + bk_t]
                    if look[0] != -1 and look[1] == 0:
                        e[0] = look[0]
                        e[1] = t
                        e[2] = look[2]
                        break

    def lookup(self, wk: int, bk: int) -> List[int]:
        return self.pair[wk * 64 + bk]


class CastlingKingSliceManager:
    """King slices for a castling material: (castling placement, free king
    square), or the placement alone when both sides hold rights. The order
    MUST match the C++: slice ids are on disk."""

    def __init__(self, white_rights: int, black_rights: int):
        self.sym = SYM_NONE
        self.rights = (white_rights, black_rights)
        self.group = CastlingGroup(white_rights, black_rights)
        self.both_pinned = self.group.both_pinned
        self.num_slices = 0
        self._lookup: Dict[Tuple[int, int], int] = {}

        for ci in range(self.group.table_size):
            pinned = 0
            king_sq = [-1, -1]
            for color in (chess.WHITE, chess.BLACK):
                i = side_index(color)
                if not self.rights[i]:
                    continue
                kf, rook_mask = self.group.placement(ci, color)
                rank = 0 if color == chess.WHITE else 7
                king_sq[i] = chess.square(kf, rank)
                pinned |= chess.BB_SQUARES[king_sq[i]] | rook_mask << (8 * rank)

            def emit(slot: int) -> None:
                self._lookup[(ci, slot)] = self.num_slices
                self.num_slices += 1

            if self.both_pinned:
                emit(0)
                continue
            w_rights, _ = self.rights
            w_ksq, b_ksq = king_sq
            ksq = w_ksq if w_rights else b_ksq
            for fk in range(64):
                if (pinned | chess.BB_KING_ATTACKS[ksq]) & chess.BB_SQUARES[fk]:
                    continue
                emit(fk)

    def slice_of(self, wk: int, bk: int, w_rooks: int, b_rooks: int) -> int:
        """The slice of both kings and each side's castling rooks (bitboards),
        -1 if they are not on their home rank or not a placement of the
        rights."""
        king_sq = (wk, bk)
        rooks = (w_rooks, b_rooks)
        kfile = [-1, -1]
        masks = [0, 0]
        for color in (chess.WHITE, chess.BLACK):
            i = side_index(color)
            if not self.rights[i]:
                if rooks[i]:
                    return -1
                continue
            rank = 0 if color == chess.WHITE else 7
            if chess.square_rank(king_sq[i]) != rank or rooks[i] & ~chess.BB_RANKS[rank]:
                return -1
            kfile[i] = chess.square_file(king_sq[i])
            masks[i] = rooks[i] >> (8 * rank)

        w_kfile, b_kfile = kfile
        w_mask, b_mask = masks
        ci = self.group.index_of(w_kfile, w_mask, b_kfile, b_mask)
        if ci < 0:
            return -1
        w_rights, _ = self.rights
        slot = 0 if self.both_pinned else (bk if w_rights else wk)
        return self._lookup.get((ci, slot), -1)


# --- Castling_Group (src/chess/castling_group.h) ---
class CastlingGroup:
    """Joint placement of each unmoved king and the rooks it can still castle
    with, on any files: 56 per side. The order MUST match the C++: stored king
    slice ids are built from it."""

    MAX_RIGHTS = 2
    # A side's castling rooks as a mask over the files of its home rank.
    ROOK_MASKS = 1 << 8
    # Per rights count: each placement as (king file, rook file mask), in order.
    _SIDE_CACHE: Dict[int, List[Tuple[int, int]]] = {}

    @staticmethod
    def _side_placements(num_rights: int) -> List[Tuple[int, int]]:
        cached = CastlingGroup._SIDE_CACHE.get(num_rights)
        if cached is not None:
            return cached
        out: List[Tuple[int, int]] = []
        if num_rights:
            for k in range(8):
                if num_rights == 1:
                    for r in range(8):
                        if r != k:
                            out.append((k, 1 << r))
                else:
                    for lo in range(k):
                        for hi in range(k + 1, 8):
                            out.append((k, 1 << lo | 1 << hi))
        CastlingGroup._SIDE_CACHE[num_rights] = out
        return out

    def __init__(self, white_rights: int, black_rights: int):
        self.rights = (white_rights, black_rights)
        self.side = (self._side_placements(white_rights),
                     self._side_placements(black_rights))
        w_side, b_side = self.side
        self.b_span = max(len(b_side), 1)
        self.table_size = max(len(w_side), 1) * self.b_span
        self.both_pinned = white_rights > 0 and black_rights > 0
        # Per side: placement index by king file * ROOK_MASKS + rook mask, -1 if none.
        self._inverse: List[List[int]] = []
        for placements in self.side:
            inv = [-1] * (8 * self.ROOK_MASKS)
            for i, (k, mask) in enumerate(placements):
                inv[k * self.ROOK_MASKS + mask] = i
            self._inverse.append(inv)

    def placement(self, idx: int, color: chess.Color) -> Tuple[int, int]:
        within = idx // self.b_span if color == chess.WHITE else idx % self.b_span
        return self.side[side_index(color)][within]

    def index_of(self, w_king: int, w_rooks: int, b_king: int, b_rooks: int) -> int:
        """The placement of each side's king file and rook file mask, -1 if
        they are not one; a side without rights is ignored."""
        within = [0, 0]
        for i, (king, rooks) in enumerate(((w_king, w_rooks), (b_king, b_rooks))):
            if not self.rights[i]:
                continue
            within[i] = self._inverse[i][king * self.ROOK_MASKS + rooks]
            if within[i] < 0:
                return -1
        return within[0] * self.b_span + within[1]


# Geometry only, so all are built at import.
_KSM: Dict[int, KingSliceManager] = {sym: KingSliceManager(sym) for sym in (SYM_FILE_MIRROR, SYM_DIHEDRAL_8)}
_CASTLE_KSM: Dict[Tuple[int, int], CastlingKingSliceManager] = {
    (w, b): CastlingKingSliceManager(w, b)
    for w in range(CastlingGroup.MAX_RIGHTS + 1)
    for b in range(CastlingGroup.MAX_RIGHTS + 1)
    if w or b}


# --- Pawn_Slice_Manager (src/egtb/pawn_slice_manager.cpp) ---
class PairGroup:
    """Opposing pawn pair ('p'): white below black on one file, 15 rank pairs
    x 8 files = 120. The order and :meth:`canonical_pair` MUST match
    src/chess/pair_group.h: pawn slice ids are on disk."""

    def __init__(self) -> None:
        self.white: List[int] = []
        self.black: List[int] = []
        self._inv: Dict[Tuple[int, int], int] = {}
        for f in range(8):
            for wr in range(1, 6):          # ranks 2..6
                for br in range(wr + 1, 7):  # ranks 3..7
                    w = chess.square(f, wr)
                    b = chess.square(f, br)
                    self._inv[(w, b)] = len(self.white)
                    self.white.append(w)
                    self.black.append(b)

    table_size = 120

    def index_of(self, w: int, b: int) -> int:
        return self._inv[(w, b)]

    @staticmethod
    def is_opposing_pair(w: int, b: int) -> bool:
        return (chess.square_file(w) == chess.square_file(b)
                and chess.square_rank(w) >= 1 and chess.square_rank(b) <= 6
                and chess.square_rank(w) < chess.square_rank(b))

    @staticmethod
    def canonical_pair(white: int, black: int) -> Optional[Tuple[int, int]]:
        """The opposing pair minimal by (file, white_rank, black_rank), or None:
        on the first file holding one, the lowest white pawn with a black one
        above it, and the lowest black pawn above that."""
        for file_bb in chess.BB_FILES:
            w = white & file_bb
            b = black & file_bb
            if w and b and chess.lsb(w) < chess.msb(b):
                pw = chess.lsb(w)
                return pw, chess.lsb(b >> pw << pw)
        return None


class PawnSliceManager:
    """Pawn slices for one pawn structure, shared via :func:`pawn_slice_mgr`."""

    def __init__(self, has_pair: bool, white_pawns: int, black_pawns: int):
        pair_group = PairGroup() if has_pair else None
        white_group = PieceGroup(chess.PAWN, white_pawns) if white_pawns else None
        black_group = PieceGroup(chess.PAWN, black_pawns) if black_pawns else None
        self.pair_group = pair_group
        self.white_group = white_group
        self.black_group = black_group
        self.has_pawns = (pair_group is not None
                          or white_group is not None or black_group is not None)
        self.pair_table_size = pair_group.table_size if pair_group else 1
        self.white_table_size = white_group.table_size if white_group else 1
        self.black_table_size = black_group.table_size if black_group else 1
        if pair_group is None:
            # Without a pair only overlaps are cut, so the slice is direct:
            # black's placement, then white's among the squares left free.
            self.white_free_size = binom(chess.H7 - chess.A2 + 1 - black_pawns, white_pawns)
            self.num_slices = self.black_table_size * self.white_free_size
            return
        n_cart = self.pair_table_size * self.white_table_size * self.black_table_size

        def placements(g: Optional[PieceGroup]) -> List[int]:
            return [g.squares(i) for i in range(g.table_size)] if g else [0]

        white_placements = placements(white_group)
        black_placements = placements(black_group)
        self._survivor_bits = bytearray((n_cart + 7) // 8)
        rank_before = array.array("q", bytes(8 * ((n_cart + 63) // 64)))
        num_slices = 0

        # Pair indices follow the canonical order, so bitmasks over all 120
        # test canonicity at once instead of canonical_pair per cell.
        all_pairs = (1 << self.pair_table_size) - 1
        white_allowed = [0] * 64
        black_allowed = [0] * 64
        for pair_idx in range(self.pair_table_size):
            pw = pair_group.white[pair_idx]
            pb = pair_group.black[pair_idx]
            pw_bb, pb_bb = chess.BB_SQUARES[pw], chess.BB_SQUARES[pb]
            for sq in range(chess.A2, chess.H7 + 1):
                if sq == pw or sq == pb:
                    continue
                sq_bb = chess.BB_SQUARES[sq]
                bit = 1 << pair_idx
                if PairGroup.canonical_pair(pw_bb | sq_bb, pb_bb) == (pw, pb):
                    white_allowed[sq] |= bit
                if PairGroup.canonical_pair(pw_bb, pb_bb | sq_bb) == (pw, pb):
                    black_allowed[sq] |= bit

        def allowed(boards: List[int], masks: List[int]) -> List[int]:
            out = []
            for bb in boards:
                bits = all_pairs
                for sq in chess.scan_forward(bb):
                    bits &= masks[sq]
                out.append(bits)
            return out

        white_candidates = allowed(white_placements, white_allowed)
        black_candidates = allowed(black_placements, black_allowed)
        row_bytes = self.pair_table_size // 8  # 120 pair slots = 15 bytes.
        offset = 0
        for b_idx, black in enumerate(black_placements):
            # The pair must also precede every opposing pair the other pawns
            # form; bound that per extra white pawn.
            before = [all_pairs] * 64
            for wsq in range(chess.A2, chess.H7 + 1):
                first = self.pair_table_size
                for bsq in chess.scan_forward(black):
                    if PairGroup.is_opposing_pair(wsq, bsq):
                        first = min(first, pair_group.index_of(wsq, bsq))
                before[wsq] = (1 << first) - 1
            candidates = black_candidates[b_idx]
            for w_idx, white in enumerate(white_placements):
                if not white & black:
                    survivors = white_candidates[w_idx] & candidates
                    for wsq in chess.scan_forward(white):
                        survivors &= before[wsq]
                    self._survivor_bits[offset:offset + row_bytes] = survivors.to_bytes(row_bytes, "little")
                    num_slices += chess.popcount(survivors)
                offset += row_bytes
        self.num_slices = num_slices

        running = 0
        for blk in range(len(rank_before)):
            rank_before[blk] = running
            running += chess.popcount(int.from_bytes(
                self._survivor_bits[blk * 8:blk * 8 + 8], "little"))
        self._rank_before_block = rank_before

    def lookup(self, pair_w: int, pair_b: int, white: int, black: int) -> int:
        """The pawn slice of the pair's squares (unused without one) and
        each side's other pawns, as bitboards."""
        b_idx = self.black_group.index_of(black) if self.black_group else 0
        if self.pair_group is None:
            # Index among the squares black leaves free; removing them keeps
            # the order, so the colex rank carries over.
            rank = 0
            for k, sq in enumerate(chess.scan_forward(white), 1):
                free_index = sq - chess.A2 - chess.popcount(black & ((1 << sq) - 1))
                rank += _BINOM[free_index][k]
            return b_idx * self.white_free_size + rank
        # With a pair: the cell's rank among the bitmap's survivors.
        w_idx = self.white_group.index_of(white) if self.white_group else 0
        cart = (self.pair_group.index_of(pair_w, pair_b)
                + w_idx * self.pair_table_size
                + b_idx * self.pair_table_size * self.white_table_size)
        blk, off = divmod(cart, 64)
        word = int.from_bytes(self._survivor_bits[blk * 8:blk * 8 + 8], "little")
        return self._rank_before_block[blk] + chess.popcount(word & ((1 << off) - 1))


# --- Index permutation (src/chess/index_permutation.h) ---
_FACT = [1, 1, 2, 6, 24, 120, 720, 5040, 40320]


def index_permutation_valid(n_classes: int, perm: int) -> bool:
    return n_classes <= 8 and perm < _FACT[n_classes]


def storage_within_class_order(populated: List[int], perm: int) -> List[int]:
    n = len(populated)
    available = list(populated)
    order = []
    idx = perm
    for i in range(n):
        f = _FACT[n - 1 - i]
        pick = idx // f
        idx %= f
        order.append(available[pick])
        del available[pick]
    return order


# --- Position_Index_Config (src/probe/position_index.h) ---
class PositionIndexConfig:
    def __init__(self, cfg: PieceConfig):
        self.cfg = cfg
        counts: Dict[Tuple[int, int], int] = {}
        for c, t in cfg.pieces:
            counts[(c, t)] = counts.get((c, t), 0) + 1
        has_pawns = (counts.get((chess.WHITE, chess.PAWN), 0) > 0
                     or counts.get((chess.BLACK, chess.PAWN), 0) > 0 or cfg.has_pair)
        self.ksm: Union[KingSliceManager, CastlingKingSliceManager]
        if cfg.has_castling:
            self.sym = SYM_NONE
            w_rights, b_rights = cfg.castling_rights
            self.ksm = _CASTLE_KSM[(w_rights, b_rights)]
        else:
            self.sym = SYM_FILE_MIRROR if has_pawns else SYM_DIHEDRAL_8
            self.ksm = _KSM[self.sym]

        self.groups: Dict[int, PieceGroup] = {}
        for c in (chess.WHITE, chess.BLACK):
            for t in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):  # pawns: self.psm
                n = counts.get((c, t), 0)
                if n == 0:
                    continue
                pcl = make_piece_class(c, t)
                self.groups[pcl] = PieceGroup(t, n)

        self.psm = pawn_slice_mgr(cfg.has_pair, counts.get((chess.WHITE, chess.PAWN), 0),
                                  counts.get((chess.BLACK, chess.PAWN), 0))
        self.num_pawn_slices = self.psm.num_slices

        self.populated: List[int] = []
        self.weights: Dict[int, int] = {}
        w = 1
        for i in range(PIECE_CLASS_NB):
            if i not in self.groups:
                continue
            self.populated.append(i)
            self.weights[i] = w
            w *= self.groups[i].table_size
        self.within_slice_size = w
        self.num_king_slices = self.ksm.num_slices
        self.pawn_slice_stride = self.num_king_slices * self.within_slice_size
        self.num_positions = self.num_pawn_slices * self.pawn_slice_stride

    def make_layout(self, perm: int) -> Tuple[List[int], List[int]]:
        order = storage_within_class_order(self.populated, perm)
        radix = [self.groups[c].table_size for c in order]
        return order, radix

    def board_index(self, board: chess.Board, order: List[int], radix: List[int]) -> Optional[int]:
        boards = {}
        for c in self.populated:
            color, tt = class_to_piece(c)
            boards[c] = board.pieces_mask(tt, color)
        white_pawns = board.pieces_mask(chess.PAWN, chess.WHITE)
        black_pawns = board.pieces_mask(chess.PAWN, chess.BLACK)
        wk, bk = board.king(chess.WHITE), board.king(chess.BLACK)
        assert wk is not None and bk is not None  # tablebase positions have both kings

        if isinstance(self.ksm, CastlingKingSliceManager):
            # Nothing folds under SYM_NONE: the right tells orientations apart.
            # A castling slice is keyed by the pinned rooks too, which ride in
            # it rather than in their rook class.
            castling_rooks = board.clean_castling_rights()
            ksid = self.ksm.slice_of(wk, bk,
                                     castling_rooks & board.occupied_co[chess.WHITE],
                                     castling_rooks & board.occupied_co[chess.BLACK])
            if ksid == -1:
                return None
            within_idx = {c: self.groups[c].index_of(boards[c] & ~castling_rooks)
                          for c in self.populated}
        else:
            # The symmetry that takes the kings to their slice's squares,
            # applied to every man.
            ksid, t, stabilizer = self.ksm.lookup(wk, bk)
            if ksid == -1:
                return None
            if t:
                boards = {c: apply_transform(bb, t) for c, bb in boards.items()}
                white_pawns = apply_transform(white_pawns, t)
                black_pawns = apply_transform(black_pawns, t)
            within_idx = {c: self.groups[c].index_of(boards[c]) for c in self.populated}
            if stabilizer:
                # Both kings on the diagonal: the a1-h8 mirror keeps their
                # slice, so the men take whichever side ranks lower.
                alt_idx = {c: self.groups[c].index_of(chess.flip_diagonal(boards[c]))
                           for c in self.populated}
                cur = sum(self.weights[c] * within_idx[c] for c in self.populated)
                alt = sum(self.weights[c] * alt_idx[c] for c in self.populated)
                if alt < cur:
                    within_idx = alt_idx

        pawn_slice = 0
        if self.psm.has_pawns:
            pw = pb = -1
            if self.cfg.has_pair:
                pw, pb = PairGroup.canonical_pair(white_pawns, black_pawns) or (-1, -1)
                white_pawns &= ~chess.BB_SQUARES[pw]
                black_pawns &= ~chess.BB_SQUARES[pb]
            pawn_slice = self.psm.lookup(pw, pb, white_pawns, black_pawns)
        within = 0
        w = 1
        for i in range(len(order)):
            within += w * within_idx[order[i]]
            w *= radix[i]
        outer = pawn_slice * self.pawn_slice_stride + ksid * self.within_slice_size
        return outer + within


_PSM_CACHE: Dict[Tuple[bool, int, int], PawnSliceManager] = {}
# Costly to build, so once per pawn structure, under the lock.
_PSM_LOCK = threading.Lock()


def pawn_slice_mgr(has_pair: bool, white_pawns: int, black_pawns: int) -> PawnSliceManager:
    key = (has_pair, white_pawns, black_pawns)
    psm = _PSM_CACHE.get(key)
    if psm is not None:
        return psm
    with _PSM_LOCK:
        psm = _PSM_CACHE.get(key)
        if psm is None:
            psm = PawnSliceManager(has_pair, white_pawns, black_pawns)
            _PSM_CACHE[key] = psm
        return psm


# --- On-disk framing (src/egtb/egtb_format.h, src/util/{memory,mono_uint_vec}.h) ---

WDL_MAGIC, DTZ_MAGIC, DTC_MAGIC, DTM_MAGIC, DTM50_MAGIC = (
    0x9bd1e3a6, 0x2ec8b161, 0x2ec8b17e, 0xab57c134, 0xab57c151)
SINGULAR_FLAG = 0x80
DROPPED_FLAG = 0x40
LOSS_ONLY_FLAG = 0x20
RELAXED_FLAG = 0x10
MAX_NON_CURSED_DTZ = 100
DTM50_HMC_COUNT = 100
DTM50_PACK_LAYERS = 101
# An 8-man winner has at most six pawns with five non-converting pushes each.
# Budgets 0..29 are solved; the embedded DTZ row supplies budget 30 for clean W/L.
DTC_BUDGET_LAYERS = 30
DTC_PACK_LAYERS = 31
DRAWN_AT_LAYER = 0xFFFF


def layered_bitmap_bytes(layers: int) -> int:
    """Bytes of a MULTI record's changepoint bitmap, in whole 32-bit words."""
    return ((layers + 31) // 32) * 4


DTM50_MULTI_BITMAP_BYTES = layered_bitmap_bytes(DTM50_PACK_LAYERS)
DTC_MULTI_BITMAP_BYTES = layered_bitmap_bytes(DTC_PACK_LAYERS)

IGNORE_50MR = -1  # sentinel (C++ uses ~0u)

LOSE, BLESSED_LOSS, DRAW, CURSED_WIN, WIN, ILLEGAL = 0, 1, 2, 3, 4, 7


def wdl_from_storage(s: int) -> int:
    if s == 6:   # BOUNDARY_WIN
        return WIN
    if s == 5:   # BOUNDARY_LOSS
        return LOSE
    return s


class _Serial:
    """Sequential little-endian reader over a table's buffer. Reads copy their
    bytes, as ``unpack_from`` would demand the buffer protocol."""

    def __init__(self, data: Any):
        self.d = data
        self.pos = 0

    def u8(self) -> int:
        v = int(self.d[self.pos])
        self.pos += 1
        return v

    def _le(self, size: int) -> int:
        v = int.from_bytes(bytes(self.d[self.pos:self.pos + size]), "little")
        self.pos += size
        return v

    def u16(self) -> int:
        return self._le(2)

    def u32(self) -> int:
        return self._le(4)

    def u64(self) -> int:
        return self._le(8)

    def advance(self, n: int) -> None:
        self.pos += n

    def caret(self) -> int:
        return self.pos

    def align(self, alignment: int) -> None:
        mis = self.pos % alignment
        if mis:
            self.pos += alignment - mis


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b


_U64LE = struct.Struct("<Q")


def _read_u64le(buf: Any, offset: int) -> int:
    """The 8 bytes at `offset`, little-endian, without a slice on the hot
    path. Slicing covers the end of a mapping and non-memoryview buffers."""
    if isinstance(buf, memoryview):
        try:
            return _U64LE.unpack_from(buf, offset)[0]  # type: ignore[no-any-return]
        except struct.error:
            return int.from_bytes(buf[offset:offset + 8], "little")
    return int.from_bytes(bytes(buf[offset:offset + 8]), "little")


def _compressed_block(chunk: Any) -> Any:
    """A compressed block as the decoders want it; other buffer types
    (:meth:`_TableFile._open_source`) are copied."""
    if isinstance(chunk, (bytes, bytearray, memoryview)):
        return chunk
    return bytes(chunk)


class MonoUintVec:
    """Block-sampled delta coder for a monotone uint64 sequence, addressed as
    `base` into the table's buffer rather than a slice of it."""

    def __init__(self, blob: Any, base: int, num_values: int, log2_bu: int,
                 sample_width: int, offset_width: int):
        self.blob = blob
        self.base = base
        self.num_values = num_values
        self.log2_bu = log2_bu
        self.sample_width = sample_width
        self.offset_width = offset_width
        num_samples = _ceil_div(num_values, 1 << log2_bu)
        self.delta_off = _ceil_div(num_samples * sample_width, 8)

    @staticmethod
    def on_disk_bytes(num_values: int, log2_bu: int, sample_width: int, offset_width: int) -> int:
        num_samples = _ceil_div(num_values, 1 << log2_bu)
        return (_ceil_div(num_samples * sample_width, 8)
                + _ceil_div(num_values * offset_width, 8))

    def _read_bits(self, base_off: int, bitpos: int, width: int) -> int:
        if width == 0:
            return 0
        byte = self.base + base_off + (bitpos >> 3)
        bit = bitpos & 7
        lo = _read_u64le(self.blob, byte)
        v = lo >> bit
        if bit + width > 64:
            hi = _read_u64le(self.blob, byte + 8)
            v |= hi << (64 - bit)
        mask = (1 << width) - 1 if width < 64 else (1 << 64) - 1
        return v & mask

    def get(self, i: int) -> int:
        sb = i >> self.log2_bu
        base = self._read_bits(0, sb * self.sample_width, self.sample_width)
        delta = self._read_bits(self.delta_off, i * self.offset_width, self.offset_width)
        return base + delta

    def get2(self, i: int) -> Tuple[int, int]:
        return (self.get(i), self.get(i + 1))


class Min0UintVec:

    def __init__(self, data: Any, base: int, size: int, width: int):
        self.data = data
        self.base = base
        self.size = size
        self.width = width

    @staticmethod
    def on_disk_bytes(size: int, width: int) -> int:
        return _ceil_div(size * width, 8)

    def get(self, i: int) -> int:
        if self.width == 0:
            return 0
        bitpos = i * self.width
        byte = self.base + (bitpos >> 3)
        bit = bitpos & 7
        lo = _read_u64le(self.data, byte)
        v = lo >> bit
        if bit + self.width > 64:
            hi = _read_u64le(self.data, byte + 8)
            v |= hi << (64 - bit)
        mask = (1 << self.width) - 1
        return v & mask


# --- LZ4 block decompression ---

def lz4_decompress_block(src: memoryview, expected_size: int, dict_bytes: bytes = b"") -> bytes:
    """Decompress an LZ4 *block* (not frame), `dict_bytes` logically preceding
    the output. Uses `python-lz4 <https://pypi.org/project/lz4/>`_ where
    installed, else :func:`lz4_decompress_block_python`."""
    if _lz4_block is not None:
        return bytes(_lz4_block.decompress(src, uncompressed_size=expected_size,
                                           dict=dict_bytes or None))
    return lz4_decompress_block_python(src, expected_size, dict_bytes)


def lz4_decompress_block_python(src: memoryview, expected_size: int,
                                dict_bytes: bytes = b"") -> bytes:
    out = bytearray(dict_bytes)
    base = len(dict_bytes)
    si = 0
    n = len(src)
    while si < n:
        token = src[si]
        si += 1
        lit_len = token >> 4
        if lit_len == 15:
            while True:
                b = src[si]
                si += 1
                lit_len += b
                if b != 255:
                    break
        out += src[si:si + lit_len]
        si += lit_len
        if si >= n:
            break
        offset = src[si] | (src[si + 1] << 8)
        si += 2
        match_len = (token & 0xF) + 4
        if (token & 0xF) == 15:
            while True:
                b = src[si]
                si += 1
                match_len += b
                if b != 255:
                    break
        start = len(out) - offset
        for j in range(match_len):
            out.append(out[start + j])
    result = bytes(out[base:])
    if len(result) != expected_size:
        raise ValueError(f"LZ4 size mismatch: got {len(result)} expected {expected_size}")
    return result


# --- Decoded-block cache ---

#: Default soft budget in bytes for decoded blocks across all tables of a
#: :class:`Tablebase`, beyond which least-recently-used blocks are evicted.
DEFAULT_BLOCK_CACHE_BYTES = 64 * 1024 * 1024


class _PerColor:
    """One color's frame of one table. Read-only once built, except
    ``_blocks``, which probes fill under the decode locks."""

    __slots__ = ("_blocks", "_block_locks", "_meta_lock")

    _blocks: Dict[int, Any]

    def __init__(self) -> None:
        self._blocks = {}
        # Per block, not per color: lzma releases the GIL, so cold decodes of
        # different blocks run in parallel.
        self._block_locks: Dict[int, threading.Lock] = {}
        self._meta_lock = threading.Lock()

    def lock_for(self, block_id: int) -> threading.Lock:
        lk = self._block_locks.get(block_id)
        if lk is not None:
            return lk
        with self._meta_lock:
            lk = self._block_locks.get(block_id)
            if lk is None:
                lk = threading.Lock()
                self._block_locks[block_id] = lk
            return lk


class _BlockCache:
    """LRU over the decoded blocks of every table of a :class:`Tablebase`.
    Sizes are approximate, so ``max_bytes`` is a soft budget."""

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        self.cur_bytes = 0
        self._lru: "collections.OrderedDict[Tuple[Any, int], int]" = collections.OrderedDict()
        self._lock = threading.Lock()

    def touch(self, pc: Any, block_id: int) -> None:
        key = (pc, block_id)
        with self._lock:
            if key in self._lru:
                self._lru.move_to_end(key)

    def record(self, pc: _PerColor, block_id: int, size: int) -> None:
        """Track a decoded block and evict down to budget. Re-recording replaces
        the old size, so concurrent decoders can't skew the total."""
        key = (pc, block_id)
        with self._lock:
            old = self._lru.pop(key, None)
            if old is not None:
                self.cur_bytes -= old
            self._lru[key] = size
            self.cur_bytes += size
            while self.cur_bytes > self.max_bytes and len(self._lru) > 1:
                (ev_pc, ev_id), ev_size = self._lru.popitem(last=False)
                self.cur_bytes -= ev_size
                self._drop(ev_pc, ev_id)

    def forget(self, pc: _PerColor) -> None:
        with self._lock:
            for key in [k for k in self._lru if k[0] is pc]:
                self.cur_bytes -= self._lru.pop(key)

    def clear(self) -> None:
        with self._lock:
            for pc, block_id in self._lru:
                self._drop(pc, block_id)
            self._lru.clear()
            self.cur_bytes = 0

    @staticmethod
    def _drop(pc: _PerColor, block_id: int) -> None:
        """Evict a block and its lock, keeping `_block_locks` bounded. A decode
        still holding the old lock is harmless: both write the same bytes."""
        pc._blocks.pop(block_id, None)
        pc._block_locks.pop(block_id, None)


#: A path, or whatever an overridden :meth:`_TableFile._open_source` accepts.
#: Interpolated into messages, so it wants a ``__str__``.
TableSource = Any


class _TableFile:
    """Source lifecycle shared by the table kinds. Files are mapped, not read
    in: a probe touches a few blocks, and the page cache stays reclaimable."""

    EXT: str
    MAGIC: int
    KIND: str
    PER_COLOR: Type[Any]
    cache: _BlockCache
    per_color: List[Any]
    path: TableSource

    _data: Optional[Any] = None
    _reader: Optional[_Serial] = None

    def __init__(self, cfg: PieceConfig, path: TableSource,
                 cache: Optional[_BlockCache] = None):
        self.cfg = cfg
        self.index_cfg = PositionIndexConfig(cfg)
        self.cache = cache if cache is not None else _BlockCache(DEFAULT_BLOCK_CACHE_BYTES)
        self.is_singular = [False, False]
        self.is_dropped = [False, False]
        self.is_loss_only = [False, False]
        self.is_relaxed = [False, False]
        self.per_color = [None, None]
        self._open(path)

    def _open(self, path: TableSource) -> None:
        self.path = path
        try:
            self._reader = _Serial(self._open_source(path))
            if (len(self._reader.d) & 63) != 8:
                raise ValueError(f"Invalid {self.KIND} file size {path}")
            self._parse(self._reader)
        except BaseException:
            self.close()
            raise

    def _parse(self, r: _Serial) -> None:
        if r.u32() != self.MAGIC:
            raise ValueError(f"Invalid {self.KIND} magic {self.path}")
        key_and_table = r.u32()
        if (key_and_table >> 2) != (self.cfg.min_key & _PACKED_MATERIAL_KEY_MASK):
            raise ValueError(f"Wrong material key in {self.KIND} {self.path}")
        # Frames stored: WHITE, and BLACK unless the material is symmetric (1).
        table_num = key_and_table & 3
        if not 1 <= table_num <= 2:
            raise ValueError(f"Invalid {self.KIND} table count {table_num} {self.path}")
        for c in range(table_num):
            flag = r.u8()
            pc = self.PER_COLOR()
            self.per_color[c] = pc
            self.is_loss_only[c] = bool(flag & LOSS_ONLY_FLAG)
            self.is_relaxed[c] = bool(flag & RELAXED_FLAG)
            if flag & SINGULAR_FLAG:
                self.is_singular[c] = True
                if not self._on_singular(r, pc):
                    raise ValueError(f"Invalid {self.KIND} singular value {self.path}")
            elif flag & DROPPED_FLAG:
                self.is_dropped[c] = True
            else:
                self._parse_header(r, pc)
        if table_num == 1:
            # Symmetric material: BLACK is WHITE mirrored, flag byte and all.
            w, b = side_index(chess.WHITE), side_index(chess.BLACK)
            self.is_dropped[b] = True
            self.is_loss_only[b] = self.is_loss_only[w]
            self.is_relaxed[b] = self.is_relaxed[w]
        self._finalize(r)

    def _on_singular(self, r: _Serial, pc: Any) -> bool:
        """Read a singular frame's value; False if it isn't a valid one."""
        pc.single_val = r.u8()
        return True

    def _parse_header(self, r: _Serial, pc: Any) -> None:
        raise NotImplementedError

    def _get_block(self, pc: Any, block_id: int) -> Any:
        """The decoded block. A cold one is decoded once, other threads
        waiting on its lock."""
        blk = pc._blocks.get(block_id)
        if blk is None:
            with pc.lock_for(block_id):
                blk = pc._blocks.get(block_id)
                if blk is None:
                    return self._decode_block(pc, block_id)
        self.cache.touch(pc, block_id)
        return blk

    def _decode_block(self, pc: Any, block_id: int) -> Any:
        """Decode a block into ``pc._blocks`` and record it in the cache."""
        raise NotImplementedError

    def _finalize(self, r: _Serial) -> None:
        raise NotImplementedError

    def _open_source(self, path: TableSource) -> Any:
        """Open `path`, set ``self._data`` to what :meth:`close` releases, and
        return the buffer to read. Maps the file; an override for another
        transport may return anything with ``len()``, indexing and slicing.
        Reads span at most one block, so it wants a page cache under it."""
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            data = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        finally:
            os.close(fd)

        if sys.platform != "win32":
            data.madvise(mmap.MADV_RANDOM)

        self._data = data
        return memoryview(data)

    def close(self) -> None:
        """Drop decoded blocks and release the source. Idempotent; no thread
        may be probing this table (:meth:`Tablebase.close` drains them first)."""
        for pc in self.per_color:
            if pc is not None:
                pc._blocks.clear()
                self.cache.forget(pc)
        # The view goes first, or mmap.close() raises BufferError.
        reader, self._reader = self._reader, None
        if reader is not None and isinstance(reader.d, memoryview):
            reader.d.release()
        data, self._data = self._data, None
        if data is not None:
            try:
                data.close()
            except BufferError:
                pass


# --- WDL table file (src/probe/wdl_file.cpp) ---

class _WDLPerColor(_PerColor):
    __slots__ = ("order", "radix", "block_size", "tail_size", "block_cnt",
                 "data_size", "offsets", "buf", "data_off", "dict", "single_val")
    order: List[int]
    radix: List[int]
    block_size: int
    tail_size: int
    block_cnt: int
    data_size: int
    offsets: MonoUintVec
    buf: Any
    data_off: int
    dict: bytes
    single_val: int
    _blocks: Dict[int, bytes]

    def __init__(self) -> None:
        super().__init__()
        self.single_val = DRAW
        self.dict = b""


class WDLFile(_TableFile):
    EXT = ".lzw"
    MAGIC = WDL_MAGIC
    KIND = "WDL"
    PER_COLOR = _WDLPerColor
    per_color: List[Optional[_WDLPerColor]]

    def _parse_header(self, r: _Serial, pc: _WDLPerColor) -> None:
        perm = r.u32()
        n = len(self.index_cfg.populated)
        if not index_permutation_valid(n, perm):
            raise ValueError("Invalid WDL index permutation")
        pc.order, pc.radix = self.index_cfg.make_layout(perm)
        pc.tail_size = r.u16()
        pc.block_size = r.u32()
        pc.block_cnt = r.u64()
        pc.data_size = r.u64()

    def _finalize(self, r: _Serial) -> None:
        for c in range(2):
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            dict_size = r.u16()
            start = r.caret()
            pc.dict = bytes(r.d[start:start + dict_size])
            r.advance(dict_size)
        for c in range(2):
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            log2_bu = r.u8()
            sample_width = r.u8()
            offset_width = r.u8()
            r.advance(1)  # usz_width
            mono_off = r.caret()
            mono_bytes = MonoUintVec.on_disk_bytes(pc.block_cnt + 1, log2_bu,
                                                   sample_width, offset_width)
            r.advance(mono_bytes)
            pc.offsets = MonoUintVec(r.d, mono_off, pc.block_cnt + 1, log2_bu,
                                     sample_width, offset_width)
        for c in range(2):
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.buf, pc.data_off = r.d, start
            r.advance(pc.data_size)

    def _decode_block(self, pc: _WDLPerColor, block_id: int) -> bytes:
        doff, dnext = pc.offsets.get2(block_id)
        dsz = dnext - doff
        out_sz = (pc.tail_size if (block_id == pc.block_cnt - 1 and pc.tail_size != 0)
                  else pc.block_size)
        blk = lz4_decompress_block(
            _compressed_block(pc.buf[pc.data_off + doff:pc.data_off + doff + dsz]),
            out_sz, pc.dict)
        pc._blocks[block_id] = blk
        self.cache.record(pc, block_id, len(blk))
        return blk

    def read(self, color: int, board: chess.Board) -> int:
        pc = self.per_color[color]
        assert pc is not None
        if self.is_singular[color]:
            return pc.single_val
        pos = self.index_cfg.board_index(board, pc.order, pc.radix)
        assert pos is not None
        packed_byte = pos // 2
        block_id = packed_byte // pc.block_size
        in_block = packed_byte % pc.block_size
        lo, hi = pc.offsets.get2(block_id)
        if lo == hi:
            return 7  # ILLEGAL
        data: bytes = self._get_block(pc, block_id)
        entry = data[in_block]
        return (entry >> ((pos % 2) * 4)) & 0xF


def _exists_case_exact(path: str) -> bool:
    """Whether `path` exists with exactly this case.

    Case is meaningful in table names (``KrK`` is not ``KRK``), which a
    case-folding filesystem ignores. The directory scan is slow, so it only
    runs when the case-flipped name also exists.
    """
    if not os.path.exists(path):
        return False
    directory, name = os.path.split(path)
    directory = directory or "."
    flipped = name.swapcase()
    if flipped == name or not os.path.exists(os.path.join(directory, flipped)):
        return True
    try:
        with os.scandir(directory) as it:
            return any(entry.name == name for entry in it)
    except OSError:
        return False


# --- Probe helpers (src/probe/probe.cpp) ---

def mirror_for_canonical(board: chess.Board) -> chess.Board:
    """Swap colors, rank-mirror the board and flip the side to move."""
    out = board.copy(stack=False)
    out.apply_mirror()
    return out


_WDL_NAME = {LOSE: "LOSE", BLESSED_LOSS: "BLESSED_LOSS", DRAW: "DRAW",
             CURSED_WIN: "CURSED_WIN", WIN: "WIN", ILLEGAL: "ILLEGAL"}


# --- WDL helpers (src/egtb/egtb_entry.h) ---

def invert_wdl(w: int) -> int:
    return {WIN: LOSE, CURSED_WIN: BLESSED_LOSS, DRAW: DRAW,
            BLESSED_LOSS: CURSED_WIN, LOSE: WIN, ILLEGAL: ILLEGAL}[w]


def invert_stored(s: int) -> int:
    return {0: WIN, 1: CURSED_WIN, 2: DRAW, 3: BLESSED_LOSS, 4: LOSE,
            5: CURSED_WIN,   # BOUNDARY_LOSS -> we win but only cursed
            6: BLESSED_LOSS,  # BOUNDARY_WIN  -> we lose but only blessed
            7: ILLEGAL}[s]


def wdl_rank(w: int) -> int:
    return {WIN: 4, CURSED_WIN: 3, DRAW: 2, BLESSED_LOSS: 1, LOSE: 0, ILLEGAL: -1}[w]


def stored_rank(s: int) -> int:
    return {0: 0,   # LOSE
            5: 1,   # BOUNDARY_LOSS
            1: 2,   # BLESSED_LOSS
            2: 3,   # DRAW
            3: 4,   # CURSED_WIN
            6: 5,   # BOUNDARY_WIN
            4: 6,   # WIN
            7: -1}[s]


def is_symmetric_material(cfg: PieceConfig) -> bool:
    return cfg.base_key == cfg.mirr_key


def material_has_pawns(cfg: PieceConfig) -> bool:
    return cfg.has_pair or any(t == chess.PAWN for _c, t in cfg.pieces)


def is_win_class(w: int) -> bool:
    return w == WIN or w == CURSED_WIN


def locate_frame(f: Any, cfg: PieceConfig, board: chess.Board,
                 wdl: int) -> Tuple[int, Optional[chess.Board], bool]:
    """The frame holding a cell, the mirrored board to read it with (or None),
    and whether the cell is stored. A dropped frame is read through the mirror
    for self-mirror material; a loss-only frame stores no wins. Unstored cells
    are derived by one ply on the unmirrored board."""
    color = side_index(board.turn)
    if not f.is_dropped[color]:
        return color, None, not (f.is_loss_only[color] and is_win_class(wdl))
    if not is_symmetric_material(cfg):
        return color, None, False
    kept = side_index(not board.turn)
    if f.is_loss_only[kept] and is_win_class(wdl):
        return kept, None, False
    return kept, mirror_for_canonical(board), True


MAX_DERIVE_DEPTH = 64


def _internal_board(board: chess.Board) -> chess.Board:
    if board.ep_square is not None:
        board = board.copy(stack=False)
        board.ep_square = None
    return board


# --- LZMA blocks and stored values (src/egtb/egtb_entry.h) ---

def lzma_raw_decompress(block: memoryview, expected_size: int) -> bytes:
    if len(block) < 5:
        raise ValueError("LZMA block too small")
    props = bytes(block[-5:])
    raw = bytes(block[:-5])
    d0 = props[0]
    lc = d0 % 9
    rem = d0 // 9
    lp = rem % 5
    pb = rem // 5
    dict_size = int.from_bytes(props[1:5], "little")
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=[{
        "id": lzma.FILTER_LZMA1, "dict_size": dict_size,
        "lc": lc, "lp": lp, "pb": pb}])
    out = dec.decompress(raw, expected_size)
    if len(out) != expected_size:
        out += dec.decompress(b"", expected_size - len(out))
    if len(out) != expected_size:
        raise ValueError(f"LZMA size mismatch {len(out)} != {expected_size}")
    return out


class _DTZValue(NamedTuple):
    dtz: int
    rounded: bool


def dtz_value_from_storage(stored: int, w: int, entry_bytes: int) -> _DTZValue:
    if w == DRAW:
        return _DTZValue(0, False)
    if entry_bytes == 1 and (w == CURSED_WIN or w == BLESSED_LOSS):
        return _DTZValue((stored << 1) - 1, True)
    return _DTZValue(stored, False)


def dtm_value_from_storage(stored: int, w: int) -> int:
    if w in (WIN, CURSED_WIN):
        return (stored << 1) | 1
    if w in (LOSE, BLESSED_LOSS):
        return stored << 1
    return 0


def dtm50_value_from_storage(stored: int, w: int) -> int:
    if w == WIN:
        return (stored << 1) | 1
    if w == LOSE:
        return stored << 1
    return 0


# --- DTZ and DTM table files (src/probe/{dtz,dtm}_file.cpp) ---

class _RankPerColor(_PerColor):
    __slots__ = ("order", "radix", "entry_bytes", "block_size", "tail_size",
                 "block_cnt", "data_size", "offsets", "buf", "data_off",
                 "rank_to_value", "single_val")
    order: List[int]
    radix: List[int]
    entry_bytes: int
    block_size: int
    tail_size: int
    block_cnt: int
    data_size: int
    offsets: MonoUintVec
    buf: Any
    data_off: int
    rank_to_value: List[int]
    single_val: int
    _blocks: Dict[int, bytes]

    def __init__(self) -> None:
        super().__init__()
        self.single_val = 0


class _RankFile(_TableFile):
    """Rank-coded, LZMA-blocked table shared by DTZ and DTM, which differ only
    in magic and value decode."""

    PER_COLOR = _RankPerColor
    per_color: List[Optional[_RankPerColor]]

    def _parse_header(self, r: _Serial, pc: _RankPerColor) -> None:
        perm = r.u32()
        pc.order, pc.radix = self.index_cfg.make_layout(perm)
        pc.entry_bytes = r.u8()
        pc.tail_size = r.u32()
        pc.block_size = r.u32()
        pc.block_cnt = r.u64()
        pc.data_size = r.u64()
        num_ranks = r.u16()
        pc.rank_to_value = [r.u16() for _ in range(num_ranks)]

    def _finalize(self, r: _Serial) -> None:
        for c in range(2):
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            log2_bu = r.u8()
            sample_width = r.u8()
            offset_width = r.u8()
            r.advance(1)  # usz_width
            mono_off = r.caret()
            mb = MonoUintVec.on_disk_bytes(pc.block_cnt + 1, log2_bu, sample_width, offset_width)
            r.advance(mb)
            pc.offsets = MonoUintVec(r.d, mono_off, pc.block_cnt + 1, log2_bu,
                                     sample_width, offset_width)
        for c in range(2):
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.buf, pc.data_off = r.d, start
            r.advance(pc.data_size)

    def _decode_block(self, pc: _RankPerColor, block_id: int) -> bytes:
        decode_sz = (pc.tail_size if (block_id == pc.block_cnt - 1 and pc.tail_size != 0)
                     else pc.block_size)
        doff, dnext = pc.offsets.get2(block_id)
        dsz = dnext - doff
        blk = b"" if dsz == 0 else lzma_raw_decompress(
            _compressed_block(pc.buf[pc.data_off + doff:pc.data_off + doff + dsz]),
            decode_sz)
        pc._blocks[block_id] = blk
        self.cache.record(pc, block_id, len(blk))
        return blk

    def _read_stored(self, color: int, board: chess.Board) -> Optional[Tuple[int, int]]:
        """(stored, entry_bytes) of a cell, or None in a skip block."""
        pc = self.per_color[color]
        assert pc is not None
        if self.is_singular[color]:
            return pc.single_val, 1
        pos = self.index_cfg.board_index(board, pc.order, pc.radix)
        assert pos is not None
        ppb = pc.block_size // pc.entry_bytes
        block_id = pos // ppb
        in_block = pos % ppb
        lo, hi = pc.offsets.get2(block_id)
        if lo == hi:
            return None  # skip block: uniform DRAW/ILLEGAL
        raw: bytes = self._get_block(pc, block_id)
        if pc.entry_bytes == 1:
            stored = raw[in_block]
        else:
            stored = struct.unpack_from("<H", raw, in_block * 2)[0]
        return pc.rank_to_value[stored], pc.entry_bytes


class DTZFile(_RankFile):
    EXT = ".lzdtz"
    MAGIC = DTZ_MAGIC
    KIND = "DTZ"

    def read(self, color: int, board: chess.Board, wdl: int) -> _DTZValue:
        cell = self._read_stored(color, board)
        return _DTZValue(0, False) if cell is None else dtz_value_from_storage(cell[0], wdl, cell[1])


class DTMFile(_RankFile):
    EXT = ".lzdtm"
    MAGIC = DTM_MAGIC
    KIND = "DTM"

    def read(self, color: int, board: chess.Board, wdl: int) -> int:
        cell = self._read_stored(color, board)
        # The class supplies the parity bit; unlike DTZ, no rounding.
        return 0 if cell is None else dtm_value_from_storage(cell[0], wdl)


# --- Changepoint packs (src/probe/layered_file.h, {dtm50,dtc}_file.cpp) ---
# DTM50 stacks 101 clock layers, DTC 30 budgets plus the embedded DTZ row.
# Block decode is shared; ``read`` is per metric.

def _bit(buf: bytes, i: int) -> int:
    return (buf[i >> 3] >> (i & 7)) & 1


# --- Block-local prefix indexes ---
# Every STRIDE-th position is indexed, so a lookup walks at most one stride;
# a full index would dwarf the block.
_LAYERED_STRIDE = 256
_STATE_STRIDE_BYTES = _LAYERED_STRIDE // 4  # 2-bit states: 4 per byte
_HINT_STRIDE_BYTES = _LAYERED_STRIDE // 8   # hint bitmaps: 8 per byte

#: State-bitmap byte -> count of its fields in state `s`, for ``bytes.translate``.
_STATE_COUNT_XLAT = tuple(
    bytes(sum(1 for k in range(4) if (b >> (2 * k)) & 3 == s) for b in range(256))
    for s in range(4))

#: ``[b][q][s]``: fields before `q` of byte `b` in state `s`.
_STATE_FIELD_PREFIX = tuple(
    tuple(tuple(sum(1 for k in range(q) if (b >> (2 * k)) & 3 == s) for s in range(4))
          for q in range(4))
    for b in range(256))


def _state_stride_index(state_bits: bytes, num_positions: int) -> Tuple[array.array[int], ...]:
    """``cum[s][k]``: positions in state `s` among the first
    ``k * _LAYERED_STRIDE``. The last entry may count padding; no read uses it."""
    n_strides = _ceil_div(num_positions, _LAYERED_STRIDE)
    out = []
    for s in range(4):
        per_byte = state_bits.translate(_STATE_COUNT_XLAT[s])
        cum = array.array("q", bytes(8 * (n_strides + 1)))
        run = 0
        at = 0
        for k in range(n_strides):
            cum[k] = run
            run += sum(per_byte[at:at + _STATE_STRIDE_BYTES])
            at += _STATE_STRIDE_BYTES
        cum[n_strides] = run
        out.append(cum)
    return tuple(out)


def _state_and_index(state_bits: bytes, cum: Tuple[array.array[int], ...],
                     pos: int) -> Tuple[int, int]:
    sid, within = divmod(pos, _LAYERED_STRIDE)
    byte_in_stride, field = divmod(within, 4)
    base = sid * _STATE_STRIDE_BYTES
    b = state_bits[base + byte_in_stride]
    st = (b >> (2 * field)) & 3
    idx = cum[st][sid]
    if byte_in_stride:
        idx += sum(state_bits[base:base + byte_in_stride].translate(_STATE_COUNT_XLAT[st]))
    return st, idx + _STATE_FIELD_PREFIX[b][field][st]


def _build_hints(payload: bytes, off: int, hint_byte: int, n: int,
                 short: int, long: int) -> bytes:
    """Draw-end bits (MSB of the last h byte) of `n` variable-width records,
    as a bitmap."""
    hints = bytearray((n + 7) // 8)
    for j in range(n):
        if payload[off + hint_byte] & 0x80:
            hints[j >> 3] |= 1 << (j & 7)
            off += short
        else:
            off += long
    return bytes(hints)


def _hint_stride_index(hints: bytes, n: int) -> array.array[int]:
    n_strides = _ceil_div(n, _LAYERED_STRIDE)
    cum = array.array("q", bytes(8 * (n_strides + 1)))
    run = 0
    for k in range(n_strides):
        cum[k] = run
        chunk = hints[k * _HINT_STRIDE_BYTES:(k + 1) * _HINT_STRIDE_BYTES]
        run += chess.popcount(int.from_bytes(chunk, "little"))
    cum[n_strides] = run
    return cum


def _hint_prefix(hints: bytes, cum: array.array[int], i: int) -> int:
    """Popcount of bits [0, `i`) of a hint bitmap. Bit `i` itself is never
    read, so the bitmap only covers the entries that exist."""
    sid, within = divmod(i, _LAYERED_STRIDE)
    base = sid * _HINT_STRIDE_BYTES
    whole, rem = divmod(within, 8)
    n = cum[sid]
    if whole:
        n += chess.popcount(int.from_bytes(hints[base:base + whole], "little"))
    if rem:
        n += chess.popcount(hints[base + whole] & ((1 << rem) - 1))
    return n


class _LayeredPerColor(_PerColor):
    __slots__ = ("order", "radix", "entry_bytes", "block_positions",
                 "tail_positions", "block_cnt", "data_size", "offsets",
                 "usizes", "buf", "data_off", "rank_to_value")
    order: List[int]
    radix: List[int]
    entry_bytes: int
    block_positions: int
    tail_positions: int
    block_cnt: int
    data_size: int
    offsets: MonoUintVec
    usizes: Min0UintVec
    buf: Any
    data_off: int
    rank_to_value: List[int]
    _blocks: Dict[int, Dict[str, Any]]

    def __init__(self) -> None:
        super().__init__()


def _multi_bitmap(payload: Any, entry: int, bm_bytes: int) -> int:
    return int.from_bytes(bytes(payload[entry + 1:entry + 1 + bm_bytes]), "little")


class _LayeredFile(_TableFile):
    """Changepoint container shared by DTM50 and DTC; ``read`` is per metric."""

    PER_COLOR = _LayeredPerColor
    per_color: List[Optional[_LayeredPerColor]]

    def _on_singular(self, r: _Serial, pc: Any) -> bool:
        return r.u8() == 0  # the singular value must be DRAW

    def _parse_header(self, r: _Serial, pc: _LayeredPerColor) -> None:
        perm = r.u32()
        pc.order, pc.radix = self.index_cfg.make_layout(perm)
        pc.entry_bytes = r.u8()
        pc.block_positions = r.u32()
        pc.block_cnt = r.u64()
        pc.tail_positions = r.u32()
        pc.data_size = r.u64()
        num_ranks = r.u16()
        pc.rank_to_value = [r.u16() for _ in range(num_ranks)]

    def _finalize(self, r: _Serial) -> None:
        for c in range(2):
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            log2_bu = r.u8()
            sample_width = r.u8()
            offset_width = r.u8()
            usz_width = r.u8()
            mono_off = r.caret()
            mb = MonoUintVec.on_disk_bytes(pc.block_cnt + 1, log2_bu, sample_width, offset_width)
            r.advance(mb)
            usz_off = r.caret()
            ub = Min0UintVec.on_disk_bytes(pc.block_cnt, usz_width)
            r.advance(ub)
            pc.offsets = MonoUintVec(r.d, mono_off, pc.block_cnt + 1, log2_bu,
                                     sample_width, offset_width)
            pc.usizes = Min0UintVec(r.d, usz_off, pc.block_cnt, usz_width)
        for c in range(2):
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.buf, pc.data_off = r.d, start
            r.advance(pc.data_size)

    def _decode_block(self, pc: _LayeredPerColor, block_id: int) -> Dict[str, Any]:
        doff, dnext = pc.offsets.get2(block_id)
        dsz = dnext - doff
        usz = pc.usizes.get(block_id)
        payload = lzma_raw_decompress(
            _compressed_block(pc.buf[pc.data_off + doff:pc.data_off + doff + dsz]), usz)
        eb = pc.entry_bytes
        (num_positions, num_single, num_double, num_multi,
         single_stream_bytes, double_stream_bytes) = struct.unpack_from("<IIIIII", payload, 0)
        num_const = num_positions - num_single - num_double - num_multi
        sb_bytes = (num_positions * 2 + 7) // 8
        p = 24
        state_bits_off = p; p += sb_bytes
        const_stream_off = p; p += num_const * eb
        single_stream_off = p; p += single_stream_bytes
        double_stream_off = p; p += double_stream_bytes
        p += (4 - (p & 3)) & 3
        multi_dir_off = p; p += (num_multi + 1) * 4
        multi_data_off = p

        state_bits = payload[state_bits_off:state_bits_off + sb_bytes]
        single_hints = _build_hints(payload, single_stream_off, 0, num_single,
                                    1 + eb, 1 + 2 * eb)
        double_hints = _build_hints(payload, double_stream_off, 1, num_double,
                                    2 + 2 * eb, 2 + 3 * eb)

        state_cum = _state_stride_index(state_bits, num_positions)
        single_pre = _hint_stride_index(single_hints, num_single)
        double_pre = _hint_stride_index(double_hints, num_double)

        blk = {
            "payload": payload, "eb": eb,
            "state_bits": state_bits, "state_cum": state_cum,
            "const_stream_off": const_stream_off,
            "single_hints": single_hints, "single_stream_off": single_stream_off,
            "double_hints": double_hints, "double_stream_off": double_stream_off,
            "multi_dir_off": multi_dir_off, "multi_data_off": multi_data_off,
            "single_pre": single_pre, "double_pre": double_pre,
        }
        pc._blocks[block_id] = blk
        self.cache.record(pc, block_id, len(payload)
                          + len(single_hints) + len(double_hints)
                          + sum(a.itemsize * len(a)
                                for a in state_cum + (single_pre, double_pre)))
        return blk

    @staticmethod
    def _read_rank(payload: bytes, off: int, eb: int) -> int:
        return payload[off] if eb == 1 else int(struct.unpack_from("<H", payload, off)[0])

    def _locate(self, color: int, board: chess.Board
                ) -> Optional[Tuple[Dict[str, Any], int, int]]:
        """A position's block, record state and index within that state, or
        ``None`` if nothing is stored (drawn at every layer)."""
        pc = self.per_color[color]
        assert pc is not None
        if self.is_singular[color]:
            return None
        pos = self.index_cfg.board_index(board, pc.order, pc.radix)
        assert pos is not None
        block_id, pos_in_block = divmod(pos, pc.block_positions)
        lo, hi = pc.offsets.get2(block_id)
        if lo == hi:
            return None  # skip block (uniform DRAW)
        blk: Dict[str, Any] = self._get_block(pc, block_id)
        st, idx = _state_and_index(blk["state_bits"], blk["state_cum"], pos_in_block)
        return blk, st, idx


class DTM50File(_LayeredFile):
    EXT = ".lzdtm50"
    MAGIC = DTM50_MAGIC
    KIND = "DTM50"

    def read(self, color: int, board: chess.Board, wdl: int,
             hmc: int) -> Tuple[int, int]:
        """The value at `hmc` and the layer where the cell turns DRAW. Only the
        draw-end hint means DRAW; a stored 0 is a mate."""
        flat = (hmc == IGNORE_50MR)
        if not flat and (wdl == CURSED_WIN or wdl == BLESSED_LOSS):
            return (DRAWN_AT_LAYER, 0)
        found = self._locate(color, board)
        if found is None:
            return (DRAWN_AT_LAYER, 0)
        blk, st, idx = found
        pc = self.per_color[color]
        assert pc is not None
        payload = blk["payload"]
        eb = blk["eb"]
        r2v = pc.rank_to_value
        layer = 0 if flat else (hmc + 1)

        draw_flip = 0
        if st == 0:  # CONST: one rank at every layer
            stored = r2v[self._read_rank(payload, blk["const_stream_off"] + idx * eb, eb)]
        elif st == 1:  # SINGLE: one transition at h
            short, long = 1 + eb, 1 + 2 * eb
            n_short = _hint_prefix(blk["single_hints"], blk["single_pre"], idx)
            off = blk["single_stream_off"] + n_short * short + (idx - n_short) * long
            draw_end = _bit(blk["single_hints"], idx)
            h = payload[off] & 0x7F
            if draw_end:
                draw_flip = h
            if layer < h:
                stored = r2v[self._read_rank(payload, off + 1, eb)]
            elif draw_end:
                return (DRAWN_AT_LAYER, draw_flip)
            else:
                stored = r2v[self._read_rank(payload, off + 1 + eb, eb)]
        elif st == 2:  # DOUBLE: transitions at h1 < h2
            short, long = 2 + 2 * eb, 2 + 3 * eb
            n_short = _hint_prefix(blk["double_hints"], blk["double_pre"], idx)
            off = blk["double_stream_off"] + n_short * short + (idx - n_short) * long
            draw_end = _bit(blk["double_hints"], idx)
            h1 = payload[off]
            h2 = payload[off + 1] & 0x7F
            if draw_end:
                draw_flip = h2
            if layer < h1:
                stored = r2v[self._read_rank(payload, off + 2, eb)]
            elif layer < h2:
                stored = r2v[self._read_rank(payload, off + 2 + eb, eb)]
            elif draw_end:
                return (DRAWN_AT_LAYER, draw_flip)
            else:
                stored = r2v[self._read_rank(payload, off + 2 + 2 * eb, eb)]
        else:  # MULTI: changepoint bitmap
            entry = blk["multi_data_off"] + struct.unpack_from(
                "<I", payload, blk["multi_dir_off"] + idx * 4)[0]
            kbyte = payload[entry]
            draw_end = (kbyte & 0x80) != 0
            k = kbyte & 0x7F
            bits = _multi_bitmap(payload, entry, DTM50_MULTI_BITMAP_BYTES)
            rsel = bin(bits & ((1 << (layer + 1)) - 1)).count("1") - 1
            if draw_end:
                draw_flip = max(bits.bit_length() - 1, 0)
            if rsel == k - 1 and draw_end:
                return (DRAWN_AT_LAYER, draw_flip)
            stored = r2v[self._read_rank(
                payload, entry + 1 + DTM50_MULTI_BITMAP_BYTES + rsel * eb, eb)]

        if flat:
            return (dtm_value_from_storage(stored, wdl), draw_flip)
        return (dtm50_value_from_storage(stored, wdl), draw_flip)


def dtc_budget_plies(rule50: int) -> int:
    """Plies a DTC answer may spend before a 50-move claim: 0 once the clock
    reaches it."""
    if rule50 == IGNORE_50MR:
        return MAX_NON_CURSED_DTZ
    return 0 if rule50 >= MAX_NON_CURSED_DTZ else MAX_NON_CURSED_DTZ - rule50


class _DTCCell(NamedTuple):
    """A DTC cell at the budget fitting the caller's clock: pushes still owed
    and plies to the next zeroing move. ``dtz`` is the unbounded row, the only
    one a cursed class has."""

    order: int = 0
    value: int = DRAWN_AT_LAYER
    dtz: int = DRAWN_AT_LAYER
    dtz_rounded: bool = False

    @property
    def priced(self) -> bool:
        return self.value != DRAWN_AT_LAYER


class _BudgetSegments(NamedTuple):
    """A position's value per push budget. Budget falls as the row rises, so
    `segs` ascends in both row and value; `draw_start` is where a trailing
    DRAW segment begins."""

    segs: List[Tuple[int, int]]
    draw_start: Optional[int]

    def end_of(self, i: int) -> int:
        if i + 1 < len(self.segs):
            return self.segs[i + 1][0]
        return DTC_PACK_LAYERS if self.draw_start is None else self.draw_start


class DTCFile(_LayeredFile):
    EXT = ".lzdtc"
    MAGIC = DTC_MAGIC
    KIND = "DTC"

    def _segments(self, color: int, board: chess.Board) -> Optional[_BudgetSegments]:
        found = self._locate(color, board)
        if found is None:
            return None
        blk, st, idx = found
        pc = self.per_color[color]
        assert pc is not None
        payload = blk["payload"]
        eb = blk["eb"]
        r2v = pc.rank_to_value
        rank = self._read_rank
        if st == 0:  # CONST: one value at every budget
            off = blk["const_stream_off"] + idx * eb
            return _BudgetSegments([(0, r2v[rank(payload, off, eb)])], None)
        if st == 1:  # SINGLE: one changepoint at h
            short, long = 1 + eb, 1 + 2 * eb
            n_short = _hint_prefix(blk["single_hints"], blk["single_pre"], idx)
            off = blk["single_stream_off"] + n_short * short + (idx - n_short) * long
            draw_end = _bit(blk["single_hints"], idx)
            h = payload[off] & 0x7F
            segs = [(0, r2v[rank(payload, off + 1, eb)])]
            if draw_end:
                return _BudgetSegments(segs, h)
            segs.append((h, r2v[rank(payload, off + 1 + eb, eb)]))
            return _BudgetSegments(segs, None)
        if st == 2:  # DOUBLE: changepoints at h1 < h2
            short, long = 2 + 2 * eb, 2 + 3 * eb
            n_short = _hint_prefix(blk["double_hints"], blk["double_pre"], idx)
            off = blk["double_stream_off"] + n_short * short + (idx - n_short) * long
            draw_end = _bit(blk["double_hints"], idx)
            h1 = payload[off]
            h2 = payload[off + 1] & 0x7F
            segs = [(0, r2v[rank(payload, off + 2, eb)]),
                    (h1, r2v[rank(payload, off + 2 + eb, eb)])]
            if draw_end:
                return _BudgetSegments(segs, h2)
            segs.append((h2, r2v[rank(payload, off + 2 + 2 * eb, eb)]))
            return _BudgetSegments(segs, None)
        entry = blk["multi_data_off"] + struct.unpack_from(
            "<I", payload, blk["multi_dir_off"] + idx * 4)[0]
        kbyte = payload[entry]
        draw_end = (kbyte & 0x80) != 0
        k = kbyte & 0x7F
        bits = _multi_bitmap(payload, entry, DTC_MULTI_BITMAP_BYTES)
        rows = []
        while bits:
            low = bits & -bits
            rows.append(low.bit_length() - 1)
            bits ^= low
        decisive = k - 1 if draw_end else k
        ranks = entry + 1 + DTC_MULTI_BITMAP_BYTES
        segs = [(rows[n], r2v[rank(payload, ranks + n * eb, eb)])
                for n in range(decisive)]
        return _BudgetSegments(segs, rows[k - 1] if draw_end else None)

    def read(self, color: int, board: chess.Board, wdl: int,
             rule50: int) -> _DTCCell:
        """The fewest pushes whose plies-to-zeroing fit within `rule50`: the
        deepest budget row that fits. Fewer pushes may take more plies."""
        seg = self._segments(color, board)
        if seg is None:
            return _DTCCell()

        dtz = seg.segs[0][1]
        if wdl == CURSED_WIN or wdl == BLESSED_LOSS:
            return _DTCCell(dtz=dtz, dtz_rounded=bool(dtz & 1))

        budget_plies = dtc_budget_plies(rule50)
        for i in range(len(seg.segs) - 1, -1, -1):
            value = seg.segs[i][1]
            if value > budget_plies:
                continue
            return _DTCCell(DTC_BUDGET_LAYERS - (seg.end_of(i) - 1), value, dtz)
        return _DTCCell(dtz=dtz)

    def read_curve(self, color: int, board: chess.Board, wdl: int) -> List[int]:
        """The value at every budget rather than at one clock, with
        ``DRAWN_AT_LAYER`` where a budget settles nothing (everywhere for a
        cursed class). The last entry is the embedded DTZ endpoint."""
        curve = [DRAWN_AT_LAYER] * DTC_PACK_LAYERS
        if wdl == CURSED_WIN or wdl == BLESSED_LOSS:
            return curve
        seg = self._segments(color, board)
        if seg is None:
            return curve
        for i, (start, value) in enumerate(seg.segs):
            for row in range(start, seg.end_of(i)):
                curve[DTC_BUDGET_LAYERS - row] = value
        return curve


# --- Probe orchestration (src/probe/probe.cpp) ---

def prefer_new(new_wdl: int, new_dtz: int, old_wdl: int, old_dtz: int) -> bool:
    rn, ro = wdl_rank(new_wdl), wdl_rank(old_wdl)
    if rn != ro:
        return rn > ro
    if new_wdl in (WIN, CURSED_WIN):
        return new_dtz < old_dtz
    if new_wdl in (LOSE, BLESSED_LOSS):
        return new_dtz > old_dtz
    return False


def prefer_new_dtc(new_wdl: int, new_order: int, new_value: int,
                   old_wdl: int, old_order: int, old_value: int) -> bool:
    rn, ro = wdl_rank(new_wdl), wdl_rank(old_wdl)
    if rn != ro:
        return rn > ro
    if new_wdl in (WIN, CURSED_WIN):
        return (new_order < old_order if new_order != old_order
                else new_value < old_value)
    if new_wdl in (LOSE, BLESSED_LOSS):
        return (new_order > old_order if new_order != old_order
                else new_value > old_value)
    return False


def offer_dtz(child_wdl: int, dtz: int, best_wdl: int, best_dtz: int) -> Tuple[int, int]:
    """Offer a move to `child_wdl` at `dtz` to the mover's best; returns the new
    best. Past 100 plies a decisive class turns cursed."""
    my_wdl = invert_wdl(child_wdl)
    if dtz > MAX_NON_CURSED_DTZ:
        if my_wdl == WIN:
            my_wdl = CURSED_WIN
        elif my_wdl == LOSE:
            my_wdl = BLESSED_LOSS
    if prefer_new(my_wdl, dtz, best_wdl, best_dtz):
        return my_wdl, dtz
    return best_wdl, best_dtz


def below_pinned_class(pinned: int, offer: int) -> bool:
    """Whether `offer` ranks below the class already known for the parent, so
    the child can't win the minimax and needn't be probed. ILLEGAL pins
    nothing."""
    return pinned != ILLEGAL and wdl_rank(offer) < wdl_rank(pinned)


def child_class_is_forced(pinned: int) -> bool:
    """Under a LOSE pin every child can be taken as WIN: exactly pinned, each is
    a clean WIN (else the parent would be BLESSED_LOSS); folded for DTM, WIN
    and CURSED_WIN minimax alike."""
    return pinned == LOSE


def dtz_lift(my_wdl: int) -> int:
    """A DTZ minimax lifts a LOSE to BLESSED_LOSS past 100."""
    return BLESSED_LOSS if my_wdl == LOSE else my_wdl


def fold_dtm_wdl(w: int) -> int:
    if w == CURSED_WIN:
        return WIN
    if w == BLESSED_LOSS:
        return LOSE
    return w


def fold_50mr_wdl(w: int) -> int:
    """5-class WDL -> the three a clocked metric holds: cursed and blessed are
    draws under the 50-move rule."""
    if w == CURSED_WIN or w == BLESSED_LOSS:
        return DRAW
    return w


def dtz_from_draw_flip(h: int, wdl: int, board: chess.Board) -> Optional[int]:
    """DTZ of a W/L cell from its DRAW flip layer `h` (layer = hmc + 1): still
    decisive at hmc = 100 - dtz, so h = 102 - dtz. h == 1 (drawn at a fresh
    clock) can't be determined; no flip means dtz <= 1, split by mate. DRAW
    and ILLEGAL give 0."""
    if wdl == DRAW or wdl == ILLEGAL:
        return 0
    if wdl not in (WIN, LOSE):
        return None
    if h == 0:
        return 0 if (wdl == LOSE and board.is_checkmate()) else 1
    if h == 1:
        return None
    return MAX_NON_CURSED_DTZ + 2 - h


# Layer bounds at `rule50`, W/L only (cursed and blessed are DRAW in every layer).
# Pinned: rule50 + dtm <= 100, so the layer is the flat DTM (a mate on the 100th
# ply beats the claim). Busted: rule50 + dtz > 100, so the layer is DRAW.
# An unknown distance reads as 0: check has_dtm before trusting a pin.
def dtm50_layer_pinned_by_dtm(wdl: int, dtm: int, rule50: int) -> bool:
    if wdl not in (WIN, LOSE):
        return False
    return rule50 + dtm <= MAX_NON_CURSED_DTZ


def layer_busted_by_dtz(wdl: int, dtz: int, rule50: int) -> bool:
    if wdl not in (WIN, LOSE):
        return False
    return rule50 + dtz > MAX_NON_CURSED_DTZ


class _DTM50Result(NamedTuple):
    """A DTM50 answer, with DTZ riding along."""

    wdl: int
    dtm: int
    has_dtz: bool = False
    dtz: int = 0


class _SkippedChildren:
    """Children a derive couldn't price. A skip unpins the minimax only if its
    class could match or beat the kept best; an unknown class always does."""

    __slots__ = ("_best_rank", "_any_unknown")

    def __init__(self) -> None:
        self._best_rank = -1
        self._any_unknown = False

    def of_class(self, my_wdl: int) -> None:
        self._best_rank = max(self._best_rank, wdl_rank(my_wdl))

    def of_dtz_class(self, my_wdl: int) -> None:
        self.of_class(dtz_lift(my_wdl))

    def unknown(self) -> None:
        self._any_unknown = True

    def unpin(self, best_wdl: int) -> bool:
        return self._any_unknown or self._best_rank >= wdl_rank(best_wdl)


def _is_cursed_exit(parent: chess.Board, child: chess.Board, child_wdl: int) -> bool:
    return (child_wdl in (CURSED_WIN, BLESSED_LOSS)
            and chess.popcount(child.clean_castling_rights())
            < chess.popcount(parent.clean_castling_rights()))


def _quiet_move_dtz(child_dtz: int, cursed_exit: bool, child_rounded: bool) -> int:
    v = child_dtz + 1
    if not cursed_exit:
        return v
    return v + 1 if child_rounded else v | 1


class _DTZMinimax:
    """DTZ minimax run beside the mate distance over the same children, since
    zeroing distance ranks moves differently."""

    __slots__ = ("_best_wdl", "_best_dtz", "_skipped")

    def __init__(self) -> None:
        self._best_wdl = LOSE
        self._best_dtz = 0
        self._skipped = _SkippedChildren()

    def zeroing_child(self, child_wdl: int) -> None:
        self._best_wdl, self._best_dtz = offer_dtz(
            child_wdl, 1, self._best_wdl, self._best_dtz)

    def quiet_child(self, child_wdl: int, child: _DTM50Result, cursed_exit: bool) -> None:
        if child.has_dtz:
            self._best_wdl, self._best_dtz = offer_dtz(
                child_wdl, _quiet_move_dtz(child.dtz, cursed_exit, False),
                self._best_wdl, self._best_dtz)
        else:
            self._skipped.of_dtz_class(invert_wdl(child_wdl))

    def unwalked(self) -> None:
        self._skipped.unknown()

    def finish(self, wdl: int, dtm: int, any_legal: bool) -> _DTM50Result:
        if not any_legal:  # mate or stalemate
            return _DTM50Result(wdl, dtm, True, 0)
        if self._skipped.unpin(self._best_wdl):
            return _DTM50Result(wdl, dtm)
        return _DTM50Result(wdl, dtm, True,
                            0 if self._best_wdl == DRAW else self._best_dtz)


class _UnboundedFold:
    """Minimax for DTC's unbounded DTZ row. One drawn child leaves the row
    unanswered: a best over only some of the moves would be wrong."""

    __slots__ = ("_winning", "_have", "_drawn", "_any_rounded", "_best")

    def __init__(self, mover_class: int) -> None:
        self._winning = mover_class in (WIN, CURSED_WIN)
        self._have = False
        self._drawn = False
        self._any_rounded = False
        self._best = 0

    def zeroing_child(self) -> None:
        self._offer(1)

    def quiet_child(self, child_dtz: int, cursed_exit: bool, child_rounded: bool) -> None:
        if child_dtz == DRAWN_AT_LAYER:
            self._drawn = True
        else:
            self._offer(_quiet_move_dtz(child_dtz, cursed_exit, child_rounded))
            self._any_rounded |= child_rounded

    def value(self) -> int:
        return self._best if (self._have and not self._drawn) else DRAWN_AT_LAYER

    def rounded(self) -> bool:
        return self._any_rounded

    def _offer(self, v: int) -> None:
        if not self._have or (v < self._best if self._winning else v > self._best):
            self._best = v
        self._have = True


def _ep_capture_moves(
    board: chess.Board, ep_square: int
) -> Tuple[chess.Board, List[chess.Move]]:
    bcopy = board.copy(stack=False)
    bcopy.ep_square = ep_square
    return bcopy, list(bcopy.generate_legal_ep())


class ProbeResult:
    """Outcome of :meth:`Tablebase.probe`.

    ``wdl`` is :data:`ILLEGAL` where the tables can't answer. ``wdl``,
    ``wdl50``, ``dtc_wdl`` and ``dtm50_wdl`` are :data:`WIN`..:data:`LOSE`
    codes; ``wdl`` ignores the clock, ``wdl50`` is the result at the probed
    halfmove clock. ``dtz``/``dtc``/``dtm``/``dtm50`` are unsigned plies,
    signed by the matching WDL class. ``dtc_order`` is the pushes the winner
    still owes; ``dtc_wdl`` is the DTC result, a 50-move draw included.
    ``dtz_rounded`` says ``dtz`` may be a ply off. Each ``has_*`` flag says
    whether its field could be determined.
    """

    __slots__ = ("wdl", "has_dtz", "dtz", "dtz_rounded", "has_wdl50", "wdl50",
                 "has_dtc", "dtc_wdl", "dtc_order", "dtc", "has_dtm", "dtm",
                 "has_dtm50", "dtm50_wdl", "dtm50")

    wdl: int
    has_dtz: bool
    dtz: int
    dtz_rounded: bool
    has_wdl50: bool
    wdl50: int
    has_dtc: bool
    dtc_wdl: int
    dtc_order: int
    dtc: int
    has_dtm: bool
    dtm: int
    has_dtm50: bool
    dtm50_wdl: int
    dtm50: int

    def __init__(self) -> None:
        self.wdl = ILLEGAL
        self.has_dtz = False
        self.dtz = 0
        self.dtz_rounded = False
        self.has_wdl50 = False
        self.wdl50 = ILLEGAL
        self.has_dtc = False
        self.dtc_wdl = ILLEGAL
        self.dtc_order = 0
        self.dtc = 0
        self.has_dtm = False
        self.dtm = 0
        self.has_dtm50 = False
        self.dtm50_wdl = ILLEGAL
        self.dtm50 = 0

    def __repr__(self) -> str:
        s = f"<ProbeResult wdl={_WDL_NAME[self.wdl]}"
        if self.has_dtz:
            s += f" dtz={self.dtz}"
        if self.has_wdl50:
            s += f" wdl50={_WDL_NAME[self.wdl50]}"
        if self.has_dtc:
            s += f" dtc={_WDL_NAME[self.dtc_wdl]}/{self.dtc_order}/{self.dtc}"
        if self.has_dtm:
            s += f" dtm={self.dtm}"
        if self.has_dtm50:
            s += f" dtm50={_WDL_NAME[self.dtm50_wdl]}/{self.dtm50}"
        return s + ">"


def _fill_dtm50_from_bounds(r: ProbeResult, rule50: int) -> None:
    if rule50 == IGNORE_50MR:
        return
    if rule50 >= DTM50_HMC_COUNT:
        if r.wdl == LOSE and not r.has_dtm:
            return
        r.dtm50_wdl = LOSE if (r.wdl == LOSE and r.dtm == 0) else DRAW
    elif (fold_50mr_wdl(r.wdl) == DRAW
            or (r.has_dtz and layer_busted_by_dtz(r.wdl, r.dtz, rule50))):
        r.dtm50_wdl = DRAW
    elif r.has_dtm and dtm50_layer_pinned_by_dtm(r.wdl, r.dtm, rule50):
        r.dtm50_wdl = r.wdl
        r.dtm50 = r.dtm
    else:
        return
    r.has_dtm50 = True


def _fill_dtc_from_bounds(r: ProbeResult, has_pawns: bool, rule50: int) -> None:
    if rule50 == IGNORE_50MR:
        return
    if r.wdl not in (WIN, LOSE):
        r.has_dtc = True
        r.dtc_wdl = DRAW
        return
    if not r.has_dtz:
        return

    busted = r.dtz > dtc_budget_plies(rule50)
    if has_pawns and not busted:
        return
    r.has_dtc = True
    r.dtc_wdl = DRAW if busted else r.wdl
    r.dtc = 0 if busted else r.dtz


def _fill_wdl50(r: ProbeResult, rule50: int) -> None:
    if rule50 == IGNORE_50MR or r.wdl == ILLEGAL:
        return
    if fold_50mr_wdl(r.wdl) == DRAW:
        r.wdl50 = DRAW
    elif r.has_dtz:
        r.wdl50 = DRAW if layer_busted_by_dtz(r.wdl, r.dtz, rule50) else r.wdl
    else:
        return
    r.has_wdl50 = True


class MissingTableError(KeyError):
    """Raised when the tables a probe needs are not available."""


_WDL_SIGNED = {WIN: 2, CURSED_WIN: 1, DRAW: 0, BLESSED_LOSS: -1, LOSE: -2}


def _signed(magnitude: int, wdl: int) -> int:
    if wdl in (WIN, CURSED_WIN):
        return magnitude
    if wdl in (LOSE, BLESSED_LOSS):
        return -magnitude
    return 0


# --- Tablebase ---

class Tablebase:
    """Probes a directory tree of chesstb tables. Use :func:`open_tablebase`.

    *directory* may hold ``wdl/``, ``dtz/``, ``dtc/``, ``dtm/`` and ``dtm50/``
    subdirectories or the table files directly. Share one instance between
    all probing threads.
    """

    #: Table classes opened per kind. A transport sets its own subclasses
    #: here and overrides :meth:`_find`.
    WDL_FILE: Type[WDLFile] = WDLFile
    DTZ_FILE: Type[DTZFile] = DTZFile
    DTC_FILE: Type[DTCFile] = DTCFile
    DTM_FILE: Type[DTMFile] = DTMFile
    DTM50_FILE: Type[DTM50File] = DTM50File

    KINDS = ("wdl", "dtz", "dtc", "dtm", "dtm50")

    def __init__(self, directory: str, *, block_cache_bytes: int = DEFAULT_BLOCK_CACHE_BYTES):
        self.dirs: Dict[str, List[str]] = {kind: [] for kind in self.KINDS}
        # Per kind: the open tables, ``None`` for "looked, no such table".
        self._caches: Dict[str, Dict[CacheKey, Any]] = {kind: {} for kind in self.KINDS}
        # Per kind, guarding its cache and ``dirs`` entry. Held only across a
        # first open, never a probe; taken in KINDS order.
        self._open_locks: Dict[str, threading.Lock] = {
            kind: threading.Lock() for kind in self.KINDS}
        self._read_condition = threading.Condition()
        self._read_count = 0
        # (men, rights, pair) -> (config, mirrored): see :meth:`_canonical_root`.
        self._roots: Dict[Tuple[Tuple[int, ...], int, int, bool], Tuple[PieceConfig, bool]] = {}
        self._block_cache = _BlockCache(block_cache_bytes)
        self.add_directory(directory)

    def add_directory(self, directory: str) -> None:
        """Adds a search directory. Each kind searches its subdirectory
        (``wdl/``, ``dtz/``, …) if present, else *directory* itself.
        Duplicates are ignored.

        Safe to call while other threads probe, but materials already looked
        up are not looked up again.
        """
        for kind in self.KINDS:
            sub = os.path.join(directory, kind)
            d = sub if os.path.isdir(sub) else directory
            with self._open_locks[kind]:
                key = os.path.normpath(d)
                if all(os.path.normpath(e) != key for e in self.dirs[kind]):
                    self.dirs[kind].append(d)

    def close(self) -> None:
        """Closes all tables and drops cached blocks, after waiting for
        probes in progress on other threads. Later probes reopen what they
        need, so a continuous stream of probes can keep this waiting.
        """
        with self._read_condition:
            while self._read_count > 0:
                self._read_condition.wait()
            self._block_cache.clear()
            self._roots.clear()
            for kind in self.KINDS:
                with self._open_locks[kind]:
                    self._close_all(self._caches[kind])

    @staticmethod
    def _close_all(cache: Dict[CacheKey, Optional[_TableFile]]) -> None:
        while cache:
            _, table = cache.popitem()
            if table is not None:
                table.close()

    def __enter__(self) -> "Tablebase":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # --- table file resolution / caching ---
    def _find(self, kind: str, name: str, ext: str) -> Optional[TableSource]:
        """A source :meth:`_TableFile._open_source` opens, or ``None``."""
        for d in self.dirs[kind]:
            p = os.path.join(d, name + ext)
            if _exists_case_exact(p):
                return p
        return None

    # A cached None means "no such table", hence subscripting, not .get().
    # Only a first open takes the lock, re-checking inside.
    def _open(self, kind: str, cfg: PieceConfig) -> Any:
        cache = self._caches[kind]
        k = cfg.cache_key
        try:
            return cache[k]
        except KeyError:
            pass
        with self._table_open_lock(kind, k):
            try:
                return cache[k]
            except KeyError:
                pass
            cls = getattr(self, kind.upper() + "_FILE")
            p = self._find(kind, cfg.name(), cls.EXT)
            table = cls(cfg, p, self._block_cache) if p is not None else None
            cache[k] = table
            return table

    def _table_open_lock(self, kind: str, cache_key: CacheKey) -> Any:
        """Lock for a table's first open; per kind, also guarding ``dirs``.
        A transport may narrow it per table."""
        return self._open_locks[kind]

    def _open_wdl(self, cfg: PieceConfig) -> Optional[WDLFile]:
        return self._open("wdl", cfg)  # type: ignore[no-any-return]

    def _open_dtz(self, cfg: PieceConfig) -> Optional[DTZFile]:
        return self._open("dtz", cfg)  # type: ignore[no-any-return]

    def _open_dtm(self, cfg: PieceConfig) -> Optional[DTMFile]:
        return self._open("dtm", cfg)  # type: ignore[no-any-return]

    def _open_dtc(self, cfg: PieceConfig) -> Optional[DTCFile]:
        return self._open("dtc", cfg)  # type: ignore[no-any-return]

    def _open_dtm50(self, cfg: PieceConfig) -> Optional[DTM50File]:
        return self._open("dtm50", cfg)  # type: ignore[no-any-return]

    # --- child construction for the derive / overlay paths ---
    def _make_child(self, parent: chess.Board, move: chess.Move
                    ) -> Tuple[PieceConfig, chess.Board, Optional[int], bool]:
        zeroing = parent.is_zeroing(move)
        child = parent.copy(stack=False)
        child.push(move)  # also sets child.ep_square on a double push
        # Routes to a 'p' or 'r' material if the move keeps a pair or right.
        cfg, cboard, ep = self._canonical_root(child)
        return cfg, cboard, ep, zeroing

    # --- WDL ---
    def _relax_bound_wdl(self, board: chess.Board, depth: int) -> int:
        """Best class a capture or promotion reaches. Those children are in
        sub-tables, so this never re-enters the frame being resolved."""
        if depth >= MAX_DERIVE_DEPTH:
            return ILLEGAL
        b = _internal_board(board)
        best = LOSE
        promo_rank = chess.BB_RANK_8 if b.turn == chess.WHITE else chess.BB_RANK_1
        for m in b.generate_legal_moves(to_mask=b.occupied_co[not b.turn] | promo_rank):
            if m.promotion is None and not b.is_capture(m):
                continue
            cfg_c, cboard, cep, _zeroing = self._make_child(b, m)
            cw = DRAW if cfg_c.is_bare_kings else self._probe_wdl_impl(
                cfg_c, cboard, cep, depth + 1)
            if cw == ILLEGAL:
                best = ILLEGAL
                continue
            mine = invert_wdl(cw)
            if mine == WIN:
                return WIN
            if best != ILLEGAL and wdl_rank(mine) > wdl_rank(best):
                best = mine
        return best

    def _raise_by_bound(self, w: WDLFile, frame: int, stored: int,
                        board: chess.Board, depth: int) -> int:
        """A relaxed frame stores no better than the truth, and worse only
        where :meth:`_relax_bound_wdl` reaches it."""
        if not w.is_relaxed[frame] or stored == ILLEGAL or stored == WIN:
            return stored
        bound = self._relax_bound_wdl(board, depth)
        if bound == ILLEGAL:
            return ILLEGAL
        return bound if wdl_rank(bound) > wdl_rank(stored) else stored

    def _read_wdl_stored(self, w: Optional[WDLFile], board: chess.Board,
                         depth: int) -> int:
        if w is None:
            return 7  # WDL_Stored::ILLEGAL
        color = side_index(board.turn)
        s = w.read(color, board)
        if not w.is_relaxed[color] or s == 7 or s == WIN:
            return s
        bound = self._relax_bound_wdl(board, depth)
        if bound == ILLEGAL:
            return 7  # WDL_Stored::ILLEGAL
        return bound if stored_rank(bound) > stored_rank(s) else s

    def _probe_wdl_internal(self, w: Optional[WDLFile], cfg: PieceConfig,
                            board: chess.Board, depth: int) -> int:
        if w is None:
            return ILLEGAL
        color = side_index(board.turn)
        if w.is_dropped[color]:
            if not is_symmetric_material(cfg):
                return self._derive_wdl(board, depth)
            mp = mirror_for_canonical(board)
            mc = side_index(mp.turn)
            return self._raise_by_bound(w, mc, wdl_from_storage(w.read(mc, mp)),
                                        board, depth)
        return self._raise_by_bound(w, color, wdl_from_storage(w.read(color, board)),
                                    board, depth)

    def _derive_wdl(self, board: chess.Board, depth: int) -> int:
        if depth >= MAX_DERIVE_DEPTH:
            return ILLEGAL
        b = _internal_board(board)
        any_legal = False
        best = LOSE
        skipped = _SkippedChildren()
        for m in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, zeroing = self._make_child(b, m)
            if cfg_c.is_bare_kings:
                mw = DRAW
            elif zeroing:
                cw = self._probe_wdl_impl(cfg_c, cboard, cep, depth + 1)
                if cw == ILLEGAL:
                    skipped.unknown()
                    continue
                mw = invert_wdl(cw)
            else:
                cs = self._read_wdl_stored(self._open_wdl(cfg_c), cboard, depth + 1)
                if cs == 7:
                    skipped.unknown()
                    continue
                mw = invert_stored(cs)
            if wdl_rank(mw) > wdl_rank(best):
                best = mw
            if best == WIN:
                return best
        if not any_legal:
            return LOSE if b.is_check() else DRAW
        if skipped.unpin(best):
            return ILLEGAL
        return best

    def _probe_wdl_impl(self, cfg: PieceConfig, board: chess.Board,
                        ep_square: Optional[int], depth: int) -> int:
        best = self._probe_wdl_internal(self._open_wdl(cfg), cfg, board, depth)
        if best == ILLEGAL or best == WIN or ep_square is None:
            return best
        bcopy, eps = _ep_capture_moves(board, ep_square)
        if not eps:
            return best
        has_non_ep_move = any(board.legal_moves)
        any_ep = False
        unresolved_ep = False
        for m in eps:
            cfg_c, cboard, _cep, _ = self._make_child(bcopy, m)
            cw = DRAW if cfg_c.is_bare_kings else self._probe_wdl_internal(
                self._open_wdl(cfg_c), cfg_c, cboard, depth + 1)
            if cw == ILLEGAL:
                unresolved_ep = True
                continue
            mine = invert_wdl(cw)
            if ((not has_non_ep_move and not any_ep)
                    or wdl_rank(mine) > wdl_rank(best)):
                best = mine
            any_ep = True
            if best == WIN:
                break
        if unresolved_ep and best != WIN:
            return ILLEGAL
        return best

    # --- DTZ ---
    def _probe_dtz_internal(self, d: Optional[DTZFile], cfg: PieceConfig,
                            board: chess.Board, wdl: int, depth: int) -> Optional[_DTZValue]:
        if d is None:
            return None
        color, mp, readable = locate_frame(d, cfg, board, wdl)
        if not readable:
            return self._derive_dtz(board, wdl, depth)
        if d.is_relaxed[color] and is_win_class(wdl):
            derived = self._derive_dtz(board, wdl, depth, True)
            if derived is None or derived.dtz == 1:
                return derived
        return d.read(color, board if mp is None else mp, wdl)

    def _derive_dtz(self, board: chess.Board, wdl: int, depth: int,
                    zeroing_only: bool = False) -> Optional[_DTZValue]:
        if depth >= MAX_DERIVE_DEPTH:
            return None
        b = _internal_board(board)
        any_legal = False
        best_wdl, best_dtz = LOSE, 0
        rounded = False
        skipped = _SkippedChildren()
        for m in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, zeroing = self._make_child(b, m)
            if cfg_c.is_bare_kings:
                cw, my_dtz = DRAW, 1
            elif zeroing:
                if child_class_is_forced(wdl):
                    cw = WIN
                else:
                    cw = self._probe_wdl_impl(cfg_c, cboard, cep, depth + 1)
                    if cw == ILLEGAL:
                        skipped.unknown()
                        continue
                my_dtz = 1
            else:
                if zeroing_only:
                    continue
                if child_class_is_forced(wdl):
                    cw = WIN
                else:
                    cw = self._probe_wdl_internal(self._open_wdl(cfg_c), cfg_c, cboard, depth + 1)
                    if cw == ILLEGAL:
                        skipped.unknown()
                        continue
                    if below_pinned_class(wdl, dtz_lift(invert_wdl(cw))):
                        continue
                child_dtz = self._probe_dtz_internal(self._open_dtz(cfg_c), cfg_c, cboard, cw, depth + 1)
                if child_dtz is None:
                    skipped.of_dtz_class(invert_wdl(cw))
                    continue
                my_dtz = _quiet_move_dtz(child_dtz.dtz, _is_cursed_exit(b, cboard, cw),
                                         child_dtz.rounded)
                rounded |= child_dtz.rounded
            best_wdl, best_dtz = offer_dtz(cw, my_dtz, best_wdl, best_dtz)
            if wdl in (WIN, CURSED_WIN) and best_wdl == wdl and best_dtz == 1:
                return _DTZValue(best_dtz, False)
        if not any_legal:
            return _DTZValue(0, False)
        if skipped.unpin(best_wdl):
            return None
        if zeroing_only or best_wdl == DRAW:
            return _DTZValue(0, False)
        return _DTZValue(best_dtz, rounded)

    # --- DTC (whose unbounded row answers DTZ too) ---
    def _probe_dtc_internal(self, c: Optional[DTCFile], cfg: PieceConfig,
                            board: chess.Board, wdl: int, rule50: int,
                            depth: int) -> Optional[_DTCCell]:
        if c is None:
            return None
        color, mp, readable = locate_frame(c, cfg, board, wdl)
        if not readable:
            return self._derive_dtc(board, wdl, rule50, depth)
        return c.read(color, board if mp is None else mp, wdl, rule50)

    def _read_dtc_curve(self, c: Optional[DTCFile], cfg: PieceConfig,
                        board: chess.Board, wdl: int) -> Optional[List[int]]:
        """The whole stored record of *board*, for a derive to minimax over,
        or ``None`` if its frame is not stored."""
        if c is None:
            return None
        color, mp, readable = locate_frame(c, cfg, board, wdl)
        if not readable:
            return None
        return c.read_curve(color, board if mp is None else mp, wdl)

    @staticmethod
    def _dtc_move_kind(board: chess.Board, move: chess.Move) -> Tuple[bool, bool]:
        """(conversion, push): a capture or promotion converts; any other
        pawn move is a push."""
        conversion = move.promotion is not None or board.is_capture(move)
        push = not conversion and board.piece_type_at(move.from_square) == chess.PAWN
        return conversion, push

    def _child_dtc_cell(self, cfg_c: PieceConfig, cboard: chess.Board,
                        cep: Optional[int], cw: int, child_rule50: int,
                        depth: int) -> Optional[_DTCCell]:
        """The child's DTC answer. A child with ep rights goes through the ep
        overlay, since its own record can't express the ep capture."""
        if cep is None:
            return self._probe_dtc_internal(self._open_dtc(cfg_c), cfg_c, cboard,
                                            cw, child_rule50, depth)
        cr = self._probe_impl(cfg_c, cboard, child_rule50, cep, depth)
        if not cr.has_dtc or not cr.has_dtz:
            return None
        if cr.dtc_wdl == DRAW:
            return _DTCCell(dtz=cr.dtz, dtz_rounded=cr.dtz_rounded)
        return _DTCCell(cr.dtc_order, cr.dtc, cr.dtz, cr.dtz_rounded)

    def _ep_conversion_wins(self, cboard: chess.Board, cep: int,
                            depth: int) -> Optional[bool]:
        """Whether an ep capture out of the child wins for the capturer;
        ``None`` if none is known to win and some can't be resolved. *depth*
        is the child's."""
        bcopy, eps = _ep_capture_moves(cboard, cep)
        unknown = False
        for mv in eps:
            cfg_g, gboard, gep, _zeroing = self._make_child(bcopy, mv)
            gw = DRAW if cfg_g.is_bare_kings else self._probe_wdl_impl(
                cfg_g, gboard, gep, depth + 1)
            if gw == ILLEGAL:
                unknown = True
                continue
            if fold_50mr_wdl(invert_wdl(gw)) == WIN:
                return True
        return None if unknown else False

    def _derive_dtc(self, board: chess.Board, wdl: int, rule50: int,
                    depth: int) -> Optional[_DTCCell]:
        """DTC by one-ply minimax for a frame the file doesn't hold. A
        conversion is terminal at value 1; a winner's push reads one budget
        lower. A win takes the cheapest budget any move offers, a loss the
        budget the most stubborn defense forces."""
        if depth >= MAX_DERIVE_DEPTH:
            return None
        if wdl == WIN:
            return self._derive_dtc_win(board, rule50, depth)
        if wdl == LOSE:
            return self._derive_dtc_loss(board, rule50, depth)
        return self._derive_dtc_cursed(board, wdl, depth)

    def _derive_dtc_win(self, board: chess.Board, rule50: int,
                        depth: int) -> Optional[_DTCCell]:
        b = _internal_board(board)
        have = False
        best_order = best_value = 0
        budget_plies = dtc_budget_plies(rule50)
        unbounded = _UnboundedFold(WIN)
        skipped = _SkippedChildren()
        for m in b.legal_moves:
            conversion, push = self._dtc_move_kind(b, m)
            cfg_c, cboard, cep, _zeroing = self._make_child(b, m)
            if cfg_c.is_bare_kings:
                continue
            cw = self._probe_wdl_impl(cfg_c, cboard, cep, depth + 1)
            if cw == ILLEGAL:
                skipped.unknown()
                continue
            if cw != LOSE:
                continue
            order, value = 0, 1
            if conversion:
                unbounded.zeroing_child()
            else:
                child_rule50 = 0 if push else (
                    1 if rule50 == IGNORE_50MR else rule50 + 1)
                cell = self._child_dtc_cell(cfg_c, cboard, cep, cw,
                                            child_rule50, depth + 1)
                if cell is None:
                    skipped.unknown()
                    continue
                if push:
                    unbounded.zeroing_child()
                else:
                    unbounded.quiet_child(cell.dtz, False, False)
                if not cell.priced:
                    continue  # that clock has taken this line
                order = cell.order + (1 if push else 0)
                value = 1 if push else cell.value + 1
            if value > budget_plies:
                continue
            if not have or order < best_order or (order == best_order
                                                  and value < best_value):
                best_order, best_value, have = order, value, True
            if best_order == 0 and best_value == 1:
                return _DTCCell(best_order, best_value, 1)
        if skipped.unpin(WIN):
            return None
        dtz = unbounded.value()
        return _DTCCell(best_order, best_value, dtz) if have else _DTCCell(dtz=dtz)

    def _derive_dtc_loss(self, board: chess.Board, rule50: int,
                         depth: int) -> Optional[_DTCCell]:
        """Walks each child's whole record: the longest wait at the highest
        budget any defense needs isn't what a child's cheapest budget reports.
        Every child wins for the opponent, so no class is read."""
        b = _internal_board(board)
        worst = [0] * DTC_PACK_LAYERS
        drawn = [False] * DTC_PACK_LAYERS
        any_legal = False
        unbounded = _UnboundedFold(LOSE)

        def raise_at(k: int, val: int) -> None:
            if val > MAX_NON_CURSED_DTZ:
                drawn[k] = True
            elif val > worst[k]:
                worst[k] = val

        for m in b.legal_moves:
            any_legal = True
            # Only a capture can bare the kings, so `conversion` already covers that.
            conversion, push = self._dtc_move_kind(b, m)
            if conversion:
                for k in range(DTC_PACK_LAYERS):
                    raise_at(k, 1)
                unbounded.zeroing_child()
                continue
            cfg_c, cboard, cep, _zeroing = self._make_child(b, m)
            if cep is not None:
                ep_wins = self._ep_conversion_wins(cboard, cep, depth + 1)
                if ep_wins is None:
                    return None
                if ep_wins:
                    for k in range(DTC_PACK_LAYERS):
                        raise_at(k, 1)
                    unbounded.zeroing_child()
                    continue

            curve = self._read_dtc_curve(self._open_dtc(cfg_c), cfg_c, cboard, WIN)
            if curve is None:
                return None
            if push:
                unbounded.zeroing_child()
            else:
                unbounded.quiet_child(curve[DTC_BUDGET_LAYERS], False, False)
            for k in range(DTC_PACK_LAYERS):
                v = curve[k]
                if v == DRAWN_AT_LAYER:
                    drawn[k] = True
                else:
                    raise_at(k, 1 if push else v + 1)

        if not any_legal:
            return _DTCCell(0, 0, 0)  # mate: converted, nothing owed
        dtz = unbounded.value()
        budget_plies = dtc_budget_plies(rule50)
        for k in range(DTC_PACK_LAYERS):
            if not drawn[k] and worst[k] <= budget_plies:
                return _DTCCell(k, worst[k], dtz)
        return _DTCCell(dtz=dtz)

    def _derive_dtc_cursed(self, board: chess.Board, wdl: int,
                           depth: int) -> Optional[_DTCCell]:
        """A cursed class has no budget, so only the unbounded row is derived."""
        b = _internal_board(board)
        winning = (wdl == CURSED_WIN)
        unbounded = _UnboundedFold(wdl)
        any_legal = False
        skipped = _SkippedChildren()
        for m in b.legal_moves:
            any_legal = True
            conversion, push = self._dtc_move_kind(b, m)
            cfg_c, cboard, cep, _zeroing = self._make_child(b, m)
            if cfg_c.is_bare_kings:
                # Bare kings is an outright draw, a move neither class counts.
                continue
            cw = self._probe_wdl_impl(cfg_c, cboard, cep, depth + 1)
            if cw == ILLEGAL:
                skipped.unknown()
                continue
            if winning and cw not in (LOSE, BLESSED_LOSS):
                continue
            # A blessed loss counts only moves that keep it blessed: into a
            # cursed win, or quietly into a win already at the horizon.
            if not winning and cw != CURSED_WIN and (conversion or push):
                continue
            if conversion or push:
                unbounded.zeroing_child()
                if winning and invert_wdl(cw) == wdl:
                    return _DTCCell(dtz=1)
                continue
            cell = self._probe_dtc_internal(self._open_dtc(cfg_c), cfg_c, cboard,
                                            cw, IGNORE_50MR, depth + 1)
            if cell is None:
                skipped.unknown()
                continue
            if not winning and cw == WIN and cell.dtz < MAX_NON_CURSED_DTZ:
                continue
            unbounded.quiet_child(cell.dtz, _is_cursed_exit(b, cboard, cw), cell.dtz_rounded)
        if skipped.unpin(wdl):
            return None
        return (_DTCCell(dtz=unbounded.value(), dtz_rounded=unbounded.rounded()) if any_legal
                else _DTCCell())

    # --- DTM (the standalone `dtm/` table) ---
    def _probe_dtm_internal(self, d: Optional[DTMFile], cfg: PieceConfig,
                            board: chess.Board, wdl: int, depth: int) -> Optional[int]:
        if d is None:
            return None
        color, mp, readable = locate_frame(d, cfg, board, wdl)
        if not readable:
            return self._derive_dtm(board, wdl, depth)
        return d.read(color, board if mp is None else mp, wdl)

    def _derive_dtm(self, board: chess.Board, wdl: int, depth: int) -> Optional[int]:
        """DTM by one-ply minimax for a dropped frame. DTM ignores the 50-move
        rule, so cursed classes fold to decisive ones and no clock is tracked."""
        if depth >= MAX_DERIVE_DEPTH:
            return None
        pinned = fold_dtm_wdl(wdl)
        b = _internal_board(board)
        any_legal = False
        best_wdl, best_dtm = LOSE, 0
        skipped = _SkippedChildren()
        for mv in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, _zeroing = self._make_child(b, mv)
            if cfg_c.is_bare_kings:
                cw, cd = DRAW, 0
            elif cep is not None:
                cr = self._probe_impl(cfg_c, cboard, IGNORE_50MR, cep, depth + 1)
                if cr.wdl == ILLEGAL:
                    skipped.unknown()
                    continue
                if not cr.has_dtm:
                    skipped.of_class(invert_wdl(fold_dtm_wdl(cr.wdl)))
                    continue
                cw, cd = cr.wdl, cr.dtm
            else:
                if child_class_is_forced(pinned):
                    cw = WIN
                else:
                    cw = self._probe_wdl_internal(self._open_wdl(cfg_c), cfg_c,
                                                  cboard, depth + 1)
                    if cw == ILLEGAL:
                        skipped.unknown()
                        continue
                    if below_pinned_class(pinned, invert_wdl(fold_dtm_wdl(cw))):
                        continue
                child_dtm = self._probe_dtm_internal(self._open_dtm(cfg_c), cfg_c,
                                                     cboard, cw, depth + 1)
                if child_dtm is None:
                    skipped.of_class(invert_wdl(fold_dtm_wdl(cw)))
                    continue
                cd = child_dtm
            my_wdl = invert_wdl(fold_dtm_wdl(cw))
            my_dtm = 1 + cd
            if prefer_new(my_wdl, my_dtm, best_wdl, best_dtm):
                best_wdl, best_dtm = my_wdl, my_dtm
            if pinned == WIN and best_wdl == pinned and best_dtm == 1:
                return best_dtm
        if not any_legal:
            return 0
        if skipped.unpin(best_wdl):
            return None
        if best_wdl in (WIN, LOSE):
            return best_dtm
        return 0

    # --- DTM50 (whose flat layer answers DTM too) ---
    def _probe_dtm50_internal(self, m: Optional[DTM50File], cfg: PieceConfig,
                              board: chess.Board, wdl: int, rule50: int,
                              depth: int) -> _DTM50Result:
        flat = (rule50 == IGNORE_50MR)
        if not flat and rule50 >= DTM50_HMC_COUNT:
            return _DTM50Result(DRAW, 0)
        if m is None:
            return _DTM50Result(ILLEGAL, 0)

        def from_cell(cell: Tuple[int, int]) -> _DTM50Result:
            value, flip = cell
            if value == DRAWN_AT_LAYER:
                cls, value = DRAW, 0
            else:
                cls = wdl if flat else fold_50mr_wdl(wdl)
            if not flat:
                return _DTM50Result(cls, value)
            dtz = dtz_from_draw_flip(flip, wdl, board)
            if dtz is None:
                return _DTM50Result(cls, value)
            return _DTM50Result(cls, value, True, dtz)

        color, mp, readable = locate_frame(m, cfg, board, wdl)
        if not readable:
            return (self._derive_dtm50_flat(board, wdl, depth) if flat
                    else self._derive_dtm50(board, wdl, rule50, depth))
        return from_cell(m.read(color, board if mp is None else mp, wdl, rule50))

    def _derive_dtm50_flat(self, board: chess.Board, wdl: int,
                           depth: int) -> _DTM50Result:
        """Unbounded DTM by one-ply minimax for a dropped layer-0 frame,
        carrying DTZ as a cell read does."""
        if depth >= MAX_DERIVE_DEPTH:
            return _DTM50Result(ILLEGAL, 0)
        pinned = fold_dtm_wdl(wdl)
        b = _internal_board(board)
        any_legal = False
        best_wdl, best_dtm = LOSE, 0
        dtz = _DTZMinimax()
        skipped = _SkippedChildren()
        for mv in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, zeroing = self._make_child(b, mv)
            if cfg_c.is_bare_kings:
                cw, cd = DRAW, 0
                dtz.zeroing_child(DRAW)
            elif cep is not None:
                cr = self._probe_impl(cfg_c, cboard, IGNORE_50MR, cep, depth + 1)
                if cr.wdl == ILLEGAL:
                    skipped.unknown()
                    dtz.unwalked()
                    continue
                dtz.zeroing_child(cr.wdl)  # a double push zeroes the clock
                if not cr.has_dtm:
                    skipped.of_class(invert_wdl(fold_dtm_wdl(cr.wdl)))
                    continue
                cw, cd = cr.wdl, cr.dtm
            else:
                if child_class_is_forced(wdl):
                    raw_wdl = WIN
                else:
                    raw_wdl = self._probe_wdl_internal(self._open_wdl(cfg_c), cfg_c,
                                                       cboard, depth + 1)
                    if raw_wdl == ILLEGAL:
                        skipped.unknown()
                        dtz.unwalked()
                        continue
                    if below_pinned_class(pinned, invert_wdl(fold_dtm_wdl(raw_wdl))):
                        continue
                child = self._probe_dtm50_internal(self._open_dtm50(cfg_c), cfg_c,
                                                   cboard, raw_wdl, IGNORE_50MR, depth + 1)
                if zeroing:
                    dtz.zeroing_child(raw_wdl)
                else:
                    dtz.quiet_child(raw_wdl, child, _is_cursed_exit(b, cboard, raw_wdl))
                if child.wdl == ILLEGAL:
                    skipped.of_class(invert_wdl(fold_dtm_wdl(raw_wdl)))
                    continue
                cw, cd = child.wdl, child.dtm
            my_wdl = invert_wdl(fold_dtm_wdl(cw))
            my_dtm = 1 + cd
            if prefer_new(my_wdl, my_dtm, best_wdl, best_dtm):
                best_wdl, best_dtm = my_wdl, my_dtm
        if not any_legal:
            return dtz.finish(LOSE if b.is_check() else DRAW, 0, False)
        if skipped.unpin(best_wdl):
            return dtz.finish(ILLEGAL, 0, True)
        if best_wdl in (WIN, LOSE):
            return dtz.finish(best_wdl, best_dtm, True)
        return dtz.finish(DRAW, 0, True)

    def _derive_dtm50(self, board: chess.Board, wdl: int, rule50: int,
                      depth: int) -> _DTM50Result:
        """Clock-aware DTM50 derive: a child at 100 plies or more is a draw
        unless mated. No DTZ: :meth:`_probe_impl` takes it from layer 0."""
        if depth >= MAX_DERIVE_DEPTH:
            return _DTM50Result(ILLEGAL, 0)
        pinned = fold_50mr_wdl(wdl)
        b = _internal_board(board)
        any_legal = False
        best_wdl, best_dtm = LOSE, 0
        skipped = _SkippedChildren()
        for mv in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, zeroing = self._make_child(b, mv)
            child_rule50 = 0 if zeroing else rule50 + 1
            if cfg_c.is_bare_kings:
                cd_wdl, cd_dtm = DRAW, 0
            elif child_rule50 >= DTM50_HMC_COUNT:
                cd_wdl, cd_dtm = (LOSE, 0) if cboard.is_checkmate() else (DRAW, 0)
            elif cep is not None:
                cr = self._probe_impl(cfg_c, cboard, child_rule50, cep, depth + 1)
                if cr.wdl == ILLEGAL:
                    skipped.unknown()
                    continue
                if not cr.has_dtm50:
                    skipped.of_class(invert_wdl(fold_50mr_wdl(cr.wdl)))
                    continue
                cd_wdl, cd_dtm = cr.dtm50_wdl, cr.dtm50
            else:
                if child_class_is_forced(wdl):
                    cw = WIN
                else:
                    cw = self._probe_wdl_internal(self._open_wdl(cfg_c), cfg_c, cboard, depth + 1)
                    if cw == ILLEGAL:
                        skipped.unknown()
                        continue
                    if below_pinned_class(wdl, invert_wdl(cw)):
                        continue
                child = self._probe_dtm50_internal(self._open_dtm50(cfg_c), cfg_c, cboard,
                                                   cw, child_rule50, depth + 1)
                if child.wdl == ILLEGAL:
                    skipped.of_class(invert_wdl(fold_50mr_wdl(cw)))
                    continue
                cd_wdl, cd_dtm = child.wdl, child.dtm
            my_wdl = invert_wdl(fold_50mr_wdl(cd_wdl))
            my_dtm = 1 + cd_dtm
            if prefer_new(my_wdl, my_dtm, best_wdl, best_dtm):
                best_wdl, best_dtm = my_wdl, my_dtm
            if pinned == WIN and best_wdl == pinned and best_dtm == 1:
                return _DTM50Result(best_wdl, best_dtm)
        if not any_legal:
            return _DTM50Result(LOSE if b.is_check() else DRAW, 0)
        if skipped.unpin(best_wdl):
            return _DTM50Result(ILLEGAL, 0)
        if best_wdl in (WIN, LOSE):
            return _DTM50Result(best_wdl, best_dtm)
        return _DTM50Result(DRAW, 0)

    # --- combined probe with ep overlay (src/probe/probe.cpp) ---
    def _probe_impl(self, cfg: PieceConfig, board: chess.Board, rule50: int,
                    ep_square: Optional[int], depth: int) -> ProbeResult:
        r = ProbeResult()
        w = self._open_wdl(cfg)
        if w is None:
            return r
        rule50_drawn = (rule50 != IGNORE_50MR and rule50 >= DTM50_HMC_COUNT)
        r.wdl = self._probe_wdl_internal(w, cfg, board, depth)
        if r.wdl == ILLEGAL:
            return r
        m50 = self._open_dtm50(cfg) if r.wdl != DRAW else None
        if r.wdl == DRAW:
            r.has_dtm = True
            r.has_dtz = True
            if rule50 != IGNORE_50MR:
                r.dtc_wdl = DRAW
                r.has_dtc = True
                r.dtm50_wdl = DRAW
                r.has_dtm50 = True
        elif m50 is not None:
            d50 = self._probe_dtm50_internal(m50, cfg, board, r.wdl, IGNORE_50MR, depth)
            r.dtm = d50.dtm
            r.has_dtm = (d50.wdl != ILLEGAL)
            r.dtz = d50.dtz
            r.has_dtz = d50.has_dtz
            _fill_dtc_from_bounds(r, material_has_pawns(cfg), rule50)
            _fill_dtm50_from_bounds(r, rule50)
            if not r.has_dtm50 and rule50 != IGNORE_50MR and rule50 < DTM50_HMC_COUNT:
                d50 = self._probe_dtm50_internal(m50, cfg, board, r.wdl, rule50, depth)
                r.dtm50_wdl = d50.wdl
                r.dtm50 = d50.dtm
                r.has_dtm50 = (d50.wdl != ILLEGAL)

        else:
            m = self._open_dtm(cfg)
            if m is not None:
                dtm = self._probe_dtm_internal(m, cfg, board, r.wdl, depth)
                if dtm is not None:
                    r.dtm = dtm
                    r.has_dtm = True
        # The DTC pack gives DTC at this clock and DTZ from its unbounded row;
        # cursed or out of clock, it prices nothing.
        if r.wdl != DRAW and (not r.has_dtc or not r.has_dtz) and material_has_pawns(cfg):
            c = self._open_dtc(cfg)
            if c is not None:
                cell = self._probe_dtc_internal(c, cfg, board, r.wdl, rule50, depth)
                if cell is not None:
                    # Unclocked, the cell serves only its DTZ row.
                    if rule50 != IGNORE_50MR:
                        r.dtc_wdl = r.wdl if cell.priced else DRAW
                        r.dtc_order = cell.order if cell.priced else 0
                        r.dtc = cell.value if cell.priced else 0
                        r.has_dtc = True
                    # Records and derives both carry the DTZ row.
                    r.dtz = cell.dtz
                    r.dtz_rounded = cell.dtz_rounded
                    r.has_dtz = True
        # Plain DTZ: DTM50 stops at the cursed band, DTC covers only some materials.
        if not r.has_dtz:
            d = self._open_dtz(cfg)
            if d is not None:
                dtz = self._probe_dtz_internal(d, cfg, board, r.wdl, depth)
                if dtz is not None:
                    r.dtz = dtz.dtz
                    r.dtz_rounded = dtz.rounded
                    r.has_dtz = True
        # Only pawnless material gets a decisive DTC from DTZ alone.
        if not r.has_dtc:
            _fill_dtc_from_bounds(r, material_has_pawns(cfg), rule50)

        if not r.has_dtm50:
            _fill_dtm50_from_bounds(r, rule50)

        _fill_wdl50(r, rule50)

        if ep_square is None or r.wdl == ILLEGAL:
            return r
        bcopy, eps = _ep_capture_moves(board, ep_square)
        if not eps:
            return r
        has_non_ep_move = any(board.legal_moves)

        best = r
        best_dtz_wdl = r.wdl
        best_dtz = r.dtz if r.has_dtz else 0
        best_dtm_wdl = fold_dtm_wdl(r.wdl)
        best_dtm = r.dtm if r.has_dtm else 0
        best_dtm50_wdl = r.dtm50_wdl if r.has_dtm50 else fold_50mr_wdl(r.wdl)
        best_dtm50 = r.dtm50 if r.has_dtm50 else 0
        # DTC compares on its own class: a base this clock has drawn must lose
        # to an ep conversion that still wins.
        best_dtc_wdl = r.dtc_wdl if r.has_dtc else r.wdl
        best_dtc_order = r.dtc_order if r.has_dtc else 0
        best_dtc = r.dtc if r.has_dtc else 0
        any_ep = False
        # Unclocked, DTC and DTM50 don't exist; a drawn clock has the claim.
        live_clock = rule50 != IGNORE_50MR and not rule50_drawn
        if rule50_drawn:
            # Even an ep capture costs a ply; the claim is already there.
            best.dtc_wdl = DRAW
            best.has_dtc = True
            best.dtm50_wdl = DRAW
            best.has_dtm50 = True
        for mv in eps:
            cfg_c, cboard, _cep, _ = self._make_child(bcopy, mv)
            if cfg_c.is_bare_kings:
                cr = ProbeResult()
                cr.wdl = DRAW
                cr.has_dtz = best.has_dtz
                cr.has_dtm = best.has_dtm
                cr.dtm50_wdl = DRAW
                cr.has_dtm50 = best.has_dtm50
            else:
                cr = self._probe_impl(cfg_c, cboard, 0 if live_clock else IGNORE_50MR,
                                     None, depth + 1)  # ep is zeroing
            if cr.wdl == ILLEGAL:
                return ProbeResult()
            my_wdl = invert_wdl(cr.wdl)
            if not has_non_ep_move and not any_ep:
                best.wdl = my_wdl

                best_dtz_wdl, best_dtz = my_wdl, 1
                best.dtz = 0 if my_wdl == DRAW else 1
                best.dtz_rounded = False
                best.has_dtz = True

                best_dtm_wdl = fold_dtm_wdl(my_wdl)
                best_dtm = 1 + cr.dtm if cr.has_dtm else 0
                best.dtm = (best_dtm if cr.has_dtm
                            and best_dtm_wdl in (WIN, LOSE) else 0)
                best.has_dtm = cr.has_dtm

                if live_clock:
                    best_dtc_wdl, best_dtc_order, best_dtc = (
                        fold_50mr_wdl(my_wdl), 0, 1)
                    best.dtc_wdl = best_dtc_wdl
                    best.dtc_order = 0
                    best.dtc = 0 if best_dtc_wdl == DRAW else 1
                    best.has_dtc = True

                    best_dtm50_wdl = invert_wdl(cr.dtm50_wdl) if cr.has_dtm50 else ILLEGAL
                    best_dtm50 = 1 + cr.dtm50 if cr.has_dtm50 else 0
                    best.dtm50_wdl = best_dtm50_wdl
                    best.dtm50 = (best_dtm50 if cr.has_dtm50
                                  and best_dtm50_wdl in (WIN, LOSE) else 0)
                    best.has_dtm50 = cr.has_dtm50

                any_ep = True
                continue
            any_ep = True
            if wdl_rank(my_wdl) > wdl_rank(best.wdl):
                best.wdl = my_wdl
            # An ep capture zeroes, so its DTZ is 1. The base DTZ is needed
            # only to break a class tie, so an unknown one doesn't block it.
            ep_outranks_dtz = wdl_rank(my_wdl) > wdl_rank(best_dtz_wdl)
            if ep_outranks_dtz or (best.has_dtz
                                   and prefer_new(my_wdl, 1, best_dtz_wdl, best_dtz)):
                best_dtz_wdl, best_dtz = my_wdl, 1
                best.dtz = 0 if my_wdl == DRAW else 1
                best.dtz_rounded = False
                best.has_dtz = True
            # A DTM ignoring a legal ep capture would be wrong, so a child
            # without one leaves this DTM undetermined.
            if not cr.has_dtm:
                best.has_dtm = False
            elif best.has_dtm:
                my_dtm_wdl = fold_dtm_wdl(my_wdl)
                my_dtm = 1 + cr.dtm
                if prefer_new(my_dtm_wdl, my_dtm, best_dtm_wdl, best_dtm):
                    best_dtm_wdl, best_dtm = my_dtm_wdl, my_dtm
                    best.dtm = my_dtm if my_dtm_wdl in (WIN, LOSE) else 0
            if live_clock:
                # An ep capture is a conversion one ply out: (0, 1), classed by
                # the child's 50MR-folded WDL. The base only breaks a class tie.
                my_dtc_wdl = fold_50mr_wdl(invert_wdl(cr.wdl))
                if (wdl_rank(my_dtc_wdl) > wdl_rank(best_dtc_wdl)
                        or (best.has_dtc and prefer_new_dtc(my_dtc_wdl, 0, 1,
                                                            best_dtc_wdl, best_dtc_order,
                                                            best_dtc))):
                    best_dtc_wdl, best_dtc_order, best_dtc = my_dtc_wdl, 0, 1
                    best.dtc_wdl = my_dtc_wdl
                    best.dtc_order = 0
                    best.dtc = 1 if my_dtc_wdl != DRAW else 0
                    best.has_dtc = True
                if not cr.has_dtm50:
                    best.has_dtm50 = False
                elif best.has_dtm50:
                    my_dtm50_wdl = invert_wdl(cr.dtm50_wdl)
                    my_dtm50 = 1 + cr.dtm50
                    if prefer_new(my_dtm50_wdl, my_dtm50, best_dtm50_wdl, best_dtm50):
                        best_dtm50_wdl, best_dtm50 = my_dtm50_wdl, my_dtm50
                        best.dtm50_wdl = my_dtm50_wdl
                        best.dtm50 = my_dtm50 if my_dtm50_wdl in (WIN, LOSE) else 0
        # An ep capture may have changed the class and DTZ; decide again.
        best.has_wdl50 = False
        _fill_wdl50(best, rule50)
        return best

    # --- public API ---
    def probe(self, board: chess.Board, rule50: Optional[int] = None) -> ProbeResult:
        """Probes all metrics of *board* at once.

        *rule50*, the halfmove clock (by default the board's own), selects
        the DTM50 and DTC values and decides ``wdl50`` where possible.

        Returns a :class:`ProbeResult` whose ``wdl`` is :data:`ILLEGAL` if
        the tables can't answer. A board with castling rights is answered only
        by tables carrying those rights.

        Thread-safe. A concurrent :meth:`close` waits for probes to finish."""
        hmc = board.halfmove_clock if rule50 is None else rule50
        with self._reading():
            cfg, cboard, ep = self._canonical_root(board)
            return self._probe_impl(cfg, cboard, hmc, ep, 0)

    @contextlib.contextmanager
    def _reading(self) -> Iterator[None]:
        with self._read_condition:
            self._read_count += 1
        try:
            yield
        finally:
            with self._read_condition:
                self._read_count -= 1
                self._read_condition.notify_all()

    def _canonical_root(self, board: chess.Board
                        ) -> Tuple[PieceConfig, chess.Board, Optional[int]]:
        """Config, canonical board and split-off ep square to probe *board*,
        which is left as it is. Rooks holding a right are marks; so is the
        opposing pair, where its table is on disk (it duplicates its full
        twin). The men, the rights and the pair alone decide the config and
        orientation, so those answers are kept."""
        white, black = board.occupied_co[chess.WHITE], board.occupied_co[chess.BLACK]
        men = (board.pawns, board.knights, board.bishops, board.rooks, board.queens)
        rights = board.clean_castling_rights()
        pair = PairGroup.canonical_pair(board.pawns & white, board.pawns & black)
        key = (tuple([chess.popcount(m & white) for m in men] + [chess.popcount(m & black) for m in men]),
               chess.popcount(rights & white), chess.popcount(rights & black),
               pair is not None)
        root = self._roots.get(key)
        if root is None:
            if pair is not None:
                root = _piece_config_from_board(board, rights, pair)
                if self._open_wdl(root[0]) is None:
                    root = None
            if root is None:
                root = _piece_config_from_board(board, rights, None)
            self._roots[key] = root
        cfg, mirrored = root
        if mirrored:
            board = mirror_for_canonical(board)
        elif board.ep_square is not None:
            board = board.copy(stack=False)
        ep = board.ep_square
        board.ep_square = None
        return cfg, board, ep

    def _require(self, board: chess.Board,
                 rule50: Optional[int] = IGNORE_50MR) -> ProbeResult:
        # Unclocked by default for DTZ and DTM; DTC and DTM50 pass a clock.
        r = self.probe(board, rule50)
        if r.wdl == ILLEGAL:
            with self._reading():  # naming the material may open a table
                raise MissingTableError(
                    f"no chesstb table for {self._canonical_root(board)[0].name()}")
        return r

    def probe_wdl(self, board: chess.Board) -> int:
        """Probes the win/draw/loss value of *board*.

        Returns ``2`` if the side to move is winning, ``0`` for a draw and
        ``-2`` if the side to move is losing; ``1`` for a cursed win and
        ``-1`` for a blessed loss (drawn by the 50-move rule).

        :raises: :exc:`MissingTableError` if the tables can't answer. Use
            :meth:`get_wdl` to get ``None`` instead."""
        with self._reading():
            cfg, cboard, ep = self._canonical_root(board)
            # No distance table is read; a WIN stands despite unresolved ep.
            w = self._probe_wdl_impl(cfg, cboard, ep, 0)
            if w == ILLEGAL:
                raise MissingTableError(
                    f"no chesstb table for {self._canonical_root(board)[0].name()}")
            return _WDL_SIGNED[w]

    def get_wdl(self, board: chess.Board, default: Any = None) -> Any:
        try:
            return self.probe_wdl(board)
        except MissingTableError:
            return default

    def probe_dtz(self, board: chess.Board) -> int:
        """Probes the distance to zeroing (capture, promotion or pawn move)
        of *board*: ``n`` if the side to move zeroes toward a win in ``n``
        plies, ``-n`` toward a loss, ``0`` for a draw.

        Not interchangeable with :meth:`chess.syzygy.Tablebase.probe_dtz`:
        this doesn't encode the base shift for cursed and blessed results,
        whose class only :meth:`probe_wdl` gives.

        :raises: :exc:`MissingTableError` if the DTZ can't be determined. Use
            :meth:`get_dtz` to get ``None`` instead.
        """
        r = self._require(board)
        if not r.has_dtz:
            raise MissingTableError("DTZ table unavailable")
        return _signed(r.dtz, r.wdl)

    def get_dtz(self, board: chess.Board, default: Any = None) -> Any:
        try:
            return self.probe_dtz(board)
        except MissingTableError:
            return default

    def probe_dtc(self, board: chess.Board,
                  rule50: Optional[int] = None) -> Tuple[int, int]:
        """Probes the distance to conversion of *board* at its halfmove clock
        (or *rule50*), counting pawn pushes separately from other moves.

        Returns ``(pushes_owed, signed_plies)``: the pushes the winning side
        still owes before a capture or promotion, and the signed plies to the
        next zeroing move on that line. Fewest pushes comes first, but a
        tight clock can force a line owing more. ``(0, 0)`` if the clock
        leaves no win (a 50-move-rule draw). Pawnless positions owe nothing:
        ``(0, dtz)``.

        :raises: :exc:`MissingTableError` if the DTC can't be determined."""
        r = self._require(board, rule50)
        if not r.has_dtc:
            raise MissingTableError("DTC unavailable")
        return (r.dtc_order, _signed(r.dtc, r.dtc_wdl))

    def probe_dtm(self, board: chess.Board) -> int:
        """Probes the signed distance to mate, ignoring the 50-move rule.

        :raises: :exc:`MissingTableError` if the DTM can't be determined. Use
            :meth:`get_dtm` to get ``None`` instead."""
        r = self._require(board)
        if not r.has_dtm:
            raise MissingTableError("DTM unavailable")
        return _signed(r.dtm, r.wdl)

    def get_dtm(self, board: chess.Board, default: Any = None) -> Any:
        try:
            return self.probe_dtm(board)
        except MissingTableError:
            return default

    def probe_dtm50(self, board: chess.Board, rule50: Optional[int] = None) -> int:
        """Probes the signed distance to mate under the 50-move rule, at the
        board's halfmove clock (or *rule50*). ``0`` if the 50-move rule draws,
        including cursed wins and blessed losses.

        :raises: :exc:`MissingTableError` if the DTM50 can't be determined."""
        r = self._require(board, rule50)
        if not r.has_dtm50:
            raise MissingTableError("DTM50 unavailable")
        return _signed(r.dtm50, r.dtm50_wdl)


def open_tablebase(directory: str, *,
                   block_cache_bytes: int = DEFAULT_BLOCK_CACHE_BYTES) -> Tablebase:
    """Opens a directory tree of chesstb tables: ``wdl/``, ``dtz/``,
    ``dtc/``, ``dtm/`` and ``dtm50/`` subdirectories, or the table files
    directly in *directory*. See :class:`~chess.chesstb.Tablebase`.

    :param block_cache_bytes: Bound of the LRU cache of decoded blocks."""
    return Tablebase(directory, block_cache_bytes=block_cache_bytes)
