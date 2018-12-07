# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2018 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

"""
A pure Python chess library with move generation and validation, Polyglot
opening book probing, PGN reading and writing, Gaviota tablebase probing,
Syzygy tablebase probing and XBoard/UCI engine communication.
"""

__author__ = "Niklas Fiekas"

__email__ = "niklas.fiekas@backscattering.de"

__version__ = "0.24.1"

import collections
import collections.abc
import copy
import enum
import re
import itertools
import struct


COLORS = [WHITE, BLACK] = [True, False]
COLOR_NAMES = ["black", "white"]
Color = bool

PIECE_TYPES = [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING] = range(1, 7)
PIECE_SYMBOLS = [None, "p", "n", "b", "r", "q", "k"]
PIECE_NAMES = [None, "pawn", "knight", "bishop", "rook", "queen", "king"]
PieceType = int

UNICODE_PIECE_SYMBOLS = {
    "R": u"♖", "r": u"♜",
    "N": u"♘", "n": u"♞",
    "B": u"♗", "b": u"♝",
    "Q": u"♕", "q": u"♛",
    "K": u"♔", "k": u"♚",
    "P": u"♙", "p": u"♟",
}

FILE_NAMES = ["a", "b", "c", "d", "e", "f", "g", "h"]

RANK_NAMES = ["1", "2", "3", "4", "5", "6", "7", "8"]

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
"""The FEN for the standard chess starting position."""

STARTING_BOARD_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
"""The board part of the FEN for the standard chess starting position."""


try:
    _IntFlag = enum.IntFlag  # Since Python 3.6
except AttributeError:
    _IntFlag = enum.IntEnum

class Status(_IntFlag):
    VALID = 0
    NO_WHITE_KING = 1
    NO_BLACK_KING = 2
    TOO_MANY_KINGS = 4
    TOO_MANY_WHITE_PAWNS = 8
    TOO_MANY_BLACK_PAWNS = 16
    PAWNS_ON_BACKRANK = 32
    TOO_MANY_WHITE_PIECES = 64
    TOO_MANY_BLACK_PIECES = 128
    BAD_CASTLING_RIGHTS = 256
    INVALID_EP_SQUARE = 512
    OPPOSITE_CHECK = 1024
    EMPTY = 2048
    RACE_CHECK = 4096
    RACE_OVER = 8192
    RACE_MATERIAL = 16384

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


SQUARES = [
    A1, B1, C1, D1, E1, F1, G1, H1,
    A2, B2, C2, D2, E2, F2, G2, H2,
    A3, B3, C3, D3, E3, F3, G3, H3,
    A4, B4, C4, D4, E4, F4, G4, H4,
    A5, B5, C5, D5, E5, F5, G5, H5,
    A6, B6, C6, D6, E6, F6, G6, H6,
    A7, B7, C7, D7, E7, F7, G7, H7,
    A8, B8, C8, D8, E8, F8, G8, H8] = range(64)
Square = int

SQUARE_NAMES = [f + r for r in RANK_NAMES for f in FILE_NAMES]

def square(file_index, rank_index):
    """Gets a square number by file and rank index."""
    return rank_index * 8 + file_index

def square_file(square):
    """Gets the file index of the square where ``0`` is the a-file."""
    return square & 7

def square_rank(square):
    """Gets the rank index of the square where ``0`` is the first rank."""
    return square >> 3

def square_name(square):
    """Gets the name of the square, like ``a3``."""
    return SQUARE_NAMES[square]

def square_distance(a, b):
    """
    Gets the distance (i.e., the number of king steps) from square *a* to *b*.
    """
    return max(abs(square_file(a) - square_file(b)), abs(square_rank(a) - square_rank(b)))

def square_mirror(square):
    """Mirrors the square vertically."""
    return square ^ 0x38

SQUARES_180 = [square_mirror(sq) for sq in SQUARES]


BB_EMPTY = 0
BB_ALL = 0xffffffffffffffff

BB_SQUARES = [
    BB_A1, BB_B1, BB_C1, BB_D1, BB_E1, BB_F1, BB_G1, BB_H1,
    BB_A2, BB_B2, BB_C2, BB_D2, BB_E2, BB_F2, BB_G2, BB_H2,
    BB_A3, BB_B3, BB_C3, BB_D3, BB_E3, BB_F3, BB_G3, BB_H3,
    BB_A4, BB_B4, BB_C4, BB_D4, BB_E4, BB_F4, BB_G4, BB_H4,
    BB_A5, BB_B5, BB_C5, BB_D5, BB_E5, BB_F5, BB_G5, BB_H5,
    BB_A6, BB_B6, BB_C6, BB_D6, BB_E6, BB_F6, BB_G6, BB_H6,
    BB_A7, BB_B7, BB_C7, BB_D7, BB_E7, BB_F7, BB_G7, BB_H7,
    BB_A8, BB_B8, BB_C8, BB_D8, BB_E8, BB_F8, BB_G8, BB_H8
] = [1 << sq for sq in SQUARES]

BB_CORNERS = BB_A1 | BB_H1 | BB_A8 | BB_H8
BB_CENTER = BB_D4 | BB_E4 | BB_D5 | BB_E5

BB_LIGHT_SQUARES = 0x55aa55aa55aa55aa
BB_DARK_SQUARES = 0xaa55aa55aa55aa55

BB_FILES = [
    BB_FILE_A,
    BB_FILE_B,
    BB_FILE_C,
    BB_FILE_D,
    BB_FILE_E,
    BB_FILE_F,
    BB_FILE_G,
    BB_FILE_H
] = [0x0101010101010101 << i for i in range(8)]

BB_RANKS = [
    BB_RANK_1,
    BB_RANK_2,
    BB_RANK_3,
    BB_RANK_4,
    BB_RANK_5,
    BB_RANK_6,
    BB_RANK_7,
    BB_RANK_8
] = [0xff << (8 * i) for i in range(8)]

BB_BACKRANKS = BB_RANK_1 | BB_RANK_8


def lsb(bb):
    return (bb & -bb).bit_length() - 1

def scan_forward(bb):
    while bb:
        r = bb & -bb
        yield r.bit_length() - 1
        bb ^= r

def msb(bb):
    return bb.bit_length() - 1

def scan_reversed(bb, *, _BB_SQUARES=BB_SQUARES):
    while bb:
        r = bb.bit_length() - 1
        yield r
        bb ^= _BB_SQUARES[r]

def popcount(bb, *, _bin=bin):
    return _bin(bb).count("1")

def flip_vertical(bb):
    # https://www.chessprogramming.org/Flipping_Mirroring_and_Rotating#FlipVertically
    bb = ((bb >> 8) & 0x00ff00ff00ff00ff) | ((bb & 0x00ff00ff00ff00ff) << 8)
    bb = ((bb >> 16) & 0x0000ffff0000ffff) | ((bb & 0x0000ffff0000ffff) << 16)
    bb = (bb >> 32) | ((bb & 0x00000000ffffffff) << 32)
    return bb

def flip_horizontal(bb):
    # https://www.chessprogramming.org/Flipping_Mirroring_and_Rotating#MirrorHorizontally
    bb = ((bb >> 1) & 0x5555555555555555) | ((bb & 0x5555555555555555) << 1)
    bb = ((bb >> 2) & 0x3333333333333333) | ((bb & 0x3333333333333333) << 2)
    bb = ((bb >> 4) & 0x0f0f0f0f0f0f0f0f) | ((bb & 0x0f0f0f0f0f0f0f0f) << 4)
    return bb

def flip_diagonal(bb):
    # https://www.chessprogramming.org/Flipping_Mirroring_and_Rotating#FlipabouttheDiagonal
    t = (bb ^ (bb << 28)) & 0x0f0f0f0f00000000
    bb = bb ^ (t ^ (t >> 28))
    t = (bb ^ (bb << 14)) & 0x3333000033330000
    bb = bb ^ (t ^ (t >> 14))
    t = (bb ^ (bb << 7)) & 0x5500550055005500
    bb = bb ^ (t ^ (t >> 7))
    return bb

def flip_anti_diagonal(bb):
    # https://www.chessprogramming.org/Flipping_Mirroring_and_Rotating#FlipabouttheAntidiagonal
    t = bb ^ (bb << 36)
    bb = bb ^ ((t ^ (bb >> 36)) & 0xf0f0f0f00f0f0f0f)
    t = (bb ^ (bb << 18)) & 0xcccc0000cccc0000
    bb = bb ^ (t ^ (t >> 18))
    t = (bb ^ (bb << 9)) & 0xaa00aa00aa00aa00
    bb = bb ^ (t ^ (t >> 9))
    return bb


def shift_down(b):
    return b >> 8

def shift_2_down(b):
    return b >> 16

def shift_up(b):
    return (b << 8) & BB_ALL

def shift_2_up(b):
    return (b << 16) & BB_ALL

def shift_right(b):
    return (b << 1) & ~BB_FILE_A & BB_ALL

def shift_2_right(b):
    return (b << 2) & ~BB_FILE_A & ~BB_FILE_B & BB_ALL

def shift_left(b):
    return (b >> 1) & ~BB_FILE_H

def shift_2_left(b):
    return (b >> 2) & ~BB_FILE_G & ~BB_FILE_H

def shift_up_left(b):
    return (b << 7) & ~BB_FILE_H & BB_ALL

def shift_up_right(b):
    return (b << 9) & ~BB_FILE_A & BB_ALL

def shift_down_left(b):
    return (b >> 9) & ~BB_FILE_H

def shift_down_right(b):
    return (b >> 7) & ~BB_FILE_A


def _sliding_attacks(square, occupied, deltas):
    attacks = 0

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

