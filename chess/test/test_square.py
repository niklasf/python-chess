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

class SquareTestCase(unittest.TestCase):
    """Tests the Square class."""

    def test_equality(self):
        """Tests the overriden equality behaviour of the Square class."""
        a = chess.Square("b4")
        b = chess.Square("b4")
        c = chess.Square("b3")
        d = chess.Square("f3")

        self.assertEqual(a, b)
        self.assertEqual(b, a)

        self.assertNotEqual(a, c)
        self.assertNotEqual(a, d)
        self.assertNotEqual(c, d)

    def test_simple_properties(self):
        """Tests simple properties of Square objects."""
        f7 = chess.Square("f7")
        self.assertFalse(f7.is_dark())
        self.assertTrue(f7.is_light())
        self.assertEqual(f7.get_rank(), 7)
        self.assertEqual(f7.get_file(), 'f')
        self.assertEqual(f7.get_name(), 'f7')
        self.assertEqual(f7.get_0x88_index(), 21)
        self.assertEqual(f7.get_x(), 5)
        self.assertEqual(f7.get_y(), 6)
        self.assertFalse(f7.is_backrank())

    def test_creation(self):
        """Tests creation of Square instances."""
        self.assertEqual(chess.Square.from_x_and_y(3, 5), chess.Square("d6"))
        self.assertEqual(chess.Square.from_0x88_index(2), chess.Square("c8"))
        self.assertEqual(chess.Square.from_rank_and_file(rank=2, file="g"), chess.Square("g2"))

    def test_iteration(self):
        """Tests iteration over all squares."""
        self.assertTrue(chess.Square("h8") in chess.Square.get_all())
        self.assertTrue(chess.Square("b1") in chess.Square.get_all())
