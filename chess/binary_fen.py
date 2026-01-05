from __future__ import annotations

# Almost all code based on: //github.com/lichess-org/scalachess/blob/8c94e2087f83affb9718fd2be19c34866c9a1a22/core/src/main/scala/format/BinaryFen.scala
import typing

import chess
import chess.variant

from enum import IntEnum, unique
from typing import Tuple, Optional, List, Union, Iterator, Literal, cast
from dataclasses import dataclass, field
from itertools import zip_longest

if typing.TYPE_CHECKING:
    from typing_extensions import Self, assert_never

@unique
class ChessHeader(IntEnum):
    STANDARD = 0
    CHESS_960 = 2
    FROM_POSITION = 3

    @classmethod
    def from_int_opt(cls, value: int) -> Optional[Self]:
        """Convert an integer to a ChessHeader enum member, or return None if invalid."""
        try:
            return cls(value)
        except ValueError:
            return None

@unique
class VariantHeader(IntEnum):
    # chess/std
    STANDARD = 0
    CHESS_960 = 2
    FROM_POSITION = 3

    CRAZYHOUSE = 1
    KING_OF_THE_HILL = 4
    THREE_CHECK = 5
    ANTICHESS = 6
    ATOMIC = 7
    HORDE = 8
    RACING_KINGS = 9

    def board(self) -> chess.Board:
        if self == VariantHeader.CRAZYHOUSE:
            return chess.variant.CrazyhouseBoard.empty()
        elif self == VariantHeader.KING_OF_THE_HILL:
            return chess.variant.KingOfTheHillBoard.empty()
        elif self == VariantHeader.THREE_CHECK:
            return chess.variant.ThreeCheckBoard.empty()
        elif self == VariantHeader.ANTICHESS:
            return chess.variant.AntichessBoard.empty()
        elif self == VariantHeader.ATOMIC:
            return chess.variant.AtomicBoard.empty()
        elif self == VariantHeader.HORDE:
            return chess.variant.HordeBoard.empty()
        elif self == VariantHeader.RACING_KINGS:
            return chess.variant.RacingKingsBoard.empty()
        # mypy... pyright can use `self in (...)`
        elif self == VariantHeader.STANDARD or self == VariantHeader.CHESS_960 or self == VariantHeader.FROM_POSITION:
            return chess.Board.empty(chess960=True)
        else:
            assert_never(self)

    @classmethod
    def encode(cls, board: chess.Board) -> VariantHeader:
        uci_variant = type(board).uci_variant
        if uci_variant == "chess":
            # TODO check if this auto mode is OK
            root = board.root()
            if root in CHESS_960_STARTING_POSITIONS:
                return cls.CHESS_960
            elif root == STANDARD_STARTING_POSITION:
                return cls.STANDARD
            else:
                return cls.FROM_POSITION
        elif uci_variant == "crazyhouse":
            return cls.CRAZYHOUSE
        elif uci_variant == "kingofthehill":
            return cls.KING_OF_THE_HILL
        elif uci_variant == "3check":
            return cls.THREE_CHECK
        elif uci_variant == "antichess":
            return cls.ANTICHESS
        elif uci_variant == "atomic":
            return cls.ATOMIC
        elif uci_variant == "horde":
            return cls.HORDE
        elif uci_variant == "racingkings":
            return cls.RACING_KINGS
        else:
            raise ValueError(f"Unsupported variant: {uci_variant}")

CHESS_960_STARTING_POSITIONS = [chess.Board.from_chess960_pos(i) for i in range(960)]
STANDARD_STARTING_POSITION = chess.Board()

Nibble = Literal[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]

# TODO FIXME actually implement __eq__ for variant.pocket?
# not using `chess.variant.CrazyhousePocket` because its __eq__ is wrong for our case
# only using `chess.variant.CrazyhousePocket` public API for now
@dataclass(frozen=True)
class CrazyhousePiecePocket:
    pawns: Nibble
    knights: Nibble
    bishops: Nibble
    rooks: Nibble
    queens: Nibble

    @classmethod
    def from_crazyhouse_pocket(cls, pocket: chess.variant.CrazyhousePocket) -> Self:
        return cls(
            pawns=_to_nibble(pocket.count(chess.PAWN)),
            knights=_to_nibble(pocket.count(chess.KNIGHT)),
            bishops=_to_nibble(pocket.count(chess.BISHOP)),
            rooks=_to_nibble(pocket.count(chess.ROOK)),
            queens=_to_nibble(pocket.count(chess.QUEEN))
        )

    def to_crazyhouse_pocket(self) -> chess.variant.CrazyhousePocket:
        return chess.variant.CrazyhousePocket(
            "p"*self.pawns +
            "n"*self.knights +
            "b"*self.bishops +
            "r"*self.rooks +
            "q"*self.queens
        )

