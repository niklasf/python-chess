"""Pure-Python prober for the *chesstb* endgame tablebase format
(WDL ``.lzw`` / DTC ``.lzdtc`` / DTM50 ``.lzdtm50``).

Upstream: https://github.com/noobpwnftw/chesstb

This is a faithful re-implementation of the C++ probe library in
``src/probe`` and is validated bit-for-bit against ``tests/probe_fen``.

Square numbering matches python-chess exactly (a1=0 .. h8=63, rank-major),
so positions are taken as :class:`chess.Board` instances directly.

Design mirrors :mod:`chess.syzygy`: a :class:`Tablebase` opens a directory of
table files and answers WDL / DTZ-equivalent (DTC) / DTM / DTM50 queries.
"""
from __future__ import annotations

import collections
import lzma
import os
import struct
import threading
from typing import Any, Dict, List, Optional, Tuple

import chess

__all__ = ["Tablebase", "ProbeResult", "MissingTableError", "open_tablebase"]

# ---------------------------------------------------------------------------
# Chess primitive constants, mirroring src/chess/chess.h.
# python-chess: WHITE=True, BLACK=False; piece types KING..PAWN = 6..1? No:
#   chess.PAWN=1, KNIGHT=2, BISHOP=3, ROOK=4, QUEEN=5, KING=6.
# The C++ enum differs (KING=1..PAWN=6) but we never serialize C++ piece ints;
# we only need: square transforms, the legal-square set per piece, the material
# key, and class ordering. Those we encode against the C++ semantics below.
# ---------------------------------------------------------------------------

WHITE = chess.WHITE
BLACK = chess.BLACK

# Piece "type" codes as used by the C++ side (KING=1,QUEEN=2,ROOK=3,BISHOP=4,
# KNIGHT=5,PAWN=6) and Piece = (color<<3)+type, color WHITE=0 BLACK=1.
KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN = 1, 2, 3, 4, 5, 6

# map C++ piece-type code -> python-chess piece type
_CPP_TO_PC = {KING: chess.KING, QUEEN: chess.QUEEN, ROOK: chess.ROOK,
              BISHOP: chess.BISHOP, KNIGHT: chess.KNIGHT, PAWN: chess.PAWN}
_PC_TO_CPP = {v: k for k, v in _CPP_TO_PC.items()}

# C++ Color: WHITE=0, BLACK=1.  python-chess: WHITE=True(1), BLACK=False(0).
# We use a dedicated 0/1 color int matching C++ where indexing matters.
CPP_WHITE, CPP_BLACK = 0, 1


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
    # transpose along a1-h8: (file f, rank r) -> (file r, rank f)
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

SYM_FILE_MIRROR = 0
SYM_DIHEDRAL_8 = 1

# Anchor square sets for king canonicalization.
_ANCHOR_FILE_MIRROR = [sq_make(r, f) for r in range(8) for f in range(4)]  # files a-d
_ANCHOR_TRIANGLE = [sq_make(r, f) for r in range(4) for f in range(r, 4)]  # a1,b1..d1,b2..

# ---------------------------------------------------------------------------
# Binomial table C(n, k) for n<=64, k<=7.  C++ BINOMIAL[k][n] indexing.
# ---------------------------------------------------------------------------
_BINOM = [[0] * 8 for _ in range(65)]
for _k in range(65):
    _BINOM[_k][0] = 1
    for _n in range(1, 8):
        _BINOM[_k][_n] = 0 if _n > _k else _BINOM[_k - 1][_n - 1] + _BINOM[_k - 1][_n]


def binom(n: int, k: int) -> int:
    if k < 0 or k > 7 or n < 0 or n > 64:
        return 0
    return _BINOM[n][k]


# ---------------------------------------------------------------------------
# Material_Key (src/chess/chess.h): base-9 mixed radix, indexed by C++ Piece.
#   WHITE_QUEEN..WHITE_PAWN -> 9^4..9^0 ; BLACK_QUEEN..BLACK_PAWN -> 9^9..9^5.
# ---------------------------------------------------------------------------
_MAT_WEIGHT = {  # (cpp_color, type) -> weight
    (CPP_WHITE, QUEEN): 9 ** 4, (CPP_WHITE, ROOK): 9 ** 3, (CPP_WHITE, BISHOP): 9 ** 2,
    (CPP_WHITE, KNIGHT): 9 ** 1, (CPP_WHITE, PAWN): 9 ** 0, (CPP_WHITE, KING): 0,
    (CPP_BLACK, QUEEN): 9 ** 9, (CPP_BLACK, ROOK): 9 ** 8, (CPP_BLACK, BISHOP): 9 ** 7,
    (CPP_BLACK, KNIGHT): 9 ** 6, (CPP_BLACK, PAWN): 9 ** 5, (CPP_BLACK, KING): 0,
}


def material_key_of(pieces: List[Tuple[int, int]]) -> int:
    """pieces: list of (cpp_color, type)."""
    return sum(_MAT_WEIGHT[(c, t)] for c, t in pieces)


