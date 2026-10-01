"""Pure-Python prober for the *chesstb* endgame tablebase format
(WDL ``.lzw`` / DTZ ``.lzdtz`` / DTC ``.lzdtc`` / DTM ``.lzdtm``
/ DTM50 ``.lzdtm50``).

Upstream: https://github.com/noobpwnftw/chesstb

A re-implementation of the C++ probe library in ``src/probe``, validated against
``tools/probe_fen``. Square numbering matches python-chess (a1=0 .. h8=63) and
the shape follows :mod:`chess.syzygy`: a :class:`Tablebase` opens a directory of
table files and answers WDL / DTZ / DTC / DTM / DTM50 queries.

Every ``probe_*`` distance is signed from the side to move: ``+N`` toward a win,
``-N`` toward a loss, ``0`` for no decisive result -- a draw, a clock that has
taken the win, or a mate already on the board. :meth:`Tablebase.probe` keeps
every class field explicit for callers wanting the class outright.

A :class:`Tablebase` is safe to share between threads and probe concurrently:
tables open lazily under a per-kind lock, blocks decode under a per-(color,
block) one, and :meth:`close` waits on a read count before unmapping.
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
import threading
from typing import Any, Dict, Iterator, List, NamedTuple, Optional, Tuple, Type, TypeVar, Union

import chess

try:
    _lz4_block: Any = importlib.import_module("lz4.block")
except ImportError:
    _lz4_block = None

__all__ = ["Tablebase", "ProbeResult", "MissingTableError", "open_tablebase"]

WHITE = chess.WHITE
BLACK = chess.BLACK

KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN = 1, 2, 3, 4, 5, 6

_CPP_TO_PC = {KING: chess.KING, QUEEN: chess.QUEEN, ROOK: chess.ROOK,
              BISHOP: chess.BISHOP, KNIGHT: chess.KNIGHT, PAWN: chess.PAWN}
_PC_TO_CPP = {v: k for k, v in _CPP_TO_PC.items()}

CPP_WHITE, CPP_BLACK = 0, 1

#: In-memory key for one material: see :attr:`PieceConfig.cache_key`. A 'p' or
#: 'r' material shares its plain twin's ``min_key``, so the marks join the key.
CacheKey = Tuple[int, bool, int]

#: One material's key: see :func:`full_material_key`.
MaterialKey = Tuple[int, bool, int]
# The uint32 table header reserves its low two bits for the table number.
_PACKED_MATERIAL_KEY_MASK = 0x3FFFFFFF


def cpp_color(piece_color: bool) -> int:
    return CPP_WHITE if piece_color == WHITE else CPP_BLACK


# --- square transforms (src/chess/chess.h tables) ---

def sq_file(sq: int) -> int:
    return sq & 7


def sq_rank(sq: int) -> int:
    return sq >> 3


def sq_make(rank: int, file: int) -> int:
    return (rank << 3) + file


def sq_file_mirror(sq: int) -> int:
    return sq_make(sq_rank(sq), 7 - sq_file(sq))


def sq_rank_mirror(sq: int) -> int:
    return sq_make(7 - sq_rank(sq), sq_file(sq))


def sq_diag_mirror(sq: int) -> int:
    return sq_make(sq_file(sq), sq_rank(sq))


def apply_transform(sq: int, t: int) -> int:
    """Symmetry_Transform: bit0=file flip, bit1=rank flip, bit2=diag swap."""
    f = sq_file(sq)
    r = sq_rank(sq)
    if t & 1:
        f = 7 - f
    if t & 2:
        r = 7 - r
    if t & 4:
        f, r = r, f
    return sq_make(r, f)


T_IDENTITY, T_FILE, T_RANK, T_FILE_RANK = 0, 1, 2, 3
T_DIAG, T_FILE_DIAG, T_RANK_DIAG, T_FILE_RANK_DIAG = 4, 5, 6, 7

SYM_NONE = 0
SYM_FILE_MIRROR = 1
SYM_DIHEDRAL_8 = 2

_ANCHOR_FILE_MIRROR = [sq_make(r, f) for r in range(8) for f in range(4)]  # files a-d
_ANCHOR_TRIANGLE = [sq_make(r, f) for r in range(4) for f in range(r, 4)]  # a1,b1..d1,b2..

# --- Binomial table C(n, k) for n<=64, k<=7.  C++ BINOMIAL[k][n] indexing. ---
_BINOM = [[0] * 8 for _ in range(65)]
for _k in range(65):
    _BINOM[_k][0] = 1
    for _n in range(1, 8):
        _BINOM[_k][_n] = 0 if _n > _k else _BINOM[_k - 1][_n - 1] + _BINOM[_k - 1][_n]


def binom(n: int, k: int) -> int:
    if k < 0 or k > 7 or n < 0 or n > 64:
        return 0
    return _BINOM[n][k]


_MAT_WEIGHT = {  # (cpp_color, type) -> weight
    (CPP_WHITE, QUEEN): 9 ** 4, (CPP_WHITE, ROOK): 9 ** 3, (CPP_WHITE, BISHOP): 9 ** 2,
    (CPP_WHITE, KNIGHT): 9 ** 1, (CPP_WHITE, PAWN): 9 ** 0, (CPP_WHITE, KING): 0,
    (CPP_BLACK, QUEEN): 9 ** 9, (CPP_BLACK, ROOK): 9 ** 8, (CPP_BLACK, BISHOP): 9 ** 7,
    (CPP_BLACK, KNIGHT): 9 ** 6, (CPP_BLACK, PAWN): 9 ** 5, (CPP_BLACK, KING): 0,
}


def material_key_of(pieces: List[Tuple[int, int]]) -> int:
    return sum(_MAT_WEIGHT[(c, t)] for c, t in pieces)


def castling_rook_key(white_rights: int, black_rights: int) -> int:
    """A rook holding a right is a man on the board like any other, so it is
    counted into the material key -- unlike the pair's pawns, which are one of
    each color and so cannot tip the side ordering. Counting them is what makes
    KrK order ahead of its mirror KKr."""
    return (white_rights * _MAT_WEIGHT[(CPP_WHITE, ROOK)]
            + black_rights * _MAT_WEIGHT[(CPP_BLACK, ROOK)])


def full_material_key(pieces: List[Tuple[int, int]], has_pair: bool = False,
                      castling_rights: Tuple[int, int] = (0, 0)) -> MaterialKey:
    """The whole of Material_Key (src/chess/chess.h): the base-9 count word,
    then the pair flag and rights code as tiebreaks. KRKr and KrKR share the
    count word and differ only in the code, so compare these whole."""
    w, b = castling_rights
    return (material_key_of(pieces) + castling_rook_key(w, b), has_pair, w * 3 + b)


# --- Piece_Config: canonical (strength-ordered) piece list, white = stronger side. ---
_STRENGTH = {QUEEN: 900, ROOK: 500, BISHOP: 330, KNIGHT: 320, PAWN: 100, KING: 0}
_TYPE_ORDER = {KING: 0, QUEEN: 1, ROOK: 2, BISHOP: 3, KNIGHT: 4, PAWN: 5}


def _composition_key(pieces: List[Tuple[int, int]], color: int) -> List[int]:
    """Per-type piece counts for `color`, indexed by C++ type code so that
    lexicographic comparison orders by KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN.
    Mirrors the ``std::array<int8_t, PIECE_TYPE_NB>`` tiebreak key in
    ``Piece_Config::sort_pieces`` (src/chess/piece_config.cpp)."""
    counts = [0] * (PAWN + 1)
    for c, t in pieces:
        if c == color:
            counts[t] += 1
    return counts


class PieceConfig:
    """Canonical material config. `pieces` is a list of (cpp_color, type) of the
    FREE pieces. `has_pair` marks an opposing pawn pair (lowercase 'p'):
    one white + one black pawn locked on a file, indexed jointly and excluded
    from `pieces` (mirrors src/chess/piece_config.h)."""

    __slots__ = ("pieces", "has_pair", "castling_rights", "base_key", "mirr_key",
                 "mirrored", "has_castling", "castling_code", "min_key",
                 "cache_key", "num_pieces", "is_bare_kings")

    def __init__(self, pieces: List[Tuple[int, int]], has_pair: bool = False,
                 castling_rights: Tuple[int, int] = (0, 0)):
        cr = list(castling_rights)
        ws = sum(_STRENGTH[t] for c, t in pieces if c == CPP_WHITE)
        bs = sum(_STRENGTH[t] for c, t in pieces if c == CPP_BLACK)
        ws += cr[CPP_WHITE] * _STRENGTH[ROOK]
        bs += cr[CPP_BLACK] * _STRENGTH[ROOK]
        swap = bs > ws
        if bs == ws:
            wkey = _composition_key(pieces, CPP_WHITE)
            bkey = _composition_key(pieces, CPP_BLACK)
            wkey[ROOK] += cr[CPP_WHITE]
            bkey[ROOK] += cr[CPP_BLACK]
            if wkey != bkey:
                swap = bkey > wkey
            else:
                # Same men both sides: order by which side's rook kept its right.
                swap = cr[CPP_WHITE] > cr[CPP_BLACK]
        if swap:
            pieces = [(CPP_BLACK if c == CPP_WHITE else CPP_WHITE, t) for c, t in pieces]
            cr = [cr[CPP_BLACK], cr[CPP_WHITE]]
        pieces = sorted(pieces, key=lambda ct: (ct[0], _TYPE_ORDER[ct[1]]))
        # Whether the literal material handed in had to swap colors to reach
        # this one. A self-mirror material forces equal rights and color-symmetric
        # men, which drive `swap` false, so this is exactly `literal != base_key`.
        self.mirrored = swap
        self.pieces = pieces
        self.has_pair = has_pair
        self.castling_rights = (cr[0], cr[1])
        self.base_key = full_material_key(pieces, has_pair, (cr[0], cr[1]))
        self.mirr_key = full_material_key(
            [(CPP_BLACK if c == CPP_WHITE else CPP_WHITE, t) for c, t in pieces],
            has_pair, (cr[1], cr[0]))
        self.has_castling = cr[CPP_WHITE] + cr[CPP_BLACK] > 0
        # Rights per side, below `min_key` in the ordering: KRKr and KrKR hold
        # the same men and differ only in whose rook kept its right. Smaller is
        # fewer white rights, matching the key, where white's slots weigh less.
        self.castling_code = cr[CPP_WHITE] * 3 + cr[CPP_BLACK]
        # The 30-bit count word alone, as the on-disk header carries it.
        self.min_key = min(self.base_key, self.mirr_key)[0]
        self.cache_key: CacheKey = (self.min_key, has_pair, self.castling_code)
        self.num_pieces = len(pieces)
        # `num_pieces` counts only FREE pieces, so KpKp sits at 2 while holding
        # four -- which is why every "just kings?" test goes through here.
        self.is_bare_kings = (self.num_pieces <= 2 and not has_pair
                              and not self.has_castling)

    def name(self) -> str:
        letters = {KING: "K", QUEEN: "Q", ROOK: "R", BISHOP: "B", KNIGHT: "N", PAWN: "P"}
        s = []
        seen_white_king = False
        # Castling rooks are not in `pieces`, so they go where they would have
        # sorted: before the first man of their color that outranks a rook.
        written = [0, 0]

        def write_castling_before(order: Tuple[int, int]) -> None:
            for cc in (CPP_WHITE, CPP_BLACK):
                if written[cc] == self.castling_rights[cc]:
                    continue
                if (cc, _TYPE_ORDER[ROOK]) >= order:
                    continue
                s.append("r" * (self.castling_rights[cc] - written[cc]))
                written[cc] = self.castling_rights[cc]

        for c, t in self.pieces:
            write_castling_before((c, _TYPE_ORDER[t]))
            if t == KING:
                if seen_white_king and self.has_pair:
                    s.append("p")
                seen_white_king = True
            s.append(letters[t])
        write_castling_before((CPP_BLACK + 1, 0))
        if self.has_pair:
            s.append("p")
        return "".join(s)


_PIECE_CONFIG_CACHE: Dict[Tuple[Tuple[Tuple[int, int], ...], bool, Tuple[int, int]],
                          PieceConfig] = {}


def piece_config(pieces: List[Tuple[int, int]], has_pair: bool = False,
                 castling_rights: Tuple[int, int] = (0, 0)) -> PieceConfig:
    """A :class:`PieceConfig` for this material, built once and shared. Every
    quiet move keeps its parent's material, so the derive walks ask for the same
    few over and over. Immutable, and building one twice is harmless, so a
    racing build needs no lock -- unlike :func:`position_index_config`."""
    key = (tuple(sorted(pieces)), has_pair, castling_rights)
    cfg = _PIECE_CONFIG_CACHE.get(key)
    if cfg is None:
        cfg = PieceConfig(pieces, has_pair, castling_rights)
        _PIECE_CONFIG_CACHE[key] = cfg
    return cfg


def _material_from_board(board: chess.Board, excluded: int = 0) -> List[Tuple[int, int]]:
    """The men on `board` as (cpp_color, cpp_type), squares in `excluded` left
    out. Only the multiset matters downstream, so this counts bits per mask
    rather than walking 64 squares and building a chess.Piece for each."""
    keep = ~excluded
    out = []
    for cpp_col, color in ((CPP_WHITE, WHITE), (CPP_BLACK, BLACK)):
        for cpp_type, pc_type in _CPP_TO_PC.items():
            n = chess.popcount(board.pieces_mask(pc_type, color) & keep)
            if n:
                out.extend([(cpp_col, cpp_type)] * n)
    return out


def piece_config_from_board(board: chess.Board) -> Tuple["PieceConfig", bool]:
    """(canonical PieceConfig, mirrored?) for the board's material. Mirrored
    means the literal material had to swap colors to reach the canonical base
    orientation, white being the stronger side."""
    pieces = _material_from_board(board)
    cfg = piece_config(pieces)
    return cfg, cfg.mirrored


def specialized_config_from_board(board: chess.Board, with_pair: bool
                                  ) -> Optional[Tuple["PieceConfig", bool]]:
    """Specialized material for `board`: the physical men, minus the canonical
    pair's two pawns when `with_pair` and minus every rook still holding a
    right, both recorded as marks instead. None when nothing applies, or when
    `with_pair` found no pair. Mirrors specialized_config_from_position.
    """
    excluded = 0
    if with_pair:
        found = PairGroup.find_canonical(list(board.pieces(chess.PAWN, WHITE)),
                                         list(board.pieces(chess.PAWN, BLACK)))
        if found is None:
            return None
        pw, pb = found
        excluded = chess.BB_SQUARES[pw] | chess.BB_SQUARES[pb]

    rights = [0, 0]
    for cc in (CPP_WHITE, CPP_BLACK):
        color = WHITE if cc == CPP_WHITE else BLACK
        rs = board_castling_rooks(board, color)
        for r in rs:
            excluded |= chess.BB_SQUARES[r]
        rights[cc] = len(rs)

    if not with_pair and not rights[CPP_WHITE] and not rights[CPP_BLACK]:
        return None

    pieces = _material_from_board(board, excluded)
    cfg = piece_config(pieces, with_pair,
                       (rights[CPP_WHITE], rights[CPP_BLACK]))
    return cfg, cfg.mirrored


# --- Piece_Class enum (src/chess/piece_config.h) ---
(BLACK_KINGS, BLACK_KNIGHTS, BLACK_BISHOPS, BLACK_ROOKS, BLACK_QUEENS, BLACK_PAWNS,
 WHITE_KINGS, WHITE_KNIGHTS, WHITE_BISHOPS, WHITE_ROOKS, WHITE_QUEENS, WHITE_PAWNS) = range(12)
PIECE_CLASS_NB = 12

_PTCLASS = {KING: 0, KNIGHT: 1, BISHOP: 2, ROOK: 3, QUEEN: 4, PAWN: 5}


def make_piece_class(cpp_col: int, ptype: int) -> int:
    base = WHITE_KINGS if cpp_col == CPP_WHITE else BLACK_KINGS
    return base + _PTCLASS[ptype]


def class_to_piece(pcl: int) -> Tuple[int, int]:
    cpp_col = CPP_WHITE if pcl >= WHITE_KINGS else CPP_BLACK
    off = pcl - (WHITE_KINGS if cpp_col == CPP_WHITE else BLACK_KINGS)
    inv = {0: KING, 1: KNIGHT, 2: BISHOP, 3: ROOK, 4: QUEEN, 5: PAWN}
    return cpp_col, inv[off]


class PieceGroup:
    def __init__(self, ptype: int, count: int):
        self.count = count
        if ptype == PAWN:
            legal = list(range(chess.A2, chess.H7 + 1))  # 8..55
        else:
            legal = list(range(64))
        legal.sort()
        self.pos_to_sq = legal
        self.sq_to_pos = {sq: i for i, sq in enumerate(legal)}
        self.num_legal = len(legal)
        self.table_size = binom(self.num_legal, count)

    def compound_index(self, squares: List[int]) -> int:
        sqs = sorted(squares)
        rank = 0
        for i, sq in enumerate(sqs):
            p = self.sq_to_pos[sq]
            rank += binom(p, i + 1)
        return rank

    def squares(self, idx: int) -> List[int]:
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
        return [self.pos_to_sq[p] for p in pos]


# --- King_Slice_Manager: built once per symmetry group. ---
def _kings_adjacent(a: int, b: int) -> bool:
    return chess.square_distance(a, b) == 1


def _sq_on_main_diag(sq: int) -> bool:
    return sq_file(sq) == sq_rank(sq)


class KingSliceManager:
    def __init__(self, sym: int):
        self.sym = sym
        n_trans = 8 if sym == SYM_DIHEDRAL_8 else 2
        anchors = _ANCHOR_TRIANGLE if sym == SYM_DIHEDRAL_8 else _ANCHOR_FILE_MIRROR
        anchor_set = set(anchors)
        SLICE_NONE = -1
        self.pair: List[List[int]] = [[SLICE_NONE, T_IDENTITY, 0] for _ in range(64 * 64)]
        self.kings_of_slice: List[Tuple[int, int]] = []

        for wk in range(64):
            if wk not in anchor_set:
                continue
            for bk in range(64):
                if bk == wk or _kings_adjacent(wk, bk):
                    continue
                if sym == SYM_DIHEDRAL_8 and _sq_on_main_diag(wk):
                    bk_d = sq_diag_mirror(bk)
                    if bk_d != bk and bk > bk_d:
                        continue
                sid = len(self.kings_of_slice)
                self.kings_of_slice.append((wk, bk))
                stab = 1 if (sym == SYM_DIHEDRAL_8 and _sq_on_main_diag(wk)
                             and _sq_on_main_diag(bk)) else 0
                self.pair[wk * 64 + bk] = [sid, T_IDENTITY, stab]
        self.num_slices = len(self.kings_of_slice)

        for wk in range(64):
            for bk in range(64):
                e = self.pair[wk * 64 + bk]
                if e[0] != SLICE_NONE:
                    continue
                if wk == bk or _kings_adjacent(wk, bk):
                    continue
                for t in range(n_trans):
                    wk_t = apply_transform(wk, t)
                    bk_t = apply_transform(bk, t)
                    look = self.pair[wk_t * 64 + bk_t]
                    if look[0] != -1 and look[1] == T_IDENTITY:
                        e[0] = look[0]
                        e[1] = t
                        e[2] = look[2]
                        break

    def lookup(self, wk: int, bk: int) -> List[int]:
        return self.pair[wk * 64 + bk]


class CastlingKingSliceManager:
    """King slices for a castling material: (Castling_Group placement, free king
    square), carrying the rook squares alongside, or the placement alone when
    both sides hold rights. The enumeration MUST match King_Slice_Manager's
    castling constructor in src/egtb/king_slice_manager.cpp -- the slice ids are
    on disk."""

    def __init__(self, white_rights: int, black_rights: int):
        self.sym = SYM_NONE
        self.rights = (white_rights, black_rights)
        self.group = CastlingGroup(white_rights, black_rights)
        self.both_pinned = self.group.both_pinned
        self.kings_of_slice: List[Tuple[int, int]] = []
        self.rooks_of_slice: List[Tuple[List[int], List[int]]] = []
        self._lookup: Dict[Tuple[int, int], int] = {}

        for ci in range(self.group.table_size):
            pinned = set()
            king_sq = [-1, -1]
            rooks: Tuple[List[int], List[int]] = ([], [])
            for cc in (CPP_WHITE, CPP_BLACK):
                if not self.rights[cc]:
                    continue
                kf, rfs = self.group.placement(ci, cc)
                rank = castling_home_rank(cc)
                king_sq[cc] = sq_make(rank, kf)
                pinned.add(king_sq[cc])
                for rf in rfs:
                    r = sq_make(rank, rf)
                    rooks[cc].append(r)
                    pinned.add(r)

            def emit(wk: int, bk: int, slot: int) -> None:
                self._lookup[(ci, slot)] = len(self.kings_of_slice)
                self.kings_of_slice.append((wk, bk))
                self.rooks_of_slice.append((list(rooks[CPP_WHITE]), list(rooks[CPP_BLACK])))

            if self.both_pinned:
                emit(king_sq[CPP_WHITE], king_sq[CPP_BLACK], 0)
                continue
            pinned_col = CPP_WHITE if self.rights[CPP_WHITE] else CPP_BLACK
            ksq = king_sq[pinned_col]
            for fk in range(64):
                if fk in pinned or _kings_adjacent(ksq, fk):
                    continue
                emit(ksq if pinned_col == CPP_WHITE else fk,
                     fk if pinned_col == CPP_WHITE else ksq,
                     fk)
        self.num_slices = len(self.kings_of_slice)

    def slice_of(self, wk: int, bk: int,
                 w_rooks: List[int], b_rooks: List[int]) -> int:
        king_sq = (wk, bk)
        rooks = (w_rooks, b_rooks)
        files: List[Tuple[int, ...]] = [(), ()]
        kfile = [-1, -1]
        for cc in (CPP_WHITE, CPP_BLACK):
            if len(rooks[cc]) != self.rights[cc]:
                return -1
            if not self.rights[cc]:
                continue
            rank = castling_home_rank(cc)
            if sq_rank(king_sq[cc]) != rank:
                return -1
            kfile[cc] = sq_file(king_sq[cc])
            for r in rooks[cc]:
                if sq_rank(r) != rank:
                    return -1
            files[cc] = tuple(sorted(sq_file(r) for r in rooks[cc]))

        ci = self.group.index_of(kfile[CPP_WHITE], files[CPP_WHITE],
                                 kfile[CPP_BLACK], files[CPP_BLACK])
        if ci < 0:
            return -1
        slot = 0 if self.both_pinned else king_sq[
            CPP_WHITE if not self.rights[CPP_WHITE] else CPP_BLACK]
        return self._lookup.get((ci, slot), -1)


_CASTLE_KSM_CACHE: Dict[Tuple[int, int], CastlingKingSliceManager] = {}


def castling_king_slice_mgr(white_rights: int, black_rights: int) -> CastlingKingSliceManager:
    key = (white_rights, black_rights)
    ksm = _CASTLE_KSM_CACHE.get(key)
    if ksm is not None:
        return ksm
    with _KSM_LOCK:
        ksm = _CASTLE_KSM_CACHE.get(key)
        if ksm is None:
            ksm = CastlingKingSliceManager(white_rights, black_rights)
            _CASTLE_KSM_CACHE[key] = ksm
        return ksm


_KSM_CACHE: Dict[int, KingSliceManager] = {}
# Building a manager walks 64x64 placements over up to 8 transforms, so two
# threads must not both do it. Double-checked, and the entry is published only
# after __init__ returns, so a half-built manager is never visible.
_KSM_LOCK = threading.Lock()


def king_slice_mgr(sym: int) -> KingSliceManager:
    ksm = _KSM_CACHE.get(sym)
    if ksm is not None:
        return ksm
    with _KSM_LOCK:
        ksm = _KSM_CACHE.get(sym)
        if ksm is None:
            ksm = KingSliceManager(sym)
            _KSM_CACHE[sym] = ksm
        return ksm


# --- Castling_Group (src/chess/castling_group.h) ---
class CastlingGroup:
    """Joint placement of the men standing rights pin: each unmoved king and the
    rooks it could still castle with, on whichever files the game started from.
    56 placements per side, the joint dimension their product. The enumeration
    order MUST match src/chess/castling_group.h -- stored king slice ids are
    built from it."""

    MAX_RIGHTS = 2
    _SIDE_CACHE: Dict[int, List[Tuple[int, Tuple[int, ...]]]] = {}

    @staticmethod
    def _side_placements(num_rights: int) -> List[Tuple[int, Tuple[int, ...]]]:
        cached = CastlingGroup._SIDE_CACHE.get(num_rights)
        if cached is not None:
            return cached
        out: List[Tuple[int, Tuple[int, ...]]] = []
        if num_rights:
            for k in range(8):
                if num_rights == 1:
                    for r in range(8):
                        if r != k:
                            out.append((k, (r,)))
                else:
                    for lo in range(k):
                        for hi in range(k + 1, 8):
                            out.append((k, (lo, hi)))
        CastlingGroup._SIDE_CACHE[num_rights] = out
        return out

    def __init__(self, white_rights: int, black_rights: int):
        self.rights = (white_rights, black_rights)
        self.side = (self._side_placements(white_rights),
                     self._side_placements(black_rights))
        self.b_span = max(len(self.side[CPP_BLACK]), 1)
        self.table_size = max(len(self.side[CPP_WHITE]), 1) * self.b_span
        self.both_pinned = white_rights > 0 and black_rights > 0
        self._inverse: Dict[Tuple[int, Tuple[int, ...], int, Tuple[int, ...]], int] = {}
        for i in range(self.table_size):
            self._inverse[self._key(i)] = i

    def _key(self, idx: int) -> Tuple[int, Tuple[int, ...], int, Tuple[int, ...]]:
        w = self.side[CPP_WHITE][idx // self.b_span] if self.rights[CPP_WHITE] else (-1, ())
        b = self.side[CPP_BLACK][idx % self.b_span] if self.rights[CPP_BLACK] else (-1, ())
        return (w[0], w[1], b[0], b[1])

    def placement(self, idx: int, cpp_col: int) -> Tuple[int, Tuple[int, ...]]:
        within = idx // self.b_span if cpp_col == CPP_WHITE else idx % self.b_span
        return self.side[cpp_col][within]

    def index_of(self, w_king: int, w_rooks: Tuple[int, ...],
                 b_king: int, b_rooks: Tuple[int, ...]) -> int:
        key = (w_king if self.rights[CPP_WHITE] else -1,
               tuple(sorted(w_rooks)) if self.rights[CPP_WHITE] else (),
               b_king if self.rights[CPP_BLACK] else -1,
               tuple(sorted(b_rooks)) if self.rights[CPP_BLACK] else ())
        return self._inverse.get(key, -1)


def castling_home_rank(cpp_col: int) -> int:
    return 0 if cpp_col == CPP_WHITE else 7


def board_castling_rooks(board: chess.Board, color: bool) -> List[int]:
    """Squares of `color`'s rooks that still hold a right, ascending by file.
    python-chess stores the rights as a bitboard of exactly those rooks -- but
    the raw field can name squares no rook stands on, or two rights on one side
    of the king. Those are not table dimensions, so read the cleaned set."""
    return sorted(chess.SquareSet(board.clean_castling_rights()
                                  & board.occupied_co[color]))


# --- Pawn_Slice_Manager ---
class PairGroup:
    """Opposing pawn pair (lowercase 'p'): white pawn on rank r, black on rank s,
    r < s, same file. Enumeration / index_of / find_canonical must match
    src/egtb/pair_group.h exactly -- the on-disk pawn-slice ids depend on them.
    White ranks 2..6, black 3..7: C(6,2)=15 rank pairs x 8 files = 120."""

    def __init__(self) -> None:
        self.white: List[int] = []
        self.black: List[int] = []
        self._inv: Dict[Tuple[int, int], int] = {}
        for f in range(8):
            for wr in range(1, 6):          # ranks 2..6
                for br in range(wr + 1, 7):  # ranks 3..7
                    w = sq_make(wr, f)
                    b = sq_make(br, f)
                    self._inv[(w, b)] = len(self.white)
                    self.white.append(w)
                    self.black.append(b)

    @property
    def table_size(self) -> int:
        return len(self.white)

    def white_square(self, i: int) -> int:
        return self.white[i]

    def black_square(self, i: int) -> int:
        return self.black[i]

    def index_of(self, w: int, b: int) -> int:
        return self._inv[(w, b)]

    @staticmethod
    def is_opposing_pair(w: int, b: int) -> bool:
        return (sq_file(w) == sq_file(b)
                and sq_rank(w) >= 1 and sq_rank(b) <= 6
                and sq_rank(w) < sq_rank(b))

    @staticmethod
    def find_canonical(white_sqs: List[int], black_sqs: List[int]
                       ) -> Optional[Tuple[int, int]]:
        """The opposing pair minimal by (file, white_rank, black_rank), or None.
        Both the generator's prune and this lookup use this one rule."""
        best: Optional[Tuple[Tuple[int, int, int], int, int]] = None
        for w in white_sqs:
            for b in black_sqs:
                if not PairGroup.is_opposing_pair(w, b):
                    continue
                key = (sq_file(w), sq_rank(w), sq_rank(b))
                if best is None or key < best[0]:
                    best = (key, w, b)
        return None if best is None else (best[1], best[2])

    @staticmethod
    def canonical_pair(white_sqs: List[int], black_sqs: List[int]) -> Tuple[int, int]:
        """For callers that know an opposing pair is present (indexing a stored
        pair-table position): the canonical pair, asserting one exists."""
        found = PairGroup.find_canonical(white_sqs, black_sqs)
        assert found is not None
        return found


