"""
A chess library with move generation and validation,
Polyglot opening book probing, PGN reading and writing,
Gaviota tablebase probing,
Syzygy tablebase probing, and XBoard/UCI engine communication.
"""

from __future__ import annotations

__author__ = "Niklas Fiekas"

__email__ = "niklas.fiekas@backscattering.de"

__version__ = "1.11.1"

import collections
import copy
import dataclasses
import enum
import math
import re
import itertools
import typing

from typing import ClassVar, Callable, Counter, Dict, Generic, Hashable, Iterable, Iterator, List, Literal, Mapping, Optional, SupportsInt, Tuple, Type, TypeVar, Union

if typing.TYPE_CHECKING:
    from typing_extensions import Self, TypeAlias


EnPassantSpec = Literal["legal", "fen", "xfen"]


Color: TypeAlias = bool
WHITE: Color = True
BLACK: Color = False
COLORS: List[Color] = [WHITE, BLACK]
ColorName = Literal["white", "black"]
COLOR_NAMES: List[ColorName] = ["black", "white"]

PieceType: TypeAlias = int
PAWN: PieceType = 1
KNIGHT: PieceType = 2
BISHOP: PieceType = 3
ROOK: PieceType = 4
QUEEN: PieceType = 5
KING: PieceType = 6
PIECE_TYPES: List[PieceType] = [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]
PIECE_SYMBOLS = [None, "p", "n", "b", "r", "q", "k"]
PIECE_NAMES = [None, "pawn", "knight", "bishop", "rook", "queen", "king"]

def piece_symbol(piece_type: PieceType) -> str:
    return typing.cast(str, PIECE_SYMBOLS[piece_type])

def piece_name(piece_type: PieceType) -> str:
    return typing.cast(str, PIECE_NAMES[piece_type])

UNICODE_PIECE_SYMBOLS = {
    "R": "♖", "r": "♜",
    "N": "♘", "n": "♞",
    "B": "♗", "b": "♝",
    "Q": "♕", "q": "♛",
    "K": "♔", "k": "♚",
    "P": "♙", "p": "♟",
}

FILE_NAMES = ["a", "b", "c", "d", "e", "f", "g", "h"]

RANK_NAMES = ["1", "2", "3", "4", "5", "6", "7", "8"]

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
"""The FEN for the standard chess starting position."""

STARTING_BOARD_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
"""The board part of the FEN for the standard chess starting position."""


class Status(enum.IntFlag):
    VALID = 0
    NO_WHITE_KING = 1 << 0
    NO_BLACK_KING = 1 << 1
    TOO_MANY_KINGS = 1 << 2
    TOO_MANY_WHITE_PAWNS = 1 << 3
    TOO_MANY_BLACK_PAWNS = 1 << 4
    PAWNS_ON_BACKRANK = 1 << 5
    TOO_MANY_WHITE_PIECES = 1 << 6
    TOO_MANY_BLACK_PIECES = 1 << 7
    BAD_CASTLING_RIGHTS = 1 << 8
    INVALID_EP_SQUARE = 1 << 9
    OPPOSITE_CHECK = 1 << 10
    EMPTY = 1 << 11
    RACE_CHECK = 1 << 12
    RACE_OVER = 1 << 13
    RACE_MATERIAL = 1 << 14
    TOO_MANY_CHECKERS = 1 << 15
    IMPOSSIBLE_CHECK = 1 << 16

STATUS_VALID = Status.VALID
STATUS_NO_WHITE_KING = Status.NO_WHITE_KING
STATUS_NO_BLACK_KING = Status.NO_BLACK_KING
STATUS_TOO_MANY_KINGS = Status.TOO_MANY_KINGS
STATUS_TOO_MANY_WHITE_PAWNS = Status.TOO_MANY_WHITE_PAWNS
STATUS_TOO_MANY_BLACK_PAWNS = Status.TOO_MANY_BLACK_PAWNS
STATUS_PAWNS_ON_BACKRANK = Status.PAWNS_ON_BACKRANK
STATUS_TOO_MANY_WHITE_PIECES = Status.TOO_MANY_WHITE_PIECES
STATUS_TOO_MANY_BLACK_PIECES = Status.TOO_MANY_BLACK_PIECES
STATUS_BAD_CASTLING_RIGHTS = Status.BAD_CASTLING_RIGHTS
STATUS_INVALID_EP_SQUARE = Status.INVALID_EP_SQUARE
STATUS_OPPOSITE_CHECK = Status.OPPOSITE_CHECK
STATUS_EMPTY = Status.EMPTY
STATUS_RACE_CHECK = Status.RACE_CHECK
STATUS_RACE_OVER = Status.RACE_OVER
STATUS_RACE_MATERIAL = Status.RACE_MATERIAL
STATUS_TOO_MANY_CHECKERS = Status.TOO_MANY_CHECKERS
STATUS_IMPOSSIBLE_CHECK = Status.IMPOSSIBLE_CHECK


class Termination(enum.Enum):
    """Enum with reasons for a game to be over."""

    CHECKMATE = enum.auto()
    """See :func:`chess.Board.is_checkmate()`."""
    STALEMATE = enum.auto()
    """See :func:`chess.Board.is_stalemate()`."""
    INSUFFICIENT_MATERIAL = enum.auto()
    """See :func:`chess.Board.is_insufficient_material()`."""
    SEVENTYFIVE_MOVES = enum.auto()
    """See :func:`chess.Board.is_seventyfive_moves()`."""
    FIVEFOLD_REPETITION = enum.auto()
    """See :func:`chess.Board.is_fivefold_repetition()`."""
    FIFTY_MOVES = enum.auto()
    """See :func:`chess.Board.can_claim_fifty_moves()`."""
    THREEFOLD_REPETITION = enum.auto()
    """See :func:`chess.Board.can_claim_threefold_repetition()`."""
    VARIANT_WIN = enum.auto()
    """See :func:`chess.Board.is_variant_win()`."""
    VARIANT_LOSS = enum.auto()
    """See :func:`chess.Board.is_variant_loss()`."""
    VARIANT_DRAW = enum.auto()
    """See :func:`chess.Board.is_variant_draw()`."""

@dataclasses.dataclass
class Outcome:
    """
    Information about the outcome of an ended game, usually obtained from
    :func:`chess.Board.outcome()`.
    """

    termination: Termination
    """The reason for the game to have ended."""

    winner: Optional[Color]
    """The winning color or ``None`` if drawn."""

    def result(self) -> str:
        """Returns ``1-0``, ``0-1`` or ``1/2-1/2``."""
        return "1/2-1/2" if self.winner is None else ("1-0" if self.winner else "0-1")


class InvalidMoveError(ValueError):
    """Raised when move notation is not syntactically valid"""


class IllegalMoveError(ValueError):
    """Raised when the attempted move is illegal in the current position"""


class AmbiguousMoveError(ValueError):
    """Raised when the attempted move is ambiguous in the current position"""


Square: TypeAlias = int
A1: Square = 0
B1: Square = 1
C1: Square = 2
D1: Square = 3
E1: Square = 4
F1: Square = 5
G1: Square = 6
H1: Square = 7
A2: Square = 8
B2: Square = 9
C2: Square = 10
D2: Square = 11
E2: Square = 12
F2: Square = 13
G2: Square = 14
H2: Square = 15
A3: Square = 16
B3: Square = 17
C3: Square = 18
D3: Square = 19
E3: Square = 20
F3: Square = 21
G3: Square = 22
H3: Square = 23
A4: Square = 24
B4: Square = 25
C4: Square = 26
D4: Square = 27
E4: Square = 28
F4: Square = 29
G4: Square = 30
H4: Square = 31
A5: Square = 32
B5: Square = 33
C5: Square = 34
D5: Square = 35
E5: Square = 36
F5: Square = 37
G5: Square = 38
H5: Square = 39
A6: Square = 40
B6: Square = 41
C6: Square = 42
D6: Square = 43
E6: Square = 44
F6: Square = 45
G6: Square = 46
H6: Square = 47
A7: Square = 48
B7: Square = 49
C7: Square = 50
D7: Square = 51
E7: Square = 52
F7: Square = 53
G7: Square = 54
H7: Square = 55
A8: Square = 56
B8: Square = 57
C8: Square = 58
D8: Square = 59
E8: Square = 60
F8: Square = 61
G8: Square = 62
H8: Square = 63
SQUARES: List[Square] = list(range(64))

SQUARE_NAMES = [f + r for r in RANK_NAMES for f in FILE_NAMES]

def parse_square(name: str) -> Square:
    """
    Gets the square index for the given square *name*
    (e.g., ``a1`` returns ``0``).

    :raises: :exc:`ValueError` if the square name is invalid.
    """
    return SQUARE_NAMES.index(name)

def square_name(square: Square) -> str:
    """Gets the name of the square, like ``a3``."""
    return SQUARE_NAMES[square]

def square(file_index: int, rank_index: int) -> Square:
    """Gets a square number by file and rank index."""
    return rank_index * 8 + file_index

def square_file(square: Square) -> int:
    """Gets the file index of the square where ``0`` is the a-file."""
    return square & 7

def square_rank(square: Square) -> int:
    """Gets the rank index of the square where ``0`` is the first rank."""
    return square >> 3

def square_distance(a: Square, b: Square) -> int:
    """
    Gets the Chebyshev distance (i.e., the number of king steps) from square *a* to *b*.
    """
    return max(abs(square_file(a) - square_file(b)), abs(square_rank(a) - square_rank(b)))

def square_manhattan_distance(a: Square, b: Square) -> int:
    """
    Gets the Manhattan/Taxicab distance (i.e., the number of orthogonal king steps) from square *a* to *b*.
    """
    return abs(square_file(a) - square_file(b)) + abs(square_rank(a) - square_rank(b))

def square_knight_distance(a: Square, b: Square) -> int:
    """
    Gets the Knight distance (i.e., the number of knight moves) from square *a* to *b*.
    """
    dx = abs(square_file(a) - square_file(b))
    dy = abs(square_rank(a) - square_rank(b))

    if dx + dy == 1:
        return 3
    elif dx == dy == 2:
        return 4
    elif dx == dy == 1:
        if BB_SQUARES[a] & BB_CORNERS or BB_SQUARES[b] & BB_CORNERS:  # Special case only for corner squares
            return 4

    m = math.ceil(max(dx / 2, dy / 2, (dx + dy) / 3))
    return m + ((m + dx + dy) % 2)

def square_mirror(square: Square) -> Square:
    """Mirrors the square vertically."""
    return square ^ 0x38

SQUARES_180: List[Square] = [square_mirror(sq) for sq in SQUARES]


Bitboard: TypeAlias = int
BB_EMPTY: Bitboard = 0
BB_ALL: Bitboard = 0xffff_ffff_ffff_ffff

BB_A1: Bitboard = 1 << A1
BB_B1: Bitboard = 1 << B1
BB_C1: Bitboard = 1 << C1
BB_D1: Bitboard = 1 << D1
BB_E1: Bitboard = 1 << E1
BB_F1: Bitboard = 1 << F1
BB_G1: Bitboard = 1 << G1
BB_H1: Bitboard = 1 << H1
BB_A2: Bitboard = 1 << A2
BB_B2: Bitboard = 1 << B2
BB_C2: Bitboard = 1 << C2
BB_D2: Bitboard = 1 << D2
BB_E2: Bitboard = 1 << E2
BB_F2: Bitboard = 1 << F2
BB_G2: Bitboard = 1 << G2
BB_H2: Bitboard = 1 << H2
BB_A3: Bitboard = 1 << A3
BB_B3: Bitboard = 1 << B3
BB_C3: Bitboard = 1 << C3
BB_D3: Bitboard = 1 << D3
BB_E3: Bitboard = 1 << E3
BB_F3: Bitboard = 1 << F3
BB_G3: Bitboard = 1 << G3
BB_H3: Bitboard = 1 << H3
BB_A4: Bitboard = 1 << A4
BB_B4: Bitboard = 1 << B4
BB_C4: Bitboard = 1 << C4
BB_D4: Bitboard = 1 << D4
BB_E4: Bitboard = 1 << E4
BB_F4: Bitboard = 1 << F4
BB_G4: Bitboard = 1 << G4
BB_H4: Bitboard = 1 << H4
BB_A5: Bitboard = 1 << A5
BB_B5: Bitboard = 1 << B5
BB_C5: Bitboard = 1 << C5
BB_D5: Bitboard = 1 << D5
BB_E5: Bitboard = 1 << E5
BB_F5: Bitboard = 1 << F5
BB_G5: Bitboard = 1 << G5
BB_H5: Bitboard = 1 << H5
BB_A6: Bitboard = 1 << A6
BB_B6: Bitboard = 1 << B6
BB_C6: Bitboard = 1 << C6
BB_D6: Bitboard = 1 << D6
BB_E6: Bitboard = 1 << E6
BB_F6: Bitboard = 1 << F6
BB_G6: Bitboard = 1 << G6
BB_H6: Bitboard = 1 << H6
BB_A7: Bitboard = 1 << A7
BB_B7: Bitboard = 1 << B7
BB_C7: Bitboard = 1 << C7
BB_D7: Bitboard = 1 << D7
BB_E7: Bitboard = 1 << E7
BB_F7: Bitboard = 1 << F7
BB_G7: Bitboard = 1 << G7
BB_H7: Bitboard = 1 << H7
BB_A8: Bitboard = 1 << A8
BB_B8: Bitboard = 1 << B8
BB_C8: Bitboard = 1 << C8
BB_D8: Bitboard = 1 << D8
BB_E8: Bitboard = 1 << E8
BB_F8: Bitboard = 1 << F8
BB_G8: Bitboard = 1 << G8
BB_H8: Bitboard = 1 << H8
BB_SQUARES: List[Bitboard] = [1 << sq for sq in SQUARES]

BB_CORNERS: Bitboard = BB_A1 | BB_H1 | BB_A8 | BB_H8
BB_CENTER: Bitboard = BB_D4 | BB_E4 | BB_D5 | BB_E5

BB_LIGHT_SQUARES: Bitboard = 0x55aa_55aa_55aa_55aa
BB_DARK_SQUARES: Bitboard = 0xaa55_aa55_aa55_aa55

BB_FILE_A: Bitboard = 0x0101_0101_0101_0101 << 0
BB_FILE_B: Bitboard = 0x0101_0101_0101_0101 << 1
BB_FILE_C: Bitboard = 0x0101_0101_0101_0101 << 2
BB_FILE_D: Bitboard = 0x0101_0101_0101_0101 << 3
BB_FILE_E: Bitboard = 0x0101_0101_0101_0101 << 4
BB_FILE_F: Bitboard = 0x0101_0101_0101_0101 << 5
BB_FILE_G: Bitboard = 0x0101_0101_0101_0101 << 6
BB_FILE_H: Bitboard = 0x0101_0101_0101_0101 << 7
BB_FILES: List[Bitboard] = [BB_FILE_A, BB_FILE_B, BB_FILE_C, BB_FILE_D, BB_FILE_E, BB_FILE_F, BB_FILE_G, BB_FILE_H]

BB_RANK_1: Bitboard = 0xff << (8 * 0)
BB_RANK_2: Bitboard = 0xff << (8 * 1)
BB_RANK_3: Bitboard = 0xff << (8 * 2)
BB_RANK_4: Bitboard = 0xff << (8 * 3)
BB_RANK_5: Bitboard = 0xff << (8 * 4)
BB_RANK_6: Bitboard = 0xff << (8 * 5)
BB_RANK_7: Bitboard = 0xff << (8 * 6)
BB_RANK_8: Bitboard = 0xff << (8 * 7)
BB_RANKS: List[Bitboard] = [BB_RANK_1, BB_RANK_2, BB_RANK_3, BB_RANK_4, BB_RANK_5, BB_RANK_6, BB_RANK_7, BB_RANK_8]

BB_BACKRANKS: Bitboard = BB_RANK_1 | BB_RANK_8


def lsb(bb: Bitboard) -> int:
    return (bb & -bb).bit_length() - 1

def scan_forward(bb: Bitboard) -> Iterator[Square]:
    while bb:
        r = bb & -bb
        yield r.bit_length() - 1
        bb ^= r

def msb(bb: Bitboard) -> int:
    return bb.bit_length() - 1

def scan_reversed(bb: Bitboard) -> Iterator[Square]:
    while bb:
        r = bb.bit_length() - 1
        yield r
        bb ^= BB_SQUARES[r]

# Python 3.10 or fallback.
popcount: Callable[[Bitboard], int] = getattr(int, "bit_count", lambda bb: bin(bb).count("1"))

def flip_vertical(bb: Bitboard) -> Bitboard:
    # https://www.chessprogramming.org/Flipping_Mirroring_and_Rotating#FlipVertically
    bb = ((bb >> 8) & 0x00ff_00ff_00ff_00ff) | ((bb & 0x00ff_00ff_00ff_00ff) << 8)
    bb = ((bb >> 16) & 0x0000_ffff_0000_ffff) | ((bb & 0x0000_ffff_0000_ffff) << 16)
    bb = (bb >> 32) | ((bb & 0x0000_0000_ffff_ffff) << 32)
    return bb

def flip_horizontal(bb: Bitboard) -> Bitboard:
    # https://www.chessprogramming.org/Flipping_Mirroring_and_Rotating#MirrorHorizontally
    bb = ((bb >> 1) & 0x5555_5555_5555_5555) | ((bb & 0x5555_5555_5555_5555) << 1)
    bb = ((bb >> 2) & 0x3333_3333_3333_3333) | ((bb & 0x3333_3333_3333_3333) << 2)
    bb = ((bb >> 4) & 0x0f0f_0f0f_0f0f_0f0f) | ((bb & 0x0f0f_0f0f_0f0f_0f0f) << 4)
    return bb

