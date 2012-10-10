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

import chess
import unittest

class MoveTestCase(unittest.TestCase):
    """Tests the Move class."""

    def test_equality(self):
        """Tests the custom equality behaviour of the move class."""
        a = chess.Move(chess.Square("a1"), chess.Square("a2"))
        b = chess.Move(chess.Square("a1"), chess.Square("a2"))
        c = chess.Move(chess.Square("h7"), chess.Square("h8"), "b")
        d = chess.Move(chess.Square("h7"), chess.Square("h8"))

        self.assertEqual(a, b)
        self.assertEqual(b, a)

        self.assertNotEqual(a, c)
        self.assertNotEqual(c, d)
        self.assertNotEqual(b, d)

    def test_uci_parsing(self):
        """Tests the UCI move parsing."""
        self.assertEqual(chess.Move.from_uci('b5c7').uci, 'b5c7')
        self.assertEqual(chess.Move.from_uci('e7e8q').uci, 'e7e8q')
