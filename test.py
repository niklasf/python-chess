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
import chess.pgn
import chess.uci
import chess.syzygy
import collections
import os.path
import textwrap
import time
import unittest

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class MoveTestCase(unittest.TestCase):

    def test_equality(self):
        a = chess.Move(chess.A1, chess.A2)
        b = chess.Move(chess.A1, chess.A2)
        c = chess.Move(chess.H7, chess.H8, chess.BISHOP)
        d1 = chess.Move(chess.H7, chess.H8)
        d2 = chess.Move(chess.H7, chess.H8)

        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertEqual(d1, d2)

        self.assertNotEqual(a, c)
        self.assertNotEqual(c, d1)
        self.assertNotEqual(b, d1)
        self.assertFalse(d1 != d2)

    def test_uci_parsing(self):
        self.assertEqual(chess.Move.from_uci("b5c7").uci(), "b5c7")
        self.assertEqual(chess.Move.from_uci("e7e8q").uci(), "e7e8q")


class PieceTestCase(unittest.TestCase):

    def test_equality(self):
        a = chess.Piece(chess.BISHOP, chess.WHITE)
        b = chess.Piece(chess.KING, chess.BLACK)
        c = chess.Piece(chess.KING, chess.WHITE)
        d1 = chess.Piece(chess.BISHOP, chess.WHITE)
        d2 = chess.Piece(chess.BISHOP, chess.WHITE)

        self.assertEqual(a, d1)
        self.assertEqual(d1, a)
        self.assertEqual(d1, d2)

        self.assertEqual(repr(a), repr(d1))

        self.assertNotEqual(a, b)
        self.assertNotEqual(b, c)
        self.assertNotEqual(b, d1)
        self.assertNotEqual(a, c)
        self.assertFalse(d1 != d2)

        self.assertNotEqual(repr(a), repr(b))
        self.assertNotEqual(repr(b), repr(c))
        self.assertNotEqual(repr(b), repr(d1))
        self.assertNotEqual(repr(a), repr(c))

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

        bitboard = chess.Bitboard("8/8/8/3R1P2/8/2k2K2/3p4/r7 b - - 0 82")
        bitboard.push_san("d1=Q+")
        self.assertEqual(bitboard.fen(), "8/8/8/3R1P2/8/2k2K2/8/r2q4 w - - 0 83")

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

        # Promotion.
        fen = "7k/1p2Npbp/8/2P5/1P1r4/3b2QP/3q1pPK/2RB4 b - - 1 29"
        bitboard = chess.Bitboard(fen)
        self.assertEqual(bitboard.san(chess.Move.from_uci("f2f1q")), "f1=Q")
        self.assertEqual(bitboard.san(chess.Move.from_uci("f2f1n")), "f1=N+")
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

    def test_move_count(self):
        board = chess.Bitboard("1N2k3/P7/8/8/3n4/8/2PP4/R3K2R w KQ - 0 1")
        self.assertEqual(board.pseudo_legal_move_count(), 8 + 4 + 3 + 2 + 1 + 6 + 9)

    def test_polyglot(self):
        # Test polyglot compability using test data from
        # http://hardy.uhasselt.be/Toga/book_format.html. Forfeiting castling
        # rights should not reset the half move counter, though.

        board = chess.Bitboard()
        self.assertEqual(board.fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(board.zobrist_hash(), 0x463b96181691fc9c)

        board.push_san("e4")
        self.assertEqual(board.fen(), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        self.assertEqual(board.zobrist_hash(), 0x823c9b50fd114196)

        board.push_san("d5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
        self.assertEqual(board.zobrist_hash(), 0x0756b94461c50fb0)

        board.push_san("e5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
        self.assertEqual(board.zobrist_hash(), 0x662fafb965db29d4)

        board.push_san("f5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3")
        self.assertEqual(board.zobrist_hash(), 0x22a48b5a8e47ff78)

        board.push_san("Ke2")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR b kq - 1 3")
        self.assertEqual(board.zobrist_hash(), 0x652a607ca3f242c1)

        board.push_san("Kf7")
        self.assertEqual(board.fen(), "rnbq1bnr/ppp1pkpp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR w - - 2 4")
        self.assertEqual(board.zobrist_hash(), 0x00fdd303c946bdd9)

        board = chess.Bitboard()
        board.push_san("a4")
        board.push_san("b5")
        board.push_san("h4")
        board.push_san("b4")
        board.push_san("c4")
        self.assertEqual(board.fen(), "rnbqkbnr/p1pppppp/8/8/PpP4P/8/1P1PPPP1/RNBQKBNR b KQkq c3 0 3")
        self.assertEqual(board.zobrist_hash(), 0x3c8123ea7b067637)

        board.push_san("bxc3")
        board.push_san("Ra3")
        self.assertEqual(board.fen(), "rnbqkbnr/p1pppppp/8/8/P6P/R1p5/1P1PPPP1/1NBQKBNR b Kkq - 1 4")
        self.assertEqual(board.zobrist_hash(), 0x5c3f9b829b279560)

    def test_castling_move_generation_bug(self):
        # Specific test position right after castling.
        fen = "rnbqkbnr/2pp1ppp/8/4p3/2BPP3/P1N2N2/PB3PPP/2RQ1RK1 b kq - 1 10"
        board = chess.Bitboard(fen)
        illegal_move = chess.Move.from_uci("g1g2")
        self.assertFalse(illegal_move in board.legal_moves)
        self.assertFalse(illegal_move in list(board.legal_moves))
        self.assertFalse(illegal_move in board.pseudo_legal_moves)
        self.assertFalse(illegal_move in list(board.pseudo_legal_moves))

        # Make a move.
        board.push_san("exd4")

        # Already castled short, can not castle long.
        illegal_move = chess.Move.from_uci("e1c1")
        self.assertFalse(illegal_move in board.pseudo_legal_moves)
        self.assertFalse(illegal_move in board.generate_pseudo_legal_moves())
        self.assertFalse(illegal_move in board.legal_moves)
        self.assertFalse(illegal_move in list(board.legal_moves))

        # Unmake the move.
        board.pop()

        # Generate all pseudo legal moves, two moves deep.
        for move in board.pseudo_legal_moves:
            board.push(move)
            for move in board.pseudo_legal_moves:
                board.push(move)
                board.pop()
            board.pop()

        # Check that board is still consistent.
        self.assertEqual(board.fen(), fen)
        self.assertTrue(board.kings & chess.BB_G1)
        self.assertTrue(board.occupied & chess.BB_G1)
        self.assertTrue(board.occupied_co[chess.WHITE] & chess.BB_G1)
        self.assertEqual(board.piece_at(chess.G1), chess.Piece(chess.KING, chess.WHITE))
        self.assertEqual(board.piece_at(chess.C1), chess.Piece(chess.ROOK, chess.WHITE))

    def test_move_generation_bug(self):
        # Specific problematic position.
        fen = "4kb1r/3b1ppp/8/1r2pNB1/6P1/pP2QP2/P6P/4R1K1 w k - 0 27"
        board = chess.Bitboard(fen)

        # Make a move.
        board.push_san("Re2")

        # Check for the illegal move.
        illegal_move = chess.Move.from_uci("e8f8")
        self.assertFalse(illegal_move in board.pseudo_legal_moves)
        self.assertFalse(illegal_move in board.generate_pseudo_legal_moves())
        self.assertFalse(illegal_move in board.legal_moves)
        self.assertFalse(illegal_move in board.generate_legal_moves())

        # Generate all pseudo legal moves.
        for a in board.pseudo_legal_moves:
            board.push(a)
            board.pop()

        # Unmake the move.
        board.pop()

        # Check that board is still consistent.
        self.assertEqual(board.fen(), fen)

    def test_equality(self):
        self.assertEqual(chess.Bitboard(), chess.Bitboard())
        self.assertFalse(chess.Bitboard() != chess.Bitboard())

        a = chess.Bitboard()
        a.push_san("d4")
        b = chess.Bitboard()
        b.push_san("d3")
        self.assertNotEqual(a, b)
        self.assertFalse(a == b)

    def test_status(self):
        board = chess.Bitboard()
        self.assertEqual(board.status(), chess.STATUS_VALID)

        board.remove_piece_at(chess.H1)
        self.assertTrue(board.status() & chess.STATUS_BAD_CASTLING_RIGHTS)

        board.remove_piece_at(chess.E8)
        self.assertTrue(board.status() & chess.STATUS_NO_BLACK_KING)

        # The en-passant square should be set even if no capture is actually
        # possible.
        board = chess.Bitboard()
        board.push_san("e4")
        self.assertEqual(board.ep_square, chess.E3)
        self.assertEqual(board.status(), chess.STATUS_VALID)

        # But there must indeed be a pawn there.
        board.remove_piece_at(chess.E4)
        self.assertEqual(board.status(), chess.STATUS_INVALID_EP_SQUARE)

    def test_epd(self):
        # Create an EPD with a move and a string.
        board = chess.Bitboard("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - 0 1")
        epd = board.epd(bm=chess.Move(chess.D6, chess.D1), id="BK.01")
        self.assertTrue(epd in (
            "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";",
            "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - id \"BK.01\"; bm Qd1+;" ))

        # Create an EPD with a noop.
        board = chess.Bitboard("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        self.assertEqual(board.epd(noop=None), "4k3/8/8/8/8/8/8/4K3 w - - noop;")

        # Test loading an EPD.
        board = chess.Bitboard()
        operations = board.set_epd("r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - bm f4; id \"BK.24\";")
        self.assertEqual(board.fen(), "r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - 0 1")
        self.assertEqual(operations["bm"], chess.Move(chess.F2, chess.F4))
        self.assertEqual(operations["id"], "BK.24")

        # Test loading an EPD with half counter operations.
        board = chess.Bitboard()
        operations = board.set_epd("4k3/8/8/8/8/8/8/4K3 b - - fmvn 17; hmvc 13")
        self.assertEqual(board.fen(), "4k3/8/8/8/8/8/8/4K3 b - - 13 17")
        self.assertEqual(operations["fmvn"], 17)
        self.assertEqual(operations["hmvc"], 13)

        # Test context of parsed SANs.
        board = chess.Bitboard()
        operations = board.set_epd("4k3/8/8/2N5/8/8/8/4K3 w - - test Ne4")
        self.assertEqual(operations["test"], chess.Move(chess.C5, chess.E4))

    def test_null_moves(self):
        self.assertFalse(chess.Move.null())

        fen = "rnbqkbnr/ppp1pppp/8/2Pp4/8/8/PP1PPPPP/RNBQKBNR w KQkq d6 0 2"
        board = chess.Bitboard(fen)

        self.assertEqual(chess.Move.from_uci("0000"), board.push_san("--"))
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/2Pp4/8/8/PP1PPPPP/RNBQKBNR b KQkq - 1 2")

        self.assertEqual(chess.Move.null(), board.pop())
        self.assertEqual(board.fen(), fen)

    def test_attackers(self):
        board = chess.Bitboard("r1b1k2r/pp1n1ppp/2p1p3/q5B1/1b1P4/P1n1PN2/1P1Q1PPP/2R1KB1R b Kkq - 3 10")

        attackers = board.attackers(chess.WHITE, chess.C3)
        self.assertEqual(len(attackers), 3)
        self.assertTrue(chess.C1 in attackers)
        self.assertTrue(chess.D2 in attackers)
        self.assertTrue(chess.B2 in attackers)
        self.assertFalse(chess.D4 in attackers)
        self.assertFalse(chess.E1 in attackers)

    def test_clear(self):
        board = chess.Bitboard()
        board.clear()

        self.assertEqual(board.turn, chess.WHITE)
        self.assertEqual(board.fullmove_number, 1)
        self.assertEqual(board.halfmove_clock, 0)
        self.assertEqual(board.castling_rights, chess.CASTLING_NONE)
        self.assertFalse(board.ep_square)

        self.assertFalse(board.piece_at(chess.E1))
        self.assertEqual(chess.pop_count(board.occupied), 0)

    def test_rotation(self):
        bb = chess.BB_G1
        bb = chess.l90(bb)
        self.assertEqual(bb, chess.BB_H7)
        bb = chess.l90(bb)
        self.assertEqual(bb, chess.BB_B8)
        bb = chess.l90(bb)
        self.assertEqual(bb, chess.BB_A2)
        bb = chess.l90(bb)
        self.assertEqual(bb, chess.BB_G1)

        self.assertEqual(chess.l45(chess.BB_F2), chess.BB_F8)

        self.assertEqual(chess.r45(chess.BB_F8), chess.BB_F3)

    def test_threefold_repitition(self):
        board = chess.Bitboard()

        # Go back and forth with the nights to reach the starting position
        # for a second time.
        self.assertFalse(board.can_claim_threefold_repitition())
        board.push_san("Nf3")
        self.assertFalse(board.can_claim_threefold_repitition())
        board.push_san("Nf6")
        self.assertFalse(board.can_claim_threefold_repitition())
        board.push_san("Ng1")
        self.assertFalse(board.can_claim_threefold_repitition())
        board.push_san("Ng8")

        # Once more.
        self.assertFalse(board.can_claim_threefold_repitition())
        board.push_san("Nf3")
        self.assertFalse(board.can_claim_threefold_repitition())
        board.push_san("Nf6")
        self.assertFalse(board.can_claim_threefold_repitition())
        board.push_san("Ng1")

        # Now black can go back to the starting position (thus reaching it a
        # third time.)
        self.assertTrue(board.can_claim_threefold_repitition())
        board.push_san("Ng8")

        # They indee do it. Also white can now claim.
        self.assertTrue(board.can_claim_threefold_repitition())

        # But not after a different move.
        board.push_san("e4")
        self.assertFalse(board.can_claim_threefold_repitition())

        # Undo moves and check if everything works backwards.
        board.pop() # e4
        self.assertTrue(board.can_claim_threefold_repitition())
        board.pop() # Ng8
        self.assertTrue(board.can_claim_threefold_repitition())
        while board.move_stack:
            board.pop()
            self.assertFalse(board.can_claim_threefold_repitition())

    def test_fivefold_repitition(self):
        fen = "rnbq1rk1/ppp3pp/3bpn2/3p1p2/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 3 7"
        board = chess.Bitboard(fen)

        # Repeat the position up to the fourth time.
        for i in range(3):
            board.push_san("Be2")
            self.assertFalse(board.is_fivefold_repitition())
            board.push_san("Ne4")
            self.assertFalse(board.is_fivefold_repitition())
            board.push_san("Bd3")
            self.assertFalse(board.is_fivefold_repitition())
            board.push_san("Nf6")
            self.assertEqual(board.fen().split()[0], fen.split()[0])
            self.assertFalse(board.is_fivefold_repitition())
            self.assertFalse(board.is_game_over())

        # Repeat it once more. Now it is a five-fold repitition.
        board.push_san("Be2")
        self.assertFalse(board.is_fivefold_repitition())
        board.push_san("Ne4")
        self.assertFalse(board.is_fivefold_repitition())
        board.push_san("Bd3")
        self.assertFalse(board.is_fivefold_repitition())
        board.push_san("Nf6")
        self.assertEqual(board.fen().split()[0], fen.split()[0])
        self.assertTrue(board.is_fivefold_repitition())
        self.assertTrue(board.is_game_over())

        # It is also a threefold repitition.
        self.assertTrue(board.can_claim_threefold_repitition())

        # Now no longer.
        board.push_san("Qc2")
        board.push_san("Qd7")
        self.assertFalse(board.can_claim_threefold_repitition())
        self.assertFalse(board.is_fivefold_repitition())
        board.push_san("Qd2")
        board.push_san("Qe7")
        self.assertFalse(board.can_claim_threefold_repitition())
        self.assertFalse(board.is_fivefold_repitition())

        # Give the possibility to repeat.
        board.push_san("Qd1")
        self.assertFalse(board.is_fivefold_repitition())
        self.assertTrue(board.can_claim_threefold_repitition())

        # Do in fact repeat.
        self.assertFalse(board.is_fivefold_repitition())
        board.push_san("Qd8")

        # This is a threefold repitition but not a fivefold repitition, because
        # consecutive moves are required for that.
        self.assertTrue(board.can_claim_threefold_repitition())
        self.assertFalse(board.is_fivefold_repitition())
        self.assertEqual(board.fen().split()[0], fen.split()[0])

    def test_fifty_moves(self):
        # Test positions from Timman - Lutz (1995).
        board = chess.Bitboard()
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Bitboard("8/5R2/8/r2KB3/6k1/8/8/8 w - - 19 79")
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Bitboard("8/8/6r1/4B3/8/4K2k/5R2/8 b - - 68 103")
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Bitboard("6R1/7k/8/8/1r3B2/5K2/8/8 w - - 99 119")
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Bitboard("8/7k/8/6R1/1r3B2/5K2/8/8 b - - 100 119")
        self.assertTrue(board.can_claim_fifty_moves())
        board = chess.Bitboard("8/7k/8/1r3KR1/5B2/8/8/8 w - - 105 122")
        self.assertTrue(board.can_claim_fifty_moves())

        # Once checkmated it is too late to claim.
        board = chess.Bitboard("k7/8/NKB5/8/8/8/8/8 b - - 105 176")
        self.assertFalse(board.can_claim_fifty_moves())

        # A stalemate is a draw, but you can not and do not need to claim it by
        # the fifty move rule.
        board = chess.Bitboard("k7/3N4/1K6/1B6/8/8/8/8 b - - 99 1")
        self.assertTrue(board.is_stalemate())
        self.assertTrue(board.is_game_over())
        self.assertFalse(board.can_claim_fifty_moves())
        self.assertFalse(board.can_claim_draw())

    def test_ep_legality(self):
        move = chess.Move.from_uci("h5g6")
        board = chess.Bitboard("rnbqkbnr/pppppp2/7p/6pP/8/8/PPPPPPP1/RNBQKBNR w KQkq g6 0 3")
        self.assertTrue(board.is_legal(move))
        board.push_san("Nf3")
        self.assertFalse(board.is_legal(move))
        board.push_san("Nf6")
        self.assertFalse(board.is_legal(move))

        move = chess.Move.from_uci("c4d3")
        board = chess.Bitboard("rnbqkbnr/pp1ppppp/8/8/2pP4/2P2N2/PP2PPPP/RNBQKB1R b KQkq d3 0 3")
        self.assertTrue(board.is_legal(move))
        board.push_san("Qc7")
        self.assertFalse(board.is_legal(move))
        board.push_san("Bd2")
        self.assertFalse(board.is_legal(move))

    def test_pseudo_legality(self):
        sample_moves = [
            chess.Move(chess.A2, chess.A4),
            chess.Move(chess.C1, chess.E3),
            chess.Move(chess.G8, chess.F6),
            chess.Move(chess.D7, chess.D8, chess.QUEEN),
            chess.Move(chess.E5, chess.E4) ]

        sample_fens = [
            chess.STARTING_FEN,
            "rnbqkbnr/pp1ppppp/2p5/8/6P1/2P5/PP1PPP1P/RNBQKBNR b KQkq - 0 1",
            "rnb1kbnr/ppq1pppp/2pp4/8/6P1/2P5/PP1PPPBP/RNBQK1NR w KQkq - 0 1",
            "rn2kbnr/p1q1ppp1/1ppp3p/8/4B1b1/2P4P/PPQPPP2/RNB1K1NR w KQkq - 0 1",
            "rnkq1bnr/p3ppp1/1ppp3p/3B4/6b1/2PQ3P/PP1PPP2/RNB1K1NR w KQ - 0 1",
            "rn1q1bnr/3kppp1/2pp3p/pp6/1P2b3/2PQ1N1P/P2PPPB1/RNB1K2R w KQ - 0 1",
            "rnkq1bnr/4pp2/2pQ2pp/pp6/1P5N/2P4P/P2PPP2/RNB1KB1b w Q - 0 1",
            "rn3b1r/1kq1p3/2pQ1npp/Pp6/4b3/2PPP2P/P4P2/RNB1KB2 w Q - 0 1",
            "r4br1/8/k1p2npp/Ppn1p3/P7/2PPP1qP/4bPQ1/RNB1KB2 w Q - 0 1",
            "rnbqk1nr/p2p3p/1p5b/2pPppp1/8/P7/1PPQPPPP/RNB1KBNR w KQkq c6 0 1",
            "rnb1k2r/pp1p1p1p/1q1P4/2pnpPp1/6P1/2N5/PP1BP2P/R2QKBNR w KQkq e6 0 1",
            "1n4kr/2B4p/2nb2b1/ppp5/P1PpP3/3P4/5K2/1N1R4 b - c3 0 1",
            "r2n3r/1bNk2pp/6P1/pP3p2/3pPqnP/1P1P1p1R/2P3B1/Q1B1bKN1 b - e3 0 1" ]

        for sample_fen in sample_fens:
            board = chess.Bitboard(sample_fen)

            pseudo_legal_moves = list(board.generate_pseudo_legal_moves())

            # Ensure that all moves generated as pseudo legal pass the pseudo-
            # legality check.
            for move in pseudo_legal_moves:
                self.assertTrue(board.is_pseudo_legal(move))

            # Check that moves not generated as pseudo legal do not pass the
            # pseudo legality check.
            for move in sample_moves:
                if not move in pseudo_legal_moves:
                    self.assertFalse(board.is_pseudo_legal(move))


class LegalMoveGeneratorTestCase(unittest.TestCase):

    def test_list_conversion(self):
        self.assertEqual(len(list(chess.Bitboard().legal_moves)), 20)

    def test_nonzero(self):
        self.assertTrue(chess.Bitboard().legal_moves)

        caro_kann_mate = chess.Bitboard("r1bqkb1r/pp1npppp/2pN1n2/8/3P4/8/PPP1QPPP/R1B1KBNR b KQkq - 4 6")
        self.assertFalse(caro_kann_mate.legal_moves)

    def test_string_conversion(self):
        expected = textwrap.dedent("""\
            r n b q k b n r
            p p p p p p p p
            . . . . . . . .
            . . . . . . . .
            . . . . P . . .
            . . . . . . . .
            P P P P . P P P
            R N B Q K B N R""")

        bb = chess.Bitboard()
        bb.push_san("e4")
        self.assertEqual(str(bb), expected)


class SquareSetTestCase(unittest.TestCase):

    def test_equality(self):
        a1 = chess.SquareSet(chess.BB_RANK_4)
        a2 = chess.SquareSet(chess.BB_RANK_4)
        b1 = chess.SquareSet(chess.BB_RANK_5 | chess.BB_RANK_6)
        b2 = chess.SquareSet(chess.BB_RANK_5 | chess.BB_RANK_6)

        self.assertEqual(a1, a2)
        self.assertEqual(b1, b2)
        self.assertFalse(a1 != a2)
        self.assertFalse(b1 != b2)

        self.assertNotEqual(a1, b1)
        self.assertNotEqual(a2, b2)
        self.assertFalse(a1 == b1)
        self.assertFalse(a2 == b2)

        self.assertEqual(chess.SquareSet(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.BB_ALL, chess.SquareSet(chess.BB_ALL))

    def test_string_conversion(self):
        expected = textwrap.dedent("""\
            . . . . . . . 1
            . 1 . . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .
            1 1 1 1 1 1 1 1""")

        bb = chess.SquareSet(chess.BB_H8 | chess.BB_B7 | chess.BB_RANK_1)
        self.assertEqual(str(bb), expected)

    def test_iter(self):
        bb = chess.SquareSet(chess.BB_G7 | chess.BB_G8)
        self.assertEqual(set(bb), {chess.G7, chess.G8})

    def test_arithmetic(self):
        self.assertEqual(chess.SquareSet(chess.BB_RANK_2) & chess.BB_FILE_D, chess.BB_D2)
        self.assertEqual(chess.SquareSet(chess.BB_ALL) ^ chess.BB_VOID, chess.BB_ALL)
        self.assertEqual(chess.SquareSet(chess.BB_C1) | chess.BB_FILE_C, chess.BB_FILE_C)

        bb = chess.SquareSet(chess.BB_VOID)
        bb ^= chess.BB_ALL
        self.assertEqual(bb, chess.BB_ALL)
        bb &= chess.BB_E4
        self.assertEqual(bb, chess.BB_E4)
        bb |= chess.BB_RANK_4
        self.assertEqual(bb, chess.BB_RANK_4)

        self.assertEqual(chess.SquareSet(chess.BB_F3) << 1, chess.BB_G3)
        self.assertEqual(chess.SquareSet(chess.BB_C8) >> 2, chess.BB_A8)

        bb = chess.SquareSet(chess.BB_D1)
        bb <<= 1
        self.assertEqual(bb, chess.BB_E1)
        bb >>= 2
        self.assertEqual(bb, chess.BB_C1)


class PolyglotTestCase(unittest.TestCase):

    def test_performance_bin(self):
        with chess.polyglot.open_reader("data/opening-books/performance.bin") as book:
            pos = chess.Bitboard()

            e4 = next(book.get_entries_for_position(pos))
            self.assertEqual(e4.move(), pos.parse_san("e4"))
            pos.push(e4.move())

            e5 = next(book.get_entries_for_position(pos))
            self.assertEqual(e5.move(), pos.parse_san("e5"))
            pos.push(e5.move())

    def test_mainline(self):
        with chess.polyglot.open_reader("data/opening-books/performance.bin") as book:
            board = chess.Bitboard()

            while True:
                try:
                    entry = next(book.get_entries_for_position(board))
                    board.push(entry.move())
                except StopIteration:
                    break

            self.assertEqual(board.fen(), "r2q1rk1/4bppp/p2p1n2/np5b/3BP1P1/5N1P/PPB2P2/RN1QR1K1 b - g3 0 15")

    def test_lasker_trap(self):
        with chess.polyglot.open_reader("data/opening-books/lasker-trap.bin") as book:
            board = chess.Bitboard("rnbqk1nr/ppp2ppp/8/4P3/1BP5/8/PP2KpPP/RN1Q1BNR b kq - 1 7")
            entry = next(book.get_entries_for_position(board))
            cute_underpromotion = entry.move()
            self.assertEqual(cute_underpromotion, board.parse_san("fxg1=N+"))

    def test_castling(self):
        with chess.polyglot.open_reader("data/opening-books/performance.bin") as book:
            # White decides between short castling and long castling at this
            # turning point in the Queens Gambit Exchange.
            pos = chess.Bitboard("r1bqr1k1/pp1nbppp/2p2n2/3p2B1/3P4/2NBP3/PPQ1NPPP/R3K2R w KQ - 5 10")
            moves = set(entry.move() for entry in book.get_entries_for_position(pos))
            self.assertTrue(pos.parse_san("O-O") in moves)
            self.assertTrue(pos.parse_san("O-O-O") in moves)
            self.assertTrue(pos.parse_san("h3") in moves)
            self.assertEqual(len(moves), 3)

            # Black usually castles long at this point in the Ruy Lopez
            # Exchange.
            pos = chess.Bitboard("r3k1nr/1pp1q1pp/p1pb1p2/4p3/3PP1b1/2P1BN2/PP1N1PPP/R2Q1RK1 b kq - 4 9")
            moves = set(entry.move() for entry in book.get_entries_for_position(pos))
            self.assertTrue(pos.parse_san("O-O-O") in moves)
            self.assertEqual(len(moves), 1)


class PgnTestCase(unittest.TestCase):

    def test_exporter(self):
        game = chess.pgn.Game()
        game.comment = "Test game:"
        game.headers["Result"] = "*"

        e4 = game.add_variation(game.board().parse_san("e4"))
        e4.comment = "Scandinavian defense:"

        e4_d5 = e4.add_variation(e4.board().parse_san("d5"))

        e4_h5 = e4.add_variation(e4.board().parse_san("h5"))
        e4_h5.nags.add(chess.pgn.NAG_MISTAKE)
        e4_h5.starting_comment = "This"
        e4_h5.comment = "is nonesense"

        e4_e5 = e4.add_variation(e4.board().parse_san("e5"))
        e4_e5_Qf3 = e4_e5.add_variation(e4_e5.board().parse_san("Qf3"))
        e4_e5_Qf3.nags.add(chess.pgn.NAG_MISTAKE)

        e4_c5 = e4.add_variation(e4.board().parse_san("c5"))
        e4_c5.comment = "Sicilian"

        e4_d5_exd5 = e4_d5.add_main_variation(e4_d5.board().parse_san("exd5"))

        # Test string exporter with various options.
        exporter = chess.pgn.StringExporter()
        game.export(exporter, headers=False, comments=False, variations=False)
        self.assertEqual(str(exporter), "1. e4 d5 2. exd5 *")

        exporter = chess.pgn.StringExporter()
        game.export(exporter, headers=False, comments=False)
        self.assertEqual(str(exporter), "1. e4 d5 ( 1... h5 ) ( 1... e5 2. Qf3 ) ( 1... c5 ) 2. exd5 *")

        exporter = chess.pgn.StringExporter()
        game.export(exporter)
        pgn = textwrap.dedent("""\
            [Event "?"]
            [Site "?"]
            [Date "????.??.??"]
            [Round "?"]
            [White "?"]
            [Black "?"]
            [Result "*"]

            { Test game: } 1. e4 { Scandinavian defense: } d5 ( { This } 1... h5 $2
            { is nonesense } ) ( 1... e5 2. Qf3 $2 ) ( 1... c5 { Sicilian } ) 2. exd5 *""")
        self.assertEqual(str(exporter), pgn)

        # Test file exporter.
        virtual_file = StringIO()
        exporter = chess.pgn.FileExporter(virtual_file)
        game.export(exporter)
        self.assertEqual(virtual_file.getvalue(), pgn + "\n\n")

    def test_setup(self):
        game = chess.pgn.Game()
        self.assertEqual(game.board(), chess.Bitboard())
        self.assertFalse("FEN" in game.headers)
        self.assertFalse("SetUp" in game.headers)

        fen = "rnbqkbnr/pp1ppp1p/6p1/8/3pP3/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 4"
        game.setup(fen)
        self.assertEqual(game.headers["FEN"], fen)
        self.assertEqual(game.headers["SetUp"], "1")

        game.setup(chess.STARTING_FEN)
        self.assertFalse("FEN" in game.headers)
        self.assertFalse("SetUp" in game.headers)

        game.setup(chess.Bitboard(fen))
        self.assertEqual(game.headers["FEN"], fen)
        self.assertEqual(game.headers["SetUp"], "1")

    def test_promote_to_main(self):
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")

        node = chess.pgn.Game()
        node.add_variation(e4)
        node.add_variation(d4)
        self.assertEqual(list(variation.move for variation in node.variations), [e4, d4])

        node.promote_to_main(d4)
        self.assertEqual(list(variation.move for variation in node.variations), [d4, e4])

    def test_read_game(self):
        pgn = open("data/games/kasparov-deep-blue-1997.pgn")
        first_game = chess.pgn.read_game(pgn)
        second_game = chess.pgn.read_game(pgn)
        third_game = chess.pgn.read_game(pgn)
        fourth_game = chess.pgn.read_game(pgn)
        fifth_game = chess.pgn.read_game(pgn)
        sixth_game = chess.pgn.read_game(pgn)
        self.assertTrue(chess.pgn.read_game(pgn) is None)
        pgn.close()

        self.assertEqual(first_game.headers["Event"], "IBM Man-Machine, New York USA")
        self.assertEqual(first_game.headers["Site"], "01")
        self.assertEqual(first_game.headers["Result"], "1-0")

        self.assertEqual(second_game.headers["Event"], "IBM Man-Machine, New York USA")
        self.assertEqual(second_game.headers["Site"], "02")

        self.assertEqual(third_game.headers["ECO"], "A00")

        self.assertEqual(fourth_game.headers["PlyCount"], "111")

        self.assertEqual(fifth_game.headers["Result"], "1/2-1/2")

        self.assertEqual(sixth_game.headers["White"], "Deep Blue (Computer)")
        self.assertEqual(sixth_game.headers["Result"], "1-0")

    def test_comment_at_eol(self):
        pgn = StringIO(textwrap.dedent("""\
            1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. Nbd2 a6 $6 (6... Bb6 $5 {
            /\ Ne7, c6}) *"""))

        game = chess.pgn.read_game(pgn)

        # Seek the node after 6.Nbd2 and before 6...a6.
        node = game
        while node.variations and not node.has_variation(chess.Move.from_uci("a7a6")):
            node = node.variation(0)

        # Make sure the comment for the second variation is there.
        self.assertTrue(5 in node.variation(1).nags)
        self.assertEqual(node.variation(1).comment, "/\\ Ne7, c6")

    def test_variation_stack(self):
        # Ignore superfluous closing brackets.
        pgn = StringIO("1. e4 (1. d4))) !? *")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.variation(0).san(), "e4")
        self.assertEqual(game.variation(1).san(), "d4")

        # Ignore superfluous opening brackets.
        pgn = StringIO("((( 1. c4 *")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.variation(0).san(), "c4")

    def test_game_starting_comment(self):
        pgn = StringIO("{ Game starting comment } 1. d3")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comment, "Game starting comment")
        self.assertEqual(game.variation(0).san(), "d3")

        pgn = StringIO("{ Empty game, but has a comment }")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comment, "Empty game, but has a comment")

    def test_annotation_symbols(self):
        pgn = StringIO("1. b4?! g6 2. Bb2 Nc6? 3. Bxh8!!")
        game = chess.pgn.read_game(pgn)

        node = game.variation(0)
        self.assertTrue(chess.pgn.NAG_DUBIOUS_MOVE in node.nags)
        self.assertEqual(len(node.nags), 1)

        node = node.variation(0)
        self.assertEqual(len(node.nags), 0)

        node = node.variation(0)
        self.assertEqual(len(node.nags), 0)

        node = node.variation(0)
        self.assertTrue(chess.pgn.NAG_MISTAKE in node.nags)
        self.assertEqual(len(node.nags), 1)

        node = node.variation(0)
        self.assertTrue(chess.pgn.NAG_BRILLIANT_MOVE in node.nags)
        self.assertEqual(len(node.nags), 1)

    def test_tree_traversal(self):
        game = chess.pgn.Game()
        node = game.add_variation(chess.Move(chess.E2, chess.E4))
        alternative_node = game.add_variation(chess.D2, chess.D4)
        end_node = node.add_variation(chess.Move(chess.E7, chess.E5))

        self.assertEqual(game.root(), game)
        self.assertEqual(node.root(), game)
        self.assertEqual(alternative_node.root(), game)
        self.assertEqual(end_node.root(), game)

        self.assertEqual(game.end(), end_node)
        self.assertEqual(node.end(), end_node)
        self.assertEqual(end_node.end(), end_node)
        self.assertEqual(alternative_node.end(), alternative_node)

        self.assertTrue(game.is_main_line())
        self.assertTrue(node.is_main_line())
        self.assertTrue(end_node.is_main_line())
        self.assertFalse(alternative_node.is_main_line())

        self.assertFalse(game.starts_variation())
        self.assertFalse(node.starts_variation())
        self.assertFalse(end_node.starts_variation())
        self.assertTrue(alternative_node.starts_variation())

    def test_promote_demote(self):
        game = chess.pgn.Game()
        a = game.add_variation(chess.Move(chess.A2, chess.A3))
        b = game.add_variation(chess.Move(chess.B2, chess.B3))

        self.assertTrue(a.is_main_variation())
        self.assertFalse(b.is_main_variation())
        self.assertEqual(game.variation(0), a)
        self.assertEqual(game.variation(1), b)

        game.promote(b)
        self.assertTrue(b.is_main_variation())
        self.assertFalse(a.is_main_variation())
        self.assertEqual(game.variation(0), b)
        self.assertEqual(game.variation(1), a)

        game.demote(b)
        self.assertTrue(a.is_main_variation())

        c = game.add_main_variation(chess.Move(chess.C2, chess.C3))
        self.assertTrue(c.is_main_variation())
        self.assertFalse(a.is_main_variation())
        self.assertFalse(b.is_main_variation())
        self.assertEqual(game.variation(0), c)
        self.assertEqual(game.variation(1), a)
        self.assertEqual(game.variation(2), b)

    def test_scan_offsets(self):
        with open("data/games/kasparov-deep-blue-1997.pgn") as pgn:
            offsets = list(chess.pgn.scan_offsets(pgn))
            self.assertEqual(len(offsets), 6)

            pgn.seek(offsets[0])
            first_game = chess.pgn.read_game(pgn)
            self.assertEqual(first_game.headers["Event"], "IBM Man-Machine, New York USA")
            self.assertEqual(first_game.headers["Site"], "01")

            pgn.seek(offsets[5])
            sixth_game = chess.pgn.read_game(pgn)
            self.assertEqual(sixth_game.headers["Event"], "IBM Man-Machine, New York USA")
            self.assertEqual(sixth_game.headers["Site"], "06")

    def test_scan_headers(self):
        with open("data/games/kasparov-deep-blue-1997.pgn") as pgn:
            offsets = (offset for offset, headers in chess.pgn.scan_headers(pgn)
                              if headers["Result"] == "1/2-1/2")

            first_drawn_game_offset = next(offsets)
            pgn.seek(first_drawn_game_offset)
            first_drawn_game = chess.pgn.read_game(pgn)
            self.assertEqual(first_drawn_game.headers["Site"], "03")
            self.assertEqual(first_drawn_game.variation(0).move, chess.Move.from_uci("d2d3"))


class StockfishTestCase(unittest.TestCase):

    @unittest.skipUnless(os.path.isfile("/usr/games/stockfish"), "need /usr/games/stockfish")
    def setUp(self):
        self.engine = chess.uci.popen_engine("/usr/games/stockfish")
        self.engine.uci()

    def tearDown(self):
        self.engine.quit()

    def test_forced_mates(self):
        epds = [
            "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";",
            "4R3/p1p2p2/P4P2/P7/1r1pN1p1/1p1PpkP1/1P2r2p/3B3K w - - bm Rh8; id \"Tamminen 1944\";",
        ]

        board = chess.Bitboard()

        for epd in epds:
            operations = board.set_epd(epd)
            self.engine.ucinewgame()
            self.engine.position(board)
            result = self.engine.go(movetime=4000)
            self.assertEqual(result[0], operations["bm"], operations["id"])

    def test_async(self):
        self.engine.ucinewgame()
        command = self.engine.go(movetime=1000, async_callback=True)
        self.assertFalse(command.done())
        command.result()
        self.assertTrue(command.done())

    def test_async_callback(self):
        self.async_callback_called = False
        def async_callback(command):
            self.async_callback_called = True

        command = self.engine.isready(async_callback=async_callback)

        self.engine.isready() # Synchronize
        self.assertTrue(self.async_callback_called)
        self.assertTrue(command.done())

    def test_initialization(self):
        self.assertTrue("Stockfish" in self.engine.name)
        self.assertEqual(self.engine.options["UCI_Chess960"].name, "UCI_Chess960")
        self.assertEqual(self.engine.options["uci_Chess960"].type, "check")
        self.assertEqual(self.engine.options["UCI_CHESS960"].default, False)

    def test_multi_pv(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.setoption({
            "MultiPV": 2
        })

        self.engine.ucinewgame()

        board = chess.Bitboard("r3r3/pp3qk1/2p3Pp/3pP3/3P2b1/2NB4/PPQ1N1P1/4b2K w - - 0 24")
        self.engine.position(board)

        self.engine.go(infinite=True)
        time.sleep(4)

        with handler as info:
            self.assertEqual(info["pv"][1][0], chess.Move.from_uci("g6f7"))
            self.assertEqual(info["pv"][2][0], chess.Move.from_uci("c3e4"))

        self.engine.stop()

    def test_terminate(self):
        self.engine.go(infinite=True)


class SpurEngineTestCase(unittest.TestCase):

    def setUp(self):
        try:
            import spur
            self.shell = spur.LocalShell()
        except ImportError:
            self.skipTest("need spur library")

    @unittest.skipUnless(os.path.isfile("/usr/games/stockfish"), "need /usr/games/stockfish")
    def test_local_shell(self):
        engine = chess.uci.spur_spawn_engine(self.shell, ["/usr/games/stockfish"])

        engine.uci()

        engine.ucinewgame()

        # Find fools mate.
        board = chess.Bitboard()
        board.push_san("g4")
        board.push_san("e5")
        board.push_san("f4")
        engine.position(board)
        bestmove, pondermove = engine.go(mate=1, movetime=2000)
        self.assertEqual(board.san(bestmove), "Qh4#")

    @unittest.skipUnless(os.path.isfile("/usr/games/stockfish"), "need /usr/games/stockfish")
    def test_terminate(self):
        engine = chess.uci.spur_spawn_engine(self.shell, ["/usr/games/stockfish"])

        engine.uci()
        engine.go(infinite=True)

        engine.terminate()
        self.assertFalse(engine.is_alive())

    @unittest.skipUnless(os.path.isfile("/usr/games/stockfish"), "need /usr/games/stockfish")
    def test_kill(self):
        engine = chess.uci.spur_spawn_engine(self.shell, ["/usr/games/stockfish"])

        engine.uci()
        engine.go(infinite=True)

        engine.kill()
        self.assertFalse(engine.is_alive())

    @unittest.skipUnless(os.path.isfile("/usr/games/stockfish"), "need /usr/games/stockfish")
    def test_async_terminate(self):
        engine = chess.uci.spur_spawn_engine(self.shell, ["/usr/games/stockfish"])

        command = engine.terminate(async=True)
        command.result()
        self.assertTrue(command.done())


class UciEngineTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = chess.uci.Engine(chess.uci.MockProcess())
        self.mock = self.engine.process

        self.mock.expect("uci", ("uciok", ))
        self.engine.uci()
        self.mock.assert_done()

    def tearDown(self):
        self.engine.terminate()
        self.mock.assert_terminated()

    def test_debug(self):
        self.mock.expect("debug on")
        self.engine.debug(True)
        self.mock.assert_done()

        self.mock.expect("debug off")
        self.engine.debug(False)
        self.mock.assert_done()

    def test_ponderhit(self):
        self.mock.expect("ponderhit")
        self.mock.expect("isready", ("readyok", ))
        self.engine.ponderhit()
        self.mock.assert_done()

    def test_async_ponderhit(self):
        self.mock.expect("ponderhit")
        self.mock.expect("isready", ("readyok", ))
        command = self.engine.ponderhit(async_callback=True)
        command.result()
        self.assertTrue(command.done())
        self.mock.assert_done()

    def test_kill(self):
        self.engine.kill()
        self.mock.assert_terminated()

    def test_go(self):
        self.mock.expect("go searchmoves e2e4 d2d4 ponder infinite")
        self.engine.go(
            searchmoves=[chess.Move.from_uci("e2e4"), chess.Move.from_uci("d2d4")],
            ponder=True,
            infinite=True)
        self.mock.assert_done()

        self.mock.expect("stop", ("bestmove e2e4", ))
        self.mock.expect("isready", ("readyok", ))
        bestmove, pondermove = self.engine.stop()
        self.mock.assert_done()
        self.assertEqual(bestmove, chess.Move.from_uci("e2e4"))
        self.assertTrue(pondermove is None)

        self.mock.expect("go wtime 1 btime 2 winc 3 binc 4 movestogo 5 depth 6 nodes 7 mate 8 movetime 9", (
            "bestmove d2d4 ponder d7d5",
        ))
        self.engine.go(wtime=1, btime=2, winc=3, binc=4, movestogo=5, depth=6, nodes=7, mate=8, movetime=9)
        self.mock.assert_done()

    def test_info_refutation(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info refutation d1h5 g6h5")

        d1h5 = chess.Move.from_uci("d1h5")
        g6h5 = chess.Move.from_uci("g6h5")

        with handler as info:
            self.assertEqual(len(info["refutation"][d1h5]), 1)
            self.assertEqual(info["refutation"][d1h5][0], g6h5)

        self.engine.on_line_received("info refutation d1h5")
        with handler as info:
            self.assertTrue(info["refutation"][d1h5] is None)

    def test_info_string(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info string goes to end no matter score cp 4 what")
        with handler as info:
            self.assertEqual(info["string"], "goes to end no matter score cp 4 what")
            self.assertFalse("score" in info)

    def test_info_currline(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info currline 0 e2e4 e7e5")
        with handler as info:
            self.assertEqual(info["currline"][0], [
                chess.Move.from_uci("e2e4"),
                chess.Move.from_uci("e7e5"),
            ])

        self.engine.on_line_received("info currline 1 string eol")
        with handler as info:
            self.assertEqual(info["currline"][1], [])

    def test_mate_score(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info depth 7 seldepth 8 score mate 3")
        with handler as info:
            self.assertEqual(info["score"].mate, 3)
            self.assertEqual(info["score"].cp, None)

    def test_info(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info tbhits 123 cpuload 456 hashfull 789")
        with handler as info:
            self.assertEqual(info["tbhits"], 123)
            self.assertEqual(info["cpuload"], 456)
            self.assertEqual(info["hashfull"], 789)

    def test_combo_option(self):
        self.engine.on_line_received("option name MyEnum type combo var Abc def var g h")
        self.assertEqual(self.engine.options["MyEnum"].type, "combo")
        self.assertEqual(self.engine.options["MyEnum"].var, ["Abc def", "g h"])

    def test_set_option(self):
        self.mock.expect("setoption name Yes value true")
        self.mock.expect("setoption name No value false")
        self.mock.expect("setoption name Null option value none")
        self.mock.expect("setoption name String option value value value")
        self.mock.expect("isready", ("readyok", ))
        self.engine.setoption(collections.OrderedDict([
            ("Yes", True),
            ("No", False),
            ("Null option", None),
            ("String option", "value value"),
        ]))
        self.mock.assert_done()


class SyzygyTestCase(unittest.TestCase):

    def test_calc_key(self):
        board = chess.Bitboard("8/8/8/5N2/5K2/2kB4/8/8 b - - 0 1")
        key_from_board = chess.syzygy.calc_key(board)
        key_from_filename = chess.syzygy.calc_key_from_filename("KBNvK")
        self.assertEqual(key_from_board, key_from_filename)

    def test_probe_pawnless_wdl_table(self):
        wdl = chess.syzygy.WdlTable("data/syzygy", "KBNvK")

        board = chess.Bitboard("8/8/8/5N2/5K2/2kB4/8/8 b - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), -2)

        board = chess.Bitboard("7B/5kNK/8/8/8/8/8/8 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        board = chess.Bitboard("N7/8/2k5/8/7K/8/8/B7 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        board = chess.Bitboard("8/8/1NkB4/8/7K/8/8/8 w - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 0)

        board = chess.Bitboard("8/8/8/2n5/2b1K3/2k5/8/8 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), -2)

        wdl.close()

    def test_probe_wdl_table(self):
        wdl = chess.syzygy.WdlTable("data/syzygy", "KRvKP")

        board = chess.Bitboard("8/8/2K5/4P3/8/8/8/3r3k b - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 0)

        board = chess.Bitboard("8/8/2K5/8/4P3/8/8/3r3k b - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        wdl.close()

    def test_probe_dtz_table_piece(self):
        dtz = chess.syzygy.DtzTable("data/syzygy", "KRvKN")

        # Pawnless position with white to move.
        board = chess.Bitboard("7n/6k1/4R3/4K3/8/8/8/8 w - - 0 1")
        self.assertEqual(dtz.probe_dtz_table(board, 2), (0, -1))

        # Same position with black to move.
        board = chess.Bitboard("7n/6k1/4R3/4K3/8/8/8/8 b - - 1 1")
        self.assertEqual(dtz.probe_dtz_table(board, -2), (8, 1))

        dtz.close()

    def test_probe_dtz_table_pawn(self):
        dtz = chess.syzygy.DtzTable("data/syzygy", "KNvKP")

        board = chess.Bitboard("8/1K6/1P6/8/8/8/6n1/7k w - - 0 1")
        self.assertEqual(dtz.probe_dtz_table(board, 2), (2, 1))

        dtz.close()

    def test_probe_wdl_tablebase(self):
        tablebases = chess.syzygy.Tablebases()
        self.assertEqual(tablebases.open_directory("data/syzygy"), 70)

        # Winning KRvKB.
        board = chess.Bitboard("7k/6b1/6K1/8/8/8/8/3R4 b - - 12 7")
        self.assertEqual(tablebases.probe_wdl_table(board), -2)

        # Drawn KBBvK.
        board = chess.Bitboard("7k/8/8/4K3/3B4/4B3/8/8 b - - 12 7")
        self.assertEqual(tablebases.probe_wdl_table(board), 0)

        # Winning KBBvK.
        board = chess.Bitboard("7k/8/8/4K2B/8/4B3/8/8 w - - 12 7")
        self.assertEqual(tablebases.probe_wdl_table(board), 2)

        tablebases.close()

    def test_wdl_ep(self):
        tablebases = chess.syzygy.Tablebases("data/syzygy")

        # Winning KPvKP because of en-passant.
        board = chess.Bitboard("8/8/8/k2Pp3/8/8/8/4K3 w - e6 0 2")

        # If there was no en-passant this would be a draw.
        self.assertEqual(tablebases.probe_wdl_table(board), 0)

        # But it is a win.
        self.assertEqual(tablebases.probe_wdl(board), 2)

        tablebases.close()

    def test_dtz_ep(self):
        tablebases = chess.syzygy.Tablebases("data/syzygy")

        board = chess.Bitboard("8/8/8/8/2pP4/2K5/4k3/8 b - d3 0 1")
        self.assertEqual(tablebases.probe_dtz_no_ep(board), -1)
        self.assertEqual(tablebases.probe_dtz(board), 1)

        tablebases.close()

    def test_testsuite(self):
        tablebases = chess.syzygy.Tablebases("data/syzygy")

        board = chess.Bitboard()

        with open("data/endgame.epd") as epds:
            for line, epd in enumerate(epds):
                extra = board.set_epd(epd)

                wdl_table = tablebases.probe_wdl_table(board)
                self.assertEqual(
                    wdl_table, extra["wdl_table"],
                    "Expecting wdl_table %d for %s, got %d (at line %d)" % (extra["wdl_table"], board.fen(), wdl_table, line + 1))

                wdl = tablebases.probe_wdl(board)
                self.assertEqual(
                    wdl, extra["wdl"],
                    "Expecting wdl %d for %s, got %d (at line %d)" % (extra["wdl"], board.fen(), wdl, line + 1))

                dtz = tablebases.probe_dtz(board)
                self.assertEqual(
                    dtz, extra["dtz"],
                    "Expecting dtz %d for %s, got %d (at line %d)" % (extra["dtz"], board.fen(), dtz, line + 1))

        tablebases.close()


if __name__ == "__main__":
    unittest.main()
