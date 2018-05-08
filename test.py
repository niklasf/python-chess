#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2018 Niklas Fiekas <niklas.fiekas@backscattering.de>
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
import chess.xboard
import chess.syzygy
import chess.gaviota
import chess.variant
import chess.svg
import collections
import copy
import os
import os.path
import textwrap
import sys
import time
import threading
import logging
import platform
import unittest

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO  # Python 3


class RaiseLogHandler(logging.StreamHandler):
    def handle(self, record):
        super(RaiseLogHandler, self).handle(record)
        raise RuntimeError("was expecting no log messages")


def catchAndSkip(signature, message=None):
    def _decorator(f):
        def _wrapper(self):
            try:
                return f(self)
            except signature as err:
                raise unittest.SkipTest(message or err)
        return _wrapper
    return _decorator


class SquareTestCase(unittest.TestCase):

    def test_square(self):
        for square in chess.SQUARES:
            file_index = chess.square_file(square)
            rank_index = chess.square_rank(square)
            self.assertEqual(chess.square(file_index, rank_index), square, chess.SQUARE_NAMES[square])

    def test_shifts(self):
        shifts = [
            chess.shift_down,
            chess.shift_2_down,
            chess.shift_up,
            chess.shift_2_up,
            chess.shift_right,
            chess.shift_2_right,
            chess.shift_left,
            chess.shift_2_left,
            chess.shift_up_left,
            chess.shift_up_right,
            chess.shift_down_left,
            chess.shift_down_right,
        ]

        for shift in shifts:
            for bb_square in chess.BB_SQUARES:
                shifted = shift(bb_square)
                c = chess.popcount(shifted)
                self.assertLessEqual(c, 1)
                self.assertEqual(c, chess.popcount(shifted & chess.BB_ALL))


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
        self.assertEqual(chess.Move.from_uci("P@e4").uci(), "P@e4")
        self.assertEqual(chess.Move.from_uci("B@f4").uci(), "B@f4")

    def test_invalid_uci(self):
        with self.assertRaises(ValueError):
            chess.Move.from_uci("")

        with self.assertRaises(ValueError):
            chess.Move.from_uci("N")

        with self.assertRaises(ValueError):
            chess.Move.from_uci("z1g3")

        with self.assertRaises(ValueError):
            chess.Move.from_uci("Q@g9")

    def test_copy(self):
        a = chess.Move.from_uci("N@f3")
        b = chess.Move.from_uci("a1h8")
        c = chess.Move.from_uci("g7g8r")
        self.assertEqual(copy.copy(a), a)
        self.assertEqual(copy.copy(b), b)
        self.assertEqual(copy.copy(c), c)


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