@dataclass(frozen=True)
class ThreeCheckData:
    white_received_checks: Nibble
    black_received_checks: Nibble

@dataclass(frozen=True)
class CrazyhouseData:
    white_pocket: CrazyhousePiecePocket
    black_pocket: CrazyhousePiecePocket
    promoted: chess.Bitboard

@dataclass(frozen=True)
class BinaryFen:
    """
    A simple binary format that encode a position in a compact way, initially used by Stockfish and Lichess 

    See https://lichess.org/@/revoof/blog/adapting-nnue-pytorchs-binary-position-format-for-lichess/cpeeAMeY for more information
    """
    occupied: chess.Bitboard
    nibbles: List[Nibble]
    halfmove_clock: Optional[int]
    plies: Optional[int]
    variant_header: int
    variant_data: Optional[Union[ThreeCheckData, CrazyhouseData]]

    def _halfmove_clock_or_zero(self) -> int:
        return self.halfmove_clock if self.halfmove_clock is not None else 0
    def _plies_or_zero(self) -> int:
        return self.plies if self.plies is not None else 0

    def to_canonical(self) -> Self:
        """
        Multiple binary FEN can correspond to the same position:

        - When a position has multiple black kings with black to move
        - When trailing zeros are omitted from halfmove clock or plies
        - When its black to move and the ply is even

        The 'canonical' position is then the one with every king with the turn set
        And trailing zeros removed

        Return the canonical version of the binary FEN
        """
        is_black_to_move = (15 in self.nibbles) or (self._plies_or_zero() % 2 == 1)
        
        if is_black_to_move:
            canon_nibbles: List[Nibble] = [(15 if nibble == 11 else nibble) for nibble in self.nibbles]
        else:
            canon_nibbles = self.nibbles.copy()

        is_black_to_move_due_to_plies = (15 not in canon_nibbles) and (self._plies_or_zero() % 2 == 1)

        canon_plies = (self._plies_or_zero() + 1) if (is_black_to_move and self._plies_or_zero() % 2 == 0) else self.plies
        canon_halfmove_clock = self.halfmove_clock

        if self.variant_header == 0 and not is_black_to_move_due_to_plies:
            # with black to move, ply == 1 add no information, it's the same as ply == None which
            # equivalent to ply == 0
            if self._plies_or_zero() <= 1:
                canon_plies = None
                if self._halfmove_clock_or_zero() == 0:
                    canon_halfmove_clock = None
        
        return self.__class__(occupied=self.occupied,
                         nibbles=canon_nibbles,
                         halfmove_clock=canon_halfmove_clock,
                         plies=canon_plies,
                         variant_header=self.variant_header,
                         variant_data=self.variant_data
                         )

    @classmethod
    def parse_from_bytes(cls, data: bytes) -> Self:
        """
        Read from bytes and return a BinaryFen

        should not error even if data is invalid
        """
        reader = iter(data)
        return cls.parse_from_iter(reader)

    @classmethod
    def parse_from_iter(cls, reader: Iterator[int]) -> Self:
        """
        Read from bytes and return a `BinaryFen`

        should not error even if data is invalid
        """
        occupied = _read_bitboard(reader)

        nibbles = []
        iter_occupied = chess.scan_forward(occupied)
        for (sq1, sq2) in zip_longest(iter_occupied, iter_occupied):
            lo, hi = _read_nibbles(reader)
            nibbles.append(lo)
            if sq2 is not None:
                nibbles.append(hi)

        halfmove_clock = _read_leb128(reader)
        plies = _read_leb128(reader)

        variant_header = _next0(reader)

        variant_data: Optional[Union[ThreeCheckData, CrazyhouseData]] = None
        if variant_header == VariantHeader.THREE_CHECK:
            lo, hi = _read_nibbles(reader)
            variant_data = ThreeCheckData(white_received_checks=lo, black_received_checks=hi)
        elif variant_header == VariantHeader.CRAZYHOUSE:
            wp, bp = _read_nibbles(reader)
            wn, bn = _read_nibbles(reader)
            wb, bb = _read_nibbles(reader)
            wr, br = _read_nibbles(reader)
            wq, bq = _read_nibbles(reader)
            # optimise?
            white_pocket = CrazyhousePiecePocket(pawns=wp, knights=wn, bishops=wb, rooks=wr, queens=wq)
            black_pocket = CrazyhousePiecePocket(pawns=bp, knights=bn, bishops=bb, rooks=br, queens=bq)
            promoted = _read_bitboard(reader)
            variant_data = CrazyhouseData(white_pocket=white_pocket, black_pocket=black_pocket, promoted=promoted)
        return cls(occupied=occupied,
                   nibbles=nibbles,
                   halfmove_clock=halfmove_clock,
                   plies=plies,
                   variant_header=variant_header,
                   variant_data=variant_data)


    def to_board(self) -> Tuple[chess.Board, Optional[ChessHeader]]:
        """
        Return a chess.Board of the proper variant, and std_mode if applicable

        The returned board might be illegal, check with `board.is_valid()`

        Raise `ValueError` if the BinaryFen data is invalid in a way that chess.Board cannot handle:
        - Invalid variant header
        - Invalid en passant square
        - Multiple en passant squares
        """
        std_mode: Optional[ChessHeader] = ChessHeader.from_int_opt(self.variant_header)

        board = VariantHeader(self.variant_header).board()
        ep_square_set = False
        for sq, nibble in zip(chess.scan_forward(self.occupied), self.nibbles):
            if not ep_square_set:
                ep_square_set = _unpack_piece(board, sq, nibble)
            else:
                if _unpack_piece(board, sq, nibble):
                    raise ValueError("At least two passant squares found")
        board.halfmove_clock = self._halfmove_clock_or_zero()
        board.fullmove_number = self._plies_or_zero()//2 + 1
        # it is important to write it that way
        # because default turn can have been already set to black inside `_unpack_piece`
        if self._plies_or_zero() % 2 == 1:
            board.turn = chess.BLACK

        if isinstance(board, chess.variant.ThreeCheckBoard) and isinstance(self.variant_data, ThreeCheckData):
            # remaining check are for the opposite side
            board.remaining_checks[chess.WHITE] = 3 - self.variant_data.black_received_checks
            board.remaining_checks[chess.BLACK] = 3 - self.variant_data.white_received_checks
        elif isinstance(board, chess.variant.CrazyhouseBoard) and isinstance(self.variant_data, CrazyhouseData):
            board.pockets[chess.WHITE] = self.variant_data.white_pocket.to_crazyhouse_pocket()
            board.pockets[chess.BLACK] = self.variant_data.black_pocket.to_crazyhouse_pocket()
            board.promoted = self.variant_data.promoted
        return (board, std_mode)
        

    @classmethod
    def decode(cls, data: bytes) -> Tuple[chess.Board, Optional[ChessHeader]]:
        """
        Read from bytes and return a chess.Board of the proper variant

        If it is standard chess position, also return the mode (standard, chess960, from_position)

        raise `ValueError` if data is invalid
        """
        binary_fen = cls.parse_from_bytes(data)
        return binary_fen.to_board()


    @classmethod
    def parse_from_board(cls, board: chess.Board, std_mode: Optional[ChessHeader]=None) -> Self:
        """
        Given a chess.Board, return its binary FEN representation, and std_mode if applicable

        If the board is a standard chess position, `std_mode` can be provided to specify the mode (standard, chess960, from_position)
        if not provided, it will be inferred from the root position
        """
        if std_mode is not None and type(board).uci_variant != "chess":
            raise ValueError("std_mode can only be provided for standard chess positions")
        occupied = board.occupied
        iter_occupied = chess.scan_forward(occupied)
        nibbles: List[Nibble] = []
        for (sq1, sq2) in zip_longest(iter_occupied, iter_occupied):
            lo = _pack_piece(board, sq1)
            nibbles.append(lo)
            if sq2 is not None:
                hi = _pack_piece(board, sq2)
                nibbles.append(hi)
            
        plies = board.ply()
        binary_ply = None
        binary_halfmove_clock = None

        broken_turn = board.king(chess.BLACK) is None and board.turn == chess.BLACK
        variant_header = std_mode.value if std_mode is not None else VariantHeader.encode(board).value

        if board.halfmove_clock > 0 or plies > 1 or broken_turn or variant_header != 0:
            binary_halfmove_clock = board.halfmove_clock

        if plies > 1 or broken_turn or variant_header != 0:
            binary_ply = plies

        variant_data: Optional[Union[ThreeCheckData, CrazyhouseData]] = None
        if variant_header != VariantHeader.STANDARD:
            if isinstance(board, chess.variant.ThreeCheckBoard):
                black_received_checks = _to_nibble(3 - board.remaining_checks[chess.WHITE])
                white_received_checks = _to_nibble(3 - board.remaining_checks[chess.BLACK])
                variant_data = ThreeCheckData(white_received_checks=white_received_checks, black_received_checks=black_received_checks)
            elif isinstance(board, chess.variant.CrazyhouseBoard):
                variant_data = CrazyhouseData(
                    white_pocket=CrazyhousePiecePocket.from_crazyhouse_pocket(board.pockets[chess.WHITE]),
                    black_pocket=CrazyhousePiecePocket.from_crazyhouse_pocket(board.pockets[chess.BLACK]),
                    promoted=board.promoted
                )
        return cls(occupied=occupied,
                     nibbles=nibbles,
                     halfmove_clock=binary_halfmove_clock,
                     plies=binary_ply,
                     variant_header=variant_header,
                     variant_data=variant_data)


    def to_bytes(self) -> bytes:
        """
        Write the BinaryFen data as bytes
        """
        builder = bytearray()
        _write_bitboard(builder, self.occupied)
        iter_nibbles: Iterator[Nibble] = iter(self.nibbles)
        for (lo, hi) in zip_longest(iter_nibbles, iter_nibbles,fillvalue=0):
            _write_nibbles(builder, cast(Nibble, lo), cast(Nibble, hi))
        

        if self.halfmove_clock is not None:
            _write_leb128(builder, self.halfmove_clock)

        if self.plies is not None:
            _write_leb128(builder, self.plies)

        if self.variant_header != VariantHeader.STANDARD:
            builder.append(self.variant_header)
            if isinstance(self.variant_data, ThreeCheckData):
                _write_nibbles(builder, self.variant_data.white_received_checks, self.variant_data.black_received_checks)
            elif isinstance(self.variant_data, CrazyhouseData):
                _write_nibbles(builder, self.variant_data.white_pocket.pawns, self.variant_data.black_pocket.pawns)
                _write_nibbles(builder, self.variant_data.white_pocket.knights, self.variant_data.black_pocket.knights)
                _write_nibbles(builder, self.variant_data.white_pocket.bishops, self.variant_data.black_pocket.bishops)
                _write_nibbles(builder, self.variant_data.white_pocket.rooks, self.variant_data.black_pocket.rooks)
                _write_nibbles(builder, self.variant_data.white_pocket.queens, self.variant_data.black_pocket.queens)

                if self.variant_data.promoted:
                    _write_bitboard(builder, self.variant_data.promoted)
        return bytes(builder)

    def __bytes__(self) -> bytes:
        """
        Write the BinaryFen data as bytes

        Example: bytes(my_binary_fen)
        """
        return self.to_bytes()


    @classmethod
    def encode(cls, board: chess.Board, std_mode: Optional[ChessHeader]=None) -> bytes:
        """
        Given a chess.Board, return its binary FEN representation, and std_mode if applicable

        If the board is a standard chess position, `std_mode` can be provided to specify the mode (standard, chess960, from_position)
        if not provided, it will be inferred from the root position
        """
        binary_fen = cls.parse_from_board(board, std_mode)
        return binary_fen.to_bytes()

