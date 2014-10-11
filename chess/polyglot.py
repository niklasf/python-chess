# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
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


ENTRY_STRUCT = struct.Struct(">QHHI")


class Entry(collections.namedtuple("Entry", ["key", "raw_move", "weight", "learn"])):
    """An entry from a polyglot opening book."""

    def move(self):
        """Gets the move (as a `Move` object)."""
        # Extract source and target square.
        to_square = self.raw_move & 0x3f
        from_square = (self.raw_move >> 6) & 0x3f

        # Replace non standard castling moves.
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


class Reader(object):
    """
    A reader for a polyglot opening book opened in binary mode. The file has to
    be seekable.

    Provides methods to seek entries for specific positions but also ways to
    efficiently use the opening book like a list.

    >>> # Get the number of entries
    >>> len(reader)
    92954

    >>> # Get the nth entry
    >>> entry = reader[n]

    >>> # Iteration
    >>> for entry in reader:
    >>>     pass

    >>> # Backwards iteration
    >>> for entry in reversed(reader):
    >>>     pass
    """

    def __init__(self, handle):
        self.handle = handle

        self.seek_entry(0, 2)
        self.__entry_count = int(self.handle.tell() / ENTRY_STRUCT.size)

    def __len__(self):
        return self.__entry_count

    def __getitem__(self, key):
        if key >= self.__entry_count:
            raise IndexError()
        self.seek_entry(key)
        return self.next()

    def __iter__(self):
        self.seek_entry(0)
        return self

    def __reversed__(self):
        for i in xrange(self.__entry_count - 1, -1, -1):
            self.seek_entry(i)
            yield self.next()

    def seek_entry(self, offset, whence=0):
        """
        Seek an entry by its index.

        Translated directly to a low level seek on the binary file. `whence` is
        equivalent."""
        self.handle.seek(offset * ENTRY_STRUCT.size, whence)

    def seek_position(self, position):
        """
        Seek the first entry for the given position.

        Raises `KeyError` if there are no entries for the position.
        """
        # Calculate the position hash.
        key = position.zobrist_hash()

        # Do a binary search.
        start = 0
        end = len(self)
        while end >= start:
            middle = int((start + end) / 2)

            self.seek_entry(middle)
            raw_entry = self.next_raw()

            if raw_entry[0] < key:
                start = middle + 1
            elif raw_entry[0] > key:
                end = middle - 1
            else:
                # Position found. Move back to the first occurence.
                self.seek_entry(-1, 1)
                while raw_entry[0] == key and middle > start:
                    middle -= 1
                    self.seek_entry(middle)
                    raw_entry = self.next_raw()

                    if middle == start and raw_entry[0] == key:
                        self.seek_entry(-1, 1)

                return

        raise KeyError()

    def next_raw(self):
        """
        Reads the next raw entry as a tuple.

        Raises `StopIteration` at the EOF.
        """
        try:
            return ENTRY_STRUCT.unpack(self.handle.read(ENTRY_STRUCT.size))
        except struct.error:
            raise StopIteration()

    def next(self):
        """
        Reads the next `Entry`.

        Raises `StopIteration` at the EOF.
        """
        key, raw_move, weight, learn = self.next_raw()
        return Entry(key, raw_move, weight, learn)

    def get_entries_for_position(self, position):
        """Seeks a specific position and yields all entries."""
        zobrist_hash = position.zobrist_hash()

        # Seek the position. Stop iteration if not entry exists.
        try:
            self.seek_position(position)
        except KeyError:
            raise StopIteration()

        # Iterate.
        entry = self.next()
        while entry.key == zobrist_hash:
            if entry.move() in position.legal_moves:
                yield entry

            entry = self.next()


class ClosableReader(Reader):

    def close(self):
        self.handle.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


def open_reader(path):
    """
    Creates a reader for the file at the given path.

    >>> with open_reader("data/opening-books/performance.bin") as reader:
    >>>    entries = reader.get_entries_for_position(board)
    """
    return ClosableReader(open(path, "rb"))