def flip_diagonal(bb: Bitboard) -> Bitboard:
    # https://www.chessprogramming.org/Flipping_Mirroring_and_Rotating#FlipabouttheDiagonal
    t = (bb ^ (bb << 28)) & 0x0f0f_0f0f_0000_0000
    bb = bb ^ t ^ (t >> 28)
    t = (bb ^ (bb << 14)) & 0x3333_0000_3333_0000
    bb = bb ^ t ^ (t >> 14)
    t = (bb ^ (bb << 7)) & 0x5500_5500_5500_5500
    bb = bb ^ t ^ (t >> 7)
    return bb

def flip_anti_diagonal(bb: Bitboard) -> Bitboard:
    # https://www.chessprogramming.org/Flipping_Mirroring_and_Rotating#FlipabouttheAntidiagonal
    t = bb ^ (bb << 36)
    bb = bb ^ ((t ^ (bb >> 36)) & 0xf0f0_f0f0_0f0f_0f0f)
    t = (bb ^ (bb << 18)) & 0xcccc_0000_cccc_0000
    bb = bb ^ t ^ (t >> 18)
    t = (bb ^ (bb << 9)) & 0xaa00_aa00_aa00_aa00
    bb = bb ^ t ^ (t >> 9)
    return bb


def shift_down(b: Bitboard) -> Bitboard:
    return b >> 8

def shift_2_down(b: Bitboard) -> Bitboard:
    return b >> 16

def shift_up(b: Bitboard) -> Bitboard:
    return (b << 8) & BB_ALL

def shift_2_up(b: Bitboard) -> Bitboard:
    return (b << 16) & BB_ALL

def shift_right(b: Bitboard) -> Bitboard:
    return (b << 1) & ~BB_FILE_A & BB_ALL

def shift_2_right(b: Bitboard) -> Bitboard:
    return (b << 2) & ~BB_FILE_A & ~BB_FILE_B & BB_ALL

def shift_left(b: Bitboard) -> Bitboard:
    return (b >> 1) & ~BB_FILE_H

def shift_2_left(b: Bitboard) -> Bitboard:
    return (b >> 2) & ~BB_FILE_G & ~BB_FILE_H

def shift_up_left(b: Bitboard) -> Bitboard:
    return (b << 7) & ~BB_FILE_H & BB_ALL

def shift_up_right(b: Bitboard) -> Bitboard:
    return (b << 9) & ~BB_FILE_A & BB_ALL

def shift_down_left(b: Bitboard) -> Bitboard:
    return (b >> 9) & ~BB_FILE_H

def shift_down_right(b: Bitboard) -> Bitboard:
    return (b >> 7) & ~BB_FILE_A


def _sliding_attacks(square: Square, occupied: Bitboard, deltas: Iterable[int]) -> Bitboard:
    attacks = BB_EMPTY

    for delta in deltas:
        sq = square

        while True:
            sq += delta
            if not (0 <= sq < 64) or square_distance(sq, sq - delta) > 2:
                break

            attacks |= BB_SQUARES[sq]

            if occupied & BB_SQUARES[sq]:
                break

    return attacks

def _step_attacks(square: Square, deltas: Iterable[int]) -> Bitboard:
    return _sliding_attacks(square, BB_ALL, deltas)

BB_KNIGHT_ATTACKS: List[Bitboard] = [_step_attacks(sq, [17, 15, 10, 6, -17, -15, -10, -6]) for sq in SQUARES]
BB_KING_ATTACKS: List[Bitboard] = [_step_attacks(sq, [9, 8, 7, 1, -9, -8, -7, -1]) for sq in SQUARES]
BB_PAWN_ATTACKS: List[List[Bitboard]] = [[_step_attacks(sq, deltas) for sq in SQUARES] for deltas in [[-7, -9], [7, 9]]]


def _edges(square: Square) -> Bitboard:
    return (((BB_RANK_1 | BB_RANK_8) & ~BB_RANKS[square_rank(square)]) |
            ((BB_FILE_A | BB_FILE_H) & ~BB_FILES[square_file(square)]))

def _carry_rippler(mask: Bitboard) -> Iterator[Bitboard]:
    # Carry-Rippler trick to iterate subsets of mask.
    subset = BB_EMPTY
    while True:
        yield subset
        subset = (subset - mask) & mask
        if not subset:
            break

def _attack_table(deltas: List[int]) -> Tuple[List[Bitboard], List[Dict[Bitboard, Bitboard]]]:
    mask_table: List[Bitboard] = []
    attack_table: List[Dict[Bitboard, Bitboard]] = []

    for square in SQUARES:
        attacks = {}

        mask = _sliding_attacks(square, 0, deltas) & ~_edges(square)
        for subset in _carry_rippler(mask):
            attacks[subset] = _sliding_attacks(square, subset, deltas)

        attack_table.append(attacks)
        mask_table.append(mask)

    return mask_table, attack_table

BB_DIAG_MASKS, BB_DIAG_ATTACKS = _attack_table([-9, -7, 7, 9])
BB_FILE_MASKS, BB_FILE_ATTACKS = _attack_table([-8, 8])
BB_RANK_MASKS, BB_RANK_ATTACKS = _attack_table([-1, 1])


def _rays() -> List[List[Bitboard]]:
    rays: List[List[Bitboard]] = []
    for a, bb_a in enumerate(BB_SQUARES):
        rays_row: List[Bitboard] = []
        for b, bb_b in enumerate(BB_SQUARES):
            if BB_DIAG_ATTACKS[a][0] & bb_b:
                rays_row.append((BB_DIAG_ATTACKS[a][0] & BB_DIAG_ATTACKS[b][0]) | bb_a | bb_b)
            elif BB_RANK_ATTACKS[a][0] & bb_b:
                rays_row.append(BB_RANK_ATTACKS[a][0] | bb_a)
            elif BB_FILE_ATTACKS[a][0] & bb_b:
                rays_row.append(BB_FILE_ATTACKS[a][0] | bb_a)
            else:
                rays_row.append(BB_EMPTY)
        rays.append(rays_row)
    return rays

BB_RAYS = _rays()

def ray(a: Square, b: Square) -> Bitboard:
    return BB_RAYS[a][b]

def between(a: Square, b: Square) -> Bitboard:
    bb = BB_RAYS[a][b] & ((BB_ALL << a) ^ (BB_ALL << b))
    return bb & (bb - 1)


SAN_REGEX = re.compile(r"^([NBKRQ])?([a-h])?([1-8])?[\-x]?([a-h][1-8])(=?[nbrqkNBRQK])?[\+#]?\Z")

FEN_CASTLING_REGEX = re.compile(r"^(?:-|[KQABCDEFGH]{0,2}[kqabcdefgh]{0,2})\Z")


@dataclasses.dataclass
class Piece:
    """A piece with type and color."""

    piece_type: PieceType
    """The piece type."""

    color: Color
    """The piece color."""

    def symbol(self) -> str:
        """
        Gets the symbol ``P``, ``N``, ``B``, ``R``, ``Q`` or ``K`` for white
        pieces or the lower-case variants for the black pieces.
        """
        symbol = piece_symbol(self.piece_type)
        return symbol.upper() if self.color else symbol

    def unicode_symbol(self, *, invert_color: bool = False) -> str:
        """
        Gets the Unicode character for the piece.
        """
        symbol = self.symbol().swapcase() if invert_color else self.symbol()
        return UNICODE_PIECE_SYMBOLS[symbol]

    def __hash__(self) -> int:
        return self.piece_type + (-1 if self.color else 5)

    def __repr__(self) -> str:
        return f"Piece.from_symbol({self.symbol()!r})"

    def __str__(self) -> str:
        return self.symbol()

    def _repr_svg_(self) -> str:
        import chess.svg
        return chess.svg.piece(self, size=45)

    @classmethod
    def from_symbol(cls, symbol: str) -> Piece:
        """
        Creates a :class:`~chess.Piece` instance from a piece symbol.

        :raises: :exc:`ValueError` if the symbol is invalid.
        """
        return cls(PIECE_SYMBOLS.index(symbol.lower()), symbol.isupper())


@dataclasses.dataclass(unsafe_hash=True)
class Move:
    """
    Represents a move from a square to a square and possibly the promotion
    piece type.

    Drops and null moves are supported.
    """

    from_square: Square
    """The source square."""

    to_square: Square
    """The target square."""

    promotion: Optional[PieceType] = None
    """The promotion piece type or ``None``."""

    drop: Optional[PieceType] = None
    """The drop piece type or ``None``."""

    def uci(self) -> str:
        """
        Gets a UCI string for the move.

        For example, a move from a7 to a8 would be ``a7a8`` or ``a7a8q``
        (if the latter is a promotion to a queen).

        The UCI representation of a null move is ``0000``.
        """
        if self.drop:
            return piece_symbol(self.drop).upper() + "@" + SQUARE_NAMES[self.to_square]
        elif self.promotion:
            return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square] + piece_symbol(self.promotion)
        elif self:
            return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square]
        else:
            return "0000"

    def xboard(self) -> str:
        return self.uci() if self else "@@@@"

    def __bool__(self) -> bool:
        return bool(self.from_square or self.to_square or self.promotion or self.drop)

    def __repr__(self) -> str:
        return f"Move.from_uci({self.uci()!r})"

    def __str__(self) -> str:
        return self.uci()

    @classmethod
    def from_uci(cls, uci: str) -> Move:
        """
        Parses a UCI string.

        :raises: :exc:`InvalidMoveError` if the UCI string is invalid.
        """
        if uci == "0000":
            return cls.null()
        elif len(uci) == 4 and "@" == uci[1]:
            try:
                drop = PIECE_SYMBOLS.index(uci[0].lower())
                square = SQUARE_NAMES.index(uci[2:])
            except ValueError:
                raise InvalidMoveError(f"invalid uci: {uci!r}")
            return cls(square, square, drop=drop)
        elif 4 <= len(uci) <= 5:
            try:
                from_square = SQUARE_NAMES.index(uci[0:2])
                to_square = SQUARE_NAMES.index(uci[2:4])
                promotion = PIECE_SYMBOLS.index(uci[4]) if len(uci) == 5 else None
            except ValueError:
                raise InvalidMoveError(f"invalid uci: {uci!r}")
            if from_square == to_square:
                raise InvalidMoveError(f"invalid uci (use 0000 for null moves): {uci!r}")
            return cls(from_square, to_square, promotion=promotion)
        else:
            raise InvalidMoveError(f"expected uci string to be of length 4 or 5: {uci!r}")

    @classmethod
    def null(cls) -> Move:
        """
        Gets a null move.

        A null move just passes the turn to the other side (and possibly
        forfeits en passant capturing). Null moves evaluate to ``False`` in
        boolean contexts.

        >>> import chess
        >>>
        >>> bool(chess.Move.null())
        False
        """
        return cls(0, 0)


BaseBoardT = TypeVar("BaseBoardT", bound="BaseBoard")

