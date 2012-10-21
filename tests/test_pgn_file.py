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
        self.assertEqual(first_game.headers["Event"], "IBM Man-Machine, New York USA")
        self.assertEqual(first_game.headers["Site"], "01")
        self.assertEqual(first_game.headers["Date"], "1997.??.??")
        self.assertEqual(first_game.headers["EventDate"], "?")
        self.assertEqual(first_game.headers["Round"], "?")
        self.assertEqual(first_game.headers["Result"], "1-0")
        self.assertEqual(first_game.headers["White"], "Garry Kasparov")
        self.assertEqual(first_game.headers["Black"], "Deep Blue (Computer)")
        self.assertEqual(first_game.headers["ECO"], "A06")

        self.assertEqual(first_game[0].move, first_game.position.get_move_from_san("Nf3"))
