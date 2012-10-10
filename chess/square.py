# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import types

class Square(object):
    """Represents a square on the chess board.

    :param name: The name of the square in algebraic notation.

    Square objects that represent the same square compare as equal.

    >>> import chess
    >>> chess.Square("e4") == chess.Square("e4")
    True
    """
    def __init__(self, name):
        if type(name) is not types.StringType:
            raise TypeError(
                "Expected the square name as a string: %s." % repr(name))
        if not len(name) == 2:
            raise ValueError(
                "Invalid length for a square name: %s." % repr(name))
        if not name[0] in ["a", "b", "c", "d", "e", "f", "g", "h"]:
            raise ValueError(
                "File: Expected a, b, c, e, e, f, g or h: %s." % repr(name[0]))
        if not name[1] in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            raise ValueError(
                "Rank: Expected 1, 2, 3, 4, 5, 6, 7 or 8: %s." % repr(name[1]))

        self.__name = name

    @property
    def x(self):
        """The x-coordinate, starting with 0 for the a-file."""
        return ord(self.__name[0]) - ord("a")

    @property
    def y(self):
        """The y-coordinate, starting with 0 for the first rank."""
        return ord(self.__name[1]) - ord("1")

    @property
    def rank(self):
        """The rank as an integer between 1 and 8."""
        return self.y + 1

    @property
    def file(self):
        """The file as a letter between `"a"` and `"h"`."""
        return self.__name[0]

    @property
    def name(self):
        """The algebraic name of the square."""
        return self.__name

    @property
    def x88(self):
        """The `x88 <http://en.wikipedia.org/wiki/Board_representation_(chess)#0x88_method>`_
        index of the square."""
        return self.x + 16 * (7 - self.y)

    def is_dark(self):
        """:return: Whether it is a dark square."""
        return (ord(self.__name[0]) - ord(self.__name[1])) % 2 == 0

    def is_light(self):
        """:return: Whether it is a light square."""
        return not self.is_dark()

    def is_backrank(self):
        """:return: Whether the square is on either sides backrank."""
        return self.__name[1] in ["1", "8"]

    def __str__(self):
        return self.__name

    def __repr__(self):
        return "Square('%s')" % self.__name

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return self.name != other.name

    def __hash__(self):
        return self.x88

    @classmethod
    def from_x88(cls, x88):
        """Creates a square object from an `x88 <http://en.wikipedia.org/wiki/Board_representation_(chess)#0x88_method>`_
        index.

        :param x88:
            The x88 index as integer between 0 and 128.
        """
        if type(x88) is not types.IntType:
            raise TypeError(
                "Expected the x88 index as an integer: %s." % repr(x88))
        if x88 < 0 or x88 > 128:
            raise ValueError("x88 index is out of range: %s." % repr(x88))
        if x88 & 0x88:
            raise ValueError(
                "x88 index is on the second board: %s." % repr(x88))

        return cls("abcdefgh"[x88 & 7] + "87654321"[x88 >> 4])

    @classmethod
    def from_rank_and_file(cls, rank, file):
        """Creates a square object from rank and file.

        :param rank:
            An integer between 1 and 8.
        :param file:
            The rank as a letter between `"a"` and `"h"`.
        """
        if type(rank) is not types.IntType:
            raise TypeError("Expected rank to be an integer: %s." % repr(rank))
        if rank < 1 or rank > 8:
            raise ValueError(
                "Expected rank to be between 1 and 8: %s." % repr(rank))
        if not file in ["a", "b", "c", "d", "e", "f", "g", "h"]:
            raise ValueError(
                "Expected the file to be a letter between 'a' and 'h': %s."
                    % repr(file))

        return cls(file + str(rank))

    @classmethod
    def from_x_and_y(cls, x, y):
        """Creates a square object from x and y coordinates.

        :param x:
            An integer between 0 and 7 where 0 is the a-file.
        :param y:
            An integer between 0 and 7 where 0 is the first rank.
        """
        return cls("abcdefgh"[x] + "12345678"[y])

    @classmethod
    def get_all(cls):
        """:yield: All squares."""
        for x in range(0, 8):
            for y in range(0, 8):
                yield cls.from_x_and_y(x, y)
