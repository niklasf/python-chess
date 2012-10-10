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

class Piece(object):
    """Represents a chess piece.

    :param symbol:
        The symbol of the piece as used in `FENs <http://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation#Definition>`_.


    Piece objects that have the same type and color compare as equal.

    >>> import chess
    >>> chess.Piece("Q") == chess.Piece.from_color_and_type("w", "q")
    True
    """
    def __init__(self, symbol):
        if not symbol.lower() in ["p", "b", "n", "r", "k", "q"]:
            raise ValueError("Invalid piece symbol: %s." % repr(symbol))
        self.__symbol = symbol

    @property
    def color(self):
        """The color of the piece as `"b"` or `"w"`."""
        return "b" if self.__symbol.lower() == self.__symbol else "w"

    @property
    def full_color(self):
        """The full color of the piece as `"black"` or `"white`."""
        return "black" if self.__symbol.lower() == self.__symbol else "white"

    @property
    def type(self):
        """The type of the piece as `"p"`, `"b"`, `"n"`, `"r"`, `"k"`,
        or `"q"` for pawn, bishop, knight, rook, king or queen.
        """
        return self.__symbol.lower()

    @property
    def full_type(self):
        """The full type of the piece as `"pawn"`, `"bishop"`,
        `"knight"`, `"rook"`, `"king"` or `"queen"`.
        """
        type = self.type
        if type == "p":
            return "pawn"
        elif type == "b":
            return "bishop"
        elif type == "n":
            return "knight"
        elif type == "r":
            return "rook"
        elif type == "k":
            return "king"
        elif type == "q":
            return "queen"

    @property
    def symbol(self):
        "The symbol of the piece as used in `FENs <http://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation#Definition>`_."""
        return self.__symbol

    def __str__(self):
        return self.symbol

    def __repr__(self):
        return "Piece('%s')" % self.symbol

    def __eq__(self, other):
        if not other:
            return True
        return self.symbol == other.symbol

    def __ne__(self, other):
        if not other:
            return True
        return self.symbol != other.symbol

    def __hash__(self):
        return ord(self.symbol)

    @classmethod
    def from_color_and_type(cls, color, type):
        """Creates a piece object from color and type.

        An alternate way of creating pieces is from color and type.

        :param color:
            `"w"`, `"b"`, `"white"` or `"black"`.
        :param type:
            `"p"`, `"pawn"`, `"r"`, `"rook"`, `"n"`, `"knight"`, `"b"`,
            `"bishop"`, `"q"`, `"queen"`, `"k"` or `"king"`.

        >>> chess.Piece.from_color_and_type("w", "pawn")
        Piece('P')
        >>> chess.Piece.from_color_and_type("black", "q")
        Piece('q')
        """
        if type in ["p", "pawn"]:
            symbol = "p"
        elif type in ["r", "rook"]:
            symbol = "r"
        elif type in ["n", "knight"]:
            symbol = "n"
        elif type in ["b", "bishop"]:
            symbol = "b"
        elif type in ["q", "queen"]:
            symbol = "q"
        elif type in ["k", "king"]:
            symbol = "k"
        else:
            raise ValueError("Invalid piece type: %s." % repr(type))

        if color in ["w", "white"]:
            return cls(symbol.upper())
        elif color in ["b", "black"]:
            return cls(symbol)
        else:
            raise ValueError("Invalid piece color: %s." % repr(color))
