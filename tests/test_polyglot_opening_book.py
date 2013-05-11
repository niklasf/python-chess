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

class PolyglotOpeningBookTestCase(unittest.TestCase):

    def test_performance_bin(self):
        pos = chess.Position()
        book = chess.PolyglotOpeningBook("data/opening-books/performance.bin")

        e4 = book.get_entries_for_position(pos).next()
        self.assertEqual(e4.move, pos.get_move_from_san("e4"))
        pos.make_move(e4.move)

        e5 = book.get_entries_for_position(pos).next()
        self.assertEqual(e5.move, pos.get_move_from_san("e5"))
        pos.make_move(e5.move)

    def test_mainline(self):
        pos = chess.Position()
        book = chess.PolyglotOpeningBook("data/opening-books/performance.bin")

        while True:
            try:
                entry = book.get_entries_for_position(pos).next()
                pos.make_move(entry.move)
            except StopIteration:
                break