def _pack_piece(board: chess.Board, sq: chess.Square) -> Nibble:
    # Encoding from
    # https://github.com/official-stockfish/nnue-pytorch/blob/2db3787d2e36f7142ea4d0e307b502dda4095cd9/lib/nnue_training_data_formats.h#L4607
    piece = board.piece_at(sq)
    if piece is None:
        raise ValueError(f"Unreachable: no piece at square {sq}, board: {board}")
    if piece.piece_type == chess.PAWN:
        if board.ep_square is not None:
            rank = chess.square_rank(sq)
            if (board.ep_square + 8 == sq and piece.color == chess.WHITE and rank == 3) or (board.ep_square - 8 == sq and piece.color == chess.BLACK and rank == 4):
                return 12
        return 0 if piece.color == chess.WHITE else 1
    elif piece.piece_type == chess.KNIGHT:
        return 2 if piece.color == chess.WHITE else 3
    elif piece.piece_type == chess.BISHOP:
        return 4 if piece.color == chess.WHITE else 5
    elif piece.piece_type == chess.ROOK:
        if board.castling_rights & chess.BB_SQUARES[sq]:
            return 13 if piece.color == chess.WHITE else 14
        return 6 if piece.color == chess.WHITE else 7
    elif piece.piece_type == chess.QUEEN:
        return 8 if piece.color == chess.WHITE else 9
    elif piece.piece_type == chess.KING:
        if piece.color == chess.BLACK and board.turn == chess.BLACK:
            return 15
        return 10 if piece.color == chess.WHITE else 11
    raise ValueError(f"Unreachable: unknown piece {piece} at square {sq}, board: {board}")