def _step_attacks(square, deltas):
    return _sliding_attacks(square, BB_ALL, deltas)

BB_KNIGHT_ATTACKS = [_step_attacks(sq, [17, 15, 10, 6, -17, -15, -10, -6]) for sq in SQUARES]
BB_KING_ATTACKS = [_step_attacks(sq, [9, 8, 7, 1, -9, -8, -7, -1]) for sq in SQUARES]
BB_PAWN_ATTACKS = [[_step_attacks(sq, deltas) for sq in SQUARES] for deltas in [[-7, -9], [7, 9]]]


def _edges(square):
    return (((BB_RANK_1 | BB_RANK_8) & ~BB_RANKS[square_rank(square)]) |
            ((BB_FILE_A | BB_FILE_H) & ~BB_FILES[square_file(square)]))

def _carry_rippler(mask):
    # Carry-Rippler trick to iterate subsets of mask.
    subset = 0
    while True:
        yield subset
        subset = (subset - mask) & mask
        if not subset:
            break

def _attack_table(deltas):
    mask_table = []
    attack_table = []

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


def _rays():
    rays = []
    between = []
    for a, bb_a in enumerate(BB_SQUARES):
        rays_row = []
        between_row = []
        for b, bb_b in enumerate(BB_SQUARES):
            if BB_DIAG_ATTACKS[a][0] & bb_b:
                rays_row.append((BB_DIAG_ATTACKS[a][0] & BB_DIAG_ATTACKS[b][0]) | bb_a | bb_b)
                between_row.append(BB_DIAG_ATTACKS[a][BB_DIAG_MASKS[a] & bb_b] & BB_DIAG_ATTACKS[b][BB_DIAG_MASKS[b] & bb_a])
            elif BB_RANK_ATTACKS[a][0] & bb_b:
                rays_row.append(BB_RANK_ATTACKS[a][0] | bb_a)
                between_row.append(BB_RANK_ATTACKS[a][BB_RANK_MASKS[a] & bb_b] & BB_RANK_ATTACKS[b][BB_RANK_MASKS[b] & bb_a])
            elif BB_FILE_ATTACKS[a][0] & bb_b:
                rays_row.append(BB_FILE_ATTACKS[a][0] | bb_a)
                between_row.append(BB_FILE_ATTACKS[a][BB_FILE_MASKS[a] & bb_b] & BB_FILE_ATTACKS[b][BB_FILE_MASKS[b] & bb_a])
            else:
                rays_row.append(0)
                between_row.append(0)
        rays.append(rays_row)
        between.append(between_row)
    return rays, between

BB_RAYS, BB_BETWEEN = _rays()


SAN_REGEX = re.compile(r"^([NBKRQ])?([a-h])?([1-8])?[\-x]?([a-h][1-8])(=?[nbrqkNBRQK])?(\+|#)?\Z")

FEN_CASTLING_REGEX = re.compile(r"^(?:-|[KQABCDEFGH]{0,2}[kqabcdefgh]{0,2})\Z")


class Piece:
    """A piece with type and color."""

    def __init__(self, piece_type, color):
        self.piece_type = piece_type
        self.color = color

    def symbol(self):
        """
        Gets the symbol ``P``, ``N``, ``B``, ``R``, ``Q`` or ``K`` for white
        pieces or the lower-case variants for the black pieces.
        """
        if self.color == WHITE:
            return PIECE_SYMBOLS[self.piece_type].upper()
        else:
            return PIECE_SYMBOLS[self.piece_type]

    def unicode_symbol(self, *, invert_color=False):
        """
        Gets the Unicode character for the piece.
        """
        if not invert_color:
            return UNICODE_PIECE_SYMBOLS[self.symbol()]
        else:
            return UNICODE_PIECE_SYMBOLS[self.symbol().swapcase()]

    def __hash__(self):
        return hash(self.piece_type * (self.color + 1))

    def __repr__(self):
        return "Piece.from_symbol('{}')".format(self.symbol())

    def __str__(self):
        return self.symbol()

    def _repr_svg_(self):
        import chess.svg
        return chess.svg.piece(self, size=45)

    def __eq__(self, other):
        ne = self.__ne__(other)
        return NotImplemented if ne is NotImplemented else not ne

    def __ne__(self, other):
        try:
            if self.piece_type != other.piece_type:
                return True
            elif self.color != other.color:
                return True
            else:
                return False
        except AttributeError:
            return NotImplemented

    @classmethod
    def from_symbol(cls, symbol):
        """
        Creates a :class:`~chess.Piece` instance from a piece symbol.

        :raises: :exc:`ValueError` if the symbol is invalid.
        """
        if symbol.islower():
            return cls(PIECE_SYMBOLS.index(symbol), BLACK)
        else:
            return cls(PIECE_SYMBOLS.index(symbol.lower()), WHITE)


class Move:
    """
    Represents a move from a square to a square and possibly the promotion
    piece type.

    Drops and null moves are supported.
    """

    def __init__(self, from_square, to_square, promotion=None, drop=None):
        self.from_square = from_square
        self.to_square = to_square
        self.promotion = promotion
        self.drop = drop

    def uci(self):
        """
        Gets an UCI string for the move.

        For example, a move from a7 to a8 would be ``a7a8`` or ``a7a8q``
        (if the latter is a promotion to a queen).

        The UCI representation of a null move is ``0000``.
        """
        if self.drop:
            return PIECE_SYMBOLS[self.drop].upper() + "@" + SQUARE_NAMES[self.to_square]
        elif self.promotion:
            return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square] + PIECE_SYMBOLS[self.promotion]
        elif self:
            return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square]
        else:
            return "0000"

    def __bool__(self):
        return bool(self.from_square or self.to_square or self.promotion or self.drop)

    def __eq__(self, other):
        ne = self.__ne__(other)
        return NotImplemented if ne is NotImplemented else not ne

    def __ne__(self, other):
        try:
            if self.from_square != other.from_square:
                return True
            elif self.to_square != other.to_square:
                return True
            elif self.promotion != other.promotion:
                return True
            elif self.drop != other.drop:
                return True
            else:
                return False
        except AttributeError:
            return NotImplemented

    def __repr__(self):
        return "Move.from_uci('{}')".format(self.uci())

    def __str__(self):
        return self.uci()

    def __hash__(self):
        return hash((self.to_square, self.from_square, self.promotion, self.drop))

    def __copy__(self):
        return type(self)(self.from_square, self.to_square, self.promotion, self.drop)

    def __deepcopy__(self, memo):
        move = self.__copy__()
        memo[id(self)] = move
        return move

    @classmethod
    def from_uci(cls, uci):
        """
        Parses an UCI string.

        :raises: :exc:`ValueError` if the UCI string is invalid.
        """
        if uci == "0000":
            return cls.null()
        elif len(uci) == 4 and "@" == uci[1]:
            drop = PIECE_SYMBOLS.index(uci[0].lower())
            square = SQUARE_NAMES.index(uci[2:])
            return cls(square, square, drop=drop)
        elif len(uci) == 4:
            return cls(SQUARE_NAMES.index(uci[0:2]), SQUARE_NAMES.index(uci[2:4]))
        elif len(uci) == 5:
            promotion = PIECE_SYMBOLS.index(uci[4])
            return cls(SQUARE_NAMES.index(uci[0:2]), SQUARE_NAMES.index(uci[2:4]), promotion=promotion)
        else:
            raise ValueError("expected uci string to be of length 4 or 5: {}".format(repr(uci)))

    @classmethod
    def null(cls):
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


