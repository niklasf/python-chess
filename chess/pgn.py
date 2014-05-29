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
import io
import sys
import collections


def scan_offsets(handle):
    """
    Scan a PGN file opened in text mode.

    Yields the starting offsets of all the games, so that they can be seeked
    later.
    """
    in_comment = False

    last_pos = handle.tell()
    line = handle.readline()

    while line:
        if not in_comment and line.startswith("[Event \""):
            yield last_pos
        elif (not in_comment and "{" in line) or (in_comment and "}" in line):
            if line.rfind("{") < line.rfind("}"):
                in_comment = False
            else:
                in_comment = True

        last_pos = handle.tell()
        line = handle.readline()


class GameNode(object):

    def __init__(self):
        self.parent = None
        """The parent node in the game."""

        self.move = None
        """The move that leads to the node."""

        self.san = None
        """The SAN representation of the move that leads to the node."""

        self.starting_comment = ""
        """Comment before the variation started by this node."""

        self.comment = ""
        """Commend after this node."""

        self.variations = collections.OrderedDict()
        """Ordered dictionary mapping moves to child nodes."""

    def board(self):
        """Gets the position of the node."""
        board = self.parent.board()
        board.push(self.move)
        return board

    def root(self):
        """Gets the root node."""
        node = self

        while node.parent:
            node = node.parent

        return node

    def starts_variation(self):
        """
        Checks if this node starts a variation (and can thus have a starting
        comment).
        """
        if not self.parent:
            return True

        # Checks that this is not the first variation.
        for variation in self.parent.variations.values():
            if variation == self:
                return False
            break

        return True

    def is_main_line(self):
        """Checks if the node is in the main line of the game."""
        node = self

        while node.parent:
            parent = node.parent

            for variation in parent.variations.values():
                if variation != self:
                    return False
                break

            node = parent

        return True

    def is_main_variation(self):
        """
        Checks if this node is the first variation from the point of view of its
        parent. The root node also is in the main variation.
        """
        if not self.parent:
            return True

        for variation in self.parent.variation.values():
            if variation == self:
                return True
            break

        return False

    def variation(self, move):
        """
        Gets a child node by move or index.
        """
        try:
            return self.variations[move]
        except KeyError:
            # Try using move as an integer index.
            # TODO: Avoid creating a list.
            return list(self.variations.values())[move]

    def has_variation(self, move):
        """Checks if the given move appears as a variation."""
        return move in self.variations

    def promote_to_main(self, move):
        """Promotes the given move to the main variation."""
        self.variations.move_to_end(move, False)

    def remove_variation(self, move):
        """Removes a variation by move."""
        del self.variations[move]

    def add_variation(self, move, comment="", starting_comment=""):
        node = GameNode()
        node.move = move
        node.san = self.board().san(move)
        node.parent = self
        node.comment = comment
        node.starting_comment = starting_comment
        self.variations[move] = node
        return node

    def add_main_variation(self, move, comment=""):
        node = self.add_variation(move, comment=comment)
        self.promote_to_main(move)
        return node


class Game(GameNode):

    def __init__(self):
        super(Game, self).__init__()

        self.headers = collections.OrderedDict()
        self.headers["Event"] = "?"
        self.headers["Site"] = "?"
        self.headers["Date"] = "????.??.??"
        self.headers["Round"] = "?"
        self.headers["White"] = "?"
        self.headers["Black"] = "?"
        self.headers["Result"] = "1/2-1/2"

    def board(self):
        return chess.Bitboard()