def _unpack_piece(board: chess.Board, sq: chess.Square, nibble: Nibble) -> bool:
    """Return true if set the en passant square"""
    if nibble == 0:
        board.set_piece_at(sq, chess.Piece(chess.PAWN, chess.WHITE))
    elif nibble == 1:
        board.set_piece_at(sq, chess.Piece(chess.PAWN, chess.BLACK))
    elif nibble == 2:
        board.set_piece_at(sq, chess.Piece(chess.KNIGHT, chess.WHITE))
    elif nibble == 3:
        board.set_piece_at(sq, chess.Piece(chess.KNIGHT, chess.BLACK))
    elif nibble == 4:
        board.set_piece_at(sq, chess.Piece(chess.BISHOP, chess.WHITE))
    elif nibble == 5:
        board.set_piece_at(sq, chess.Piece(chess.BISHOP, chess.BLACK))
    elif nibble == 6:
        board.set_piece_at(sq, chess.Piece(chess.ROOK, chess.WHITE))
    elif nibble == 7:
        board.set_piece_at(sq, chess.Piece(chess.ROOK, chess.BLACK))
    elif nibble == 8:
        board.set_piece_at(sq, chess.Piece(chess.QUEEN, chess.WHITE))
    elif nibble == 9:
        board.set_piece_at(sq, chess.Piece(chess.QUEEN, chess.BLACK))
    elif nibble == 10:
        board.set_piece_at(sq, chess.Piece(chess.KING, chess.WHITE))
    elif nibble == 11:
        board.set_piece_at(sq, chess.Piece(chess.KING, chess.BLACK))
    elif nibble == 12:
        # in scalachess rank starts at 1, python-chess 0
        rank = chess.square_rank(sq)
        if rank == 3:
            color = chess.WHITE
        elif rank == 4:
            color = chess.BLACK
        else:
            raise ValueError(f"Pawn at square {chess.square_name(sq)} cannot be an en passant pawn")
        board.ep_square = sq - 8 if color else sq + 8
        board.set_piece_at(sq, chess.Piece(chess.PAWN, color))
        return True
    elif nibble == 13:
        board.castling_rights |= chess.BB_SQUARES[sq]
        board.set_piece_at(sq, chess.Piece(chess.ROOK, chess.WHITE))
    elif nibble == 14:
        board.castling_rights |= chess.BB_SQUARES[sq]
        board.set_piece_at(sq, chess.Piece(chess.ROOK, chess.BLACK))
    elif nibble == 15:
        board.turn = chess.BLACK
        board.set_piece_at(sq, chess.Piece(chess.KING, chess.BLACK))
    else:
        raise ValueError(f"Impossible nibble value: {nibble} at square {chess.square_name(sq)}")
    return False

