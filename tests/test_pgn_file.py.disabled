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
        return
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

    def test_variations_nags_and_comments(self):
        """Tests reading a PGN with variations, NAGs and comments."""
        pgn = chess.PgnFile.open("data/games/variations-nags-and-comments.pgn")
        game = pgn[0]
        self.assertEqual(game.headers["Result"], "*")
        self.assertEqual(game.start_comment, "Main opening:")
        self.assertEqual(game[0].move, chess.Move.from_uci("e2e4"))
        self.assertEqual(game[0][0].move, chess.Move.from_uci("c7c5"))
        self.assertEqual(game[0][0].comment, "Sicilian")
        self.assertEqual(game[0][1].start_comment, "Scandinavian defense:")
        self.assertEqual(game[0][1].move, chess.Move.from_uci("d7d5"))
        self.assertEqual(game[0][2].move, chess.Move.from_uci("h7h5"))
        self.assertEqual(game[0][2].comment, "is nonesense")
        self.assertEqual(game[0][3].move, chess.Move.from_uci("e7e5"))
        self.assertEqual(game[0][3][0].move, chess.Move.from_uci("d1f3"))
        self.assertTrue(2 in game[0][3][0].nags)
