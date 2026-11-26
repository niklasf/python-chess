from __future__ import annotations

import chess
import contextlib
import mmap
import os

from types import TracebackType
from typing import NamedTuple, TypeAlias
from collections.abc import Iterator


StrOrBytesPath: TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]


# Codes of square contents as (bits, length), for the side to move as white.
_SQUARE_CODES = {
    None: (0x00, 1),
    (chess.KING, chess.WHITE): (0x20, 6), (chess.KING, chess.BLACK): (0x21, 6),
    (chess.QUEEN, chess.WHITE): (0x22, 6), (chess.QUEEN, chess.BLACK): (0x23, 6),
    (chess.KNIGHT, chess.WHITE): (0x12, 5), (chess.KNIGHT, chess.BLACK): (0x13, 5),
    (chess.BISHOP, chess.WHITE): (0x14, 5), (chess.BISHOP, chess.BLACK): (0x15, 5),
    (chess.ROOK, chess.WHITE): (0x16, 5), (chess.ROOK, chess.BLACK): (0x17, 5),
    (chess.PAWN, chess.WHITE): (0x06, 3), (chess.PAWN, chess.BLACK): (0x07, 3),
}

_HASH_BITS = [
    0x3100d2bf, 0x3118e3de, 0x34ab1372, 0x2807a847, 0x1633f566, 0x2143b359, 0x26d56488, 0x3b9e6f59,
    0x37755656, 0x3089ca7b, 0x18e92d85, 0x0cd0e9d8, 0x1a9e3b54, 0x3eaa902f, 0x0d9bfaae, 0x2f32b45b,
    0x31ed6102, 0x3d3c8398, 0x146660e3, 0x0f8d4b76, 0x02c77a5f, 0x146c8799, 0x1c47f51f, 0x249f8f36,
    0x24772043, 0x1fbc1e4d, 0x1e86b3fa, 0x37df36a6, 0x16ed30e4, 0x02c3148e, 0x216e5929, 0x0636b34e,
    0x317f9f56, 0x15f09d70, 0x131026fb, 0x38c784b1, 0x29ac3305, 0x2b485dc5, 0x3c049ddc, 0x35a9fbcd,
    0x31d5373b, 0x2b246799, 0x0a2923d3, 0x08a96e9d, 0x30031a9f, 0x08f525b5, 0x33611c06, 0x2409db98,
    0x0ca4feb2, 0x1000b71e, 0x30566e32, 0x39447d31, 0x194e3752, 0x08233a95, 0x0f38fe36, 0x29c7cd57,
    0x0f7b3a39, 0x328e8a16, 0x1e7d1388, 0x0fba78f5, 0x274c7e7c, 0x1e8be65c, 0x2fa0b0bb, 0x1eb6c371,
]

# Squares in the order of the encoding: a1, a2, ..., a8, b1, ..., h8.
_FILE_MAJOR = [chess.square(file, rank) for file in range(8) for rank in range(8)]

# Move byte -> move code. Codes past the end of _MOVES are not moves.
_CODES = bytes.fromhex(
    "816bc397730b7eb8995605d472453e63c8ec49018d47dab587e69450f557c0eb"
    "fa425da28eb94a7a1d176de5c28543126c1455d160bc5f0ea01648a64ce7d9e3"
    "cfa120ea041bbd23dfff8c22688fbedb2cdc33a75e77f1b0f7abfeee89d0c980"
    "e41e74a4b2ac4e02d83b4609c1d632a3c4ad58d513c5afb6f659293a7935242e"
    "212786d2f061342b5be9657106f3a918b7ed9de10dca7507302a1078cb0cb454"
    "91e21a8bfd39f24dc73df4a5bf3f9f0092844bfbe840fc0fde53ba7f9a9003d3"
    "cc44524f3c38938a88955c835a2fb17bf876676ab3c6cd2641256470bbef8208"
    "6e2de037dd157c1c2866ae7d6f1faa319c19ce6936510a62969b989ed711a8f9")