class BaseBoard:
    """
    A board representing the position of chess pieces. See
    :class:`~chess.Board` for a full board with move generation.

    The board is initialized with the standard chess starting position, unless
    otherwise specified in the optional *board_fen* argument. If *board_fen*
    is ``None``, an empty board is created.
    """

    def __init__(self, board_fen: Optional[str] = STARTING_BOARD_FEN) -> None:
        self.occupied_co = [BB_EMPTY, BB_EMPTY]

        if board_fen is None:
            self._clear_board()
        elif board_fen == STARTING_BOARD_FEN:
            self._reset_board()
        else:
            self._set_board_fen(board_fen)

    def _reset_board(self) -> None:
        self.pawns = BB_RANK_2 | BB_RANK_7
        self.knights = BB_B1 | BB_G1 | BB_B8 | BB_G8
        self.bishops = BB_C1 | BB_F1 | BB_C8 | BB_F8
        self.rooks = BB_CORNERS
        self.queens = BB_D1 | BB_D8
        self.kings = BB_E1 | BB_E8

        self.promoted = BB_EMPTY

        self.occupied_co[WHITE] = BB_RANK_1 | BB_RANK_2
        self.occupied_co[BLACK] = BB_RANK_7 | BB_RANK_8
        self.occupied = BB_RANK_1 | BB_RANK_2 | BB_RANK_7 | BB_RANK_8

    def reset_board(self) -> None:
        """
        Resets pieces to the starting position.

        :class:`~chess.Board` also resets the move stack, but not turn,
        castling rights and move counters. Use :func:`chess.Board.reset()` to
        fully restore the starting position.
        """
        self._reset_board()

    def _clear_board(self) -> None:
        self.pawns = BB_EMPTY
        self.knights = BB_EMPTY
        self.bishops = BB_EMPTY
        self.rooks = BB_EMPTY
        self.queens = BB_EMPTY
        self.kings = BB_EMPTY

        self.promoted = BB_EMPTY

        self.occupied_co[WHITE] = BB_EMPTY
        self.occupied_co[BLACK] = BB_EMPTY
        self.occupied = BB_EMPTY

    def clear_board(self) -> None:
        """
        Clears the board.

        :class:`~chess.Board` also clears the move stack.
        """
        self._clear_board()

    def pieces_mask(self, piece_type: PieceType, color: Color) -> Bitboard:
        if piece_type == PAWN:
            bb = self.pawns
        elif piece_type == KNIGHT:
            bb = self.knights
        elif piece_type == BISHOP:
            bb = self.bishops
        elif piece_type == ROOK:
            bb = self.rooks
        elif piece_type == QUEEN:
            bb = self.queens
        elif piece_type == KING:
            bb = self.kings
        else:
            assert False, f"expected PieceType, got {piece_type!r}"

        return bb & self.occupied_co[color]

    def pieces(self, piece_type: PieceType, color: Color) -> SquareSet:
        """
        Gets pieces of the given type and color.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.pieces_mask(piece_type, color))

    def piece_at(self, square: Square) -> Optional[Piece]:
        """Gets the :class:`piece <chess.Piece>` at the given square."""
        piece_type = self.piece_type_at(square)
        if piece_type:
            mask = BB_SQUARES[square]
            color = bool(self.occupied_co[WHITE] & mask)
            return Piece(piece_type, color)
        else:
            return None

    def piece_type_at(self, square: Square) -> Optional[PieceType]:
        """Gets the piece type at the given square."""
        mask = BB_SQUARES[square]

        if not self.occupied & mask:
            return None  # Early return
        elif self.pawns & mask:
            return PAWN
        elif self.knights & mask:
            return KNIGHT
        elif self.bishops & mask:
            return BISHOP
        elif self.rooks & mask:
            return ROOK
        elif self.queens & mask:
            return QUEEN
        else:
            return KING

    def color_at(self, square: Square) -> Optional[Color]:
        """Gets the color of the piece at the given square."""
        mask = BB_SQUARES[square]
        if self.occupied_co[WHITE] & mask:
            return WHITE
        elif self.occupied_co[BLACK] & mask:
            return BLACK
        else:
            return None

    def king(self, color: Color) -> Optional[Square]:
        """
        Finds the king square of the given side. Returns ``None`` if there
        is no king of that color.

        In variants with king promotions, only non-promoted kings are
        considered.
        """
        king_mask = self.occupied_co[color] & self.kings & ~self.promoted
        return msb(king_mask) if king_mask else None

    def attacks_mask(self, square: Square) -> Bitboard:
        bb_square = BB_SQUARES[square]

        if bb_square & self.pawns:
            color = bool(bb_square & self.occupied_co[WHITE])
            return BB_PAWN_ATTACKS[color][square]
        elif bb_square & self.knights:
            return BB_KNIGHT_ATTACKS[square]
        elif bb_square & self.kings:
            return BB_KING_ATTACKS[square]
        else:
            attacks = 0
            if bb_square & self.bishops or bb_square & self.queens:
                attacks = BB_DIAG_ATTACKS[square][BB_DIAG_MASKS[square] & self.occupied]
            if bb_square & self.rooks or bb_square & self.queens:
                attacks |= (BB_RANK_ATTACKS[square][BB_RANK_MASKS[square] & self.occupied] |
                            BB_FILE_ATTACKS[square][BB_FILE_MASKS[square] & self.occupied])
            return attacks

    def attacks(self, square: Square) -> SquareSet:
        """
        Gets the set of attacked squares from the given square.

        There will be no attacks if the square is empty. Pinned pieces are
        still attacking other squares.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.attacks_mask(square))

    def attackers_mask(self, color: Color, square: Square, occupied: Optional[Bitboard] = None) -> Bitboard:
        occupied = self.occupied if occupied is None else occupied

        rank_pieces = BB_RANK_MASKS[square] & occupied
        file_pieces = BB_FILE_MASKS[square] & occupied
        diag_pieces = BB_DIAG_MASKS[square] & occupied

        queens_and_rooks = self.queens | self.rooks
        queens_and_bishops = self.queens | self.bishops

        attackers = (
            (BB_KING_ATTACKS[square] & self.kings) |
            (BB_KNIGHT_ATTACKS[square] & self.knights) |
            (BB_RANK_ATTACKS[square][rank_pieces] & queens_and_rooks) |
            (BB_FILE_ATTACKS[square][file_pieces] & queens_and_rooks) |
            (BB_DIAG_ATTACKS[square][diag_pieces] & queens_and_bishops) |
            (BB_PAWN_ATTACKS[not color][square] & self.pawns))

        return attackers & self.occupied_co[color]

    def is_attacked_by(self, color: Color, square: Square, occupied: Optional[IntoSquareSet] = None) -> bool:
        """
        Checks if the given side attacks the given square.

        Pinned pieces still count as attackers. Pawns that can be captured
        en passant are **not** considered attacked.

        *occupied* determines which squares are considered to block attacks.
        For example,
        ``board.occupied ^ board.pieces_mask(chess.KING, board.turn)`` can be
        used to consider X-ray attacks through the king.
        Defaults to ``board.occupied`` (all pieces including the king,
        no X-ray attacks).
        """
        return bool(self.attackers_mask(color, square, None if occupied is None else SquareSet(occupied).mask))

    def attackers(self, color: Color, square: Square, occupied: Optional[IntoSquareSet] = None) -> SquareSet:
        """
        Gets the set of attackers of the given color for the given square.

        Pinned pieces still count as attackers.

        *occupied* determines which squares are considered to block attacks.
        For example,
        ``board.occupied ^ board.pieces_mask(chess.KING, board.turn)`` can be
        used to consider X-ray attacks through the king.
        Defaults to ``board.occupied`` (all pieces including the king,
        no X-ray attacks).

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.attackers_mask(color, square, None if occupied is None else SquareSet(occupied).mask))

    def pin_mask(self, color: Color, square: Square) -> Bitboard:
        king = self.king(color)
        if king is None:
            return BB_ALL

        square_mask = BB_SQUARES[square]

        for attacks, sliders in [(BB_FILE_ATTACKS, self.rooks | self.queens),
                                 (BB_RANK_ATTACKS, self.rooks | self.queens),
                                 (BB_DIAG_ATTACKS, self.bishops | self.queens)]:
            rays = attacks[king][0]
            if rays & square_mask:
                snipers = rays & sliders & self.occupied_co[not color]
                for sniper in scan_reversed(snipers):
                    if between(sniper, king) & (self.occupied | square_mask) == square_mask:
                        return ray(king, sniper)

                break

        return BB_ALL

    def pin(self, color: Color, square: Square) -> SquareSet:
        """
        Detects an absolute pin (and its direction) of the given square to
        the king of the given color.

        >>> import chess
        >>>
        >>> board = chess.Board("rnb1k2r/ppp2ppp/5n2/3q4/1b1P4/2N5/PP3PPP/R1BQKBNR w KQkq - 3 7")
        >>> board.is_pinned(chess.WHITE, chess.C3)
        True
        >>> direction = board.pin(chess.WHITE, chess.C3)
        >>> direction
        SquareSet(0x0000_0001_0204_0810)
        >>> print(direction)
        . . . . . . . .
        . . . . . . . .
        . . . . . . . .
        1 . . . . . . .
        . 1 . . . . . .
        . . 1 . . . . .
        . . . 1 . . . .
        . . . . 1 . . .

        Returns a :class:`set of squares <chess.SquareSet>` that mask the rank,
        file or diagonal of the pin. If there is no pin, then a mask of the
        entire board is returned.
        """
        return SquareSet(self.pin_mask(color, square))

    def is_pinned(self, color: Color, square: Square) -> bool:
        """
        Detects if the given square is pinned to the king of the given color.
        """
        return self.pin_mask(color, square) != BB_ALL

    def _remove_piece_at(self, square: Square) -> Optional[PieceType]:
        piece_type = self.piece_type_at(square)
        mask = BB_SQUARES[square]

        if piece_type == PAWN:
            self.pawns ^= mask
        elif piece_type == KNIGHT:
            self.knights ^= mask
        elif piece_type == BISHOP:
            self.bishops ^= mask
        elif piece_type == ROOK:
            self.rooks ^= mask
        elif piece_type == QUEEN:
            self.queens ^= mask
        elif piece_type == KING:
            self.kings ^= mask
        else:
            return None

        self.occupied ^= mask
        self.occupied_co[WHITE] &= ~mask
        self.occupied_co[BLACK] &= ~mask

        self.promoted &= ~mask

        return piece_type

    def remove_piece_at(self, square: Square) -> Optional[Piece]:
        """
        Removes the piece from the given square. Returns the
        :class:`~chess.Piece` or ``None`` if the square was already empty.

        :class:`~chess.Board` also clears the move stack.
        """
        color = bool(self.occupied_co[WHITE] & BB_SQUARES[square])
        piece_type = self._remove_piece_at(square)
        return Piece(piece_type, color) if piece_type else None

    def _set_piece_at(self, square: Square, piece_type: PieceType, color: Color, promoted: bool = False) -> None:
        self._remove_piece_at(square)

        mask = BB_SQUARES[square]

        if piece_type == PAWN:
            self.pawns |= mask
        elif piece_type == KNIGHT:
            self.knights |= mask
        elif piece_type == BISHOP:
            self.bishops |= mask
        elif piece_type == ROOK:
            self.rooks |= mask
        elif piece_type == QUEEN:
            self.queens |= mask
        elif piece_type == KING:
            self.kings |= mask
        else:
            return

        self.occupied ^= mask
        self.occupied_co[color] ^= mask

        if promoted:
            self.promoted ^= mask

    def set_piece_at(self, square: Square, piece: Optional[Piece], promoted: bool = False) -> None:
        """
        Sets a piece at the given square.

        An existing piece is replaced. Setting *piece* to ``None`` is
        equivalent to :func:`~chess.Board.remove_piece_at()`.

        :class:`~chess.Board` also clears the move stack.
        """
        if piece is None:
            self._remove_piece_at(square)
        else:
            self._set_piece_at(square, piece.piece_type, piece.color, promoted)

    def board_fen(self, *, promoted: Optional[bool] = False) -> str:
        """
        Gets the board FEN (e.g.,
        ``rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR``).
        """
        builder: List[str] = []
        empty = 0

        for square in SQUARES_180:
            piece = self.piece_at(square)

            if not piece:
                empty += 1
            else:
                if empty:
                    builder.append(str(empty))
                    empty = 0
                builder.append(piece.symbol())
                if promoted and BB_SQUARES[square] & self.promoted:
                    builder.append("~")

            if BB_SQUARES[square] & BB_FILE_H:
                if empty:
                    builder.append(str(empty))
                    empty = 0

                if square != H1:
                    builder.append("/")

        return "".join(builder)

    def _set_board_fen(self, fen: str) -> None:
        # Compatibility with set_fen().
        fen = fen.strip()
        if " " in fen:
            raise ValueError(f"expected position part of fen, got multiple parts: {fen!r}")

        # Ensure the FEN is valid.
        rows = fen.split("/")
        if len(rows) != 8:
            raise ValueError(f"expected 8 rows in position part of fen: {fen!r}")

        # Validate each row.
        for row in rows:
            field_sum = 0
            previous_was_digit = False
            previous_was_piece = False

            for c in row:
                if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                    if previous_was_digit:
                        raise ValueError(f"two subsequent digits in position part of fen: {fen!r}")
                    field_sum += int(c)
                    previous_was_digit = True
                    previous_was_piece = False
                elif c == "~":
                    if not previous_was_piece:
                        raise ValueError(f"'~' not after piece in position part of fen: {fen!r}")
                    previous_was_digit = False
                    previous_was_piece = False
                elif c.lower() in PIECE_SYMBOLS:
                    field_sum += 1
                    previous_was_digit = False
                    previous_was_piece = True
                else:
                    raise ValueError(f"invalid character in position part of fen: {fen!r}")

            if field_sum != 8:
                raise ValueError(f"expected 8 columns per row in position part of fen: {fen!r}")

        # Clear the board.
        self._clear_board()

        # Put pieces on the board.
        square_index = 0
        for c in fen:
            if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                square_index += int(c)
            elif c.lower() in PIECE_SYMBOLS:
                piece = Piece.from_symbol(c)
                self._set_piece_at(SQUARES_180[square_index], piece.piece_type, piece.color)
                square_index += 1
            elif c == "~":
                self.promoted |= BB_SQUARES[SQUARES_180[square_index - 1]]

    def set_board_fen(self, fen: str) -> None:
        """
        Parses *fen* and sets up the board, where *fen* is the board part of
        a FEN.

        :class:`~chess.Board` also clears the move stack.

        :raises: :exc:`ValueError` if syntactically invalid.
        """
        self._set_board_fen(fen)

    def piece_map(self, *, mask: Bitboard = BB_ALL) -> Dict[Square, Piece]:
        """
        Gets a dictionary of :class:`pieces <chess.Piece>` by square index.
        """
        result: Dict[Square, Piece] = {}
        for square in scan_reversed(self.occupied & mask):
            result[square] = typing.cast(Piece, self.piece_at(square))
        return result

    def _set_piece_map(self, pieces: Mapping[Square, Piece]) -> None:
        self._clear_board()
        for square, piece in pieces.items():
            self._set_piece_at(square, piece.piece_type, piece.color)

    def set_piece_map(self, pieces: Mapping[Square, Piece]) -> None:
        """
        Sets up the board from a dictionary of :class:`pieces <chess.Piece>`
        by square index.

        :class:`~chess.Board` also clears the move stack.
        """
        self._set_piece_map(pieces)

    def _set_chess960_pos(self, scharnagl: int) -> None:
        if not 0 <= scharnagl <= 959:
            raise ValueError(f"chess960 position index not 0 <= {scharnagl!r} <= 959")

        # See http://www.russellcottrell.com/Chess/Chess960.htm for
        # a description of the algorithm.
        n, bw = divmod(scharnagl, 4)
        n, bb = divmod(n, 4)
        n, q = divmod(n, 6)

        for n1 in range(0, 4):
            n2 = n + (3 - n1) * (4 - n1) // 2 - 5
            if n1 < n2 and 1 <= n2 <= 4:
                break

        # Bishops.
        bw_file = bw * 2 + 1
        bb_file = bb * 2
        self.bishops = (BB_FILES[bw_file] | BB_FILES[bb_file]) & BB_BACKRANKS

        # Queens.
        q_file = q
        q_file += int(min(bw_file, bb_file) <= q_file)
        q_file += int(max(bw_file, bb_file) <= q_file)
        self.queens = BB_FILES[q_file] & BB_BACKRANKS

        used = [bw_file, bb_file, q_file]

        # Knights.
        self.knights = BB_EMPTY
        for i in range(0, 8):
            if i not in used:
                if n1 == 0 or n2 == 0:
                    self.knights |= BB_FILES[i] & BB_BACKRANKS
                    used.append(i)
                n1 -= 1
                n2 -= 1

        # RKR.
        for i in range(0, 8):
            if i not in used:
                self.rooks = BB_FILES[i] & BB_BACKRANKS
                used.append(i)
                break
        for i in range(1, 8):
            if i not in used:
                self.kings = BB_FILES[i] & BB_BACKRANKS
                used.append(i)
                break
        for i in range(2, 8):
            if i not in used:
                self.rooks |= BB_FILES[i] & BB_BACKRANKS
                break

        # Finalize.
        self.pawns = BB_RANK_2 | BB_RANK_7
        self.occupied_co[WHITE] = BB_RANK_1 | BB_RANK_2
        self.occupied_co[BLACK] = BB_RANK_7 | BB_RANK_8
        self.occupied = BB_RANK_1 | BB_RANK_2 | BB_RANK_7 | BB_RANK_8
        self.promoted = BB_EMPTY

    def set_chess960_pos(self, scharnagl: int) -> None:
        """
        Sets up a Chess960 starting position given its index between 0 and 959.
        Also see :func:`~chess.BaseBoard.from_chess960_pos()`.
        """
        self._set_chess960_pos(scharnagl)

    def chess960_pos(self) -> Optional[int]:
        """
        Gets the Chess960 starting position index between 0 and 959,
        or ``None``.
        """
        if self.occupied_co[WHITE] != BB_RANK_1 | BB_RANK_2:
            return None
        if self.occupied_co[BLACK] != BB_RANK_7 | BB_RANK_8:
            return None
        if self.pawns != BB_RANK_2 | BB_RANK_7:
            return None
        if self.promoted:
            return None

        # Piece counts.
        brnqk = [self.bishops, self.rooks, self.knights, self.queens, self.kings]
        if [popcount(pieces) for pieces in brnqk] != [4, 4, 4, 2, 2]:
            return None

        # Symmetry.
        if any((BB_RANK_1 & pieces) << 56 != BB_RANK_8 & pieces for pieces in brnqk):
            return None

        # Algorithm from ChessX, src/database/bitboard.cpp, r2254.
        x = self.bishops & (2 + 8 + 32 + 128)
        if not x:
            return None
        bs1 = (lsb(x) - 1) // 2
        cc_pos = bs1
        x = self.bishops & (1 + 4 + 16 + 64)
        if not x:
            return None
        bs2 = lsb(x) * 2
        cc_pos += bs2

        q = 0
        qf = False
        n0 = 0
        n1 = 0
        n0f = False
        n1f = False
        rf = 0
        n0s = [0, 4, 7, 9]
        for square in range(A1, H1 + 1):
            bb = BB_SQUARES[square]
            if bb & self.queens:
                qf = True
            elif bb & self.rooks or bb & self.kings:
                if bb & self.kings:
                    if rf != 1:
                        return None
                else:
                    rf += 1

                if not qf:
                    q += 1

                if not n0f:
                    n0 += 1
                elif not n1f:
                    n1 += 1
            elif bb & self.knights:
                if not qf:
                    q += 1

                if not n0f:
                    n0f = True
                elif not n1f:
                    n1f = True

        if n0 < 4 and n1f and qf:
            cc_pos += q * 16
            krn = n0s[n0] + n1
            cc_pos += krn * 96
            return cc_pos
        else:
            return None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.board_fen()!r})"

    def __str__(self) -> str:
        builder: List[str] = []

        for square in SQUARES_180:
            piece = self.piece_at(square)

            if piece:
                builder.append(piece.symbol())
            else:
                builder.append(".")

            if BB_SQUARES[square] & BB_FILE_H:
                if square != H1:
                    builder.append("\n")
            else:
                builder.append(" ")

        return "".join(builder)

    def unicode(self, *, invert_color: bool = False, borders: bool = False, empty_square: str = "⭘", orientation: Color = WHITE) -> str:
        """
        Returns a string representation of the board with Unicode pieces.
        Useful for pretty-printing to a terminal.

        :param invert_color: Invert color of the Unicode pieces.
        :param borders: Show borders and a coordinate margin.
        """
        builder: List[str] = []
        for rank_index in (range(7, -1, -1) if orientation else range(8)):
            if borders:
                builder.append("  ")
                builder.append("-" * 17)
                builder.append("\n")

                builder.append(RANK_NAMES[rank_index])
                builder.append(" ")

            for i, file_index in enumerate(range(8) if orientation else range(7, -1, -1)):
                square_index = square(file_index, rank_index)

                if borders:
                    builder.append("|")
                elif i > 0:
                    builder.append(" ")

                piece = self.piece_at(square_index)

                if piece:
                    builder.append(piece.unicode_symbol(invert_color=invert_color))
                else:
                    builder.append(empty_square)

            if borders:
                builder.append("|")

            if borders or (rank_index > 0 if orientation else rank_index < 7):
                builder.append("\n")

        if borders:
            builder.append("  ")
            builder.append("-" * 17)
            builder.append("\n")
            letters = "a b c d e f g h" if orientation else "h g f e d c b a"
            builder.append("   " + letters)

        return "".join(builder)

    def _repr_svg_(self) -> str:
        import chess.svg
        return chess.svg.board(board=self, size=400)

    def __eq__(self, board: object) -> bool:
        if isinstance(board, BaseBoard):
            return (
                self.occupied == board.occupied and
                self.occupied_co[WHITE] == board.occupied_co[WHITE] and
                self.pawns == board.pawns and
                self.knights == board.knights and
                self.bishops == board.bishops and
                self.rooks == board.rooks and
                self.queens == board.queens and
                self.kings == board.kings)
        else:
            return NotImplemented

    def apply_transform(self, f: Callable[[Bitboard], Bitboard]) -> None:
        self.pawns = f(self.pawns)
        self.knights = f(self.knights)
        self.bishops = f(self.bishops)
        self.rooks = f(self.rooks)
        self.queens = f(self.queens)
        self.kings = f(self.kings)

        self.occupied_co[WHITE] = f(self.occupied_co[WHITE])
        self.occupied_co[BLACK] = f(self.occupied_co[BLACK])
        self.occupied = f(self.occupied)
        self.promoted = f(self.promoted)

    def transform(self, f: Callable[[Bitboard], Bitboard]) -> Self:
        """
        Returns a transformed copy of the board (without move stack)
        by applying a bitboard transformation function.

        Available transformations include :func:`chess.flip_vertical()`,
        :func:`chess.flip_horizontal()`, :func:`chess.flip_diagonal()`,
        :func:`chess.flip_anti_diagonal()`, :func:`chess.shift_down()`,
        :func:`chess.shift_up()`, :func:`chess.shift_left()`, and
        :func:`chess.shift_right()`.

        Alternatively, :func:`~chess.BaseBoard.apply_transform()` can be used
        to apply the transformation on the board.
        """
        board = self.copy()
        board.apply_transform(f)
        return board

    def apply_mirror(self) -> None:
        self.apply_transform(flip_vertical)
        self.occupied_co[WHITE], self.occupied_co[BLACK] = self.occupied_co[BLACK], self.occupied_co[WHITE]

    def mirror(self) -> Self:
        """
        Returns a mirrored copy of the board (without move stack).

        The board is mirrored vertically and piece colors are swapped, so that
        the position is equivalent modulo color.

        Alternatively, :func:`~chess.BaseBoard.apply_mirror()` can be used
        to mirror the board.
        """
        board = self.copy()
        board.apply_mirror()
        return board

    def copy(self) -> Self:
        """Creates a copy of the board."""
        board = type(self)(None)

        board.pawns = self.pawns
        board.knights = self.knights
        board.bishops = self.bishops
        board.rooks = self.rooks
        board.queens = self.queens
        board.kings = self.kings

        board.occupied_co[WHITE] = self.occupied_co[WHITE]
        board.occupied_co[BLACK] = self.occupied_co[BLACK]
        board.occupied = self.occupied
        board.promoted = self.promoted

        return board

    def __copy__(self) -> Self:
        return self.copy()

    def __deepcopy__(self, memo: Dict[int, object]) -> Self:
        board = self.copy()
        memo[id(self)] = board
        return board

    @classmethod
    def empty(cls: Type[BaseBoardT]) -> BaseBoardT:
        """
        Creates a new empty board. Also see
        :func:`~chess.BaseBoard.clear_board()`.
        """
        return cls(None)

    @classmethod
    def from_chess960_pos(cls: Type[BaseBoardT], scharnagl: int) -> BaseBoardT:
        """
        Creates a new board, initialized with a Chess960 starting position.

        >>> import chess
        >>> import random
        >>>
        >>> board = chess.Board.from_chess960_pos(random.randint(0, 959))
        """
        board = cls.empty()
        board.set_chess960_pos(scharnagl)
        return board


BoardT = TypeVar("BoardT", bound="Board")

class _BoardState:

    def __init__(self, board: Board) -> None:
        self.pawns = board.pawns
        self.knights = board.knights
        self.bishops = board.bishops
        self.rooks = board.rooks
        self.queens = board.queens
        self.kings = board.kings

        self.occupied_w = board.occupied_co[WHITE]
        self.occupied_b = board.occupied_co[BLACK]
        self.occupied = board.occupied

        self.promoted = board.promoted

        self.turn = board.turn
        self.castling_rights = board.castling_rights
        self.ep_square = board.ep_square
        self.halfmove_clock = board.halfmove_clock
        self.fullmove_number = board.fullmove_number

    def restore(self, board: Board) -> None:
        board.pawns = self.pawns
        board.knights = self.knights
        board.bishops = self.bishops
        board.rooks = self.rooks
        board.queens = self.queens
        board.kings = self.kings

        board.occupied_co[WHITE] = self.occupied_w
        board.occupied_co[BLACK] = self.occupied_b
        board.occupied = self.occupied

        board.promoted = self.promoted

        board.turn = self.turn
        board.castling_rights = self.castling_rights
        board.ep_square = self.ep_square
        board.halfmove_clock = self.halfmove_clock
        board.fullmove_number = self.fullmove_number

class Board(BaseBoard):
    """
    A :class:`~chess.BaseBoard`, additional information representing
    a chess position, and a :data:`move stack <chess.Board.move_stack>`.

    Provides :data:`move generation <chess.Board.legal_moves>`, validation,
    :func:`parsing <chess.Board.parse_san()>`, attack generation,
    :func:`game end detection <chess.Board.is_game_over()>`,
    and the capability to :func:`make <chess.Board.push()>` and
    :func:`unmake <chess.Board.pop()>` moves.

    The board is initialized to the standard chess starting position,
    unless otherwise specified in the optional *fen* argument.
    If *fen* is ``None``, an empty board is created.

    Optionally supports *chess960*. In Chess960, castling moves are encoded
    by a king move to the corresponding rook square.
    Use :func:`chess.Board.from_chess960_pos()` to create a board with one
    of the Chess960 starting positions.

    It's safe to set :data:`~Board.turn`, :data:`~Board.castling_rights`,
    :data:`~Board.ep_square`, :data:`~Board.halfmove_clock` and
    :data:`~Board.fullmove_number` directly.

    .. warning::
        It is possible to set up and work with invalid positions. In this
        case, :class:`~chess.Board` implements a kind of "pseudo-chess"
        (useful to gracefully handle errors or to implement chess variants).
        Use :func:`~chess.Board.is_valid()` to detect invalid positions.
    """

    aliases: ClassVar[List[str]] = ["Standard", "Chess", "Classical", "Normal", "Illegal", "From Position"]
    uci_variant: ClassVar[Optional[str]] = "chess"
    xboard_variant: ClassVar[Optional[str]] = "normal"
    starting_fen: ClassVar[str] = STARTING_FEN

    tbw_suffix: ClassVar[Optional[str]] = ".rtbw"
    tbz_suffix: ClassVar[Optional[str]] = ".rtbz"
    tbw_magic: ClassVar[Optional[bytes]] = b"\x71\xe8\x23\x5d"
    tbz_magic: ClassVar[Optional[bytes]] = b"\xd7\x66\x0c\xa5"
    pawnless_tbw_suffix: ClassVar[Optional[str]] = None
    pawnless_tbz_suffix: ClassVar[Optional[str]] = None
    pawnless_tbw_magic: ClassVar[Optional[bytes]] = None
    pawnless_tbz_magic: ClassVar[Optional[bytes]] = None
    connected_kings: ClassVar[bool] = False
    one_king: ClassVar[bool] = True
    captures_compulsory: ClassVar[bool] = False

    turn: Color
    """The side to move (``chess.WHITE`` or ``chess.BLACK``)."""

    castling_rights: Bitboard
    """
    Bitmask of the rooks with castling rights.

    To test for specific squares:

    >>> import chess
    >>>
    >>> board = chess.Board()
    >>> bool(board.castling_rights & chess.BB_H1)  # White can castle with the h1 rook
    True

    To add a specific square:

    >>> board.castling_rights |= chess.BB_A1

    Use :func:`~chess.Board.set_castling_fen()` to set multiple castling
    rights. Also see :func:`~chess.Board.has_castling_rights()`,
    :func:`~chess.Board.has_kingside_castling_rights()`,
    :func:`~chess.Board.has_queenside_castling_rights()`,
    :func:`~chess.Board.has_chess960_castling_rights()`,
    :func:`~chess.Board.clean_castling_rights()`.
    """

    ep_square: Optional[Square]
    """
    The potential en passant square on the third or sixth rank or ``None``.

    Use :func:`~chess.Board.has_legal_en_passant()` to test if en passant
    capturing would actually be possible on the next move.
    """

    fullmove_number: int
    """
    Counts move pairs. Starts at `1` and is incremented after every move
    of the black side.
    """

    halfmove_clock: int
    """The number of half-moves since the last capture or pawn move."""

    promoted: Bitboard
    """A bitmask of pieces that have been promoted."""

    chess960: bool
    """
    Whether the board is in Chess960 mode. In Chess960 castling moves are
    represented as king moves to the corresponding rook square.
    """

    move_stack: List[Move]
    """
    The move stack. Use :func:`Board.push() <chess.Board.push()>`,
    :func:`Board.pop() <chess.Board.pop()>`,
    :func:`Board.peek() <chess.Board.peek()>` and
    :func:`Board.clear_stack() <chess.Board.clear_stack()>` for
    manipulation.
    """

    def __init__(self, fen: Optional[str] = STARTING_FEN, *, chess960: bool = False) -> None:
        BaseBoard.__init__(self, None)

        self.chess960 = chess960

        self.ep_square = None
        self.move_stack = []
        self._stack: List[_BoardState] = []

        if fen is None:
            self.clear()
        elif fen == type(self).starting_fen:
            self.reset()
        else:
            self.set_fen(fen)

    @property
    def legal_moves(self) -> LegalMoveGenerator:
        """
        A dynamic list of legal moves.

        >>> import chess
        >>>
        >>> board = chess.Board()
        >>> board.legal_moves.count()
        20
        >>> bool(board.legal_moves)
        True
        >>> move = chess.Move.from_uci("g1f3")
        >>> move in board.legal_moves
        True

        Wraps :func:`~chess.Board.generate_legal_moves()` and
        :func:`~chess.Board.is_legal()`.
        """
        return LegalMoveGenerator(self)

    @property
    def pseudo_legal_moves(self) -> PseudoLegalMoveGenerator:
        """
        A dynamic list of pseudo-legal moves, much like the legal move list.

        Pseudo-legal moves might leave or put the king in check, but are
        otherwise valid. Null moves are not pseudo-legal. Castling moves are
        only included if they are completely legal.

        Wraps :func:`~chess.Board.generate_pseudo_legal_moves()` and
        :func:`~chess.Board.is_pseudo_legal()`.
        """
        return PseudoLegalMoveGenerator(self)

    def reset(self) -> None:
        """Restores the starting position."""
        self.turn = WHITE
        self.castling_rights = BB_CORNERS
        self.ep_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1

        self.reset_board()

    def reset_board(self) -> None:
        super().reset_board()
        self.clear_stack()

    def clear(self) -> None:
        """
        Clears the board.

        Resets move stack and move counters. The side to move is white. There
        are no rooks or kings, so castling rights are removed.

        In order to be in a valid :func:`~chess.Board.status()`, at least kings
        need to be put on the board.
        """
        self.turn = WHITE
        self.castling_rights = BB_EMPTY
        self.ep_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1

        self.clear_board()

    def clear_board(self) -> None:
        super().clear_board()
        self.clear_stack()

    def clear_stack(self) -> None:
        """Clears the move stack."""
        self.move_stack.clear()
        self._stack.clear()

    def root(self) -> Self:
        """Returns a copy of the root position."""
        if self._stack:
            board = type(self)(None, chess960=self.chess960)
            self._stack[0].restore(board)
            return board
        else:
            return self.copy(stack=False)

    def ply(self) -> int:
        """
        Returns the number of half-moves since the start of the game, as
        indicated by :data:`~chess.Board.fullmove_number` and
        :data:`~chess.Board.turn`.

        If moves have been pushed from the beginning, this is usually equal to
        ``len(board.move_stack)``. But note that a board can be set up with
        arbitrary starting positions, and the stack can be cleared.
        """
        return 2 * (self.fullmove_number - 1) + (self.turn == BLACK)

    def remove_piece_at(self, square: Square) -> Optional[Piece]:
        piece = super().remove_piece_at(square)
        self.clear_stack()
        return piece

    def set_piece_at(self, square: Square, piece: Optional[Piece], promoted: bool = False) -> None:
        super().set_piece_at(square, piece, promoted=promoted)
        self.clear_stack()

    def generate_pseudo_legal_moves(self, from_mask: Bitboard = BB_ALL, to_mask: Bitboard = BB_ALL) -> Iterator[Move]:
        our_pieces = self.occupied_co[self.turn]

        # Generate piece moves.
        non_pawns = our_pieces & ~self.pawns & from_mask
        for from_square in scan_reversed(non_pawns):
            moves = self.attacks_mask(from_square) & ~our_pieces & to_mask
            for to_square in scan_reversed(moves):
                yield Move(from_square, to_square)

        # Generate castling moves.
        if from_mask & self.kings:
            yield from self.generate_castling_moves(from_mask, to_mask)

        # The remaining moves are all pawn moves.
        pawns = self.pawns & self.occupied_co[self.turn] & from_mask
        if not pawns:
            return

        # Generate pawn captures.
        capturers = pawns
        for from_square in scan_reversed(capturers):
            targets = (
                BB_PAWN_ATTACKS[self.turn][from_square] &
                self.occupied_co[not self.turn] & to_mask)

            for to_square in scan_reversed(targets):
                if square_rank(to_square) in [0, 7]:
                    yield Move(from_square, to_square, QUEEN)
                    yield Move(from_square, to_square, ROOK)
                    yield Move(from_square, to_square, BISHOP)
                    yield Move(from_square, to_square, KNIGHT)
                else:
                    yield Move(from_square, to_square)

        # Prepare pawn advance generation.
        if self.turn == WHITE:
            single_moves = pawns << 8 & ~self.occupied
            double_moves = single_moves << 8 & ~self.occupied & (BB_RANK_3 | BB_RANK_4)
        else:
            single_moves = pawns >> 8 & ~self.occupied
            double_moves = single_moves >> 8 & ~self.occupied & (BB_RANK_6 | BB_RANK_5)

        single_moves &= to_mask
        double_moves &= to_mask

        # Generate single pawn moves.
        for to_square in scan_reversed(single_moves):
            from_square = to_square + (8 if self.turn == BLACK else -8)

            if square_rank(to_square) in [0, 7]:
                yield Move(from_square, to_square, QUEEN)
                yield Move(from_square, to_square, ROOK)
                yield Move(from_square, to_square, BISHOP)
                yield Move(from_square, to_square, KNIGHT)
            else:
                yield Move(from_square, to_square)

        # Generate double pawn moves.
        for to_square in scan_reversed(double_moves):
            from_square = to_square + (16 if self.turn == BLACK else -16)
            yield Move(from_square, to_square)

        # Generate en passant captures.
        if self.ep_square:
            yield from self.generate_pseudo_legal_ep(from_mask, to_mask)

    def generate_pseudo_legal_ep(self, from_mask: Bitboard = BB_ALL, to_mask: Bitboard = BB_ALL) -> Iterator[Move]:
        if not self.ep_square or not BB_SQUARES[self.ep_square] & to_mask:
            return

        if BB_SQUARES[self.ep_square] & self.occupied:
            return

        capturers = (
            self.pawns & self.occupied_co[self.turn] & from_mask &
            BB_PAWN_ATTACKS[not self.turn][self.ep_square] &
            BB_RANKS[4 if self.turn else 3])

        for capturer in scan_reversed(capturers):
            yield Move(capturer, self.ep_square)

    def generate_pseudo_legal_captures(self, from_mask: Bitboard = BB_ALL, to_mask: Bitboard = BB_ALL) -> Iterator[Move]:
        return itertools.chain(
            self.generate_pseudo_legal_moves(from_mask, to_mask & self.occupied_co[not self.turn]),
            self.generate_pseudo_legal_ep(from_mask, to_mask))

    def checkers_mask(self) -> Bitboard:
        king = self.king(self.turn)
        return BB_EMPTY if king is None else self.attackers_mask(not self.turn, king)

    def checkers(self) -> SquareSet:
        """
        Gets the pieces currently giving check.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.checkers_mask())

    def is_check(self) -> bool:
        """Tests if the current side to move is in check."""
        return bool(self.checkers_mask())

    def gives_check(self, move: Move) -> bool:
        """
        Probes if the given move would put the opponent in check. The move
        must be at least pseudo-legal.
        """
        self.push(move)
        try:
            return self.is_check()
        finally:
            self.pop()

    def is_into_check(self, move: Move) -> bool:
        king = self.king(self.turn)
        if king is None:
            return False

        # If already in check, look if it is an evasion.
        checkers = self.attackers_mask(not self.turn, king)
        if checkers and move not in self._generate_evasions(king, checkers, BB_SQUARES[move.from_square], BB_SQUARES[move.to_square]):
            return True

        return not self._is_safe(king, self._slider_blockers(king), move)

    def was_into_check(self) -> bool:
        king = self.king(not self.turn)
        return king is not None and self.is_attacked_by(self.turn, king)

    def is_pseudo_legal(self, move: Move) -> bool:
        # Null moves are not pseudo-legal.
        if not move:
            return False

        # Drops are not pseudo-legal.
        if move.drop:
            return False

        # Source square must not be vacant.
        piece = self.piece_type_at(move.from_square)
        if not piece:
            return False

        # Get square masks.
        from_mask = BB_SQUARES[move.from_square]
        to_mask = BB_SQUARES[move.to_square]

        # Check turn.
        if not self.occupied_co[self.turn] & from_mask:
            return False

        # Only pawns can promote and only on the backrank.
        if move.promotion:
            if piece != PAWN:
                return False

            if self.turn == WHITE and square_rank(move.to_square) != 7:
                return False
            elif self.turn == BLACK and square_rank(move.to_square) != 0:
                return False

        # Handle castling.
        if piece == KING:
            move = self._from_chess960(self.chess960, move.from_square, move.to_square)
            if move in self.generate_castling_moves():
                return True

        # Destination square can not be occupied.
        if self.occupied_co[self.turn] & to_mask:
            return False

        # Handle pawn moves.
        if piece == PAWN:
            return move in self.generate_pseudo_legal_moves(from_mask, to_mask)

        # Handle all other pieces.
        return bool(self.attacks_mask(move.from_square) & to_mask)

    def is_legal(self, move: Move) -> bool:
        return not self.is_variant_end() and self.is_pseudo_legal(move) and not self.is_into_check(move)

    def is_variant_end(self) -> bool:
        """
        Checks if the game is over due to a special variant end condition.

        Note, for example, that stalemate is not considered a variant-specific
        end condition (this method will return ``False``), yet it can have a
        special **result** in suicide chess (any of
        :func:`~chess.Board.is_variant_loss()`,
        :func:`~chess.Board.is_variant_win()`,
        :func:`~chess.Board.is_variant_draw()` might return ``True``).
        """
        return False

    def is_variant_loss(self) -> bool:
        """
        Checks if the current side to move lost due to a variant-specific
        condition.
        """
        return False

    def is_variant_win(self) -> bool:
        """
        Checks if the current side to move won due to a variant-specific
        condition.
        """
        return False

    def is_variant_draw(self) -> bool:
        """
        Checks if a variant-specific drawing condition is fulfilled.
        """
        return False

    def is_game_over(self, *, claim_draw: bool = False) -> bool:
        return self.outcome(claim_draw=claim_draw) is not None

    def result(self, *, claim_draw: bool = False) -> str:
        outcome = self.outcome(claim_draw=claim_draw)
        return outcome.result() if outcome else "*"

    def outcome(self, *, claim_draw: bool = False) -> Optional[Outcome]:
        """
        Checks if the game is over due to
        :func:`checkmate <chess.Board.is_checkmate()>`,
        :func:`stalemate <chess.Board.is_stalemate()>`,
        :func:`insufficient material <chess.Board.is_insufficient_material()>`,
        the :func:`seventyfive-move rule <chess.Board.is_seventyfive_moves()>`,
        :func:`fivefold repetition <chess.Board.is_fivefold_repetition()>`,
        or a :func:`variant end condition <chess.Board.is_variant_end()>`.
        Returns the :class:`chess.Outcome` if the game has ended, otherwise
        ``None``.

        Alternatively, use :func:`~chess.Board.is_game_over()` if you are not
        interested in who won the game and why.

        The game is not considered to be over by the
        :func:`fifty-move rule <chess.Board.can_claim_fifty_moves()>` or
        :func:`threefold repetition <chess.Board.can_claim_threefold_repetition()>`,
        unless *claim_draw* is given. Note that checking the latter can be
        slow.
        """
        # Variant support.
        if self.is_variant_loss():
            return Outcome(Termination.VARIANT_LOSS, not self.turn)
        if self.is_variant_win():
            return Outcome(Termination.VARIANT_WIN, self.turn)
        if self.is_variant_draw():
            return Outcome(Termination.VARIANT_DRAW, None)

        # Normal game end.
        if self.is_checkmate():
            return Outcome(Termination.CHECKMATE, not self.turn)
        if self.is_insufficient_material():
            return Outcome(Termination.INSUFFICIENT_MATERIAL, None)
        if not any(self.generate_legal_moves()):
            return Outcome(Termination.STALEMATE, None)

        # Automatic draws.
        if self.is_seventyfive_moves():
            return Outcome(Termination.SEVENTYFIVE_MOVES, None)
        if self.is_fivefold_repetition():
            return Outcome(Termination.FIVEFOLD_REPETITION, None)

        # Claimable draws.
        if claim_draw:
            if self.can_claim_fifty_moves():
                return Outcome(Termination.FIFTY_MOVES, None)
            if self.can_claim_threefold_repetition():
                return Outcome(Termination.THREEFOLD_REPETITION, None)

        return None

    def is_checkmate(self) -> bool:
        """Checks if the current position is a checkmate."""
        if not self.is_check():
            return False

        return not any(self.generate_legal_moves())

    def is_stalemate(self) -> bool:
        """Checks if the current position is a stalemate."""
        if self.is_check():
            return False

        if self.is_variant_end():
            return False

        return not any(self.generate_legal_moves())

    def is_insufficient_material(self) -> bool:
        """
        Checks if neither side has sufficient winning material
        (:func:`~chess.Board.has_insufficient_material()`).
        """
        return all(self.has_insufficient_material(color) for color in COLORS)

    def has_insufficient_material(self, color: Color) -> bool:
        """
        Checks if *color* has insufficient winning material.

        This is guaranteed to return ``False`` if *color* can still win the
        game.

        The converse does not necessarily hold:
        The implementation only looks at the material, including the colors
        of bishops, but not considering piece positions. So fortress
        positions or positions with forced lines may return ``False``, even
        though there is no possible winning line.
        """
        if self.occupied_co[color] & (self.pawns | self.rooks | self.queens):
            return False

        # Knights are only insufficient material if:
        # (1) We do not have any other pieces, including more than one knight.
        # (2) The opponent does not have pawns, knights, bishops or rooks.
        #     These would allow selfmate.
        if self.occupied_co[color] & self.knights:
            return (popcount(self.occupied_co[color]) <= 2 and
                    not (self.occupied_co[not color] & ~self.kings & ~self.queens))

        # Bishops are only insufficient material if:
        # (1) We do not have any other pieces, including bishops of the
        #     opposite color.
        # (2) The opponent does not have bishops of the opposite color,
        #     pawns or knights. These would allow selfmate.
        if self.occupied_co[color] & self.bishops:
            same_color = (not self.bishops & BB_DARK_SQUARES) or (not self.bishops & BB_LIGHT_SQUARES)
            return same_color and not self.pawns and not self.knights

        return True

    def _is_halfmoves(self, n: int) -> bool:
        return self.halfmove_clock >= n and any(self.generate_legal_moves())

    def is_seventyfive_moves(self) -> bool:
        """
        Since the 1st of July 2014, a game is automatically drawn (without
        a claim by one of the players) if the half-move clock since a capture
        or pawn move is equal to or greater than 150. Other means to end a game
        take precedence.
        """
        return self._is_halfmoves(150)

    def is_fivefold_repetition(self) -> bool:
        """
        Since the 1st of July 2014 a game is automatically drawn (without
        a claim by one of the players) if a position occurs for the fifth time.
        Originally this had to occur on consecutive alternating moves, but
        this has since been revised.
        """
        return self.is_repetition(5)

    def can_claim_draw(self) -> bool:
        """
        Checks if the player to move can claim a draw by the fifty-move rule or
        by threefold repetition.

        Note that checking the latter can be slow.
        """
        return self.can_claim_fifty_moves() or self.can_claim_threefold_repetition()

    def is_fifty_moves(self) -> bool:
        """
        Checks that the clock of halfmoves since the last capture or pawn move
        is greater or equal to 100, and that no other means of ending the game
        (like checkmate) take precedence.
        """
        return self._is_halfmoves(100)

    def can_claim_fifty_moves(self) -> bool:
        """
        Checks if the player to move can claim a draw by the fifty-move rule.

        In addition to :func:`~chess.Board.is_fifty_moves()`, the fifty-move
        rule can also be claimed if there is a legal move that achieves this
        condition.
        """
        if self.is_fifty_moves():
            return True

        if self.halfmove_clock >= 99:
            for move in self.generate_legal_moves():
                if not self.is_zeroing(move):
                    self.push(move)
                    try:
                        if self.is_fifty_moves():
                            return True
                    finally:
                        self.pop()

        return False

    def can_claim_threefold_repetition(self) -> bool:
        """
        Checks if the player to move can claim a draw by threefold repetition.

        Draw by threefold repetition can be claimed if the position on the
        board occurred for the third time or if such a repetition is reached
        with one of the possible legal moves.

        Note that checking this can be slow: In the worst case
        scenario, every legal move has to be tested and the entire game has to
        be replayed because there is no incremental transposition table.
        """
        transposition_key = self._transposition_key()
        transpositions: Counter[Hashable] = collections.Counter()
        transpositions.update((transposition_key, ))

        # Count positions.
        switchyard: List[Move] = []
        while self.move_stack:
            move = self.pop()
            switchyard.append(move)

            if self.is_irreversible(move):
                break

            transpositions.update((self._transposition_key(), ))

        while switchyard:
            self.push(switchyard.pop())

        # Threefold repetition occurred.
        if transpositions[transposition_key] >= 3:
            return True

        # The next legal move is a threefold repetition.
        for move in self.generate_legal_moves():
            self.push(move)
            try:
                if transpositions[self._transposition_key()] >= 2:
                    return True
            finally:
                self.pop()

        return False

    def is_repetition(self, count: int = 3) -> bool:
        """
        Checks if the current position has repeated 3 (or a given number of)
        times.

        Unlike :func:`~chess.Board.can_claim_threefold_repetition()`,
        this does not consider a repetition that can be played on the next
        move.

        Note that checking this can be slow: In the worst case, the entire
        game has to be replayed because there is no incremental transposition
        table.
        """
        # Fast check, based on occupancy only.
        maybe_repetitions = 1
        for state in reversed(self._stack):
            if state.occupied == self.occupied:
                maybe_repetitions += 1
                if maybe_repetitions >= count:
                    break
        if maybe_repetitions < count:
            return False

        # Check full replay.
        transposition_key = self._transposition_key()
        switchyard: List[Move] = []

        try:
            while True:
                if count <= 1:
                    return True

                if len(self.move_stack) < count - 1:
                    break

                move = self.pop()
                switchyard.append(move)

                if self.is_irreversible(move):
                    break

                if self._transposition_key() == transposition_key:
                    count -= 1
        finally:
            while switchyard:
                self.push(switchyard.pop())

        return False

    def _push_capture(self, move: Move, capture_square: Square, piece_type: PieceType, was_promoted: bool) -> None:
        pass

    def push(self, move: Move) -> None:
        """
        Updates the position with the given *move* and puts it onto the
        move stack.

        >>> import chess
        >>>
        >>> board = chess.Board()
        >>>
        >>> Nf3 = chess.Move.from_uci("g1f3")
        >>> board.push(Nf3)  # Make the move

        >>> board.pop()  # Unmake the last move
        Move.from_uci('g1f3')

        Null moves just increment the move counters, switch turns and forfeit
        en passant capturing.

        .. warning::
            Moves are not checked for legality. It is the caller's
            responsibility to ensure that the move is at least pseudo-legal or
            a null move.
        """
        # Push move and remember board state.
        move = self._to_chess960(move)
        board_state = _BoardState(self)
        self.castling_rights = self.clean_castling_rights()  # Before pushing stack
        self.move_stack.append(self._from_chess960(self.chess960, move.from_square, move.to_square, move.promotion, move.drop))
        self._stack.append(board_state)

        # Reset en passant square.
        ep_square = self.ep_square
        self.ep_square = None

        # Increment move counters.
        self.halfmove_clock += 1
        if self.turn == BLACK:
            self.fullmove_number += 1

        # On a null move, simply swap turns and reset the en passant square.
        if not move:
            self.turn = not self.turn
            return

        # Drops.
        if move.drop:
            self._set_piece_at(move.to_square, move.drop, self.turn)
            self.turn = not self.turn
            return

        # Zero the half-move clock.
        if self.is_zeroing(move):
            self.halfmove_clock = 0

        from_bb = BB_SQUARES[move.from_square]
        to_bb = BB_SQUARES[move.to_square]

        promoted = bool(self.promoted & from_bb)
        piece_type = self._remove_piece_at(move.from_square)
        assert piece_type is not None, f"push() expects move to be pseudo-legal, but got {move} in {self.board_fen()}"
        capture_square = move.to_square
        captured_piece_type = self.piece_type_at(capture_square)

        # Update castling rights.
        self.castling_rights &= ~to_bb & ~from_bb
        if piece_type == KING and not promoted:
            if self.turn == WHITE:
                self.castling_rights &= ~BB_RANK_1
            else:
                self.castling_rights &= ~BB_RANK_8
        elif captured_piece_type == KING and not self.promoted & to_bb:
            if self.turn == WHITE and square_rank(move.to_square) == 7:
                self.castling_rights &= ~BB_RANK_8
            elif self.turn == BLACK and square_rank(move.to_square) == 0:
                self.castling_rights &= ~BB_RANK_1

        # Handle special pawn moves.
        if piece_type == PAWN:
            diff = move.to_square - move.from_square

            if diff == 16 and square_rank(move.from_square) == 1:
                self.ep_square = move.from_square + 8
            elif diff == -16 and square_rank(move.from_square) == 6:
                self.ep_square = move.from_square - 8
            elif move.to_square == ep_square and abs(diff) in [7, 9] and not captured_piece_type:
                # Remove pawns captured en passant.
                down = -8 if self.turn == WHITE else 8
                capture_square = ep_square + down
                captured_piece_type = self._remove_piece_at(capture_square)

        # Promotion.
        if move.promotion:
            promoted = True
            piece_type = move.promotion

        # Castling.
        castling = piece_type == KING and self.occupied_co[self.turn] & to_bb
        if castling:
            a_side = square_file(move.to_square) < square_file(move.from_square)

            self._remove_piece_at(move.from_square)
            self._remove_piece_at(move.to_square)

            if a_side:
                self._set_piece_at(C1 if self.turn == WHITE else C8, KING, self.turn)
                self._set_piece_at(D1 if self.turn == WHITE else D8, ROOK, self.turn)
            else:
                self._set_piece_at(G1 if self.turn == WHITE else G8, KING, self.turn)
                self._set_piece_at(F1 if self.turn == WHITE else F8, ROOK, self.turn)

        # Put the piece on the target square.
        if not castling:
            was_promoted = bool(self.promoted & to_bb)
            self._set_piece_at(move.to_square, piece_type, self.turn, promoted)

            if captured_piece_type:
                self._push_capture(move, capture_square, captured_piece_type, was_promoted)

        # Swap turn.
        self.turn = not self.turn

    def pop(self) -> Move:
        """
        Restores the previous position and returns the last move from the stack.

        :raises: :exc:`IndexError` if the move stack is empty.
        """
        move = self.move_stack.pop()
        self._stack.pop().restore(self)
        return move

    def peek(self) -> Move:
        """
        Gets the last move from the move stack.

        :raises: :exc:`IndexError` if the move stack is empty.
        """
        return self.move_stack[-1]

    def find_move(self, from_square: Square, to_square: Square, promotion: Optional[PieceType] = None) -> Move:
        """
        Finds a matching legal move for an origin square, a target square, and
        an optional promotion piece type.

        For pawn moves to the backrank, the promotion piece type defaults to
        :data:`chess.QUEEN`, unless otherwise specified.

        Castling moves are normalized to king moves by two steps, except in
        Chess960.

        :raises: :exc:`IllegalMoveError` if no matching legal move is found.
        """
        if promotion is None and self.pawns & BB_SQUARES[from_square] and BB_SQUARES[to_square] & BB_BACKRANKS:
            promotion = QUEEN

        move = self._from_chess960(self.chess960, from_square, to_square, promotion)
        if not self.is_legal(move):
            raise IllegalMoveError(f"no matching legal move for {move.uci()} ({SQUARE_NAMES[from_square]} -> {SQUARE_NAMES[to_square]}) in {self.fen()}")

        return move

    def castling_shredder_fen(self) -> str:
        castling_rights = self.clean_castling_rights()
        if not castling_rights:
            return "-"

        builder: List[str] = []

        for square in scan_reversed(castling_rights & BB_RANK_1):
            builder.append(FILE_NAMES[square_file(square)].upper())

        for square in scan_reversed(castling_rights & BB_RANK_8):
            builder.append(FILE_NAMES[square_file(square)])

        return "".join(builder)

    def castling_xfen(self) -> str:
        builder: List[str] = []

        for color in COLORS:
            king = self.king(color)
            if king is None:
                continue

            king_file = square_file(king)
            backrank = BB_RANK_1 if color == WHITE else BB_RANK_8

            for rook_square in scan_reversed(self.clean_castling_rights() & backrank):
                rook_file = square_file(rook_square)
                a_side = rook_file < king_file

                other_rooks = self.occupied_co[color] & self.rooks & backrank & ~BB_SQUARES[rook_square]

                if any((square_file(other) < rook_file) == a_side for other in scan_reversed(other_rooks)):
                    ch = FILE_NAMES[rook_file]
                else:
                    ch = "q" if a_side else "k"

                builder.append(ch.upper() if color == WHITE else ch)

        if builder:
            return "".join(builder)
        else:
            return "-"

    def has_pseudo_legal_en_passant(self) -> bool:
        """Checks if there is a pseudo-legal en passant capture."""
        return self.ep_square is not None and any(self.generate_pseudo_legal_ep())

    def has_legal_en_passant(self) -> bool:
        """Checks if there is a legal en passant capture."""
        return self.ep_square is not None and any(self.generate_legal_ep())

    def fen(self, *, shredder: bool = False, en_passant: EnPassantSpec = "legal", promoted: Optional[bool] = None) -> str:
        """
        Gets a FEN representation of the position.

        A FEN string (e.g.,
        ``rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1``) consists
        of the board part :func:`~chess.Board.board_fen()`, the
        :data:`~chess.Board.turn`, the castling part
        (:data:`~chess.Board.castling_rights`),
        the en passant square (:data:`~chess.Board.ep_square`),
        the :data:`~chess.Board.halfmove_clock`
        and the :data:`~chess.Board.fullmove_number`.

        :param shredder: Use :func:`~chess.Board.castling_shredder_fen()`
            and encode castling rights by the file of the rook
            (like ``HAha``) instead of the default
            :func:`~chess.Board.castling_xfen()` (like ``KQkq``).
        :param en_passant: By default, only fully legal en passant squares
            are included (:func:`~chess.Board.has_legal_en_passant()`).
            Pass ``fen`` to strictly follow the FEN specification
            (always include the en passant square after a two-step pawn move)
            or ``xfen`` to follow the X-FEN specification
            (:func:`~chess.Board.has_pseudo_legal_en_passant()`).
        :param promoted: Mark promoted pieces like ``Q~``. By default, this is
            only enabled in chess variants where this is relevant.
        """
        return " ".join([
            self.epd(shredder=shredder, en_passant=en_passant, promoted=promoted),
            str(self.halfmove_clock),
            str(self.fullmove_number)
        ])

    def shredder_fen(self, *, en_passant: EnPassantSpec = "legal", promoted: Optional[bool] = None) -> str:
        return " ".join([
            self.epd(shredder=True, en_passant=en_passant, promoted=promoted),
            str(self.halfmove_clock),
            str(self.fullmove_number)
        ])

    def set_fen(self, fen: str) -> None:
        """
        Parses a FEN and sets the position from it.

        :raises: :exc:`ValueError` if syntactically invalid. Use
            :func:`~chess.Board.is_valid()` to detect invalid positions.
        """
        parts = fen.split()

        # Board part.
        try:
            board_part = parts.pop(0)
        except IndexError:
            raise ValueError("empty fen")

        # Turn.
        try:
            turn_part = parts.pop(0)
        except IndexError:
            turn = WHITE
        else:
            if turn_part == "w":
                turn = WHITE
            elif turn_part == "b":
                turn = BLACK
            else:
                raise ValueError(f"expected 'w' or 'b' for turn part of fen: {fen!r}")

        # Validate castling part.
        try:
            castling_part = parts.pop(0)
        except IndexError:
            castling_part = "-"
        else:
            if not FEN_CASTLING_REGEX.match(castling_part):
                raise ValueError(f"invalid castling part in fen: {fen!r}")

        # En passant square.
        try:
            ep_part = parts.pop(0)
        except IndexError:
            ep_square = None
        else:
            try:
                ep_square = None if ep_part == "-" else SQUARE_NAMES.index(ep_part)
            except ValueError:
                raise ValueError(f"invalid en passant part in fen: {fen!r}")

        # Check that the half-move part is valid.
        try:
            halfmove_part = parts.pop(0)
        except IndexError:
            halfmove_clock = 0
        else:
            try:
                halfmove_clock = int(halfmove_part)
            except ValueError:
                raise ValueError(f"invalid half-move clock in fen: {fen!r}")

            if halfmove_clock < 0:
                raise ValueError(f"half-move clock cannot be negative: {fen!r}")

        # Check that the full-move number part is valid.
        # 0 is allowed for compatibility, but later replaced with 1.
        try:
            fullmove_part = parts.pop(0)
        except IndexError:
            fullmove_number = 1
        else:
            try:
                fullmove_number = int(fullmove_part)
            except ValueError:
                raise ValueError(f"invalid fullmove number in fen: {fen!r}")

            if fullmove_number < 0:
                raise ValueError(f"fullmove number cannot be negative: {fen!r}")

            fullmove_number = max(fullmove_number, 1)

        # All parts should be consumed now.
        if parts:
            raise ValueError(f"fen string has more parts than expected: {fen!r}")

        # Validate the board part and set it.
        self._set_board_fen(board_part)

        # Apply.
        self.turn = turn
        self._set_castling_fen(castling_part)
        self.ep_square = ep_square
        self.halfmove_clock = halfmove_clock
        self.fullmove_number = fullmove_number
        self.clear_stack()

    def _set_castling_fen(self, castling_fen: str) -> None:
        if not castling_fen or castling_fen == "-":
            self.castling_rights = BB_EMPTY
            return

        if not FEN_CASTLING_REGEX.match(castling_fen):
            raise ValueError(f"invalid castling fen: {castling_fen!r}")

        self.castling_rights = BB_EMPTY

        for flag in castling_fen:
            color = WHITE if flag.isupper() else BLACK
            flag = flag.lower()
            backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
            rooks = self.occupied_co[color] & self.rooks & backrank
            king = self.king(color)

            if flag == "q":
                # Select the leftmost rook.
                if king is not None and lsb(rooks) < king:
                    self.castling_rights |= rooks & -rooks
                else:
                    self.castling_rights |= BB_FILE_A & backrank
            elif flag == "k":
                # Select the rightmost rook.
                rook = msb(rooks)
                if king is not None and king < rook:
                    self.castling_rights |= BB_SQUARES[rook]
                else:
                    self.castling_rights |= BB_FILE_H & backrank
            else:
                self.castling_rights |= BB_FILES[FILE_NAMES.index(flag)] & backrank

    def set_castling_fen(self, castling_fen: str) -> None:
        """
        Sets castling rights from a string in FEN notation like ``Qqk``.

        Also clears the move stack.

        :raises: :exc:`ValueError` if the castling FEN is syntactically
            invalid.
        """
        self._set_castling_fen(castling_fen)
        self.clear_stack()

    def set_board_fen(self, fen: str) -> None:
        super().set_board_fen(fen)
        self.clear_stack()

    def set_piece_map(self, pieces: Mapping[Square, Piece]) -> None:
        super().set_piece_map(pieces)
        self.clear_stack()

    def set_chess960_pos(self, scharnagl: int) -> None:
        super().set_chess960_pos(scharnagl)
        self.chess960 = True
        self.turn = WHITE
        self.castling_rights = self.rooks
        self.ep_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1

        self.clear_stack()

    def chess960_pos(self, *, ignore_turn: bool = False, ignore_castling: bool = False, ignore_counters: bool = True) -> Optional[int]:
        """
        Gets the Chess960 starting position index between 0 and 956,
        or ``None`` if the current position is not a Chess960 starting
        position.

        By default, white to move (**ignore_turn**) and full castling rights
        (**ignore_castling**) are required, but move counters
        (**ignore_counters**) are ignored.
        """
        if self.ep_square:
            return None

        if not ignore_turn:
            if self.turn != WHITE:
                return None

        if not ignore_castling:
            if self.clean_castling_rights() != self.rooks:
                return None

        if not ignore_counters:
            if self.fullmove_number != 1 or self.halfmove_clock != 0:
                return None

        return super().chess960_pos()

    def _epd_operations(self, operations: Mapping[str, Union[None, str, int, float, Move, Iterable[Move]]]) -> str:
        epd: List[str] = []
        first_op = True

        for opcode, operand in operations.items():
            self._validate_epd_opcode(opcode)

            if not first_op:
                epd.append(" ")
            first_op = False
            epd.append(opcode)

            if operand is None:
                epd.append(";")
            elif isinstance(operand, Move):
                epd.append(" ")
                epd.append(self.san(operand))
                epd.append(";")
            elif isinstance(operand, int):
                epd.append(f" {operand};")
            elif isinstance(operand, float):
                assert math.isfinite(operand), f"expected numeric epd operand to be finite, got: {operand}"
                epd.append(f" {operand};")
            elif opcode == "pv" and not isinstance(operand, str) and hasattr(operand, "__iter__"):
                position = self.copy(stack=False)
                for move in operand:
                    epd.append(" ")
                    epd.append(position.san_and_push(move))
                epd.append(";")
            elif opcode in ["am", "bm"] and not isinstance(operand, str) and hasattr(operand, "__iter__"):
                for san in sorted(self.san(move) for move in operand):
                    epd.append(" ")
                    epd.append(san)
                epd.append(";")
            else:
                # Append as escaped string.
                epd.append(" \"")
                epd.append(str(operand).replace("\\", "\\\\").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n").replace("\"", "\\\""))
                epd.append("\";")

        return "".join(epd)

    def epd(self, *, shredder: bool = False, en_passant: EnPassantSpec = "legal", promoted: Optional[bool] = None, **operations: Union[None, str, int, float, Move, Iterable[Move]]) -> str:
        """
        Gets an EPD representation of the current position.

        See :func:`~chess.Board.fen()` for FEN formatting options (*shredder*,
        *ep_square* and *promoted*).

        EPD operations can be given as keyword arguments. Supported operands
        are strings, integers, finite floats, legal moves and ``None``.
        Additionally, the operation ``pv`` accepts a legal variation as
        a list of moves. The operations ``am`` and ``bm`` accept a list of
        legal moves in the current position.

        The name of the field cannot be a lone dash and cannot contain spaces,
        newlines, carriage returns or tabs.

        *hmvc* and *fmvn* are not included by default. You can use:

        >>> import chess
        >>>
        >>> board = chess.Board()
        >>> board.epd(hmvc=board.halfmove_clock, fmvn=board.fullmove_number)
        'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - hmvc 0; fmvn 1;'
        """
        if en_passant == "fen":
            ep_square = self.ep_square
        elif en_passant == "xfen":
            ep_square = self.ep_square if self.has_pseudo_legal_en_passant() else None
        else:
            ep_square = self.ep_square if self.has_legal_en_passant() else None

        epd = [self.board_fen(promoted=promoted),
               "w" if self.turn == WHITE else "b",
               self.castling_shredder_fen() if shredder else self.castling_xfen(),
               SQUARE_NAMES[ep_square] if ep_square is not None else "-"]

        if operations:
            epd.append(self._epd_operations(operations))

        return " ".join(epd)

    def _validate_epd_opcode(self, opcode: str) -> None:
        if not opcode:
            raise ValueError("empty string is not a valid epd opcode")
        if opcode == "-":
            raise ValueError("dash (-) is not a valid epd opcode")
        if not opcode[0].isalpha():
            raise ValueError(f"expected epd opcode to start with a letter, got: {opcode!r}")
        for blacklisted in [" ", "\n", "\t", "\r"]:
            if blacklisted in opcode:
                raise ValueError(f"invalid character {blacklisted!r} in epd opcode: {opcode!r}")

    def _parse_epd_ops(self, operation_part: str, make_board: Callable[[], Self]) -> Dict[str, Union[None, str, int, float, Move, List[Move]]]:
        operations: Dict[str, Union[None, str, int, float, Move, List[Move]]] = {}
        state = "opcode"
        opcode = ""
        operand = ""
        position = None

        for ch in itertools.chain(operation_part, [None]):
            if state == "opcode":
                if ch in [" ", "\t", "\r", "\n"]:
                    if opcode == "-":
                        opcode = ""
                    elif opcode:
                        self._validate_epd_opcode(opcode)
                        state = "after_opcode"
                elif ch is None or ch == ";":
                    if opcode == "-":
                        opcode = ""
                    elif opcode:
                        operations[opcode] = [] if opcode in ["pv", "am", "bm"] else None
                        opcode = ""
                else:
                    opcode += ch
            elif state == "after_opcode":
                if ch in [" ", "\t", "\r", "\n"]:
                    pass
                elif ch == "\"":
                    state = "string"
                elif ch is None or ch == ";":
                    if opcode:
                        operations[opcode] = [] if opcode in ["pv", "am", "bm"] else None
                        opcode = ""
                    state = "opcode"
                elif ch in "+-.0123456789":
                    operand = ch
                    state = "numeric"
                else:
                    operand = ch
                    state = "san"
            elif state == "numeric":
                if ch is None or ch == ";":
                    if "." in operand or "e" in operand or "E" in operand:
                        parsed = float(operand)
                        if not math.isfinite(parsed):
                            raise ValueError(f"invalid numeric operand for epd operation {opcode!r}: {operand!r}")
                        operations[opcode] = parsed
                    else:
                        operations[opcode] = int(operand)
                    opcode = ""
                    operand = ""
                    state = "opcode"
                else:
                    operand += ch
            elif state == "string":
                if ch is None or ch == "\"":
                    operations[opcode] = operand
                    opcode = ""
                    operand = ""
                    state = "opcode"
                elif ch == "\\":
                    state = "string_escape"
                else:
                    operand += ch
            elif state == "string_escape":
                if ch is None:
                    operations[opcode] = operand
                    opcode = ""
                    operand = ""
                    state = "opcode"
                elif ch == "r":
                    operand += "\r"
                    state = "string"
                elif ch == "n":
                    operand += "\n"
                    state = "string"
                elif ch == "t":
                    operand += "\t"
                    state = "string"
                else:
                    operand += ch
                    state = "string"
            elif state == "san":
                if ch is None or ch == ";":
                    if position is None:
                        position = make_board()

                    if opcode == "pv":
                        # A variation.
                        variation: List[Move] = []
                        for token in operand.split():
                            move = position.parse_xboard(token)
                            variation.append(move)
                            position.push(move)

                        # Reset the position.
                        while position.move_stack:
                            position.pop()

                        operations[opcode] = variation
                    elif opcode in ["bm", "am"]:
                        # A set of moves.
                        operations[opcode] = [position.parse_xboard(token) for token in operand.split()]
                    else:
                        # A single move.
                        operations[opcode] = position.parse_xboard(operand)

                    opcode = ""
                    operand = ""
                    state = "opcode"
                else:
                    operand += ch

        assert state == "opcode"
        return operations

    def set_epd(self, epd: str) -> Dict[str, Union[None, str, int, float, Move, List[Move]]]:
        """
        Parses the given EPD string and uses it to set the position.

        If present, ``hmvc`` and ``fmvn`` are used to set the half-move
        clock and the full-move number. Otherwise, ``0`` and ``1`` are used.

        Returns a dictionary of parsed operations. Values can be strings,
        integers, floats, move objects, or lists of moves.

        :raises: :exc:`ValueError` if the EPD string is invalid.
        """
        parts = epd.strip().rstrip(";").split(None, 4)

        # Parse ops.
        if len(parts) > 4:
            operations = self._parse_epd_ops(parts.pop(), lambda: type(self)(" ".join(parts) + " 0 1"))
            parts.append(str(operations["hmvc"]) if "hmvc" in operations else "0")
            parts.append(str(operations["fmvn"]) if "fmvn" in operations else "1")
            self.set_fen(" ".join(parts))
            return operations
        else:
            self.set_fen(epd)
            return {}

    def san(self, move: Move) -> str:
        """
        Gets the standard algebraic notation of the given move in the context
        of the current position.
        """
        return self._algebraic(move)

    def lan(self, move: Move) -> str:
        """
        Gets the long algebraic notation of the given move in the context of
        the current position.
        """
        return self._algebraic(move, long=True)

    def san_and_push(self, move: Move) -> str:
        return self._algebraic_and_push(move)

    def _algebraic(self, move: Move, *, long: bool = False) -> str:
        san = self._algebraic_and_push(move, long=long)
        self.pop()
        return san

    def _algebraic_and_push(self, move: Move, *, long: bool = False) -> str:
        san = self._algebraic_without_suffix(move, long=long)

        # Look ahead for check or checkmate.
        self.push(move)
        is_check = self.is_check()
        is_checkmate = (is_check and self.is_checkmate()) or self.is_variant_loss() or self.is_variant_win()

        # Add check or checkmate suffix.
        if is_checkmate and move:
            return san + "#"
        elif is_check and move:
            return san + "+"
        else:
            return san

    def _algebraic_without_suffix(self, move: Move, *, long: bool = False) -> str:
        # Null move.
        if not move:
            return "--"

        # Drops.
        if move.drop:
            san = ""
            if move.drop != PAWN:
                san = piece_symbol(move.drop).upper()
            san += "@" + SQUARE_NAMES[move.to_square]
            return san

        # Castling.
        if self.is_castling(move):
            if square_file(move.to_square) < square_file(move.from_square):
                return "O-O-O"
            else:
                return "O-O"

        piece_type = self.piece_type_at(move.from_square)
        assert piece_type, f"san() and lan() expect move to be legal or null, but got {move} in {self.fen()}"
        capture = self.is_capture(move)

        if piece_type == PAWN:
            san = ""
        else:
            san = piece_symbol(piece_type).upper()

        if long:
            san += SQUARE_NAMES[move.from_square]
        elif piece_type != PAWN:
            # Get ambiguous move candidates.
            # Relevant candidates: not exactly the current move,
            # but to the same square.
            others = 0
            from_mask = self.pieces_mask(piece_type, self.turn)
            from_mask &= ~BB_SQUARES[move.from_square]
            to_mask = BB_SQUARES[move.to_square]
            for candidate in self.generate_legal_moves(from_mask, to_mask):
                others |= BB_SQUARES[candidate.from_square]

            # Disambiguate.
            if others:
                row, column = False, False

                if others & BB_RANKS[square_rank(move.from_square)]:
                    column = True

                if others & BB_FILES[square_file(move.from_square)]:
                    row = True
                else:
                    column = True

                if column:
                    san += FILE_NAMES[square_file(move.from_square)]
                if row:
                    san += RANK_NAMES[square_rank(move.from_square)]
        elif capture:
            san += FILE_NAMES[square_file(move.from_square)]

        # Captures.
        if capture:
            san += "x"
        elif long:
            san += "-"

        # Destination square.
        san += SQUARE_NAMES[move.to_square]

        # Promotion.
        if move.promotion:
            san += "=" + piece_symbol(move.promotion).upper()

        return san

    def variation_san(self, variation: Iterable[Move]) -> str:
        """
        Given a sequence of moves, returns a string representing the sequence
        in standard algebraic notation (e.g., ``1. e4 e5 2. Nf3 Nc6`` or
        ``37...Bg6 38. fxg6``).

        The board will not be modified as a result of calling this.

        :raises: :exc:`IllegalMoveError` if any moves in the sequence are illegal.
        """
        board = self.copy(stack=False)
        san: List[str] = []

        for move in variation:
            if not board.is_legal(move):
                raise IllegalMoveError(f"illegal move {move} in position {board.fen()}")

            if board.turn == WHITE:
                san.append(f"{board.fullmove_number}. {board.san_and_push(move)}")
            elif not san:
                san.append(f"{board.fullmove_number}...{board.san_and_push(move)}")
            else:
                san.append(board.san_and_push(move))

        return " ".join(san)

    def parse_san(self, san: str) -> Move:
        """
        Uses the current position as the context to parse a move in standard
        algebraic notation and returns the corresponding move object.

        Ambiguous moves are rejected. Overspecified moves (including long
        algebraic notation) are accepted. Some common syntactical deviations
        are also accepted.

        The returned move is guaranteed to be either legal or a null move.

        :raises:
            :exc:`ValueError` (specifically an exception specified below) if the SAN is invalid, illegal or ambiguous.

            - :exc:`InvalidMoveError` if the SAN is syntactically invalid.
            - :exc:`IllegalMoveError` if the SAN is illegal.
            - :exc:`AmbiguousMoveError` if the SAN is ambiguous.
        """
        # Castling.
        try:
            if san in ["O-O", "O-O+", "O-O#", "0-0", "0-0+", "0-0#"]:
                return next(move for move in self.generate_castling_moves() if self.is_kingside_castling(move))
            elif san in ["O-O-O", "O-O-O+", "O-O-O#", "0-0-0", "0-0-0+", "0-0-0#"]:
                return next(move for move in self.generate_castling_moves() if self.is_queenside_castling(move))
        except StopIteration:
            raise IllegalMoveError(f"illegal san: {san!r} in {self.fen()}")

        # Match normal moves.
        match = SAN_REGEX.match(san)
        if not match:
            # Null moves.
            if san in ["--", "Z0", "0000", "@@@@"]:
                return Move.null()
            elif "," in san:
                raise InvalidMoveError(f"unsupported multi-leg move: {san!r}")
            else:
                raise InvalidMoveError(f"invalid san: {san!r}")

        # Get target square. Mask our own pieces to exclude castling moves.
        to_square = SQUARE_NAMES.index(match.group(4))
        to_mask = BB_SQUARES[to_square] & ~self.occupied_co[self.turn]

        # Get the promotion piece type.
        p = match.group(5)
        promotion = PIECE_SYMBOLS.index(p[-1].lower()) if p else None

        # Filter by original square.
        from_mask = BB_ALL
        if match.group(2):
            from_file = FILE_NAMES.index(match.group(2))
            from_mask &= BB_FILES[from_file]
        if match.group(3):
            from_rank = int(match.group(3)) - 1
            from_mask &= BB_RANKS[from_rank]

        # Filter by piece type.
        if match.group(1):
            piece_type = PIECE_SYMBOLS.index(match.group(1).lower())
            from_mask &= self.pieces_mask(piece_type, self.turn)
        elif match.group(2) and match.group(3):
            # Allow fully specified moves, even if they are not pawn moves,
            # including castling moves.
            move = self.find_move(square(from_file, from_rank), to_square, promotion)
            if move.promotion == promotion:
                return move
            else:
                raise IllegalMoveError(f"missing promotion piece type: {san!r} in {self.fen()}")
        else:
            from_mask &= self.pawns

            # Do not allow pawn captures if file is not specified.
            if not match.group(2):
                from_mask &= BB_FILES[square_file(to_square)]

        # Match legal moves.
        matched_move = None
        for move in self.generate_legal_moves(from_mask, to_mask):
            if move.promotion != promotion:
                continue

            if matched_move:
                raise AmbiguousMoveError(f"ambiguous san: {san!r} in {self.fen()}")

            matched_move = move

        if not matched_move:
            raise IllegalMoveError(f"illegal san: {san!r} in {self.fen()}")

        return matched_move

    def push_san(self, san: str) -> Move:
        """
        Parses a move in standard algebraic notation, makes the move and puts
        it onto the move stack.

        Returns the move.

        :raises:
            :exc:`ValueError` (specifically an exception specified below) if neither legal nor a null move.

            - :exc:`InvalidMoveError` if the SAN is syntactically invalid.
            - :exc:`IllegalMoveError` if the SAN is illegal.
            - :exc:`AmbiguousMoveError` if the SAN is ambiguous.
        """
        move = self.parse_san(san)
        self.push(move)
        return move

    def uci(self, move: Move, *, chess960: Optional[bool] = None) -> str:
        """
        Gets the UCI notation of the move.

        *chess960* defaults to the mode of the board. Pass ``True`` to force
        Chess960 mode.
        """
        if chess960 is None:
            chess960 = self.chess960

        move = self._to_chess960(move)
        move = self._from_chess960(chess960, move.from_square, move.to_square, move.promotion, move.drop)
        return move.uci()

    def parse_uci(self, uci: str) -> Move:
        """
        Parses the given move in UCI notation.

        Supports both Chess960 and standard UCI notation.

        The returned move is guaranteed to be either legal or a null move.

        :raises:
            :exc:`ValueError` (specifically an exception specified below) if the move is invalid or illegal in the
            current position (but not a null move).

            - :exc:`InvalidMoveError` if the UCI is syntactically invalid.
            - :exc:`IllegalMoveError` if the UCI is illegal.
        """
        move = Move.from_uci(uci)

        if not move:
            return move

        move = self._to_chess960(move)
        move = self._from_chess960(self.chess960, move.from_square, move.to_square, move.promotion, move.drop)

        if not self.is_legal(move):
            raise IllegalMoveError(f"illegal uci: {uci!r} in {self.fen()}")

        return move

    def push_uci(self, uci: str) -> Move:
        """
        Parses a move in UCI notation and puts it on the move stack.

        Returns the move.

        :raises:
            :exc:`ValueError` (specifically an exception specified below) if the move is invalid or illegal in the
            current position (but not a null move).

            - :exc:`InvalidMoveError` if the UCI is syntactically invalid.
            - :exc:`IllegalMoveError` if the UCI is illegal.
        """
        move = self.parse_uci(uci)
        self.push(move)
        return move

    def xboard(self, move: Move, chess960: Optional[bool] = None) -> str:
        if chess960 is None:
            chess960 = self.chess960

        if not chess960 or not self.is_castling(move):
            return move.xboard()
        elif self.is_kingside_castling(move):
            return "O-O"
        else:
            return "O-O-O"

    def parse_xboard(self, xboard: str) -> Move:
        return self.parse_san(xboard)

    push_xboard = push_san

    def is_en_passant(self, move: Move) -> bool:
        """Checks if the given pseudo-legal move is an en passant capture."""
        return (self.ep_square == move.to_square and
                bool(self.pawns & BB_SQUARES[move.from_square]) and
                abs(move.to_square - move.from_square) in [7, 9] and
                not self.occupied & BB_SQUARES[move.to_square])

    def is_capture(self, move: Move) -> bool:
        """Checks if the given pseudo-legal move is a capture."""
        touched = BB_SQUARES[move.from_square] ^ BB_SQUARES[move.to_square]
        return bool(touched & self.occupied_co[not self.turn]) or self.is_en_passant(move)

    def is_zeroing(self, move: Move) -> bool:
        """Checks if the given pseudo-legal move is a capture or pawn move."""
        touched = BB_SQUARES[move.from_square] ^ BB_SQUARES[move.to_square]
        return bool(touched & self.pawns or touched & self.occupied_co[not self.turn] or move.drop == PAWN)

    def _reduces_castling_rights(self, move: Move) -> bool:
        cr = self.clean_castling_rights()
        touched = BB_SQUARES[move.from_square] ^ BB_SQUARES[move.to_square]
        return bool(touched & cr or
                    cr & BB_RANK_1 and touched & self.kings & self.occupied_co[WHITE] & ~self.promoted or
                    cr & BB_RANK_8 and touched & self.kings & self.occupied_co[BLACK] & ~self.promoted)

    def is_irreversible(self, move: Move) -> bool:
        """
        Checks if the given pseudo-legal move is irreversible.

        In standard chess, pawn moves, captures, moves that destroy castling
        rights and moves that cede en passant are irreversible.

        This method has false-negatives with forced lines. For example, a check
        that will force the king to lose castling rights is not considered
        irreversible. Only the actual king move is.
        """
        return self.is_zeroing(move) or self._reduces_castling_rights(move) or self.has_legal_en_passant()

    def is_castling(self, move: Move) -> bool:
        """Checks if the given pseudo-legal move is a castling move."""
        if self.kings & BB_SQUARES[move.from_square]:
            diff = square_file(move.from_square) - square_file(move.to_square)
            return abs(diff) > 1 or bool(self.rooks & self.occupied_co[self.turn] & BB_SQUARES[move.to_square])
        return False

    def is_kingside_castling(self, move: Move) -> bool:
        """
        Checks if the given pseudo-legal move is a kingside castling move.
        """
        return self.is_castling(move) and square_file(move.to_square) > square_file(move.from_square)

    def is_queenside_castling(self, move: Move) -> bool:
        """
        Checks if the given pseudo-legal move is a queenside castling move.
        """
        return self.is_castling(move) and square_file(move.to_square) < square_file(move.from_square)

    def clean_castling_rights(self) -> Bitboard:
        """
        Returns valid castling rights filtered from
        :data:`~chess.Board.castling_rights`.
        """
        if self._stack:
            # No new castling rights are assigned in a game, so we can assume
            # they were filtered already.
            return self.castling_rights

        castling = self.castling_rights & self.rooks
        white_castling = castling & BB_RANK_1 & self.occupied_co[WHITE]
        black_castling = castling & BB_RANK_8 & self.occupied_co[BLACK]

        if not self.chess960:
            # The rooks must be on a1, h1, a8 or h8.
            white_castling &= (BB_A1 | BB_H1)
            black_castling &= (BB_A8 | BB_H8)

            # The kings must be on e1 or e8.
            if not self.occupied_co[WHITE] & self.kings & ~self.promoted & BB_E1:
                white_castling = 0
            if not self.occupied_co[BLACK] & self.kings & ~self.promoted & BB_E8:
                black_castling = 0

            return white_castling | black_castling
        else:
            # The kings must be on the back rank.
            white_king_mask = self.occupied_co[WHITE] & self.kings & BB_RANK_1 & ~self.promoted
            black_king_mask = self.occupied_co[BLACK] & self.kings & BB_RANK_8 & ~self.promoted
            if not white_king_mask:
                white_castling = 0
            if not black_king_mask:
                black_castling = 0

            # There are only two ways of castling, a-side and h-side, and the
            # king must be between the rooks.
            white_a_side = white_castling & -white_castling
            white_h_side = BB_SQUARES[msb(white_castling)] if white_castling else 0

            if white_a_side and msb(white_a_side) > msb(white_king_mask):
                white_a_side = 0
            if white_h_side and msb(white_h_side) < msb(white_king_mask):
                white_h_side = 0

            black_a_side = black_castling & -black_castling
            black_h_side = BB_SQUARES[msb(black_castling)] if black_castling else BB_EMPTY

            if black_a_side and msb(black_a_side) > msb(black_king_mask):
                black_a_side = 0
            if black_h_side and msb(black_h_side) < msb(black_king_mask):
                black_h_side = 0

            # Done.
            return black_a_side | black_h_side | white_a_side | white_h_side

    def has_castling_rights(self, color: Color) -> bool:
        """Checks if the given side has castling rights."""
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
        return bool(self.clean_castling_rights() & backrank)

    def has_kingside_castling_rights(self, color: Color) -> bool:
        """
        Checks if the given side has kingside (that is h-side in Chess960)
        castling rights.
        """
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
        king_mask = self.kings & self.occupied_co[color] & backrank & ~self.promoted
        if not king_mask:
            return False

        castling_rights = self.clean_castling_rights() & backrank
        while castling_rights:
            rook = castling_rights & -castling_rights

            if rook > king_mask:
                return True

            castling_rights &= castling_rights - 1

        return False

    def has_queenside_castling_rights(self, color: Color) -> bool:
        """
        Checks if the given side has queenside (that is a-side in Chess960)
        castling rights.
        """
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
        king_mask = self.kings & self.occupied_co[color] & backrank & ~self.promoted
        if not king_mask:
            return False

        castling_rights = self.clean_castling_rights() & backrank
        while castling_rights:
            rook = castling_rights & -castling_rights

            if rook < king_mask:
                return True

            castling_rights &= castling_rights - 1

        return False

    def has_chess960_castling_rights(self) -> bool:
        """
        Checks if there are castling rights that are only possible in Chess960.
        """
        # Get valid Chess960 castling rights.
        chess960 = self.chess960
        self.chess960 = True
        castling_rights = self.clean_castling_rights()
        self.chess960 = chess960

        # Standard chess castling rights can only be on the standard
        # starting rook squares.
        if castling_rights & ~BB_CORNERS:
            return True

        # If there are any castling rights in standard chess, the king must be
        # on e1 or e8.
        if castling_rights & BB_RANK_1 and not self.occupied_co[WHITE] & self.kings & BB_E1:
            return True
        if castling_rights & BB_RANK_8 and not self.occupied_co[BLACK] & self.kings & BB_E8:
            return True

        return False

    def status(self) -> Status:
        """
        Gets a bitmask of possible problems with the position.

        :data:`~chess.STATUS_VALID` if all basic validity requirements are met.
        This does not imply that the position is actually reachable with a
        series of legal moves from the starting position.

        Otherwise, bitwise combinations of:
        :data:`~chess.STATUS_NO_WHITE_KING`,
        :data:`~chess.STATUS_NO_BLACK_KING`,
        :data:`~chess.STATUS_TOO_MANY_KINGS`,
        :data:`~chess.STATUS_TOO_MANY_WHITE_PAWNS`,
        :data:`~chess.STATUS_TOO_MANY_BLACK_PAWNS`,
        :data:`~chess.STATUS_PAWNS_ON_BACKRANK`,
        :data:`~chess.STATUS_TOO_MANY_WHITE_PIECES`,
        :data:`~chess.STATUS_TOO_MANY_BLACK_PIECES`,
        :data:`~chess.STATUS_BAD_CASTLING_RIGHTS`,
        :data:`~chess.STATUS_INVALID_EP_SQUARE`,
        :data:`~chess.STATUS_OPPOSITE_CHECK`,
        :data:`~chess.STATUS_EMPTY`,
        :data:`~chess.STATUS_RACE_CHECK`,
        :data:`~chess.STATUS_RACE_OVER`,
        :data:`~chess.STATUS_RACE_MATERIAL`,
        :data:`~chess.STATUS_TOO_MANY_CHECKERS`,
        :data:`~chess.STATUS_IMPOSSIBLE_CHECK`.
        """
        errors = STATUS_VALID

        # There must be at least one piece.
        if not self.occupied:
            errors |= STATUS_EMPTY

        # There must be exactly one king of each color.
        if not self.occupied_co[WHITE] & self.kings:
            errors |= STATUS_NO_WHITE_KING
        if not self.occupied_co[BLACK] & self.kings:
            errors |= STATUS_NO_BLACK_KING
        if popcount(self.occupied & self.kings) > 2:
            errors |= STATUS_TOO_MANY_KINGS

        # There can not be more than 16 pieces of any color.
        if popcount(self.occupied_co[WHITE]) > 16:
            errors |= STATUS_TOO_MANY_WHITE_PIECES
        if popcount(self.occupied_co[BLACK]) > 16:
            errors |= STATUS_TOO_MANY_BLACK_PIECES

        # There can not be more than 8 pawns of any color.
        if popcount(self.occupied_co[WHITE] & self.pawns) > 8:
            errors |= STATUS_TOO_MANY_WHITE_PAWNS
        if popcount(self.occupied_co[BLACK] & self.pawns) > 8:
            errors |= STATUS_TOO_MANY_BLACK_PAWNS

        # Pawns can not be on the back rank.
        if self.pawns & BB_BACKRANKS:
            errors |= STATUS_PAWNS_ON_BACKRANK

        # Castling rights.
        if self.castling_rights != self.clean_castling_rights():
            errors |= STATUS_BAD_CASTLING_RIGHTS

        # En passant.
        valid_ep_square = self._valid_ep_square()
        if self.ep_square != valid_ep_square:
            errors |= STATUS_INVALID_EP_SQUARE

        # Side to move giving check.
        if self.was_into_check():
            errors |= STATUS_OPPOSITE_CHECK

        # More than the maximum number of possible checkers in the variant.
        checkers = self.checkers_mask()
        our_kings = self.kings & self.occupied_co[self.turn] & ~self.promoted
        if checkers:
            if popcount(checkers) > 2:
                errors |= STATUS_TOO_MANY_CHECKERS

            if valid_ep_square is not None:
                pushed_to = valid_ep_square ^ A2
                pushed_from = valid_ep_square ^ A4
                occupied_before = (self.occupied & ~BB_SQUARES[pushed_to]) | BB_SQUARES[pushed_from]
                if popcount(checkers) > 1 or (
                        msb(checkers) != pushed_to and
                        self._attacked_for_king(our_kings, occupied_before)):
                    errors |= STATUS_IMPOSSIBLE_CHECK
            else:
                if popcount(checkers) > 2 or (popcount(checkers) == 2 and ray(lsb(checkers), msb(checkers)) & our_kings):
                    errors |= STATUS_IMPOSSIBLE_CHECK

        return errors

    def _valid_ep_square(self) -> Optional[Square]:
        if not self.ep_square:
            return None

        if self.turn == WHITE:
            ep_rank = 5
            pawn_mask = shift_down(BB_SQUARES[self.ep_square])
            seventh_rank_mask = shift_up(BB_SQUARES[self.ep_square])
        else:
            ep_rank = 2
            pawn_mask = shift_up(BB_SQUARES[self.ep_square])
            seventh_rank_mask = shift_down(BB_SQUARES[self.ep_square])

        # The en passant square must be on the third or sixth rank.
        if square_rank(self.ep_square) != ep_rank:
            return None

        # The last move must have been a double pawn push, so there must
        # be a pawn of the correct color on the fourth or fifth rank.
        if not self.pawns & self.occupied_co[not self.turn] & pawn_mask:
            return None

        # And the en passant square must be empty.
        if self.occupied & BB_SQUARES[self.ep_square]:
            return None

        # And the second rank must be empty.
        if self.occupied & seventh_rank_mask:
            return None

        return self.ep_square

    def is_valid(self) -> bool:
        """
        Checks some basic validity requirements.

        See :func:`~chess.Board.status()` for details.
        """
        return self.status() == STATUS_VALID

    def _ep_skewered(self, king: Square, capturer: Square) -> bool:
        # Handle the special case where the king would be in check if the
        # pawn and its capturer disappear from the rank.

        # Vertical skewers of the captured pawn are not possible. (Pins on
        # the capturer are not handled here.)
        assert self.ep_square is not None

        last_double = self.ep_square + (-8 if self.turn == WHITE else 8)

        occupancy = (self.occupied & ~BB_SQUARES[last_double] &
                     ~BB_SQUARES[capturer] | BB_SQUARES[self.ep_square])

        # Horizontal attack on the fifth or fourth rank.
        horizontal_attackers = self.occupied_co[not self.turn] & (self.rooks | self.queens)
        if BB_RANK_ATTACKS[king][BB_RANK_MASKS[king] & occupancy] & horizontal_attackers:
            return True

        # Diagonal skewers. These are not actually possible in a real game,
        # because if the latest double pawn move covers a diagonal attack,
        # then the other side would have been in check already.
        diagonal_attackers = self.occupied_co[not self.turn] & (self.bishops | self.queens)
        if BB_DIAG_ATTACKS[king][BB_DIAG_MASKS[king] & occupancy] & diagonal_attackers:
            return True

        return False

    def _slider_blockers(self, king: Square) -> Bitboard:
        rooks_and_queens = self.rooks | self.queens
        bishops_and_queens = self.bishops | self.queens

        snipers = ((BB_RANK_ATTACKS[king][0] & rooks_and_queens) |
                   (BB_FILE_ATTACKS[king][0] & rooks_and_queens) |
                   (BB_DIAG_ATTACKS[king][0] & bishops_and_queens))

        blockers = 0

        for sniper in scan_reversed(snipers & self.occupied_co[not self.turn]):
            b = between(king, sniper) & self.occupied

            # Add to blockers if exactly one piece in-between.
            if b and BB_SQUARES[msb(b)] == b:
                blockers |= b

        return blockers & self.occupied_co[self.turn]

    def _is_safe(self, king: Square, blockers: Bitboard, move: Move) -> bool:
        if move.from_square == king:
            if self.is_castling(move):
                return True
            else:
                return not self.is_attacked_by(not self.turn, move.to_square)
        elif self.is_en_passant(move):
            return bool(self.pin_mask(self.turn, move.from_square) & BB_SQUARES[move.to_square] and
                        not self._ep_skewered(king, move.from_square))
        else:
            return bool(not blockers & BB_SQUARES[move.from_square] or
                        ray(move.from_square, move.to_square) & BB_SQUARES[king])

    def _generate_evasions(self, king: Square, checkers: Bitboard, from_mask: Bitboard = BB_ALL, to_mask: Bitboard = BB_ALL) -> Iterator[Move]:
        sliders = checkers & (self.bishops | self.rooks | self.queens)

        attacked = 0
        for checker in scan_reversed(sliders):
            attacked |= ray(king, checker) & ~BB_SQUARES[checker]

        if BB_SQUARES[king] & from_mask:
            for to_square in scan_reversed(BB_KING_ATTACKS[king] & ~self.occupied_co[self.turn] & ~attacked & to_mask):
                yield Move(king, to_square)

        checker = msb(checkers)
        if BB_SQUARES[checker] == checkers:
            # Capture or block a single checker.
            target = between(king, checker) | checkers

            yield from self.generate_pseudo_legal_moves(~self.kings & from_mask, target & to_mask)

            # Capture the checking pawn en passant (but avoid yielding
            # duplicate moves).
            if self.ep_square and not BB_SQUARES[self.ep_square] & target:
                last_double = self.ep_square + (-8 if self.turn == WHITE else 8)
                if last_double == checker:
                    yield from self.generate_pseudo_legal_ep(from_mask, to_mask)

    def generate_legal_moves(self, from_mask: Bitboard = BB_ALL, to_mask: Bitboard = BB_ALL) -> Iterator[Move]:
        if self.is_variant_end():
            return

        king_mask = self.kings & self.occupied_co[self.turn]
        if king_mask:
            king = msb(king_mask)
            blockers = self._slider_blockers(king)
            checkers = self.attackers_mask(not self.turn, king)
            if checkers:
                for move in self._generate_evasions(king, checkers, from_mask, to_mask):
                    if self._is_safe(king, blockers, move):
                        yield move
            else:
                for move in self.generate_pseudo_legal_moves(from_mask, to_mask):
                    if self._is_safe(king, blockers, move):
                        yield move
        else:
            yield from self.generate_pseudo_legal_moves(from_mask, to_mask)

    def generate_legal_ep(self, from_mask: Bitboard = BB_ALL, to_mask: Bitboard = BB_ALL) -> Iterator[Move]:
        if self.is_variant_end():
            return

        for move in self.generate_pseudo_legal_ep(from_mask, to_mask):
            if not self.is_into_check(move):
                yield move

    def generate_legal_captures(self, from_mask: Bitboard = BB_ALL, to_mask: Bitboard = BB_ALL) -> Iterator[Move]:
        return itertools.chain(
            self.generate_legal_moves(from_mask, to_mask & self.occupied_co[not self.turn]),
            self.generate_legal_ep(from_mask, to_mask))

    def _attacked_for_king(self, path: Bitboard, occupied: Bitboard) -> bool:
        return any(self.attackers_mask(not self.turn, sq, occupied) for sq in scan_reversed(path))

    def generate_castling_moves(self, from_mask: Bitboard = BB_ALL, to_mask: Bitboard = BB_ALL) -> Iterator[Move]:
        if self.is_variant_end():
            return

        backrank = BB_RANK_1 if self.turn == WHITE else BB_RANK_8
        king = self.occupied_co[self.turn] & self.kings & ~self.promoted & backrank & from_mask
        king &= -king
        if not king:
            return

        bb_c = BB_FILE_C & backrank
        bb_d = BB_FILE_D & backrank
        bb_f = BB_FILE_F & backrank
        bb_g = BB_FILE_G & backrank

        for candidate in scan_reversed(self.clean_castling_rights() & backrank & to_mask):
            rook = BB_SQUARES[candidate]

            a_side = rook < king
            king_to = bb_c if a_side else bb_g
            rook_to = bb_d if a_side else bb_f

            king_path = between(msb(king), msb(king_to))
            rook_path = between(candidate, msb(rook_to))

            if not ((self.occupied ^ king ^ rook) & (king_path | rook_path | king_to | rook_to) or
                    self._attacked_for_king(king_path | king, self.occupied ^ king) or
                    self._attacked_for_king(king_to, self.occupied ^ king ^ rook ^ rook_to)):
                yield self._from_chess960(self.chess960, msb(king), candidate)

    def _from_chess960(self, chess960: bool, from_square: Square, to_square: Square, promotion: Optional[PieceType] = None, drop: Optional[PieceType] = None) -> Move:
        if not chess960 and promotion is None and drop is None:
            if from_square == E1 and self.kings & BB_E1:
                if to_square == H1:
                    return Move(E1, G1)
                elif to_square == A1:
                    return Move(E1, C1)
            elif from_square == E8 and self.kings & BB_E8:
                if to_square == H8:
                    return Move(E8, G8)
                elif to_square == A8:
                    return Move(E8, C8)

        return Move(from_square, to_square, promotion, drop)

    def _to_chess960(self, move: Move) -> Move:
        if move.from_square == E1 and self.kings & BB_E1:
            if move.to_square == G1 and not self.rooks & BB_G1:
                return Move(E1, H1)
            elif move.to_square == C1 and not self.rooks & BB_C1:
                return Move(E1, A1)
        elif move.from_square == E8 and self.kings & BB_E8:
            if move.to_square == G8 and not self.rooks & BB_G8:
                return Move(E8, H8)
            elif move.to_square == C8 and not self.rooks & BB_C8:
                return Move(E8, A8)

        return move

    def _transposition_key(self) -> Hashable:
        return (self.pawns, self.knights, self.bishops, self.rooks,
                self.queens, self.kings,
                self.occupied_co[WHITE], self.occupied_co[BLACK],
                self.turn, self.clean_castling_rights(),
                self.ep_square if self.has_legal_en_passant() else None)

    def __repr__(self) -> str:
        if not self.chess960:
            return f"{type(self).__name__}({self.fen()!r})"
        else:
            return f"{type(self).__name__}({self.fen()!r}, chess960=True)"

    def _repr_svg_(self) -> str:
        import chess.svg
        return chess.svg.board(
            board=self,
            size=390,
            lastmove=self.peek() if self.move_stack else None,
            check=self.king(self.turn) if self.is_check() else None)

    def __eq__(self, board: object) -> bool:
        if isinstance(board, Board):
            return (
                self.halfmove_clock == board.halfmove_clock and
                self.fullmove_number == board.fullmove_number and
                type(self).uci_variant == type(board).uci_variant and
                self._transposition_key() == board._transposition_key())
        else:
            return NotImplemented

    def apply_transform(self, f: Callable[[Bitboard], Bitboard]) -> None:
        super().apply_transform(f)
        self.clear_stack()
        self.ep_square = None if self.ep_square is None else msb(f(BB_SQUARES[self.ep_square]))
        self.castling_rights = f(self.castling_rights)

    def transform(self, f: Callable[[Bitboard], Bitboard]) -> Self:
        board = self.copy(stack=False)
        board.apply_transform(f)
        return board

    def apply_mirror(self) -> None:
        super().apply_mirror()
        self.turn = not self.turn

    def mirror(self) -> Self:
        """
        Returns a mirrored copy of the board.

        The board is mirrored vertically and piece colors are swapped, so that
        the position is equivalent modulo color. Also swap the "en passant"
        square, castling rights and turn.

        Alternatively, :func:`~chess.Board.apply_mirror()` can be used
        to mirror the board.
        """
        board = self.copy()
        board.apply_mirror()
        return board

    def copy(self, *, stack: Union[bool, int] = True) -> Self:
        """
        Creates a copy of the board.

        Defaults to copying the entire move stack. Alternatively, *stack* can
        be ``False``, or an integer to copy a limited number of moves.
        """
        board = super().copy()

        board.chess960 = self.chess960

        board.ep_square = self.ep_square
        board.castling_rights = self.castling_rights
        board.turn = self.turn
        board.fullmove_number = self.fullmove_number
        board.halfmove_clock = self.halfmove_clock

        if stack:
            stack = len(self.move_stack) if stack is True else stack
            board.move_stack = [copy.copy(move) for move in self.move_stack[-stack:]]
            board._stack = self._stack[-stack:]

        return board

    @classmethod
    def empty(cls: Type[BoardT], *, chess960: bool = False) -> BoardT:
        """Creates a new empty board. Also see :func:`~chess.Board.clear()`."""
        return cls(None, chess960=chess960)

    @classmethod
    def from_epd(cls: Type[BoardT], epd: str, *, chess960: bool = False) -> Tuple[BoardT, Dict[str, Union[None, str, int, float, Move, List[Move]]]]:
        """
        Creates a new board from an EPD string. See
        :func:`~chess.Board.set_epd()`.

        Returns the board and the dictionary of parsed operations as a tuple.
        """
        board = cls.empty(chess960=chess960)
        return board, board.set_epd(epd)

    @classmethod
    def from_chess960_pos(cls: Type[BoardT], scharnagl: int) -> BoardT:
        board = cls.empty(chess960=True)
        board.set_chess960_pos(scharnagl)
        return board


