#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import chess
import chess.polyglot
import unittest


class MoveTestCase(unittest.TestCase):

    def test_equality(self):
        a = chess.Move(chess.A1, chess.A2)
        b = chess.Move(chess.A1, chess.A2)
        c = chess.Move(chess.H7, chess.H8, chess.BISHOP)
        d = chess.Move(chess.H7, chess.H8)

        self.assertEqual(a, b)
        self.assertEqual(b, a)

        self.assertNotEqual(a, c)
        self.assertNotEqual(c, d)
        self.assertNotEqual(b, d)

    def test_uci_parsing(self):
        self.assertEqual(chess.Move.from_uci("b5c7").uci(), "b5c7")
        self.assertEqual(chess.Move.from_uci("e7e8q").uci(), "e7e8q")


class PieceTestCase(unittest.TestCase):

    def test_equality(self):
        a = chess.Piece(chess.WHITE, chess.BISHOP)
        b = chess.Piece(chess.BLACK, chess.KING)
        c = chess.Piece(chess.WHITE, chess.KING)
        d = chess.Piece(chess.WHITE, chess.BISHOP)

        self.assertEqual(a, d)
        self.assertEqual(d, a)

        self.assertEqual(repr(a), repr(d))

        self.assertNotEqual(a, b)
        self.assertNotEqual(b, c)
        self.assertNotEqual(b, d)
        self.assertNotEqual(a, c)

    def test_from_symbol(self):
        white_knight = chess.Piece.from_symbol("N")

        self.assertEqual(white_knight.color, chess.WHITE)
        self.assertEqual(white_knight.piece_type, chess.KNIGHT)
        self.assertEqual(white_knight.symbol(), "N")

        black_queen = chess.Piece.from_symbol("q")

        self.assertEqual(black_queen.color, chess.BLACK)
        self.assertEqual(black_queen.piece_type, chess.QUEEN)
        self.assertEqual(black_queen.symbol(), "q")