# Steps as (files right, ranks forward), modulo 8: targets wrap around.
_KING = [(0, 1), (1, 1), (1, 0), (1, 7), (0, 7), (7, 7), (7, 0), (7, 1), (2, 0), (6, 0)]
_ROOK = [(0, i) for i in range(1, 8)] + [(i, 0) for i in range(1, 8)]
_BISHOP = [(i, i) for i in range(1, 8)] + [(i, 8 - i) for i in range(1, 8)]
_KNIGHT = [(2, 1), (1, 2), (7, 2), (6, 1), (6, 7), (7, 6), (1, 6), (2, 7)]
_PAWN = [(0, 1), (0, 2), (1, 1), (7, 1)]

# Move code -> (piece type, nth such piece in _FILE_MAJOR order, step), from
# the point of view of the side to move. Codes start at 1.
_MOVES = [(piece_type, nth, step) for piece_type, nth, steps in [
    (chess.KING, 1, _KING), (chess.QUEEN, 1, _ROOK + _BISHOP), (chess.ROOK, 1, _ROOK), (chess.ROOK, 2, _ROOK),
    (chess.BISHOP, 1, _BISHOP), (chess.BISHOP, 2, _BISHOP), (chess.KNIGHT, 1, _KNIGHT), (chess.KNIGHT, 2, _KNIGHT),
    *[(chess.PAWN, nth, _PAWN) for nth in range(1, 9)],
    (chess.QUEEN, 2, _ROOK + _BISHOP), (chess.QUEEN, 3, _ROOK + _BISHOP), (chess.ROOK, 3, _ROOK),
    (chess.BISHOP, 3, _BISHOP), (chess.KNIGHT, 3, _KNIGHT),
] for step in steps]

# Evaluations are stored for the side to move as white.
_FLIP_NAG = {14: 15, 15: 14, 16: 17, 17: 16, 18: 19, 19: 18}

# Fields of a position record as (tag, size), unless the book lists its own:
# signature, moves, and statistics of 30, 2 and 1 bytes. Statistics are read
# from the start of the fields of fixed size, whatever their tags.
_LAYOUT_OFFSET = 0x400
_VARIABLE = 0x7fff
_LAYOUT = [(1, _VARIABLE), (3, _VARIABLE), (5, 30), (6, 2), (7, 1)]
_STATS_SIZE = 33


class Entry(NamedTuple):
    """A move from a CTG opening book."""

    move: chess.Move
    """The :class:`~chess.Move`."""

    games: int
    """The number of games with this move."""

    wins: int
    """The number of games won by the side making the move."""

    draws: int
    """The number of drawn games."""

    losses: int
    """The number of games lost by the side making the move."""

    rating: int | None
    """
    The average rating of the players making the move, or ``None`` if none
    of them is rated.
    """

    opponent_rating: int | None
    """The average rating of their opponents, or ``None``."""

    nag: int
    """
    The NAG annotating the move, like :data:`chess.pgn.NAG_GOOD_MOVE`, or
    ``0``.
    """

    weight: int
    """
    How engines choose the move: ``0`` by its statistics, ``1`` to ``7`` by
    this weight, higher values preferred.
    """

    recommendation: int
    """
    Flags for engines: ``0x80`` marks a tournament move, ``0x40`` a move to
    avoid. Lower bits record engine learning.
    """

    learn: int
    """A score engines use for the move, from ``-128`` to ``127``."""

    evaluation: int
    """
    The NAG evaluating the position after the move, like
    ``chess.pgn.NAG_WHITE_SLIGHT_ADVANTAGE``, or ``0``.
    """