class BoardTestCase(unittest.TestCase):

    def test_default_position(self):
        board = chess.Board()
        self.assertEqual(board.piece_at(chess.B1), chess.Piece.from_symbol("N"))
        self.assertEqual(board.fen(), chess.STARTING_FEN)
        self.assertEqual(board.turn, chess.WHITE)

    def test_empty(self):
        board = chess.Board.empty()
        self.assertEqual(board.fen(), "8/8/8/8/8/8/8/8 w - - 0 1")
        self.assertEqual(board, chess.Board(None))

    def test_from_epd(self):
        base_epd = "rnbqkb1r/ppp1pppp/5n2/3P4/8/8/PPPP1PPP/RNBQKBNR w KQkq -"
        board, ops = chess.Board.from_epd(base_epd + " ce 55;")
        self.assertEqual(ops["ce"], 55)
        self.assertEqual(board.fen(), base_epd + " 0 1")

    def test_move_making(self):
        board = chess.Board()
        move = chess.Move(chess.E2, chess.E4)
        board.push(move)
        self.assertEqual(board.peek(), move)

    def test_fen(self):
        board = chess.Board()
        self.assertEqual(board.fen(), chess.STARTING_FEN)

        fen = "6k1/pb3pp1/1p2p2p/1Bn1P3/8/5N2/PP1q1PPP/6K1 w - - 0 24"
        board.set_fen(fen)
        self.assertEqual(board.fen(), fen)

        board.push(chess.Move.from_uci("f3d2"))
        self.assertEqual(board.fen(), "6k1/pb3pp1/1p2p2p/1Bn1P3/8/8/PP1N1PPP/6K1 b - - 0 24")

    def test_xfen(self):
        # https://de.wikipedia.org/wiki/Forsyth-Edwards-Notation#Beispiel
        xfen = "rn2k1r1/ppp1pp1p/3p2p1/5bn1/P7/2N2B2/1PPPPP2/2BNK1RR w Gkq - 4 11"
        board = chess.Board(xfen, chess960=True)
        self.assertEqual(board.castling_rights, chess.BB_G1 | chess.BB_A8 | chess.BB_G8)
        self.assertEqual(board.clean_castling_rights(), chess.BB_G1 | chess.BB_A8 | chess.BB_G8)
        self.assertEqual(board.shredder_fen(), "rn2k1r1/ppp1pp1p/3p2p1/5bn1/P7/2N2B2/1PPPPP2/2BNK1RR w Gga - 4 11")
        self.assertEqual(board.fen(), xfen)
        self.assertTrue(board.has_castling_rights(chess.WHITE))
        self.assertTrue(board.has_castling_rights(chess.BLACK))
        self.assertTrue(board.has_kingside_castling_rights(chess.BLACK))
        self.assertTrue(board.has_kingside_castling_rights(chess.WHITE))
        self.assertTrue(board.has_queenside_castling_rights(chess.BLACK))
        self.assertFalse(board.has_queenside_castling_rights(chess.WHITE))

        # Chess960 position #284.
        board = chess.Board("rkbqrbnn/pppppppp/8/8/8/8/PPPPPPPP/RKBQRBNN w - - 0 1", chess960=True)
        board.castling_rights = board.rooks
        self.assertTrue(board.clean_castling_rights() & chess.BB_A1)
        self.assertEqual(board.fen(), "rkbqrbnn/pppppppp/8/8/8/8/PPPPPPPP/RKBQRBNN w KQkq - 0 1")
        self.assertEqual(board.shredder_fen(), "rkbqrbnn/pppppppp/8/8/8/8/PPPPPPPP/RKBQRBNN w EAea - 0 1")

        # Valid en passant square on illegal board.
        fen = "8/8/8/pP6/8/8/8/8 w - a6 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.fen(), fen)

        # Illegal en passant square in illegal board.
        fen = "1r6/8/8/pP6/8/8/8/1K6 w - a6 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.fen(), "1r6/8/8/pP6/8/8/8/1K6 w - - 0 1")

    def test_fen_en_passant(self):
        board = chess.Board()
        board.push_san("e4")
        self.assertEqual(board.fen(en_passant="fen"), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        self.assertEqual(board.fen(en_passant="xfen"), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")

    def test_get_set(self):
        board = chess.Board()
        self.assertEqual(board.piece_at(chess.B1), chess.Piece.from_symbol("N"))

        board.remove_piece_at(chess.E2)
        self.assertEqual(board.piece_at(chess.E2), None)

        board.set_piece_at(chess.E4, chess.Piece.from_symbol("r"))
        self.assertEqual(board.piece_type_at(chess.E4), chess.ROOK)

        board.set_piece_at(chess.F1, None)
        self.assertEqual(board.piece_at(chess.F1), None)

        board.set_piece_at(chess.H7, chess.Piece.from_symbol("Q"), promoted=True)
        self.assertEqual(board.promoted, chess.BB_H7)

    def test_pawn_captures(self):
        board = chess.Board()

        # Kings gambit.
        board.push(chess.Move.from_uci("e2e4"))
        board.push(chess.Move.from_uci("e7e5"))
        board.push(chess.Move.from_uci("f2f4"))

        # Accepted.
        exf4 = chess.Move.from_uci("e5f4")
        self.assertIn(exf4, board.pseudo_legal_moves)
        self.assertIn(exf4, board.legal_moves)
        board.push(exf4)
        board.pop()

    def test_pawn_move_generation(self):
        board = chess.Board("8/2R1P3/8/2pp4/2k1r3/P7/8/1K6 w - - 1 55")
        self.assertEqual(len(list(board.generate_pseudo_legal_moves())), 16)

    def test_single_step_pawn_move(self):
        board = chess.Board()
        a3 = chess.Move.from_uci("a2a3")
        self.assertIn(a3, board.pseudo_legal_moves)
        self.assertIn(a3, board.legal_moves)
        board.push(a3)
        board.pop()
        self.assertEqual(board.fen(), chess.STARTING_FEN)

    def test_castling(self):
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

        # Let white castle short.
        move = board.parse_san("O-O")
        self.assertEqual(move, chess.Move.from_uci("e1g1"))
        self.assertEqual(board.san(move), "O-O")
        self.assertIn(move, board.legal_moves)
        board.push(move)

        # Let black castle long.
        move = board.parse_san("O-O-O")
        self.assertEqual(board.san(move), "O-O-O")
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.fen(), "2kr3r/8/8/8/8/8/8/R4RK1 w - - 3 2")

        # Undo both castling moves.
        board.pop()
        board.pop()
        self.assertEqual(board.fen(), "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

        # Let white castle long.
        move = board.parse_san("O-O-O")
        self.assertEqual(board.san(move), "O-O-O")
        self.assertIn(move, board.legal_moves)
        board.push(move)

        # Let black castle short.
        move = board.parse_san("O-O")
        self.assertEqual(board.san(move), "O-O")
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.fen(), "r4rk1/8/8/8/8/8/8/2KR3R w - - 3 2")

        # Undo both castling moves.
        board.pop()
        board.pop()
        self.assertEqual(board.fen(), "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

    def test_ninesixty_castling(self):
        fen = "3r1k1r/4pp2/8/8/8/8/8/4RKR1 w Gd - 1 1"
        board = chess.Board(fen, chess960=True)

        # Let white do the king side swap.
        move = board.parse_san("O-O")
        self.assertEqual(board.san(move), "O-O")
        self.assertEqual(move.from_square, chess.F1)
        self.assertEqual(move.to_square, chess.G1)
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.shredder_fen(), "3r1k1r/4pp2/8/8/8/8/8/4RRK1 b d - 2 1")

        # Black can not castle kingside.
        self.assertNotIn(chess.Move.from_uci("e8h8"), board.legal_moves)

        # Let black castle queenside.
        move = board.parse_san("O-O-O")
        self.assertEqual(board.san(move), "O-O-O")
        self.assertEqual(move.from_square, chess.F8)
        self.assertEqual(move.to_square, chess.D8)
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.shredder_fen(), "2kr3r/4pp2/8/8/8/8/8/4RRK1 w - - 3 2")

        # Restore initial position.
        board.pop()
        board.pop()
        self.assertEqual(board.shredder_fen(), fen)

        fen = "Qr4k1/4pppp/8/8/8/8/8/R5KR w Hb - 0 1"
        board = chess.Board(fen, chess960=True)

        # White can just hop the rook over.
        move = board.parse_san("O-O")
        self.assertEqual(board.san(move), "O-O")
        self.assertEqual(move.from_square, chess.G1)
        self.assertEqual(move.to_square, chess.H1)
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.shredder_fen(), "Qr4k1/4pppp/8/8/8/8/8/R4RK1 b b - 1 1")

        # Black can not castle queenside nor kingside.
        self.assertFalse(any(board.generate_castling_moves()))

        # Restore initial position.
        board.pop()
        self.assertEqual(board.shredder_fen(), fen)

    def test_selective_castling(self):
        board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")

        # King not selected
        self.assertFalse(any(board.generate_castling_moves(chess.BB_ALL & ~board.kings)))

        # Rook on h1 not selected
        moves = board.generate_castling_moves(chess.BB_ALL, chess.BB_ALL & ~chess.BB_H1)
        self.assertEqual(len(list(moves)), 1)

    def test_castling_right_not_destroyed_bug(self):
        # A rook move from H8 to H1 was only taking whites possible castling
        # rights away.
        board = chess.Board("2r1k2r/2qbbpp1/p2pp3/1p3PP1/Pn2P3/1PN1B3/1P3QB1/1K1R3R b k - 0 22")
        board.push_san("Rxh1")
        self.assertEqual(board.epd(), "2r1k3/2qbbpp1/p2pp3/1p3PP1/Pn2P3/1PN1B3/1P3QB1/1K1R3r w - -")

    def test_invalid_castling_rights(self):
        # KQkq is not valid in this standard chess position.
        board = chess.Board("1r2k3/8/8/8/8/8/8/R3KR2 w KQkq - 0 1")
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)
        self.assertEqual(board.fen(), "1r2k3/8/8/8/8/8/8/R3KR2 w Q - 0 1")
        self.assertTrue(board.has_queenside_castling_rights(chess.WHITE))
        self.assertFalse(board.has_kingside_castling_rights(chess.WHITE))
        self.assertFalse(board.has_queenside_castling_rights(chess.BLACK))
        self.assertFalse(board.has_kingside_castling_rights(chess.BLACK))

        board = chess.Board("4k2r/8/8/8/8/8/8/R1K5 w KQkq - 0 1", chess960=True)
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)
        self.assertEqual(board.fen(), "4k2r/8/8/8/8/8/8/R1K5 w Qk - 0 1")

        board = chess.Board("1r2k3/8/1p6/8/8/5P2/8/1R2KR2 w KQkq - 0 1", chess960=True)
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)
        self.assertEqual(board.fen(), "1r2k3/8/1p6/8/8/5P2/8/1R2KR2 w KQq - 0 1")

    def test_ninesixty_different_king_and_rook_file(self):
        # Theoretically this position (with castling rights) can not be reached
        # with a series of legal moves from one of the 960 starting positions.
        # Decision: We don't care. Neither does Stockfish or lichess.org.
        fen = "1r1k1r2/5p2/8/8/8/8/3N4/R5KR b KQkq - 0 1"
        board = chess.Board(fen, chess960=True)
        self.assertEqual(board.fen(), fen)

    def test_ninesixty_prevented_castle(self):
        board = chess.Board("4k3/8/8/1b6/8/8/8/5RKR w KQ - 0 1", chess960=True)
        self.assertFalse(board.is_legal(chess.Move.from_uci("g1f1")))

    def test_insufficient_material(self):
        # Starting position.
        board = chess.Board()
        self.assertFalse(board.is_insufficient_material())

        # King vs. King + 2 bishops of the same color.
        board = chess.Board("k1K1B1B1/8/8/8/8/8/8/8 w - - 7 32")
        self.assertTrue(board.is_insufficient_material())

        # Add bishop of opposite color for the weaker side.
        board.set_piece_at(chess.B8, chess.Piece.from_symbol("b"))
        self.assertFalse(board.is_insufficient_material())

    def test_promotion_with_check(self):
        board = chess.Board("8/6P1/2p5/1Pqk4/6P1/2P1RKP1/4P1P1/8 w - - 0 1")
        board.push(chess.Move.from_uci("g7g8q"))
        self.assertTrue(board.is_check())
        self.assertEqual(board.fen(), "6Q1/8/2p5/1Pqk4/6P1/2P1RKP1/4P1P1/8 b - - 0 1")

        board = chess.Board("8/8/8/3R1P2/8/2k2K2/3p4/r7 b - - 0 82")
        board.push_san("d1=Q+")
        self.assertEqual(board.fen(), "8/8/8/3R1P2/8/2k2K2/8/r2q4 w - - 0 83")

    def test_scholars_mate(self):
        board = chess.Board()

        e4 = chess.Move.from_uci("e2e4")
        self.assertIn(e4, board.legal_moves)
        board.push(e4)

        e5 = chess.Move.from_uci("e7e5")
        self.assertIn(e5, board.legal_moves)
        board.push(e5)

        Qf3 = chess.Move.from_uci("d1f3")
        self.assertIn(Qf3, board.legal_moves)
        board.push(Qf3)

        Nc6 = chess.Move.from_uci("b8c6")
        self.assertIn(Nc6, board.legal_moves)
        board.push(Nc6)

        Bc4 = chess.Move.from_uci("f1c4")
        self.assertIn(Bc4, board.legal_moves)
        board.push(Bc4)

        Rb8 = chess.Move.from_uci("a8b8")
        self.assertIn(Rb8, board.legal_moves)
        board.push(Rb8)

        self.assertFalse(board.is_check())
        self.assertFalse(board.is_checkmate())
        self.assertFalse(board.is_game_over())
        self.assertFalse(board.is_stalemate())

        Qf7_mate = chess.Move.from_uci("f3f7")
        self.assertIn(Qf7_mate, board.legal_moves)
        board.push(Qf7_mate)

        self.assertTrue(board.is_check())
        self.assertTrue(board.is_checkmate())
        self.assertTrue(board.is_game_over())
        self.assertTrue(board.is_game_over(claim_draw=True))
        self.assertFalse(board.is_stalemate())

        self.assertEqual(board.fen(), "1rbqkbnr/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQk - 0 4")

    def test_result(self):
        # Undetermined.
        board = chess.Board()
        self.assertEqual(board.result(claim_draw=True), "*")

        # White checkmated.
        board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        self.assertEqual(board.result(claim_draw=True), "0-1")

        # Stalemate.
        board = chess.Board("7K/7P/7k/8/6q1/8/8/8 w - - 0 1")
        self.assertEqual(board.result(), "1/2-1/2")

        # Insufficient material.
        board = chess.Board("4k3/8/8/8/8/5B2/8/4K3 w - - 0 1")
        self.assertEqual(board.result(), "1/2-1/2")

        # Fiftyseven-move rule.
        board = chess.Board("4k3/8/6r1/8/8/8/2R5/4K3 w - - 369 1")
        self.assertEqual(board.result(), "1/2-1/2")

        # Fifty-move rule.
        board = chess.Board("4k3/8/6r1/8/8/8/2R5/4K3 w - - 120 1")
        self.assertEqual(board.result(), "*")
        self.assertEqual(board.result(claim_draw=True), "1/2-1/2")

    def test_san(self):
        # Castling with check.
        fen = "rnbk1b1r/ppp2pp1/5n1p/4p1B1/2P5/2N5/PP2PPPP/R3KBNR w KQ - 0 7"
        board = chess.Board(fen)
        long_castle_check = chess.Move.from_uci("e1a1")
        self.assertEqual(board.san(long_castle_check), "O-O-O+")
        self.assertEqual(board.fen(), fen)

        # En passant mate.
        fen = "6bk/7b/8/3pP3/8/8/8/Q3K3 w - d6 0 2"
        board = chess.Board(fen)
        fxe6_mate_ep = chess.Move.from_uci("e5d6")
        self.assertEqual(board.san(fxe6_mate_ep), "exd6#")
        self.assertEqual(board.fen(), fen)

        # Test disambiguation.
        fen = "N3k2N/8/8/3N4/N4N1N/2R5/1R6/4K3 w - - 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.san(chess.Move.from_uci("e1f1")), "Kf1")
        self.assertEqual(board.san(chess.Move.from_uci("c3c2")), "Rcc2")
        self.assertEqual(board.san(chess.Move.from_uci("b2c2")), "Rbc2")
        self.assertEqual(board.san(chess.Move.from_uci("a4b6")), "N4b6")
        self.assertEqual(board.san(chess.Move.from_uci("h8g6")), "N8g6")
        self.assertEqual(board.san(chess.Move.from_uci("h4g6")), "Nh4g6")
        self.assertEqual(board.fen(), fen)

        # Do not disambiguate illegal alternatives.
        fen = "8/8/8/R2nkn2/8/8/2K5/8 b - - 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.san(chess.Move.from_uci("f5e3")), "Ne3+")
        self.assertEqual(board.fen(), fen)

        # Promotion.
        fen = "7k/1p2Npbp/8/2P5/1P1r4/3b2QP/3q1pPK/2RB4 b - - 1 29"
        board = chess.Board(fen)
        self.assertEqual(board.san(chess.Move.from_uci("f2f1q")), "f1=Q")
        self.assertEqual(board.san(chess.Move.from_uci("f2f1n")), "f1=N+")
        self.assertEqual(board.fen(), fen)

    def test_lan(self):
        # Normal moves always with origin square.
        fen = "N3k2N/8/8/3N4/N4N1N/2R5/1R6/4K3 w - - 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.lan(chess.Move.from_uci("e1f1")), "Ke1-f1")
        self.assertEqual(board.lan(chess.Move.from_uci("c3c2")), "Rc3-c2")
        self.assertEqual(board.lan(chess.Move.from_uci("a4c5")), "Na4-c5")
        self.assertEqual(board.fen(), fen)

        # Normal capture.
        fen = "rnbq1rk1/ppp1bpp1/4pn1p/3p2B1/2PP4/2N1PN2/PP3PPP/R2QKB1R w KQ - 0 7"
        board = chess.Board(fen)
        self.assertEqual(board.lan(chess.Move.from_uci("g5f6")), "Bg5xf6")
        self.assertEqual(board.fen(), fen)

        # Pawn captures and moves.
        fen = "6bk/7b/8/3pP3/8/8/8/Q3K3 w - d6 0 2"
        board = chess.Board(fen)
        self.assertEqual(board.lan(chess.Move.from_uci("e5d6")), "e5xd6#")
        self.assertEqual(board.lan(chess.Move.from_uci("e5e6")), "e5-e6+")
        self.assertEqual(board.fen(), fen)

    def test_san_newline(self):
        fen = "rnbqk2r/ppppppbp/5np1/8/8/5NP1/PPPPPPBP/RNBQK2R w KQkq - 2 4"
        board = chess.Board(fen)

        with self.assertRaises(ValueError):
            board.parse_san("O-O\n")

        with self.assertRaises(ValueError):
            board.parse_san("Nc3\n")

    def test_variation_san(self):
        board = chess.Board()
        self.assertEqual('1. e4 e5 2. Nf3',
                         board.variation_san([chess.Move.from_uci(m) for m in
                                              ['e2e4', 'e7e5', 'g1f3']]))
        self.assertEqual('1. e4 e5 2. Nf3 Nc6 3. Bb5 a6',
                         board.variation_san([chess.Move.from_uci(m) for m in
                                              ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6']]))

        fen = "rn1qr1k1/1p2bppp/p3p3/3pP3/P2P1B2/2RB1Q1P/1P3PP1/R5K1 w - - 0 19"
        board = chess.Board(fen)
        variation = ['d3h7', 'g8h7', 'f3h5', 'h7g8', 'c3g3', 'e7f8', 'f4g5',
                     'e8e7', 'g5f6', 'b8d7', 'h5h6', 'd7f6', 'e5f6', 'g7g6',
                     'f6e7', 'f8e7']
        var_w = board.variation_san([chess.Move.from_uci(m) for m in variation])
        self.assertEqual(("19. Bxh7+ Kxh7 20. Qh5+ Kg8 21. Rg3 Bf8 22. Bg5 Re7 "
                          "23. Bf6 Nd7 24. Qh6 Nxf6 25. exf6 g6 26. fxe7 Bxe7"),
                         var_w)
        self.assertEqual(fen, board.fen(), msg="Board unchanged by variation_san")
        board.push(chess.Move.from_uci(variation.pop(0)))
        var_b = board.variation_san([chess.Move.from_uci(m) for m in variation])
        self.assertEqual(("19...Kxh7 20. Qh5+ Kg8 21. Rg3 Bf8 22. Bg5 Re7 "
                          "23. Bf6 Nd7 24. Qh6 Nxf6 25. exf6 g6 26. fxe7 Bxe7"),
                         var_b)

        illegal_variation = ['d3h7', 'g8h7', 'f3h6', 'h7g8']
        board = chess.Board(fen)
        with self.assertRaises(ValueError) as err:
            board.variation_san([chess.Move.from_uci(m) for m in illegal_variation])
        message = str(err.exception)
        self.assertIn('illegal move', message.lower(),
                      msg="Error [{0}] mentions illegal move".format(message))
        self.assertIn('f3h6', message,
                      msg="Illegal move f3h6 appears in message [{0}]".format(message))

    def test_move_stack_usage(self):
        board = chess.Board()
        board.push_uci("d2d4")
        board.push_uci("d7d5")
        board.push_uci("g1f3")
        board.push_uci("c8f5")
        board.push_uci("e2e3")
        board.push_uci("e7e6")
        board.push_uci("f1d3")
        board.push_uci("f8d6")
        board.push_uci("e1h1")
        san = chess.Board().variation_san(board.move_stack)
        self.assertEqual(san, "1. d4 d5 2. Nf3 Bf5 3. e3 e6 4. Bd3 Bd6 5. O-O")

    def test_is_legal_move(self):
        fen = "3k4/6P1/7P/8/K7/8/8/4R3 w - - 0 1"
        board = chess.Board(fen)

        # Legal moves: Rg1, g8=R+.
        self.assertIn(chess.Move.from_uci("e1g1"), board.legal_moves)
        self.assertIn(chess.Move.from_uci("g7g8r"), board.legal_moves)

        # Impossible promotion: Kb5, h7.
        self.assertNotIn(chess.Move.from_uci("a5b5q"), board.legal_moves)
        self.assertNotIn(chess.Move.from_uci("h6h7n"), board.legal_moves)

        # Missing promotion.
        self.assertNotIn(chess.Move.from_uci("g7g8"), board.legal_moves)

        # Promote to pawn or king.
        self.assertFalse(board.is_legal(chess.Move.from_uci("g7g8p")))
        self.assertFalse(board.is_pseudo_legal(chess.Move.from_uci("g7g8p")))
        self.assertFalse(board.is_legal(chess.Move.from_uci("g7g8k")))
        self.assertFalse(board.is_pseudo_legal(chess.Move.from_uci("g7g8k")))

        self.assertEqual(board.fen(), fen)

    def test_move_count(self):
        board = chess.Board("1N2k3/P7/8/8/3n4/8/2PP4/R3K2R w KQ - 0 1")
        self.assertEqual(board.pseudo_legal_moves.count(), 8 + 4 + 3 + 2 + 1 + 6 + 9)

    def test_polyglot(self):
        # Test polyglot compability using test data from
        # http://hardy.uhasselt.be/Toga/book_format.html. Forfeiting castling
        # rights should not reset the half-move counter, though.

        board = chess.Board()
        self.assertEqual(board.fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x463b96181691fc9c)

        board.push_san("e4")
        self.assertEqual(board.fen(), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x823c9b50fd114196)

        board.push_san("d5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x0756b94461c50fb0)

        board.push_san("e5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x662fafb965db29d4)

        board.push_san("f5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x22a48b5a8e47ff78)

        board.push_san("Ke2")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR b kq - 1 3")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x652a607ca3f242c1)

        board.push_san("Kf7")
        self.assertEqual(board.fen(), "rnbq1bnr/ppp1pkpp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR w - - 2 4")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x00fdd303c946bdd9)

        board = chess.Board()
        board.push_san("a4")
        board.push_san("b5")
        board.push_san("h4")
        board.push_san("b4")
        board.push_san("c4")
        self.assertEqual(board.fen(), "rnbqkbnr/p1pppppp/8/8/PpP4P/8/1P1PPPP1/RNBQKBNR b KQkq c3 0 3")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x3c8123ea7b067637)

        board.push_san("bxc3")
        board.push_san("Ra3")
        self.assertEqual(board.fen(), "rnbqkbnr/p1pppppp/8/8/P6P/R1p5/1P1PPPP1/1NBQKBNR b Kkq - 1 4")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x5c3f9b829b279560)

    def test_castling_move_generation_bug(self):
        # Specific test position right after castling.
        fen = "rnbqkbnr/2pp1ppp/8/4p3/2BPP3/P1N2N2/PB3PPP/2RQ1RK1 b kq - 1 10"
        board = chess.Board(fen)
        illegal_move = chess.Move.from_uci("g1g2")
        self.assertNotIn(illegal_move, board.legal_moves)
        self.assertNotIn(illegal_move, list(board.legal_moves))
        self.assertNotIn(illegal_move, board.pseudo_legal_moves)
        self.assertNotIn(illegal_move, list(board.pseudo_legal_moves))

        # Make a move.
        board.push_san("exd4")

        # Already castled short, can not castle long.
        illegal_move = chess.Move.from_uci("e1c1")
        self.assertNotIn(illegal_move, board.pseudo_legal_moves)
        self.assertNotIn(illegal_move, board.generate_pseudo_legal_moves())
        self.assertNotIn(illegal_move, board.legal_moves)
        self.assertNotIn(illegal_move, list(board.legal_moves))

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
        board = chess.Board(fen)

        # Make a move.
        board.push_san("Re2")

        # Check for the illegal move.
        illegal_move = chess.Move.from_uci("e8f8")
        self.assertNotIn(illegal_move, board.pseudo_legal_moves)
        self.assertNotIn(illegal_move, board.generate_pseudo_legal_moves())
        self.assertNotIn(illegal_move, board.legal_moves)
        self.assertNotIn(illegal_move, board.generate_legal_moves())

        # Generate all pseudo legal moves.
        for a in board.pseudo_legal_moves:
            board.push(a)
            board.pop()

        # Unmake the move.
        board.pop()

        # Check that board is still consistent.
        self.assertEqual(board.fen(), fen)

    def test_stateful_move_generation_bug(self):
        board = chess.Board("r1b1k3/p2p1Nr1/n2b3p/3pp1pP/2BB1p2/P3P2R/Q1P3P1/R3K1N1 b Qq - 0 1")
        count = 0
        for move in board.legal_moves:
            board.push(move)
            list(board.generate_legal_moves())
            count += 1
            board.pop()

        self.assertEqual(count, 26)

    def test_ninesixty_castling_bug(self):
        board = chess.Board("4r3/3k4/8/8/8/8/q5PP/1R1KR3 w Q - 2 2", chess960=True)
        move = chess.Move.from_uci("d1b1")
        self.assertTrue(board.is_castling(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_legal_moves())
        self.assertTrue(board.is_legal(move))
        self.assertEqual(board.parse_san("O-O-O+"), move)
        self.assertEqual(board.san(move), "O-O-O+")

    def test_equality(self):
        self.assertEqual(chess.Board(), chess.Board())
        self.assertFalse(chess.Board() != chess.Board())

        a = chess.Board()
        a.push_san("d4")
        b = chess.Board()
        b.push_san("d3")
        self.assertNotEqual(a, b)
        self.assertFalse(a == b)

    def test_status(self):
        board = chess.Board()
        self.assertEqual(board.status(), chess.STATUS_VALID)
        self.assertTrue(board.is_valid())

        board.remove_piece_at(chess.H1)
        self.assertTrue(board.status() & chess.STATUS_BAD_CASTLING_RIGHTS)

        board.remove_piece_at(chess.E8)
        self.assertTrue(board.status() & chess.STATUS_NO_BLACK_KING)

        # The en passant square should be set even if no capture is actually
        # possible.
        board = chess.Board()
        board.push_san("e4")
        self.assertEqual(board.ep_square, chess.E3)
        self.assertEqual(board.status(), chess.STATUS_VALID)

        # But there must indeed be a pawn there.
        board.remove_piece_at(chess.E4)
        self.assertEqual(board.status(), chess.STATUS_INVALID_EP_SQUARE)

        # King must be between the two rooks.
        board = chess.Board("2rrk3/8/8/8/8/8/3PPPPP/2RK4 w cd - 0 1")
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)

        # Generally valid position, but not valid standard chess position due
        # to non-standard castling rights. Chess960 start position #0.
        board = chess.Board("bbqnnrkr/pppppppp/8/8/8/8/PPPPPPPP/BBQNNRKR w KQkq - 0 1", chess960=True)
        self.assertEqual(board.status(), chess.STATUS_VALID)
        board = chess.Board("bbqnnrkr/pppppppp/8/8/8/8/PPPPPPPP/BBQNNRKR w KQkq - 0 1", chess960=False)
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)

    def test_one_king_movegen(self):
        board = chess.Board.empty()
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        self.assertFalse(board.is_valid())
        self.assertEqual(board.legal_moves.count(), 3)
        self.assertEqual(board.pseudo_legal_moves.count(), 3)
        board.push_san("Kb1")
        self.assertEqual(board.legal_moves.count(), 0)
        self.assertEqual(board.pseudo_legal_moves.count(), 0)
        board.push_san("--")
        self.assertEqual(board.legal_moves.count(), 5)
        self.assertEqual(board.pseudo_legal_moves.count(), 5)

    def test_epd(self):
        # Create an EPD with a move and a string.
        board = chess.Board("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - 0 1")
        epd = board.epd(bm=chess.Move(chess.D6, chess.D1), id="BK.01")
        self.assertIn(epd, [
            "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";",
            "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - id \"BK.01\"; bm Qd1+;"])

        # Create an EPD with a noop.
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        self.assertEqual(board.epd(noop=None), "4k3/8/8/8/8/8/8/4K3 w - - noop;")

        # Create an EPD with a variation.
        board = chess.Board("k7/8/8/8/8/8/4PPPP/4K1NR w K - 0 1")
        epd = board.epd(pv=[
            chess.Move.from_uci("g1f3"),  # Nf3
            chess.Move.from_uci("a8a7"),  # Ka7
            chess.Move.from_uci("e1h1"),  # O-O
        ])
        self.assertEqual(epd, "k7/8/8/8/8/8/4PPPP/4K1NR w K - pv Nf3 Ka7 O-O;")

        # Create an EPD with a set of moves.
        board = chess.Board("8/8/8/4k3/8/1K6/8/8 b - - 0 1")
        epd = board.epd(bm=[
            chess.Move.from_uci("e5e6"),  # Ke6
            chess.Move.from_uci("e5e4"),  # Ke4
        ])
        self.assertEqual(epd, "8/8/8/4k3/8/1K6/8/8 b - - bm Ke6 Ke4;")

        # Test loading an EPD.
        board = chess.Board()
        operations = board.set_epd("r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - bm f4; id \"BK.24\";")
        self.assertEqual(board.fen(), "r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - 0 1")
        self.assertIn(chess.Move(chess.F2, chess.F4), operations["bm"])
        self.assertEqual(operations["id"], "BK.24")

        # Test loading an EPD with half counter operations.
        board = chess.Board()
        operations = board.set_epd("4k3/8/8/8/8/8/8/4K3 b - - fmvn 17; hmvc 13")
        self.assertEqual(board.fen(), "4k3/8/8/8/8/8/8/4K3 b - - 13 17")
        self.assertEqual(operations["fmvn"], 17)
        self.assertEqual(operations["hmvc"], 13)

        # Test context of parsed SANs.
        board = chess.Board()
        operations = board.set_epd("4k3/8/8/2N5/8/8/8/4K3 w - - test Ne4")
        self.assertEqual(operations["test"], chess.Move(chess.C5, chess.E4))

        # Test parsing EPD with a set of moves.
        board = chess.Board()
        operations = board.set_epd("4k3/8/3QK3/8/8/8/8/8 w - - bm Qe7# Qb8#;")
        self.assertEqual(board.fen(), "4k3/8/3QK3/8/8/8/8/8 w - - 0 1")
        self.assertEqual(len(operations["bm"]), 2)
        self.assertIn(chess.Move.from_uci("d6b8"), operations["bm"])
        self.assertIn(chess.Move.from_uci("d6e7"), operations["bm"])

        # Test parsing EPD with a stack of moves.
        board = chess.Board()
        operations = board.set_epd("6k1/1p6/6K1/8/8/8/8/7Q w - - pv Qh7+ Kf8 Qf7#;")
        self.assertEqual(len(operations["pv"]), 3)
        self.assertEqual(operations["pv"][0], chess.Move.from_uci("h1h7"))
        self.assertEqual(operations["pv"][1], chess.Move.from_uci("g8f8"))
        self.assertEqual(operations["pv"][2], chess.Move.from_uci("h7f7"))

    def test_null_moves(self):
        self.assertEqual(str(chess.Move.null()), "0000")
        self.assertEqual(chess.Move.null().uci(), "0000")
        self.assertFalse(chess.Move.null())

        fen = "rnbqkbnr/ppp1pppp/8/2Pp4/8/8/PP1PPPPP/RNBQKBNR w KQkq d6 0 2"
        board = chess.Board(fen)

        self.assertEqual(chess.Move.from_uci("0000"), board.push_san("--"))
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/2Pp4/8/8/PP1PPPPP/RNBQKBNR b KQkq - 1 2")

        self.assertEqual(chess.Move.null(), board.pop())
        self.assertEqual(board.fen(), fen)

    def test_attackers(self):
        board = chess.Board("r1b1k2r/pp1n1ppp/2p1p3/q5B1/1b1P4/P1n1PN2/1P1Q1PPP/2R1KB1R b Kkq - 3 10")

        attackers = board.attackers(chess.WHITE, chess.C3)
        self.assertEqual(len(attackers), 3)
        self.assertIn(chess.C1, attackers)
        self.assertIn(chess.D2, attackers)
        self.assertIn(chess.B2, attackers)
        self.assertNotIn(chess.D4, attackers)
        self.assertNotIn(chess.E1, attackers)

    def test_en_passant_attackers(self):
        board = chess.Board("4k3/8/8/8/4pPp1/8/8/4K3 b - f3 0 1")

        # Attacking the en passant square.
        attackers = board.attackers(chess.BLACK, chess.F3)
        self.assertEqual(len(attackers), 2)
        self.assertIn(chess.E4, attackers)
        self.assertIn(chess.G4, attackers)

        # Not attacking the pawn directly.
        attackers = board.attackers(chess.BLACK, chess.F4)
        self.assertEqual(attackers, chess.BB_VOID)

    def test_attacks(self):
        board = chess.Board("5rk1/p5pp/2p3p1/1p1pR3/3P2P1/2N5/PP3n2/2KB4 w - - 1 26")

        attacks = board.attacks(chess.E5)
        self.assertEqual(len(attacks), 11)
        self.assertIn(chess.D5, attacks)
        self.assertIn(chess.E1, attacks)
        self.assertIn(chess.F5, attacks)
        self.assertNotIn(chess.E5, attacks)
        self.assertNotIn(chess.C5, attacks)
        self.assertNotIn(chess.F4, attacks)

        self.assertFalse(board.attacks(chess.G1))

    def test_clear(self):
        board = chess.Board()
        board.clear()

        self.assertEqual(board.turn, chess.WHITE)
        self.assertEqual(board.fullmove_number, 1)
        self.assertEqual(board.halfmove_clock, 0)
        self.assertEqual(board.castling_rights, chess.BB_VOID)
        self.assertFalse(board.ep_square)

        self.assertFalse(board.piece_at(chess.E1))
        self.assertEqual(chess.popcount(board.occupied), 0)

    def test_threefold_repetition(self):
        board = chess.Board()

        # Go back and forth with the nights to reach the starting position
        # for a second time.
        self.assertFalse(board.can_claim_threefold_repetition())
        board.push_san("Nf3")
        self.assertFalse(board.can_claim_threefold_repetition())
        board.push_san("Nf6")
        self.assertFalse(board.can_claim_threefold_repetition())
        board.push_san("Ng1")
        self.assertFalse(board.can_claim_threefold_repetition())
        board.push_san("Ng8")

        # Once more.
        self.assertFalse(board.can_claim_threefold_repetition())
        board.push_san("Nf3")
        self.assertFalse(board.can_claim_threefold_repetition())
        board.push_san("Nf6")
        self.assertFalse(board.can_claim_threefold_repetition())
        board.push_san("Ng1")

        # Now black can go back to the starting position (thus reaching it a
        # third time.)
        self.assertTrue(board.can_claim_threefold_repetition())
        board.push_san("Ng8")

        # They indee do it. Also white can now claim.
        self.assertTrue(board.can_claim_threefold_repetition())

        # But not after a different move.
        board.push_san("e4")
        self.assertFalse(board.can_claim_threefold_repetition())

        # Undo moves and check if everything works backwards.
        board.pop()  # e4
        self.assertTrue(board.can_claim_threefold_repetition())
        board.pop()  # Ng8
        self.assertTrue(board.can_claim_threefold_repetition())
        while board.move_stack:
            board.pop()
            self.assertFalse(board.can_claim_threefold_repetition())

    def test_fivefold_repetition(self):
        fen = "rnbq1rk1/ppp3pp/3bpn2/3p1p2/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 3 7"
        board = chess.Board(fen)

        # Repeat the position up to the fourth time.
        for i in range(3):
            board.push_san("Be2")
            self.assertFalse(board.is_fivefold_repetition())
            board.push_san("Ne4")
            self.assertFalse(board.is_fivefold_repetition())
            board.push_san("Bd3")
            self.assertFalse(board.is_fivefold_repetition())
            board.push_san("Nf6")
            self.assertEqual(board.fen().split()[0], fen.split()[0])
            self.assertFalse(board.is_fivefold_repetition())
            self.assertFalse(board.is_game_over())

        # Repeat it once more. Now it is a five-fold repetition.
        board.push_san("Be2")
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Ne4")
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Bd3")
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Nf6")
        self.assertEqual(board.fen().split()[0], fen.split()[0])
        self.assertTrue(board.is_fivefold_repetition())
        self.assertTrue(board.is_game_over())

        # It is also a threefold repetition.
        self.assertTrue(board.can_claim_threefold_repetition())

        # Now no longer.
        board.push_san("Qc2")
        board.push_san("Qd7")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Qd2")
        board.push_san("Qe7")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_fivefold_repetition())

        # Give the possibility to repeat.
        board.push_san("Qd1")
        self.assertFalse(board.is_fivefold_repetition())
        self.assertFalse(board.is_game_over())
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertTrue(board.is_game_over(claim_draw=True))

        # Do in fact repeat.
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Qd8")

        # This is a threefold repetition but not a fivefold repetition, because
        # consecutive moves are required for that.
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_fivefold_repetition())
        self.assertEqual(board.fen().split()[0], fen.split()[0])

    def test_fifty_moves(self):
        # Test positions from Timman - Lutz (1995).
        board = chess.Board()
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("8/5R2/8/r2KB3/6k1/8/8/8 w - - 19 79")
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("8/8/6r1/4B3/8/4K2k/5R2/8 b - - 68 103")
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("6R1/7k/8/8/1r3B2/5K2/8/8 w - - 99 119")
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("8/7k/8/6R1/1r3B2/5K2/8/8 b - - 100 119")
        self.assertTrue(board.can_claim_fifty_moves())
        board = chess.Board("8/7k/8/1r3KR1/5B2/8/8/8 w - - 105 122")
        self.assertTrue(board.can_claim_fifty_moves())

        # Once checkmated it is too late to claim.
        board = chess.Board("k7/8/NKB5/8/8/8/8/8 b - - 105 176")
        self.assertFalse(board.can_claim_fifty_moves())

        # A stalemate is a draw, but you can not and do not need to claim it by
        # the fifty move rule.
        board = chess.Board("k7/3N4/1K6/1B6/8/8/8/8 b - - 99 1")
        self.assertTrue(board.is_stalemate())
        self.assertTrue(board.is_game_over())
        self.assertFalse(board.can_claim_fifty_moves())
        self.assertFalse(board.can_claim_draw())

    def test_promoted_comparison(self):
        board = chess.Board()
        board.set_fen("5R2/3P4/8/8/7r/7r/7k/K7 w - - 0 1")
        board.push_san("d8=R")

        same_board = chess.Board(board.fen())
        self.assertEqual(board, same_board)

    def test_ep_legality(self):
        move = chess.Move.from_uci("h5g6")
        board = chess.Board("rnbqkbnr/pppppp2/7p/6pP/8/8/PPPPPPP1/RNBQKBNR w KQkq g6 0 3")
        self.assertTrue(board.is_legal(move))
        board.push_san("Nf3")
        self.assertFalse(board.is_legal(move))
        board.push_san("Nf6")
        self.assertFalse(board.is_legal(move))

        move = chess.Move.from_uci("c4d3")
        board = chess.Board("rnbqkbnr/pp1ppppp/8/8/2pP4/2P2N2/PP2PPPP/RNBQKB1R b KQkq d3 0 3")
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
            chess.Move(chess.E5, chess.E4),
        ]

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
            "r2n3r/1bNk2pp/6P1/pP3p2/3pPqnP/1P1P1p1R/2P3B1/Q1B1bKN1 b - e3 0 1",
        ]

        for sample_fen in sample_fens:
            board = chess.Board(sample_fen)

            pseudo_legal_moves = list(board.generate_pseudo_legal_moves())

            # Ensure that all moves generated as pseudo legal pass the pseudo-
            # legality check.
            for move in pseudo_legal_moves:
                self.assertTrue(board.is_pseudo_legal(move))

            # Check that moves not generated as pseudo legal do not pass the
            # pseudo legality check.
            for move in sample_moves:
                if move not in pseudo_legal_moves:
                    self.assertFalse(board.is_pseudo_legal(move))

    def test_pseudo_legal_castling_masks(self):
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        kingside = chess.Move.from_uci("e1g1")
        queenside = chess.Move.from_uci("e1c1")

        moves = list(board.generate_pseudo_legal_moves())
        self.assertIn(kingside, moves)
        self.assertIn(queenside, moves)

        moves = list(board.generate_pseudo_legal_moves(from_mask=chess.BB_RANK_2))
        self.assertEqual(moves, [])

        moves = list(board.generate_pseudo_legal_moves(to_mask=chess.BB_A1))
        self.assertNotIn(kingside, moves)
        self.assertIn(queenside, moves)

    def test_pieces(self):
        board = chess.Board()
        king = board.pieces(chess.KING, chess.WHITE)
        self.assertIn(chess.E1, king)
        self.assertEqual(len(king), 1)

    def test_string_conversion(self):
        board = chess.Board("7k/1p1qn1b1/pB1p1n2/3Pp3/4Pp1p/2QN1B2/PP4PP/6K1 w - - 0 28")

        self.assertEqual(str(board), textwrap.dedent(u"""\
            . . . . . . . k
            . p . q n . b .
            p B . p . n . .
            . . . P p . . .
            . . . . P p . p
            . . Q N . B . .
            P P . . . . P P
            . . . . . . K ."""))

        self.assertEqual(board.unicode(), textwrap.dedent(u"""\
            · · · · · · · ♚
            · ♟ · ♛ ♞ · ♝ ·
            ♟ ♗ · ♟ · ♞ · ·
            · · · ♙ ♟ · · ·
            · · · · ♙ ♟ · ♟
            · · ♕ ♘ · ♗ · ·
            ♙ ♙ · · · · ♙ ♙
            · · · · · · ♔ ·"""))

    def test_move_info(self):
        board = chess.Board("r1bqkb1r/p3np2/2n1p2p/1p4pP/2pP4/4PQ1N/1P2BPP1/RNB1K2R w KQkq g6 0 11")

        self.assertTrue(board.is_capture(board.parse_san("Qxf7+")))
        self.assertFalse(board.is_en_passant(board.parse_san("Qxf7+")))
        self.assertFalse(board.is_castling(board.parse_san("Qxf7+")))

        self.assertTrue(board.is_capture(board.parse_san("hxg6")))
        self.assertTrue(board.is_en_passant(board.parse_san("hxg6")))
        self.assertFalse(board.is_castling(board.parse_san("hxg6")))

        self.assertFalse(board.is_capture(board.parse_san("b3")))
        self.assertFalse(board.is_en_passant(board.parse_san("b3")))
        self.assertFalse(board.is_castling(board.parse_san("b3")))

        self.assertFalse(board.is_capture(board.parse_san("Ra6")))
        self.assertFalse(board.is_en_passant(board.parse_san("Ra6")))
        self.assertFalse(board.is_castling(board.parse_san("Ra6")))

        self.assertFalse(board.is_capture(board.parse_san("O-O")))
        self.assertFalse(board.is_en_passant(board.parse_san("O-O")))
        self.assertTrue(board.is_castling(board.parse_san("O-O")))

    def test_pin(self):
        board = chess.Board("rnb1k1nr/2pppppp/3P4/8/1b5q/8/PPPNPBPP/RNBQKB1R w KQkq - 0 1")
        self.assertTrue(board.is_pinned(chess.WHITE, chess.F2))
        self.assertTrue(board.is_pinned(chess.WHITE, chess.D2))
        self.assertFalse(board.is_pinned(chess.WHITE, chess.E1))
        self.assertFalse(board.is_pinned(chess.BLACK, chess.H4))
        self.assertFalse(board.is_pinned(chess.BLACK, chess.E8))

        self.assertEqual(board.pin(chess.WHITE, chess.B1), chess.BB_ALL)

        self.assertEqual(board.pin(chess.WHITE, chess.F2), chess.BB_E1 | chess.BB_F2 | chess.BB_G3 | chess.BB_H4)

        self.assertEqual(board.pin(chess.WHITE, chess.D2), chess.BB_E1 | chess.BB_D2 | chess.BB_C3 | chess.BB_B4 | chess.BB_A5)

    def test_pin_in_check(self):
        # The knight on the eighth rank is on the outer side of the rank attack.
        board = chess.Board("1n1R2k1/2b1qpp1/p3p2p/1p6/1P2Q2P/4PNP1/P4PB1/6K1 b - - 0 1")
        self.assertFalse(board.is_pinned(chess.BLACK, chess.B8))

        # The empty square e8 would be considered pinned.
        self.assertTrue(board.is_pinned(chess.BLACK, chess.E8))

    def test_impossible_en_passant(self):
        # Not a pawn there.
        board = chess.Board("1b1b4/8/b1P5/2kP4/8/2b4K/8/8 w - c6 0 1")
        self.assertTrue(board.status() & chess.STATUS_INVALID_EP_SQUARE)

        # Sixth rank square not empty.
        board = chess.Board("5K2/8/2pp2Pp/2PP4/P5Pp/2pP1Ppp/P6p/7k b - g3 0 1")
        self.assertTrue(board.status() & chess.STATUS_INVALID_EP_SQUARE)

        # Seventh rank square not empty.
        board = chess.Board("8/7k/8/7p/8/8/8/K7 w - h6 0 1")
        self.assertTrue(board.status() & chess.STATUS_INVALID_EP_SQUARE)

    def test_horizontally_skewered_en_passant(self):
        # Horizontal pin. Non evasion.
        board = chess.Board("8/8/8/r2Pp2K/8/8/4k3/8 w - e6 0 1")
        move = chess.Move.from_uci("d5e6")
        self.assertEqual(board.status(), chess.STATUS_VALID)
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertFalse(board.is_legal(move))
        self.assertNotIn(move, board.generate_legal_moves())
        self.assertNotIn(move, board.generate_legal_ep())

    def test_diagonally_skewered_en_passant(self):
        # The capturing pawn is still blocking the diagonal.
        board = chess.Board("2b1r2r/8/5P1k/2p1pP2/5R1P/6PK/4q3/4R3 w - e6 0 1")
        move = chess.Move.from_uci("f5e6")
        self.assertIn(move, board.generate_legal_ep())
        self.assertIn(move, board.generate_legal_moves())

        # Regarding the following positions:
        # Note that the positions under test can not be reached by a sequence
        # of legal moves. The last move must have been a double pawn move,
        # but then the king would have been in check already.

        # Diagonal attack uncovered. Evasion try.
        board = chess.Board("8/8/8/5k2/4Pp2/8/2B5/4K3 b - e3 0 1")
        move = chess.Move.from_uci("f4e3")
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertFalse(board.is_legal(move))
        self.assertNotIn(move, board.generate_legal_moves())
        self.assertNotIn(move, board.generate_legal_ep())

        # Diagonal attack uncovered. Non-evasion.
        board = chess.Board("8/8/8/7B/6Pp/8/4k2K/3r4 b - g3 0 1")
        move = chess.Move.from_uci("h4g3")
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertFalse(board.is_legal(move))
        self.assertNotIn(move, board.generate_legal_moves())
        self.assertNotIn(move, board.generate_legal_ep())

    def test_file_pinned_en_passant(self):
        board = chess.Board("8/5K2/8/3k4/3pP3/8/8/3R4 b - e3 0 1")
        move = chess.Move.from_uci("d4e3")
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertFalse(board.is_legal(move))
        self.assertNotIn(move, board.generate_legal_moves())
        self.assertNotIn(move, board.generate_legal_ep())

    def test_en_passant_evasion(self):
        board = chess.Board("8/8/8/2k5/2pP4/8/4K3/8 b - d3 0 1")
        move = chess.Move.from_uci("c4d3")
        self.assertEqual(move, board.parse_san("cxd3"))
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertTrue(board.is_legal(move))
        self.assertIn(move, board.generate_legal_moves())
        self.assertIn(move, board.generate_legal_ep())

    def test_capture_generation(self):
        board = chess.Board("3q1rk1/ppp1p1pp/4b3/3pPp2/3P4/1K1n4/PPQ2PPP/3b1BNR w - f6 0 1")

        # Fully legal captures.
        lc = list(board.generate_legal_captures())
        self.assertIn(board.parse_san("Qxd1"), lc)
        self.assertIn(board.parse_san("exf6"), lc)  # En passant.
        self.assertIn(board.parse_san("Bxd3"), lc)
        self.assertEqual(len(lc), 3)

        plc = list(board.generate_pseudo_legal_captures())
        self.assertIn(board.parse_san("Qxd1"), plc)
        self.assertIn(board.parse_san("exf6"), plc)  # En passant.
        self.assertIn(board.parse_san("Bxd3"), plc)
        self.assertIn(chess.Move.from_uci("c2c7"), plc)
        self.assertIn(chess.Move.from_uci("c2d3"), plc)
        self.assertEqual(len(plc), 5)

    def test_from_chess960_pos(self):
        board = chess.Board.from_chess960_pos(909)
        self.assertTrue(board.chess960)
        self.assertEqual(board.fen(), "rkqbrnbn/pppppppp/8/8/8/8/PPPPPPPP/RKQBRNBN w KQkq - 0 1")

    def test_mirror(self):
        board = chess.Board("r1bq1r2/pp2n3/4N2k/3pPppP/1b1n2Q1/2N5/PP3PP1/R1B1K2R w KQ g6 0 15")
        mirrored = chess.Board("r1b1k2r/pp3pp1/2n5/1B1N2q1/3PpPPp/4n2K/PP2N3/R1BQ1R2 b kq g3 0 15")
        self.assertEqual(board.mirror(), mirrored)


