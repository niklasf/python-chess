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

class PieceTestCase(unittest.TestCase):
    """Tests the Piece class."""

    def test_equality(self):
        """Tests the overriden equality behavior of the Piece class."""
        a = chess.Piece.from_color_and_type("w", "b")
        b = chess.Piece.from_color_and_type("b", "k")
        c = chess.Piece.from_color_and_type("w", "k")
        d = chess.Piece.from_color_and_type("w", "b")

        self.assertEqual(a, d)
        self.assertEqual(d, a)

        self.assertEqual(repr(a), repr(d))

        self.assertNotEqual(a, b)
        self.assertNotEqual(b, c)
        self.assertNotEqual(b, d)
        self.assertNotEqual(a, c)

        self.assertNotEqual(a, None)
        self.assertFalse(a == None)

    def test_simple_properties(self):
        """Tests simple properties."""
        white_knight = chess.Piece('N')

        self.assertEqual(white_knight.color, 'w')
        self.assertEqual(white_knight.full_color, 'white')

        self.assertEqual(white_knight.type, 'n')
        self.assertEqual(white_knight.full_type, 'knight')