def _transform(board: chess.Board) -> list[chess.Square] | None:
    # Positions are stored with the side to move as white. If nobody can
    # castle, its king is moved to files e-h. Without pawns it is also moved
    # to ranks 1-4, and if it is then below the a8-h1 diagonal, or on it with
    # the other king below, the board is reflected in the a1-h8 diagonal.
    # Returns the square of the board for each square of the stored position.
    king = board.king(board.turn)
    other = board.king(not board.turn)
    if king is None or other is None:
        return None
    mask = 0 if board.turn == chess.WHITE else 0x38
    transpose = False
    if not board.castling_rights:
        if chess.square_file(king) < 4:
            mask ^= 0x07
        if not board.pawns:
            if chess.square_rank(king ^ mask) > 3:
                mask ^= 0x38
            diagonal = [chess.square_file(k ^ mask) + chess.square_rank(k ^ mask) - 7 for k in [king, other]]
            transpose = diagonal[0] < 0 or (diagonal[0] == 0 and diagonal[1] < 0)
    if transpose:
        return [(square >> 3 | (square & 7) << 3) ^ mask for square in chess.SQUARES]
    return [square ^ mask for square in chess.SQUARES]


def _signature(board: chess.Board, squares: list[chess.Square], alternate: bool, chess960: bool) -> bytes:
    # Bits fill each byte from the top. The alternate format starts with the
    # side to move, which is white.
    bits: list[int] = [0] if alternate else []

    def append(value: int, length: int) -> None:
        bits.extend((value >> i) & 1 for i in reversed(range(length)))

    for square in _FILE_MAJOR:
        piece = board.piece_at(squares[square])
        append(*_SQUARE_CODES[None if piece is None else (piece.piece_type, piece.color == board.turn)])

    # Chess960 positions add the files of the rooks for white O-O, white
    # O-O-O, black O-O and black O-O-O, in the colours of the board.
    chess960 = chess960 and not alternate
    if chess960:
        for color in chess.COLORS:
            king = board.king(color)
            assert king is not None
            rooks = [chess.square_file(rook) for rook in chess.scan_forward(board.clean_castling_rights() & board.occupied_co[color])]
            append(max([file for file in rooks if file > chess.square_file(king)], default=7), 3)
            append(min([file for file in rooks if file < chess.square_file(king)], default=0), 3)

    # Castling rights and the en passant file go into the low bits of the
    # last byte. Without them, standard signatures end with an empty byte if
    # the last one is full.
    castling = (
        (board.has_queenside_castling_rights(board.turn) and 0x01) |
        (board.has_kingside_castling_rights(board.turn) and 0x02) |
        (board.has_queenside_castling_rights(not board.turn) and 0x04) |
        (board.has_kingside_castling_rights(not board.turn) and 0x08))
    ep_square = board.ep_square if board.has_pseudo_legal_en_passant() else None
    flags, length = castling, 4 if castling else 0
    if ep_square is not None:
        flags |= chess.square_file(squares.index(ep_square)) << length
        length += 3

    used = len(bits) % 8
    if length:
        if used + length > 8:
            bits.extend([0] * (8 - used))
            used = 0
        bits.extend([0] * (8 - used - length))
        append(flags, length)
    elif used:
        bits.extend([0] * (8 - used))
    elif not chess960 and not alternate:
        bits.extend([0] * 8)

    size = 1 + len(bits) // 8
    header = size | (0x20 if ep_square is not None else 0) | (0x40 if castling else 0) | (0x80 if chess960 else 0)
    return bytes([header]) + bytes(sum(bit << (7 - i) for i, bit in enumerate(bits[j:j + 8])) for j in range(0, len(bits), 8))


def _hash(signature: bytes) -> int:
    h = 0
    t = 0
    for byte in signature:
        t += ((0x0f - (byte & 0x0f)) << 2) + 1
        h += _HASH_BITS[t & 0x3f]
        t += ((0xf0 - (byte & 0xf0)) >> 2) + 1
        h += _HASH_BITS[t & 0x3f]
    return h & 0xffff_ffff