class LegalMoveGeneratorTestCase(unittest.TestCase):

    def test_list_conversion(self):
        self.assertEqual(len(list(chess.Board().legal_moves)), 20)

    def test_nonzero(self):
        self.assertTrue(chess.Board().legal_moves)

        caro_kann_mate = chess.Board("r1bqkb1r/pp1npppp/2pN1n2/8/3P4/8/PPP1QPPP/R1B1KBNR b KQkq - 4 6")
        self.assertFalse(caro_kann_mate.legal_moves)

    def test_string_conversion(self):
        board = chess.Board("r3k1nr/ppq1pp1p/2p3p1/8/1PPR4/2N5/P3QPPP/5RK1 b kq b3 0 16")

        self.assertIn("Qxh2+", str(board.legal_moves))
        self.assertIn("Qxh2+", repr(board.legal_moves))

        self.assertIn("Qxh2+", str(board.pseudo_legal_moves))
        self.assertIn("Qxh2+", repr(board.pseudo_legal_moves))
        self.assertIn("e8d7", str(board.pseudo_legal_moves))
        self.assertIn("e8d7", repr(board.pseudo_legal_moves))

    def test_traverse_once(self):
        class MockBoard(object):
            def __init__(self):
                self.traversals = 0

            def generate_legal_moves(self):
                self.traversals += 1
                return
                yield

        board = MockBoard()
        gen = chess.LegalMoveGenerator(board)
        _ = list(gen)
        self.assertEqual(board.traversals, 1)


