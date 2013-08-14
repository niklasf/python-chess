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

class PositionTestCase(unittest.TestCase):
    """Tests the position class."""

    def test_default_position(self):
        """Tests the default position."""
        pos = chess.Position()
        self.assertEqual(pos[chess.Square('b1')], chess.Piece('N'))
        self.assertEqual(pos.fen, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(pos.turn, "w")

    def test_scholars_mate(self):
        """Tests the scholars mate."""
        pos = chess.Position()
        self.assertTrue(pos.has_queenside_castling_right("b"))

        e4 = chess.Move.from_uci('e2e4')
        self.assertTrue(e4 in pos.get_legal_moves())
        pos.make_move(e4)
        self.assertTrue(pos.has_queenside_castling_right("b"))

        e5 = chess.Move.from_uci('e7e5')
        self.assertTrue(e5 in pos.get_legal_moves())
        self.assertFalse(e4 in pos.get_legal_moves())
        pos.make_move(e5)
        self.assertTrue(pos.has_queenside_castling_right("b"))

        Qf3 = chess.Move.from_uci('d1f3')
        self.assertTrue(Qf3 in pos.get_legal_moves())
        pos.make_move(Qf3)
        self.assertTrue(pos.has_queenside_castling_right("b"))

        Nc6 = chess.Move.from_uci('b8c6')
        self.assertTrue(Nc6 in pos.get_legal_moves())
        pos.make_move(Nc6)
        self.assertTrue(pos.has_queenside_castling_right("b"))

        Bc4 = chess.Move.from_uci('f1c4')
        self.assertTrue(Bc4 in pos.get_legal_moves())
        pos.make_move(Bc4)
        self.assertTrue(pos.has_queenside_castling_right("b"))

        Rb8 = chess.Move.from_uci('a8b8')
        self.assertTrue(Rb8 in pos.get_legal_moves())
        pos.make_move(Rb8)
        self.assertFalse(pos.has_queenside_castling_right("b"))

        self.assertFalse(pos.is_check())
        self.assertFalse(pos.is_checkmate())
        self.assertFalse(pos.is_game_over())
        self.assertFalse(pos.is_stalemate())

        Qf7_mate = chess.Move.from_uci('f3f7')
        self.assertTrue(Qf7_mate in pos.get_legal_moves())
        pos.make_move(Qf7_mate)

        self.assertTrue(pos.is_check())
        self.assertTrue(pos.is_checkmate())
        self.assertTrue(pos.is_game_over())
        self.assertFalse(pos.is_stalemate())

        self.assertEqual(pos.fen, "1rbqkbnr/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQk - 0 4")

    def test_move_info(self):
        """Tests move info generation."""
        pos = chess.Position()
        e4 = pos.make_move(chess.Move.from_uci('e2e4'))
        self.assertEqual(e4.san, 'e4')
        self.assertFalse(e4.is_check)
        self.assertFalse(e4.is_checkmate)
        self.assertFalse(e4.is_castle)

    def test_pawn_captures(self):
        """Tests pawn captures in the kings gambit."""
        pos = chess.Position()
        pos.make_move(pos.get_move_from_san("e4"))
        pos.make_move(pos.get_move_from_san("e5"))
        pos.make_move(pos.get_move_from_san("f4"))

        accepted = chess.Position(pos)
        self.assertTrue(chess.Move.from_uci("e5f4") in accepted.get_pseudo_legal_moves())
        self.assertTrue(chess.Move.from_uci("e5f4") in accepted.get_legal_moves())
        accepted.make_move(accepted.get_move_from_san("exf4"))

        wierd_declined = chess.Position(pos)
        wierd_declined.make_move(wierd_declined.get_move_from_san("d5"))
        wierd_declined.make_move(wierd_declined.get_move_from_san("exd5"))


    def test_single_step_pawn_move(self):
        """Tests that single step pawn moves are possible."""
        pos = chess.Position()
        a3 = chess.Move.from_uci('a2a3')
        self.assertTrue(a3 in pos.get_pseudo_legal_moves())
        self.assertTrue(a3 in pos.get_legal_moves())
        pos.make_move(a3)

    def test_pawn_move_generation(self):
        """Tests pawn move generation in a specific position from a
        Kasparov vs. Deep Blue game."""
        pos = chess.Position("8/2R1P3/8/2pp4/2k1r3/P7/8/1K6 w - - 1 55")
        list(pos.get_pseudo_legal_moves())

    def test_get_set(self):
        """Tests the get and set methods."""
        pos = chess.Position()
        self.assertEqual(pos["b1"], chess.Piece("N"))

        del pos["e2"]
        self.assertEqual(pos[chess.Square("e2")], None)

        pos[chess.Square("e4")] = chess.Piece("r")
        self.assertEqual(pos["e4"], chess.Piece("r"))

    def test_ep_file(self):
        pos = chess.Position("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
        self.assertEqual(pos.ep_file, "d")

    def test_san_moves(self):
        """Tests making moves from SANs."""
        pos = chess.Position()

        pos.make_move(pos.get_move_from_san('Nc3'))
        pos.make_move(pos.get_move_from_san('c5'))

        pos.make_move(pos.get_move_from_san('e4'))
        pos.make_move(pos.get_move_from_san('g6'))

        pos.make_move(pos.get_move_from_san('Nge2'))
        pos.make_move(pos.get_move_from_san('Bg7'))

        pos.make_move(pos.get_move_from_san('d3'))
        pos.make_move(pos.get_move_from_san('Bxc3'))

        pos.make_move(pos.get_move_from_san('bxc3'))

        self.assertEqual(pos.fen, 'rnbqk1nr/pp1ppp1p/6p1/2p5/4P3/2PP4/P1P1NPPP/R1BQKB1R b KQkq - 0 5')

    def test_ambigous_rank(self):
        """Tests ambigous rank in SANs."""
        pos = chess.Position("r1bqkb1r/pp1n1ppp/2p1pn2/6N1/3P4/3B4/PPP2PPP/R1BQK1NR w KQkq - 0 7")

        first_rank_move = pos.get_move_from_san("N1f3")
        self.assertEqual(first_rank_move, chess.Move.from_uci("g1f3"))


        fifth_rank_move = pos.get_move_from_san("N5f3")
        self.assertEqual(fifth_rank_move, chess.Move.from_uci("g5f3"))


    def test_insufficient_material(self):
        """Tests material counting."""
        # Starting position.
        pos = chess.Position()
        self.assertFalse(pos.is_insufficient_material())

        # King vs. King + 2 bishops of the same color.
        pos = chess.Position("k1K1B1B1/8/8/8/8/8/8/8 w - - 7 32")
        self.assertTrue(pos.is_insufficient_material())

        # Add a black bishop of the opposite color for the weaker side.
        pos["b8"] = chess.Piece("b")
        self.assertFalse(pos.is_insufficient_material())
