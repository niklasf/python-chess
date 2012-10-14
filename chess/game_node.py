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

class GameNode(object):
    """A node in the tree of a game.

    :param previous_node:
        The parent node.
    :param move:
        The move that leads to the position of this node.
    :param nags:
        A list of numeric annotation glyphs. Defaults to no annotation
        glyphs.
    :param comment:
        The comment that goes along with the move. Defaults to no
        comment.
    :param start_comment:
        The first node of a variation can have a start comment.
        Defaults to no start comment.
    """
    def __init__(self, previous_node, move, nags=[], comment="",
                 start_comment=""):
        self.__previous_node = previous_node
        self.__move = move

        if move:
            self.__position = previous_node.position.make_move(move)

        self.__nags = nags
        self.comment = comment
        self.start_comment = start_comment

        self.__variations = []

    @property
    def previous_node(self):
        """The previous node of the game."""
        return self.__previous_node

    @property
    def move(self):
        """The move that makes the position of this node from the
        previous node.
        """
        return self.__move

    @property
    def position(self):
        """A copy of the position."""
        return self.__position.copy()

    @property
    def comment(self):
        """The comment. An empty string means no comment."""
        return self.__comment

    @comment.setter
    def comment(self, value):
        if type(value) is not types.StringType:
            raise TypeError(
                "Expected comment to be string, got: %s." % comment)
        self.__comment = value

    @property
    def start_comment(self):
        """The start comment of the variation.

        If the node is not the start of a variation it can not have a
        start comment.
        An empty string means no comment.
        """
        if self.can_have_start_comment():
            return self.__start_comment
        else:
            return ""

    @start_comment.setter
    def start_comment(self, value):
        if type(value) is not types.StringType:
            raise TypeError(
                "Expected start comment to be string, got: %s." % comment)

        if value != "" and not self.can_have_start_comment():
            raise ValueError("Game node can not have a start comment.")

        self.__start_comment = value

    @property
    def nags(self):
        """A list of numeric annotation glyphs."""
        return self.__nags