class BaseBoardTestCase(unittest.TestCase):

    def test_set_chess960_pos(self):
        board = chess.BaseBoard()

        board.set_chess960_pos(0)
        self.assertEqual(board.board_fen(), "bbqnnrkr/pppppppp/8/8/8/8/PPPPPPPP/BBQNNRKR")
        self.assertEqual(board.chess960_pos(), 0)

        board.set_chess960_pos(631)
        self.assertEqual(board.board_fen(), "rnbkqrnb/pppppppp/8/8/8/8/PPPPPPPP/RNBKQRNB")
        self.assertEqual(board.chess960_pos(), 631)

        board.set_chess960_pos(518)
        self.assertEqual(board.board_fen(), chess.STARTING_BOARD_FEN)
        self.assertEqual(board.chess960_pos(), 518)

        board.set_chess960_pos(959)
        self.assertEqual(board.board_fen(), "rkrnnqbb/pppppppp/8/8/8/8/PPPPPPPP/RKRNNQBB")
        self.assertEqual(board.chess960_pos(), 959)

    def test_set_piece_map(self):
        a = chess.BaseBoard.empty()
        b = chess.BaseBoard()
        a.set_piece_map(b.piece_map())
        self.assertEqual(a, b)
        a.set_piece_map({})
        self.assertNotEqual(a, b)


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
        self.assertEqual(list(bb), [chess.G7, chess.G8])

    def test_reversed(self):
        bb = chess.SquareSet(chess.BB_A1 | chess.BB_B1 | chess.BB_A7 | chess.BB_E1)
        self.assertEqual(list(reversed(bb)), [chess.A7, chess.E1, chess.B1, chess.A1])

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

    def test_immutable_set_operations(self):
        self.assertFalse(chess.SquareSet(chess.BB_A1).issubset(chess.BB_RANK_1))
        self.assertTrue(chess.SquareSet(chess.BB_RANK_1).issubset(chess.BB_A1))

        self.assertTrue(chess.SquareSet(chess.BB_A1).issuperset(chess.BB_RANK_1))
        self.assertFalse(chess.SquareSet(chess.BB_RANK_1).issuperset(chess.BB_A1))

        self.assertEqual(chess.SquareSet(chess.BB_A1).union(chess.BB_FILE_A), chess.BB_FILE_A)

        self.assertEqual(chess.SquareSet(chess.BB_A1).intersection(chess.BB_A2), chess.BB_VOID)

        self.assertEqual(chess.SquareSet(chess.BB_A1).difference(chess.BB_A2), chess.BB_A1)

        self.assertEqual(chess.SquareSet(chess.BB_A1).symmetric_difference(chess.BB_A2), chess.BB_A1 | chess.BB_A2)

        self.assertEqual(chess.SquareSet(chess.BB_C5).copy(), chess.BB_C5)

    def test_mutable_set_operations(self):
        squares = chess.SquareSet(chess.BB_A1)
        squares.update(chess.BB_FILE_H)
        self.assertEqual(squares, chess.BB_A1 | chess.BB_FILE_H)

        squares.intersection_update(chess.BB_RANK_8)
        self.assertEqual(squares, chess.BB_H8)

        squares.difference_update(chess.BB_A1)
        self.assertEqual(squares, chess.BB_H8)

        squares.symmetric_difference_update(chess.BB_A1)
        self.assertEqual(squares, chess.BB_A1 | chess.BB_H8)

        squares.add(chess.A3)
        self.assertEqual(squares, chess.BB_A1 | chess.BB_A3 | chess.BB_H8)

        squares.remove(chess.H8)
        self.assertEqual(squares, chess.BB_A1 | chess.BB_A3)

        with self.assertRaises(KeyError):
            squares.remove(chess.H8)

        squares.discard(chess.H8)

        squares.discard(chess.A1)
        self.assertEqual(squares, chess.BB_A3)

        squares.clear()
        self.assertEqual(squares, chess.BB_VOID)

        with self.assertRaises(KeyError):
            squares.pop()

        squares.add(chess.C7)
        self.assertEqual(squares.pop(), chess.C7)
        self.assertEqual(squares, chess.BB_VOID)

    def test_from_square(self):
        self.assertEqual(chess.SquareSet.from_square(chess.H5), chess.BB_H5)
        self.assertEqual(chess.SquareSet.from_square(chess.C2), chess.BB_C2)

    def test_carry_rippler(self):
        self.assertEqual(sum(1 for _ in chess.SquareSet(chess.BB_D1).carry_rippler()), 2 ** 1)
        self.assertEqual(sum(1 for _ in chess.SquareSet(chess.BB_FILE_B).carry_rippler()), 2 ** 8)

    def test_mirror(self):
        self.assertEqual(chess.SquareSet(0xa209000004a600).mirror(), 0xa604000009a200)