class PseudoLegalMoveGenerator:

    def __init__(self, board: Board) -> None:
        self.board = board

    def __bool__(self) -> bool:
        return any(self.board.generate_pseudo_legal_moves())

    def count(self) -> int:
        # List conversion is faster than iterating.
        return len(list(self))

    def __iter__(self) -> Iterator[Move]:
        return self.board.generate_pseudo_legal_moves()

    def __contains__(self, move: Move) -> bool:
        return self.board.is_pseudo_legal(move)

    def __repr__(self) -> str:
        builder: List[str] = []

        for move in self:
            if self.board.is_legal(move):
                builder.append(self.board.san(move))
            else:
                builder.append(self.board.uci(move))

        sans = ", ".join(builder)
        return f"<PseudoLegalMoveGenerator at {id(self):#x} ({sans})>"


class LegalMoveGenerator:

    def __init__(self, board: Board) -> None:
        self.board = board

    def __bool__(self) -> bool:
        return any(self.board.generate_legal_moves())

    def count(self) -> int:
        # List conversion is faster than iterating.
        return len(list(self))

    def __iter__(self) -> Iterator[Move]:
        return self.board.generate_legal_moves()

    def __contains__(self, move: Move) -> bool:
        return self.board.is_legal(move)

    def __repr__(self) -> str:
        sans = ", ".join(self.board.san(move) for move in self)
        return f"<LegalMoveGenerator at {id(self):#x} ({sans})>"


