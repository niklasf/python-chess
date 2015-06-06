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
import collections
import struct
import os
import mmap
import random
import itertools


ENTRY_STRUCT = struct.Struct(">QHHI")


class Entry(collections.namedtuple("Entry", ["key", "raw_move", "weight", "learn"])):
    """An entry from a polyglot opening book."""

    def move(self):
        """Gets the move (as a `Move` object)."""
        # Extract source and target square.
        to_square = self.raw_move & 0x3f
        from_square = (self.raw_move >> 6) & 0x3f

        # Extract the promotion type.
        promotion_part = (self.raw_move >> 12) & 0x7
        if promotion_part == 4:
            return chess.Move(from_square, to_square, chess.QUEEN)
        elif promotion_part == 3:
            return chess.Move(from_square, to_square, chess.ROOK)
        elif promotion_part == 2:
            return chess.Move(from_square, to_square, chess.BISHOP)
        elif promotion_part == 1:
            return chess.Move(from_square, to_square, chess.KNIGHT)
        else:
            return chess.Move(from_square, to_square)


class MemoryMappedReader(object):
    """Maps a polylgot opening book to memory."""

    def __init__(self, filename):
        self.fd = os.open(filename, os.O_RDONLY | os.O_BINARY if hasattr(os, "O_BINARY") else os.O_RDONLY)

        try:
            self.mmap = mmap.mmap(self.fd, 0, access=mmap.ACCESS_READ)
        except ValueError:
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
            key = len(self) - key

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

    def find(self, board, minimum_weight=1):
        """
        Finds the main entry for the given position or zobrist hash.

        The main entry is the first entry with the highest weight.

        By default entries with weight *0* are excluded. This is a common way
        to delete entries from an opening book without compacting it. Pass
        *minimum_weight=0* to select all entries.

        Raises *IndexError* if no entries are found.
        """
        try:
            return max(self.find_all(board, minimum_weight), key=lambda entry: entry.weight)
        except ValueError:
            raise IndexError()

    def find_all(self, board, minimum_weight=1):
        """Seeks a specific position and yields corresponding entries."""
        try:
            zobrist_hash = board.zobrist_hash()
        except AttributeError:
            zobrist_hash = int(board)

        i = self.bisect_key_left(zobrist_hash)
        size = len(self)

        while i < size:
            entry = self[i]

            if entry.key != zobrist_hash:
                break
            else:
                yield entry

            i += 1

    def choice(self, board, minimum_weight=1, random=random):
        """
        Uniformly selects a random entry for the given position.

        Raises *IndexError* if no entries are found.
        """
        total_entries = sum(1 for entry in self.find_all(board, minimum_weight))
        if not total_entries:
            raise IndexError()

        choice = random.randint(0, total_entries - 1)
        return next(itertools.islice(self.find_all(board, minimum_weight), choice, None))

    def weighted_choice(self, board, random=random):
        """
        Selects a random entry for the given position, distrubuted by the
        weights of the entries.

        Raises *IndexError* if no entries are found.
        """
        total_weights = sum(entry.weight for entry in self.find_all(board))
        if not total_weights:
            raise IndexError()

        choice = random.randint(0, total_weights - 1)

        current_sum = 0
        for entry in self.find_all(board):
            current_sum += entry.weight
            if current_sum > choice:
                return entry

        assert False


def open_reader(path):
    """
    Creates a reader for the file at the given path.

    >>> with open_reader("data/opening-books/performance.bin") as reader:
    ...    for entry in reader.find_all(board):
    ...        print(entry.move(), entry.weight, entry.learn)
    e2e4 1 0
    d2d4 1 0
    c2c4 1 0
    """
    return MemoryMappedReader(path)