class PolyglotTestCase(unittest.TestCase):

    def test_performance_bin(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            pos = chess.Board()

            e4 = next(book.find_all(pos))
            self.assertEqual(e4.move(), pos.parse_san("e4"))
            pos.push(e4.move())

            e5 = next(book.find_all(pos))
            self.assertEqual(e5.move(), pos.parse_san("e5"))
            pos.push(e5.move())

    def test_mainline(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            board = chess.Board()

            while True:
                try:
                    entry = book.find(board)
                except IndexError:
                    break
                else:
                    board.push(entry.move())

            self.assertEqual(board.fen(), "r2q1rk1/4bppp/p2p1n2/np5b/3BP1P1/5N1P/PPB2P2/RN1QR1K1 b - - 0 15")

    def test_lasker_trap(self):
        with chess.polyglot.open_reader("data/polyglot/lasker-trap.bin") as book:
            board = chess.Board("rnbqk1nr/ppp2ppp/8/4P3/1BP5/8/PP2KpPP/RN1Q1BNR b kq - 1 7")
            entry = book.find(board)
            cute_underpromotion = entry.move()
            self.assertEqual(cute_underpromotion, board.parse_san("fxg1=N+"))

    def test_castling(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            # White decides between short castling and long castling at this
            # turning point in the Queens Gambit Exchange.
            pos = chess.Board("r1bqr1k1/pp1nbppp/2p2n2/3p2B1/3P4/2NBP3/PPQ1NPPP/R3K2R w KQ - 5 10")
            moves = set(entry.move() for entry in book.find_all(pos))
            self.assertIn(pos.parse_san("O-O"), moves)
            self.assertIn(pos.parse_san("O-O-O"), moves)
            self.assertIn(pos.parse_san("h3"), moves)
            self.assertEqual(len(moves), 3)

            # Black usually castles long at this point in the Ruy Lopez
            # Exchange.
            pos = chess.Board("r3k1nr/1pp1q1pp/p1pb1p2/4p3/3PP1b1/2P1BN2/PP1N1PPP/R2Q1RK1 b kq - 4 9")
            moves = set(entry.move() for entry in book.find_all(pos))
            self.assertIn(pos.parse_san("O-O-O"), moves)
            self.assertEqual(len(moves), 1)

    def test_empty_book(self):
        with chess.polyglot.open_reader("data/polyglot/empty.bin") as book:
            self.assertEqual(len(book), 0)

            entries = book.find_all(chess.Board())
            self.assertEqual(len(list(entries)), 0)

    def test_reversed(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            # Last is first of reversed.
            self.assertEqual(book[-1], next(reversed(book)))

            # First is last of reversed.
            for last in reversed(book):
                pass
            self.assertEqual(book[0], last)

    def test_random_choice(self):
        class FirstMockRandom(object):
            @staticmethod
            def randint(first, last):
                assert first <= last
                return first

        class LastMockRandom(object):
            @staticmethod
            def randint(first, last):
                assert first <= last
                return last

        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            # Uniform choice.
            entry = book.choice(chess.Board(), random=FirstMockRandom())
            self.assertEqual(entry.move(), chess.Move.from_uci("e2e4"))

            entry = book.choice(chess.Board(), random=LastMockRandom())
            self.assertEqual(entry.move(), chess.Move.from_uci("c2c4"))

            # Weighted choice.
            entry = book.weighted_choice(chess.Board(), random=FirstMockRandom())
            self.assertEqual(entry.move(), chess.Move.from_uci("e2e4"))

            entry = book.weighted_choice(chess.Board(), random=LastMockRandom())
            self.assertEqual(entry.move(), chess.Move.from_uci("c2c4"))

            # Weighted choice with excluded move.
            entry = book.weighted_choice(chess.Board(),
                exclude_moves=[chess.Move.from_uci("e2e4")], random=FirstMockRandom())
            self.assertEqual(entry.move(), chess.Move.from_uci("d2d4"))

    def test_find(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            entry = book.find(chess.Board())
            self.assertEqual(entry.move(), chess.Move.from_uci("e2e4"))

    def test_exclude_moves(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            entry = book.find(chess.Board(), exclude_moves=[chess.Move.from_uci("e2e4")])
            self.assertEqual(entry.move(), chess.Move.from_uci("d2d4"))

    def test_contains(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            for entry in book:
                self.assertIn(entry, book)

    def test_last(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            last_entry = book[len(book) - 1]
            self.assertTrue(any(book.find_all(last_entry.key)))
            self.assertTrue(all(book.find_all(last_entry.key)))

    def test_minimum_weight(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            with self.assertRaises(IndexError):
                book.find(chess.Board(), minimum_weight=2)


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
        e4_d5_exd5.comment = "Best"

        # Test string exporter with various options.
        exporter = chess.pgn.StringExporter(headers=False, comments=False, variations=False)
        game.accept(exporter)
        self.assertEqual(str(exporter), "1. e4 d5 2. exd5 *")

        exporter = chess.pgn.StringExporter(headers=False, comments=False)
        game.accept(exporter)
        self.assertEqual(str(exporter), "1. e4 d5 ( 1... h5 ) ( 1... e5 2. Qf3 ) ( 1... c5 ) 2. exd5 *")

        exporter = chess.pgn.StringExporter()
        game.accept(exporter)
        pgn = textwrap.dedent("""\
            [Event "?"]
            [Site "?"]
            [Date "????.??.??"]
            [Round "?"]
            [White "?"]
            [Black "?"]
            [Result "*"]

            { Test game: } 1. e4 { Scandinavian defense: } 1... d5 ( { This } 1... h5 $2
            { is nonesense } ) ( 1... e5 2. Qf3 $2 ) ( 1... c5 { Sicilian } ) 2. exd5
            { Best } *""")
        self.assertEqual(str(exporter), pgn)

        # Test file exporter.
        virtual_file = StringIO()
        exporter = chess.pgn.FileExporter(virtual_file)
        game.accept(exporter)
        self.assertEqual(virtual_file.getvalue(), pgn + "\n\n")

    def test_empty_game(self):
        game = chess.pgn.Game.without_tag_roster()
        self.assertEqual(str(game), "*")

    def test_setup(self):
        game = chess.pgn.Game()
        self.assertEqual(game.board(), chess.Board())
        self.assertNotIn("FEN", game.headers)
        self.assertNotIn("SetUp", game.headers)
        self.assertNotIn("Variant", game.headers)

        fen = "rnbqkbnr/pp1ppp1p/6p1/8/3pP3/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 4"
        game.setup(fen)
        self.assertEqual(game.headers["FEN"], fen)
        self.assertEqual(game.headers["SetUp"], "1")
        self.assertNotIn("Variant", game.headers)

        game.setup(chess.STARTING_FEN)
        self.assertNotIn("FEN", game.headers)
        self.assertNotIn("SetUp", game.headers)
        self.assertNotIn("Variant", game.headers)

        # Setup again, while starting FEN is already set.
        game.setup(chess.STARTING_FEN)
        self.assertNotIn("FEN", game.headers)
        self.assertNotIn("SetUp", game.headers)
        self.assertNotIn("Variant", game.headers)

        game.setup(chess.Board(fen))
        self.assertEqual(game.headers["FEN"], fen)
        self.assertEqual(game.headers["SetUp"], "1")
        self.assertNotIn("Variant", game.headers)

        # Chess960 starting position 283.
        fen = "rkbqrnnb/pppppppp/8/8/8/8/PPPPPPPP/RKBQRNNB w KQkq - 0 1"
        game.setup(fen)
        self.assertEqual(game.headers["FEN"], fen)
        self.assertEqual(game.headers["SetUp"], "1")
        self.assertEqual(game.headers["Variant"], "Chess960")
        board = game.board()
        self.assertTrue(board.chess960)
        self.assertEqual(board.fen(), fen)

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
        with open("data/pgn/kasparov-deep-blue-1997.pgn") as pgn:
            first_game = chess.pgn.read_game(pgn)
            second_game = chess.pgn.read_game(pgn)
            third_game = chess.pgn.read_game(pgn)
            fourth_game = chess.pgn.read_game(pgn)
            fifth_game = chess.pgn.read_game(pgn)
            sixth_game = chess.pgn.read_game(pgn)
            self.assertTrue(chess.pgn.read_game(pgn) is None)

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
        self.assertIn(5, node.variation(1).nags)
        self.assertEqual(node.variation(1).comment, "/\\ Ne7, c6")

    def test_promotion_without_equals(self):
        # Example game from https://github.com/rozim/ChessData as originally
        # reported.
        pgn = StringIO(textwrap.dedent("""\
            [Event "It (open)"]
            [Site "Aschach (Austria)"]
            [Date "2011.12.26"]
            [Round "1"]
            [White "Ennsberger Ulrich (AUT)"]
            [Black "Koller Hans-Juergen (AUT)"]
            [Result "0-1"]
            [ECO "A45"]
            [WhiteElo "2373"]
            [BlackElo "2052"]
            [ID ""]
            [FileName ""]
            [Annotator ""]
            [Source ""]
            [Remark ""]

            1.d4 Nf6 2.Bg5 c5 3.d5 Ne4 4.Bf4 Qb6 5.Nd2 Nxd2 6.Bxd2 e6 7.Bc3
            d6 8.e4 e5 9.a4 Be7 10.a5 Qc7 11.f4 f6 12.f5 g6 13.Bb5+ Bd7 14.Bc4
            gxf5 15.Qh5+ Kd8 16.exf5 Qc8 17.g4 Na6 18.Ne2 b5 19.axb6 axb6
            20.O-O Nc7 21.Qf7 h5 22.Qg7 Rf8 23.gxh5 Ne8 24.Rxa8 Nxg7 25.Rxc8+
            Kxc8 26.Ng3 Rh8 27.Be2 Be8 28.Be1 Nxh5 29.Bxh5 Bxh5 30.Nxh5 Rxh5
            31.h4 Bf8 32.c4 Bh6 33.Bg3 Be3+ 34.Kg2 Kb7 35.Kh3 b5 36.b3 b4
            37.Kg4 Rh8 38.Kf3 Bh6 39.Bf2 Ra8 40.Kg4 Bf4 41.Kh5 Ra3 42.Kg6
            Rxb3 43.h5 Rf3 44.h6 Bxh6 45.Kxh6 Rxf5 46.Kg6 Rf4 47.Kf7 e4 48.Re1
            Rxf2 49.Ke6 Kc7 50.Rh1 b3 51.Rh7+ Kb6 52.Kxd6 b2 53.Rh1 Rd2 54.Rh8
            e3 55.Rb8+ Ka5 56.Kxc5 Ka4 57.d6 e2 58.Re8 b1Q 0-1"""))

        game = chess.pgn.read_game(pgn)

        # Make sure the last move is a promotion.
        last_node = game.end()
        self.assertEqual(last_node.move.uci(), "b2b1q")

    def test_chess960_without_fen(self):
        pgn = StringIO(textwrap.dedent("""\
            [Variant "Chess960"]

            1. e4 *
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.variation(0).move, chess.Move.from_uci("e2e4"))

    def test_variation_stack(self):
        # Survive superfluous closing brackets.
        pgn = StringIO("1. e4 (1. d4))) !? *")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(game.variation(0).san(), "e4")
        self.assertEqual(game.variation(1).san(), "d4")
        self.assertEqual(len(game.errors), 2)

        # Survive superfluous opening brackets.
        pgn = StringIO("((( 1. c4 *")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(game.variation(0).san(), "c4")
        self.assertEqual(len(game.errors), 3)

    def test_game_starting_comment(self):
        pgn = StringIO("{ Game starting comment } 1. d3")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comment, "Game starting comment")
        self.assertEqual(game.variation(0).san(), "d3")

        pgn = StringIO("{ Empty game, but has a comment }")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comment, "Empty game, but has a comment")

    def test_game_starting_variation(self):
        pgn = StringIO(textwrap.dedent("""\
            {Start of game} 1. e4 ({Start of variation} 1. d4) 1... e5
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comment, "Start of game")

        node = game.variation(0)
        self.assertEqual(node.move, chess.Move.from_uci("e2e4"))
        self.assertFalse(node.comment)
        self.assertFalse(node.starting_comment)

        node = game.variation(1)
        self.assertEqual(node.move, chess.Move.from_uci("d2d4"))
        self.assertFalse(node.comment)
        self.assertEqual(node.starting_comment, "Start of variation")

    def test_annotation_symbols(self):
        pgn = StringIO("1. b4?! g6 2. Bb2 Nc6? 3. Bxh8!!")
        game = chess.pgn.read_game(pgn)

        node = game.variation(0)
        self.assertIn(chess.pgn.NAG_DUBIOUS_MOVE, node.nags)
        self.assertEqual(len(node.nags), 1)

        node = node.variation(0)
        self.assertEqual(len(node.nags), 0)

        node = node.variation(0)
        self.assertEqual(len(node.nags), 0)

        node = node.variation(0)
        self.assertIn(chess.pgn.NAG_MISTAKE, node.nags)
        self.assertEqual(len(node.nags), 1)

        node = node.variation(0)
        self.assertIn(chess.pgn.NAG_BRILLIANT_MOVE, node.nags)
        self.assertEqual(len(node.nags), 1)

    def test_tree_traversal(self):
        game = chess.pgn.Game()
        node = game.add_variation(chess.Move(chess.E2, chess.E4))
        alternative_node = game.add_variation(chess.Move(chess.D2, chess.D4))
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

        self.assertFalse(game.is_end())
        self.assertFalse(node.is_end())
        self.assertTrue(alternative_node.is_end())
        self.assertTrue(end_node.is_end())

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
        with open("data/pgn/kasparov-deep-blue-1997.pgn") as pgn:
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
        with open("data/pgn/kasparov-deep-blue-1997.pgn") as pgn:
            offsets = (offset for offset, headers in chess.pgn.scan_headers(pgn)
                       if headers["Result"] == "1/2-1/2")

            first_drawn_game_offset = next(offsets)
            pgn.seek(first_drawn_game_offset)
            first_drawn_game = chess.pgn.read_game(pgn)
            self.assertEqual(first_drawn_game.headers["Site"], "03")
            self.assertEqual(first_drawn_game.variation(0).move, chess.Move.from_uci("d2d3"))

    def test_black_to_move(self):
        game = chess.pgn.Game()
        game.setup("8/8/4k3/8/4P3/4K3/8/8 b - - 0 17")
        node = game
        node = node.add_main_variation(chess.Move.from_uci("e6d6"))
        node = node.add_main_variation(chess.Move.from_uci("e3d4"))
        node = node.add_main_variation(chess.Move.from_uci("d6e6"))

        expected = textwrap.dedent("""\
            [Event "?"]
            [Site "?"]
            [Date "????.??.??"]
            [Round "?"]
            [White "?"]
            [Black "?"]
            [Result "*"]
            [FEN "8/8/4k3/8/4P3/4K3/8/8 b - - 0 17"]
            [SetUp "1"]

            17... Kd6 18. Kd4 Ke6 *""")

        self.assertEqual(str(game), expected)

    def test_result_termination_marker(self):
        pgn = StringIO("1. d4 1-0")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Result"], "1-0")

    def test_missing_setup_tag(self):
        pgn = StringIO(textwrap.dedent("""\
            [Event "Test position"]
            [Site "Black to move "]
            [Date "1997.10.26"]
            [Round "?"]
            [White "Pos  16"]
            [Black "VA33.EPD"]
            [Result "1-0"]
            [FEN "rbb1N1k1/pp1n1ppp/8/2Pp4/3P4/4P3/P1Q2PPq/R1BR1K2 b - - 0 1"]

            {Houdini 1.5 x64: 1)} 1... Nxc5 ({Houdini 1.5 x64: 2)} 1... Qh1+ 2. Ke2 Qxg2 3.
            Kd2 Nxc5 4. Qxc5 Bg4 5. Ba3 Qxf2+ 6. Kc3 Qxe3+ 7. Kb2 Qxe8 8. Re1 Be6 9. Rh1 a5
            10. Rag1 Ba7 11. Qc3 g6 12. Bc5 Qb5+ 13. Qb3 Qe2+ 14. Qc2 Qxc2+ 15. Kxc2 Bxc5
            16. dxc5 Rc8 17. Kd2 {-2.39/22}) 2. dxc5 Bg4 3. f3 Bxf3 4. Qf2 Bxd1 5. Nd6 Bxd6
            6. cxd6 Qxd6 7. Bb2 Ba4 8. Qf4 Bb5+ 9. Kf2 Qg6 10. Bd4 f6 11. Qc7 Bc6 12. a4 a6
            13. Qg3 Qxg3+ 14. Kxg3 Rc8 15. Rc1 Kf7 16. a5 h5 17. Rh1 {-2.63/23}
            1-0"""))

        game = chess.pgn.read_game(pgn)
        self.assertIn("FEN", game.headers)
        self.assertNotIn("SetUp", game.headers)

        board = chess.Board("rbb1N1k1/pp1n1ppp/8/2Pp4/3P4/4P3/P1Q2PPq/R1BR1K2 b - - 0 1")
        self.assertEqual(game.board(), board)

    def test_game_from_board(self):
        setup = "3k4/8/4K3/8/8/8/8/2R5 b - - 0 1"
        board = chess.Board(setup)
        board.push_san("Ke8")
        board.push_san("Rc8#")

        game = chess.pgn.Game.from_board(board)
        self.assertEqual(game.headers["FEN"], setup)

        end_node = game.end()
        self.assertEqual(end_node.move, chess.Move.from_uci("c1c8"))
        self.assertEqual(end_node.parent.move, chess.Move.from_uci("d8e8"))

        self.assertEqual(game.headers["Result"], "1-0")

    def test_errors(self):
        pgn = StringIO("1. e4 Qa1 e5 2. Qxf8")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(len(game.errors), 2)

    def test_add_line(self):
        game = chess.pgn.Game()
        game.add_variation(chess.Move.from_uci("e2e4"))

        moves = [chess.Move.from_uci("g1f3"), chess.Move.from_uci("d7d5")]

        tail = game.add_line(moves, starting_comment="start", comment="end", nags=(17, 42))

        self.assertEqual(tail.parent.move, chess.Move.from_uci("g1f3"))
        self.assertEqual(tail.parent.starting_comment, "start")
        self.assertEqual(tail.parent.comment, "")
        self.assertEqual(len(tail.parent.nags), 0)

        self.assertEqual(tail.move, chess.Move.from_uci("d7d5"))
        self.assertEqual(tail.comment, "end")
        self.assertIn(42, tail.nags)

    def test_main_line(self):
        moves = [chess.Move.from_uci(uci) for uci in ["d2d3", "g8f6", "e2e4"]]

        game = chess.pgn.Game()
        game.add_line(moves)

        self.assertEqual(list(game.main_line()), moves)

    def test_lan(self):
        pgn = StringIO("1. e2-e4")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.end().move, chess.Move.from_uci("e2e4"))

    def test_variants(self):
        pgn = StringIO(textwrap.dedent("""\
            [Variant "Atomic"]
            [FEN "8/8/1b6/8/3Nk3/4K3/8/8 w - - 0 1"]

            1. Ne6
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.end().board().fen(), "8/8/1b2N3/8/4k3/4K3/8/8 b - - 1 1")

        game.setup(chess.variant.SuicideBoard())
        self.assertEqual(game.headers["Variant"], "Suicide")

        game.setup(chess.Board())
        self.assertNotIn("Variant", game.headers)

    def test_cutechess_fischerrandom(self):
        with open("data/pgn/cutechess-fischerrandom.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            board = game.board()
            self.assertTrue(board.chess960)
            self.assertEqual(board.fen(), "nbbrknrq/pppppppp/8/8/8/8/PPPPPPPP/NBBRKNRQ w KQkq - 0 1")

    def test_z0(self):
        with open("data/pgn/anastasian-lewis.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            board = game.end().board()
            self.assertEqual(board.fen(), "5rk1/2p1R2p/p5pb/2PPR3/8/2Q2B2/5P2/4K2q w - - 3 43")

    def test_wierd_header(self):
        pgn = StringIO(r"""[Black "[=0040.34h5a4]"]""")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Black"], "[=0040.34h5a4]")

    def test_semicolon_comment(self):
        pgn = StringIO("1. e4 ; e5")
        game = chess.pgn.read_game(pgn)
        node = game.variations[0]
        self.assertEqual(node.move, chess.Move.from_uci("e2e4"))
        self.assertTrue(node.is_end())

    def test_empty_game(self):
        pgn = StringIO(" \n\n   ")
        game = chess.pgn.read_game(pgn)
        self.assertTrue(game is None)

    def test_no_movetext(self):
        pgn = StringIO(textwrap.dedent("""
            [Event "A"]


            [Event "B"]
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Event"], "A")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Event"], "B")

        self.assertTrue(chess.pgn.read_game(pgn) is None)

    def test_subgame(self):
        pgn = StringIO("1. d4 d5 (1... Nf6 2. c4 (2. Nf3 g6 3. g3))")
        game = chess.pgn.read_game(pgn)
        node = game.variations[0].variations[1]
        subgame = node.accept_subgame(chess.pgn.GameModelCreator())
        self.assertEqual(subgame.headers["FEN"], "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2")
        self.assertEqual(subgame.variations[0].move, chess.Move.from_uci("c2c4"))
        self.assertEqual(subgame.variations[1].move, chess.Move.from_uci("g1f3"))


class CraftyTestCase(unittest.TestCase):

    def setUp(self):
        try:
            self.engine = chess.xboard.popen_engine("crafty")
        except OSError:
            self.skipTest("need crafty")

        self.engine.xboard()
        self.engine.send_line("log off")

    def tearDown(self):
        if self.engine.is_alive():
            self.engine.quit()

    def test_undo(self):
        self.engine.new()
        board = chess.Board()
        board.set_fen("4r1k1/pQ3pp1/7p/4q3/4r3/P7/1P2nPPP/2BR1R1K b - - 0 1")
        self.engine.setboard(board)
        self.engine.force()
        self.engine.usermove(chess.Move.from_uci("e5h2"))
        self.engine.undo()
        self.assertEqual(board.fen(), self.engine.board.fen())

    def test_remove(self):
        self.engine.new()
        board = chess.Board()
        board.set_fen("4r1k1/pQ3pp1/7p/4q3/4r3/P7/1P2nPPP/2BR1R1K b - - 0 1")
        self.engine.setboard(board)
        self.engine.force()
        self.engine.usermove(chess.Move.from_uci("e5h2"))
        self.engine.usermove(chess.Move.from_uci("h1h2"))
        self.engine.remove()
        self.assertEqual(board.fen(), self.engine.board.fen())

    def test_level(self):
        self.engine.new()
        self.engine.level(1, 0, 1, 0)
        self.engine.go()

    def test_stop(self):
        self.engine.new()
        self.engine.time(1000000)
        self.engine.go(async_callback=True)
        self.engine.search_started.wait()
        self.engine.stop()

    def test_time(self):
        self.engine.new()
        self.engine.level(0, 1, 0, 0)
        self.engine.time(100)
        self.engine.otim(100)
        self.engine.go()

    def test_mate_search(self):
        board = chess.Board()
        board.set_fen("4r1k1/pQ3pp1/7p/4q3/4r3/P7/1P2nPPP/2BR1R1K b - - 0 1") # Mate in 2
        self.engine.setboard(board)
        self.engine.sd(15) # Just to be safe
        post_handler = chess.xboard.PostHandler()
        self.engine.post_handlers.append(post_handler)
        self.engine.go()

        for move in post_handler.post["pv"]:
            board.push(move)
        self.assertTrue(board.is_checkmate(), True)

    def test_usermove(self):
        board = chess.Board()
        board.set_fen("4r1k1/pQ3pp1/7p/4q3/4r3/P7/1P2nPPP/2BR1R1K b - - 0 1") # Mate in 2
        self.engine.setboard(board)
        self.engine.usermove(chess.Move.from_uci("e5h2"))
        self.engine.usermove(chess.Move.from_uci("h1h2"))
        self.engine.sd(15)
        post_handler = chess.xboard.PostHandler()
        self.engine.post_handlers.append(post_handler)
        self.engine.go()

        board.push(chess.Move.from_uci("e5h2"))
        board.push(chess.Move.from_uci("h1h2"))
        for move in post_handler.post["pv"]:
            board.push(move)
        self.assertTrue(board.is_checkmate(), True)

    def test_playother(self):
        board = chess.Board()
        board.set_fen("4r1k1/pQ3pp1/7p/4q3/4r3/P7/1P2nPPP/2BR1R1K b - - 0 1") # Mate in 2
        self.engine.setboard(board)
        board.push(chess.Move.from_uci("e5h2"))
        self.engine.playother()

        self.engine.sd(15)
        post_handler = chess.xboard.PostHandler()
        self.engine.post_handlers.append(post_handler)
        self.engine.usermove(chess.Move.from_uci("e5h2"))

        for move in post_handler.post["pv"]:
            board.push(move)
        self.assertTrue(board.is_checkmate(), True)

    def test_terminate(self):
        self.engine.st(100)
        self.engine.sd(32)
        self.engine.go(async_callback=True)

        self.engine.search_started.wait()

        self.engine.terminate()
        self.assertFalse(self.engine.is_alive())

    def test_kill(self):
        self.engine.st(100)
        self.engine.sd(32)
        self.engine.go(async_callback=True)

        self.engine.search_started.wait()

        self.engine.kill()
        self.assertFalse(self.engine.is_alive())


class StockfishTestCase(unittest.TestCase):

    def setUp(self):
        try:
            self.engine = chess.uci.popen_engine("stockfish")
        except OSError:
            self.skipTest("need stockfish")

        self.engine.uci()

    def tearDown(self):
        self.engine.quit()

    def test_forced_mates(self):
        epds = [
            "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";",
            "6k1/N1p3pp/2p5/3n1P2/4K3/1P5P/P1Pr1r2/R1R5 b - - bm Rf4+; id \"Clausthal 2014\";",
        ]

        board = chess.Board()

        for epd in epds:
            operations = board.set_epd(epd)
            self.engine.ucinewgame()
            self.engine.position(board)
            result = self.engine.go(mate=5)
            self.assertIn(result[0], operations["bm"], operations["id"])

    def test_async_callback(self):
        self.async_callback_called = threading.Event()

        def async_callback(command):
            self.async_callback_called.set()

        command = self.engine.isready(async_callback=async_callback)

        # Wait for the command to be executed.
        command.result()
        self.assertTrue(command.done())

        self.async_callback_called.wait()
        self.assertTrue(self.async_callback_called.is_set())

    def test_initialization(self):
        self.assertIn("Stockfish", self.engine.name)
        self.assertEqual(self.engine.options["UCI_Chess960"].name, "UCI_Chess960")
        self.assertEqual(self.engine.options["uci_Chess960"].type, "check")
        self.assertEqual(self.engine.options["UCI_CHESS960"].default, False)

    def test_terminate(self):
        self.engine.go(infinite=True, async_callback=True)


class SpurEngineTestCase(unittest.TestCase):

    def setUp(self):
        try:
            import spur
            self.shell = spur.LocalShell()
        except ImportError:
            self.skipTest("need spur library")

        try:
            self.engine = chess.uci.spur_spawn_engine(self.shell, ["stockfish"])
        except OSError:
            self.skipTest("need stockfish")

    def test_local_shell(self):
        self.engine.uci()

        self.engine.ucinewgame()

        # Find fools mate.
        board = chess.Board()
        board.push_san("g4")
        board.push_san("e5")
        board.push_san("f4")
        self.engine.position(board)
        bestmove, pondermove = self.engine.go(mate=1, movetime=2000)
        self.assertEqual(board.san(bestmove), "Qh4#")

        self.engine.quit()

    def test_terminate(self):
        self.engine.uci()
        self.engine.go(infinite=True, async_callback=True)

        self.engine.search_started.wait()

        self.engine.terminate()
        self.assertFalse(self.engine.is_alive())

    def test_kill(self):
        self.engine.uci()
        self.engine.go(infinite=True, async_callback=True)

        self.engine.search_started.wait()

        self.engine.kill()
        self.assertFalse(self.engine.is_alive())

    def test_async_terminate(self):
        command = self.engine.terminate(async_callback=True)
        command.result()
        self.assertTrue(command.done())


class XboardEngineTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = chess.xboard.Engine()
        self.mock = chess.engine.MockProcess(self.engine)
        self.mock.expect("xboard")
        feature_list = (
                "feature egt=syzygy,gaviota",
                "feature option=\"spinvar -spin 50 0 100\"",
                "feature option=\"combovar -combo HI /// HELLO /// BYE\"",
                "feature option=\"checkvar -check 0\"",
                "feature option=\"stringvar -string \"\"\"",
                "feature option=\"filevar -file \"\"\"",
                "feature option=\"pathvar -path \"\"\"",
                "feature option=\"buttonvar -button\"",
                "feature option=\"resetvar -reset\"",
                "feature option=\"savevar -save\"",

                )
        self.mock.expect("protover 2", feature_list)
        self.mock.expect("post")
        self.mock.expect("easy")
        self.mock.expect("ping 123", ("pong 123", ))
        self.engine.xboard()
        self.mock.assert_done()

    def tearDown(self):
        self.engine.terminate()
        self.mock.assert_terminated()

    def test_engine_offer_draw_during_engine_search(self):
        draw_handler = chess.xboard.DrawHandler()
        self.engine.draw_handler = draw_handler

        self.mock.expect("nopost")
        self.engine.nopost()
        self.mock.expect("st 10")
        self.engine.st(10)
        self.mock.expect("go", ("offer draw", ))

        with draw_handler:
            self.engine.go(async_callback=True)
            draw_handler.draw_offered.wait()

        self.assertEqual(draw_handler.pending_offer, True)
        self.assertEqual(self.engine.engine_offered_draw, True)

        self.mock.expect("?", ("move e2e4", ))
        self.engine.stop()
        self.mock.expect("result 1/2-1/2")
        self.engine.result(chess.xboard.DRAW)

        self.assertEqual(self.engine.end_result, chess.xboard.DRAW)
        self.mock.assert_done()

    def test_engine_offer_draw_during_human_turn(self):
        draw_handler = chess.xboard.DrawHandler()
        self.engine.draw_handler = draw_handler

        self.mock.expect("nopost")
        self.engine.nopost()
        self.mock.expect("st 1")
        self.engine.st(1)
        self.mock.expect("go", ("move e2e4", "offer draw", ))

        with draw_handler:
            self.engine.go()
            draw_handler.draw_offered.wait()

        self.assertEqual(draw_handler.pending_offer, True)
        self.assertEqual(self.engine.engine_offered_draw, True)

        self.mock.expect("result 1/2-1/2")
        self.engine.result(chess.xboard.DRAW)

        self.assertEqual(self.engine.end_result, chess.xboard.DRAW)
        self.mock.assert_done()

    def test_human_offer_draw_during_engine_search(self):
        draw_handler = chess.xboard.DrawHandler()
        self.engine.draw_handler = draw_handler

        self.mock.expect("nopost")
        self.engine.nopost()
        self.mock.expect("st 10")
        self.engine.st(10)
        self.mock.expect("go")
        go = self.engine.go(async_callback=True)
        self.engine.search_started.wait()

        self.mock.expect("draw", ("offer draw", ))
        self.mock.expect("result 1/2-1/2")

        self.engine.draw()
        self.assertEqual(go.result(), chess.xboard.GAME_DRAW)

        self.assertEqual(self.engine.idle, True)
        self.assertEqual(self.engine.end_result, chess.xboard.DRAW)
        self.mock.assert_done()

    def test_human_offer_draw_during_human_turn(self):
        draw_handler = chess.xboard.DrawHandler()
        self.engine.draw_handler = draw_handler

        self.assertEqual(self.engine.idle, True)
        self.mock.expect("draw", ("offer draw", ))
        self.mock.expect("result 1/2-1/2")
        self.engine.draw()

        # Set when handling "offer draw" from the engine.
        self.engine.move_received.wait()

        self.assertEqual(self.engine.idle, True)
        self.assertEqual(self.engine.end_result, chess.xboard.DRAW)
        self.mock.assert_done()

    def test_resign_during_engine_turn(self):
        self.mock.expect("nopost")
        self.engine.nopost()
        self.mock.expect("st 10")
        self.engine.st(10)
        self.mock.expect("go", ("resign", ))
        self.mock.expect("result 0-1")
        self.engine.go()
        self.assertEqual(self.engine.end_result, chess.xboard.BLACK_WIN)
        self.mock.assert_done()

    def test_resign_during_human_turn(self):
        self.mock.expect("nopost", ("resign", ))
        self.mock.expect("result 1-0")
        self.engine.nopost() # Command to make MockProcess expect a random `resign`

        # Set when handling "offer draw" from the engine.
        self.engine.move_received.wait()

        self.assertEqual(self.engine.end_result, chess.xboard.WHITE_WIN)
        self.mock.assert_done()

    def test_egtpath(self):
        self.mock.expect("egtpath syzygy /abc")
        try:
            self.engine.egtpath("non-existent", "random_path")
        except chess.engine.EngineStateException:
            pass
        self.engine.egtpath("syzygy", "/abc")
        self.mock.assert_done()

    def test_options(self):
        """
        Could do with dictionary instead, but that fails to preserve order
        on some versions of Python.

        Done with an *OrderedDict* just for testing purposes, the order is
        not actually important.
        """
        option_map = collections.OrderedDict()
        option_map["spinvar"] = 99
        option_map["combovar"] = "BYE"
        option_map["checkvar"] = 1
        option_map["stringvar"] = "teststring"
        option_map["filevar"] = "filename"
        option_map["pathvar"] = "path/to/some/dir"
        option_map["buttonvar"] = None
        option_map["resetvar"] = None
        option_map["savevar"] = None

        self.mock.expect("option spinvar=99")
        self.mock.expect("option combovar=BYE")
        self.mock.expect("option checkvar=1")
        self.mock.expect("option stringvar=\"teststring\"")
        self.mock.expect("option filevar=\"filename\"")
        self.mock.expect("option pathvar=\"path/to/some/dir\"")
        self.mock.expect("option buttonvar")
        self.mock.expect("option resetvar")
        self.mock.expect("option savevar")
        self.engine.option(option_map)
        self.mock.assert_done()


class UciEngineTestCase(unittest.TestCase):

    def setUp(self):
        self.engine = chess.uci.Engine()
        self.mock = chess.uci.MockProcess(self.engine)

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
        self.mock.expect("go ponder")
        ponder_command = self.engine.go(ponder=True, async_callback=True)
        self.mock.expect("ponderhit", ("bestmove e2e4", ))
        self.engine.ponderhit()
        self.assertEqual(ponder_command.result().bestmove, chess.Move.from_uci("e2e4"))
        self.mock.assert_done()

    def test_kill(self):
        self.engine.kill()
        self.mock.assert_terminated()

    def test_go(self):
        self.mock.expect("go infinite searchmoves e2e4 d2d4")
        go_command = self.engine.go(searchmoves=[chess.Move.from_uci("e2e4"), chess.Move.from_uci("d2d4")], infinite=True, async_callback=True)
        self.assertFalse(go_command.done())

        self.mock.expect("stop", ("bestmove e2e4", ))
        self.engine.stop()
        bestmove, pondermove = go_command.result()
        self.assertTrue(go_command.done())
        self.mock.assert_done()
        self.assertEqual(bestmove, chess.Move.from_uci("e2e4"))
        self.assertTrue(pondermove is None)

        self.mock.expect("go wtime 1 btime 2 winc 3 binc 4 movestogo 5 depth 6 nodes 7 mate 8 movetime 9", (
            "bestmove d2d4 ponder d7d5",
        ))
        self.engine.go(wtime=1, btime=2, winc=3, binc=4, movestogo=5, depth=6, nodes=7, mate=8, movetime=9)
        self.mock.assert_done()

        self.mock.expect("go movetime 3333", (
            "bestmove (none) ponder (none)",
        ))
        bestmove, pondermove = self.engine.go(movetime=3333)
        self.assertTrue(bestmove is None)
        self.assertTrue(pondermove is None)
        self.mock.assert_done()

        self.mock.expect("go mate 2", (
            "bestmove (none)",
        ))
        bestmove, pondermove = self.engine.go(mate=2)
        self.assertTrue(bestmove is None)
        self.assertTrue(pondermove is None)
        self.mock.assert_done()

    def test_info_refutation(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        # Set a position where d1h5 g6h5 would be a legal sequence of moves.
        fen = "8/8/6k1/8/8/8/1K6/3B4 w - - 0 1"
        self.mock.expect("position fen " + fen)
        self.engine.position(chess.Board(fen))

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
            self.assertNotIn(1, info["score"])

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

    def test_info_ebf(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info ebf 0.42")
        with handler as info:
            self.assertEqual(info["ebf"], 0.42)

    def test_mate_score(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info depth 7 seldepth 8 score mate 3")
        with handler as info:
            self.assertEqual(info["score"][1].mate, 3)
            self.assertEqual(info["score"][1].cp, None)

    def test_info(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.mock.expect("go", ("bestmove d2d4", ))
        self.engine.go()

        self.engine.on_line_received("info tbhits 123 cpuload 456 hashfull 789")
        with handler as info:
            self.assertEqual(info["tbhits"], 123)
            self.assertEqual(info["cpuload"], 456)
            self.assertEqual(info["hashfull"], 789)

        self.mock.expect("go", ("bestmove e2e4", ))
        self.engine.go()

        self.assertNotIn("tbhits", handler.info)
        self.assertNotIn("cpuload", handler.info)
        self.assertNotIn("hashfull", handler.info)

        self.engine.on_line_received("info time 987 nodes 654 nps 321")
        with handler as info:
            self.assertEqual(info["time"], 987)
            self.assertEqual(info["nodes"], 654)
            self.assertEqual(info["nps"], 321)

        self.mock.assert_done()

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

    def test_multi_pv(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info score cp 777 multipv 13 pv e2e4")
        self.engine.on_line_received("info score cp 888 pv d2d4")
        with handler as info:
            # Principal variations.
            self.assertEqual(info["pv"][13][0], chess.Move.from_uci("e2e4"))
            self.assertEqual(info["pv"][1][0], chess.Move.from_uci("d2d4"))

            # Score is relative to multipv as well.
            self.assertEqual(info["score"][13].cp, 777)
            self.assertEqual(info["score"][1].cp, 888)

    def test_castling_move_conversion(self):
        # Setup a position where white can castle on the next move.
        fen = "rnbqkbnr/pppppppp/8/8/8/4PN2/PPPPBPPP/RNBQK2R w KQkq - 1 1"
        board = chess.Board(fen)
        self.mock.expect("position fen " + fen)
        self.engine.position(board)
        self.mock.assert_done()

        # Expect the standard castling move notation e1g1 and respond with it.
        self.mock.expect("go movetime 70 searchmoves a2a3 e1g1", (
            "bestmove e1g1",
        ))
        bestmove, pondermove = self.engine.go(movetime=70, searchmoves=[
            board.parse_san("a3"),
            board.parse_san("O-O"),
        ])
        self.assertTrue(bestmove.from_square, chess.E1)
        self.assertTrue(bestmove.to_square, chess.H1)
        self.mock.assert_done()

        # Assert that we can change to UCI_Chess960 mode.
        self.assertFalse(self.engine.uci_chess960)
        self.mock.expect("setoption name uCi_CheSS960 value true")
        self.mock.expect("isready", ("readyok", ))
        self.engine.setoption({"uCi_CheSS960": True})
        self.assertTrue(self.engine.uci_chess960)
        self.mock.assert_done()

        # Expect a Shredder FEN during for the position command.
        self.mock.expect("position fen rnbqkbnr/pppppppp/8/8/8/4PN2/PPPPBPPP/RNBQK2R w HAha - 1 1")
        self.engine.position(board)
        self.mock.assert_done()

        # Check that castling move conversion is now disabled.
        self.mock.expect("go movetime 70 searchmoves a2a3 e1h1", (
            "bestmove e1h1",
        ))
        bestmove, pondermove = self.engine.go(movetime=70, searchmoves=[
            board.parse_san("a3"),
            board.parse_san("O-O"),
        ])
        self.assertTrue(bestmove.from_square, chess.E1)
        self.assertTrue(bestmove.to_square, chess.H1)
        self.mock.assert_done()

    def test_castling_ponder(self):
        # Setup position.
        fen = "rnbqkb1r/pp1ppppp/5n2/2p5/4P3/5N2/PPPPBPPP/RNBQK2R b KQkq - 3 3"
        board = chess.Board(fen, chess960=True)
        self.mock.expect("position fen " + fen)
        self.engine.position(board)

        # Test castling moves as ponder moves.
        self.mock.expect("go depth 15", ("bestmove f6e4 ponder e1g1", ))
        bestmove, ponder = self.engine.go(depth=15)
        self.assertEqual(bestmove, chess.Move.from_uci("f6e4"))
        self.assertEqual(ponder, chess.Move.from_uci("e1h1"))

        self.mock.assert_done()

    def test_invalid_castling_rights(self):
        fen = "3qk3/4pp2/5r2/8/8/8/3PP1P1/4K1R1 b G - 0 1"
        board = chess.Board(fen, chess960=True)
        board.push_san("Rf5")

        # White can castle with the G-side rook, which is not possible in
        # standard chess. The UCI module should just send the final FEN,
        # show a warning and hope for the best.
        self.mock.expect("position fen 3qk3/4pp2/8/5r2/8/8/3PP1P1/4K1R1 w K - 1 2")
        logging.disable(logging.ERROR)
        self.engine.position(board)
        logging.disable(logging.NOTSET)
        self.mock.assert_done()

        # Activate Chess960 mode.
        self.mock.expect("setoption name UCI_Chess960 value true")
        self.mock.expect("isready", ("readyok", ))
        self.engine.setoption({"UCI_Chess960": True})

        # Then those castling rights should work fine.
        self.mock.expect("position fen " + fen + " moves f6f5")
        self.engine.position(board)
        self.mock.assert_done()

    def test_hakkapeliitta_double_spaces(self):
        handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(handler)

        self.engine.on_line_received("info depth 10 seldepth 9 score cp 22  time 17 nodes 48299 nps 2683000 tbhits 0")

        with handler as info:
            self.assertEqual(info["depth"], 10)
            self.assertEqual(info["seldepth"], 9)
            self.assertEqual(info["score"][1].cp, 22)
            self.assertEqual(info["score"][1].mate, None)
            self.assertEqual(info["time"], 17)
            self.assertEqual(info["nodes"], 48299)
            self.assertEqual(info["nps"], 2683000)
            self.assertEqual(info["tbhits"], 0)


class UciOptionMapTestCase(unittest.TestCase):

    def test_equality(self):
        a = chess.uci.OptionMap()
        b = chess.uci.OptionMap()
        c = chess.uci.OptionMap()
        self.assertEqual(a, b)

        a["fOO"] = "bAr"
        b["foo"] = "bAr"
        c["fOo"] = "bar"
        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertNotEqual(a, c)
        self.assertNotEqual(c, a)
        self.assertNotEqual(b, c)

        b["hello"] = "world"
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, a)

    def test_len(self):
        a = chess.uci.OptionMap()
        self.assertEqual(len(a), 0)

        a["key"] = "value"
        self.assertEqual(len(a), 1)

        del a["key"]
        self.assertEqual(len(a), 0)


class SyzygyTestCase(unittest.TestCase):

    def test_calc_key(self):
        board = chess.Board("8/8/8/5N2/5K2/2kB4/8/8 b - - 0 1")
        key_from_board = chess.syzygy.calc_key(board)
        key_from_filename = chess.syzygy.normalize_tablename("KBNvK")
        self.assertEqual(key_from_board, key_from_filename)

    def test_tablenames(self):
        self.assertIn("KPPvKN", chess.syzygy.tablenames())
        self.assertIn("KNNPvKN", chess.syzygy.tablenames())
        self.assertIn("KQRNvKR", chess.syzygy.tablenames())
        self.assertIn("KRRRvKR", chess.syzygy.tablenames())
        self.assertIn("KRRvKRR", chess.syzygy.tablenames())
        self.assertIn("KRNvKRP", chess.syzygy.tablenames())
        self.assertIn("KRPvKP", chess.syzygy.tablenames())

    def test_suicide_tablenames(self):
        # Test number of 6 piece tables.
        self.assertEqual(sum(1 for eg in chess.syzygy.tablenames(one_king=False) if len(eg) == 7), 5754)

    def test_normalize_tablename(self):
        names = set(chess.syzygy.tablenames())
        for name in names:
            self.assertTrue(
                chess.syzygy.normalize_tablename(name) in names,
                "Already normalized {0}".format(name))

            w, b = name.split("v", 1)
            swapped = b + "v" + w
            self.assertTrue(
                chess.syzygy.normalize_tablename(swapped) in names,
                "Normalized {0}".format(swapped))

    def test_normalize_nnvbb(self):
        self.assertEqual(chess.syzygy.normalize_tablename("KNNvKBB"), "KBBvKNN")

    def test_probe_pawnless_wdl_table(self):
        wdl = chess.syzygy.WdlTable("data/syzygy/regular/KBNvK.rtbw")
        wdl.init_table_wdl()

        board = chess.Board("8/8/8/5N2/5K2/2kB4/8/8 b - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), -2)

        board = chess.Board("7B/5kNK/8/8/8/8/8/8 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        board = chess.Board("N7/8/2k5/8/7K/8/8/B7 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        board = chess.Board("8/8/1NkB4/8/7K/8/8/8 w - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 0)

        board = chess.Board("8/8/8/2n5/2b1K3/2k5/8/8 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), -2)

        wdl.close()

    def test_probe_wdl_table(self):
        wdl = chess.syzygy.WdlTable("data/syzygy/regular/KRvKP.rtbw")
        wdl.init_table_wdl()

        board = chess.Board("8/8/2K5/4P3/8/8/8/3r3k b - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 0)

        board = chess.Board("8/8/2K5/8/4P3/8/8/3r3k b - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        wdl.close()

    def test_probe_dtz_table_piece(self):
        dtz = chess.syzygy.DtzTable("data/syzygy/regular/KRvKN.rtbz")
        dtz.init_table_dtz()

        # Pawnless position with white to move.
        board = chess.Board("7n/6k1/4R3/4K3/8/8/8/8 w - - 0 1")
        self.assertEqual(dtz.probe_dtz_table(board, 2), (0, -1))

        # Same position with black to move.
        board = chess.Board("7n/6k1/4R3/4K3/8/8/8/8 b - - 1 1")
        self.assertEqual(dtz.probe_dtz_table(board, -2), (8, 1))

        dtz.close()

    def test_probe_dtz_table_pawn(self):
        dtz = chess.syzygy.DtzTable("data/syzygy/regular/KNvKP.rtbz")
        dtz.init_table_dtz()

        board = chess.Board("8/1K6/1P6/8/8/8/6n1/7k w - - 0 1")
        self.assertEqual(dtz.probe_dtz_table(board, 2), (2, 1))

        dtz.close()

    def test_probe_wdl_tablebase(self):
        with chess.syzygy.Tablebases(max_fds=2) as tables:
            self.assertGreaterEqual(tables.open_directory("data/syzygy/regular"), 70)

            # Winning KRvKB.
            board = chess.Board("7k/6b1/6K1/8/8/8/8/3R4 b - - 12 7")
            self.assertEqual(tables.probe_wdl_table(board), -2)

            # Drawn KBBvK.
            board = chess.Board("7k/8/8/4K3/3B4/4B3/8/8 b - - 12 7")
            self.assertEqual(tables.probe_wdl_table(board), 0)

            # Winning KBBvK.
            board = chess.Board("7k/8/8/4K2B/8/4B3/8/8 w - - 12 7")
            self.assertEqual(tables.probe_wdl_table(board), 2)

    def test_wdl_ep(self):
        with chess.syzygy.open_tablebases("data/syzygy/regular") as tables:
            # Winning KPvKP because of en passant.
            board = chess.Board("8/8/8/k2Pp3/8/8/8/4K3 w - e6 0 2")

            # If there was no en passant this would be a draw.
            self.assertEqual(tables.probe_wdl_table(board), 0)

            # But it is a win.
            self.assertEqual(tables.probe_wdl(board), 2)

    def test_dtz_ep(self):
        with chess.syzygy.open_tablebases("data/syzygy/regular") as tables:
            board = chess.Board("8/8/8/8/2pP4/2K5/4k3/8 b - d3 0 1")
            self.assertEqual(tables.probe_dtz_no_ep(board), -1)
            self.assertEqual(tables.probe_dtz(board), 1)

    def test_testsuite(self):
        with chess.syzygy.open_tablebases("data/syzygy/regular") as tables, open("data/endgame.epd") as epds:
            board = chess.Board()

            for line, epd in enumerate(epds):
                extra = board.set_epd(epd)

                wdl_table = tables.probe_wdl_table(board)
                self.assertEqual(
                    wdl_table, extra["wdl_table"],
                    "Expecting wdl_table {0} for {1}, got {2} (at line {3})".format(extra["wdl_table"], board.fen(), wdl_table, line + 1))

                wdl = tables.probe_wdl(board)
                self.assertEqual(
                    wdl, extra["wdl"],
                    "Expecting wdl {0} for {1}, got {2} (at line {3})".format(extra["wdl"], board.fen(), wdl, line + 1))

                dtz = tables.probe_dtz(board)
                self.assertEqual(
                    dtz, extra["dtz"],
                    "Expecting dtz {0} for {1}, got {2} (at line {3})".format(extra["dtz"], board.fen(), dtz, line + 1))

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_stockfish_dtz_bug(self):
        with chess.syzygy.open_tablebases("data/syzygy/regular") as tables:
            board = chess.Board("3K4/8/3k4/8/4p3/4B3/5P2/8 w - - 0 5")
            self.assertEqual(tables.probe_dtz(board), 15)

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_issue_93(self):
        with chess.syzygy.open_tablebases("data/syzygy/regular") as tables:
            board = chess.Board("4r1K1/6PP/3k4/8/8/8/8/8 w - - 1 64")
            self.assertEqual(tables.probe_wdl(board), 2)
            self.assertEqual(tables.probe_dtz(board), 4)

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_suicide_dtm(self):
        with chess.syzygy.open_tablebases("data/syzygy/suicide", VariantBoard=chess.variant.SuicideBoard) as tables, open("data/suicide-dtm.epd") as epds:
            for epd in epds:
                epd = epd.strip()

                board, solution = chess.variant.SuicideBoard.from_epd(epd)

                wdl = tables.probe_wdl(board)

                expected_wdl = ((solution["max_dtm"] > 0) - (solution["max_dtm"] < 0)) * 2
                self.assertEqual(wdl, expected_wdl, "Expecting wdl {0}, got {1} (in {2})".format(expected_wdl, wdl, epd))

                dtz = tables.probe_dtz(board)

                if wdl > 0:
                    self.assertGreaterEqual(dtz, chess.syzygy.dtz_before_zeroing(wdl))
                    self.assertLessEqual(dtz, 2 * solution["max_dtm"])
                elif wdl == 0:
                    self.assertEqual(dtz, 0)
                else:
                    self.assertLessEqual(dtz, chess.syzygy.dtz_before_zeroing(wdl))
                    self.assertGreaterEqual(dtz, 2 * solution["max_dtm"])

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_suicide_dtz(self):
        with chess.syzygy.open_tablebases("data/syzygy/suicide", VariantBoard=chess.variant.SuicideBoard) as tables, open("data/suicide-dtz.epd") as epds:
            for epd in epds:
                epd = epd.strip()
                if epd.startswith("%") or epd.startswith("#"):
                    continue

                board, solution = chess.variant.SuicideBoard.from_epd(epd)

                dtz = tables.probe_dtz(board)
                self.assertEqual(dtz, solution["dtz"], "Expecting dtz {0}, got {1} (in {2})".format(solution["dtz"], dtz, epd))

    @unittest.skipIf(os.environ.get("TRAVIS_PYTHON_VERSION", "").startswith("pypy"), "travis pypy is very slow")
    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_suicide_stats(self):
        board = chess.variant.SuicideBoard()

        with chess.syzygy.open_tablebases("data/syzygy/suicide", VariantBoard=type(board)) as tables, open("data/suicide-stats.epd") as epds:
            for l, epd in enumerate(epds):
                solution = board.set_epd(epd)

                dtz = tables.probe_dtz(board)
                self.assertAlmostEqual(dtz, solution["dtz"], delta=1, msg="Expected dtz {0}, got {1} (in l. {2}, fen: {3})".format(solution["dtz"], dtz, l + 1, board.fen()))


class NativeGaviotaTestCase(unittest.TestCase):

    @unittest.skipUnless(platform.python_implementation() == "CPython", "need CPython for native Gaviota")
    @catchAndSkip((OSError, RuntimeError), "need libgtb")
    def setUp(self):
        self.tablebases = chess.gaviota.open_tablebases_native("data/gaviota")

    def tearDown(self):
        self.tablebases.close()

    def test_native_probe_dtm(self):
        board = chess.Board("6K1/8/8/8/4Q3/8/6k1/8 b - - 0 1")
        self.assertEqual(self.tablebases.probe_dtm(board), -14)

        board = chess.Board("8/3K4/8/8/8/4r3/4k3/8 b - - 0 1")
        self.assertEqual(self.tablebases.get_dtm(board), 21)

    def test_native_probe_wdl(self):
        board = chess.Board("8/8/4K3/2n5/8/3k4/8/8 w - - 0 1")
        self.assertEqual(self.tablebases.probe_wdl(board), 0)

        board = chess.Board("8/8/1p2K3/8/8/3k4/8/8 b - - 0 1")
        self.assertEqual(self.tablebases.get_wdl(board), 1)


class GaviotaTestCase(unittest.TestCase):

    @catchAndSkip(ImportError)
    def setUp(self):
        self.tablebases = chess.gaviota.open_tablebases("data/gaviota", LibraryLoader=None)

    def tearDown(self):
        self.tablebases.close()

    @catchAndSkip(chess.gaviota.MissingTableError)
    def test_dm_4(self):
        with open("data/endgame-dm-4.epd") as epds:
            for line, epd in enumerate(epds):
                # Skip empty lines and comments.
                epd = epd.strip()
                if not epd or epd.startswith("#"):
                    continue

                # Parse EPD.
                board, extra = chess.Board.from_epd(epd)

                # Check DTM.
                if extra["dm"] > 0:
                    expected = extra["dm"] * 2 - 1
                else:
                    expected = extra["dm"] * 2
                dtm = self.tablebases.probe_dtm(board)
                self.assertEqual(dtm, expected,
                    "Expecting dtm {0} for {1}, got {2} (at line {3})".format(expected, board.fen(), dtm, line + 1))

    @catchAndSkip(chess.gaviota.MissingTableError)
    def test_dm_5(self):
        with open("data/endgame-dm-5.epd") as epds:
            for line, epd in enumerate(epds):
                # Skip empty lines and comments.
                epd = epd.strip()
                if not epd or epd.startswith("#"):
                    continue

                # Parse EPD.
                board, extra = chess.Board.from_epd(epd)

                # Check DTM.
                if extra["dm"] > 0:
                    expected = extra["dm"] * 2 - 1
                else:
                    expected = extra["dm"] * 2
                dtm = self.tablebases.probe_dtm(board)
                self.assertEqual(dtm, expected,
                    "Expecting dtm {0} for {1}, got {2} (at line {3})".format(expected, board.fen(), dtm, line + 1))

    def test_wdl(self):
        board = chess.Board("8/8/4K3/2n5/8/3k4/8/8 w - - 0 1")
        self.assertEqual(self.tablebases.probe_wdl(board), 0)

        board = chess.Board("8/8/1p2K3/8/8/3k4/8/8 b - - 0 1")
        self.assertEqual(self.tablebases.probe_wdl(board), 1)

    def test_context_manager(self):
        self.assertTrue(self.tablebases.available_tables)

        with self.tablebases:
            pass

        self.assertFalse(self.tablebases.available_tables)


class SvgTestCase(unittest.TestCase):

    def test_svg_board(self):
        svg = chess.BaseBoard("4k3/8/8/8/8/8/8/4KB2")._repr_svg_()
        self.assertIn("white bishop", svg)
        self.assertNotIn("black queen", svg)

    def test_svg_arrows(self):
        svg = chess.svg.board(arrows=[(chess.A1, chess.A1)])
        self.assertIn("<circle", svg)
        self.assertNotIn("<line", svg)

        svg = chess.svg.board(arrows=[(chess.A1, chess.H8)])
        self.assertNotIn("<circle", svg)
        self.assertIn("<line", svg)


class SuicideTestCase(unittest.TestCase):

    def test_parse_san(self):
        board = chess.variant.SuicideBoard()
        board.push_san("e4")
        board.push_san("d5")

        # Capture mandatory.
        with self.assertRaises(ValueError):
            board.push_san("Nf3")

    def test_is_legal(self):
        board = chess.variant.SuicideBoard("4k3/8/8/8/8/1r3B2/8/4K3 b - - 0 1")
        Rxf3 = board.parse_san("Rxf3")
        Rb4 = chess.Move.from_uci("b3b4")
        self.assertTrue(board.is_legal(Rxf3))
        self.assertIn(Rxf3, board.generate_legal_moves())
        self.assertFalse(board.is_legal(Rb4))
        self.assertNotIn(Rb4, board.generate_legal_moves())

    def test_insufficient_material(self):
        # Kings only.
        board = chess.variant.SuicideBoard("8/8/8/2k5/8/8/4K3/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Bishops on same color.
        board = chess.variant.SuicideBoard("8/8/8/5b2/2B5/1B6/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Opposite color bishops.
        board = chess.variant.SuicideBoard("4b3/8/8/8/3B4/2B5/8/8 b - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # Pawn not blocked.
        board = chess.variant.SuicideBoard("8/5b2/5P2/8/3B4/2B5/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Pawn blocked.
        board = chess.variant.SuicideBoard("8/5p2/5P2/8/3B4/1bB5/8/8 b - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # Pawns blocked but on wrong color.
        board = chess.variant.SuicideBoard("8/5p2/5P2/8/8/8/3b4/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Stalemate.
        board = chess.variant.SuicideBoard("6B1/6pB/6P1/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Pawns not really locked up.
        board = chess.variant.SuicideBoard("8/8/8/2pp4/2PP4/8/8/8 w - - 0 1")
        self.assertFalse(board.is_insufficient_material())

    def test_king_promotions(self):
        board = chess.variant.SuicideBoard("8/6P1/8/3K1k2/8/8/3p4/8 b - - 0 1")
        d1K = chess.Move.from_uci("d2d1k")
        self.assertIn(d1K, board.generate_legal_moves())
        self.assertTrue(board.is_pseudo_legal(d1K))
        self.assertTrue(board.is_legal(d1K))
        self.assertEqual(board.san(d1K), "d1=K")
        self.assertEqual(board.parse_san("d1=K"), d1K)


class AtomicTestCase(unittest.TestCase):

    def test_atomic_capture(self):
        fen = "rnbqkb1r/pp2pppp/2p2n2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq - 3 4"
        board = chess.variant.AtomicBoard(fen)
        board.push_san("dxc4")
        self.assertEqual(board.fen(), "rnbqkb1r/pp2pppp/2p2n2/8/3P4/5N2/PP2PPPP/R1BQKB1R w KQkq - 0 5")
        board.pop()
        self.assertEqual(board.fen(), fen)

    def test_atomic_mate_legality(self):
        # We are in check. Not just any move will do.
        board = chess.variant.AtomicBoard("8/8/1Q2pk2/8/8/8/3K4/1n6 w - - 0 1")
        self.assertTrue(board.is_check())
        Qa7 = chess.Move.from_uci("b6a7")
        self.assertTrue(board.is_pseudo_legal(Qa7))
        self.assertFalse(board.is_legal(Qa7))
        self.assertNotIn(Qa7, board.generate_legal_moves())

        # Ignore check to explode the opponents king.
        Qxe6 = board.parse_san("Qxe6#")
        self.assertTrue(board.is_legal(Qxe6))
        self.assertIn(Qxe6, board.generate_legal_moves())

        # Exploding both kings is not a legal check evasion.
        board = chess.variant.AtomicBoard("8/8/8/2K5/2P5/2k1n3/8/2R5 b - - 0 1")
        Nxc4 = chess.Move.from_uci("e3c4")
        self.assertTrue(board.is_pseudo_legal(Nxc4))
        self.assertFalse(board.is_legal(Nxc4))
        self.assertNotIn(Nxc4, board.generate_legal_moves())

    def test_atomic_en_passant(self):
        # Real world position.
        board = chess.variant.AtomicBoard("rn2kb1r/2p1p2p/p2q1pp1/1pPP4/Q7/4P3/PP3P1P/R3K3 w Qkq b6 0 11")
        board.push_san("cxb6+")
        self.assertEqual(board.fen(), "rn2kb1r/2p1p2p/p2q1pp1/3P4/Q7/4P3/PP3P1P/R3K3 b Qkq - 0 11")

        # Test the explosion radius.
        board = chess.variant.AtomicBoard("3kK3/8/8/2NNNNN1/2NN1pN1/2NN1NN1/2NNPNN1/2NNNNN1 w - - 0 1")
        board.push_san("e4")
        board.push_san("fxe3")
        self.assertEqual(board.fen(), "3kK3/8/8/2NNNNN1/2N3N1/2N3N1/2N3N1/2NNNNN1 w - - 0 2")

    def test_atomic_insufficient_material(self):
        # Starting position.
        board = chess.variant.AtomicBoard()
        self.assertFalse(board.is_insufficient_material())

        # Single rook.
        board = chess.variant.AtomicBoard("8/3k4/8/8/4R3/4K3/8/8 w - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # Only bishops but no captures possible.
        board = chess.variant.AtomicBoard("7k/4b3/8/8/8/3B4/2B5/K7 w - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # Bishops of both sides on the same color complex.
        board = chess.variant.AtomicBoard("7k/3b4/8/8/8/3B4/2B5/K7 w - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Knights on both sides.
        board = chess.variant.AtomicBoard("8/1n6/1k6/8/8/8/3KN3/8 w - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Two knights can not win.
        board = chess.variant.AtomicBoard("8/1nn5/1k6/8/8/8/3K4/8 w - - 0 1")
        self.assertTrue(board.is_insufficient_material())

    def test_castling_uncovered_rank_attack(self):
        board = chess.variant.AtomicBoard("8/8/8/8/8/8/4k3/rR4KR w KQ - 0 1", chess960=True)
        self.assertFalse(board.is_legal(chess.Move.from_uci("g1b1")))

        # Kings are touching at the end.
        board = chess.variant.AtomicBoard("8/8/8/8/8/8/2k5/rR4KR w KQ - 0 1", chess960=True)
        self.assertTrue(board.is_legal(chess.Move.from_uci("g1b1")))

    def test_atomic_castle_with_kings_touching(self):
        board = chess.variant.AtomicBoard("5b1r/1p5p/4ppp1/4Bn2/1PPP1PP1/4P2P/3k4/4K2R w K - 1 1")
        board.push_san("O-O")
        self.assertEqual(board.fen(), "5b1r/1p5p/4ppp1/4Bn2/1PPP1PP1/4P2P/3k4/5RK1 b - - 2 1")

    def test_lone_king_wdl(self):
        tables = chess.syzygy.Tablebases(VariantBoard=chess.variant.AtomicBoard)
        board = chess.variant.AtomicBoard.empty()
        board.set_piece_at(chess.D1, chess.Piece.from_symbol("k"))
        self.assertEqual(tables.probe_wdl(board), -2)


class RacingKingsTestCase(unittest.TestCase):

    def test_variant_end(self):
        board = chess.variant.RacingKingsBoard()
        board.push_san("Nxc2")
        self.assertFalse(board.is_variant_draw())
        self.assertFalse(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())

        # Black is given a chance to catch up.
        board = chess.variant.RacingKingsBoard("1K6/7k/8/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_game_over())

        board.push_san("Kg7")  # ??
        self.assertFalse(board.is_variant_draw())
        self.assertTrue(board.is_variant_win())
        self.assertFalse(board.is_variant_loss())

        # White to move is lost, because black reached the backrank.
        board = chess.variant.RacingKingsBoard("1k6/6K1/8/8/8/8/8/8 w - - 0 1")
        self.assertFalse(board.is_variant_draw())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_loss())

        # Black to move is lost, because they cannot reach the backrank.
        board = chess.variant.RacingKingsBoard("5RK1/1k6/8/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_variant_draw())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_loss())

    def test_stalemate(self):
        board = chess.variant.RacingKingsBoard("1Q4R1/5K2/4B3/8/8/3N4/8/k7 b - - 0 1")
        self.assertTrue(board.is_game_over())
        self.assertTrue(board.is_stalemate())
        self.assertFalse(board.is_variant_win())
        self.assertFalse(board.is_variant_draw())
        self.assertFalse(board.is_variant_loss())
        self.assertEqual(board.result(), "1/2-1/2")

        # Here white already reached the backrank.
        board = chess.variant.RacingKingsBoard("4Q1K1/8/7k/4R3/8/5B2/8/3N4 b - - 0 1")
        self.assertTrue(board.is_game_over())
        self.assertFalse(board.is_stalemate())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_variant_draw())
        self.assertEqual(board.result(), "1-0")

    def test_race_over(self):
        self.assertTrue(chess.variant.RacingKingsBoard().is_valid())

        # This position with black to move and both kings on the backrank is
        # invalid because the race should have been over already.
        board = chess.variant.RacingKingsBoard("3krQK1/8/8/8/1q6/3B1N2/1b6/1R4R1 b - - 0 0")
        self.assertEqual(board.status(), chess.STATUS_RACE_OVER)

    def test_race_material(self):
        board = chess.variant.RacingKingsBoard()

        # Switch color of the black rook.
        board.set_piece_at(chess.B1, chess.Piece.from_symbol("R"))
        self.assertEqual(board.status(), chess.STATUS_RACE_MATERIAL)

    def test_legal_moves_after_end(self):
        board = chess.variant.RacingKingsBoard("1k5b/5b2/8/8/8/8/3N3K/N4B2 w - - 0 1")
        self.assertTrue(board.is_variant_end())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_stalemate())
        self.assertFalse(any(board.generate_legal_moves()))


class HordeTestCase(unittest.TestCase):

    def test_status(self):
        board = chess.variant.HordeBoard()
        self.assertEqual(board.status(), chess.STATUS_VALID)

    def test_double_pawn_push(self):
        board = chess.variant.HordeBoard("8/8/8/8/8/3k1p2/8/PPPPPPPP w - - 0 1")

        # Double pawn push blocked by king.
        self.assertNotIn(chess.Move.from_uci("d1d3"), board.generate_legal_moves())

        # Double pawn push from backrank possible.
        self.assertIn(chess.Move.from_uci("e1e2"), board.generate_legal_moves())
        self.assertTrue(board.is_legal(board.parse_san("e2")))
        self.assertIn(chess.Move.from_uci("e1e3"), board.generate_legal_moves())
        self.assertTrue(board.is_legal(board.parse_san("e3")))

        # En-passant not possible.
        board.push_san("e3")
        self.assertFalse(any(board.generate_pseudo_legal_ep()))


class ThreeCheckTestCase(unittest.TestCase):

    def test_get_fen(self):
        board = chess.variant.ThreeCheckBoard()
        self.assertEqual(board.fen(), chess.variant.ThreeCheckBoard.starting_fen)
        self.assertEqual(board.epd(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 3+3")

        board.push_san("e4")
        board.push_san("e5")
        board.push_san("Qf3")
        board.push_san("Nc6")
        board.push_san("Qxf7+")
        self.assertEqual(board.fen(), "r1bqkbnr/pppp1Qpp/2n5/4p3/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 2+3 0 3")

        lichess_fen = "r1bqkbnr/pppp1Qpp/2n5/4p3/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 0 3 +1+0"
        self.assertEqual(board.fen(), chess.variant.ThreeCheckBoard(lichess_fen).fen())

    def test_copy(self):
        fen = "8/8/1K2p3/3qP2k/8/8/8/8 b - - 2+1 3 57"
        board = chess.variant.ThreeCheckBoard(fen)
        self.assertEqual(board.copy().fen(), fen)

    def test_lichess_fen(self):
        board = chess.variant.ThreeCheckBoard("8/8/1K2p3/3qP2k/8/8/8/8 b - - 3 57 +1+2")
        self.assertEqual(board.remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.remaining_checks[chess.BLACK], 1)

    def test_set_epd(self):
        epd = "4r3/ppk3p1/4b2p/2ppPp2/5P2/2P3P1/PP1N2P1/3R2K1 w - - 1+3 foo \"bar\";"
        board, extra = chess.variant.ThreeCheckBoard.from_epd(epd)
        self.assertEqual(board.epd(), "4r3/ppk3p1/4b2p/2ppPp2/5P2/2P3P1/PP1N2P1/3R2K1 w - - 1+3")
        self.assertEqual(extra["foo"], "bar")

    def test_check_is_irreversible(self):
        board = chess.variant.ThreeCheckBoard()

        move = board.parse_san("Nf3")
        self.assertFalse(board.is_irreversible(move))
        board.push(move)

        move = board.parse_san("e5")
        self.assertTrue(board.is_irreversible(move))
        board.push(move)

        move = board.parse_san("Nxe5")
        self.assertTrue(board.is_irreversible(move))
        board.push(move)

        # Loses castling rights.
        move = board.parse_san("Ke7")
        self.assertTrue(board.is_irreversible(move))
        board.push(move)

        # Gives a check.
        move = board.parse_san("Nc6+")
        self.assertTrue(board.is_irreversible(move))

    def test_three_check_eq(self):
        a = chess.variant.ThreeCheckBoard()
        a.push_san("e4")

        b = chess.variant.ThreeCheckBoard("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1 +0+0")
        c = chess.variant.ThreeCheckBoard("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1 +0+1")

        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(b, c)


class CrazyhouseTestCase(unittest.TestCase):

    def test_pawn_drop(self):
        board = chess.variant.CrazyhouseBoard("r2q1rk1/ppp2pp1/1bnp3p/3B4/3PP1b1/4PN2/PP4PP/R2Q1RK1[BNPnp] b - - 0 13")
        P_at_e6 = chess.Move.from_uci("P@e6")
        self.assertIn(chess.E6, board.legal_drop_squares())
        self.assertIn(P_at_e6, board.generate_legal_moves())
        self.assertTrue(board.is_pseudo_legal(P_at_e6))
        self.assertTrue(board.is_legal(P_at_e6))

    def test_lichess_pgn(self):
        with open("data/pgn/saturs-jannlee-zh-lichess.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            final_board = game.end().board()
            self.assertEqual(final_board.fen(), "r4r2/ppp2ppk/pb1p1pNp/K2NpP2/3qn3/1B3b2/PP5P/8[QRRBNPP] w - - 8 62")
            self.assertTrue(final_board.is_valid())

        with open("data/pgn/knightvuillaume-jannlee-zh-lichess.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.end().board().move_stack[23], chess.Move.from_uci("N@f3"))

    def test_pawns_in_pocket(self):
        board = chess.variant.CrazyhouseBoard("r2q1rk1/ppp2pp1/1bnp3p/3Bp3/4P1b1/2PPPN2/PP4PP/R2Q1RK1/NBn w - - 22 12")
        board.push_san("d4")
        board.push_san("exd4")
        board.push_san("cxd4")
        self.assertEqual(board.fen(), "r2q1rk1/ppp2pp1/1bnp3p/3B4/3PP1b1/4PN2/PP4PP/R2Q1RK1[BNPnp] b - - 0 13")
        board.push_san("@e6")
        self.assertEqual(board.fen(), "r2q1rk1/ppp2pp1/1bnpp2p/3B4/3PP1b1/4PN2/PP4PP/R2Q1RK1[BNPn] w - - 1 14")

    def test_capture(self):
        board = chess.variant.CrazyhouseBoard("4k3/8/8/1n6/8/3B4/8/4K3 w - - 0 1")
        board.push_san("Bxb5+")
        self.assertEqual(board.fen(), "4k3/8/8/1B6/8/8/8/4K3[N] b - - 0 1")
        board.pop()
        self.assertEqual(board.fen(), "4k3/8/8/1n6/8/3B4/8/4K3[] w - - 0 1")

    def test_capture_with_promotion(self):
        board = chess.variant.CrazyhouseBoard("4k3/8/8/8/8/8/1p6/2R1K3 b - - 0 1")
        move = board.parse_san("bxc1=Q")
        self.assertFalse(board.is_irreversible(move))
        board.push(move)
        self.assertEqual(board.fen(), "4k3/8/8/8/8/8/8/2q~1K3[r] w - - 0 2")
        board.pop()
        self.assertEqual(board.fen(), "4k3/8/8/8/8/8/1p6/2R1K3[] b - - 0 1")

    def test_uci_info_handler(self):
        fen = "3r1r1k/p1p1Ppp1/2Np1n2/2b1p1N1/4P1bq/3P4/PPP2PPP/R4RK1[QBPbn] b - - 35 18"
        board = chess.variant.CrazyhouseBoard(fen)
        bestmove = board.parse_uci("B@f4")

        engine = chess.uci.Engine()
        mock = chess.uci.MockProcess(engine)
        info_handler = chess.uci.InfoHandler()
        engine.info_handlers.append(info_handler)

        mock.expect("setoption name UCI_Variant value crazyhouse")
        mock.expect("isready", ("readyok", ))
        engine.setoption({"UCI_Variant": type(board).uci_variant})

        mock.expect("position fen %s" % fen)
        engine.position(board)

        mock.expect("go", ("info pv B@f4 P@g3", "bestmove B@f4"))
        self.assertEqual(engine.go().bestmove, bestmove)
        mock.assert_done()

    def test_illegal_drop_uci(self):
        board = chess.variant.CrazyhouseBoard()
        with self.assertRaises(ValueError):
            board.parse_uci("N@f3")

    def test_crazyhouse_fen(self):
        fen = "r3kb1r/p1pN1ppp/2p1p3/8/2Pn4/3Q4/PP3PPP/R1B2q~K1[] w kq - 0 1"
        board = chess.variant.CrazyhouseBoard(fen)
        self.assertEqual(board.fen(), fen)

    def test_push_pop_ep(self):
        fen = "rnbqkb1r/ppp1pppp/5n2/3pP3/8/8/PPPP1PPP/RNBQKBNR[] w KQkq d6 0 3"
        board = chess.variant.CrazyhouseBoard(fen)
        board.push_san("exd6")
        self.assertEqual(board.fen(), "rnbqkb1r/ppp1pppp/3P1n2/8/8/8/PPPP1PPP/RNBQKBNR[P] b KQkq - 0 3")
        self.assertEqual(board.pop(), chess.Move.from_uci("e5d6"))
        self.assertEqual(board.fen(), fen)

    def test_crazyhouse_insufficient_material(self):
        board = chess.variant.CrazyhouseBoard()
        self.assertFalse(board.is_insufficient_material())

        board = chess.variant.CrazyhouseBoard.empty()
        self.assertTrue(board.is_insufficient_material())

        board.pockets[chess.WHITE].add(chess.PAWN)
        self.assertFalse(board.is_insufficient_material())


class GiveawayTestCase(unittest.TestCase):

    def test_antichess_pgn(self):
        with open("data/pgn/antichess-programfox.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.end().board().fen(), "8/2k5/8/8/8/8/6b1/8 w - - 0 32")

            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.end().board().fen(), "8/6k1/3K4/8/8/3k4/8/8 w - - 4 33")


if __name__ == "__main__":
    verbosity = sum(arg.count("v") for arg in sys.argv if all(c == "v" for c in arg.lstrip("-")))
    verbosity += sys.argv.count("--verbose")

    if verbosity >= 2:
        logging.basicConfig(level=logging.DEBUG)

    raise_log_handler = RaiseLogHandler()
    raise_log_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(raise_log_handler)

    unittest.main()