def _next0(reader: Iterator[int]) -> int:
    return next(reader, 0)

def _read_bitboard(reader: Iterator[int]) -> chess.Bitboard:
    bb = chess.BB_EMPTY
    for _ in range(8):
        bb = (bb << 8) | (_next0(reader) & 0xFF)
    return bb

def _write_bitboard(data: bytearray, bb: chess.Bitboard) -> None:
    for shift in range(56, -1, -8):
        data.append((bb >> shift) & 0xFF)

def _read_nibbles(reader: Iterator[int]) -> Tuple[Nibble, Nibble]:
    byte = _next0(reader)
    return cast(Nibble, byte & 0x0F), cast(Nibble, (byte >> 4) & 0x0F)

def _write_nibbles(data: bytearray, lo: Nibble, hi: Nibble) -> None:
    data.append((hi << 4) | (lo & 0x0F)) 

def _read_leb128(reader: Iterator[int]) -> Optional[int]:
    result = 0
    shift = 0
    while True:
        byte = next(reader, None)
        if byte is None:
            return None
        result |= (byte & 127) << shift
        if (byte & 128) == 0:
            break
        shift += 7
    # this is useless
    return result & 0x7fff_ffff

def _write_leb128(data: bytearray, value: int) -> None:
    while True:
        byte = value & 127
        value >>= 7
        if value != 0:
            byte |= 128
        data.append(byte)
        if value == 0:
            break

def _to_nibble(value: int) -> Nibble:
    if 0 <= value <= 15:
        return cast(Nibble, value)
    else:
        raise ValueError(f"Value {value} cannot be represented as a nibble")



