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

import re
import chess

uci_move_regex = re.compile(r"^([a-h][1-8])([a-h][1-8])([rnbq]?)$")

class Move(object):
    """Represents a move.

    :param source:
        The source square.
    :param target:
        The target square.
    :param promotion:
        Optional. If given this indicates which piece a pawn has been
        promoted to: `"r"`, `"n"`, `"b"` or `"q"`.

    Identical moves compare as equal.

    >>> import chess
    >>> e4 = chess.Move(chess.Square("e2"), chess.Square("e4"))
    >>> e4 == chess.Move.from_uci("e2e4")
    True
    """
    def __init__(self, source, target, promotion = None):
        if type(source) is not chess.Square:
            raise TypeError(
                "Expected source to be Square object: %s." % repr(source))
        if type(target) is not chess.Square:
            raise TypeError(
                "Expected target to be Square object: %s." % repr(target))

        if not promotion in ["r", "n", "b", "q", None]:
            raise ValueError(
                "Invalid promotion piece: %s.", repr(promotion))
        if promotion is not None and not target.is_backrank():
            raise ValueError(
                "Promotion move even though target is no backrank square.")

        self.__source = source
        self.__target = target
        self.__promotion = promotion

    @property
    def uci(self):
        """The UCI move string like `"a1a2"` or `"b7b8q"`."""
        if self.__promotion:
            return self.__source.name + self.__target.name + self.__promotion
        else:
            return self.__source.name + self.__target.name

    @property
    def source(self):
        """The source square."""
        return self.__source

    @property
    def target(self):
        """The target square."""
        return self.__target

    @property
    def promotion(self):
        """The promotion type as `None`, `"r"`, `"n"`, `"b"` or `"q"`."""
        return self.__promotion

    def __str__(self):
        return self.uci

    def __repr__(self):
        return "Move.from_uci(%s)" % repr(self.uci)

    def __eq__(self, other):
        return isinstance(other, chess.Move) and self.uci == other.uci

    def __ne__(self, other):
        return self.uci != other.uci

    def __hash__(self):
        return hash(self.uci)

    @classmethod
    def from_uci(cls, move):
        """Creates a move object from an UCI move string.

        :param move: An UCI move string like "a1a2" or "b7b8q".
        """
        match = uci_move_regex.match(move)

        return cls(
            source=chess.Square(match.group(1)),
            target=chess.Square(match.group(2)),
            promotion=match.group(3) or None)
