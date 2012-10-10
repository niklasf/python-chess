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

class Move(object):
    def __init__(self, source, target, promotion = None):
        """Inits a move.

        Args:
            source: Source square.
            target: Target square.
            promotion: The piece type the pawn has been promoted to, if any.
        """
        self._source = source
        self._target = target
        self._promotion = promotion

        if promotion:
            assert target.is_backrank()
            assert promotion in "rnbq"

    def get_uci(self):
        """Gets an UCI move.

        Returns:
            A string like "a1a2" or "b7b8q".
        """
        promotion = ""
        if self._promotion:
            promotion = self._promotion
        return self._source.name + self._target.name + promotion

    def get_source(self):
        """Gets the source square.

        Returns:
            The source square.
        """
        return self._source

    def get_target(self):
        """Gets the target square.

        Returns:
            The target square.
        """
        return self._target

    def get_promotion(self):
        """Gets the promotion type.

        Returns:
            None, "r", "n", "b" or "q".
        """
        if not self._promotion:
            return None
        else:
            return self._promotion

    def __str__(self):
        return self.get_uci()

    def __repr__(self):
        return "Move.from_uci('%s')" % self.get_uci()

    def __eq__(self, other):
        return self.get_uci() == other.get_uci()

    def __ne__(self, other):
        return self.get_uci() != other.get_uci()

    def __hash__(self):
        return hash(self.get_uci())

    @classmethod
    def from_uci(cls, move):
        """Parses an UCI move like "a1a2" or "b7b8q

        Returns:
            A new move object.
        """
        uci_move_regex = re.compile("^([a-h][1-8])([a-h][1-8])([rnbq]?)$")
        match = uci_move_regex.match(move)
        return cls(chess.Square(match.group(1)), chess.Square(match.group(2)), match.group(3))