IntoSquareSet: TypeAlias = Union[SupportsInt, Iterable[Square]]

class SquareSet:
    """
    A set of squares.

    >>> import chess
    >>>
    >>> squares = chess.SquareSet([chess.A8, chess.A1])
    >>> squares
    SquareSet(0x0100_0000_0000_0001)

    >>> squares = chess.SquareSet(chess.BB_A8 | chess.BB_RANK_1)
    >>> squares
    SquareSet(0x0100_0000_0000_00ff)

    >>> print(squares)
    1 . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    . . . . . . . .
    1 1 1 1 1 1 1 1

    >>> len(squares)
    9

    >>> bool(squares)
    True

    >>> chess.B1 in squares
    True

    >>> for square in squares:
    ...     # 0 -- chess.A1
    ...     # 1 -- chess.B1
    ...     # 2 -- chess.C1
    ...     # 3 -- chess.D1
    ...     # 4 -- chess.E1
    ...     # 5 -- chess.F1
    ...     # 6 -- chess.G1
    ...     # 7 -- chess.H1
    ...     # 56 -- chess.A8
    ...     print(square)
    ...
    0
    1
    2
    3
    4
    5
    6
    7
    56

    >>> list(squares)
    [0, 1, 2, 3, 4, 5, 6, 7, 56]

    Square sets are internally represented by 64-bit integer masks of the
    included squares. Bitwise operations can be used to compute unions,
    intersections and shifts.

    >>> int(squares)
    72057594037928191

    Also supports common set operations like
    :func:`~chess.SquareSet.issubset()`, :func:`~chess.SquareSet.issuperset()`,
    :func:`~chess.SquareSet.union()`, :func:`~chess.SquareSet.intersection()`,
    :func:`~chess.SquareSet.difference()`,
    :func:`~chess.SquareSet.symmetric_difference()` and
    :func:`~chess.SquareSet.copy()` as well as
    :func:`~chess.SquareSet.update()`,
    :func:`~chess.SquareSet.intersection_update()`,
    :func:`~chess.SquareSet.difference_update()`,
    :func:`~chess.SquareSet.symmetric_difference_update()` and
    :func:`~chess.SquareSet.clear()`.
    """

    def __init__(self, squares: IntoSquareSet = BB_EMPTY) -> None:
        try:
            self.mask: Bitboard = squares.__int__() & BB_ALL  # type: ignore
            return
        except AttributeError:
            self.mask = 0

        # Try squares as an iterable. Not under except clause for nicer
        # backtraces.
        for square in squares:  # type: ignore
            self.add(square)

    # Set

    def __contains__(self, square: Square) -> bool:
        return bool(BB_SQUARES[square] & self.mask)

    def __iter__(self) -> Iterator[Square]:
        return scan_forward(self.mask)

    def __reversed__(self) -> Iterator[Square]:
        return scan_reversed(self.mask)

    def __len__(self) -> int:
        return popcount(self.mask)

    # MutableSet

    def add(self, square: Square) -> None:
        """Adds a square to the set."""
        self.mask |= BB_SQUARES[square]

    def discard(self, square: Square) -> None:
        """Discards a square from the set."""
        self.mask &= ~BB_SQUARES[square]

    # frozenset

    def isdisjoint(self, other: IntoSquareSet) -> bool:
        """Tests if the square sets are disjoint."""
        return not bool(self & other)

    def issubset(self, other: IntoSquareSet) -> bool:
        """Tests if this square set is a subset of another."""
        return not bool(self & ~SquareSet(other))

    def issuperset(self, other: IntoSquareSet) -> bool:
        """Tests if this square set is a superset of another."""
        return not bool(~self & other)

    def union(self, other: IntoSquareSet) -> SquareSet:
        return self | other

    def __or__(self, other: IntoSquareSet) -> SquareSet:
        r = SquareSet(other)
        r.mask |= self.mask
        return r

    def intersection(self, other: IntoSquareSet) -> SquareSet:
        return self & other

    def __and__(self, other: IntoSquareSet) -> SquareSet:
        r = SquareSet(other)
        r.mask &= self.mask
        return r

    def difference(self, other: IntoSquareSet) -> SquareSet:
        return self - other

    def __sub__(self, other: IntoSquareSet) -> SquareSet:
        r = SquareSet(other)
        r.mask = self.mask & ~r.mask
        return r

    def symmetric_difference(self, other: IntoSquareSet) -> SquareSet:
        return self ^ other

    def __xor__(self, other: IntoSquareSet) -> SquareSet:
        r = SquareSet(other)
        r.mask ^= self.mask
        return r

    def copy(self) -> SquareSet:
        return SquareSet(self.mask)

    # set

    def update(self, *others: IntoSquareSet) -> None:
        for other in others:
            self |= other

    def __ior__(self, other: IntoSquareSet) -> SquareSet:
        self.mask |= SquareSet(other).mask
        return self

    def intersection_update(self, *others: IntoSquareSet) -> None:
        for other in others:
            self &= other

    def __iand__(self, other: IntoSquareSet) -> SquareSet:
        self.mask &= SquareSet(other).mask
        return self

    def difference_update(self, other: IntoSquareSet) -> None:
        self -= other

    def __isub__(self, other: IntoSquareSet) -> SquareSet:
        self.mask &= ~SquareSet(other).mask
        return self

    def symmetric_difference_update(self, other: IntoSquareSet) -> None:
        self ^= other

    def __ixor__(self, other: IntoSquareSet) -> SquareSet:
        self.mask ^= SquareSet(other).mask
        return self

    def remove(self, square: Square) -> None:
        """
        Removes a square from the set.

        :raises: :exc:`KeyError` if the given *square* was not in the set.
        """
        mask = BB_SQUARES[square]
        if self.mask & mask:
            self.mask ^= mask
        else:
            raise KeyError(square)

    def pop(self) -> Square:
        """
        Removes and returns a square from the set.

        :raises: :exc:`KeyError` if the set is empty.
        """
        if not self.mask:
            raise KeyError("pop from empty SquareSet")

        square = lsb(self.mask)
        self.mask &= (self.mask - 1)
        return square

    def clear(self) -> None:
        """Removes all elements from this set."""
        self.mask = BB_EMPTY

    # SquareSet

    def carry_rippler(self) -> Iterator[Bitboard]:
        """Iterator over the subsets of this set."""
        return _carry_rippler(self.mask)

    def mirror(self) -> SquareSet:
        """Returns a vertically mirrored copy of this square set."""
        return SquareSet(flip_vertical(self.mask))

    def tolist(self) -> List[bool]:
        """Converts the set to a list of 64 bools."""
        result = [False] * 64
        for square in self:
            result[square] = True
        return result

    def __bool__(self) -> bool:
        return bool(self.mask)

    def __eq__(self, other: object) -> bool:
        try:
            return self.mask == SquareSet(other).mask  # type: ignore
        except (TypeError, ValueError):
            return NotImplemented

    def __lshift__(self, shift: int) -> SquareSet:
        return SquareSet((self.mask << shift) & BB_ALL)

    def __rshift__(self, shift: int) -> SquareSet:
        return SquareSet(self.mask >> shift)

    def __ilshift__(self, shift: int) -> SquareSet:
        self.mask = (self.mask << shift) & BB_ALL
        return self

    def __irshift__(self, shift: int) -> SquareSet:
        self.mask >>= shift
        return self

    def __invert__(self) -> SquareSet:
        return SquareSet(~self.mask & BB_ALL)

    def __int__(self) -> int:
        return self.mask

    def __index__(self) -> int:
        return self.mask

    def __repr__(self) -> str:
        return f"SquareSet({self.mask:#021_x})"

    def __str__(self) -> str:
        builder: List[str] = []

        for square in SQUARES_180:
            mask = BB_SQUARES[square]
            builder.append("1" if self.mask & mask else ".")

            if not mask & BB_FILE_H:
                builder.append(" ")
            elif square != H1:
                builder.append("\n")

        return "".join(builder)

    def _repr_svg_(self) -> str:
        import chess.svg
        return chess.svg.board(squares=self, size=390)

    @classmethod
    def ray(cls, a: Square, b: Square) -> SquareSet:
        """
        All squares on the rank, file or diagonal with the two squares, if they
        are aligned.

        >>> import chess
        >>>
        >>> print(chess.SquareSet.ray(chess.E2, chess.B5))
        . . . . . . . .
        . . . . . . . .
        1 . . . . . . .
        . 1 . . . . . .
        . . 1 . . . . .
        . . . 1 . . . .
        . . . . 1 . . .
        . . . . . 1 . .
        """
        return cls(ray(a, b))

    @classmethod
    def between(cls, a: Square, b: Square) -> SquareSet:
        """
        All squares on the rank, file or diagonal between the two squares
        (bounds not included), if they are aligned.

        >>> import chess
        >>>
        >>> print(chess.SquareSet.between(chess.E2, chess.B5))
        . . . . . . . .
        . . . . . . . .
        . . . . . . . .
        . . . . . . . .
        . . 1 . . . . .
        . . . 1 . . . .
        . . . . . . . .
        . . . . . . . .
        """
        return cls(between(a, b))

    @classmethod
    def from_square(cls, square: Square) -> SquareSet:
        """
        Creates a :class:`~chess.SquareSet` from a single square.

        >>> import chess
        >>>
        >>> chess.SquareSet.from_square(chess.A1) == chess.BB_A1
        True
        """
        return cls(BB_SQUARES[square])