# ---------------------------------------------------------------------------
# Piece_Config: canonical (strength-ordered) piece list, white = stronger side.
# ---------------------------------------------------------------------------
_STRENGTH = {QUEEN: 900, ROOK: 500, BISHOP: 330, KNIGHT: 320, PAWN: 100, KING: 0}
# within-side sort order: K,Q,R,B,N,P (descending strength, kings first)
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
    FREE pieces. `has_pair` marks a frozen opposing pawn pair (lowercase 'p'):
    one white + one black pawn locked on a file, indexed jointly and excluded
    from `pieces` (mirrors src/chess/piece_config.h)."""

    def __init__(self, pieces: List[Tuple[int, int]], has_pair: bool = False):
        # Determine side ordering by total strength; stronger side -> WHITE.
        # Input may be in any orientation; we canonicalize. The pair is
        # strength-neutral (one pawn each side), so it never affects the swap.
        ws = sum(_STRENGTH[t] for c, t in pieces if c == CPP_WHITE)
        bs = sum(_STRENGTH[t] for c, t in pieces if c == CPP_BLACK)
        swap = bs > ws
        if bs == ws:
            swap = _composition_key(pieces, CPP_BLACK) > _composition_key(pieces, CPP_WHITE)
        if swap:
            pieces = [(CPP_BLACK if c == CPP_WHITE else CPP_WHITE, t) for c, t in pieces]
        # sort: white side first then black; within side by type order.
        pieces = sorted(pieces, key=lambda ct: (ct[0], _TYPE_ORDER[ct[1]]))
        self.pieces = pieces
        self.has_pair = has_pair
        self.base_key = material_key_of(pieces)
        self.mirr_key = material_key_of(
            [(CPP_BLACK if c == CPP_WHITE else CPP_WHITE, t) for c, t in pieces])

    @property
    def min_key(self) -> int:
        # Pair-stripped 30-bit value, as serialized in the on-disk header.
        return min(self.base_key, self.mirr_key)

    @property
    def cache_key(self) -> int:
        # In-memory key distinguishing a 'p'-material from its free-pieces twin
        # (which share min_key). Not for disk; canonical min-keys are < 2^31.
        return self.min_key | (0x80000000 if self.has_pair else 0)

    def name(self) -> str:
        # The pair contributes one pawn to each side; emit a 'p' at the end of
        # the white side (before the 2nd king) and another at the very end, e.g.
        # "KQpKp" -- so a board-derived pair config resolves the right filename.
        letters = {KING: "K", QUEEN: "Q", ROOK: "R", BISHOP: "B", KNIGHT: "N", PAWN: "P"}
        s = []
        seen_white_king = False
        for c, t in self.pieces:
            if t == KING:
                if seen_white_king and self.has_pair:
                    s.append("p")
                seen_white_king = True
            s.append(letters[t])
        if self.has_pair:
            s.append("p")
        return "".join(s)

    @property
    def num_pieces(self) -> int:
        return len(self.pieces)


def piece_config_from_board(board: chess.Board) -> Tuple["PieceConfig", bool]:
    """Return (canonical PieceConfig, mirrored?) for the board's material.

    mirrored is True when the literal material had to swap colors to match the
    canonical base orientation (white = stronger side).
    """
    pieces = []
    for sq in range(64):
        p = board.piece_at(sq)
        if p:
            pieces.append((cpp_color(p.color), _PC_TO_CPP[p.piece_type]))
    cfg = PieceConfig(pieces)
    literal = material_key_of(pieces)
    mirrored = literal != cfg.base_key
    return cfg, mirrored


def pair_config_from_board(board: chess.Board) -> Optional[Tuple["PieceConfig", bool]]:
    """If `board` has an opposing pawn pair, return (frozen-pair PieceConfig,
    mirrored?); else None. The pair's two pawns are excluded from the config and
    flagged via has_pair, mirroring src/probe/probe.cpp pair_config_from_position.
    Used to prefer a 'p' table over the full material when one is on disk."""
    wp = list(board.pieces(chess.PAWN, WHITE))
    bp = list(board.pieces(chess.PAWN, BLACK))
    found = PairGroup.find_canonical(wp, bp)
    if found is None:
        return None
    pw, pb = found
    pieces = []
    for sq in range(64):
        if sq == pw or sq == pb:
            continue
        p = board.piece_at(sq)
        if p:
            pieces.append((cpp_color(p.color), _PC_TO_CPP[p.piece_type]))
    cfg = PieceConfig(pieces, has_pair=True)
    mirrored = material_key_of(pieces) != cfg.base_key
    return cfg, mirrored


# ---------------------------------------------------------------------------
# Piece_Class enum (src/chess/piece_config.h)
# ---------------------------------------------------------------------------
(BLACK_KINGS, BLACK_KNIGHTS, BLACK_BISHOPS, BLACK_ROOKS, BLACK_QUEENS, BLACK_PAWNS,
 WHITE_KINGS, WHITE_KNIGHTS, WHITE_BISHOPS, WHITE_ROOKS, WHITE_QUEENS, WHITE_PAWNS) = range(12)
PIECE_CLASS_NB = 12

# Piece_Type_Class: KINGS=0,KNIGHTS=1,BISHOPS=2,ROOKS=3,QUEENS=4,PAWNS=5
_PTCLASS = {KING: 0, KNIGHT: 1, BISHOP: 2, ROOK: 3, QUEEN: 4, PAWN: 5}


def make_piece_class(cpp_col: int, ptype: int) -> int:
    base = WHITE_KINGS if cpp_col == CPP_WHITE else BLACK_KINGS
    return base + _PTCLASS[ptype]


def class_to_piece(pcl: int) -> Tuple[int, int]:
    """piece class -> (cpp_color, ptype)."""
    cpp_col = CPP_WHITE if pcl >= WHITE_KINGS else CPP_BLACK
    off = pcl - (WHITE_KINGS if cpp_col == CPP_WHITE else BLACK_KINGS)
    inv = {0: KING, 1: KNIGHT, 2: BISHOP, 3: ROOK, 4: QUEEN, 5: PAWN}
    return cpp_col, inv[off]


# ---------------------------------------------------------------------------
# Piece_Group: combinatorial ranking of `count` identical pieces over the
# legal squares of their type.
# ---------------------------------------------------------------------------
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
        # squares: the placement (any order); rank a sorted combination.
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


# ---------------------------------------------------------------------------
# King_Slice_Manager: built once per symmetry group.
# ---------------------------------------------------------------------------
def _king_attacks(sq: int) -> List[int]:
    f, r = sq_file(sq), sq_rank(sq)
    out = []
    for df in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if df == 0 and dr == 0:
                continue
            nf, nr = f + df, r + dr
            if 0 <= nf < 8 and 0 <= nr < 8:
                out.append(sq_make(nr, nf))
    return out


def _kings_adjacent(a: int, b: int) -> bool:
    return b in _king_attacks(a)


def _sq_on_main_diag(sq: int) -> bool:
    return sq_file(sq) == sq_rank(sq)


class KingSliceManager:
    def __init__(self, sym: int):
        self.sym = sym
        n_trans = 8 if sym == SYM_DIHEDRAL_8 else 2
        anchors = _ANCHOR_TRIANGLE if sym == SYM_DIHEDRAL_8 else _ANCHOR_FILE_MIRROR
        anchor_set = set(anchors)
        SLICE_NONE = -1
        # pair_lookup[wk*64+bk] = [slice_id, transform, has_diag_stabilizer]
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


_KSM_CACHE: Dict[int, KingSliceManager] = {}


def king_slice_mgr(sym: int) -> KingSliceManager:
    if sym not in _KSM_CACHE:
        _KSM_CACHE[sym] = KingSliceManager(sym)
    return _KSM_CACHE[sym]


# ---------------------------------------------------------------------------
# Pawn_Slice_Manager
# ---------------------------------------------------------------------------
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
        if not self.has_pawns:
            self.num_slices = 1
            self.pair_table_size = 1
            self.white_table_size = 1
            self.black_table_size = 1
            self.storage_by_cartesian = [0]
            self.cartesian_by_storage = [0]
            return
        self.pair_table_size = pair_group.table_size if pair_group else 1
        self.white_table_size = white_group.table_size if white_group else 1
        self.black_table_size = black_group.table_size if black_group else 1
        # Mixed radix: cart = pair_idx + w_idx*pair_size + b_idx*pair_size*white_size.
        n_cart = self.pair_table_size * self.white_table_size * self.black_table_size
        self.storage_by_cartesian = [-1] * n_cart
        self.cartesian_by_storage = []
        for cart in range(n_cart):
            pair_idx = cart % self.pair_table_size
            rem = cart // self.pair_table_size
            w_idx = rem % self.white_table_size
            b_idx = rem // self.white_table_size
            sqs: List[int] = []
            if pair_group:
                sqs.append(pair_group.white_square(pair_idx))
                sqs.append(pair_group.black_square(pair_idx))
            if white_group:
                sqs.extend(white_group.squares(w_idx))
            if black_group:
                sqs.extend(black_group.squares(b_idx))
            if len(set(sqs)) != len(sqs):
                continue
            if pair_group:
                pair_w = pair_group.white_square(pair_idx)
                pair_b = pair_group.black_square(pair_idx)
                wsqs = [pair_w]
                bsqs = [pair_b]
                if white_group:
                    wsqs.extend(white_group.squares(w_idx))
                if black_group:
                    bsqs.extend(black_group.squares(b_idx))
                cw, cb = PairGroup.canonical_pair(wsqs, bsqs)
                if cw != pair_w or cb != pair_b:
                    continue
            self.storage_by_cartesian[cart] = len(self.cartesian_by_storage)
            self.cartesian_by_storage.append(cart)
        self.num_slices = len(self.cartesian_by_storage)

    def compose(self, pair_idx: int, w_idx: int, b_idx: int) -> int:
        if not self.has_pawns:
            return 0
        cart = (pair_idx
                + w_idx * self.pair_table_size
                + b_idx * self.pair_table_size * self.white_table_size)
        return self.storage_by_cartesian[cart]

    def lookup_from_squares(self, pair_w: int, pair_b: int,
                            white_pawn_sqs: List[int], black_pawn_sqs: List[int]) -> int:
        if not self.has_pawns:
            return 0
        pair_idx = self.pair_group.index_of(pair_w, pair_b) if self.pair_group else 0
        w_idx = self.white_group.compound_index(white_pawn_sqs) if self.white_group else 0
        b_idx = self.black_group.compound_index(black_pawn_sqs) if self.black_group else 0
        return self.compose(pair_idx, w_idx, b_idx)


# ---------------------------------------------------------------------------
# Index permutation (src/chess/index_permutation.h)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Position_Index_Config
# ---------------------------------------------------------------------------
class PositionIndexConfig:
    def __init__(self, cfg: PieceConfig):
        self.cfg = cfg
        counts: Dict[Tuple[int, int], int] = {}
        for c, t in cfg.pieces:
            counts[(c, t)] = counts.get((c, t), 0) + 1
        # A frozen pair is two pawns on the board, so it breaks symmetry to
        # file-mirror like any pawn even with no free pawns.
        has_pawns = (counts.get((CPP_WHITE, PAWN), 0) > 0
                     or counts.get((CPP_BLACK, PAWN), 0) > 0 or cfg.has_pair)
        self.sym = SYM_FILE_MIRROR if has_pawns else SYM_DIHEDRAL_8
        self.ksm = king_slice_mgr(self.sym)

        self.groups: Dict[int, PieceGroup] = {}
        # make groups for Q,R,B,N,P per color (NOT kings)
        for c in (CPP_WHITE, CPP_BLACK):
            for t in (QUEEN, ROOK, BISHOP, KNIGHT, PAWN):
                n = counts.get((c, t), 0)
                if n == 0:
                    continue
                pcl = make_piece_class(c, t)
                self.groups[pcl] = PieceGroup(t, n)

        self.pair_group = PairGroup() if cfg.has_pair else None
        if has_pawns:
            self.psm = PawnSliceManager(self.pair_group,
                                        self.groups.get(WHITE_PAWNS), self.groups.get(BLACK_PAWNS))
        else:
            self.psm = PawnSliceManager(None, None, None)
        self.num_pawn_slices = self.psm.num_slices

        # populated non-pawn classes in ascending class-id order; native weights.
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
        """Return (order, radix) lists per index permutation."""
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
        for c in self.populated:
            cc, tt = class_to_piece(c)
            color = WHITE if cc == CPP_WHITE else BLACK
            pl[c] = list(board.pieces(_CPP_TO_PC[tt], color))
        # Collect pawns when a free-pawn class is populated OR a frozen pair adds
        # pawns with no free-pawn class (e.g. KpKp). The pair members are folded
        # in here and split out by find_canonical at index time.
        for c in (WHITE_PAWNS, BLACK_PAWNS):
            if c in self.groups or self.pair_group is not None:
                color = WHITE if c == WHITE_PAWNS else BLACK
                pl[c] = list(board.pieces(chess.PAWN, color))
        return pl

    def _canonicalize(self, pl: Dict[int, List[int]]) -> bool:
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
        ksid = self.ksm.lookup(wk, bk)[0]
        if ksid == -1:
            return None
        pawn_slice = 0
        if self.psm.has_pawns:
            w_pl, b_pl = pl[WHITE_PAWNS], pl[BLACK_PAWNS]
            if self.pair_group is not None:
                # Identify the pair (canonical opposing pair); the rest are free.
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


_INDEX_CFG_CACHE: Dict[int, PositionIndexConfig] = {}


def position_index_config(cfg: PieceConfig) -> PositionIndexConfig:
    k = cfg.cache_key
    if k not in _INDEX_CFG_CACHE:
        _INDEX_CFG_CACHE[k] = PositionIndexConfig(cfg)
    return _INDEX_CFG_CACHE[k]


# ===========================================================================
# On-disk file framing (src/util/memory.h, mono_uint_vec.h, egtb_format.h)
# ===========================================================================

WDL_MAGIC, DTC_MAGIC, DTM_MAGIC, DTM50_MAGIC = 0x9bd1e3a6, 0x2ec8b161, 0xab57c134, 0xab57c150
SINGULAR_FLAG = 0x80
DROPPED_FLAG = 0x40
DTM50_HMC_COUNT = 100
DTM50_PACK_LAYERS = 101
IGNORE_50MR = -1  # sentinel (C++ uses ~0u)

# WDL_Entry
LOSE, BLESSED_LOSS, DRAW, CURSED_WIN, WIN, ILLEGAL = 0, 1, 2, 3, 4, 7
# WDL_Stored adds BOUNDARY_LOSS=5, BOUNDARY_WIN=6.


def wdl_from_storage(s: int) -> int:
    if s == 6:   # BOUNDARY_WIN
        return WIN
    if s == 5:   # BOUNDARY_LOSS
        return LOSE
    return s


class _Serial:
    """Sequential little-endian reader over a bytes/memoryview, mirroring
    Serial_Memory_Reader (offset tracking + align relative to begin)."""

    def __init__(self, data: memoryview):
        self.d = data
        self.pos = 0

    def u8(self) -> int:
        v = self.d[self.pos]
        self.pos += 1
        return v

    def u16(self) -> int:
        v = int(struct.unpack_from("<H", self.d, self.pos)[0])
        self.pos += 2
        return v

    def u32(self) -> int:
        v = int(struct.unpack_from("<I", self.d, self.pos)[0])
        self.pos += 4
        return v

    def u64(self) -> int:
        v = int(struct.unpack_from("<Q", self.d, self.pos)[0])
        self.pos += 8
        return v

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


class MonoUintVec:
    """Block-sampled delta coder for a monotone uint64 sequence."""

    def __init__(self, blob: memoryview, num_values: int, log2_bu: int,
                 sample_width: int, offset_width: int):
        self.blob = blob
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
        byte = base_off + (bitpos >> 3)
        bit = bitpos & 7
        # read up to 16 bytes to cover width<=64 with bit offset
        lo = int.from_bytes(self.blob[byte:byte + 8], "little")
        v = lo >> bit
        if bit + width > 64:
            hi = int.from_bytes(self.blob[byte + 8:byte + 16], "little")
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
    def __init__(self, data: memoryview, size: int, width: int):
        self.data = data
        self.size = size
        self.width = width

    @staticmethod
    def on_disk_bytes(size: int, width: int) -> int:
        return _ceil_div(size * width, 8)

    def get(self, i: int) -> int:
        if self.width == 0:
            return 0
        bitpos = i * self.width
        byte = bitpos >> 3
        bit = bitpos & 7
        lo = int.from_bytes(self.data[byte:byte + 8], "little")
        v = lo >> bit
        if bit + self.width > 64:
            hi = int.from_bytes(self.data[byte + 8:byte + 16], "little")
            v |= hi << (64 - bit)
        mask = (1 << self.width) - 1
        return v & mask


# --- pure-Python LZ4 block decompression with optional dictionary prefix ---

def lz4_decompress_block(src: memoryview, expected_size: int, dict_bytes: bytes = b"") -> bytes:
    """Decompress an LZ4 *block* (not frame). A dictionary, if given, logically
    precedes the output; match offsets may reference into it. Mirrors
    LZ4_decompress_safe[_usingDict]."""
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
        # overlapping copy, byte by byte
        for j in range(match_len):
            out.append(out[start + j])
    result = bytes(out[base:])
    if len(result) != expected_size:
        raise ValueError(f"LZ4 size mismatch: got {len(result)} expected {expected_size}")
    return result


# ===========================================================================
# Decoded-block cache
# ===========================================================================

#: Default soft budget (bytes) for decoded blocks held resident across all
#: tables of a :class:`Tablebase`. The cache evicts least-recently-used blocks
#: once the budget is exceeded, so memory is reclaimed automatically without an
#: explicit :meth:`Tablebase.close`.
DEFAULT_BLOCK_CACHE_BYTES = 64 * 1024 * 1024


class _BlockCache:
    """LRU reclaimer shared by every table of a :class:`Tablebase`.

    Decoding a block is expensive, so each per-color object keeps its own
    ``_blocks`` dict of decoded blocks. This cache tracks those entries in a
    global least-recently-used order keyed by ``(per_color, block_id)`` and,
    once the resident byte estimate exceeds ``max_bytes``, evicts the oldest
    blocks by dropping them from their owning ``_blocks`` dict. Sizes are
    approximate; the budget is a soft target.
    """

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        self.cur_bytes = 0
        # (per_color, block_id) -> approximate size in bytes, ordered LRU-first.
        self._lru: "collections.OrderedDict[Tuple[Any, int], int]" = collections.OrderedDict()
        self._lock = threading.Lock()

    def touch(self, pc: Any, block_id: int) -> None:
        """Mark an already-cached block as most-recently-used (a cache hit)."""
        key = (pc, block_id)
        with self._lock:
            if key in self._lru:
                self._lru.move_to_end(key)

    def record(self, pc: Any, block_id: int, size: int) -> None:
        """Register a freshly decoded block and evict until within budget."""
        key = (pc, block_id)
        with self._lock:
            old = self._lru.pop(key, None)
            if old is not None:
                self.cur_bytes -= old
            self._lru[key] = size
            self.cur_bytes += size
            # Keep the just-added block (it is at the end); never empty fully.
            while self.cur_bytes > self.max_bytes and len(self._lru) > 1:
                (ev_pc, ev_id), ev_size = self._lru.popitem(last=False)
                self.cur_bytes -= ev_size
                ev_pc._blocks.pop(ev_id, None)

    def clear(self) -> None:
        """Drop every tracked block and reset the budget."""
        with self._lock:
            for pc, block_id in self._lru:
                pc._blocks.pop(block_id, None)
            self._lru.clear()
            self.cur_bytes = 0


# ===========================================================================
# WDL table file
# ===========================================================================

def egtb_table_colors(table_num: int) -> List[int]:
    # WHITE always; BLACK only when table_num == 2.  C++ Color WHITE=0,BLACK=1.
    return [CPP_WHITE] + ([CPP_BLACK] if table_num == 2 else [])


class _WDLPerColor:
    __slots__ = ("order", "radix", "block_size", "tail_size", "block_cnt",
                 "data_size", "offsets", "compressed", "dict", "single_val",
                 "dict_size", "_blocks")
    order: List[int]
    radix: List[int]
    block_size: int
    tail_size: int
    block_cnt: int
    data_size: int
    offsets: MonoUintVec
    compressed: memoryview
    dict: bytes
    single_val: int
    dict_size: int
    _blocks: Dict[int, bytes]

    def __init__(self) -> None:
        self.single_val = DRAW
        self.dict = b""
        self.dict_size = 0
        self._blocks = {}


class WDLFile:
    EXT = ".lzw"
    MAGIC = WDL_MAGIC

    def __init__(self, cfg: PieceConfig, path: str, cache: Optional[_BlockCache] = None):
        self.cfg = cfg
        self.index_cfg = position_index_config(cfg)
        self.cache = cache if cache is not None else _BlockCache(DEFAULT_BLOCK_CACHE_BYTES)
        self.is_singular = [False, False]
        self.is_dropped = [False, False]
        self.per_color: List[Optional[_WDLPerColor]] = [None, None]
        self._load(path)

    def _load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = f.read()
        if (len(data) & 63) != 8:
            raise ValueError(f"Invalid WDL file size {path}")
        r = _Serial(memoryview(data))
        self._data = data
        magic = r.u32()
        if magic != self.MAGIC:
            raise ValueError(f"Invalid WDL magic {path}")
        key_and_table = r.u32()
        key = key_and_table >> 2
        if key != self.cfg.min_key:
            raise ValueError(f"Wrong material key in WDL {path}: {key} != {self.cfg.min_key}")
        table_num = key_and_table & 3
        colors = egtb_table_colors(table_num)
        for c in colors:
            flag = r.u8()
            pc = _WDLPerColor()
            self.per_color[c] = pc
            if flag & SINGULAR_FLAG:
                self.is_singular[c] = True
                pc.single_val = r.u8()
            elif flag & DROPPED_FLAG:
                self.is_dropped[c] = True
            else:
                self._parse_header(r, pc)
        if table_num == 1:
            self.is_dropped[CPP_BLACK] = True
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
            pc.offsets = MonoUintVec(r.d[mono_off:], pc.block_cnt + 1, log2_bu,
                                     sample_width, offset_width)
        for c in colors:
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.compressed = r.d[start:start + pc.data_size]
            r.advance(pc.data_size)

    def _get_block(self, pc: _WDLPerColor, block_id: int) -> bytes:
        blk = pc._blocks.get(block_id)
        if blk is not None:
            self.cache.touch(pc, block_id)
            return blk
        doff, dnext = pc.offsets.get2(block_id)
        dsz = dnext - doff
        out_sz = (pc.tail_size if (block_id == pc.block_cnt - 1 and pc.tail_size != 0)
                  else pc.block_size)
        blk = lz4_decompress_block(pc.compressed[doff:doff + dsz], out_sz, pc.dict)
        pc._blocks[block_id] = blk
        self.cache.record(pc, block_id, len(blk))
        return blk

    def read(self, color: int, board: chess.Board) -> int:
        """Return WDL_Stored at the board's index in `color`'s frame."""
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


# ===========================================================================
# Probe orchestration (subset: WDL).  Mirrors src/probe/probe.cpp.
# ===========================================================================

def mirror_for_canonical(board: chess.Board) -> chess.Board:
    """Swap colors and rank-mirror every piece; flip side to move."""
    out = chess.Board.empty()
    for sq in range(64):
        p = board.piece_at(sq)
        if p:
            out.set_piece_at(sq_rank_mirror(sq), chess.Piece(p.piece_type, not p.color))
    out.turn = not board.turn
    return out


_WDL_NAME = {LOSE: "LOSE", BLESSED_LOSS: "BLESSED_LOSS", DRAW: "DRAW",
             CURSED_WIN: "CURSED_WIN", WIN: "WIN", ILLEGAL: "ILLEGAL"}


# --- WDL semantic helpers (egtb_entry.h / probe.cpp) ---

def invert_wdl(w: int) -> int:
    return {WIN: LOSE, CURSED_WIN: BLESSED_LOSS, DRAW: DRAW,
            BLESSED_LOSS: CURSED_WIN, LOSE: WIN, ILLEGAL: ILLEGAL}[w]


def invert_stored(s: int) -> int:
    # WDL_Stored -> WDL_Entry, inverted across one quiet ply (markers tip a ply).
    return {0: WIN, 1: CURSED_WIN, 2: DRAW, 3: BLESSED_LOSS, 4: LOSE,
            5: CURSED_WIN,   # BOUNDARY_LOSS -> we win but only cursed
            6: BLESSED_LOSS,  # BOUNDARY_WIN  -> we lose but only blessed
            7: ILLEGAL}[s]


def wdl_rank(w: int) -> int:
    return {WIN: 4, CURSED_WIN: 3, DRAW: 2, BLESSED_LOSS: 1, LOSE: 0, ILLEGAL: -1}[w]


def is_symmetric_material(cfg: PieceConfig) -> bool:
    return cfg.base_key == cfg.mirr_key


MAX_DERIVE_DEPTH = 16


def _is_pawn_double_push(board: chess.Board, move: chess.Move) -> bool:
    p = board.piece_at(move.from_square)
    return p is not None and p.piece_type == chess.PAWN and \
        abs(sq_rank(move.to_square) - sq_rank(move.from_square)) == 2


def _internal_board(board: chess.Board) -> chess.Board:
    """A copy with no en-passant square (derive move-gen excludes ep; the
    overlay handles ep separately)."""
    if board.ep_square is not None:
        board = board.copy(stack=False)
        board.ep_square = None
    return board


# ===========================================================================
# Tablebase
# ===========================================================================

def _is_legal(board: chess.Board) -> bool:
    """The side that just moved must not be in check; kings present."""
    opp_king = board.king(not board.turn)
    if board.king(board.turn) is None or opp_king is None:
        return False
    return not board.is_attacked_by(board.turn, opp_king)


def _ep_square_after_double_push(move: chess.Move) -> int:
    return (move.from_square + move.to_square) // 2


# ===========================================================================
# LZMA block decode + value-from-storage helpers (egtb_entry.h)
# ===========================================================================

def lzma_raw_decompress(block: memoryview, expected_size: int) -> bytes:
    """Decode a raw LZMA1 stream with 5 props bytes appended at the tail
    (the LZMA SDK ``LzmaUncompress`` framing used by the C++ side)."""
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


def dtc_value_from_storage(stored: int, w: int, entry_bytes: int) -> int:
    if w == DRAW:
        return 0
    if entry_bytes == 1 and (w == CURSED_WIN or w == BLESSED_LOSS):
        return (stored << 1) - 1
    return stored


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


def dtm50_layered_value_from_storage(stored: int, w: int) -> int:
    if stored == 0:
        return 0
    return dtm50_value_from_storage(stored, w)


# ===========================================================================
# DTC table file  —  src/probe/dtc_file.cpp
# ===========================================================================
class _RankPerColor:
    __slots__ = ("order", "radix", "entry_bytes", "block_size", "tail_size",
                 "block_cnt", "data_size", "offsets", "compressed",
                 "rank_to_value", "single_val", "_blocks")
    order: List[int]
    radix: List[int]
    entry_bytes: int
    block_size: int
    tail_size: int
    block_cnt: int
    data_size: int
    offsets: MonoUintVec
    compressed: memoryview
    rank_to_value: List[int]
    single_val: int
    _blocks: Dict[int, bytes]

    def __init__(self) -> None:
        self.single_val = 0
        self._blocks = {}


class DTCFile:
    EXT = ".lzdtc"
    MAGIC = DTC_MAGIC

    def __init__(self, cfg: PieceConfig, path: str, cache: Optional[_BlockCache] = None):
        self.cfg = cfg
        self.index_cfg = position_index_config(cfg)
        self.cache = cache if cache is not None else _BlockCache(DEFAULT_BLOCK_CACHE_BYTES)
        self.is_singular = [False, False]
        self.is_dropped = [False, False]
        self.per_color: List[Optional[_RankPerColor]] = [None, None]
        self._load(path)

    def _load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = f.read()
        if (len(data) & 63) != 8:
            raise ValueError(f"Invalid DTC file size {path}")
        self._data = data
        r = _Serial(memoryview(data))
        if r.u32() != self.MAGIC:
            raise ValueError(f"Invalid DTC magic {path}")
        kat = r.u32()
        if (kat >> 2) != self.cfg.min_key:
            raise ValueError("Wrong material key in DTC")
        table_num = kat & 3
        colors = egtb_table_colors(table_num)
        for c in colors:
            flag = r.u8()
            pc = _RankPerColor()
            self.per_color[c] = pc
            if flag & SINGULAR_FLAG:
                self.is_singular[c] = True
                pc.single_val = r.u8()
            elif flag & DROPPED_FLAG:
                self.is_dropped[c] = True
            else:
                self._parse_header(r, pc)
        if table_num == 1:
            self.is_dropped[CPP_BLACK] = True
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
            r.advance(1)  # usz_width (unused by DTC)
            mono_off = r.caret()
            mb = MonoUintVec.on_disk_bytes(pc.block_cnt + 1, log2_bu, sample_width, offset_width)
            r.advance(mb)
            pc.offsets = MonoUintVec(r.d[mono_off:], pc.block_cnt + 1, log2_bu,
                                     sample_width, offset_width)
        for c in colors:
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.compressed = r.d[start:start + pc.data_size]
            r.advance(pc.data_size)

    def _get_block_raw(self, pc: _RankPerColor, block_id: int) -> bytes:
        blk = pc._blocks.get(block_id)
        if blk is not None:
            self.cache.touch(pc, block_id)
            return blk
        decode_sz = (pc.tail_size if (block_id == pc.block_cnt - 1 and pc.tail_size != 0)
                     else pc.block_size)
        doff, dnext = pc.offsets.get2(block_id)
        dsz = dnext - doff
        blk = b"" if dsz == 0 else lzma_raw_decompress(pc.compressed[doff:doff + dsz], decode_sz)
        pc._blocks[block_id] = blk
        self.cache.record(pc, block_id, len(blk))
        return blk

    def read(self, color: int, board: chess.Board, wdl: int) -> int:
        if wdl == DRAW or wdl == ILLEGAL:
            return 0
        pc = self.per_color[color]
        assert pc is not None
        if self.is_singular[color]:
            return dtc_value_from_storage(pc.single_val, wdl, 1)
        pos = self.index_cfg.board_index(board, pc.order, pc.radix)
        assert pos is not None
        ppb = pc.block_size // pc.entry_bytes
        block_id = pos // ppb
        in_block = pos % ppb
        lo, hi = pc.offsets.get2(block_id)
        if lo == hi:
            return 0  # skip block: uniform DRAW/ILLEGAL
        raw = self._get_block_raw(pc, block_id)
        if pc.entry_bytes == 1:
            stored = raw[in_block]
        else:
            stored = struct.unpack_from("<H", raw, in_block * 2)[0]
        stored = pc.rank_to_value[stored]
        return dtc_value_from_storage(stored, wdl, pc.entry_bytes)


# ===========================================================================
# DTM50 table file (changepoint pack)  —  src/probe/dtm50_file.cpp
# ===========================================================================
def _bit(buf: bytes, i: int) -> int:
    return (buf[i >> 3] >> (i & 7)) & 1


def _prefix_popcount(buf: bytes, n: int) -> List[int]:
    """pre[i] = popcount of bits [0, i) in `buf` (a hint bitmap), i in [0, n]."""
    pre = [0] * (n + 1)
    acc = 0
    for i in range(n):
        acc += (buf[i >> 3] >> (i & 7)) & 1
        pre[i + 1] = acc
    return pre


class _DTM50PerColor:
    __slots__ = ("order", "radix", "entry_bytes", "block_positions",
                 "tail_positions", "block_cnt", "data_size", "offsets",
                 "usizes", "compressed", "rank_to_value", "_blocks")
    order: List[int]
    radix: List[int]
    entry_bytes: int
    block_positions: int
    tail_positions: int
    block_cnt: int
    data_size: int
    offsets: MonoUintVec
    usizes: Min0UintVec
    compressed: memoryview
    rank_to_value: List[int]
    _blocks: Dict[int, Dict[str, Any]]

    def __init__(self) -> None:
        self._blocks = {}


class DTM50File:
    EXT = ".lzdtm50"
    MAGIC = DTM50_MAGIC

    def __init__(self, cfg: PieceConfig, path: str, cache: Optional[_BlockCache] = None):
        self.cfg = cfg
        self.index_cfg = position_index_config(cfg)
        self.cache = cache if cache is not None else _BlockCache(DEFAULT_BLOCK_CACHE_BYTES)
        self.is_singular = [False, False]
        self.is_dropped = [False, False]
        self.per_color: List[Optional[_DTM50PerColor]] = [None, None]
        self._load(path)

    def _load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = f.read()
        if (len(data) & 63) != 8:
            raise ValueError(f"Invalid DTM50 file size {path}")
        self._data = data
        r = _Serial(memoryview(data))
        if r.u32() != self.MAGIC:
            raise ValueError("Invalid DTM50 magic")
        kat = r.u32()
        if (kat >> 2) != self.cfg.min_key:
            raise ValueError("Wrong material key in DTM50")
        table_num = kat & 3
        colors = egtb_table_colors(table_num)
        for c in colors:
            flag = r.u8()
            pc = _DTM50PerColor()
            self.per_color[c] = pc
            if flag & SINGULAR_FLAG:
                self.is_singular[c] = True
                if r.u8() != 0:
                    raise ValueError("DTM50 singular value must be DRAW")
            elif flag & DROPPED_FLAG:
                self.is_dropped[c] = True
            else:
                self._parse_header(r, pc)
        if table_num == 1:
            self.is_dropped[CPP_BLACK] = True
        self._finalize(r, colors)

    def _parse_header(self, r: _Serial, pc: _DTM50PerColor) -> None:
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
            pc.offsets = MonoUintVec(r.d[mono_off:], pc.block_cnt + 1, log2_bu,
                                     sample_width, offset_width)
            pc.usizes = Min0UintVec(r.d[usz_off:], pc.block_cnt, usz_width)
        for c in colors:
            if self.is_singular[c] or self.is_dropped[c]:
                continue
            pc = self.per_color[c]
            assert pc is not None
            r.align(64)
            start = r.caret()
            pc.compressed = r.d[start:start + pc.data_size]
            r.advance(pc.data_size)

    def _get_block(self, pc: _DTM50PerColor, block_id: int) -> Dict[str, Any]:
        blk = pc._blocks.get(block_id)
        if blk is not None:
            self.cache.touch(pc, block_id)
            return blk
        doff, dnext = pc.offsets.get2(block_id)
        dsz = dnext - doff
        usz = pc.usizes.get(block_id)
        payload = lzma_raw_decompress(pc.compressed[doff:doff + dsz], usz)
        eb = pc.entry_bytes
        (num_positions, num_single, num_double, num_multi,
         single_stream_bytes, double_stream_bytes) = struct.unpack_from("<IIIIII", payload, 0)
        num_const = num_positions - num_single - num_double - num_multi
        sb_bytes = (num_positions * 2 + 7) // 8
        sh_bytes = (num_single + 7) // 8
        dh_bytes = (num_double + 7) // 8
        p = 24
        state_bits_off = p; p += sb_bytes
        const_stream_off = p; p += num_const * eb
        single_hints_off = p; p += sh_bytes
        single_stream_off = p; p += single_stream_bytes
        double_hints_off = p; p += dh_bytes
        double_stream_off = p; p += double_stream_bytes
        p += (4 - (p & 3)) & 3
        multi_dir_off = p; p += (num_multi + 1) * 4
        multi_data_off = p

        state_bits = payload[state_bits_off:state_bits_off + sb_bytes]
        single_hints = payload[single_hints_off:single_hints_off + sh_bytes]
        double_hints = payload[double_hints_off:double_hints_off + dh_bytes]

        # Per-position 2-bit state, and each position's index within its class.
        # (The C++ side keeps an O(STRIDE) prefix index; precomputing exact
        # per-position indices is simpler and adequate in Python.)
        state = bytearray(num_positions)
        index_of = [0] * num_positions
        c0 = c1 = c2 = c3 = 0
        for q in range(num_positions):
            bitpos = q * 2
            st = (state_bits[bitpos >> 3] >> (bitpos & 7)) & 3
            state[q] = st
            if st == 0:
                index_of[q] = c0; c0 += 1
            elif st == 1:
                index_of[q] = c1; c1 += 1
            elif st == 2:
                index_of[q] = c2; c2 += 1
            else:
                index_of[q] = c3; c3 += 1
        single_short_pre = _prefix_popcount(single_hints, num_single)
        double_short_pre = _prefix_popcount(double_hints, num_double)

        blk = {
            "payload": payload, "eb": eb,
            "state": state, "index_of": index_of,
            "const_stream_off": const_stream_off,
            "single_hints": single_hints, "single_stream_off": single_stream_off,
            "double_hints": double_hints, "double_stream_off": double_stream_off,
            "multi_dir_off": multi_dir_off, "multi_data_off": multi_data_off,
            "single_short_pre": single_short_pre, "double_short_pre": double_short_pre,
        }
        pc._blocks[block_id] = blk
        # Approximate resident size: the decoded payload plus the per-position
        # Python state/index lists derived above.
        self.cache.record(pc, block_id, len(payload) + 9 * num_positions)
        return blk

    @staticmethod
    def _read_rank(payload: bytes, off: int, eb: int) -> int:
        return payload[off] if eb == 1 else int(struct.unpack_from("<H", payload, off)[0])

    def read(self, color: int, board: chess.Board, wdl: int, hmc: int) -> int:
        if wdl == DRAW or wdl == ILLEGAL:
            return 0
        flat = (hmc == IGNORE_50MR)
        if not flat and (wdl == CURSED_WIN or wdl == BLESSED_LOSS):
            return 0
        pc = self.per_color[color]
        assert pc is not None
        if self.is_singular[color]:
            return 0
        ppb = pc.block_positions
        pos = self.index_cfg.board_index(board, pc.order, pc.radix)
        assert pos is not None
        block_id = pos // ppb
        pos_in_block = pos % ppb
        lo, hi = pc.offsets.get2(block_id)
        if lo == hi:
            return 0  # skip block (uniform DRAW)
        blk = self._get_block(pc, block_id)
        payload = blk["payload"]
        eb = blk["eb"]
        st = blk["state"][pos_in_block]
        idx = blk["index_of"][pos_in_block]
        r2v = pc.rank_to_value
        layer = 0 if flat else (hmc + 1)

        if st == 0:  # CONST: one rank for all layers
            stored = r2v[self._read_rank(payload, blk["const_stream_off"] + idx * eb, eb)]
        elif st == 1:  # SINGLE: one transition at h
            short, long = 1 + eb, 1 + 2 * eb
            n_short = blk["single_short_pre"][idx]
            off = blk["single_stream_off"] + n_short * short + (idx - n_short) * long
            draw_end = _bit(blk["single_hints"], idx)
            h = payload[off] & 0x7F
            if layer < h:
                stored = r2v[self._read_rank(payload, off + 1, eb)]
            elif draw_end:
                stored = 0
            else:
                stored = r2v[self._read_rank(payload, off + 1 + eb, eb)]
        elif st == 2:  # DOUBLE: transitions at h1 < h2
            short, long = 2 + 2 * eb, 2 + 3 * eb
            n_short = blk["double_short_pre"][idx]
            off = blk["double_stream_off"] + n_short * short + (idx - n_short) * long
            draw_end = _bit(blk["double_hints"], idx)
            h1 = payload[off]
            h2 = payload[off + 1] & 0x7F
            rsel = 0 if layer < h1 else (1 if layer < h2 else 2)
            if rsel == 2 and draw_end:
                stored = 0
            else:
                stored = r2v[self._read_rank(payload, off + 2 + rsel * eb, eb)]
        else:  # MULTI: 128-bit changepoint bitmap
            entry = blk["multi_data_off"] + struct.unpack_from(
                "<I", payload, blk["multi_dir_off"] + idx * 4)[0]
            kbyte = payload[entry]
            draw_end = (kbyte & 0x80) != 0
            k = kbyte & 0x7F
            lo64 = struct.unpack_from("<Q", payload, entry + 1)[0]
            hi64 = struct.unpack_from("<Q", payload, entry + 9)[0]
            if layer < 63:
                mask_lo, mask_hi = (1 << (layer + 1)) - 1, 0
            elif layer == 63:
                mask_lo, mask_hi = (1 << 64) - 1, 0
            else:
                mask_lo, mask_hi = (1 << 64) - 1, (1 << (layer - 63)) - 1
            rsel = bin(lo64 & mask_lo).count("1") + bin(hi64 & mask_hi).count("1") - 1
            if rsel == k - 1 and draw_end:
                stored = 0
            else:
                stored = r2v[self._read_rank(payload, entry + 17 + rsel * eb, eb)]

        if flat:
            return dtm_value_from_storage(stored, wdl)
        if hmc == 0:
            return dtm50_value_from_storage(stored, wdl)
        return dtm50_layered_value_from_storage(stored, wdl)


# ===========================================================================
# Probe orchestration  —  src/probe/probe.cpp
# ===========================================================================
DTC_MAX_NON_CURSED_DTZ = 100


def prefer_new(new_wdl: int, new_dtc: int, old_wdl: int, old_dtc: int) -> bool:
    rn, ro = wdl_rank(new_wdl), wdl_rank(old_wdl)
    if rn != ro:
        return rn > ro
    if new_wdl in (WIN, CURSED_WIN):
        return new_dtc < old_dtc
    if new_wdl in (LOSE, BLESSED_LOSS):
        return new_dtc > old_dtc
    return False


def fold_dtm_wdl(w: int) -> int:
    if w == CURSED_WIN:
        return WIN
    if w == BLESSED_LOSS:
        return LOSE
    return w


def fold_dtm50_wdl(w: int) -> int:
    if w == CURSED_WIN or w == BLESSED_LOSS:
        return DRAW
    return w


def _is_checkmate(board: chess.Board) -> bool:
    return board.is_checkmate()


def _ep_capture_moves(
    board: chess.Board, ep_square: Optional[int]
) -> Tuple[Optional[chess.Board], List[chess.Move]]:
    """Legal en-passant captures available given `ep_square`, using python-chess
    to execute the capture correctly. Returns (ep_board, [moves])."""
    if ep_square is None:
        return None, []
    bcopy = board.copy(stack=False)
    bcopy.ep_square = ep_square
    return bcopy, [m for m in bcopy.legal_moves if bcopy.is_en_passant(m)]


class ProbeResult:
    """Outcome of :meth:`Tablebase.probe`.

    ``status`` is ``"ok"``, ``"illegal_pos"`` or ``"tb_not_found"``. ``wdl`` and
    ``dtm50_wdl`` are :data:`WIN`..:data:`LOSE` codes; ``dtc``/``dtm``/``dtm50``
    are unsigned ply counts whose sign is given by the corresponding WDL class.
    """

    __slots__ = ("status", "wdl", "has_dtc", "dtc", "has_dtm", "dtm",
                 "has_dtm50", "dtm50_wdl", "dtm50")

    status: str
    wdl: int
    has_dtc: bool
    dtc: int
    has_dtm: bool
    dtm: int
    has_dtm50: bool
    dtm50_wdl: int
    dtm50: int

    def __init__(self) -> None:
        self.status = "tb_not_found"
        self.wdl = ILLEGAL
        self.has_dtc = False
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
        if self.has_dtc:
            s += f" dtz={self.dtc}"
        if self.has_dtm:
            s += f" dtm={self.dtm}"
        if self.has_dtm50:
            s += f" dtm50={_WDL_NAME[self.dtm50_wdl]}/{self.dtm50}"
        return s + ">"


class MissingTableError(KeyError):
    """Raised when no table is available for the queried material."""


# Signed WDL convention matching chess.syzygy: +2 win, +1 cursed win,
# 0 draw, -1 blessed loss, -2 loss.
_WDL_SIGNED = {WIN: 2, CURSED_WIN: 1, DRAW: 0, BLESSED_LOSS: -1, LOSE: -2}


def _signed(magnitude: int, wdl: int) -> int:
    if wdl in (WIN, CURSED_WIN):
        return magnitude
    if wdl in (LOSE, BLESSED_LOSS):
        return -magnitude
    return 0


class Tablebase:
    """Probe a directory tree of chesstb tables.

    `directory` may contain ``wdl/``, ``dtc/`` and ``dtm50/`` subdirectories
    (the generator's layout) or the table files directly. Use
    :func:`open_tablebase`. Probing is read-only and the result of each query is
    derived from the canonical orientation of the board's material.
    """

    def __init__(self, directory: str, *, block_cache_bytes: int = DEFAULT_BLOCK_CACHE_BYTES):
        self.dirs: Dict[str, List[str]] = {kind: [] for kind in ("wdl", "dtc", "dtm50")}
        self._wdl_cache: Dict[int, Optional[WDLFile]] = {}
        self._dtc_cache: Dict[int, Optional[DTCFile]] = {}
        self._dtm50_cache: Dict[int, Optional[DTM50File]] = {}
        # Shared LRU so decoded blocks are reclaimed automatically once the
        # budget is exceeded, rather than growing for the lifetime of the probe.
        self._block_cache = _BlockCache(block_cache_bytes)
        self.add_directory(directory)

    def add_directory(self, directory: str) -> None:
        """Add another search directory (and its kind subdirectories)."""
        for kind in ("wdl", "dtc", "dtm50"):
            self.dirs[kind].append(os.path.join(directory, kind))
            self.dirs[kind].append(directory)

    def close(self) -> None:
        """Drop all cached decoded blocks and open tables."""
        self._block_cache.clear()
        self._wdl_cache.clear()
        self._dtc_cache.clear()
        self._dtm50_cache.clear()

    def __enter__(self) -> "Tablebase":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # --- table file resolution / caching ---
    def _find(self, kind: str, name: str, ext: str) -> Optional[str]:
        for d in self.dirs[kind]:
            p = os.path.join(d, name + ext)
            if os.path.exists(p):
                return p
        return None

    def _open_wdl(self, cfg: PieceConfig) -> Optional[WDLFile]:
        k = cfg.cache_key
        if k not in self._wdl_cache:
            p = self._find("wdl", cfg.name(), WDLFile.EXT)
            self._wdl_cache[k] = WDLFile(cfg, p, self._block_cache) if p else None
        return self._wdl_cache[k]

    def _open_dtc(self, cfg: PieceConfig) -> Optional[DTCFile]:
        k = cfg.cache_key
        if k not in self._dtc_cache:
            p = self._find("dtc", cfg.name(), DTCFile.EXT)
            self._dtc_cache[k] = DTCFile(cfg, p, self._block_cache) if p else None
        return self._dtc_cache[k]

    def _open_dtm50(self, cfg: PieceConfig) -> Optional[DTM50File]:
        k = cfg.cache_key
        if k not in self._dtm50_cache:
            p = self._find("dtm50", cfg.name(), DTM50File.EXT)
            self._dtm50_cache[k] = DTM50File(cfg, p, self._block_cache) if p else None
        return self._dtm50_cache[k]

    def _has_any_table(self, cfg: PieceConfig) -> bool:
        return self._open_wdl(cfg) is not None

    # --- child construction for the derive / overlay paths ---
    def _make_child(self, parent: chess.Board, move: chess.Move
                    ) -> Tuple[PieceConfig, chess.Board, Optional[int], bool, bool]:
        zeroing = parent.is_zeroing(move)
        raw_ep = _ep_square_after_double_push(move) if _is_pawn_double_push(parent, move) else None
        child = parent.copy(stack=False)
        child.push(move)
        child.ep_square = None

        # Prefer the child's frozen-pair table when one is on disk: a move that
        # keeps the pair (any non-capture, including a free-pawn push) stays in a
        # 'p' material that the board-derived config below would miss -- it sees
        # the pair pawns as ordinary free pawns. Falls back to the full physical
        # material for captures/promotions and when no 'p' table is present. Owns
        # the child ep so the routed/mirrored board and ep can't desync.
        paired = pair_config_from_board(child)
        if paired is not None and self._has_any_table(paired[0]):
            cfg, mirrored = paired
        else:
            cfg, mirrored = piece_config_from_board(child)

        ep = raw_ep
        if mirrored:
            child = mirror_for_canonical(child)
            if ep is not None:
                ep = sq_rank_mirror(ep)
        is_kk = cfg.num_pieces <= 2
        return cfg, child, ep, is_kk, zeroing

    # --- WDL ---
    def _read_wdl_stored(self, w: Optional[WDLFile], board: chess.Board) -> int:
        if w is None:
            return 7  # WDL_Stored::ILLEGAL
        color = CPP_WHITE if board.turn == WHITE else CPP_BLACK
        return w.read(color, board)

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
            return wdl_from_storage(w.read(mc, mp))
        return wdl_from_storage(w.read(color, board))

    def _derive_wdl(self, board: chess.Board, depth: int) -> int:
        if depth >= MAX_DERIVE_DEPTH:
            return ILLEGAL
        b = _internal_board(board)
        any_legal = have = False
        best = LOSE
        for m in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, is_kk, zeroing = self._make_child(b, m)
            if is_kk:
                mw = DRAW
            elif zeroing:
                cw = self._probe_wdl_impl(cfg_c, cboard, cep, depth + 1)
                if cw == ILLEGAL:
                    continue
                mw = invert_wdl(cw)
            else:
                cs = self._read_wdl_stored(self._open_wdl(cfg_c), cboard)
                if cs == 7:
                    continue
                mw = invert_stored(cs)
            if wdl_rank(mw) > wdl_rank(best):
                best = mw
            have = True
        if not any_legal:
            return LOSE if b.is_check() else DRAW
        if not have:
            return ILLEGAL
        return best

    def _probe_wdl_impl(self, cfg: PieceConfig, board: chess.Board,
                        ep_square: Optional[int], depth: int) -> int:
        if not _is_legal(board):
            return ILLEGAL
        best = self._probe_wdl_internal(self._open_wdl(cfg), cfg, board, depth)
        if best == ILLEGAL or ep_square is None:
            return best
        bcopy, eps = _ep_capture_moves(board, ep_square)
        assert bcopy is not None  # ep_square is not None here
        for m in eps:
            cfg_c, cboard, _cep, is_kk, _ = self._make_child(bcopy, m)
            cw = DRAW if is_kk else self._probe_wdl_internal(
                self._open_wdl(cfg_c), cfg_c, cboard, depth + 1)
            if cw == ILLEGAL:
                continue
            mine = invert_wdl(cw)
            if wdl_rank(mine) > wdl_rank(best):
                best = mine
        return best

    # --- DTC ---
    def _probe_dtc_internal(self, d: Optional[DTCFile], cfg: PieceConfig,
                            board: chess.Board, wdl: int, depth: int) -> Optional[int]:
        if d is None:
            return None
        color = CPP_WHITE if board.turn == WHITE else CPP_BLACK
        if d.is_dropped[color]:
            if not is_symmetric_material(cfg):
                return self._derive_dtc(board, depth)
            mp = mirror_for_canonical(board)
            mc = CPP_WHITE if mp.turn == WHITE else CPP_BLACK
            return d.read(mc, mp, wdl)
        return d.read(color, board, wdl)

    def _derive_dtc(self, board: chess.Board, depth: int) -> Optional[int]:
        if depth >= MAX_DERIVE_DEPTH:
            return None
        b = _internal_board(board)
        any_legal = have = False
        best_wdl, best_dtc = LOSE, 0
        for m in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, is_kk, zeroing = self._make_child(b, m)
            if is_kk:
                cw, my_dtc = DRAW, 1
            elif zeroing:
                cw = self._probe_wdl_impl(cfg_c, cboard, cep, depth + 1)
                if cw == ILLEGAL:
                    continue
                my_dtc = 1
            else:
                cw = self._probe_wdl_internal(self._open_wdl(cfg_c), cfg_c, cboard, depth + 1)
                if cw == ILLEGAL:
                    continue
                child_dtc = self._probe_dtc_internal(self._open_dtc(cfg_c), cfg_c, cboard, cw, depth + 1)
                if child_dtc is None:
                    continue
                my_dtc = 1 + child_dtc
            my_wdl = invert_wdl(cw)
            if my_dtc > DTC_MAX_NON_CURSED_DTZ:
                if my_wdl == WIN:
                    my_wdl = CURSED_WIN
                elif my_wdl == LOSE:
                    my_wdl = BLESSED_LOSS
            if not have or prefer_new(my_wdl, my_dtc, best_wdl, best_dtc):
                best_wdl, best_dtc, have = my_wdl, my_dtc, True
        if not any_legal or best_wdl == DRAW:
            return 0
        if not have:
            return None
        return best_dtc

    # --- DTM50 / DTM ---
    def _recover_mate_at_hmc(self, board: chess.Board, wdl: int) -> Tuple[int, int]:
        if wdl == WIN:
            for m in board.legal_moves:
                child = board.copy(stack=False)
                child.push(m)
                if child.is_checkmate():
                    return (WIN, 1)
            return (DRAW, 0)
        if wdl == LOSE:
            return (LOSE, 0) if board.is_checkmate() else (DRAW, 0)
        return (DRAW, 0)

    def _probe_dtm50_internal(self, m: Optional[DTM50File], cfg: PieceConfig,
                              board: chess.Board, wdl: int, rule50: int,
                              depth: int) -> Tuple[int, int]:
        flat = (rule50 == IGNORE_50MR)
        if not flat and rule50 >= DTM50_HMC_COUNT:
            return (DRAW, 0)
        if m is None:
            return (ILLEGAL, 0)
        color = CPP_WHITE if board.turn == WHITE else CPP_BLACK
        if not m.is_dropped[color]:
            val = m.read(color, board, wdl, rule50)
            d = (wdl if flat else fold_dtm50_wdl(wdl), val)
        elif not is_symmetric_material(cfg):
            d = (self._derive_dtm50_flat(board, depth) if flat
                 else self._derive_dtm50(board, rule50, depth))
        else:
            mp = mirror_for_canonical(board)
            mc = CPP_WHITE if mp.turn == WHITE else CPP_BLACK
            val = m.read(mc, mp, wdl, rule50)
            d = (wdl if flat else fold_dtm50_wdl(wdl), val)
        if (not flat) and rule50 > 0 and d[1] == 0 and (wdl == WIN or wdl == LOSE):
            return self._recover_mate_at_hmc(board, wdl)
        return d

    def _derive_dtm50_flat(self, board: chess.Board,
                           depth: int) -> Tuple[int, int]:
        if depth >= MAX_DERIVE_DEPTH:
            return (ILLEGAL, 0)
        b = _internal_board(board)
        any_legal = have = False
        best_wdl, best_dtm = LOSE, 0
        for mv in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, is_kk, zeroing = self._make_child(b, mv)
            if is_kk:
                cw, cd = DRAW, 0
            elif cep is not None:
                cr = self._probe_impl(cfg_c, cboard, IGNORE_50MR, cep, depth + 1)
                if cr.status != "ok" or cr.wdl == ILLEGAL or not cr.has_dtm:
                    continue
                cw, cd = cr.wdl, cr.dtm
            else:
                cw = self._probe_wdl_internal(self._open_wdl(cfg_c), cfg_c, cboard, depth + 1)
                if cw == ILLEGAL:
                    continue
                cwd, cdd = self._probe_dtm50_internal(self._open_dtm50(cfg_c), cfg_c, cboard,
                                                      cw, IGNORE_50MR, depth + 1)
                if cwd == ILLEGAL:
                    continue
                cw, cd = cwd, cdd
            if cw == CURSED_WIN:
                cw = WIN
            elif cw == BLESSED_LOSS:
                cw = LOSE
            my_wdl = invert_wdl(cw)
            my_dtm = 1 + cd
            if not have or prefer_new(my_wdl, my_dtm, best_wdl, best_dtm):
                best_wdl, best_dtm, have = my_wdl, my_dtm, True
        if not any_legal:
            return (LOSE, 0) if b.is_check() else (DRAW, 0)
        if not have:
            return (ILLEGAL, 0)
        if best_wdl in (WIN, LOSE):
            return (best_wdl, best_dtm)
        return (DRAW, 0)

    def _derive_dtm50(self, board: chess.Board, rule50: int,
                      depth: int) -> Tuple[int, int]:
        if depth >= MAX_DERIVE_DEPTH:
            return (ILLEGAL, 0)
        b = _internal_board(board)
        any_legal = have = False
        best_wdl, best_dtm = LOSE, 0
        for mv in b.legal_moves:
            any_legal = True
            cfg_c, cboard, cep, is_kk, zeroing = self._make_child(b, mv)
            child_rule50 = 0 if zeroing else rule50 + 1
            if is_kk:
                cd = (DRAW, 0)
            elif child_rule50 >= DTM50_HMC_COUNT:
                cd = (LOSE, 0) if _is_checkmate(cboard) else (DRAW, 0)
            elif cep is not None:
                cr = self._probe_impl(cfg_c, cboard, child_rule50, cep, depth + 1)
                if cr.status != "ok" or not cr.has_dtm50:
                    continue
                cd = (cr.dtm50_wdl, cr.dtm50)
            else:
                cw = self._probe_wdl_internal(self._open_wdl(cfg_c), cfg_c, cboard, depth + 1)
                if cw == ILLEGAL:
                    continue
                cd = self._probe_dtm50_internal(self._open_dtm50(cfg_c), cfg_c, cboard,
                                                cw, child_rule50, depth + 1)
                if cd[0] == ILLEGAL:
                    continue
            my_wdl = invert_wdl(fold_dtm50_wdl(cd[0]))
            my_dtm = 1 + cd[1]
            if not have or prefer_new(my_wdl, my_dtm, best_wdl, best_dtm):
                best_wdl, best_dtm, have = my_wdl, my_dtm, True
        if not any_legal:
            return (LOSE, 0) if b.is_check() else (DRAW, 0)
        if not have:
            return (ILLEGAL, 0)
        if best_wdl in (WIN, LOSE):
            return (best_wdl, best_dtm)
        return (DRAW, 0)

    # --- combined probe (mirrors probe.cpp's probe_impl, with ep overlay) ---
    def _probe_impl(self, cfg: PieceConfig, board: chess.Board, rule50: int,
                    ep_square: Optional[int], depth: int) -> ProbeResult:
        r = ProbeResult()
        if not _is_legal(board):
            r.status = "illegal_pos"
            return r
        w = self._open_wdl(cfg)
        rule50_drawn = (rule50 != IGNORE_50MR and rule50 >= DTM50_HMC_COUNT)
        # DTC/DTM50 reads are all gated on WDL, so WDL absent (and not a rule50
        # auto-draw) means there is nothing to return.
        if w is None and not rule50_drawn:
            return r  # tb_not_found
        r.status = "ok"
        if w is not None:
            r.wdl = self._probe_wdl_internal(w, cfg, board, depth)
            d = self._open_dtc(cfg)
            if d is not None:
                dtc = self._probe_dtc_internal(d, cfg, board, r.wdl, depth)
                if dtc is not None:
                    r.has_dtc = True
                    r.dtc = dtc
            m50 = self._open_dtm50(cfg)
            if m50 is not None:
                d50w, d50v = self._probe_dtm50_internal(m50, cfg, board, r.wdl, IGNORE_50MR, depth)
                r.dtm = d50v
                r.has_dtm = (d50w != ILLEGAL)
                if rule50_drawn:
                    mated = (r.wdl == LOSE and _is_checkmate(board))
                    r.dtm50_wdl = LOSE if mated else DRAW
                    r.dtm50 = 0
                    r.has_dtm50 = True
                elif rule50 != IGNORE_50MR:
                    rw, rv = self._probe_dtm50_internal(m50, cfg, board, r.wdl, rule50, depth)
                    r.dtm50_wdl = rw
                    r.dtm50 = rv
                    r.has_dtm50 = (rw != ILLEGAL)

        if ep_square is None:
            return r
        bcopy, eps = _ep_capture_moves(board, ep_square)
        if not eps:
            return r
        assert bcopy is not None

        best = r
        best_dtc_wdl = r.wdl
        best_dtc = r.dtc if r.has_dtc else 0
        best_dtm_wdl = fold_dtm_wdl(r.wdl)
        best_dtm = r.dtm if r.has_dtm else 0
        best_dtm50_wdl = r.dtm50_wdl if r.has_dtm50 else fold_dtm50_wdl(r.wdl)
        best_dtm50 = r.dtm50 if r.has_dtm50 else 0
        for mv in eps:
            cfg_c, cboard, _cep, is_kk, _ = self._make_child(bcopy, mv)
            if is_kk:
                cr = ProbeResult()
                cr.status = "ok"
                cr.wdl = DRAW
                cr.has_dtc = best.has_dtc; cr.dtc = 0
                cr.has_dtm = best.has_dtm; cr.dtm = 0
                cr.has_dtm50 = best.has_dtm50; cr.dtm50_wdl = DRAW; cr.dtm50 = 0
            else:
                cr = self._probe_impl(cfg_c, cboard, 0, None, depth + 1)  # ep is zeroing
            if cr.status != "ok" or cr.wdl == ILLEGAL:
                continue
            my_wdl = invert_wdl(cr.wdl)
            if wdl_rank(my_wdl) > wdl_rank(best.wdl):
                best.wdl = my_wdl
            if best.has_dtc and cr.has_dtc and prefer_new(my_wdl, 1, best_dtc_wdl, best_dtc):
                best_dtc_wdl, best_dtc, best.dtc = my_wdl, 1, 1
            if best.has_dtm and cr.has_dtm:
                my_dtm_wdl = fold_dtm_wdl(my_wdl)
                my_dtm = 1 + cr.dtm
                if prefer_new(my_dtm_wdl, my_dtm, best_dtm_wdl, best_dtm):
                    best_dtm_wdl, best_dtm = my_dtm_wdl, my_dtm
                    best.dtm = my_dtm if my_dtm_wdl in (WIN, LOSE) else 0
            if best.has_dtm50 and cr.has_dtm50:
                my_dtm50_wdl = invert_wdl(cr.dtm50_wdl)
                my_dtm50 = 1 + cr.dtm50
                if prefer_new(my_dtm50_wdl, my_dtm50, best_dtm50_wdl, best_dtm50):
                    best_dtm50_wdl, best_dtm50 = my_dtm50_wdl, my_dtm50
                    best.dtm50_wdl = my_dtm50_wdl
                    best.dtm50 = my_dtm50 if my_dtm50_wdl in (WIN, LOSE) else 0
        return best

    # --- public API ---
    def probe(self, board: chess.Board, rule50: int = 0) -> ProbeResult:
        """Full probe of `board`. `rule50` (the halfmove clock) selects the DTM50
        layer. Returns a :class:`ProbeResult`; its ``status`` is ``"ok"``,
        ``"tb_not_found"`` (no table for the material), or ``"illegal_pos"``."""
        # Prefer a frozen-pair table: if the board has an opposing pawn pair and
        # that 'p' table is on disk, route there; else fall back to the full
        # material. The pair table is partial and a position has the same value
        # in either, so preferring the pair table when present is safe.
        paired = pair_config_from_board(board)
        if paired is not None and self._has_any_table(paired[0]):
            cfg, mirrored = paired
        else:
            cfg, mirrored = piece_config_from_board(board)
        if mirrored:
            cboard = mirror_for_canonical(board)
            ep = sq_rank_mirror(board.ep_square) if board.ep_square is not None else None
        else:
            cboard = board.copy(stack=False)
            ep = board.ep_square
        cboard.ep_square = None
        return self._probe_impl(cfg, cboard, rule50, ep, 0)

    def _require(self, board: chess.Board) -> ProbeResult:
        r = self.probe(board)
        if r.status == "tb_not_found":
            cfg, _ = piece_config_from_board(board)
            raise MissingTableError(f"no chesstb table for {cfg.name()}")
        if r.status == "illegal_pos":
            raise ValueError("illegal position")
        return r

    def probe_wdl(self, board: chess.Board) -> int:
        """5-class WDL as a signed int: +2 win, +1 cursed win, 0 draw,
        -1 blessed loss, -2 loss. Raises :class:`MissingTableError` if no table
        and :class:`ValueError` on an illegal position."""
        return _WDL_SIGNED[self._require(board).wdl]

    def get_wdl(self, board: chess.Board, default: Any = None) -> Any:
        try:
            return self.probe_wdl(board)
        except (MissingTableError, ValueError):
            return default

    def probe_dtz(self, board: chess.Board) -> int:
        """Signed distance-to-conversion (chesstb DTC): +N = side to move
        converts toward a win in N plies, -N toward a loss, 0 = draw."""
        r = self._require(board)
        if not r.has_dtc:
            raise MissingTableError("DTC table unavailable")
        return _signed(r.dtc, r.wdl)

    def get_dtz(self, board: chess.Board, default: Any = None) -> Any:
        try:
            return self.probe_dtz(board)
        except (MissingTableError, ValueError):
            return default

    def probe_dtm(self, board: chess.Board) -> int:
        """Signed distance-to-mate, ignoring the 50-move rule."""
        r = self._require(board)
        if not r.has_dtm:
            raise MissingTableError("DTM unavailable")
        return _signed(r.dtm, r.wdl)

    def get_dtm(self, board: chess.Board, default: Any = None) -> Any:
        try:
            return self.probe_dtm(board)
        except (MissingTableError, ValueError):
            return default

    def probe_dtm50(self, board: chess.Board, rule50: Optional[int] = None) -> Tuple[int, int]:
        """50-move-rule-aware distance to mate at the board's halfmove clock (or
        `rule50` if given). Returns ``(signed_wdl, plies)``; cursed/blessed both
        collapse to draw under the 50-move rule."""
        hmc = board.halfmove_clock if rule50 is None else rule50
        cfg, _ = piece_config_from_board(board)
        r = self.probe(board, hmc)
        if r.status == "tb_not_found":
            raise MissingTableError(f"no chesstb table for {cfg.name()}")
        if r.status == "illegal_pos":
            raise ValueError("illegal position")
        if not r.has_dtm50:
            raise MissingTableError("DTM50 unavailable")
        return (_WDL_SIGNED[r.dtm50_wdl], r.dtm50)


def open_tablebase(directory: str, *,
                   block_cache_bytes: int = DEFAULT_BLOCK_CACHE_BYTES) -> Tablebase:
    """Open a directory tree of chesstb tables (``wdl/``, ``dtc/``, ``dtm50/``
    subdirectories, or table files directly under `directory`).

    Decoded blocks are kept in a least-recently-used cache bounded by
    `block_cache_bytes`; older blocks are reclaimed automatically once the
    budget is exceeded."""
    return Tablebase(directory, block_cache_bytes=block_cache_bytes)
