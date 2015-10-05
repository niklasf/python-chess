# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2015 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
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

import chess
import struct
import os
import mmap
import random
import itertools
import chess
import errno
import sys

try:
    import backport_collections as collections
except ImportError:
    import collections

ENTRY_STRUCT = struct.Struct(">QHHI")


class Entry(collections.namedtuple("Entry", ["key", "raw_move", "weight", "learn"])):
    """An entry from a polyglot opening book."""

    def move(self, chess960=False):
        """Gets the move (as a :class:`~chess.Move` object)."""
        # Extract source and target square.
        to_square = self.raw_move & 0x3f
        from_square = (self.raw_move >> 6) & 0x3f

        # Extract the promotion type.
        promotion_part = (self.raw_move >> 12) & 0x7
        promotion = promotion_part + 1 if promotion_part else None

        # Convert castling moves.
        if not chess960 and not promotion:
            if from_square == chess.E1:
                if to_square == chess.H1:
                    return chess.Move(chess.E1, chess.G1)
                elif to_square == chess.A1:
                    return chess.Move(chess.E1, chess.C1)
            elif from_square == chess.E8:
                if to_square == chess.H8:
                    return chess.Move(chess.E8, chess.G8)
                elif to_square == chess.A8:
                    return chess.Move(chess.E8, chess.C8)

        return chess.Move(from_square, to_square, promotion)


class MemoryMappedReader(object):
    """Maps a polyglot opening book to memory."""

    def __init__(self, filename):
        self.fd = os.open(filename, os.O_RDONLY | os.O_BINARY if hasattr(os, "O_BINARY") else os.O_RDONLY)

        try:
            self.mmap = mmap.mmap(self.fd, 0, access=mmap.ACCESS_READ)
        except (ValueError, mmap.error):
            # Can not memory map empty opening books.
            self.mmap = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.close()

    def close(self):
        """Closes the reader."""
        if self.mmap is not None:
            self.mmap.close()

        try:
            os.close(self.fd)
        except OSError:
            pass

    def __len__(self):
        if self.mmap is None:
            return 0
        else:
            return self.mmap.size() // ENTRY_STRUCT.size

    def __getitem__(self, key):
        if self.mmap is None:
            raise IndexError()

        if key < 0:
            key = len(self) + key

        try:
            key, raw_move, weight, learn = ENTRY_STRUCT.unpack_from(self.mmap, key * ENTRY_STRUCT.size)
        except struct.error:
            raise IndexError()

        return Entry(key, raw_move, weight, learn)

    def __iter__(self):
        i = 0
        size = len(self)
        while i < size:
            yield self[i]
            i += 1

    def bisect_key_left(self, key):
        lo = 0
        hi = len(self)

        while lo < hi:
            mid = (lo + hi) // 2
            mid_key, _, _, _ = ENTRY_STRUCT.unpack_from(self.mmap, mid * ENTRY_STRUCT.size)
            if mid_key < key:
                lo = mid + 1
            else:
                hi = mid

        return lo

    def __contains__(self, entry):
        return any(current == entry for current in self.find_all(entry.key, entry.weight))

    def find_all(self, board, minimum_weight=1, exclude_moves=()):
        """Seeks a specific position and yields corresponding entries."""
        try:
            zobrist_hash = board.zobrist_hash()
        except AttributeError:
            zobrist_hash = int(board)
            board = None

        i = self.bisect_key_left(zobrist_hash)
        size = len(self)

        while i < size:
            entry = self[i]
            i += 1

            if entry.key != zobrist_hash:
                break

            if entry.weight < minimum_weight:
                continue

            if board:
                move = entry.move(chess960=board.chess960)
            elif exclude_moves:
                move = entry.move()

            if exclude_moves and move in exclude_moves:
                continue

            if board and not board.is_legal(move):
                continue

            yield entry

    def find(self, board, minimum_weight=1, exclude_moves=()):
        """
        Finds the main entry for the given position or zobrist hash.

        The main entry is the first entry with the highest weight.

        By default entries with weight ``0`` are excluded. This is a common way
        to delete entries from an opening book without compacting it. Pass
        *minimum_weight* ``0`` to select all entries.

        Raises :exc:`IndexError` if no entries are found.
        """
        try:
            return max(self.find_all(board, minimum_weight, exclude_moves), key=lambda entry: entry.weight)
        except ValueError:
            raise IndexError()

    def choice(self, board, minimum_weight=1, exclude_moves=(), random=random):
        """
        Uniformly selects a random entry for the given position.

        Raises :exc:`IndexError` if no entries are found.
        """
        total_entries = sum(1 for entry in self.find_all(board, minimum_weight, exclude_moves))
        if not total_entries:
            raise IndexError()

        choice = random.randint(0, total_entries - 1)
        return next(itertools.islice(self.find_all(board, minimum_weight, exclude_moves), choice, None))

    def weighted_choice(self, board, exclude_moves=(), random=random):
        """
        Selects a random entry for the given position, distributed by the
        weights of the entries.

        Raises :exc:`IndexError` if no entries are found.
        """
        total_weights = sum(entry.weight for entry in self.find_all(board, exclude_moves=exclude_moves))
        if not total_weights:
            raise IndexError()

        choice = random.randint(0, total_weights - 1)

        current_sum = 0
        for entry in self.find_all(board, exclude_moves=exclude_moves):
            current_sum += entry.weight
            if current_sum > choice:
                return entry

        assert False


def open_reader(path):
    """
    Creates a reader for the file at the given path.

    >>> with open_reader("data/polyglot/performance.bin") as reader:
    ...    for entry in reader.find_all(board):
    ...        print(entry.move(), entry.weight, entry.learn)
    e2e4 1 0
    d2d4 1 0
    c2c4 1 0
    """
    return MemoryMappedReader(path)
