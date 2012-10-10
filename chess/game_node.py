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

class GameNode(object):
    def __init__(self, previous_node, move, nags=[], comment=""):
        self._previous_node = previous_node
        self._move = move

        if previous_node and previous_node.get_position():
            self._position = previous_node.get_position().copy()
            self._position.make_move(self._move)

        self._nags = nags
        self._comment = comment
        self._variations = []

    def get_move(self):
        return self._move

    def get_position(self):
        return self._position.copy()

    def get_nags(self):
        return tuple(self._nags)

    def add_nag(self, nag):
        if not nag in self._nags:
            self._nags.append(nag)

    def remove_nag(self, nag):
        self._nags.remove(nag)

    def get_comment(self):
        return self._comment

    def set_comment(self, comment):
        self._comment = comment

    def get_variations(self):
        return tuple(self._variations)

    def add_variation(self, node):
        if not node in self._variations:
            self._variations.append(node)

    def add_main_variation(self, node):
        if node in self._variations:
            self._variations.remove(node)
        self._variations.insert(0, node)

    def remove_variation(self, node):
        self._variations.remove(node)