class PawnSliceManager:
    def __init__(self, pair_group: Optional[PairGroup],
                 white_group: Optional[PieceGroup], black_group: Optional[PieceGroup]):
        self.pair_group = pair_group
        self.white_group = white_group
        self.black_group = black_group
        self.has_pawns = (pair_group is not None
                          or white_group is not None or black_group is not None)
        self.pair_table_size = pair_group.table_size if pair_group else 1
        self.white_table_size = white_group.table_size if white_group else 1
        self.black_table_size = black_group.table_size if black_group else 1
        n_cart = self.pair_table_size * self.white_table_size * self.black_table_size

        def occupancies(g: Optional[PieceGroup]) -> Tuple[List[List[int]], List[int]]:
            if g is None:
                return [[]], [0]
            sqs = [g.squares(i) for i in range(g.table_size)]
            masks = []
            for pl in sqs:
                m = 0
                for s in pl:
                    m |= 1 << s
                masks.append(m)
            return sqs, masks

        white_sqs, white_masks = occupancies(white_group)
        black_sqs, black_masks = occupancies(black_group)
        if pair_group:
            pair_masks = [(1 << pair_group.white_square(p)) | (1 << pair_group.black_square(p))
                          for p in range(self.pair_table_size)]
        else:
            pair_masks = [0]

        self._survivor_bits = bytearray((n_cart + 7) // 8)
        rank_before = array.array("q", bytes(8 * ((n_cart + 63) // 64)))

        num_slices = 0
        cart = 0
        for b_idx in range(self.black_table_size):
            b_mask = black_masks[b_idx]
            for w_idx in range(self.white_table_size):
                if white_masks[w_idx] & b_mask:
                    cart += self.pair_table_size
                    continue
                free_mask = white_masks[w_idx] | b_mask
                for pair_idx in range(self.pair_table_size):
                    if pair_masks[pair_idx] & free_mask:
                        cart += 1
                        continue
                    if pair_group:
                        pair_w = pair_group.white_square(pair_idx)
                        pair_b = pair_group.black_square(pair_idx)
                        cw, cb = PairGroup.canonical_pair(
                            [pair_w] + white_sqs[w_idx], [pair_b] + black_sqs[b_idx])
                        if cw != pair_w or cb != pair_b:
                            cart += 1
                            continue
                    self._survivor_bits[cart >> 3] |= 1 << (cart & 7)
                    num_slices += 1
                    cart += 1
        self.num_slices = num_slices

        running = 0
        for blk in range(len(rank_before)):
            rank_before[blk] = running
            running += chess.popcount(int.from_bytes(
                self._survivor_bits[blk * 8:blk * 8 + 8], "little"))
        self._rank_before_block = rank_before

    def compose(self, pair_idx: int, w_idx: int, b_idx: int) -> int:
        if not self.has_pawns:
            return 0
        cart = (pair_idx
                + w_idx * self.pair_table_size
                + b_idx * self.pair_table_size * self.white_table_size)
        blk, off = divmod(cart, 64)
        word = int.from_bytes(self._survivor_bits[blk * 8:blk * 8 + 8], "little")
        return self._rank_before_block[blk] + chess.popcount(word & ((1 << off) - 1))

    def lookup_from_squares(self, pair_w: int, pair_b: int,
                            white_pawn_sqs: List[int], black_pawn_sqs: List[int]) -> int:
        if not self.has_pawns:
            return 0
        pair_idx = self.pair_group.index_of(pair_w, pair_b) if self.pair_group else 0
        w_idx = self.white_group.compound_index(white_pawn_sqs) if self.white_group else 0
        b_idx = self.black_group.compound_index(black_pawn_sqs) if self.black_group else 0
        return self.compose(pair_idx, w_idx, b_idx)


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


# --- Position_Index_Config ---
class PositionIndexConfig:
    def __init__(self, cfg: PieceConfig):
        self.cfg = cfg
        counts: Dict[Tuple[int, int], int] = {}
        for c, t in cfg.pieces:
            counts[(c, t)] = counts.get((c, t), 0) + 1
        has_pawns = (counts.get((CPP_WHITE, PAWN), 0) > 0
                     or counts.get((CPP_BLACK, PAWN), 0) > 0 or cfg.has_pair)
        self.ksm: Union[KingSliceManager, CastlingKingSliceManager]
        if cfg.has_castling:
            self.sym = SYM_NONE
            self.ksm = castling_king_slice_mgr(cfg.castling_rights[CPP_WHITE],
                                             cfg.castling_rights[CPP_BLACK])
        else:
            self.sym = SYM_FILE_MIRROR if has_pawns else SYM_DIHEDRAL_8
            self.ksm = king_slice_mgr(self.sym)

        self.groups: Dict[int, PieceGroup] = {}
        for c in (CPP_WHITE, CPP_BLACK):
            for t in (QUEEN, ROOK, BISHOP, KNIGHT, PAWN):
                n = counts.get((c, t), 0)
                if n == 0:
                    continue
                pcl = make_piece_class(c, t)
                self.groups[pcl] = PieceGroup(t, n)

        self.pair_group = PairGroup() if cfg.has_pair else None
        self.psm = PawnSliceManager(self.pair_group,
                                    self.groups.get(WHITE_PAWNS), self.groups.get(BLACK_PAWNS))
        self.num_pawn_slices = self.psm.num_slices

        self.populated: List[int] = []
        self.weights: Dict[int, int] = {}
        w = 1
        for i in range(PIECE_CLASS_NB):
            if i not in self.groups:
                continue
            if i == WHITE_PAWNS or i == BLACK_PAWNS:
                continue
            self.populated.append(i)
            self.weights[i] = w
            w *= self.groups[i].table_size
        self.within_slice_size = w
        self.num_king_slices = self.ksm.num_slices
        self.pawn_slice_stride = self.num_king_slices * self.within_slice_size
        self.num_positions = self.num_pawn_slices * self.pawn_slice_stride

    def num_populated_classes(self) -> int:
        return len(self.populated)

    def make_layout(self, perm: int) -> Tuple[List[int], List[int]]:
        order = storage_within_class_order(self.populated, perm)
        radix = [self.groups[c].table_size for c in order]
        return order, radix

    # --- canonicalization + indexing ---
    def _placements_from_board(self, board: chess.Board) -> Dict[int, List[int]]:
        pl: Dict[int, List[int]] = {c: [] for c in range(PIECE_CLASS_NB)}
        wk, bk = board.king(WHITE), board.king(BLACK)
        assert wk is not None and bk is not None  # tablebase positions have both kings
        pl[WHITE_KINGS] = [wk]
        pl[BLACK_KINGS] = [bk]
        # A rook holding a right rides in the king slice, so it is lifted out
        # of its color's rook class.
        castling_rooks = set()
        if self.cfg.has_castling:
            for cc in (CPP_WHITE, CPP_BLACK):
                color = WHITE if cc == CPP_WHITE else BLACK
                castling_rooks.update(board_castling_rooks(board, color))
        for c in self.populated:
            cc, tt = class_to_piece(c)
            color = WHITE if cc == CPP_WHITE else BLACK
            sqs = list(board.pieces(_CPP_TO_PC[tt], color))
            if tt == ROOK and castling_rooks:
                sqs = [s for s in sqs if s not in castling_rooks]
            pl[c] = sqs
        for c in (WHITE_PAWNS, BLACK_PAWNS):
            if c in self.groups or self.pair_group is not None:
                color = WHITE if c == WHITE_PAWNS else BLACK
                pl[c] = list(board.pieces(chess.PAWN, color))
        return pl

    def _canonicalize(self, pl: Dict[int, List[int]]) -> bool:
        # Nothing folds under SYM_NONE: the right tells orientations apart.
        if isinstance(self.ksm, CastlingKingSliceManager):
            return True
        wk = pl[WHITE_KINGS][0]
        bk = pl[BLACK_KINGS][0]
        look = self.ksm.lookup(wk, bk)
        if look[0] == -1:
            return False
        t = look[1]
        if t != T_IDENTITY:
            for c in range(PIECE_CLASS_NB):
                if pl[c]:
                    pl[c] = [apply_transform(s, t) for s in pl[c]]
        if look[2]:  # diagonal stabilizer tie-break (non-pawn populated only)
            cur = alt = 0
            for c in self.populated:
                g = self.groups[c]
                cur += self.weights[c] * g.compound_index(pl[c])
                alt += self.weights[c] * g.compound_index([sq_diag_mirror(s) for s in pl[c]])
            if alt < cur:
                for c in self.populated:
                    pl[c] = [sq_diag_mirror(s) for s in pl[c]]
        return True

    def board_index(self, board: chess.Board, order: List[int], radix: List[int]) -> Optional[int]:
        pl = self._placements_from_board(board)
        if not self._canonicalize(pl):
            return None
        wk = pl[WHITE_KINGS][0]
        bk = pl[BLACK_KINGS][0]
        if isinstance(self.ksm, CastlingKingSliceManager):
            # A castling slice is keyed by the pinned rooks too.
            ksid = self.ksm.slice_of(wk, bk,
                                     board_castling_rooks(board, WHITE),
                                     board_castling_rooks(board, BLACK))
        else:
            ksid = self.ksm.lookup(wk, bk)[0]
        if ksid == -1:
            return None
        pawn_slice = 0
        if self.psm.has_pawns:
            w_pl, b_pl = pl[WHITE_PAWNS], pl[BLACK_PAWNS]
            if self.pair_group is not None:
                pw, pb = PairGroup.canonical_pair(w_pl, b_pl)
                free_w = [s for s in w_pl if s != pw]
                free_b = [s for s in b_pl if s != pb]
            else:
                pw = pb = -1
                free_w, free_b = w_pl, b_pl
            pawn_slice = self.psm.lookup_from_squares(pw, pb, free_w, free_b)
        within_idx = {c: self.groups[c].compound_index(pl[c]) for c in self.populated}
        within = 0
        w = 1
        for i in range(len(order)):
            within += w * within_idx[order[i]]
            w *= radix[i]
        outer = pawn_slice * self.pawn_slice_stride + ksid * self.within_slice_size
        return outer + within


_INDEX_CFG_CACHE: Dict[CacheKey, PositionIndexConfig] = {}
# As for _KSM_LOCK: enumerating pawn slices is worth doing once, and a config is
# immutable once built. Lock order _INDEX_CFG_LOCK -> _KSM_LOCK, never reversed.
_INDEX_CFG_LOCK = threading.Lock()


def position_index_config(cfg: PieceConfig) -> PositionIndexConfig:
    k = cfg.cache_key
    icfg = _INDEX_CFG_CACHE.get(k)
    if icfg is not None:
        return icfg
    with _INDEX_CFG_LOCK:
        icfg = _INDEX_CFG_CACHE.get(k)
        if icfg is None:
            icfg = PositionIndexConfig(cfg)
            _INDEX_CFG_CACHE[k] = icfg
        return icfg


# === On-disk file framing (src/util/memory.h, mono_uint_vec.h, egtb_format.h) ===

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
    """Width of a MULTI record's changepoint bitmap for a stack of `layers`:
    whole 32-bit words, so DTC's 31 layers take 4 bytes and DTM50's 101 take 16."""
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
    """Sequential little-endian reader over a table's buffer, mirroring
    Serial_Memory_Reader. Multi-byte reads materialize the few bytes they need
    rather than ``unpack_from``, which would demand the buffer protocol.
    Nothing derived from the buffer outlives parsing."""

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
    """The 8 bytes at `offset`, little-endian: the hottest read in a probe, so
    it avoids the throwaway slice ``int.from_bytes`` would build. Near the end
    of a mapping fewer than 8 remain, which ``unpack_from`` rejects and the
    slicing form tolerates -- as does a buffer that is not a memoryview."""
    if isinstance(buf, memoryview):
        try:
            return _U64LE.unpack_from(buf, offset)[0]  # type: ignore[no-any-return]
        except struct.error:
            return int.from_bytes(buf[offset:offset + 8], "little")
    return int.from_bytes(bytes(buf[offset:offset + 8]), "little")


def _compressed_block(chunk: Any) -> Any:
    """One compressed block as the decoders want it: slicing a memoryview
    already gives that, any other buffer (:meth:`_TableFile._open_source`)
    materializes here -- a block being the widest span a probe asks for."""
    if isinstance(chunk, (bytes, bytearray, memoryview)):
        return chunk
    return bytes(chunk)


class MonoUintVec:
    """Block-sampled delta coder for a monotone uint64 sequence.

    Addressed as `base` plus a bit offset into the table's buffer, not as a
    slice of it: no span wider than one read is taken
    (:meth:`_TableFile._open_source`)."""

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


# --- LZ4 block decompression with optional dictionary prefix ---

def lz4_decompress_block(src: memoryview, expected_size: int, dict_bytes: bytes = b"") -> bytes:
    """Decompress an LZ4 *block* (not frame). A dictionary, if given, logically
    precedes the output. Handed to `python-lz4 <https://pypi.org/project/lz4/>`_
    where installed -- the same C library that wrote the tables, and it releases
    the GIL -- else to :func:`lz4_decompress_block_python`."""
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


# === Decoded-block cache ===

#: Default soft budget (bytes) for decoded blocks held resident across all
#: tables of a :class:`Tablebase`. The cache evicts least-recently-used blocks
#: once the budget is exceeded, so memory is reclaimed automatically without an
#: explicit :meth:`Tablebase.close`.
DEFAULT_BLOCK_CACHE_BYTES = 64 * 1024 * 1024


class _PerColor:
    """State for one color's frame of one table: the decoded-block dict plus
    the locks guarding decodes into it. Everything else here is written once
    during construction, before any other thread can reach the table, and
    read-only after; ``_blocks`` is the exception probes fill as they go.
    """

    __slots__ = ("_blocks", "_block_locks", "_meta_lock")

    _blocks: Dict[int, Any]

    def __init__(self) -> None:
        self._blocks = {}
        # One lock per block id, not one per color, and lzma releases the GIL,
        # so two cold-block decodes really do run in parallel.
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
    """LRU reclaimer shared by every table of a :class:`Tablebase`. Tracks the
    per-color ``_blocks`` entries in one least-recently-used order and, once the
    resident estimate exceeds ``max_bytes``, drops the oldest from their owning
    dict. Sizes are approximate; the budget is a soft target.
    """

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
        """Register a freshly decoded block and evict until within budget.
        Re-recording a tracked block subtracts the old size first, so two
        concurrent decoders cannot skew the running total.
        """
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
        """Evict one block from its owning per-color object, decode lock included
        so `_block_locks` stays bounded. A thread may hold that lock mid-decode;
        a later one then makes a fresh lock and both write the same bytes.
        """
        pc._blocks.pop(block_id, None)
        pc._block_locks.pop(block_id, None)


#: What :meth:`Tablebase._find` resolves a table to: a path by default, else
#: whatever that transport's :meth:`_TableFile._open_source` understands. Only
#: interpolated into messages, so a handle wants a ``__str__``.
TableSource = Any


class _TableFile:
    """Shared source lifecycle for the four table kinds. Files are mapped
    read-only rather than read in: a probe touches a handful of blocks, so the
    page cache serves them and stays reclaimable. :meth:`_open_source` is the
    only place that choice is made.
    """

    EXT: str
    MAGIC: int
    KIND: str
    cache: _BlockCache
    per_color: List[Any]
    path: TableSource

    _data: Optional[Any] = None
    _reader: Optional[_Serial] = None

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
        raise NotImplementedError

    def _open_source(self, path: TableSource) -> Any:
        """Open `path`, set ``self._data`` to what :meth:`close` releases, and
        return the buffer to read the table through. Maps the file by default,
        and is the one seam another transport replaces. An override may return
        any object with ``len()``, indexing and slicing; no span wider than one
        block is taken, so it wants a page cache under it."""
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            data = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        finally:
            os.close(fd)

        try:
            data.madvise(mmap.MADV_RANDOM)
        except AttributeError:
            pass

        self._data = data
        return memoryview(data)

    def close(self) -> None:
        """Drop decoded blocks and release the source. Idempotent, and requires
        that no thread is inside a probe of this table -- which is why
        :meth:`Tablebase.close` drains its readers first.
        """
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


_TableFileT = TypeVar("_TableFileT", bound=_TableFile)


# === WDL table file ===

def egtb_table_colors(table_num: int) -> List[int]:
    return [CPP_WHITE] + ([CPP_BLACK] if table_num == 2 else [])


class _WDLPerColor(_PerColor):
    __slots__ = ("order", "radix", "block_size", "tail_size", "block_cnt",
                 "data_size", "offsets", "buf", "data_off", "dict", "single_val",
                 "dict_size")
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
    dict_size: int
    _blocks: Dict[int, bytes]

    def __init__(self) -> None:
        super().__init__()
        self.single_val = DRAW
        self.dict = b""
        self.dict_size = 0


class WDLFile(_TableFile):
    EXT = ".lzw"
    MAGIC = WDL_MAGIC
    KIND = "WDL"

    def __init__(self, cfg: PieceConfig, path: TableSource,
                 cache: Optional[_BlockCache] = None):
        self.cfg = cfg
        self.index_cfg = position_index_config(cfg)
        self.cache = cache if cache is not None else _BlockCache(DEFAULT_BLOCK_CACHE_BYTES)
        self.is_singular = [False, False]
        self.is_dropped = [False, False]
        self.is_loss_only = [False, False]
        self.is_relaxed = [False, False]
        self.per_color: List[Optional[_WDLPerColor]] = [None, None]
        self._open(path)

    def _parse(self, r: _Serial) -> None:
        magic = r.u32()
        if magic != self.MAGIC:
            raise ValueError(f"Invalid WDL magic {self.path}")
        key_and_table = r.u32()
        key = key_and_table >> 2
        expected_key = self.cfg.min_key & _PACKED_MATERIAL_KEY_MASK
        if key != expected_key:
            raise ValueError(f"Wrong material key in WDL {self.path}: {key} != {expected_key}")
        table_num = key_and_table & 3
        colors = egtb_table_colors(table_num)
        for c in colors:
            flag = r.u8()
            pc = _WDLPerColor()
            self.per_color[c] = pc
            self.is_loss_only[c] = bool(flag & LOSS_ONLY_FLAG)
            self.is_relaxed[c] = bool(flag & RELAXED_FLAG)
            if flag & SINGULAR_FLAG:
                self.is_singular[c] = True
                pc.single_val = r.u8()
            elif flag & DROPPED_FLAG:
                self.is_dropped[c] = True
            else:
                self._parse_header(r, pc)
        if table_num == 1:
            self.is_dropped[CPP_BLACK] = True
            self.is_loss_only[CPP_BLACK] = self.is_loss_only[CPP_WHITE]
            self.is_relaxed[CPP_BLACK] = self.is_relaxed[CPP_WHITE]
        self._finalize(r, colors)

    def _parse_header(self, r: _Serial, pc: _WDLPerColor) -> None:
        perm = r.u32()
        n = self.index_cfg.num_populated_classes()
        if not index_permutation_valid(n, perm):
            raise ValueError("Invalid WDL index permutation")
        pc.order, pc.radix = self.index_cfg.make_layout(perm)
        pc.tail_size = r.u16()
        pc.block_size = r.u32()
        pc.block_cnt = r.u64()
        pc.data_size = r.u64()

    def _finalize(self, r: _Serial, colors: List[int]) -> None:
        for c in colors:
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            pc.dict_size = r.u16()
            if pc.dict_size != 0:
                start = r.caret()
                pc.dict = bytes(r.d[start:start + pc.dict_size])
                r.advance(pc.dict_size)
        for c in colors:
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
        for c in colors:
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.buf, pc.data_off = r.d, start
            r.advance(pc.data_size)

    def _get_block(self, pc: _WDLPerColor, block_id: int) -> bytes:
        blk = pc._blocks.get(block_id)
        if blk is not None:
            self.cache.touch(pc, block_id)
            return blk
        # Cold block: one thread decodes, others wait rather than duplicate.
        # Re-checked inside the lock, the winner having filled `_blocks`.
        with pc.lock_for(block_id):
            blk = pc._blocks.get(block_id)
            if blk is not None:
                self.cache.touch(pc, block_id)
                return blk
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
        data = self._get_block(pc, block_id)
        entry = data[in_block]
        return (entry >> ((pos % 2) * 4)) & 0xF


def _exists_case_exact(path: str) -> bool:
    """Whether `path` exists spelled exactly as it is on disk.

    Case carries meaning in a table name -- lowercase ``p`` is the opposing
    pair, ``r`` a rook still holding a right -- so ``KRK`` must not answer for
    ``KrK``: the specialized tables are optional, and a miss falls back to the
    plain twin. Only a case-folding filesystem can get that wrong, and the scan
    that settles it is O(entries) over a directory holding a great many tables,
    so one stat on the case-flipped name decides whether it is needed.
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


# === Probe orchestration (subset: WDL).  Mirrors src/probe/probe.cpp. ===

def mirror_for_canonical(board: chess.Board) -> chess.Board:
    """Swap colors and rank-mirror every piece; flip side to move. The ep square
    is rank-mirrored with everything else. Mirrors Position::mirror in
    src/chess/position.h."""
    out = board.copy(stack=False)
    out.apply_mirror()
    return out


_WDL_NAME = {LOSE: "LOSE", BLESSED_LOSS: "BLESSED_LOSS", DRAW: "DRAW",
             CURSED_WIN: "CURSED_WIN", WIN: "WIN", ILLEGAL: "ILLEGAL"}


# --- WDL semantic helpers (egtb_entry.h / probe.cpp) ---

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
    return cfg.has_pair or any(t == PAWN for _c, t in cfg.pieces)


def is_win_class(w: int) -> bool:
    return w == WIN or w == CURSED_WIN


def locate_frame(f: Any, cfg: PieceConfig, board: chess.Board,
                 wdl: int) -> Tuple[int, Optional[chess.Board], bool]:
    """Which frame holds a cell, whether it needs mirroring, and whether it is
    there to be read. A dropped frame is reachable through the mirror when the
    material is its own mirror; a loss-only frame holds no win. Both gaps are
    filled by the same one-ply derive, run on the unmirrored board."""
    color = CPP_WHITE if board.turn == WHITE else CPP_BLACK
    if not f.is_dropped[color]:
        return color, None, not (f.is_loss_only[color] and is_win_class(wdl))
    if not is_symmetric_material(cfg):
        return color, None, False
    kept = CPP_BLACK if color == CPP_WHITE else CPP_WHITE
    if f.is_loss_only[kept] and is_win_class(wdl):
        return kept, None, False
    return kept, mirror_for_canonical(board), True


MAX_DERIVE_DEPTH = 64


def _internal_board(board: chess.Board) -> chess.Board:
    if board.ep_square is not None:
        board = board.copy(stack=False)
        board.ep_square = None
    return board


# === LZMA block decode + value-from-storage helpers (egtb_entry.h) ===

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


# === DTZ / DTM table files  —  src/probe/dtz_file.cpp, src/probe/dtm_file.cpp ===

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
    """The rank-coded, LZMA-blocked table body. DTM is the byte-for-byte twin
    of DTZ (as ``src/probe/dtm_file.cpp`` says of its own traits); only the
    magic and the value decode differ, so both files parse and read their
    stored cells through this one."""

    def __init__(self, cfg: PieceConfig, path: TableSource,
                 cache: Optional[_BlockCache] = None):
        self.cfg = cfg
        self.index_cfg = position_index_config(cfg)
        self.cache = cache if cache is not None else _BlockCache(DEFAULT_BLOCK_CACHE_BYTES)
        self.is_singular = [False, False]
        self.is_dropped = [False, False]
        self.is_loss_only = [False, False]
        self.is_relaxed = [False, False]
        self.per_color: List[Optional[_RankPerColor]] = [None, None]
        self._open(path)

    def _parse(self, r: _Serial) -> None:
        if r.u32() != self.MAGIC:
            raise ValueError(f"Invalid {self.KIND} magic {self.path}")
        kat = r.u32()
        if (kat >> 2) != (self.cfg.min_key & _PACKED_MATERIAL_KEY_MASK):
            raise ValueError(f"Wrong material key in {self.KIND}")
        table_num = kat & 3
        colors = egtb_table_colors(table_num)
        for c in colors:
            flag = r.u8()
            pc = _RankPerColor()
            self.per_color[c] = pc
            self.is_loss_only[c] = bool(flag & LOSS_ONLY_FLAG)
            self.is_relaxed[c] = bool(flag & RELAXED_FLAG)
            if flag & SINGULAR_FLAG:
                self.is_singular[c] = True
                pc.single_val = r.u8()
            elif flag & DROPPED_FLAG:
                self.is_dropped[c] = True
            else:
                self._parse_header(r, pc)
        if table_num == 1:
            self.is_dropped[CPP_BLACK] = True
            self.is_loss_only[CPP_BLACK] = self.is_loss_only[CPP_WHITE]
            self.is_relaxed[CPP_BLACK] = self.is_relaxed[CPP_WHITE]
        self._finalize(r, colors)

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

    def _finalize(self, r: _Serial, colors: List[int]) -> None:
        for c in colors:
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            log2_bu = r.u8()
            sample_width = r.u8()
            offset_width = r.u8()
            r.advance(1)  # usz_width (unused here)
            mono_off = r.caret()
            mb = MonoUintVec.on_disk_bytes(pc.block_cnt + 1, log2_bu, sample_width, offset_width)
            r.advance(mb)
            pc.offsets = MonoUintVec(r.d, mono_off, pc.block_cnt + 1, log2_bu,
                                     sample_width, offset_width)
        for c in colors:
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.buf, pc.data_off = r.d, start
            r.advance(pc.data_size)

    def _get_block_raw(self, pc: _RankPerColor, block_id: int) -> bytes:
        blk = pc._blocks.get(block_id)
        if blk is not None:
            self.cache.touch(pc, block_id)
            return blk
        with pc.lock_for(block_id):  # see WDLFile._get_block
            blk = pc._blocks.get(block_id)
            if blk is not None:
                self.cache.touch(pc, block_id)
                return blk
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
        raw = self._get_block_raw(pc, block_id)
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
        # Plain parity: the class supplies the low bit, not the cell width.
        return 0 if cell is None else dtm_value_from_storage(cell[0], wdl)


# === Changepoint packs  —  src/probe/layered_file.h, dtm50_file.cpp, dtc_file.cpp ===
#
# One container, two metrics: DTM50 stacks 101 layers by halfmove clock, DTC 30
# budget points plus DTZ's terminal changepoint. Both open every record with
# that embedded endpoint. Block decode is shared; each ``read`` is its own.

def _bit(buf: bytes, i: int) -> int:
    return (buf[i >> 3] >> (i & 7)) & 1


# --- block-local prefix indexes (src/probe/layered_file.h) ---
#
# A read needs a position's 2-bit state and its index among positions sharing
# it. Indexing all 1,048,576 per block would cost a ~40 MiB list that dwarfs the
# payload, so index every STRIDE-th and walk at most one stride, as the C++ does.
_LAYERED_STRIDE = 256
_STATE_STRIDE_BYTES = _LAYERED_STRIDE // 4  # 2-bit states: 4 per byte
_HINT_STRIDE_BYTES = _LAYERED_STRIDE // 8   # hint bitmaps: 8 per byte

#: State-bitmap byte -> how many of its four fields are state `s`, so that
#: ``translate`` + ``sum`` counts a byte range in C.
_STATE_COUNT_XLAT = tuple(
    bytes(sum(1 for k in range(4) if (b >> (2 * k)) & 3 == s) for b in range(256))
    for s in range(4))

#: ``[b][q][s]``: fields before `q` of byte `b` in state `s` -- the partial
#: byte a walk ends on.
_STATE_FIELD_PREFIX = tuple(
    tuple(tuple(sum(1 for k in range(q) if (b >> (2 * k)) & 3 == s) for s in range(4))
          for q in range(4))
    for b in range(256))


def _state_stride_index(state_bits: bytes, num_positions: int) -> Tuple[array.array[int], ...]:
    """Per-state cumulative counts at every stride boundary: ``cum[s][k]`` is
    how many of the first ``k * _LAYERED_STRIDE`` positions are in state `s`.

    The last entry may include padding fields, which no read reaches: stride
    `k` only ever consults ``cum[s][k]``."""
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
    """The draw-end bits of `n` variable-width records, gathered into a bitmap.
    The bit is the MSB of the record's last h byte -- its first for SINGLE, its
    second for DOUBLE -- and only a walk finds the next record."""
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
    """Popcount of bits [0, `i`) of a hint bitmap: the stride total, then at
    most one stride of walking. Entry `i` itself is never counted, so the
    bitmap only has to cover the entries that exist."""
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


def _multi_last_changepoint(bits: int) -> int:
    return bits.bit_length() - 1 if bits else 0


class _LayeredFile(_TableFile):
    """The changepoint container both packs are written in: header, offsets
    section and block decode, down to the per-position state and its record.
    What a record *means* is the metric's, so ``read`` lives in the subclass."""

    def __init__(self, cfg: PieceConfig, path: TableSource,
                 cache: Optional[_BlockCache] = None):
        self.cfg = cfg
        self.index_cfg = position_index_config(cfg)
        self.cache = cache if cache is not None else _BlockCache(DEFAULT_BLOCK_CACHE_BYTES)
        self.is_singular = [False, False]
        self.is_dropped = [False, False]
        self.is_loss_only = [False, False]
        self.per_color: List[Optional[_LayeredPerColor]] = [None, None]
        self._open(path)

    def _parse(self, r: _Serial) -> None:
        if r.u32() != self.MAGIC:
            raise ValueError(f"Invalid {self.KIND} magic")
        kat = r.u32()
        if (kat >> 2) != (self.cfg.min_key & _PACKED_MATERIAL_KEY_MASK):
            raise ValueError(f"Wrong material key in {self.KIND}")
        table_num = kat & 3
        colors = egtb_table_colors(table_num)
        for c in colors:
            flag = r.u8()
            pc = _LayeredPerColor()
            self.per_color[c] = pc
            self.is_loss_only[c] = bool(flag & LOSS_ONLY_FLAG)
            if flag & SINGULAR_FLAG:
                self.is_singular[c] = True
                if r.u8() != 0:
                    raise ValueError(f"{self.KIND} singular value must be DRAW")
            elif flag & DROPPED_FLAG:
                self.is_dropped[c] = True
            else:
                self._parse_header(r, pc)
        if table_num == 1:
            self.is_dropped[CPP_BLACK] = True
            self.is_loss_only[CPP_BLACK] = self.is_loss_only[CPP_WHITE]
        self._finalize(r, colors)

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

    def _finalize(self, r: _Serial, colors: List[int]) -> None:
        for c in colors:
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
        for c in colors:
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.buf, pc.data_off = r.d, start
            r.advance(pc.data_size)

    def _get_block(self, pc: _LayeredPerColor, block_id: int) -> Dict[str, Any]:
        blk = pc._blocks.get(block_id)
        if blk is not None:
            self.cache.touch(pc, block_id)
            return blk
        with pc.lock_for(block_id):
            blk = pc._blocks.get(block_id)
            if blk is not None:
                self.cache.touch(pc, block_id)
                return blk
            return self._decode_block(pc, block_id)

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
        """A position's decoded block, its record state and its index among the
        records sharing that state. ``None`` where nothing is stored, which
        reads as drawn at every layer."""
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
        blk = self._get_block(pc, block_id)
        st, idx = _state_and_index(blk["state_bits"], blk["state_cum"], pos_in_block)
        return blk, st, idx


class DTM50File(_LayeredFile):
    EXT = ".lzdtm50"
    MAGIC = DTM50_MAGIC
    KIND = "DTM50"

    def read(self, color: int, board: chess.Board, wdl: int,
             hmc: int) -> Tuple[int, int]:
        """The value at `hmc`, and the layer where the cell turns DRAW; the
        terminal rank decides both. Only the draw-end hint says DRAW; a stored
        0 is a mate."""
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
        if st == 0:  # CONST: one rank for all layers, so it never flips
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
        else:  # MULTI: changepoint bitmap, the stack height in bits used
            entry = blk["multi_data_off"] + struct.unpack_from(
                "<I", payload, blk["multi_dir_off"] + idx * 4)[0]
            kbyte = payload[entry]
            draw_end = (kbyte & 0x80) != 0
            k = kbyte & 0x7F
            bits = _multi_bitmap(payload, entry, DTM50_MULTI_BITMAP_BYTES)
            rsel = bin(bits & ((1 << (layer + 1)) - 1)).count("1") - 1
            if draw_end:
                draw_flip = _multi_last_changepoint(bits)
            if rsel == k - 1 and draw_end:
                return (DRAWN_AT_LAYER, draw_flip)
            stored = r2v[self._read_rank(
                payload, entry + 1 + DTM50_MULTI_BITMAP_BYTES + rsel * eb, eb)]

        if flat:
            return (dtm_value_from_storage(stored, wdl), draw_flip)
        return (dtm50_value_from_storage(stored, wdl), draw_flip)


def dtc_budget_plies(rule50: int) -> int:
    """Plies a DTC answer may still spend before the 50-move claim: the whole
    band where the caller ignores the rule, and none at all once the clock has
    reached the claim, where only a mate already on the board, at distance 0,
    outruns it."""
    if rule50 == IGNORE_50MR:
        return MAX_NON_CURSED_DTZ
    return 0 if rule50 >= MAX_NON_CURSED_DTZ else MAX_NON_CURSED_DTZ - rule50


class _DTCCell(NamedTuple):
    """One DTC cell: pushes the winning side still owes before a conversion, and
    plies to the next zeroing move on the line that owes them, both from the
    budget layer fitting the caller's clock. ``dtz`` is the record's unbounded
    row -- the DTZ table the pack embeds -- which a cursed class has only."""

    order: int = 0
    value: int = DRAWN_AT_LAYER
    dtz: int = DRAWN_AT_LAYER
    dtz_rounded: bool = False

    @property
    def priced(self) -> bool:
        return self.value != DRAWN_AT_LAYER


class _BudgetSegments(NamedTuple):
    """One position's value as a function of push budget, read off its record.
    The budget runs down as the pack index runs up, so `segs` is ascending in
    both row and value; `draw_start` is the row a trailing DRAW segment begins
    at, which is what the record's hint bit says."""

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
        """The fewest pushes whose plies-to-zeroing still fit the clock the
        caller holds: the deepest budget index that stays inside `rule50`.
        Fewer pushes may cost a longer wait, so a fresh clock buys the fewest any
        line manages -- which is whatever the position needs, not necessarily
        none."""
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
        """The same decode, spread over the budgets it covers instead of
        resolved against a clock: ``DRAWN_AT_LAYER`` wherever a budget point settles
        nothing, which for a cursed class is everywhere. The first 30 entries
        are separately solved finite points; the top entry is the embedded DTZ
        terminal endpoint."""
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


# === Probe orchestration  —  src/probe/probe.cpp ===

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


def below_pinned_class(pinned: int, offer: int) -> bool:
    """Derivation stands in for `read(color, board, wdl)`. Reads are
    class-driven: the WDL companion pins the class, while the file only prices
    the distance. A child that cannot reach the pinned class never wins the
    minimax and never needs a probe. ILLEGAL pins nothing -- the WDL table had
    no answer either."""
    return pinned != ILLEGAL and wdl_rank(offer) < wdl_rank(pinned)


def child_class_is_forced(pinned: int) -> bool:
    """A LOSE pin makes WIN a safe child-class surrogate: under an exact pin
    every child is a clean WIN, or the parent would be BLESSED_LOSS, and under a
    folded DTM pin WIN and CURSED_WIN are equivalent to the minimax anyway.
    """
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
    """5-class WDL -> the three a clocked metric holds, DTM50's layers and DTC's
    budgets alike: cursed and blessed are unreachable under 50MR."""
    if w == CURSED_WIN or w == BLESSED_LOSS:
        return DRAW
    return w


def dtz_from_draw_flip(h: int, wdl: int, board: chess.Board) -> Optional[int]:
    """The DRAW flip pins DTZ: a W/L cell still decisive at hmc = 100 - dtz turns
    one tick later, so its flip layer (hmc + 1) is h = 102 - dtz. h == 1 is a
    cell already drawn at a fresh clock -- the cursed band, whose distance the
    flip says nothing about; never flipping means dtz <= 1, which only a mate
    splits. DRAW/ILLEGAL answer 0, the don't-care the DTZ table decodes."""
    if wdl == DRAW or wdl == ILLEGAL:
        return 0
    if wdl not in (WIN, LOSE):
        return None
    if h == 0:
        return 0 if (wdl == LOSE and board.is_checkmate()) else 1
    if h == 1:
        return None
    return MAX_NON_CURSED_DTZ + 2 - h


# Two bounds on the layer at `rule50`, W/L only -- cursed and blessed are DRAW at
# every layer. Pinned: rule50 + dtm <= 100, the whole mating line fits the
# window, so the layer takes the flat DTM (inclusive: the game ends at mate,
# before a draw can be claimed). Busted: rule50 + dtz > 100, no line resets the
# count in time, so the layer is DRAW and no surviving position gets a distance.
#
# An unpriced distance reads as 0, so the pin needs a has_dtm at the call site
# while the bust cannot fire on one.
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
    """Children a derive could not price. A skip unpins the minimax only if the
    class it could have offered outranks the kept best; an unknown class unpins
    outright. Every deriver runs this."""

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
    """The DTZ half of a derive: zeroing distance ranks moves its own way, so
    it minimaxes beside the mate distance over the same children. Fed per child;
    `finish` writes the field a read cell gets from its flip."""

    __slots__ = ("_have", "_best_wdl", "_best_dtz", "_skipped")

    def __init__(self) -> None:
        self._have = False
        self._best_wdl = LOSE
        self._best_dtz = 0
        self._skipped = _SkippedChildren()

    def zeroing_child(self, child_wdl: int) -> None:
        self._offer(child_wdl, 1)

    def quiet_child(self, child_wdl: int, child: _DTM50Result, cursed_exit: bool) -> None:
        if child.has_dtz:
            self._offer(child_wdl, _quiet_move_dtz(child.dtz, cursed_exit, False))
        else:
            self._skipped.of_dtz_class(invert_wdl(child_wdl))

    def unwalked(self) -> None:
        self._skipped.unknown()

    def finish(self, wdl: int, dtm: int, any_legal: bool) -> _DTM50Result:
        if not any_legal:  # mate or stalemate: terminal, zeroing distance 0
            return _DTM50Result(wdl, dtm, True, 0)
        if not self._have or self._skipped.unpin(self._best_wdl):
            return _DTM50Result(wdl, dtm)
        return _DTM50Result(wdl, dtm, True,
                            0 if self._best_wdl == DRAW else self._best_dtz)

    def _offer(self, child_wdl: int, dtz: int) -> None:
        my_wdl = invert_wdl(child_wdl)
        if dtz > MAX_NON_CURSED_DTZ:
            if my_wdl == WIN:
                my_wdl = CURSED_WIN
            elif my_wdl == LOSE:
                my_wdl = BLESSED_LOSS
        if not self._have or prefer_new(my_wdl, dtz, self._best_wdl, self._best_dtz):
            self._best_wdl, self._best_dtz, self._have = my_wdl, dtz, True


class _UnboundedFold:
    """DTC's fold for the unbounded row it carries: a zeroing move ends the
    count one ply out, a quiet move waits one longer, and the class says whether
    the shortest or the longest of them stands. One child unable to say leaves
    the row unanswered, since a best over part of the moves is a wrong answer
    rather than a partial one."""

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

    ``status`` is ``"ok"`` or ``"tb_not_found"``. ``wdl``, ``dtc_wdl`` and
    ``dtm50_wdl`` are :data:`WIN`..:data:`LOSE` codes; ``dtz``/``dtc``/``dtm``/
    ``dtm50`` are unsigned plies signed by the matching WDL class. ``dtc_order``
    is the pushes the winner still owes; ``has_dtc`` says the metric is
    available and ``dtc_wdl`` what it found, a 50MR draw included.
    ``dtz_rounded`` says ``dtz`` may be a ply off.
    """

    __slots__ = ("status", "wdl", "has_dtz", "dtz", "dtz_rounded", "has_dtc", "dtc_wdl",
                 "dtc_order", "dtc", "has_dtm", "dtm",
                 "has_dtm50", "dtm50_wdl", "dtm50")

    status: str
    wdl: int
    has_dtz: bool
    dtz: int
    dtz_rounded: bool
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
        self.status = "tb_not_found"
        self.wdl = ILLEGAL
        self.has_dtz = False
        self.dtz = 0
        self.dtz_rounded = False
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
        if self.status != "ok":
            return f"<ProbeResult {self.status}>"
        s = f"<ProbeResult wdl={_WDL_NAME[self.wdl]}"
        if self.has_dtz:
            s += f" dtz={self.dtz}"
        if self.has_dtc:
            s += f" dtc={_WDL_NAME[self.dtc_wdl]}/{self.dtc_order}/{self.dtc}"
        if self.has_dtm:
            s += f" dtm={self.dtm}"
        if self.has_dtm50:
            s += f" dtm50={_WDL_NAME[self.dtm50_wdl]}/{self.dtm50}"
        return s + ">"


def _fill_pawnless_dtc_from_dtz(r: ProbeResult, rule50: int) -> None:
    if r.wdl not in (WIN, LOSE):
        r.has_dtc = True
        r.dtc_wdl = DRAW
        return
    if not r.has_dtz:
        return

    busted = r.dtz > dtc_budget_plies(rule50)
    r.has_dtc = True
    r.dtc_wdl = DRAW if busted else r.wdl
    r.dtc = 0 if busted else r.dtz


class MissingTableError(KeyError):
    """Raised when no table is available for the queried material."""


_WDL_SIGNED = {WIN: 2, CURSED_WIN: 1, DRAW: 0, BLESSED_LOSS: -1, LOSE: -2}


def _signed(magnitude: int, wdl: int) -> int:
    if wdl in (WIN, CURSED_WIN):
        return magnitude
    if wdl in (LOSE, BLESSED_LOSS):
        return -magnitude
    return 0


# === Tablebase ===

class Tablebase:
    """Probe a directory tree of chesstb tables.

    `directory` may hold ``wdl/``, ``dtz/``, ``dtc/``, ``dtm/`` and ``dtm50/``
    subdirectories (the generator's layout) or the table files directly. Use
    :func:`open_tablebase`. One instance is meant to be shared by every thread
    that probes, so tables and blocks are opened and decoded once for everyone.
    """

    #: The classes ``_open_wdl`` and its siblings instantiate. A transport
    #: names its subclasses here and overrides :meth:`_find`.
    WDL_FILE: Type[WDLFile] = WDLFile
    DTZ_FILE: Type[DTZFile] = DTZFile
    DTC_FILE: Type[DTCFile] = DTCFile
    DTM_FILE: Type[DTMFile] = DTMFile
    DTM50_FILE: Type[DTM50File] = DTM50File

    KINDS = ("wdl", "dtz", "dtc", "dtm", "dtm50")

    def __init__(self, directory: str, *, block_cache_bytes: int = DEFAULT_BLOCK_CACHE_BYTES):
        self.dirs: Dict[str, List[str]] = {kind: [] for kind in self.KINDS}
        self._wdl_cache: Dict[CacheKey, Optional[WDLFile]] = {}
        self._dtz_cache: Dict[CacheKey, Optional[DTZFile]] = {}
        self._dtc_cache: Dict[CacheKey, Optional[DTCFile]] = {}
        self._dtm_cache: Dict[CacheKey, Optional[DTMFile]] = {}
        self._dtm50_cache: Dict[CacheKey, Optional[DTM50File]] = {}
        # One lock per kind, guarding that kind's open cache and `dirs` entry.
        # Held only across a first open, never across a probe; KINDS order.
        self._open_locks: Dict[str, threading.Lock] = {
            kind: threading.Lock() for kind in self.KINDS}
        self._read_condition = threading.Condition()
        self._read_count = 0
        self._block_cache = _BlockCache(block_cache_bytes)
        self.add_directory(directory)

    def add_directory(self, directory: str) -> None:
        """Add another search directory. Each kind searches its subdirectory
        (``wdl/``, ``dtz/``, …) when that exists, else the directory itself; a
        directory already searched for a kind is not added again.

        Safe to call while other threads probe: each kind's list is extended
        under the lock its :meth:`_find` holds. Tables already resolved are not
        re-resolved, so a late directory only affects materials not yet looked
        up.
        """
        for kind in self.KINDS:
            sub = os.path.join(directory, kind)
            d = sub if os.path.isdir(sub) else directory
            with self._open_locks[kind]:
                key = os.path.normpath(d)
                if all(os.path.normpath(e) != key for e in self.dirs[kind]):
                    self.dirs[kind].append(d)

    def close(self) -> None:
        """Drop all cached decoded blocks and unmap all open tables. Waits for
        probes on other threads first: unmapping under a live probe would pull
        the table's memory out from under it.
        Probes arriving afterwards are not turned away -- they reopen what
        they need -- so a continuous stream can keep this waiting.
        """
        with self._read_condition:
            while self._read_count > 0:
                self._read_condition.wait()
            self._block_cache.clear()
            with self._open_locks["wdl"]:
                self._close_all(self._wdl_cache)
            with self._open_locks["dtz"]:
                self._close_all(self._dtz_cache)
            with self._open_locks["dtc"]:
                self._close_all(self._dtc_cache)
            with self._open_locks["dtm"]:
                self._close_all(self._dtm_cache)
            with self._open_locks["dtm50"]:
                self._close_all(self._dtm50_cache)

    @staticmethod
    def _close_all(cache: Dict[CacheKey, Optional[_TableFileT]]) -> None:
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
        """Resolve one table to something :meth:`_TableFile._open_source` opens,
        or ``None`` if this tablebase has no such table."""
        for d in self.dirs[kind]:
            p = os.path.join(d, name + ext)
            if _exists_case_exact(p):
                return p
        return None

    # A cached `None` means "looked, no such table", so these subscript rather
    # than `.get()`. Only a first open takes the lock, re-checking inside.
    def _open_wdl(self, cfg: PieceConfig) -> Optional[WDLFile]:
        k = cfg.cache_key
        try:
            return self._wdl_cache[k]
        except KeyError:
            pass
        with self._open_locks["wdl"]:
            try:
                return self._wdl_cache[k]
            except KeyError:
                pass
            p = self._find("wdl", cfg.name(), self.WDL_FILE.EXT)
            table = self.WDL_FILE(cfg, p, self._block_cache) if p is not None else None
            self._wdl_cache[k] = table
            return table

    def _open_dtz(self, cfg: PieceConfig) -> Optional[DTZFile]:
        k = cfg.cache_key
        try:
            return self._dtz_cache[k]
        except KeyError:
            pass
        with self._open_locks["dtz"]:
            try:
                return self._dtz_cache[k]
            except KeyError:
                pass
            p = self._find("dtz", cfg.name(), self.DTZ_FILE.EXT)
            table = self.DTZ_FILE(cfg, p, self._block_cache) if p is not None else None
            self._dtz_cache[k] = table
            return table

    def _open_dtm(self, cfg: PieceConfig) -> Optional[DTMFile]:
        k = cfg.cache_key
        try:
            return self._dtm_cache[k]
        except KeyError:
            pass
        with self._open_locks["dtm"]:
            try:
                return self._dtm_cache[k]
            except KeyError:
                pass
            p = self._find("dtm", cfg.name(), self.DTM_FILE.EXT)
            table = self.DTM_FILE(cfg, p, self._block_cache) if p is not None else None
            self._dtm_cache[k] = table
            return table

    def _open_dtc(self, cfg: PieceConfig) -> Optional[DTCFile]:
        k = cfg.cache_key
        try:
            return self._dtc_cache[k]
        except KeyError:
            pass
        with self._open_locks["dtc"]:
            try:
                return self._dtc_cache[k]
            except KeyError:
                pass
            p = self._find("dtc", cfg.name(), self.DTC_FILE.EXT)
            table = self.DTC_FILE(cfg, p, self._block_cache) if p is not None else None
            self._dtc_cache[k] = table
            return table

    def _open_dtm50(self, cfg: PieceConfig) -> Optional[DTM50File]:
        k = cfg.cache_key
        try:
            return self._dtm50_cache[k]
        except KeyError:
            pass
        with self._open_locks["dtm50"]:
            try:
                return self._dtm50_cache[k]
            except KeyError:
                pass
            p = self._find("dtm50", cfg.name(), self.DTM50_FILE.EXT)
            table = self.DTM50_FILE(cfg, p, self._block_cache) if p is not None else None
            self._dtm50_cache[k] = table
            return table

    def _has_any_table(self, cfg: PieceConfig) -> bool:
        return self._open_wdl(cfg) is not None

    def _route_specialized(self, board: chess.Board
                           ) -> Optional[Tuple[PieceConfig, bool]]:
        """The specialized table `board` belongs in, or None for the caller's own
        material. A 'p' table and its full twin hold the SAME position, so the
        pair is a free preference: take it when on disk, else fall through. A
        rights-bearing position exists only in a table carrying those rights, so
        rights name their material WHETHER OR NOT it is on disk and a miss
        surfaces as a missing table. With both marks, the table carrying both
        comes first, then the rights-only one."""
        if board.clean_castling_rights():
            both = specialized_config_from_board(board, True)
            if both is not None and self._has_any_table(both[0]):
                return both
            return specialized_config_from_board(board, False)
        paired = specialized_config_from_board(board, True)
        if paired is not None and self._has_any_table(paired[0]):
            return paired
        return None

    def _material_name(self, board: chess.Board) -> str:
        """The material the probe looked `board` up under, for error messages:
        standing rights name an 'r' material whether or not it is on disk."""
        routed = self._route_specialized(board)
        cfg = routed[0] if routed is not None else piece_config_from_board(board)[0]
        return cfg.name()

    # --- child construction for the derive / overlay paths ---
    def _make_child(self, parent: chess.Board, move: chess.Move
                    ) -> Tuple[PieceConfig, chess.Board, Optional[int], bool]:
        zeroing = parent.is_zeroing(move)
        child = parent.copy(stack=False)
        child.push(move)  # also sets child.ep_square on a double push

        # A move that keeps a pair or a castling right stays in a 'p' or 'r'
        # material, which the board-derived config below would miss.
        routed = self._route_specialized(child)
        if routed is not None:
            cfg, mirrored = routed
        else:
            cfg, mirrored = piece_config_from_board(child)

        if mirrored:
            child = mirror_for_canonical(child)
        ep = child.ep_square
        child.ep_square = None
        return cfg, child, ep, zeroing

    # --- WDL ---
    def _relax_bound_wdl(self, board: chess.Board, depth: int) -> int:
        """Best class a move out of this material reaches. Captures and
        promotions only: their children live in a sub-table, so this never
        re-enters the frame it is resolving."""
        if depth >= MAX_DERIVE_DEPTH:
            return ILLEGAL
        b = _internal_board(board)
        best = LOSE
        promo_rank = chess.BB_RANK_8 if b.turn == WHITE else chess.BB_RANK_1
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
        """A relaxed frame stores no better than the truth, and stores strictly
        worse only where the bound above reaches it. ILLEGAL stays ILLEGAL."""
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
        color = CPP_WHITE if board.turn == WHITE else CPP_BLACK
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
        color = CPP_WHITE if board.turn == WHITE else CPP_BLACK
        if w.is_dropped[color]:
            if not is_symmetric_material(cfg):
                return self._derive_wdl(board, depth)
            mp = mirror_for_canonical(board)
            mc = CPP_WHITE if mp.turn == WHITE else CPP_BLACK
            return self._raise_by_bound(w, mc, wdl_from_storage(w.read(mc, mp)),
                                        board, depth)
        return self._raise_by_bound(w, color, wdl_from_storage(w.read(color, board)),
                                    board, depth)

    def _derive_wdl(self, board: chess.Board, depth: int) -> int:
        if depth >= MAX_DERIVE_DEPTH:
            return ILLEGAL
        b = _internal_board(board)
        any_legal = have = False
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
            have = True
            if best == WIN:
                return best
        if not any_legal:
            return LOSE if b.is_check() else DRAW
        if not have or skipped.unpin(best):
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
        stored = d.read(color, board if mp is None else mp, wdl)
        if not d.is_relaxed[color] or not is_win_class(wdl):
            return stored
        return self._derive_dtz(board, wdl, depth, stored)

    def _derive_dtz(self, board: chess.Board, wdl: int, depth: int,
                    stored: Optional[_DTZValue] = None) -> Optional[_DTZValue]:
        if depth >= MAX_DERIVE_DEPTH:
            return None
        b = _internal_board(board)
        any_legal = have = False
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
                if stored is not None:
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
            my_wdl = invert_wdl(cw)
            if my_dtz > MAX_NON_CURSED_DTZ:
                if my_wdl == WIN:
                    my_wdl = CURSED_WIN
                elif my_wdl == LOSE:
                    my_wdl = BLESSED_LOSS
            if not have or prefer_new(my_wdl, my_dtz, best_wdl, best_dtz):
                best_wdl, best_dtz, have = my_wdl, my_dtz, True
            if wdl in (WIN, CURSED_WIN) and best_wdl == wdl and best_dtz == 1:
                return _DTZValue(best_dtz, False)
        if stored is not None:
            return None if skipped.unpin(best_wdl) else stored
        if not any_legal:
            return _DTZValue(0, False)
        if not have or skipped.unpin(best_wdl):
            return None
        if best_wdl == DRAW:
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
        """The whole record of a position this table does hold, for a derive to
        minimax over. The child keeps the physical material, so the pack its own
        config names answers -- this file, or the 'p' table that re-indexes an
        opposing pair."""
        if c is None:
            return None
        color, mp, readable = locate_frame(c, cfg, board, wdl)
        if not readable:
            return None
        return c.read_curve(color, board if mp is None else mp, wdl)

    @staticmethod
    def _dtc_move_kind(board: chess.Board, move: chess.Move) -> Tuple[bool, bool]:
        """(conversion, push). A capture or promotion converts; a pawn move that
        does neither spends one of the budget instead."""
        conversion = move.promotion is not None or board.is_capture(move)
        push = not conversion and board.piece_type_at(move.from_square) == chess.PAWN
        return conversion, push

    def _child_dtc_cell(self, cfg_c: PieceConfig, cboard: chess.Board,
                        cep: Optional[int], cw: int, child_rule50: int,
                        depth: int) -> Optional[_DTCCell]:
        """The child's DTC answer with its ep rights folded in. A double push
        leaves the opponent a capture the child's own record cannot express, and
        the overlay is where that is priced, so a child carrying ep rights
        answers through it."""
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
        """Whether an ep capture out of the child wins for the side holding it. A
        capture converts, so it owes no push and lands one ply out -- the
        cheapest answer DTC has. A missing sub-table is a third answer rather
        than a no, though a capture that does win settles it either way.
        `depth` is the child's."""
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
        """DTC by one-ply minimax, for a frame the file does not hold. It never
        leaves this table: pushes and quiet moves keep the material, and a
        conversion is terminal at value 1 under its own WDL. A winner's push
        spends one of the budget and reads one lower; nothing else moves it.

        The class, known before any child is read, says how much of one to
        read: a win takes the cheapest budget any move offers, a loss the
        budget the most stubborn defence forces."""
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
        """Every move prices a loss, so this one walks the children's whole
        records: the budget it settles on is the highest any defence needs, and
        the value there is the longest wait among them, which a child's own
        cheapest budget does not report. Every child is a win for the other
        side, so none needs its class read."""
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
        """A cursed class has no budget to look for, none of them settling it,
        so the unbounded row is the whole of what this derives."""
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
                # Baring the kings takes a capture, and from a blessed loss such
                # a capture would be an outright draw, not a loss.
                continue
            cw = self._probe_wdl_impl(cfg_c, cboard, cep, depth + 1)
            if cw == ILLEGAL:
                skipped.unknown()
                continue
            if winning and cw not in (LOSE, BLESSED_LOSS):
                continue
            # A blessed loss counts only the moves that keep it blessed: into a
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
        """DTM by one-ply minimax for a dropped frame of the DTM table. 50MR-free,
        so a cursed win mates like any other -- which is what folding the pin
        expresses, and why no child needs its clock tracked."""
        if depth >= MAX_DERIVE_DEPTH:
            return None
        pinned = fold_dtm_wdl(wdl)
        b = _internal_board(board)
        any_legal = have = False
        best_wdl, best_dtm = LOSE, 0
        skipped = _SkippedChildren()
        for mv in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, _zeroing = self._make_child(b, mv)
            if cfg_c.is_bare_kings:
                cw, cd = DRAW, 0
            elif cep is not None:
                cr = self._probe_impl(cfg_c, cboard, IGNORE_50MR, cep, depth + 1)
                if cr.status != "ok" or cr.wdl == ILLEGAL:
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
            if not have or prefer_new(my_wdl, my_dtm, best_wdl, best_dtm):
                best_wdl, best_dtm, have = my_wdl, my_dtm, True
            if pinned == WIN and best_wdl == pinned and best_dtm == 1:
                return best_dtm
        if not any_legal:
            return 0
        if not have or skipped.unpin(best_wdl):
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
        """Reconstruct the pack's dropped layer-0 frame with an unbounded,
        one-ply DTM minimax. The result carries DTZ, just as a cell read derives
        it from the flip."""
        if depth >= MAX_DERIVE_DEPTH:
            return _DTM50Result(ILLEGAL, 0)
        pinned = fold_dtm_wdl(wdl)
        b = _internal_board(board)
        any_legal = have = False
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
                if cr.status != "ok" or cr.wdl == ILLEGAL:
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
            if not have or prefer_new(my_wdl, my_dtm, best_wdl, best_dtm):
                best_wdl, best_dtm, have = my_wdl, my_dtm, True
        if not any_legal:
            return dtz.finish(LOSE if b.is_check() else DRAW, 0, False)
        if not have or skipped.unpin(best_wdl):
            return dtz.finish(ILLEGAL, 0, True)
        if best_wdl in (WIN, LOSE):
            return dtz.finish(best_wdl, best_dtm, True)
        return dtz.finish(DRAW, 0, True)

    def _derive_dtm50(self, board: chess.Board, wdl: int, rule50: int,
                      depth: int) -> _DTM50Result:
        """rule50-aware derive: per-child hmc (zeroing resets, quiet increments);
        once >=100, the move is DRAW unless it mates. No DTZ rides along:
        zeroing is clock-free, so _probe_impl prices it once off the layer-0
        probe and drops whatever a layered one finds."""
        if depth >= MAX_DERIVE_DEPTH:
            return _DTM50Result(ILLEGAL, 0)
        pinned = fold_50mr_wdl(wdl)
        b = _internal_board(board)
        any_legal = have = False
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
                if cr.status != "ok" or cr.wdl == ILLEGAL:
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
            if not have or prefer_new(my_wdl, my_dtm, best_wdl, best_dtm):
                best_wdl, best_dtm, have = my_wdl, my_dtm, True
            if pinned == WIN and best_wdl == pinned and best_dtm == 1:
                return _DTM50Result(best_wdl, best_dtm)
        if not any_legal:
            return _DTM50Result(LOSE if b.is_check() else DRAW, 0)
        if not have or skipped.unpin(best_wdl):
            return _DTM50Result(ILLEGAL, 0)
        if best_wdl in (WIN, LOSE):
            return _DTM50Result(best_wdl, best_dtm)
        return _DTM50Result(DRAW, 0)

    # --- combined probe (mirrors probe.cpp's probe_impl, with ep overlay) ---
    def _probe_impl(self, cfg: PieceConfig, board: chess.Board, rule50: int,
                    ep_square: Optional[int], depth: int) -> ProbeResult:
        r = ProbeResult()
        w = self._open_wdl(cfg)
        if w is None:
            return r  # tb_not_found
        r.status = "ok"
        rule50_drawn = (rule50 != IGNORE_50MR and rule50 >= DTM50_HMC_COUNT)
        r.wdl = self._probe_wdl_internal(w, cfg, board, depth)
        if r.wdl == ILLEGAL:
            return r
        if r.wdl == DRAW:
            r.has_dtm = True
            r.has_dtz = True
            if rule50 != IGNORE_50MR:
                r.dtc_wdl = DRAW
                r.has_dtc = True
                r.dtm50_wdl = DRAW
                r.has_dtm50 = True
        else:
            m50 = self._open_dtm50(cfg)
            if m50 is not None:
                d50 = self._probe_dtm50_internal(m50, cfg, board, r.wdl, IGNORE_50MR, depth)
                r.dtm = d50.dtm
                r.has_dtm = (d50.wdl != ILLEGAL)
                r.dtz = d50.dtz
                r.has_dtz = d50.has_dtz
                if not material_has_pawns(cfg) and rule50 != IGNORE_50MR:
                    _fill_pawnless_dtc_from_dtz(r, rule50)
                if rule50_drawn:
                    # Mate outruns the claim, and a LOSE at flat 0 is one; an
                    # unpriced distance tells them apart from neither.
                    if r.has_dtm or r.wdl != LOSE:
                        r.dtm50_wdl = LOSE if (r.wdl == LOSE and r.dtm == 0) else DRAW
                        r.has_dtm50 = True
                elif rule50 != IGNORE_50MR:
                    # Cursed/blessed are DRAW at every layer; the clock is never read.
                    if fold_50mr_wdl(r.wdl) == DRAW:
                        r.dtm50_wdl = DRAW
                        r.has_dtm50 = True
                    elif r.has_dtm and dtm50_layer_pinned_by_dtm(r.wdl, r.dtm, rule50):
                        r.dtm50_wdl = r.wdl  # plain W/L, so the DTM50 fold is the identity
                        r.dtm50 = r.dtm
                        r.has_dtm50 = True
                    elif layer_busted_by_dtz(r.wdl, r.dtz, rule50):
                        r.dtm50_wdl = DRAW
                        r.has_dtm50 = True
                    else:
                        rr = self._probe_dtm50_internal(m50, cfg, board, r.wdl, rule50, depth)
                        r.dtm50_wdl = rr.wdl
                        r.dtm50 = rr.dtm
                        r.has_dtm50 = (rr.wdl != ILLEGAL)
            else:
                m = self._open_dtm(cfg)
                if m is not None:
                    dtm = self._probe_dtm_internal(m, cfg, board, r.wdl, depth)
                    if dtm is not None:
                        r.dtm = dtm
                        r.has_dtm = True
        # DTC next: its pack answers both metrics, the budget the caller's
        # clock picks and the unbounded row that is the DTZ table it embeds.
        # A cursed class or an outrun clock leaves no budget to pick, which
        # the read reports by pricing nothing, and a DRAW is answered above
        # without opening anything.
        if r.wdl != DRAW and not r.has_dtc and material_has_pawns(cfg):
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
                    # A record carries that row and so does the derive, so a
                    # decisive class always has one.
                    r.dtz = cell.dtz
                    r.dtz_rounded = cell.dtz_rounded
                    r.has_dtz = True
        # What the packs above left: the DTM50 one stops at the cursed band,
        # and a DTC one answers only the materials it is built for.
        if not r.has_dtz:
            d = self._open_dtz(cfg)
            if d is not None:
                dtz = self._probe_dtz_internal(d, cfg, board, r.wdl, depth)
                if dtz is not None:
                    r.dtz = dtz.dtz
                    r.dtz_rounded = dtz.rounded
                    r.has_dtz = True
        # A standalone DTZ is the last pack that can supply the direct
        # pawnless answer. DTM50 already took this path as soon as its
        # embedded DTZ was read above.
        if not r.has_dtc and not material_has_pawns(cfg) and rule50 != IGNORE_50MR:
            _fill_pawnless_dtc_from_dtz(r, rule50)

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
        # DTC compares on its own class, not the clock-independent one: a base
        # this clock has drawn must lose to an ep conversion that still wins.
        best_dtc_wdl = r.dtc_wdl if r.has_dtc else r.wdl
        best_dtc_order = r.dtc_order if r.has_dtc else 0
        best_dtc = r.dtc if r.has_dtc else 0
        any_ep = False
        # An ep capture prices DTC and DTM50 only on a live clock: unclocked they
        # do not exist, even where every move is an ep capture, and a drawn clock
        # has the claim already.
        live_clock = rule50 != IGNORE_50MR and not rule50_drawn
        if rule50_drawn:
            # Even an EP conversion costs a ply; the claim is already available.
            best.dtc_wdl = DRAW
            best.has_dtc = True
            best.dtm50_wdl = DRAW
            best.has_dtm50 = True
        for mv in eps:
            cfg_c, cboard, _cep, _ = self._make_child(bcopy, mv)
            if cfg_c.is_bare_kings:
                cr = ProbeResult()
                cr.status = "ok"
                cr.wdl = DRAW
                cr.has_dtz = best.has_dtz
                cr.has_dtm = best.has_dtm
                cr.dtm50_wdl = DRAW
                cr.has_dtm50 = best.has_dtm50
            else:
                cr = self._probe_impl(cfg_c, cboard, 0 if live_clock else IGNORE_50MR,
                                     None, depth + 1)  # ep is zeroing
            if cr.status != "ok" or cr.wdl == ILLEGAL:
                return ProbeResult()
            my_wdl = invert_wdl(cr.wdl)
            if not has_non_ep_move and not any_ep:
                best.status = "ok"
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
            # An ep capture zeroes, so its dtz is 1 whatever the child
            # holds. The base value has to be known only to break a tie in class
            # -- outranked, it does not enter, which is how a cursed base the
            # pack cannot pin still reports a dtz once ep lifts it.
            ep_outranks_dtz = wdl_rank(my_wdl) > wdl_rank(best_dtz_wdl)
            if ep_outranks_dtz or (best.has_dtz
                                   and prefer_new(my_wdl, 1, best_dtz_wdl, best_dtz)):
                best_dtz_wdl, best_dtz = my_wdl, 1
                best.dtz = 0 if my_wdl == DRAW else 1
                best.dtz_rounded = False
                best.has_dtz = True
            # The ep capture is legal, so a DTM that ignored it would be wrong:
            # a child that cannot supply one leaves this position undetermined.
            if not cr.has_dtm:
                best.has_dtm = False
            elif best.has_dtm:
                my_dtm_wdl = fold_dtm_wdl(my_wdl)
                my_dtm = 1 + cr.dtm
                if prefer_new(my_dtm_wdl, my_dtm, best_dtm_wdl, best_dtm):
                    best_dtm_wdl, best_dtm = my_dtm_wdl, my_dtm
                    best.dtm = my_dtm if my_dtm_wdl in (WIN, LOSE) else 0
            if live_clock:
                # An ep capture is a conversion: it owes no push and lands one ply
                # out, so (0, 1) needs no table to know, and the base value enters
                # only to break a tie in class. A conversion is terminal to DTC, so
                # its class is the child's WDL folded to what a layer holds, as the
                # generator classifies one.
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
        return best

    # --- public API ---
    def probe(self, board: chess.Board, rule50: Optional[int] = None) -> ProbeResult:
        """Full probe of `board`. `rule50` (the halfmove clock, by default the
        board's own) selects the DTM50 layer and the DTC budget. Returns a
        :class:`ProbeResult`; its ``status`` is ``"ok"`` or
        ``"tb_not_found"``. A board with castling rights is answered only by an
        'r' table carrying those rights.

        Safe to call concurrently. Every probe method registers as a reader for
        its whole walk; the registration only ever blocks a concurrent
        :meth:`close`."""
        hmc = board.halfmove_clock if rule50 is None else rule50
        with self._reading():
            cfg, cboard, ep = self._root(board)
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

    def _root(self, board: chess.Board) -> Tuple[PieceConfig, chess.Board, Optional[int]]:
        """The table and canonical board a probe of `board` starts from, with
        the en-passant square split off: ep travels as an overlay."""
        routed = self._route_specialized(board)
        if routed is not None:
            cfg, mirrored = routed
        else:
            cfg, mirrored = piece_config_from_board(board)
        cboard = mirror_for_canonical(board) if mirrored else board.copy(stack=False)
        ep = cboard.ep_square
        cboard.ep_square = None
        return cfg, cboard, ep

    def _require(self, board: chess.Board) -> ProbeResult:
        # DTZ and DTM do not depend on the clock, so their callers take the
        # unbounded read.
        r = self.probe(board, IGNORE_50MR)
        if r.status == "tb_not_found":
            raise MissingTableError(
                f"no chesstb table for {self._material_name(board)}")
        if r.wdl == ILLEGAL:
            # Tables exist for the material but cannot resolve this cell: a
            # dropped color is rebuilt by one-ply minimax, and that needs every
            # capture/promotion sub-table the walk reaches.
            raise MissingTableError(
                f"chesstb tables for {self._material_name(board)} "
                "cannot resolve this position")
        return r

    def probe_wdl(self, board: chess.Board) -> int:
        """5-class WDL as a signed int: +2 win, +1 cursed win, 0 draw,
        -1 blessed loss, -2 loss. Raises :class:`MissingTableError` if no table
        for the position."""
        with self._reading():
            cfg, cboard, ep = self._root(board)
            # The WDL probe alone: no distance table is read, and an unresolved
            # en-passant child still answers a WIN.
            w = self._probe_wdl_impl(cfg, cboard, ep, 0)
            if w == ILLEGAL:
                if not self._has_any_table(cfg):
                    raise MissingTableError(
                        f"no chesstb table for {self._material_name(board)}")
                raise MissingTableError(
                    f"chesstb tables for {self._material_name(board)} "
                    "cannot resolve this position")
            return _WDL_SIGNED[w]

    def get_wdl(self, board: chess.Board, default: Any = None) -> Any:
        try:
            return self.probe_wdl(board)
        except MissingTableError:
            return default

    def probe_dtz(self, board: chess.Board) -> int:
        """Signed distance to zeroing: +N = side to move reaches a capture,
        promotion or pawn move toward a win in N plies, -N toward a loss, 0 =
        draw. Measures what :meth:`chess.syzygy.Tablebase.probe_dtz` does but is
        not interchangeable: syzygy bases its cursed band off 100, so a
        magnitude carries the class; here the class stays in WDL.
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
        """Distance to conversion at the board's halfmove clock (or `rule50`),
        pricing pawn pushes separately from waiting. Returns
        ``(pushes_owed, signed_plies)``: the pushes the winning side still owes
        before a capture or promotion, and the signed plies to the next zeroing
        move on the line that owes them.

        Pushes are the primary key, so a tight clock forces the trade the other
        way; where no budget fits it the answer is a 50MR draw, ``(0, 0)``.
        Pawnless materials carry no pack: the answer is DTZ's own number at
        nothing owed."""
        r = self.probe(board, rule50)
        if r.status == "tb_not_found":
            cfg, _ = piece_config_from_board(board)
            raise MissingTableError(f"no chesstb table for {cfg.name()}")
        if not r.has_dtc:
            raise MissingTableError("DTC unavailable")
        return (r.dtc_order, _signed(r.dtc, r.dtc_wdl))

    def probe_dtm(self, board: chess.Board) -> int:
        """Signed distance-to-mate, ignoring the 50-move rule."""
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
        """Signed 50-move-rule-aware distance to mate at the board's halfmove
        clock (or `rule50` if given), ``0`` where that clock has taken the win;
        cursed/blessed both collapse to draw under the 50-move rule."""
        cfg, _ = piece_config_from_board(board)
        r = self.probe(board, rule50)
        if r.status == "tb_not_found":
            raise MissingTableError(f"no chesstb table for {cfg.name()}")
        if not r.has_dtm50:
            raise MissingTableError("DTM50 unavailable")
        return _signed(r.dtm50, r.dtm50_wdl)


def open_tablebase(directory: str, *,
                   block_cache_bytes: int = DEFAULT_BLOCK_CACHE_BYTES) -> Tablebase:
    """Open a directory tree of chesstb tables (``wdl/``, ``dtz/``, ``dtc/``,
    ``dtm/``, ``dtm50/`` subdirectories, or table files directly under
    `directory`).

    Decoded blocks are kept in an LRU cache bounded by `block_cache_bytes`."""
    return Tablebase(directory, block_cache_bytes=block_cache_bytes)
