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

class GameHeaderBagTestCase(unittest.TestCase):
    """Tests for the GameHeaderBag class."""

    def test_contains(self):
        """Tests checking if a key is in the bag."""
        bag = chess.GameHeaderBag() 
        self.assertTrue("Site" in bag)
        self.assertTrue("Round" in bag)
        self.assertFalse("PlyCount" in bag)
        self.assertFalse("FEN" in bag)
        self.assertFalse("SetUp" in bag)

        bag["FEN"] = chess.START_FEN
        self.assertFalse("FEN" in bag)

        bag["FEN"] = "8/8/8/1kr5/4KR2/5N2/8/8 w - - 0 1"
        self.assertTrue("FEN" in bag)
        self.assertTrue("SetUp" in bag)

        bag["UnknownHeader"] = "foo"
        self.assertTrue("UnknownHeader" in bag)
        self.assertFalse("OtherHeader" in bag)

    def test_iterating(self):
        """Tests iterating over a bag."""
        bag = chess.GameHeaderBag()
        bag["Lorem"] = "Ipsum"
        bag["Annotator"] = "Awesome annotator"

        order = []
        for key in bag:
            order.append(key)

        self.assertEqual(order[0], "Event")
        self.assertEqual(order[6], "Result")
        self.assertEqual(order[7], "Annotator")
        self.assertEqual(order[8], "Lorem")