def _average(buf: bytes, pos: int) -> int | None:
    games = int.from_bytes(buf[pos:pos + 3], "big")
    return int.from_bytes(buf[pos + 3:pos + 7], "big") // games if games else None


class MemoryMappedReader:
    """Maps a CTG opening book to memory."""

    def __init__(self, filename: StrOrBytesPath) -> None:
        # Books of variants have a suffix after each extension, like
        # .ctg-960, .cto-960 and .ctb-960.
        base, ext = os.path.splitext(os.fsdecode(filename))
        suffix = ext[4:].lower()
        if ext[:4].lower() != ".ctg" or suffix not in ["", "-960"]:
            raise ValueError(f"expected path to .ctg or .ctg-960 file: {filename!r}")
        self._chess960 = suffix == "-960"

        def sibling(c: str) -> str:
            return base + ext[:3] + (c.upper() if ext[3].isupper() else c) + ext[4:]

        with contextlib.ExitStack() as stack:
            self._ctg = stack.enter_context(self._map(base + ext, filename))
            self._cto = stack.enter_context(self._map(sibling("o"), filename))
            self._ctb = stack.enter_context(self._map(sibling("b"), filename))
            self._read_headers(filename)
            stack.pop_all()

    def _read_headers(self, filename: StrOrBytesPath) -> None:
        def u16(m: mmap.mmap, pos: int) -> int:
            return int.from_bytes(m[pos:pos + 2], "big")

        def u32(m: mmap.mmap, pos: int) -> int:
            return int.from_bytes(m[pos:pos + 4], "big")

        if len(self._ctg) < _LAYOUT_OFFSET + 4 or len(self._cto) < 16 or len(self._ctb) < 12:
            raise IOError(f"invalid ctg opening book: {filename!r}")

        # Pages of positions.
        self._data_offset = u16(self._ctg, 2)
        self._page_size = u16(self._ctg, 10)
        self._pages = u32(self._ctg, 16)

        # Fields of a position record. Tag 11 selects the alternate signature.
        layout = _LAYOUT
        if u16(self._ctg, _LAYOUT_OFFSET):
            count = u16(self._ctg, _LAYOUT_OFFSET + 2)
            layout = [(u16(self._ctg, _LAYOUT_OFFSET + 4 + 4 * i), u16(self._ctg, _LAYOUT_OFFSET + 6 + 4 * i)) for i in range(count)]
        self._fixed_size = sum(size for _, size in layout if size != _VARIABLE)
        self._alternate = any(tag & 0x1f == 11 for tag, _ in layout)
        if self._fixed_size < _STATS_SIZE:
            raise ValueError(f"unsupported ctg record layout {layout}: {filename!r}")

        # Page of each key.
        self._cto_offset = u16(self._cto, 0)
        self._cto_end = u32(self._cto, 4)
        self._cto_start = u32(self._cto, 8)
        self._cto_first = u32(self._cto, 12)

        # Bit per key, set if the key is split into two longer ones. Keys
        # below the range are split, keys above it are not.
        self._ctb_offset = u16(self._ctb, 0)
        self._ctb_start = u32(self._ctb, 4)
        self._ctb_end = u32(self._ctb, 8)

    @staticmethod
    def _map(path: str, filename: StrOrBytesPath) -> mmap.mmap:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            return mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        except ValueError:
            raise IOError(f"invalid ctg opening book: {filename!r}")
        finally:
            os.close(fd)

    def __enter__(self) -> MemoryMappedReader:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        return self.close()

    def _split(self, key: int) -> bool:
        if key < self._ctb_start:
            return True
        pos = self._ctb_offset + (key >> 3)
        return key < self._ctb_end and pos < len(self._ctb) and bool(self._ctb[pos] >> (key & 7) & 1)

    def _page(self, signature: bytes) -> int | None:
        # Keys take ever more low bits of the hash, until one is not split.
        h = _hash(signature)
        mask = 0
        key = 0
        while self._split(key) and mask < 0x3fff_ffff:
            mask = mask << 1 | 1
            key = (h & mask) + mask
        if not max(self._cto_start, self._cto_first) <= key < self._cto_end:
            return None
        pos = self._cto_offset + (key - self._cto_start) * 4
        page = int.from_bytes(self._cto[pos:pos + 4], "big")
        return page if page < self._pages else None

    def _lookup(self, board: chess.Board) -> tuple[list[chess.Square], bytes, bytes] | None:
        squares = _transform(board)
        if squares is None:
            return None
        signature = _signature(board, squares, self._alternate, self._chess960)
        page = self._page(signature)
        if page is None:
            return None

        start = self._data_offset + page * self._page_size
        buf = self._ctg[start:start + self._page_size]
        used = int.from_bytes(buf[2:4], "big")
        pos = 4
        for _ in range(int.from_bytes(buf[0:2], "big")):
            if pos >= used:
                break
            size = buf[pos] & 0x1f
            moves_size = buf[pos + size]
            if buf[pos:pos + size] == signature:
                stats = pos + size + moves_size
                return squares, buf[pos + size + 1:stats], buf[stats:stats + _STATS_SIZE]
            pos += size + moves_size + self._fixed_size
        return None

    def find_all(self, board: chess.Board) -> Iterator[Entry]:
        """
        Seeks a specific position and yields its book moves.

        Moves whose resulting position is not in the book are skipped.
        """
        found = self._lookup(board)
        if found is None:
            return
        squares, moves, _ = found

        for i in range(0, len(moves) - 1, 2):
            code = _CODES[moves[i]]
            if not 0 < code <= len(_MOVES):
                continue
            piece_type, nth, (right, forward) = _MOVES[code - 1]

            ours = [s for s in _FILE_MAJOR if board.piece_at(squares[s]) == chess.Piece(piece_type, board.turn)]
            if len(ours) < nth:
                continue
            from_square = ours[nth - 1]
            to_square = chess.square((chess.square_file(from_square) + right) % 8, (chess.square_rank(from_square) + forward) % 8)

            try:
                move = board.find_move(squares[from_square], squares[to_square])
            except chess.IllegalMoveError:
                continue

            # Statistics are stored with the position after the move, with
            # its side to move as white. Moves without one are not in the book.
            board.push(move)
            try:
                child = self._lookup(board)
                flipped = board.turn == chess.BLACK
            finally:
                board.pop()
            if child is None:
                continue
            stats = child[2]

            games, losses, wins, draws = (int.from_bytes(stats[j:j + 3], "big") for j in range(0, 12, 3))
            annotation = moves[i + 1]
            evaluation = stats[32]
            yield Entry(
                move=move,
                games=games,
                wins=wins,
                draws=draws,
                losses=losses,
                rating=_average(stats, 23),
                opponent_rating=_average(stats, 16),
                nag=annotation & 0x1f,
                weight=annotation >> 5,
                recommendation=stats[30],
                learn=int.from_bytes(stats[31:32], "big", signed=True),
                evaluation=_FLIP_NAG.get(evaluation, evaluation) if flipped else evaluation)

    def close(self) -> None:
        """Closes the reader."""
        self._ctg.close()
        self._cto.close()
        self._ctb.close()


def open_reader(path: StrOrBytesPath) -> MemoryMappedReader:
    """
    Creates a reader for the CTG opening book at the given path to the
    ``.ctg`` file, or ``.ctg-960`` for Chess960. The ``.cto`` and ``.ctb``
    files (``.cto-960`` and ``.ctb-960``) are expected next to it.

    >>> import chess
    >>> import chess.ctg
    >>>
    >>> board = chess.Board()
    >>>
    >>> with chess.ctg.open_reader("book.ctg") as reader:
    ...    for entry in reader.find_all(board):
    ...        print(entry.move, entry.games, entry.wins, entry.draws, entry.losses)
    """
    return MemoryMappedReader(path)