class BitboardTestCase(unittest.TestCase):

    def test_default_position(self):
        bitboard = chess.Bitboard()
        self.assertEqual(bitboard.piece_at(chess.B1), chess.Piece.from_symbol("N"))
        self.assertEqual(bitboard.fen(), chess.STARTING_FEN)
        self.assertEqual(bitboard.turn, chess.WHITE)

    def test_move_making(self):
        bitboard = chess.Bitboard()
        bitboard.push(chess.Move(chess.E2, chess.E4))

    def test_fen(self):
        bitboard = chess.Bitboard()
        self.assertEqual(bitboard.fen(), chess.STARTING_FEN)

        fen = "6k1/pb3pp1/1p2p2p/1Bn1P3/8/5N2/PP1q1PPP/6K1 w - - 0 24"
        bitboard.set_fen(fen)
        self.assertEqual(bitboard.fen(), fen)

        bitboard.push(chess.Move.from_uci("f3d2"))
        self.assertEqual(bitboard.fen(), "6k1/pb3pp1/1p2p2p/1Bn1P3/8/8/PP1N1PPP/6K1 b - - 0 24")

    def test_get_set(self):
        bitboard = chess.Bitboard()
        self.assertEqual(bitboard.piece_at(chess.B1), chess.Piece.from_symbol("N"))

        bitboard.remove_piece_at(chess.E2)
        self.assertEqual(bitboard.piece_at(chess.E2), None)

        bitboard.set_piece_at(chess.E4, chess.Piece.from_symbol("r"))
        self.assertEqual(bitboard.piece_type_at(chess.E4), chess.ROOK)

    def test_pawn_captures(self):
        bitboard = chess.Bitboard()

        # Kings gambit.
        bitboard.push(chess.Move.from_uci("e2e4"))
        bitboard.push(chess.Move.from_uci("e7e5"))
        bitboard.push(chess.Move.from_uci("f2f4"))

        # Accepted.
        exf4 = chess.Move.from_uci("e5f4")
        self.assertTrue(exf4 in bitboard.pseudo_legal_moves)
        self.assertTrue(exf4 in bitboard.legal_moves)
        bitboard.push(exf4)
        bitboard.pop()

    def test_pawn_move_generation(self):
        bitboard = chess.Bitboard("8/2R1P3/8/2pp4/2k1r3/P7/8/1K6 w - - 1 55")
        self.assertEqual(len(list(bitboard.generate_pseudo_legal_moves())), 16)

    def test_single_step_pawn_move(self):
        bitboard = chess.Bitboard()
        a3 = chess.Move.from_uci("a2a3")
        self.assertTrue(a3 in bitboard.pseudo_legal_moves)
        self.assertTrue(a3 in bitboard.legal_moves)
        bitboard.push(a3)
        bitboard.pop()
        self.assertEqual(bitboard.fen(), chess.STARTING_FEN)

    def test_castling(self):
        bitboard = chess.Bitboard("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

        # Let white castle short.
        move = bitboard.parse_san("O-O")
        self.assertTrue(move in bitboard.legal_moves)
        bitboard.push(move)

        # Let black castle long.
        move = bitboard.parse_san("O-O-O")
        self.assertTrue(move in bitboard.legal_moves)
        bitboard.push(move)
        self.assertEqual(bitboard.fen(), "2kr3r/8/8/8/8/8/8/R4RK1 w - - 3 2")

        # Undo both castling moves.
        bitboard.pop()
        bitboard.pop()
        self.assertEqual(bitboard.fen(), "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

        # Let white castle long.
        move = bitboard.parse_san("O-O-O")
        self.assertTrue(move in bitboard.legal_moves)
        bitboard.push(move)

        # Let black castle short.
        move = bitboard.parse_san("O-O")
        self.assertTrue(move in bitboard.legal_moves)
        bitboard.push(move)
        self.assertEqual(bitboard.fen(), "r4rk1/8/8/8/8/8/8/2KR3R w - - 3 2")

        # Undo both castling moves.
        bitboard.pop()
        bitboard.pop()
        self.assertEqual(bitboard.fen(), "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

    def test_insufficient_material(self):
        # Starting position.
        bitboard = chess.Bitboard()
        self.assertFalse(bitboard.is_insufficient_material())

        # King vs. King + 2 bishops of the same color.
        bitboard = chess.Bitboard("k1K1B1B1/8/8/8/8/8/8/8 w - - 7 32")
        self.assertTrue(bitboard.is_insufficient_material())

        # Add bishop of opposite color for the weaker side.
        bitboard.set_piece_at(chess.B8, chess.Piece.from_symbol("b"))
        self.assertFalse(bitboard.is_insufficient_material())

    def test_promotion_with_check(self):
        bitboard = chess.Bitboard("8/6P1/2p5/1Pqk4/6P1/2P1RKP1/4P1P1/8 w - - 0 1")
        bitboard.push(chess.Move.from_uci("g7g8q"))
        self.assertTrue(bitboard.is_check())
        self.assertEqual(bitboard.fen(), "6Q1/8/2p5/1Pqk4/6P1/2P1RKP1/4P1P1/8 b - - 0 1")

    def test_scholars_mate(self):
        bitboard = chess.Bitboard()

        e4 = chess.Move.from_uci("e2e4")
        self.assertTrue(e4 in bitboard.legal_moves)
        bitboard.push(e4)

        e5 = chess.Move.from_uci("e7e5")
        self.assertTrue(e5 in bitboard.legal_moves)
        bitboard.push(e5)

        Qf3 = chess.Move.from_uci("d1f3")
        self.assertTrue(Qf3 in bitboard.legal_moves)
        bitboard.push(Qf3)

        Nc6 = chess.Move.from_uci("b8c6")
        self.assertTrue(Nc6 in bitboard.legal_moves)
        bitboard.push(Nc6)

        Bc4 = chess.Move.from_uci("f1c4")
        self.assertTrue(Bc4 in bitboard.legal_moves)
        bitboard.push(Bc4)

        Rb8 = chess.Move.from_uci("a8b8")
        self.assertTrue(Rb8 in bitboard.legal_moves)
        bitboard.push(Rb8)

        self.assertFalse(bitboard.is_check())
        self.assertFalse(bitboard.is_checkmate())
        self.assertFalse(bitboard.is_game_over())
        self.assertFalse(bitboard.is_stalemate())

        Qf7_mate = chess.Move.from_uci("f3f7")
        self.assertTrue(Qf7_mate in bitboard.legal_moves)
        bitboard.push(Qf7_mate)

        self.assertTrue(bitboard.is_check())
        self.assertTrue(bitboard.is_checkmate())
        self.assertTrue(bitboard.is_game_over())
        self.assertFalse(bitboard.is_stalemate())

        self.assertEqual(bitboard.fen(), "1rbqkbnr/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQk - 0 4")

    def test_san(self):
        # En passant mate.
        fen = "6bk/7b/8/3pP3/8/8/8/Q3K3 w - d6 0 2"
        bitboard = chess.Bitboard(fen)
        fxe6_mate_ep = chess.Move.from_uci("e5d6")
        self.assertEqual(bitboard.san(fxe6_mate_ep), "exd6#")
        self.assertEqual(bitboard.fen(), fen)

        # Test ambiguation.
        fen = "N3k2N/8/8/3N4/N4N1N/2R5/1R6/4K3 w - - 0 1"
        bitboard = chess.Bitboard(fen)
        self.assertEqual(bitboard.san(chess.Move.from_uci("e1f1")), "Kf1")
        self.assertEqual(bitboard.san(chess.Move.from_uci("c3c2")), "Rcc2")
        self.assertEqual(bitboard.san(chess.Move.from_uci("b2c2")), "Rbc2")
        self.assertEqual(bitboard.san(chess.Move.from_uci("a4b6")), "N4b6")
        self.assertEqual(bitboard.san(chess.Move.from_uci("h8g6")), "N8g6")
        self.assertEqual(bitboard.san(chess.Move.from_uci("h4g6")), "Nh4g6")
        self.assertEqual(bitboard.fen(), fen)

        # Do not disambiguate illegal alternatives.
        fen = "8/8/8/R2nkn2/8/8/2K5/8 b - - 0 1"
        bitboard = chess.Bitboard(fen)
        self.assertEqual(bitboard.san(chess.Move.from_uci("f5e3")), "Ne3+")
        self.assertEqual(bitboard.fen(), fen)

    def test_is_legal_move(self):
        fen = "3k4/6P1/7P/8/K7/8/8/4R3 w - - 0 1"
        bitboard = chess.Bitboard(fen)

        # Legal moves: Rg1, g8=R+.
        self.assertTrue(chess.Move.from_uci("e1g1") in bitboard.legal_moves)
        self.assertTrue(chess.Move.from_uci("g7g8r") in bitboard.legal_moves)

        # Impossible promotion: Kb5, h7.
        self.assertFalse(chess.Move.from_uci("a5b5q") in bitboard.legal_moves)
        self.assertFalse(chess.Move.from_uci("h6h7n") in bitboard.legal_moves)

        # Missing promotion.
        self.assertFalse(chess.Move.from_uci("g7g8") in bitboard.legal_moves)

        self.assertEqual(bitboard.fen(), fen)

    def test_polyglot(self):
        # Test polyglot compability using test data from
        # http://hardy.uhasselt.be/Toga/book_format.html. Forfeiting castling
        # rights should not reset the half move counter, though.

        board = chess.Bitboard()
        self.assertEqual(board.fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(board.__hash__(), 0x463b96181691fc9c)

        board.push_san("e4")
        self.assertEqual(board.fen(), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        self.assertEqual(board.__hash__(), 0x823c9b50fd114196)

        board.push_san("d5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
        self.assertEqual(board.__hash__(), 0x0756b94461c50fb0)

        board.push_san("e5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
        self.assertEqual(board.__hash__(), 0x662fafb965db29d4)

        board.push_san("f5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3")
        self.assertEqual(board.__hash__(), 0x22a48b5a8e47ff78)

        board.push_san("Ke2")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR b kq - 1 3")
        self.assertEqual(board.__hash__(), 0x652a607ca3f242c1)

        board.push_san("Kf7")
        self.assertEqual(board.fen(), "rnbq1bnr/ppp1pkpp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR w - - 2 4")
        self.assertEqual(board.__hash__(), 0x00fdd303c946bdd9)

        board = chess.Bitboard()
        board.push_san("a4")
        board.push_san("b5")
        board.push_san("h4")
        board.push_san("b4")
        board.push_san("c4")
        self.assertEqual(board.fen(), "rnbqkbnr/p1pppppp/8/8/PpP4P/8/1P1PPPP1/RNBQKBNR b KQkq c3 0 3")
        self.assertEqual(board.__hash__(), 0x3c8123ea7b067637)

        board.push_san("bxc3")
        board.push_san("Ra3")
        self.assertEqual(board.fen(), "rnbqkbnr/p1pppppp/8/8/P6P/R1p5/1P1PPPP1/1NBQKBNR b Kkq - 1 4")
        self.assertEqual(board.__hash__(), 0x5c3f9b829b279560)


class LegalMoveGeneratorTestCase(unittest.TestCase):

    def test_list_conversion(self):
        list(chess.LegalMoveGenerator(chess.Bitboard()))


class PolyglotReader(unittest.TestCase):

    def test_performance_bin(self):
        pos = chess.Bitboard()
        book = chess.polyglot.open_reader("data/opening-books/performance.bin")

        e4 = book.get_entries_for_position(pos).next()
        self.assertEqual(e4.move(), pos.parse_san("e4"))
        pos.push(e4.move())

        e5 = book.get_entries_for_position(pos).next()
        self.assertEqual(e5.move(), pos.parse_san("e5"))
        pos.push(e5.move())

    def test_mainline(self):
        board = chess.Bitboard()
        book = chess.polyglot.open_reader("data/opening-books/performance.bin")

        while True:
            try:
                entry = book.get_entries_for_position(board).next()
                board.push(entry.move())
            except StopIteration:
                break

        self.assertEqual(board.fen(), "r2q1rk1/4bppp/p2p1n2/np5b/3BP1P1/5N1P/PPB2P2/RN1QR1K1 b - g3 0 15")


if __name__ == "__main__":
    unittest.main()