class BaseBoard:
    """
    A board representing the position of chess pieces. See
    :class:`~chess.Board` for a full board with move generation.

    The board is initialized with the standard chess starting position, unless
    otherwise specified in the optional *board_fen* argument. If *board_fen*
    is ``None``, an empty board is created.
    """

    def __init__(self, board_fen=STARTING_BOARD_FEN):
        self.occupied_co = [BB_EMPTY, BB_EMPTY]

        if board_fen is None:
            self._clear_board()
        elif board_fen == STARTING_BOARD_FEN:
            self._reset_board()
        else:
            self._set_board_fen(board_fen)

    def _reset_board(self):
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

    def reset_board(self):
        self._reset_board()

    def _clear_board(self):
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

    def clear_board(self):
        """Clears the board."""
        self._clear_board()

    def pieces_mask(self, piece_type, color):
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

        return bb & self.occupied_co[color]

    def pieces(self, piece_type, color):
        """
        Gets pieces of the given type and color.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.pieces_mask(piece_type, color))

    def piece_at(self, square):
        """Gets the :class:`piece <chess.Piece>` at the given square."""
        piece_type = self.piece_type_at(square)
        if piece_type:
            mask = BB_SQUARES[square]
            color = bool(self.occupied_co[WHITE] & mask)
            return Piece(piece_type, color)

    def piece_type_at(self, square):
        """Gets the piece type at the given square."""
        mask = BB_SQUARES[square]

        if not self.occupied & mask:
            return None
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
        elif self.kings & mask:
            return KING

    def king(self, color):
        """
        Finds the king square of the given side. Returns ``None`` if there
        is no king of that color.

        In variants with king promotions, only non-promoted kings are
        considered.
        """
        king_mask = self.occupied_co[color] & self.kings & ~self.promoted
        if king_mask:
            return msb(king_mask)

    def attacks_mask(self, square):
        bb_square = BB_SQUARES[square]

        if bb_square & self.pawns:
            if bb_square & self.occupied_co[WHITE]:
                return BB_PAWN_ATTACKS[WHITE][square]
            else:
                return BB_PAWN_ATTACKS[BLACK][square]
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

    def attacks(self, square):
        """
        Gets a set of attacked squares from a given square.

        There will be no attacks if the square is empty. Pinned pieces are
        still attacking other squares.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.attacks_mask(square))

    def _attackers_mask(self, color, square, occupied):
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

    def attackers_mask(self, color, square):
        return self._attackers_mask(color, square, self.occupied)

    def is_attacked_by(self, color, square):
        """
        Checks if the given side attacks the given square.

        Pinned pieces still count as attackers. Pawns that can be captured
        en passant are **not** considered attacked.
        """
        return bool(self.attackers_mask(color, square))

    def attackers(self, color, square):
        """
        Gets a set of attackers of the given color for the given square.

        Pinned pieces still count as attackers.

        Returns a :class:`set of squares <chess.SquareSet>`.
        """
        return SquareSet(self.attackers_mask(color, square))

    def pin_mask(self, color, square):
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
                    if BB_BETWEEN[sniper][king] & (self.occupied | square_mask) == square_mask:
                        return BB_RAYS[king][sniper]

                break

        return BB_ALL

    def pin(self, color, square):
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
        SquareSet(0x0000000102040810)
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

    def is_pinned(self, color, square):
        """
        Detects if the given square is pinned to the king of the given color.
        """
        return self.pin_mask(color, square) != BB_ALL

    def _remove_piece_at(self, square):
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
            return

        self.occupied ^= mask
        self.occupied_co[WHITE] &= ~mask
        self.occupied_co[BLACK] &= ~mask

        self.promoted &= ~mask

        return piece_type

    def remove_piece_at(self, square):
        """
        Removes the piece from the given square. Returns the
        :class:`~chess.Piece` or ``None`` if the square was already empty.
        """
        color = bool(self.occupied_co[WHITE] & BB_SQUARES[square])
        piece_type = self._remove_piece_at(square)
        if piece_type:
            return Piece(piece_type, color)

    def _set_piece_at(self, square, piece_type, color, promoted=False):
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

        self.occupied ^= mask
        self.occupied_co[color] ^= mask

        if promoted:
            self.promoted ^= mask

    def set_piece_at(self, square, piece, promoted=False):
        """
        Sets a piece at the given square.

        An existing piece is replaced. Setting *piece* to ``None`` is
        equivalent to :func:`~chess.Board.remove_piece_at()`.
        """
        if piece is None:
            self._remove_piece_at(square)
        else:
            self._set_piece_at(square, piece.piece_type, piece.color, promoted)

    def board_fen(self, *, promoted=False):
        """
        Gets the board FEN.
        """
        builder = []
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

    def _set_board_fen(self, fen):
        # Compability with set_fen().
        fen = fen.strip()
        if " " in fen:
            raise ValueError("expected position part of fen, got multiple parts: {}".format(repr(fen)))

        # Ensure the FEN is valid.
        rows = fen.split("/")
        if len(rows) != 8:
            raise ValueError("expected 8 rows in position part of fen: {}".format(repr(fen)))

        # Validate each row.
        for row in rows:
            field_sum = 0
            previous_was_digit = False
            previous_was_piece = False

            for c in row:
                if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                    if previous_was_digit:
                        raise ValueError("two subsequent digits in position part of fen: {}".format(repr(fen)))
                    field_sum += int(c)
                    previous_was_digit = True
                    previous_was_piece = False
                elif c == "~":
                    if not previous_was_piece:
                        raise ValueError("~ not after piece in position part of fen: {}".format(repr(fen)))
                    previous_was_digit = False
                    previous_was_piece = False
                elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                    field_sum += 1
                    previous_was_digit = False
                    previous_was_piece = True
                else:
                    raise ValueError("invalid character in position part of fen: {}".format(repr(fen)))

            if field_sum != 8:
                raise ValueError("expected 8 columns per row in position part of fen: {}".format(repr(fen)))

        # Clear the board.
        self._clear_board()

        # Put pieces on the board.
        square_index = 0
        for c in fen:
            if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                square_index += int(c)
            elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                piece = Piece.from_symbol(c)
                self._set_piece_at(SQUARES_180[square_index], piece.piece_type, piece.color)
                square_index += 1
            elif c == "~":
                self.promoted |= BB_SQUARES[SQUARES_180[square_index - 1]]

    def set_board_fen(self, fen):
        """
        Parses a FEN and sets the board from it.

        :raises: :exc:`ValueError` if the FEN string is invalid.
        """
        self._set_board_fen(fen)

    def piece_map(self):
        """
        Gets a dictionary of :class:`pieces <chess.Piece>` by square index.
        """
        result = {}
        for square in scan_reversed(self.occupied):
            result[square] = self.piece_at(square)
        return result

    def _set_piece_map(self, pieces):
        self._clear_board()
        for square, piece in pieces.items():
            self._set_piece_at(square, piece.piece_type, piece.color)

    def set_piece_map(self, pieces):
        """
        Sets up the board from a dictionary of :class:`pieces <chess.Piece>`
        by square index.
        """
        self._set_piece_map(pieces)

    def _set_chess960_pos(self, sharnagl):
        if not 0 <= sharnagl <= 959:
            raise ValueError("chess960 position index not 0 <= {} <= 959".format(repr(sharnagl)))

        # See http://www.russellcottrell.com/Chess/Chess960.htm for
        # a description of the algorithm.
        n, bw = divmod(sharnagl, 4)
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

    def set_chess960_pos(self, sharnagl):
        """
        Sets up a Chess960 starting position given its index between 0 and 959.
        Also see :func:`~chess.BaseBoard.from_chess960_pos()`.
        """
        self._set_chess960_pos(sharnagl)

    def chess960_pos(self):
        """
        Gets the Chess960 starting position index between 0 and 959
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

        if popcount(self.bishops) != 4:
            return None
        if popcount(self.rooks) != 4:
            return None
        if popcount(self.knights) != 4:
            return None
        if popcount(self.queens) != 2:
            return None
        if popcount(self.kings) != 2:
            return None

        if (BB_RANK_1 & self.knights) << 56 != BB_RANK_8 & self.knights:
            return None
        if (BB_RANK_1 & self.bishops) << 56 != BB_RANK_8 & self.bishops:
            return None
        if (BB_RANK_1 & self.rooks) << 56 != BB_RANK_8 & self.rooks:
            return None
        if (BB_RANK_1 & self.queens) << 56 != BB_RANK_8 & self.queens:
            return None
        if (BB_RANK_1 & self.kings) << 56 != BB_RANK_8 & self.kings:
            return None

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

        # Algorithm from ChessX, src/database/bitboard.cpp, r2254.
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

    def __repr__(self):
        return "{}('{}')".format(type(self).__name__, self.board_fen())

    def __str__(self):
        builder = []

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

    def unicode(self, *, invert_color=False, borders=False):
        """
        Returns a string representation of the board with Unicode pieces.
        Useful for pretty-printing to a terminal.

        :param invert_color: Invert color of the Unicode pieces.
        :param borders: Show borders and a coordinate margin.
        """
        builder = []
        for rank_index in range(7, -1, -1):
            if borders:
                builder.append("  ")
                builder.append("-" * 17)
                builder.append("\n")

                builder.append(RANK_NAMES[rank_index])
                builder.append(" ")

            for file_index in range(8):
                square_index = square(file_index, rank_index)

                if borders:
                    builder.append("|")
                elif file_index > 0:
                    builder.append(" ")

                piece = self.piece_at(square_index)

                if piece:
                    builder.append(piece.unicode_symbol(invert_color=invert_color))
                else:
                    builder.append(u"·")

            if borders:
                builder.append("|")

            if borders or rank_index > 0:
                builder.append("\n")

        if borders:
            builder.append("  ")
            builder.append("-" * 17)
            builder.append("\n")
            builder.append("   a b c d e f g h")

        return "".join(builder)

    def _repr_svg_(self):
        import chess.svg
        return chess.svg.board(board=self, size=400)

    def __eq__(self, board):
        ne = self.__ne__(board)
        return NotImplemented if ne is NotImplemented else not ne

    def __ne__(self, board):
        try:
            if self.occupied != board.occupied:
                return True
            elif self.occupied_co[WHITE] != board.occupied_co[WHITE]:
                return True
            elif self.pawns != board.pawns:
                return True
            elif self.knights != board.knights:
                return True
            elif self.bishops != board.bishops:
                return True
            elif self.rooks != board.rooks:
                return True
            elif self.queens != board.queens:
                return True
            elif self.kings != board.kings:
                return True
            else:
                return False
        except AttributeError:
            return NotImplemented

    def apply_transform(self, f):
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

    def transform(self, f):
        board = self.copy()
        board.apply_transform(f)
        return board

    def mirror(self):
        """
        Returns a mirrored copy of the board.

        The board is mirrored vertically and piece colors are swapped, so that
        the position is equivalent modulo color.
        """
        board = self.transform(flip_vertical)
        board.occupied_co[WHITE], board.occupied_co[BLACK] = board.occupied_co[BLACK], board.occupied_co[WHITE]
        return board

    def copy(self):
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

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        board = self.copy()
        memo[id(self)] = board
        return board

    @classmethod
    def empty(cls):
        """
        Creates a new empty board. Also see
        :func:`~chess.BaseBoard.clear_board()`.
        """
        return cls(None)

    @classmethod
    def from_chess960_pos(cls, sharnagl):
        """
        Creates a new board, initialized with a Chess960 starting position.

        >>> import chess
        >>> import random
        >>>
        >>> board = chess.Board.from_chess960_pos(random.randint(0, 959))
        """
        board = cls.empty()
        board.set_chess960_pos(sharnagl)
        return board


class _BoardState:

    def __init__(self, board):
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

    def restore(self, board):
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
    A :class:`~chess.BaseBoard` and additional information representing
    a chess position.

    Provides move generation, validation, parsing, attack generation,
    game end detection, move counters and the capability to make and unmake
    moves.

    The board is initialized to the standard chess starting position,
    unless otherwise specified in the optional *fen* argument.
    If *fen* is ``None``, an empty board is created.

    Optionally supports *chess960*. In Chess960 castling moves are encoded
    by a king move to the corresponding rook square.
    Use :func:`chess.Board.from_chess960_pos()` to create a board with one
    of the Chess960 starting positions.

    It's safe to set :data:`~Board.turn`, :data:`~Board.castling_rights`,
    :data:`~Board.ep_square`, :data:`~Board.halfmove_clock` and
    :data:`~Board.fullmove_number` directly.
    """

    aliases = ["Standard", "Chess", "Classical", "Normal"]
    uci_variant = "chess"
    starting_fen = STARTING_FEN

    tbw_suffix = ".rtbw"
    tbz_suffix = ".rtbz"
    tbw_magic = b"\x71\xe8\x23\x5d"
    tbz_magic = b"\xd7\x66\x0c\xa5"
    pawnless_tbw_suffix = pawnless_tbz_suffix = None
    pawnless_tbw_magic = pawnless_tbz_magic = None
    connected_kings = False
    one_king = True
    captures_compulsory = False

    def __init__(self, fen=STARTING_FEN, *, chess960=False):
        BaseBoard.__init__(self, None)

        self.chess960 = chess960

        self.pseudo_legal_moves = PseudoLegalMoveGenerator(self)
        self.legal_moves = LegalMoveGenerator(self)

        self.move_stack = []
        self.stack = []

        if fen is None:
            self.clear()
        elif fen == type(self).starting_fen:
            self.reset()
        else:
            self.set_fen(fen)

    def reset(self):
        """Restores the starting position."""
        self.turn = WHITE
        self.castling_rights = BB_CORNERS
        self.ep_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1

        self.reset_board()

    def reset_board(self):
        super().reset_board()
        self.clear_stack()

    def clear(self):
        """
        Clears the board.

        Resets move stacks and move counters. The side to move is white. There
        are no rooks or kings, so castling rights are removed.

        In order to be in a valid :func:`~chess.Board.status()` at least kings
        need to be put on the board.
        """
        self.turn = WHITE
        self.castling_rights = BB_EMPTY
        self.ep_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1

        self.clear_board()

    def clear_board(self):
        super().clear_board()
        self.clear_stack()

    def clear_stack(self):
        """Clears the move stack."""
        del self.move_stack[:]
        del self.stack[:]

    def root(self):
        """Returns a copy of the root position."""
        if self.stack:
            board = type(self)(None, chess960=self.chess960)
            self.stack[0].restore(board)
            return board
        else:
            return self.copy(stack=False)

    def remove_piece_at(self, square):
        piece = super().remove_piece_at(square)
        self.clear_stack()
        return piece

    def set_piece_at(self, square, piece, promoted=False):
        super().set_piece_at(square, piece, promoted=promoted)
        self.clear_stack()

    def generate_pseudo_legal_moves(self, from_mask=BB_ALL, to_mask=BB_ALL):
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

    def generate_pseudo_legal_ep(self, from_mask=BB_ALL, to_mask=BB_ALL):
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

    def generate_pseudo_legal_captures(self, from_mask=BB_ALL, to_mask=BB_ALL):
        return itertools.chain(
            self.generate_pseudo_legal_moves(from_mask, to_mask & self.occupied_co[not self.turn]),
            self.generate_pseudo_legal_ep(from_mask, to_mask))

    def is_check(self):
        """Returns if the current side to move is in check."""
        king = self.king(self.turn)
        return king is not None and self.is_attacked_by(not self.turn, king)

    def is_into_check(self, move):
        """
        Checks if the given move would leave the king in check or put it into
        check. The move must be at least pseudo legal.
        """
        king = self.king(self.turn)
        if king is None:
            return False

        checkers = self.attackers_mask(not self.turn, king)
        if checkers:
            # If already in check, look if it is an evasion.
            if move not in self._generate_evasions(king, checkers, BB_SQUARES[move.from_square], BB_SQUARES[move.to_square]):
                return True

        return not self._is_safe(king, self._slider_blockers(king), move)

    def was_into_check(self):
        """
        Checks if the king of the other side is attacked. Such a position is not
        valid and could only be reached by an illegal move.
        """
        king = self.king(not self.turn)
        return king is not None and self.is_attacked_by(self.turn, king)

    def is_pseudo_legal(self, move):
        # Null moves are not pseudo legal.
        if not move:
            return False

        # Drops are not pseudo legal.
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

        # Only pawns can promote and only on the back rank.
        if move.promotion:
            if piece != PAWN:
                return False

            if self.turn == WHITE and square_rank(move.to_square) != 7:
                return False
            elif self.turn == BLACK and square_rank(move.to_square) != 0:
                return False

        # Handle castling.
        if piece == KING:
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

    def is_legal(self, move):
        return not self.is_variant_end() and self.is_pseudo_legal(move) and not self.is_into_check(move)

    def is_variant_end(self):
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

    def is_variant_loss(self):
        """Checks if a special variant-specific loss condition is fulfilled."""
        return False

    def is_variant_win(self):
        """Checks if a special variant-specific win condition is fulfilled."""
        return False

    def is_variant_draw(self):
        """
        Checks if a special variant-specific drawing condition is fulfilled.
        """
        return False

    def is_game_over(self, *, claim_draw=False):
        """
        Checks if the game is over due to
        :func:`checkmate <chess.Board.is_checkmate()>`,
        :func:`stalemate <chess.Board.is_stalemate()>`,
        :func:`insufficient material <chess.Board.is_insufficient_material()>`,
        the :func:`seventyfive-move rule <chess.Board.is_seventyfive_moves()>`,
        :func:`fivefold repetition <chess.Board.is_fivefold_repetition()>`
        or a :func:`variant end condition <chess.Board.is_variant_end()>`.

        The game is not considered to be over by
        :func:`threefold repetition <chess.Board.can_claim_threefold_repetition()>`
        or the :func:`fifty-move rule <chess.Board.can_claim_fifty_moves()>`,
        unless *claim_draw* is given.
        """
        # Seventyfive-move rule.
        if self.is_seventyfive_moves():
            return True

        # Insufficient material.
        if self.is_insufficient_material():
            return True

        # Stalemate or checkmate.
        if not any(self.generate_legal_moves()):
            return True

        # Fivefold repetition.
        if self.is_fivefold_repetition():
            return True

        # Claim draw.
        if claim_draw and self.can_claim_draw():
            return True

        return False

    def result(self, *, claim_draw=False):
        """
        Gets the game result.

        ``1-0``, ``0-1`` or ``1/2-1/2`` if the
        :func:`game is over <chess.Board.is_game_over()>`. Otherwise, the
        result is undetermined: ``*``.
        """
        # Chess variant support.
        if self.is_variant_loss():
            return "0-1" if self.turn == WHITE else "1-0"
        elif self.is_variant_win():
            return "1-0" if self.turn == WHITE else "0-1"
        elif self.is_variant_draw():
            return "1/2-1/2"

        # Checkmate.
        if self.is_checkmate():
            return "0-1" if self.turn == WHITE else "1-0"

        # Draw claimed.
        if claim_draw and self.can_claim_draw():
            return "1/2-1/2"

        # Seventyfive-move rule or fivefold repetition.
        if self.is_seventyfive_moves() or self.is_fivefold_repetition():
            return "1/2-1/2"

        # Insufficient material.
        if self.is_insufficient_material():
            return "1/2-1/2"

        # Stalemate.
        if not any(self.generate_legal_moves()):
            return "1/2-1/2"

        # Undetermined.
        return "*"

    def is_checkmate(self):
        """Checks if the current position is a checkmate."""
        if not self.is_check():
            return False

        return not any(self.generate_legal_moves())

    def is_stalemate(self):
        """Checks if the current position is a stalemate."""
        if self.is_check():
            return False

        if self.is_variant_end():
            return False

        return not any(self.generate_legal_moves())

    def is_insufficient_material(self):
        """Checks for a draw due to insufficient mating material."""
        # Enough material to mate.
        if self.pawns or self.rooks or self.queens:
            return False

        # A single knight or a single bishop.
        if popcount(self.occupied) <= 3:
            return True

        # More than a single knight.
        if self.knights:
            return False

        # All bishops on the same color.
        if self.bishops & BB_DARK_SQUARES == 0:
            return True
        elif self.bishops & BB_LIGHT_SQUARES == 0:
            return True
        else:
            return False

    def is_seventyfive_moves(self):
        """
        Since the 1st of July 2014, a game is automatically drawn (without
        a claim by one of the players) if the half-move clock since a capture
        or pawn move is equal to or grather than 150. Other means to end a game
        take precedence.
        """
        if self.halfmove_clock >= 150:
            if any(self.generate_legal_moves()):
                return True

        return False

    def is_fivefold_repetition(self):
        """
        Since the 1st of July 2014 a game is automatically drawn (without
        a claim by one of the players) if a position occurs for the fifth time.
        Originally this had to occur on consecutive alternating moves, but
        this has since been revised.
        """
        transposition_key = self._transposition_key()
        repetitions = 1
        switchyard = []

        while self.move_stack and repetitions < 5:
            move = self.pop()
            switchyard.append(move)

            if self.is_irreversible(move):
                break

            if self._transposition_key() == transposition_key:
                repetitions += 1

        while switchyard:
            self.push(switchyard.pop())

        return repetitions >= 5

    def can_claim_draw(self):
        """
        Checks if the side to move can claim a draw by the fifty-move rule or
        by threefold repetition.
        """
        return self.can_claim_fifty_moves() or self.can_claim_threefold_repetition()

    def can_claim_fifty_moves(self):
        """
        Draw by the fifty-move rule can be claimed once the clock of halfmoves
        since the last capture or pawn move becomes equal or greater to 100
        and the side to move still has a legal move they can make.
        """
        # Fifty-move rule.
        if self.halfmove_clock >= 100:
            if any(self.generate_legal_moves()):
                return True

        return False

    def can_claim_threefold_repetition(self):
        """
        Draw by threefold repetition can be claimed if the position on the
        board occured for the third time or if such a repetition is reached
        with one of the possible legal moves.
        """
        transposition_key = self._transposition_key()
        transpositions = collections.Counter()
        transpositions.update((transposition_key, ))

        # Count positions.
        switchyard = []
        while self.move_stack:
            move = self.pop()
            switchyard.append(move)

            if self.is_irreversible(move):
                break

            transpositions.update((self._transposition_key(), ))

        while switchyard:
            self.push(switchyard.pop())

        # Threefold repetition occured.
        if transpositions[transposition_key] >= 3:
            return True

        # The next legal move is a threefold repetition.
        for move in self.generate_legal_moves():
            self.push(move)

            if transpositions[self._transposition_key()] >= 2:
                self.pop()
                return True

            self.pop()

        return False

    def _push_capture(self, move, capture_square, piece_type, was_promoted):
        pass

    def push(self, move):
        """
        Updates the position with the given move and puts it onto the
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

        :warning: Moves are not checked for legality.
        """
        # Push move and remember board state.
        move = self._to_chess960(move)
        self.move_stack.append(self._from_chess960(self.chess960, move.from_square, move.to_square, move.promotion, move.drop))
        self.stack.append(_BoardState(self))

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

        promoted = self.promoted & from_bb
        piece_type = self._remove_piece_at(move.from_square)
        capture_square = move.to_square
        captured_piece_type = self.piece_type_at(capture_square)

        # Update castling rights.
        self.castling_rights = self.clean_castling_rights() & ~to_bb & ~from_bb
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
        if not castling and piece_type:
            was_promoted = self.promoted & to_bb
            self._set_piece_at(move.to_square, piece_type, self.turn, promoted)

            if captured_piece_type:
                self._push_capture(move, capture_square, captured_piece_type, was_promoted)

        # Swap turn.
        self.turn = not self.turn

    def pop(self):
        """
        Restores the previous position and returns the last move from the stack.

        :raises: :exc:`IndexError` if the stack is empty.
        """
        move = self.move_stack.pop()
        self.stack.pop().restore(self)
        return move

    def peek(self):
        """
        Gets the last move from the move stack.

        :raises: :exc:`IndexError` if the move stack is empty.
        """
        return self.move_stack[-1]

    def castling_shredder_fen(self):
        castling_rights = self.clean_castling_rights()
        if not castling_rights:
            return "-"

        builder = []

        for square in scan_reversed(castling_rights & BB_RANK_1):
            builder.append(FILE_NAMES[square_file(square)].upper())

        for square in scan_reversed(castling_rights & BB_RANK_8):
            builder.append(FILE_NAMES[square_file(square)])

        return "".join(builder)

    def castling_xfen(self):
        builder = []

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

    def has_pseudo_legal_en_passant(self):
        """Checks if there is a pseudo-legal en passant capture."""
        return self.ep_square and any(self.generate_pseudo_legal_ep())

    def has_legal_en_passant(self):
        """Checks if there is a legal en passant capture."""
        return self.ep_square and any(self.generate_legal_ep())

    def fen(self, *, shredder=False, en_passant="legal", promoted=None):
        """
        Gets a FEN representation of the position.

        A FEN string (e.g.,
        ``rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1``) consists
        of the position part :func:`~chess.Board.board_fen()`, the
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

    def shredder_fen(self, *, en_passant="legal", promoted=None):
        return " ".join([
            self.epd(shredder=True, en_passant=en_passant, promoted=promoted),
            str(self.halfmove_clock),
            str(self.fullmove_number)
        ])

    def set_fen(self, fen):
        """
        Parses a FEN and sets the position from it.

        :raises: :exc:`ValueError` if the FEN string is invalid.
        """
        # Ensure there are six parts.
        parts = fen.split()
        if len(parts) != 6:
            raise ValueError("fen string should consist of 6 parts: {}".format(repr(fen)))

        # Check that the turn part is valid.
        if not parts[1] in ["w", "b"]:
            raise ValueError("expected 'w' or 'b' for turn part of fen: {}".format(repr(fen)))

        # Check that the castling part is valid.
        if not FEN_CASTLING_REGEX.match(parts[2]):
            raise ValueError("invalid castling part in fen: {}".format(repr(fen)))

        # Check that the en passant part is valid.
        if parts[3] != "-":
            if parts[3] not in SQUARE_NAMES:
                raise ValueError("invalid en passant part in fen: {}".format(repr(fen)))

        # Check that the half-move part is valid.
        if int(parts[4]) < 0:
            raise ValueError("half-move clock can not be negative: {}".format(repr(fen)))

        # Check that the full-move number part is valid.
        # 0 is allowed for compability, but later replaced with 1.
        if int(parts[5]) < 0:
            raise ValueError("full-move number must be positive: {}".format(repr(fen)))

        # Validate the board part and set it.
        self._set_board_fen(parts[0])

        # Set the turn.
        if parts[1] == "w":
            self.turn = WHITE
        else:
            self.turn = BLACK

        # Set castling flags.
        self._set_castling_fen(parts[2])

        # Set the en passant square.
        if parts[3] == "-":
            self.ep_square = None
        else:
            self.ep_square = SQUARE_NAMES.index(parts[3])

        # Set the mover counters.
        self.halfmove_clock = int(parts[4])
        self.fullmove_number = int(parts[5]) or 1

        # Clear move stack.
        self.clear_stack()

    def _set_castling_fen(self, castling_fen):
        if not castling_fen or castling_fen == "-":
            self.castling_rights = BB_EMPTY
            return

        if not FEN_CASTLING_REGEX.match(castling_fen):
            raise ValueError("invalid castling fen: {}".format(repr(castling_fen)))

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

    def set_castling_fen(self, castling_fen):
        """
        Sets castling rights from a string in FEN notation like ``Qqk``.

        :raises: :exc:`ValueError` if the castling FEN is syntactically
            invalid.
        """
        self._set_castling_fen(castling_fen)
        self.clear_stack()

    def set_board_fen(self, fen):
        super().set_board_fen(fen)
        self.clear_stack()

    def set_piece_map(self, pieces):
        super().set_piece_map(pieces)
        self.clear_stack()

    def set_chess960_pos(self, sharnagl):
        super().set_chess960_pos(sharnagl)
        self.chess960 = True
        self.turn = WHITE
        self.castling_rights = self.rooks
        self.ep_square = None
        self.halfmove_clock = 0
        self.fullmove_number = 1

        self.clear_stack()

    def chess960_pos(self, *, ignore_turn=False, ignore_castling=False, ignore_counters=True):
        """
        Gets the Chess960 starting position index between 0 and 956
        or ``None`` if the current position is not a Chess960 starting
        position.

        By default white to move (**ignore_turn**) and full castling rights
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

    def _epd_operations(self, operations):
        epd = []
        first_op = True

        for opcode, operand in operations.items():
            if not first_op:
                epd.append(" ")
            first_op = False
            epd.append(opcode)

            # Value is empty.
            if operand is None:
                epd.append(";")
                continue

            # Value is a move.
            if hasattr(operand, "from_square") and hasattr(operand, "to_square") and hasattr(operand, "promotion"):
                # Append SAN for moves.
                epd.append(" ")
                epd.append(self.san(operand))
                epd.append(";")
                continue

            # Value is numeric.
            if isinstance(operand, (int, float)):
                # Append integer or float.
                epd.append(" ")
                epd.append(str(operand))
                epd.append(";")
                continue

            # Value is a set of moves or a variation.
            if hasattr(operand, "__iter__"):
                position = Board(self.shredder_fen()) if opcode == "pv" else self
                iterator = operand.__iter__()
                first_move = next(iterator)
                if hasattr(first_move, "from_square") and hasattr(first_move, "to_square") and hasattr(first_move, "promotion"):
                    epd.append(" ")
                    epd.append(position.san(first_move))
                    if opcode == "pv":
                        position.push(first_move)

                    for move in iterator:
                        epd.append(" ")
                        epd.append(position.san(move))
                        if opcode == "pv":
                            position.push(move)

                    epd.append(";")
                    continue

            # Append as escaped string.
            epd.append(" \"")
            epd.append(str(operand).replace("\r", "").replace("\n", " ").replace("\\", "\\\\").replace("\"", "\\\""))
            epd.append("\";")

        return "".join(epd)

    def epd(self, *, shredder=False, en_passant="legal", promoted=None, **operations):
        """
        Gets an EPD representation of the current position.

        See :func:`~chess.Board.fen()` for FEN formatting options (*shredder*,
        *ep_square* and *promoted*).

        EPD operations can be given as keyword arguments. Supported operands
        are strings, integers, floats, moves, lists of moves and ``None``.
        All other operands are converted to strings.

        A list of moves for *pv* will be interpreted as a variation. All other
        move lists are interpreted as a set of moves in the current position.

        *hmvc* and *fmvc* are not included by default. You can use:

        >>> import chess
        >>>
        >>> board = chess.Board()
        >>> board.epd(hmvc=board.halfmove_clock, fmvc=board.fullmove_number)
        'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - hmvc 0; fmvc 1;'
        """
        epd = [self.board_fen(promoted=promoted),
               "w" if self.turn == WHITE else "b",
               self.castling_shredder_fen() if shredder else self.castling_xfen()]

        if en_passant == "fen":
            epd.append(SQUARE_NAMES[self.ep_square] if self.ep_square is not None else "-")
        elif en_passant == "xfen":
            epd.append(SQUARE_NAMES[self.ep_square] if self.has_pseudo_legal_en_passant() else "-")
        else:
            epd.append(SQUARE_NAMES[self.ep_square] if self.has_legal_en_passant() else "-")

        if operations:
            epd.append(self._epd_operations(operations))

        return " ".join(epd)

    def _parse_epd_ops(self, operation_part, make_board):
        operations = {}
        state = "opcode"
        opcode = ""
        operand = ""
        position = None

        for ch in itertools.chain(operation_part, [None]):
            if state == "opcode":
                if ch == " ":
                    if opcode:
                        state = "after_opcode"
                elif ch in [";", None]:
                    if opcode:
                        operations[opcode] = None
                        opcode = ""
                else:
                    opcode += ch
            elif state == "after_opcode":
                if ch == " ":
                    pass
                elif ch in "+-.0123456789":
                    operand = ch
                    state = "numeric"
                elif ch == "\"":
                    state = "string"
                elif ch in [";", None]:
                    if opcode:
                        operations[opcode] = None
                        opcode = ""
                    state = "opcode"
                else:
                    operand = ch
                    state = "san"
            elif state == "numeric":
                if ch in [";", None]:
                    operations[opcode] = float(operand)
                    try:
                        operations[opcode] = int(operand)
                    except:
                        pass
                    opcode = ""
                    operand = ""
                    state = "opcode"
                else:
                    operand += ch
            elif state == "string":
                if ch in ["\"", None]:
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
                else:
                    operand += ch
                    state = "string"
            elif state == "san":
                if ch in [";", None]:
                    if position is None:
                        position = make_board()

                    if opcode == "pv":
                        # A variation.
                        operations[opcode] = []
                        for token in operand.split():
                            move = position.parse_san(token)
                            operations[opcode].append(move)
                            position.push(move)

                        # Reset the position.
                        while position.move_stack:
                            position.pop()
                    elif opcode in ["bm", "am"]:
                        # A set of moves.
                        operations[opcode] = [position.parse_san(token) for token in operand.split()]
                    else:
                        # A single move.
                        operations[opcode] = position.parse_san(operand)

                    opcode = ""
                    operand = ""
                    state = "opcode"
                else:
                    operand += ch

        assert state == "opcode"
        return operations

    def set_epd(self, epd):
        """
        Parses the given EPD string and uses it to set the position.

        If present, ``hmvc`` and ``fmvn`` are used to set the half-move
        clock and the full-move number. Otherwise, ``0`` and ``1`` are used.

        Returns a dictionary of parsed operations. Values can be strings,
        integers, floats, move objects, or lists of moves.

        :raises: :exc:`ValueError` if the EPD string is invalid.
        """
        # Split into 4 or 5 parts.
        parts = epd.strip().rstrip(";").split(None, 4)
        if len(parts) < 4:
            raise ValueError("epd should consist of at least 4 parts: {}".format(repr(epd)))

        # Parse ops.
        if len(parts) > 4:
            operations = self._parse_epd_ops(parts.pop(), lambda: type(self)(" ".join(parts) + " 0 1"))
        else:
            operations = {}

        # Create a full FEN and parse it.
        parts.append(str(operations["hmvc"]) if "hmvc" in operations else "0")
        parts.append(str(operations["fmvn"]) if "fmvn" in operations else "1")
        self.set_fen(" ".join(parts))

        return operations

    def san(self, move):
        """
        Gets the standard algebraic notation of the given move in the context
        of the current position.
        """
        return self._algebraic(move)

    def lan(self, move):
        """
        Gets the long algebraic notation of the given move in the context of
        the current position.
        """
        return self._algebraic(move, long=True)

    def _algebraic(self, move, long=False):
        if not move:
            # Null move.
            return "--"

        # Look ahead for check or checkmate.
        self.push(move)
        is_check = self.is_check()
        is_checkmate = (is_check and self.is_checkmate()) or self.is_variant_loss() or self.is_variant_win()
        self.pop()

        # Drops.
        if move.drop:
            san = ""
            if move.drop != PAWN:
                san = PIECE_SYMBOLS[move.drop].upper()
            san += "@" + SQUARE_NAMES[move.to_square]

        # Castling.
        if self.is_castling(move):
            if square_file(move.to_square) < square_file(move.from_square):
                san = "O-O-O"
            else:
                san = "O-O"

        if move.drop or self.is_castling(move):
            if is_checkmate:
                return san + "#"
            elif is_check:
                return san + "+"
            else:
                return san

        piece = self.piece_type_at(move.from_square)
        capture = self.is_capture(move)

        if piece == PAWN:
            san = ""
        else:
            san = PIECE_SYMBOLS[piece].upper()

        if long:
            san += SQUARE_NAMES[move.from_square]
        elif piece != PAWN:
            # Get ambiguous move candidates.
            # Relevant candidates: not exactly the current move,
            # but to the same square.
            others = 0
            from_mask = self.pieces_mask(piece, self.turn)
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
            san += "=" + PIECE_SYMBOLS[move.promotion].upper()

        # Add check or checkmate suffix.
        if is_checkmate:
            san += "#"
        elif is_check:
            san += "+"

        return san

    def variation_san(self, variation):
        """
        Given a sequence of moves, returns a string representing the sequence
        in standard algebraic notation (e.g., ``1. e4 e5 2. Nf3 Nc6`` or
        ``37...Bg6 38. fxg6``).

        The board will not be modified as a result of calling this.

        :raises: :exc:`ValueError` if any moves in the sequence are illegal.
        """
        board = self.copy(stack=False)
        san = []

        for move in variation:
            if not board.is_legal(move):
                raise ValueError("illegal move {} in position {}".format(move, board.fen()))

            if board.turn == WHITE:
                san.append("{}. {}".format(board.fullmove_number, board.san(move)))
            elif not san:
                san.append("{}...{}".format(board.fullmove_number, board.san(move)))
            else:
                san.append(board.san(move))

            board.push(move)

        return " ".join(san)

    def parse_san(self, san):
        """
        Uses the current position as the context to parse a move in standard
        algebraic notation and returns the corresponding move object.

        The returned move is guaranteed to be either legal or a null move.

        :raises: :exc:`ValueError` if the SAN is invalid or ambiguous.
        """
        # Castling.
        try:
            if san in ["O-O", "O-O+", "O-O#"]:
                return next(move for move in self.generate_castling_moves() if self.is_kingside_castling(move))
            elif san in ["O-O-O", "O-O-O+", "O-O-O#"]:
                return next(move for move in self.generate_castling_moves() if self.is_queenside_castling(move))
        except StopIteration:
            raise ValueError("illegal san: {} in {}".format(repr(san), self.fen()))

        # Match normal moves.
        match = SAN_REGEX.match(san)
        if not match:
            # Null moves.
            if san in ["--", "Z0"]:
                return Move.null()

            raise ValueError("invalid san: {}".format(repr(san)))

        # Get target square.
        to_square = SQUARE_NAMES.index(match.group(4))
        to_mask = BB_SQUARES[to_square]

        # Get the promotion type.
        p = match.group(5)
        promotion = p and PIECE_SYMBOLS.index(p[-1].lower())

        # Filter by piece type.
        if match.group(1):
            piece_type = PIECE_SYMBOLS.index(match.group(1).lower())
            from_mask = self.pieces_mask(piece_type, self.turn)
        else:
            from_mask = self.pawns

        # Filter by source file.
        if match.group(2):
            from_mask &= BB_FILES[FILE_NAMES.index(match.group(2))]

        # Filter by source rank.
        if match.group(3):
            from_mask &= BB_RANKS[int(match.group(3)) - 1]

        # Match legal moves.
        matched_move = None
        for move in self.generate_legal_moves(from_mask, to_mask):
            if move.promotion != promotion:
                continue

            if matched_move:
                raise ValueError("ambiguous san: {} in {}".format(repr(san), self.fen()))

            matched_move = move

        if not matched_move:
            raise ValueError("illegal san: {} in {}".format(repr(san), self.fen()))

        return matched_move

    def push_san(self, san):
        """
        Parses a move in standard algebraic notation, makes the move and puts
        it on the the move stack.

        Returns the move.

        :raises: :exc:`ValueError` if neither legal nor a null move.
        """
        move = self.parse_san(san)
        self.push(move)
        return move

    def uci(self, move, *, chess960=None):
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

    def parse_uci(self, uci):
        """
        Parses the given move in UCI notation.

        Supports both Chess960 and standard UCI notation.

        The returned move is guaranteed to be either legal or a null move.

        :raises: :exc:`ValueError` if the move is invalid or illegal in the
            current position (but not a null move).
        """
        move = Move.from_uci(uci)

        if not move:
            return move

        move = self._to_chess960(move)
        move = self._from_chess960(self.chess960, move.from_square, move.to_square, move.promotion, move.drop)

        if not self.is_legal(move):
            raise ValueError("illegal uci: {} in {}".format(repr(uci), self.fen()))

        return move

    def push_uci(self, uci):
        """
        Parses a move in UCI notation and puts it on the move stack.

        Returns the move.

        :raises: :exc:`ValueError` if the move is invalid or illegal in the
            current position (but not a null move).
        """
        move = self.parse_uci(uci)
        self.push(move)
        return move

    def is_en_passant(self, move):
        """Checks if the given pseudo-legal move is an en passant capture."""
        return (self.ep_square == move.to_square and
                bool(self.pawns & BB_SQUARES[move.from_square]) and
                abs(move.to_square - move.from_square) in [7, 9] and
                not self.occupied & BB_SQUARES[move.to_square])

    def is_capture(self, move):
        """Checks if the given pseudo-legal move is a capture."""
        return bool(BB_SQUARES[move.to_square] & self.occupied_co[not self.turn]) or self.is_en_passant(move)

    def is_zeroing(self, move):
        """Checks if the given pseudo-legal move is a capture or pawn move."""
        return bool(BB_SQUARES[move.from_square] & self.pawns or BB_SQUARES[move.to_square] & self.occupied_co[not self.turn])

    def is_irreversible(self, move):
        """
        Checks if the given pseudo-legal move is irreversible.

        In standard chess, pawn moves, captures and moves that destroy castling
        rights are irreversible.
        """
        backrank = BB_RANK_1 if self.turn == WHITE else BB_RANK_8
        cr = self.clean_castling_rights() & backrank
        return bool(self.is_zeroing(move) or
                    cr and BB_SQUARES[move.from_square] & self.kings & ~self.promoted or
                    cr & BB_SQUARES[move.from_square] or
                    cr & BB_SQUARES[move.to_square])

    def is_castling(self, move):
        """Checks if the given pseudo-legal move is a castling move."""
        if self.kings & BB_SQUARES[move.from_square]:
            diff = square_file(move.from_square) - square_file(move.to_square)
            return abs(diff) > 1 or bool(self.rooks & self.occupied_co[self.turn] & BB_SQUARES[move.to_square])
        return False

    def is_kingside_castling(self, move):
        """
        Checks if the given pseudo-legal move is a kingside castling move.
        """
        return self.is_castling(move) and square_file(move.to_square) > square_file(move.from_square)

    def is_queenside_castling(self, move):
        """
        Checks if the given pseudo-legal move is a queenside castling move.
        """
        return self.is_castling(move) and square_file(move.to_square) < square_file(move.from_square)

    def clean_castling_rights(self):
        """
        Returns valid castling rights filtered from
        :data:`~chess.Board.castling_rights`.
        """
        if self.stack:
            # Castling rights do not change in a game, so we can assume them to
            # be filtered already.
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

            black_a_side = (black_castling & -black_castling)
            black_h_side = BB_SQUARES[msb(black_castling)] if black_castling else BB_EMPTY

            if black_a_side and msb(black_a_side) > msb(black_king_mask):
                black_a_side = 0
            if black_h_side and msb(black_h_side) < msb(black_king_mask):
                black_h_side = 0

            # Done.
            return black_a_side | black_h_side | white_a_side | white_h_side

    def has_castling_rights(self, color):
        """Checks if the given side has castling rights."""
        backrank = BB_RANK_1 if color == WHITE else BB_RANK_8
        return bool(self.clean_castling_rights() & backrank)

    def has_kingside_castling_rights(self, color):
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

            castling_rights = castling_rights & (castling_rights - 1)

        return False

    def has_queenside_castling_rights(self, color):
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

            castling_rights = castling_rights & (castling_rights - 1)

        return False

    def has_chess960_castling_rights(self):
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

    def status(self):
        """
        Gets a bitmask of possible problems with the position.

        Move making, generation and validation are only guaranteed to work on
        a completely valid board.

        :data:`~chess.STATUS_VALID` for a completely valid board.

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
        :data:`~chess.STATUS_RACE_MATERIAL`.
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
        if self.ep_square != self._valid_ep_square():
            errors |= STATUS_INVALID_EP_SQUARE

        # Side to move giving check.
        if self.was_into_check():
            errors |= STATUS_OPPOSITE_CHECK

        return errors

    def _valid_ep_square(self):
        if self.ep_square:
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
                return

            # The last move must have been a double pawn push, so there must
            # be a pawn of the correct color on the fourth or fifth rank.
            if not self.pawns & self.occupied_co[not self.turn] & pawn_mask:
                return

            # And the en passant square must be empty.
            if self.occupied & BB_SQUARES[self.ep_square]:
                return

            # And the second rank must be empty.
            if self.occupied & seventh_rank_mask:
                return

            return self.ep_square

    def is_valid(self):
        """
        Checks if the board is valid.

        Move making, generation and validation are only guaranteed to work on
        a completely valid board.

        See :func:`~chess.Board.status()` for details.
        """
        return self.status() == STATUS_VALID

    def _ep_skewered(self, king, capturer):
        # Handle the special case where the king would be in check if the
        # pawn and its capturer disappear from the rank.

        # Vertical skewers of the captured pawn are not possible. (Pins on
        # the capturer are not handled here.)

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

    def _slider_blockers(self, king):
        rooks_and_queens = self.rooks | self.queens
        bishops_and_queens = self.bishops | self.queens

        snipers = ((BB_RANK_ATTACKS[king][0] & rooks_and_queens) |
                   (BB_FILE_ATTACKS[king][0] & rooks_and_queens) |
                   (BB_DIAG_ATTACKS[king][0] & bishops_and_queens))

        blockers = 0

        for sniper in scan_reversed(snipers & self.occupied_co[not self.turn]):
            b = BB_BETWEEN[king][sniper] & self.occupied

            # Add to blockers if exactly one piece in-between.
            if b and BB_SQUARES[msb(b)] == b:
                blockers |= b

        return blockers & self.occupied_co[self.turn]

    def _is_safe(self, king, blockers, move):
        if move.from_square == king:
            if self.is_castling(move):
                return True
            else:
                return not self.is_attacked_by(not self.turn, move.to_square)
        elif self.is_en_passant(move):
            return (self.pin_mask(self.turn, move.from_square) & BB_SQUARES[move.to_square] and
                    not self._ep_skewered(king, move.from_square))
        else:
            return (not blockers & BB_SQUARES[move.from_square] or
                    BB_RAYS[move.from_square][move.to_square] & BB_SQUARES[king])

    def _generate_evasions(self, king, checkers, from_mask=BB_ALL, to_mask=BB_ALL):
        sliders = checkers & (self.bishops | self.rooks | self.queens)

        attacked = 0
        for checker in scan_reversed(sliders):
            attacked |= BB_RAYS[king][checker] & ~BB_SQUARES[checker]

        if BB_SQUARES[king] & from_mask:
            for to_square in scan_reversed(BB_KING_ATTACKS[king] & ~self.occupied_co[self.turn] & ~attacked & to_mask):
                yield Move(king, to_square)

        checker = msb(checkers)
        if BB_SQUARES[checker] == checkers:
            # Capture or block a single checker.
            target = BB_BETWEEN[king][checker] | checkers

            yield from self.generate_pseudo_legal_moves(~self.kings & from_mask, target & to_mask)

            # Capture the checking pawn en passant (but avoid yielding
            # duplicate moves).
            if self.ep_square and not BB_SQUARES[self.ep_square] & target:
                last_double = self.ep_square + (-8 if self.turn == WHITE else 8)
                if last_double == checker:
                    yield from self.generate_pseudo_legal_ep(from_mask, to_mask)

    def generate_legal_moves(self, from_mask=BB_ALL, to_mask=BB_ALL):
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

    def generate_legal_ep(self, from_mask=BB_ALL, to_mask=BB_ALL):
        if self.is_variant_end():
            return

        for move in self.generate_pseudo_legal_ep(from_mask, to_mask):
            if not self.is_into_check(move):
                yield move

    def generate_legal_captures(self, from_mask=BB_ALL, to_mask=BB_ALL):
        return itertools.chain(
            self.generate_legal_moves(from_mask, to_mask & self.occupied_co[not self.turn]),
            self.generate_legal_ep(from_mask, to_mask))

    def _attacked_for_king(self, path, occupied):
        return any(self._attackers_mask(not self.turn, sq, occupied) for sq in scan_reversed(path))

    def _castling_uncovers_rank_attack(self, rook_bb, king_to):
        # Test the special case where we castle and our rook shielded us from
        # an attack, so castling would be into check.
        rank_pieces = BB_RANK_MASKS[king_to] & (self.occupied ^ rook_bb)
        sliders = (self.queens | self.rooks) & self.occupied_co[not self.turn]
        return BB_RANK_ATTACKS[king_to][rank_pieces] & sliders

    def generate_castling_moves(self, from_mask=BB_ALL, to_mask=BB_ALL):
        if self.is_variant_end():
            return

        backrank = BB_RANK_1 if self.turn == WHITE else BB_RANK_8
        king = self.occupied_co[self.turn] & self.kings & ~self.promoted & backrank & from_mask
        king = king & -king
        if not king or self._attacked_for_king(king, self.occupied):
            return

        bb_c = BB_FILE_C & backrank
        bb_d = BB_FILE_D & backrank
        bb_f = BB_FILE_F & backrank
        bb_g = BB_FILE_G & backrank

        for candidate in scan_reversed(self.clean_castling_rights() & backrank & to_mask):
            rook = BB_SQUARES[candidate]

            a_side = rook < king

            empty_for_rook = 0
            empty_for_king = 0

            if a_side:
                king_to = msb(bb_c)
                if not rook & bb_d:
                    empty_for_rook = BB_BETWEEN[candidate][msb(bb_d)] | bb_d
                if not king & bb_c:
                    empty_for_king = BB_BETWEEN[msb(king)][king_to] | bb_c
            else:
                king_to = msb(bb_g)
                if not rook & bb_f:
                    empty_for_rook = BB_BETWEEN[candidate][msb(bb_f)] | bb_f
                if not king & bb_g:
                    empty_for_king = BB_BETWEEN[msb(king)][king_to] | bb_g

            if not ((self.occupied ^ king ^ rook) & (empty_for_king | empty_for_rook) or
                    self._attacked_for_king(empty_for_king, self.occupied ^ king) or
                    self._castling_uncovers_rank_attack(rook, king_to)):
                yield self._from_chess960(self.chess960, msb(king), candidate)

    def _from_chess960(self, chess960, from_square, to_square, promotion=None, drop=None):
        if not chess960 and drop is None:
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

    def _to_chess960(self, move):
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

    def _transposition_key(self):
        return (self.pawns, self.knights, self.bishops, self.rooks,
                self.queens, self.kings,
                self.occupied_co[WHITE], self.occupied_co[BLACK],
                self.turn, self.clean_castling_rights(),
                self.ep_square if self.has_legal_en_passant() else None)

    def __repr__(self):
        if not self.chess960:
            return "{}('{}')".format(type(self).__name__, self.fen())
        else:
            return "{}('{}', chess960=True)".format(type(self).__name__, self.fen())

    def _repr_svg_(self):
        import chess.svg
        lastmove = self.peek() if self.move_stack else None
        check = self.king(self.turn) if self.is_check() else None
        return chess.svg.board(board=self, lastmove=lastmove, check=check, size=400)

    def __ne__(self, board):
        # Compare positions (including move counters), but excluding history.
        try:
            if self.halfmove_clock != board.halfmove_clock:
                return True
            if self.fullmove_number != board.fullmove_number:
                return True

            if type(self).uci_variant != type(board).uci_variant:
                return True
            if self._transposition_key() != board._transposition_key():
                return True
        except AttributeError:
            return NotImplemented
        else:
            return False

    def apply_transform(self, f):
        super().apply_transform(f)
        self.clear_stack()

    def transform(self, f):
        board = self.copy(stack=False)
        board.apply_transform(f)
        board.ep_square = None if self.ep_square is None else msb(f(BB_SQUARES[self.ep_square]))
        board.castling_rights = f(self.castling_rights)
        return board

    def mirror(self):
        board = super().mirror()
        board.turn = not self.turn
        return board

    def copy(self, *, stack=True):
        board = super().copy()

        board.chess960 = self.chess960

        board.ep_square = self.ep_square
        board.castling_rights = self.castling_rights
        board.turn = self.turn
        board.fullmove_number = self.fullmove_number
        board.halfmove_clock = self.halfmove_clock

        if stack:
            board.move_stack = copy.deepcopy(self.move_stack)
            board.stack = copy.copy(self.stack)

        return board

    @classmethod
    def empty(cls, *, chess960=False):
        """Creates a new empty board. Also see :func:`~chess.Board.clear()`."""
        return cls(None, chess960=chess960)

    @classmethod
    def from_epd(cls, epd, *, chess960=False):
        """
        Creates a new board from an EPD string. See
        :func:`~chess.Board.set_epd()`.

        Returns the board and the dictionary of parsed operations as a tuple.
        """
        board = cls.empty(chess960=chess960)
        return board, board.set_epd(epd)

    @classmethod
    def from_chess960_pos(cls, sharnagl):
        board = cls.empty(chess960=True)
        board.set_chess960_pos(sharnagl)
        return board


class PseudoLegalMoveGenerator:

    def __init__(self, board):
        self.board = board

    def __bool__(self):
        return any(self.board.generate_pseudo_legal_moves())

    def count(self):
        # List conversion is faster than iterating.
        return len(list(self))

    def __iter__(self):
        return self.board.generate_pseudo_legal_moves()

    def __contains__(self, move):
        return self.board.is_pseudo_legal(move)

    def __repr__(self):
        builder = []

        for move in self:
            if self.board.is_legal(move):
                builder.append(self.board.san(move))
            else:
                builder.append(self.board.uci(move))

        sans = ", ".join(builder)

        return "<PseudoLegalMoveGenerator at {} ({})>".format(hex(id(self)), sans)


class LegalMoveGenerator:

    def __init__(self, board):
        self.board = board

    def __bool__(self):
        return any(self.board.generate_legal_moves())

    def count(self):
        # List conversion is faster than iterating.
        return len(list(self))

    def __iter__(self):
        return self.board.generate_legal_moves()

    def __contains__(self, move):
        return self.board.is_legal(move)

    def __repr__(self):
        sans = ", ".join(self.board.san(move) for move in self)
        return "<LegalMoveGenerator at {} ({})>".format(hex(id(self)), sans)


class SquareSet(collections.abc.MutableSet):
    """
    A set of squares.

    >>> import chess
    >>>
    >>> squares = chess.SquareSet(chess.BB_A8 | chess.BB_RANK_1)
    >>> squares
    SquareSet(0x01000000000000ff)

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

    def __init__(self, squares=BB_EMPTY):

        try:
            self.mask = squares.__int__() & BB_ALL
            return
        except AttributeError:
            self.mask = 0

        # Try squares as an iterable. Not under except clause for nicer
        # backtraces.
        for square in squares:
            self.add(square)

    # Set

    def __contains__(self, square):
        return bool(BB_SQUARES[square] & self.mask)

    def __iter__(self):
        return scan_forward(self.mask)

    def __reversed__(self):
        return scan_reversed(self.mask)

    def __len__(self):
        return popcount(self.mask)

    # MutableSet

    def add(self, square):
        """Adds a square to the set."""
        self.mask |= BB_SQUARES[square]

    def discard(self, square):
        """Discards a square from the set."""
        self.mask &= ~BB_SQUARES[square]

    # frozenset

    def isdisjoint(self, other):
        """Test if the square sets are disjoint."""
        return not bool(self & other)

    def issubset(self, other):
        """Test if this square set is a subset of another."""
        return not bool(~self & other)

    def issuperset(self, other):
        """Test if this square set is a superset of another."""
        return not bool(self & ~other)

    def union(self, other):
        return self | other

    def __or__(self, other):
        r = SquareSet(other)
        r.mask |= self.mask
        return r

    def intersection(self, other):
        return self & other

    def __and__(self, other):
        r = SquareSet(other)
        r.mask &= self.mask
        return r

    def difference(self, other):
        return self - other

    def __sub__(self, other):
        r = SquareSet(other)
        r.mask = self.mask & ~r.mask
        return r

    def symmetric_difference(self, other):
        return self ^ other

    def __xor__(self, other):
        r = SquareSet(other)
        r.mask ^= self.mask
        return r

    def copy(self):
        return SquareSet(self.mask)

    # set

    def update(self, *others):
        for other in others:
            self |= other

    def __ior__(self, other):
        self.mask |= SquareSet(other).mask
        return self

    def intersection_update(self, *others):
        for other in others:
            self &= other

    def __iand__(self, other):
        self.mask &= SquareSet(other).mask
        return self

    def difference_update(self, other):
        self -= other

    def __isub__(self, other):
        self.mask &= ~SquareSet(other).mask
        return self

    def symmetric_difference_update(self, other):
        self ^= other

    def __ixor__(self, other):
        self.mask ^= SquareSet(other).mask
        return self

    def remove(self, square):
        """
        Removes a square from the set.

        :raises: :exc:`KeyError` if the given square was not in the set.
        """
        mask = BB_SQUARES[square]
        if self.mask & mask:
            self.mask ^= mask
        else:
            raise KeyError(square)

    def pop(self):
        """
        Removes a square from the set and returns it.

        :raises: :exc:`KeyError` on an empty set.
        """
        if not self.mask:
            raise KeyError("pop from empty SquareSet")

        square = lsb(self.mask)
        self.mask &= (self.mask - 1)
        return square

    def clear(self):
        """Remove all elements from this set."""
        self.mask = BB_EMPTY

    # SquareSet

    def carry_rippler(self):
        """Iterator over the subsets of this set."""
        return _carry_rippler(self.mask)

    def mirror(self):
        """Returns a vertically mirrored copy of this square set."""
        return SquareSet(flip_vertical(self.mask))

    def tolist(self):
        """Convert the set to a list of 64 bools."""
        l = [False] * 64
        for square in self:
            l[square] = True
        return l

    def __bool__(self):
        return bool(self.mask)

    def __eq__(self, other):
        ne = self.__ne__(other)
        return NotImplemented if ne is NotImplemented else not ne

    def __ne__(self, other):
        try:
            return self.mask != SquareSet(other).mask
        except (TypeError, ValueError):
            return NotImplemented

    def __lshift__(self, shift):
        return SquareSet((self.mask << shift) & BB_ALL)

    def __rshift__(self, shift):
        return SquareSet(self.mask >> shift)

    def __ilshift__(self, shift):
        self.mask = (self.mask << shift) & BB_ALL
        return self

    def __irshift__(self, shift):
        self.mask >>= shift
        return self

    def __invert__(self):
        return SquareSet(~self.mask & BB_ALL)

    def __int__(self):
        return self.mask

    def __index__(self):
        return self.mask

    def __repr__(self):
        return "SquareSet({0:#018x})".format(self.mask)

    def __str__(self):
        builder = []

        for square in SQUARES_180:
            mask = BB_SQUARES[square]

            if self.mask & mask:
                builder.append("1")
            else:
                builder.append(".")

            if mask & BB_FILE_H:
                if square != H1:
                    builder.append("\n")
            else:
                builder.append(" ")

        return "".join(builder)

    def _repr_svg_(self):
        import chess.svg
        return chess.svg.board(squares=self, size=400)

    @classmethod
    def from_square(cls, square):
        """
        Creates a :class:`~chess.SquareSet` from a single square.

        >>> import chess
        >>>
        >>> chess.SquareSet.from_square(chess.A1) == chess.BB_A1
        True
        """
        return cls(BB_SQUARES[square])


# TODO: Deprecated
BB_VOID = 0
bswap = flip_vertical
