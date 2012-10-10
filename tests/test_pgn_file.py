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

class PgnFileTestCase(unittest.TestCase):
    def test(self):
        games = chess.PgnFile.open('data/games/kasparov-deep-blue-1997.pgn')
        self.assertEqual(len(games), 6)

        first_game = games[0]
        self.assertEqual(first_game.get_header("Event"), "IBM Man-Machine, New York USA")
        self.assertEqual(first_game.get_header("Site"), "01")
        self.assertEqual(first_game.get_header("Date"), "1997.??.??")
        self.assertEqual(first_game.get_header("EventDate"), "?")
        self.assertEqual(first_game.get_header("Round"), "?")
        self.assertEqual(first_game.get_header("Result"), "1-0")
        self.assertEqual(first_game.get_header("White"), "Garry Kasparov")
        self.assertEqual(first_game.get_header("Black"), "Deep Blue (Computer)")
        self.assertEqual(first_game.get_header("ECO"), "A06")
