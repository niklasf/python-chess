#!/usr/bin/env python3
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2021 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

import asyncio
import copy
import logging
import os
import os.path
import platform
import sys
import tempfile
import textwrap
import unittest
import io

import chess
import chess.gaviota
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant


class RaiseLogHandler(logging.StreamHandler):
    def handle(self, record):
        super().handle(record)
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
            self.assertEqual(chess.square(file_index, rank_index), square, chess.square_name(square))

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

    def test_parse_square(self):
        self.assertEqual(chess.parse_square("a1"), 0)
        with self.assertRaises(ValueError):
            self.assertEqual(chess.parse_square("A1"))
        with self.assertRaises(ValueError):
            self.assertEqual(chess.parse_square("a0"))

    def test_square_distance(self):
        self.assertEqual(chess.square_distance(chess.A1, chess.A1), 0)
        self.assertEqual(chess.square_distance(chess.A1, chess.H8), 7)
        self.assertEqual(chess.square_distance(chess.E1, chess.E8), 7)
        self.assertEqual(chess.square_distance(chess.A4, chess.H4), 7)
        self.assertEqual(chess.square_distance(chess.D4, chess.E5), 1)

    def test_square_manhattan_distance(self):
        self.assertEqual(chess.square_manhattan_distance(chess.A1, chess.A1), 0)
        self.assertEqual(chess.square_manhattan_distance(chess.A1, chess.H8), 14)
        self.assertEqual(chess.square_manhattan_distance(chess.E1, chess.E8), 7)
        self.assertEqual(chess.square_manhattan_distance(chess.A4, chess.H4), 7)
        self.assertEqual(chess.square_manhattan_distance(chess.D4, chess.E5), 2)

    def test_square_knight_distance(self):
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.A1), 0)
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.H8), 6)
        self.assertEqual(chess.square_knight_distance(chess.G1, chess.F3), 1)
        self.assertEqual(chess.square_knight_distance(chess.E1, chess.E8), 5)
        self.assertEqual(chess.square_knight_distance(chess.A4, chess.H4), 5)
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.B1), 3)
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.C3), 4)
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.B2), 4)
        self.assertEqual(chess.square_knight_distance(chess.C1, chess.B2), 2)


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
        self.assertEqual(chess.Move.from_uci("0000").uci(), "0000")

    def test_invalid_uci(self):
        with self.assertRaises(chess.InvalidMoveError):
            chess.Move.from_uci("")

        with self.assertRaises(chess.InvalidMoveError):
            chess.Move.from_uci("N")

        with self.assertRaises(chess.InvalidMoveError):
            chess.Move.from_uci("z1g3")

        with self.assertRaises(chess.InvalidMoveError):
            chess.Move.from_uci("Q@g9")

    def test_xboard_move(self):
        self.assertEqual(chess.Move.from_uci("b5c7").xboard(), "b5c7")
        self.assertEqual(chess.Move.from_uci("e7e8q").xboard(), "e7e8q")
        self.assertEqual(chess.Move.from_uci("P@e4").xboard(), "P@e4")
        self.assertEqual(chess.Move.from_uci("B@f4").xboard(), "B@f4")
        self.assertEqual(chess.Move.from_uci("0000").xboard(), "@@@@")

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

        self.assertEqual(len(set([a, b, c, d1, d2])), 3)

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
        self.assertEqual(str(white_knight), "N")

        black_queen = chess.Piece.from_symbol("q")

        self.assertEqual(black_queen.color, chess.BLACK)
        self.assertEqual(black_queen.piece_type, chess.QUEEN)
        self.assertEqual(black_queen.symbol(), "q")
        self.assertEqual(str(black_queen), "q")

    def test_hash(self):
        pieces = {chess.Piece.from_symbol(symbol) for symbol in  "pnbrqkPNBRQK"}
        self.assertEqual(len(pieces), 12)
        hashes = {hash(piece) for piece in pieces}
        self.assertEqual(hashes, set(range(12)))


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

    def test_ply(self):
        board = chess.Board()
        self.assertEqual(board.ply(), 0)
        board.push_san("d4")
        self.assertEqual(board.ply(), 1)
        board.push_san("d5")
        self.assertEqual(board.ply(), 2)
        board.clear_stack()
        self.assertEqual(board.ply(), 2)
        board.push_san("Nf3")
        self.assertEqual(board.ply(), 3)

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

        # Illegal en passant square on illegal board.
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

        board.set_piece_at(chess.H7, None)
        self.assertEqual(board.promoted, chess.BB_EMPTY)
        self.assertEqual(board.piece_at(chess.H7), None)

    def test_color_at(self):
        board = chess.Board()
        self.assertEqual(board.color_at(chess.A1), chess.WHITE)
        self.assertEqual(board.color_at(chess.G7), chess.BLACK)
        self.assertEqual(board.color_at(chess.E4), None)

    def test_pawn_captures(self):
        board = chess.Board()

        # King's Gambit.
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
        move = board.parse_xboard("O-O")
        self.assertEqual(move, chess.Move.from_uci("e1g1"))
        self.assertEqual(board.san(move), "O-O")
        self.assertEqual(board.xboard(move), "e1g1")
        self.assertIn(move, board.legal_moves)
        board.push(move)

        # Let black castle long.
        move = board.parse_xboard("O-O-O")
        self.assertEqual(board.san(move), "O-O-O")
        self.assertEqual(board.xboard(move), "e8c8")
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

    def test_castling_san(self):
        board = chess.Board("4k3/8/8/8/8/8/8/4K2R w K - 0 1")
        self.assertEqual(board.parse_san("O-O"), chess.Move.from_uci("e1g1"))
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_san("Kg1")
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_san("Kh1")

    def test_ninesixty_castling(self):
        fen = "3r1k1r/4pp2/8/8/8/8/8/4RKR1 w Gd - 1 1"
        board = chess.Board(fen, chess960=True)

        # Let white do the kingside swap.
        move = board.parse_san("O-O")
        self.assertEqual(board.san(move), "O-O")
        self.assertEqual(board.xboard(move), "O-O")
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
        self.assertEqual(board.xboard(move), "O-O-O")
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

    def test_hside_rook_blocks_aside_castling(self):
        board = chess.Board("4rrk1/pbbp2p1/1ppnp3/3n1pqp/3N1PQP/1PPNP3/PBBP2P1/4RRK1 w Ff - 10 18", chess960=True)
        self.assertNotIn(chess.Move.from_uci("g1f1"), board.legal_moves)
        self.assertNotIn(chess.Move.from_uci("g1e1"), board.legal_moves)
        self.assertNotIn(chess.Move.from_uci("g1c1"), board.legal_moves)
        self.assertNotIn(chess.Move.from_uci("g1a1"), board.legal_moves)
        self.assertIn(chess.Move.from_uci("g1h1"), board.legal_moves)  # Kh1

    def test_selective_castling(self):
        board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")

        # King not selected.
        self.assertFalse(any(board.generate_castling_moves(chess.BB_ALL & ~board.kings)))

        # Rook on h1 not selected.
        moves = board.generate_castling_moves(chess.BB_ALL, chess.BB_ALL & ~chess.BB_H1)
        self.assertEqual(len(list(moves)), 1)

    def test_castling_right_not_destroyed_bug(self):
        # A rook move from h8 to h1 was only taking white's possible castling
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
        # Theoretically, this position (with castling rights) can not be reached
        # with a series of legal moves from one of the 960 starting positions.
        # Decision: We don't care, neither do Stockfish or lichess.org.
        fen = "1r1k1r2/5p2/8/8/8/8/3N4/R5KR b KQkq - 0 1"
        board = chess.Board(fen, chess960=True)
        self.assertEqual(board.fen(), fen)

    def test_ninesixty_prevented_castle(self):
        board = chess.Board("4k3/8/8/1b6/8/8/8/5RKR w KQ - 0 1", chess960=True)
        self.assertFalse(board.is_legal(chess.Move.from_uci("g1f1")))

    def test_find_move(self):
        board = chess.Board("4k3/1P6/8/8/8/8/3P4/4K2R w K - 0 1")

        # Pawn moves.
        self.assertEqual(board.find_move(chess.D2, chess.D4), chess.Move.from_uci("d2d4"))
        self.assertEqual(board.find_move(chess.B7, chess.B8), chess.Move.from_uci("b7b8q"))
        self.assertEqual(board.find_move(chess.B7, chess.B8, chess.KNIGHT), chess.Move.from_uci("b7b8n"))

        # Illegal moves.
        with self.assertRaises(chess.IllegalMoveError):
            board.find_move(chess.D2, chess.D8)
        with self.assertRaises(chess.IllegalMoveError):
            board.find_move(chess.E1, chess.A1)

        # Castling.
        self.assertEqual(board.find_move(chess.E1, chess.G1), chess.Move.from_uci("e1g1"))
        self.assertEqual(board.find_move(chess.E1, chess.H1), chess.Move.from_uci("e1g1"))
        board.chess960 = True
        self.assertEqual(board.find_move(chess.E1, chess.H1), chess.Move.from_uci("e1h1"))

    def test_clean_castling_rights(self):
        board = chess.Board()
        board.set_board_fen("k6K/8/8/pppppppp/8/8/8/QqQq4")
        self.assertEqual(board.clean_castling_rights(), chess.BB_EMPTY)
        self.assertEqual(board.fen(), "k6K/8/8/pppppppp/8/8/8/QqQq4 w - - 0 1")
        board.push_san("Qxc5")
        self.assertEqual(board.clean_castling_rights(), chess.BB_EMPTY)
        self.assertEqual(board.fen(), "k6K/8/8/ppQppppp/8/8/8/Qq1q4 b - - 0 1")

    def test_insufficient_material(self):
        def _check(board, white, black):
            self.assertEqual(board.has_insufficient_material(chess.WHITE), white)
            self.assertEqual(board.has_insufficient_material(chess.BLACK), black)
            self.assertEqual(board.is_insufficient_material(), white and black)

        # Imperfect implementation.
        false_negative = False

        _check(chess.Board(), False, False)
        _check(chess.Board("k1K1B1B1/8/8/8/8/8/8/8 w - - 7 32"), True, True)
        _check(chess.Board("kbK1B1B1/8/8/8/8/8/8/8 w - - 7 32"), False, False)
        _check(chess.Board("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), True, True)
        _check(chess.Board("8/3k4/8/8/2N5/8/3K4/8 b - - 0 1"), True, True)
        _check(chess.Board("8/4rk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
        _check(chess.Board("8/4qk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
        _check(chess.Board("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
        _check(chess.Board("8/8/3Q4/2bK4/B7/8/1k6/8 w - - 1 68"), False, False)
        _check(chess.Board("8/5k2/8/8/8/4B3/3K1B2/8 w - - 0 1"), True, True)
        _check(chess.Board("5K2/8/8/1B6/8/k7/6b1/8 w - - 0 39"), True, True)
        _check(chess.Board("8/8/8/4k3/5b2/3K4/8/2B5 w - - 0 33"), True, True)
        _check(chess.Board("3b4/8/8/6b1/8/8/R7/K1k5 w - - 0 1"), False, True)

        _check(chess.variant.AtomicBoard("8/3k4/8/8/2N5/8/3K4/8 b - - 0 1"), True, True)
        _check(chess.variant.AtomicBoard("8/4rk2/8/8/8/8/3K4/8 w - - 0 1"), True, True)
        _check(chess.variant.AtomicBoard("8/4qk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
        _check(chess.variant.AtomicBoard("8/1k6/8/2n5/8/3NK3/8/8 b - - 0 1"), False, False)
        _check(chess.variant.AtomicBoard("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), True, True)
        _check(chess.variant.AtomicBoard("4b3/5k2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
        _check(chess.variant.AtomicBoard("3Q4/5kKB/8/8/8/8/8/8 b - - 0 1"), False, True)
        _check(chess.variant.AtomicBoard("8/5k2/8/8/8/8/5K2/4bb2 w - - 0 1"), True, False)
        _check(chess.variant.AtomicBoard("8/5k2/8/8/8/8/5K2/4nb2 w - - 0 1"), True, False)

        _check(chess.variant.GiveawayBoard("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
        _check(chess.variant.GiveawayBoard("4b3/5k2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
        _check(chess.variant.GiveawayBoard("8/8/8/6b1/8/3B4/4B3/5B2 w - - 0 1"), True, True)
        _check(chess.variant.GiveawayBoard("8/8/5b2/8/8/3B4/3B4/8 w - - 0 1"), True, False)
        _check(chess.variant.SuicideBoard("8/5p2/5P2/8/3B4/1bB5/8/8 b - - 0 1"), false_negative, false_negative)
        _check(chess.variant.AntichessBoard("8/8/8/1n2N3/8/8/8/8 w - - 0 32"), True, False)
        _check(chess.variant.AntichessBoard("8/3N4/8/1n6/8/8/8/8 b - - 1 32"), True, False)
        _check(chess.variant.AntichessBoard("6n1/8/8/4N3/8/8/8/8 b - - 0 27"), False, True)
        _check(chess.variant.AntichessBoard("8/8/5n2/4N3/8/8/8/8 w - - 1 28"), False, True)
        _check(chess.variant.AntichessBoard("8/3n4/8/8/8/8/8/8 w - - 0 29"), False, True)

        _check(chess.variant.KingOfTheHillBoard("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), False, False)

        _check(chess.variant.RacingKingsBoard("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), False, False)

        _check(chess.variant.ThreeCheckBoard("8/5k2/8/8/8/8/3K4/8 w - - 3+3 0 1"), True, True)
        _check(chess.variant.ThreeCheckBoard("8/5k2/8/8/8/8/3K2N1/8 w - - 3+3 0 1"), False, True)

        _check(chess.variant.CrazyhouseBoard("8/5k2/8/8/8/8/3K2N1/8[] w - - 0 1"), True, True)
        _check(chess.variant.CrazyhouseBoard("8/5k2/8/8/8/5B2/3KB3/8[] w - - 0 1"), False, False)
        _check(chess.variant.CrazyhouseBoard("8/8/8/8/3k4/3N~4/3K4/8 w - - 0 1"), False, False)

        _check(chess.variant.HordeBoard("8/5k2/8/8/8/4NN2/8/8 w - - 0 1"), True, False)
        _check(chess.variant.HordeBoard("8/1b5r/1P6/1Pk3q1/1PP5/r1P5/P1P5/2P5 b - - 0 52"), False, False)

    def test_promotion_with_check(self):
        board = chess.Board("8/6P1/2p5/1Pqk4/6P1/2P1RKP1/4P1P1/8 w - - 0 1")
        board.push(chess.Move.from_uci("g7g8q"))
        self.assertTrue(board.is_check())
        self.assertEqual(board.fen(), "6Q1/8/2p5/1Pqk4/6P1/2P1RKP1/4P1P1/8 b - - 0 1")

        board = chess.Board("8/8/8/3R1P2/8/2k2K2/3p4/r7 b - - 0 82")
        board.push_san("d1=Q+")
        self.assertEqual(board.fen(), "8/8/8/3R1P2/8/2k2K2/8/r2q4 w - - 0 83")

    def test_ambiguous_move(self):
        board = chess.Board("8/8/1n6/3R1P2/1n6/2k2K2/3p4/r6r b - - 0 82")
        with self.assertRaises(chess.AmbiguousMoveError):
            board.parse_san("Rf1")
        with self.assertRaises(chess.AmbiguousMoveError):
            board.parse_san("Nd5")

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
        board = chess.Board("rnbqk2r/ppppppbp/5np1/8/8/5NP1/PPPPPPBP/RNBQK2R w KQkq - 2 4")
        with self.assertRaises(chess.InvalidMoveError):
            board.parse_san("O-O\n")
        with self.assertRaises(chess.InvalidMoveError):
            board.parse_san("Nc3\n")

    def test_pawn_capture_san_without_file(self):
        board = chess.Board("2rq1rk1/pb2bppp/1p2p3/n1ppPn2/2PP4/PP3N2/1B1NQPPP/RB3RK1 b - - 4 13")
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_san("c4")
        board = chess.Board("4k3/8/8/4Pp2/8/8/8/4K3 w - f6 0 2")
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_san("f6")

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
        with self.assertRaises(chess.IllegalMoveError) as err:
            board.variation_san([chess.Move.from_uci(m) for m in illegal_variation])
        message = str(err.exception)
        self.assertIn('illegal move', message.lower(),
                      msg=f"Error [{message}] mentions illegal move")
        self.assertIn('f3h6', message,
                      msg=f"Illegal move f3h6 appears in message [{message}]")

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
        # Test Polyglot compatibility using test data from
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

        # Generate all pseudo-legal moves, two moves deep.
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

        # Generate all pseudo-legal moves.
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

        # Opposite check.
        board = chess.Board("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_OPPOSITE_CHECK)

        # Empty board.
        board = chess.Board(None)
        self.assertEqual(board.status(), chess.STATUS_EMPTY | chess.STATUS_NO_WHITE_KING | chess.STATUS_NO_BLACK_KING)

        # Too many kings.
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKKBNR w KQkq - 0 1")
        self.assertEqual(board.status(), chess.STATUS_TOO_MANY_KINGS)

        # Triple check.
        board = chess.Board("4k3/5P2/3N4/8/8/8/4R3/4K3 b - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_TOO_MANY_CHECKERS | chess.STATUS_IMPOSSIBLE_CHECK)

        # Impossible checker alignment.
        board = chess.Board("3R4/8/q4k2/2B5/1NK5/3b4/8/8 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)
        board = chess.Board("2Nq4/2K5/1b6/8/7R/3k4/7P/8 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)
        board = chess.Board("5R2/2P5/8/4k3/8/3rK2r/8/8 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)
        board = chess.Board("8/8/8/1k6/3Pp3/8/8/4KQ2 b - d3 0 1")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)

        # Checkers aligned with opponent king are fine.
        board = chess.Board("8/8/5k2/p1q5/PP1rp1P1/3P1N2/2RK1r2/5nN1 w - - 0 3")
        self.assertEqual(board.status(), chess.STATUS_VALID)

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

        # Create an EPD with numbers.
        self.assertEqual(board.epd(pi=3.14), "4k3/8/8/8/8/8/8/4K3 w - - pi 3.14;")

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
        self.assertEqual(epd, "8/8/8/4k3/8/1K6/8/8 b - - bm Ke4 Ke6;")

        # Test loading an EPD.
        board = chess.Board()
        operations = board.set_epd("r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - bm f4; id \"BK.24\";")
        self.assertEqual(board.fen(), "r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - 0 1")
        self.assertIn(chess.Move(chess.F2, chess.F4), operations["bm"])
        self.assertEqual(operations["id"], "BK.24")

        # Test loading an EPD with half-move counter operations.
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

        # Test EPD with semicolon.
        board = chess.Board()
        operations = board.set_epd("r2qk2r/ppp1b1pp/2n1p3/3pP1n1/3P2b1/2PB1NN1/PP4PP/R1BQK2R w KQkq - bm Nxg5; c0 \"ERET.095; Queen sacrifice\";")
        self.assertEqual(operations["bm"], [chess.Move.from_uci("f3g5")])
        self.assertEqual(operations["c0"], "ERET.095; Queen sacrifice")

        # Test EPD with string escaping.
        board = chess.Board()
        operations = board.set_epd(r"""4k3/8/8/8/8/8/8/4K3 w - - a "foo\"bar";; ; b "foo\\\\";""")
        self.assertEqual(operations["a"], "foo\"bar")
        self.assertEqual(operations["b"], "foo\\\\")

        # Test EPD with unmatched trailing quotes.
        board = chess.Board()
        operations = board.set_epd("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"")
        self.assertEqual(operations["bm"], [chess.Move.from_uci("d6d1")])
        self.assertEqual(operations["id"], "")
        self.assertEqual(board.epd(**operations), "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"\";")

    def test_eret_epd(self):
        # Too many dashes.
        epd = """r1bqk1r1/1p1p1n2/p1n2pN1/2p1b2Q/2P1Pp2/1PN5/PB4PP/R4RK1 w q - - bm Rxf4; id "ERET 001 - Entlastung";"""
        board, ops = chess.Board.from_epd(epd)
        self.assertEqual(ops["id"], "ERET 001 - Entlastung")
        self.assertEqual(ops["bm"], [chess.Move.from_uci("f1f4")])

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
        self.assertEqual(attackers, chess.BB_EMPTY)

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

        pawn_attacks = board.attacks(chess.B2)
        self.assertIn(chess.A3, pawn_attacks)
        self.assertNotIn(chess.B3, pawn_attacks)

        self.assertFalse(board.attacks(chess.G1))

    def test_clear(self):
        board = chess.Board()
        board.clear()

        self.assertEqual(board.turn, chess.WHITE)
        self.assertEqual(board.fullmove_number, 1)
        self.assertEqual(board.halfmove_clock, 0)
        self.assertEqual(board.castling_rights, chess.BB_EMPTY)
        self.assertFalse(board.ep_square)

        self.assertFalse(board.piece_at(chess.E1))
        self.assertEqual(chess.popcount(board.occupied), 0)

    def test_threefold_repetition(self):
        board = chess.Board()

        # Go back and forth with the knights to reach the starting position
        # for a second time.
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Nf3")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Nf6")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Ng1")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Ng8")

        # Once more.
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Nf3")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Nf6")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Ng1")

        # Now black can go back to the starting position (thus reaching it a
        # third time).
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Ng8")

        # They indeed do it. Also, white can now claim.
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertTrue(board.is_repetition())

        # But not after a different move.
        board.push_san("e4")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())

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

        # Repeat it once more. Now it is a fivefold repetition.
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

        # Do, in fact, repeat.
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Qd8")

        # This is a threefold repetition, and also a fivefold repetition since
        # it no longer has to occur on consecutive moves.
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertTrue(board.is_fivefold_repetition())
        self.assertEqual(board.fen().split()[0], fen.split()[0])

    def test_trivial_is_repetition(self):
        self.assertTrue(chess.Board().is_repetition(1))

    def test_fifty_moves(self):
        # Test positions from Jan Timman vs. Christopher Lutz (1995).
        board = chess.Board()
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("8/5R2/8/r2KB3/6k1/8/8/8 w - - 19 79")
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("8/8/6r1/4B3/8/4K2k/5R2/8 b - - 68 103")
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("6R1/7k/8/8/1r3B2/5K2/8/8 w - - 99 119")
        self.assertFalse(board.is_fifty_moves())
        self.assertTrue(board.can_claim_fifty_moves())
        board = chess.Board("8/7k/8/6R1/1r3B2/5K2/8/8 b - - 100 119")
        self.assertTrue(board.is_fifty_moves())
        self.assertTrue(board.can_claim_fifty_moves())
        board = chess.Board("8/7k/8/1r3KR1/5B2/8/8/8 w - - 105 122")
        self.assertTrue(board.is_fifty_moves())
        self.assertTrue(board.can_claim_fifty_moves())

        # Once checkmated, it is too late to claim.
        board = chess.Board("k7/8/NKB5/8/8/8/8/8 b - - 105 176")
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())

        # A stalemate is a draw, but you can not and do not need to claim it by
        # the fifty-move rule.
        board = chess.Board("k7/3N4/1K6/1B6/8/8/8/8 b - - 99 1")
        self.assertTrue(board.is_stalemate())
        self.assertTrue(board.is_game_over())
        self.assertFalse(board.is_fifty_moves())
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

            # Ensure that all moves generated as pseudo-legal pass the
            # pseudo-legality check.
            for move in pseudo_legal_moves:
                self.assertTrue(board.is_pseudo_legal(move))

            # Check that moves not generated as pseudo-legal do not pass the
            # pseudo-legality check.
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

        self.assertEqual(str(board), textwrap.dedent("""\
            . . . . . . . k
            . p . q n . b .
            p B . p . n . .
            . . . P p . . .
            . . . . P p . p
            . . Q N . B . .
            P P . . . . P P
            . . . . . . K ."""))

        self.assertEqual(board.unicode(empty_square="·"), textwrap.dedent("""\
            · · · · · · · ♚
            · ♟ · ♛ ♞ · ♝ ·
            ♟ ♗ · ♟ · ♞ · ·
            · · · ♙ ♟ · · ·
            · · · · ♙ ♟ · ♟
            · · ♕ ♘ · ♗ · ·
            ♙ ♙ · · · · ♙ ♙
            · · · · · · ♔ ·"""))

        self.assertEqual(board.unicode(invert_color=True, borders=True, empty_square="·"), textwrap.dedent("""\
              -----------------
            8 |·|·|·|·|·|·|·|♔|
              -----------------
            7 |·|♙|·|♕|♘|·|♗|·|
              -----------------
            6 |♙|♝|·|♙|·|♘|·|·|
              -----------------
            5 |·|·|·|♟|♙|·|·|·|
              -----------------
            4 |·|·|·|·|♟|♙|·|♙|
              -----------------
            3 |·|·|♛|♞|·|♝|·|·|
              -----------------
            2 |♟|♟|·|·|·|·|♟|♟|
              -----------------
            1 |·|·|·|·|·|·|♚|·|
              -----------------
               a b c d e f g h"""))

    def test_move_info(self):
        board = chess.Board("r1bqkb1r/p3np2/2n1p2p/1p4pP/2pP4/4PQ1N/1P2BPP1/RNB1K2R w KQkq g6 0 11")

        self.assertTrue(board.is_capture(board.parse_xboard("Qxf7+")))
        self.assertFalse(board.is_en_passant(board.parse_xboard("Qxf7+")))
        self.assertFalse(board.is_castling(board.parse_xboard("Qxf7+")))

        self.assertTrue(board.is_capture(board.parse_xboard("hxg6")))
        self.assertTrue(board.is_en_passant(board.parse_xboard("hxg6")))
        self.assertFalse(board.is_castling(board.parse_xboard("hxg6")))

        self.assertFalse(board.is_capture(board.parse_xboard("b3")))
        self.assertFalse(board.is_en_passant(board.parse_xboard("b3")))
        self.assertFalse(board.is_castling(board.parse_xboard("b3")))

        self.assertFalse(board.is_capture(board.parse_xboard("Ra6")))
        self.assertFalse(board.is_en_passant(board.parse_xboard("Ra6")))
        self.assertFalse(board.is_castling(board.parse_xboard("Ra6")))

        self.assertFalse(board.is_capture(board.parse_xboard("O-O")))
        self.assertFalse(board.is_en_passant(board.parse_xboard("O-O")))
        self.assertTrue(board.is_castling(board.parse_xboard("O-O")))

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

        self.assertEqual(chess.Board(None).pin(chess.WHITE, chess.F7), chess.BB_ALL)

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
        # Horizontal pin. Non-evasion.
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

        # Diagonal attack uncovered. Evasion attempt.
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
        self.assertIn(board.parse_san("exf6"), lc)  # En passant
        self.assertIn(board.parse_san("Bxd3"), lc)
        self.assertEqual(len(lc), 3)

        plc = list(board.generate_pseudo_legal_captures())
        self.assertIn(board.parse_san("Qxd1"), plc)
        self.assertIn(board.parse_san("exf6"), plc)  # En passant
        self.assertIn(board.parse_san("Bxd3"), plc)
        self.assertIn(chess.Move.from_uci("c2c7"), plc)
        self.assertIn(chess.Move.from_uci("c2d3"), plc)
        self.assertEqual(len(plc), 5)

    def test_castling_is_legal(self):
        board = chess.Board("rnbqkbnr/5p2/1pp3pp/p2P4/6P1/2NPpN2/PPP1Q1BP/R3K2R w Qq - 0 11")
        self.assertFalse(board.is_legal(chess.Move.from_uci("e1g1")))
        self.assertFalse(board.is_legal(chess.Move.from_uci("e1h1")))

        board.castling_rights |= chess.BB_H1
        self.assertTrue(board.is_legal(chess.Move.from_uci("e1g1")))
        self.assertTrue(board.is_legal(chess.Move.from_uci("e1h1")))

    def test_from_chess960_pos(self):
        board = chess.Board.from_chess960_pos(909)
        self.assertTrue(board.chess960)
        self.assertEqual(board.fen(), "rkqbrnbn/pppppppp/8/8/8/8/PPPPPPPP/RKQBRNBN w KQkq - 0 1")

    def test_mirror(self):
        board = chess.Board("r1bq1r2/pp2n3/4N2k/3pPppP/1b1n2Q1/2N5/PP3PP1/R1B1K2R w KQ g6 0 15")
        mirrored = chess.Board("r1b1k2r/pp3pp1/2n5/1B1N2q1/3PpPPp/4n2K/PP2N3/R1BQ1R2 b kq g3 0 15")
        self.assertEqual(board.mirror(), mirrored)
        board.apply_mirror()
        self.assertEqual(board, mirrored)

    def test_chess960_pos(self):
        board = chess.Board()

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

    def test_is_irreversible(self):
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1")
        self.assertTrue(board.is_irreversible(board.parse_san("Ra2")))
        self.assertTrue(board.is_irreversible(board.parse_san("O-O-O")))
        self.assertTrue(board.is_irreversible(board.parse_san("Kd1")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxa8")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxh8")))
        self.assertFalse(board.is_irreversible(board.parse_san("Rf1")))
        self.assertFalse(board.is_irreversible(chess.Move.null()))

        board.set_castling_fen("kq")
        self.assertFalse(board.is_irreversible(board.parse_san("Ra2")))
        self.assertFalse(board.is_irreversible(board.parse_san("Kd1")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxa8")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxh8")))
        self.assertFalse(board.is_irreversible(board.parse_san("Rf1")))
        self.assertFalse(board.is_irreversible(chess.Move.null()))

    def test_king_captures_unmoved_rook(self):
        board = chess.Board("8/8/8/B2p3Q/2qPp1P1/b7/2P2PkP/4K2R b K - 0 1")
        move = board.parse_uci("g2h1")
        self.assertFalse(board.is_castling(move))
        self.assertEqual(board.san(move), "Kxh1")
        board.push(move)
        self.assertEqual(board.fen(), "8/8/8/B2p3Q/2qPp1P1/b7/2P2P1P/4K2k w - - 0 2")

    def test_impossible_check_due_to_en_passant(self):
        board = chess.Board("rnbqk1nr/bb3p1p/1q2r3/2pPp3/3P4/7P/1PP1NpPP/R1BQKBNR w KQkq c6")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)
        self.assertEqual(board.ep_square, chess.C6)
        self.assertTrue(board.has_pseudo_legal_en_passant())
        self.assertFalse(board.has_legal_en_passant())
        self.assertEqual(len(list(board.legal_moves)), 2)


class LegalMoveGeneratorTestCase(unittest.TestCase):

    def test_list_conversion(self):
        self.assertEqual(len(list(chess.Board().legal_moves)), 20)

    def test_nonzero(self):
        self.assertTrue(chess.Board().legal_moves)
        self.assertTrue(chess.Board().pseudo_legal_moves)

        caro_kann_mate = chess.Board("r1bqkb1r/pp1npppp/2pN1n2/8/3P4/8/PPP1QPPP/R1B1KBNR b KQkq - 4 6")
        self.assertFalse(caro_kann_mate.legal_moves)
        self.assertTrue(caro_kann_mate.pseudo_legal_moves)

    def test_string_conversion(self):
        board = chess.Board("r3k1nr/ppq1pp1p/2p3p1/8/1PPR4/2N5/P3QPPP/5RK1 b kq b3 0 16")

        self.assertIn("Qxh2+", str(board.legal_moves))
        self.assertIn("Qxh2+", repr(board.legal_moves))

        self.assertIn("Qxh2+", str(board.pseudo_legal_moves))
        self.assertIn("Qxh2+", repr(board.pseudo_legal_moves))
        self.assertIn("e8d7", str(board.pseudo_legal_moves))
        self.assertIn("e8d7", repr(board.pseudo_legal_moves))

    def test_traverse_once(self):
        class MockBoard:
            def __init__(self):
                self.traversals = 0

            def generate_legal_moves(self):
                self.traversals += 1
                return
                yield

        board = MockBoard()
        gen = chess.LegalMoveGenerator(board)
        list(gen)
        self.assertEqual(board.traversals, 1)


class BaseBoardTestCase(unittest.TestCase):

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

        self.assertEqual(int(chess.SquareSet(chess.SquareSet(999))), 999)
        self.assertEqual(chess.SquareSet([chess.B8]), chess.BB_B8)

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
        self.assertEqual(chess.SquareSet(chess.BB_ALL) ^ chess.BB_EMPTY, chess.BB_ALL)
        self.assertEqual(chess.SquareSet(chess.BB_C1) | chess.BB_FILE_C, chess.BB_FILE_C)

        bb = chess.SquareSet(chess.BB_EMPTY)
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
        examples = [
            chess.BB_EMPTY,
            chess.BB_A1,
            chess.BB_A2,
            chess.BB_RANK_1,
            chess.BB_RANK_2,
            chess.BB_FILE_A,
            chess.BB_FILE_E,
        ]

        for a in examples:
            self.assertEqual(chess.SquareSet(a).copy(), a)

        for a in examples:
            a = chess.SquareSet(a)
            for b in examples:
                b = chess.SquareSet(b)
                self.assertEqual(set(a).isdisjoint(set(b)), a.isdisjoint(b))
                self.assertEqual(set(a).issubset(set(b)), a.issubset(b))
                self.assertEqual(set(a).issuperset(set(b)), a.issuperset(b))
                self.assertEqual(set(a).union(set(b)), set(a.union(b)))
                self.assertEqual(set(a).intersection(set(b)), set(a.intersection(b)))
                self.assertEqual(set(a).difference(set(b)), set(a.difference(b)))
                self.assertEqual(set(a).symmetric_difference(set(b)), set(a.symmetric_difference(b)))

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
        self.assertEqual(squares, chess.BB_EMPTY)

        with self.assertRaises(KeyError):
            squares.pop()

        squares.add(chess.C7)
        self.assertEqual(squares.pop(), chess.C7)
        self.assertEqual(squares, chess.BB_EMPTY)

    def test_from_square(self):
        self.assertEqual(chess.SquareSet.from_square(chess.H5), chess.BB_H5)
        self.assertEqual(chess.SquareSet.from_square(chess.C2), chess.BB_C2)

    def test_carry_rippler(self):
        self.assertEqual(sum(1 for _ in chess.SquareSet(chess.BB_D1).carry_rippler()), 2 ** 1)
        self.assertEqual(sum(1 for _ in chess.SquareSet(chess.BB_FILE_B).carry_rippler()), 2 ** 8)

    def test_mirror(self):
        self.assertEqual(chess.SquareSet(0x00a2_0900_0004_a600).mirror(), 0x00a6_0400_0009_a200)
        self.assertEqual(chess.SquareSet(0x1e22_2212_0e0a_1222).mirror(), 0x2212_0a0e_1222_221e)

    def test_flip(self):
        self.assertEqual(chess.flip_vertical(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.flip_horizontal(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.flip_diagonal(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.flip_anti_diagonal(chess.BB_ALL), chess.BB_ALL)

        s = chess.SquareSet(0x1e22_2212_0e0a_1222)  # Letter R
        self.assertEqual(chess.flip_vertical(s), 0x2212_0a0e_1222_221e)
        self.assertEqual(chess.flip_horizontal(s), 0x7844_4448_7050_4844)
        self.assertEqual(chess.flip_diagonal(s), 0x0000_6192_8c88_ff00)
        self.assertEqual(chess.flip_anti_diagonal(s), 0x00ff_1131_4986_0000)

    def test_len_of_complenent(self):
        squares = chess.SquareSet(~chess.BB_ALL)
        self.assertEqual(len(squares), 0)

        squares = ~chess.SquareSet(chess.BB_BACKRANKS)
        self.assertEqual(len(squares), 48)

    def test_int_conversion(self):
        self.assertEqual(int(chess.SquareSet(chess.BB_CENTER)), 0x0000_0018_1800_0000)
        self.assertEqual(hex(chess.SquareSet(chess.BB_CENTER)), "0x1818000000")
        self.assertEqual(bin(chess.SquareSet(chess.BB_CENTER)), "0b1100000011000000000000000000000000000")

    def test_tolist(self):
        self.assertEqual(chess.SquareSet(chess.BB_LIGHT_SQUARES).tolist().count(True), 32)

    def test_flip_ducktyping(self):
        bb = 0x1e22_2212_0e0a_1222
        squares = chess.SquareSet(bb)
        for f in [chess.flip_vertical, chess.flip_horizontal, chess.flip_diagonal, chess.flip_anti_diagonal]:
            self.assertEqual(int(f(squares)), f(bb))
            self.assertEqual(int(squares), bb)  # Not mutated


class PolyglotTestCase(unittest.TestCase):

    def test_performance_bin(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            pos = chess.Board()

            e4 = next(book.find_all(pos))
            self.assertEqual(e4.move, pos.parse_san("e4"))
            pos.push(e4.move)

            e5 = next(book.find_all(pos))
            self.assertEqual(e5.move, pos.parse_san("e5"))
            pos.push(e5.move)

    def test_mainline(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            board = chess.Board()

            while True:
                entry = book.get(board)
                if entry is None:
                    break

                board.push(entry.move)

            self.assertEqual(board.fen(), "r2q1rk1/4bppp/p2p1n2/np5b/3BP1P1/5N1P/PPB2P2/RN1QR1K1 b - - 0 15")

    def test_lasker_trap(self):
        with chess.polyglot.open_reader("data/polyglot/lasker-trap.bin") as book:
            board = chess.Board("rnbqk1nr/ppp2ppp/8/4P3/1BP5/8/PP2KpPP/RN1Q1BNR b kq - 1 7")
            entry = book.find(board)
            cute_underpromotion = entry.move
            self.assertEqual(cute_underpromotion, board.parse_san("fxg1=N+"))

    def test_castling(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            # White decides between short castling and long castling at this
            # turning point in the Queen's Gambit Declined, Exchange Variation.
            pos = chess.Board("r1bqr1k1/pp1nbppp/2p2n2/3p2B1/3P4/2NBP3/PPQ1NPPP/R3K2R w KQ - 5 10")
            moves = set(entry.move for entry in book.find_all(pos))
            self.assertIn(pos.parse_san("O-O"), moves)
            self.assertIn(pos.parse_san("O-O-O"), moves)
            self.assertIn(pos.parse_san("h3"), moves)
            self.assertEqual(len(moves), 3)

            # Black usually castles long at this point in the Ruy Lopez,
            # Exchange Variation.
            pos = chess.Board("r3k1nr/1pp1q1pp/p1pb1p2/4p3/3PP1b1/2P1BN2/PP1N1PPP/R2Q1RK1 b kq - 4 9")
            moves = set(entry.move for entry in book.find_all(pos))
            self.assertIn(pos.parse_san("O-O-O"), moves)
            self.assertEqual(len(moves), 1)

            # Not a castling move.
            pos = chess.Board("1r1qr1k1/1b2bp1n/p2p2pB/1pnPp2p/P1p1P3/R1P2NNP/1PBQ1PP1/4R1K1 w - - 0 1")
            entry = book.find(pos)
            self.assertEqual(entry.move, chess.Move.from_uci("e1a1"))

    def test_empty_book(self):
        with chess.polyglot.open_reader(os.devnull) as book:
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
        class FirstMockRandom:
            @staticmethod
            def randint(first, last):
                assert first <= last
                return first

        class LastMockRandom:
            @staticmethod
            def randint(first, last):
                assert first <= last
                return last

        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            # Uniform choice.
            entry = book.choice(chess.Board(), random=FirstMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("e2e4"))

            entry = book.choice(chess.Board(), random=LastMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("c2c4"))

            # Weighted choice.
            entry = book.weighted_choice(chess.Board(), random=FirstMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("e2e4"))

            entry = book.weighted_choice(chess.Board(), random=LastMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("c2c4"))

            # Weighted choice with excluded move.
            entry = book.weighted_choice(chess.Board(), exclude_moves=[chess.Move.from_uci("e2e4")], random=FirstMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("d2d4"))

    def test_find(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            entry = book.find(chess.Board())
            self.assertEqual(entry.move, chess.Move.from_uci("e2e4"))

    def test_exclude_moves(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            entry = book.find(chess.Board(), exclude_moves=[chess.Move.from_uci("e2e4")])
            self.assertEqual(entry.move, chess.Move.from_uci("d2d4"))

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
        game.headers["VeryLongHeader"] = "This is a very long header, much wider than the 80 columns that PGNs are formatted with by default"

        e4 = game.add_variation(game.board().parse_san("e4"))
        e4.comment = "Scandinavian Defense:"

        e4_d5 = e4.add_variation(e4.board().parse_san("d5"))

        e4_h5 = e4.add_variation(e4.board().parse_san("h5"))
        e4_h5.nags.add(chess.pgn.NAG_MISTAKE)
        e4_h5.starting_comment = "This"
        e4_h5.comment = "is nonsense"

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
            [VeryLongHeader "This is a very long header, much wider than the 80 columns that PGNs are formatted with by default"]

            { Test game: } 1. e4 { Scandinavian Defense: } 1... d5 ( { This } 1... h5 $2
            { is nonsense } ) ( 1... e5 2. Qf3 $2 ) ( 1... c5 { Sicilian } ) 2. exd5
            { Best } *""")
        self.assertEqual(str(exporter), pgn)

        # Test file exporter.
        virtual_file = io.StringIO()
        exporter = chess.pgn.FileExporter(virtual_file)
        game.accept(exporter)
        self.assertEqual(virtual_file.getvalue(), pgn + "\n\n")

    def test_game_without_tag_roster(self):
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

        # Chess960 starting position #283.
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
        pgn = io.StringIO(textwrap.dedent("""\
            1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. Nbd2 a6 $6 (6... Bb6 $5 {
            /\\ Ne7, c6}) *"""))

        game = chess.pgn.read_game(pgn)

        # Seek the node after 6.Nbd2 and before 6...a6.
        node = game
        while node.variations and not node.has_variation(chess.Move.from_uci("a7a6")):
            node = node[0]

        # Make sure the comment for the second variation is there.
        self.assertIn(5, node[1].nags)
        self.assertEqual(node[1].comment, "\n/\\ Ne7, c6")

    def test_promotion_without_equals(self):
        # Example game from https://github.com/rozim/ChessData as originally
        # reported.
        pgn = io.StringIO(textwrap.dedent("""\
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

    def test_header_with_paren(self):
        with open("data/pgn/stockfish-learning.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Opening"], "St. George (Baker) defense")
        self.assertEqual(game.end().board(), chess.Board("8/2p2k2/1pR3p1/1P1P4/p1P2P2/P4K2/8/5r2 w - - 7 78"))

    def test_special_tag_names(self):
        pgn = io.StringIO("""[BlackType: "program"]""")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["BlackType:"], "program")

        with self.assertRaises(ValueError):
            game.headers["~"] = "foo"

        game.headers["Equals="] = "bar"

    def test_chess960_without_fen(self):
        pgn = io.StringIO(textwrap.dedent("""\
            [Variant "Chess960"]

            1. e4 *
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game[0].move, chess.Move.from_uci("e2e4"))

    def test_variation_stack(self):
        # Survive superfluous closing brackets.
        pgn = io.StringIO("1. e4 (1. d4))) !? *")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(game[0].san(), "e4")
        self.assertEqual(game[0].uci(), "e2e4")
        self.assertEqual(game[1].san(), "d4")
        self.assertEqual(game[1].uci(), "d2d4")
        self.assertEqual(len(game.errors), 0)

        # Survive superfluous opening brackets.
        pgn = io.StringIO("((( 1. c4 *")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(game[0].san(), "c4")
        self.assertEqual(len(game.errors), 0)

    def test_game_starting_comment(self):
        pgn = io.StringIO("{ Game starting comment } 1. d3")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comment, "Game starting comment")
        self.assertEqual(game[0].san(), "d3")

        pgn = io.StringIO("{ Empty game, but has a comment }")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comment, "Empty game, but has a comment")

    def test_game_starting_variation(self):
        pgn = io.StringIO(textwrap.dedent("""\
            {Start of game} 1. e4 ({Start of variation} 1. d4) 1... e5
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comment, "Start of game")

        node = game[0]
        self.assertEqual(node.move, chess.Move.from_uci("e2e4"))
        self.assertFalse(node.comment)
        self.assertFalse(node.starting_comment)

        node = game[1]
        self.assertEqual(node.move, chess.Move.from_uci("d2d4"))
        self.assertFalse(node.comment)
        self.assertEqual(node.starting_comment, "Start of variation")

    def test_annotation_symbols(self):
        pgn = io.StringIO("1. b4?! g6 2. Bb2 Nc6? 3. Bxh8!!")
        game = chess.pgn.read_game(pgn)

        node = game.variation(chess.Move.from_uci("b2b4"))
        self.assertIn(chess.pgn.NAG_DUBIOUS_MOVE, node.nags)
        self.assertEqual(len(node.nags), 1)

        node = node[0]
        self.assertEqual(len(node.nags), 0)

        node = node[0]
        self.assertEqual(len(node.nags), 0)

        node = node[0]
        self.assertIn(chess.pgn.NAG_MISTAKE, node.nags)
        self.assertEqual(len(node.nags), 1)

        node = node[0]
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

        self.assertTrue(game.is_mainline())
        self.assertTrue(node.is_mainline())
        self.assertTrue(end_node.is_mainline())
        self.assertFalse(alternative_node.is_mainline())

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
        self.assertEqual(game[0], a)
        self.assertEqual(game[1], b)

        game.promote(b)
        self.assertTrue(b.is_main_variation())
        self.assertFalse(a.is_main_variation())
        self.assertEqual(game[0], b)
        self.assertEqual(game[1], a)

        game.demote(b)
        self.assertTrue(a.is_main_variation())

        c = game.add_main_variation(chess.Move(chess.C2, chess.C3))
        self.assertTrue(c.is_main_variation())
        self.assertFalse(a.is_main_variation())
        self.assertFalse(b.is_main_variation())
        self.assertEqual(game[0], c)
        self.assertEqual(game[1], a)
        self.assertEqual(game[2], b)

    def test_skip_game(self):
        with open("data/pgn/kasparov-deep-blue-1997.pgn") as pgn:
            offsets = []
            while True:
                offset = pgn.tell()
                if chess.pgn.skip_game(pgn):
                    offsets.append(offset)
                else:
                    break
            self.assertEqual(len(offsets), 6)

            pgn.seek(offsets[0])
            first_game = chess.pgn.read_game(pgn)
            self.assertEqual(first_game.headers["Event"], "IBM Man-Machine, New York USA")
            self.assertEqual(first_game.headers["Site"], "01")

            pgn.seek(offsets[5])
            sixth_game = chess.pgn.read_game(pgn)
            self.assertEqual(sixth_game.headers["Event"], "IBM Man-Machine, New York USA")
            self.assertEqual(sixth_game.headers["Site"], "06")

    def test_tricky_skip_game(self):
        raw_pgn = textwrap.dedent("""
            1. a3 ; { ; }

            1. b3 { ;
            % {
            1... g6 ; {

            1. c3 { }
            % {
            1... f6 ; { } {{{

            1. d3""")
        pgn = io.StringIO(raw_pgn)

        offsets = []
        while True:
            offset = pgn.tell()
            if chess.pgn.skip_game(pgn):
                offsets.append(offset)
            else:
                break

        self.assertEqual(len(offsets), 3)

        pgn.seek(offsets[0])
        self.assertEqual(chess.pgn.read_game(pgn).next().move, chess.Move.from_uci("a2a3"))
        pgn.seek(offsets[1])
        self.assertEqual(chess.pgn.read_game(pgn).next().move, chess.Move.from_uci("b2b3"))
        pgn.seek(offsets[2])
        self.assertEqual(chess.pgn.read_game(pgn).next().move, chess.Move.from_uci("d2d3"))
        self.assertEqual(chess.pgn.read_game(pgn), None)

    def test_read_headers(self):
        with open("data/pgn/kasparov-deep-blue-1997.pgn") as pgn:
            offsets = []

            while True:
                offset = pgn.tell()
                headers = chess.pgn.read_headers(pgn)
                if headers is None:
                    break
                elif headers.get("Result", "*") == "1/2-1/2":
                    offsets.append(offset)

            pgn.seek(offsets[0])
            first_drawn_game = chess.pgn.read_game(pgn)
            self.assertEqual(first_drawn_game.headers["Site"], "03")
            self.assertEqual(first_drawn_game[0].move, chess.Move.from_uci("d2d3"))

    def test_visit_board(self):
        class TraceVisitor(chess.pgn.BaseVisitor):
            def __init__(self):
                self.trace = []

            def visit_board(self, board):
                self.trace.append(board.fen())

            def visit_move(self, board, move):
                self.trace.append(board.san(move))

            def result(self):
                return self.trace

        pgn = io.StringIO(textwrap.dedent("""\
            [FEN "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"]

            1... e5 (1... d5 2. exd5) (1... c5) 2. Nf3 Nc6
            """))

        trace = [
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            "e5",
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "d5",
            "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "exd5",
            "rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2",
            "c5",
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "Nf3",
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
            "Nc6",
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        ]

        self.assertEqual(trace, chess.pgn.read_game(pgn, Visitor=TraceVisitor))

        pgn.seek(0)
        self.assertEqual(trace, chess.pgn.read_game(pgn).accept(TraceVisitor()))

        pgn.seek(0)
        self.assertEqual(chess.Board(trace[-1]), chess.pgn.read_game(pgn, Visitor=chess.pgn.BoardBuilder))

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
        pgn = io.StringIO("1. d4 1-0")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Result"], "1-0")

    def test_missing_setup_tag(self):
        pgn = io.StringIO(textwrap.dedent("""\
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

    def test_chessbase_empty_line(self):
        with open("data/pgn/chessbase-empty-line.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.headers["Event"], "AlphaZero vs. Stockfish")
            self.assertEqual(game.headers["Round"], "1")
            self.assertEqual(game.next().move, chess.Move.from_uci("e2e4"))

            self.assertTrue(chess.pgn.read_game(pgn) is None)

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
        pgn = io.StringIO("""
            1. e4 Qa1 e5 2. Qxf8

            1. a3""")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(len(game.errors), 1)
        self.assertEqual(game.end().board().fen(), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.end().board().fen(), "rnbqkbnr/pppppppp/8/8/8/P7/1PPPPPPP/RNBQKBNR b KQkq - 0 1")

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

    def test_mainline(self):
        moves = [chess.Move.from_uci(uci) for uci in ["d2d3", "g8f6", "e2e4"]]

        game = chess.pgn.Game()
        game.add_line(moves)

        self.assertEqual(list(game.mainline_moves()), moves)
        self.assertTrue(game.mainline_moves())
        self.assertEqual(list(reversed(game.mainline_moves())), list(reversed(moves)))
        self.assertEqual(str(game.mainline_moves()), "1. d3 Nf6 2. e4")

    def test_lan(self):
        pgn = io.StringIO("1. e2-e4")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.end().move, chess.Move.from_uci("e2e4"))

    def test_variants(self):
        pgn = io.StringIO(textwrap.dedent("""\
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

    def test_uci_moves(self):
        with open("data/pgn/uci-moves.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            board = game.end().board()
            self.assertEqual(board.fen(), "8/8/2B5/4k3/4Pp2/1b6/1P3K2/8 b - - 0 57")

    def test_wierd_header(self):
        pgn = io.StringIO(r"""[Black "[=0040.34h5a4]"]""")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Black"], "[=0040.34h5a4]")

    def test_semicolon_comment(self):
        pgn = io.StringIO("1. e4 ; e5")
        game = chess.pgn.read_game(pgn)
        node = game.next()
        self.assertEqual(node.move, chess.Move.from_uci("e2e4"))
        self.assertTrue(node.is_end())

    def test_empty_game(self):
        pgn = io.StringIO(" \n\n   ")
        game = chess.pgn.read_game(pgn)
        self.assertTrue(game is None)

    def test_no_movetext(self):
        pgn = io.StringIO(textwrap.dedent("""
            [Event "A"]


            [Event "B"]
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Event"], "A")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Event"], "B")

        self.assertTrue(chess.pgn.read_game(pgn) is None)

    def test_subgame(self):
        pgn = io.StringIO("1. d4 d5 (1... Nf6 2. c4 (2. Nf3 g6 3. g3))")
        game = chess.pgn.read_game(pgn)
        node = game.next().variations[1]
        subgame = node.accept_subgame(chess.pgn.GameBuilder())
        self.assertEqual(subgame.headers["FEN"], "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2")
        self.assertEqual(subgame.next().move, chess.Move.from_uci("c2c4"))
        self.assertEqual(subgame.variations[1].move, chess.Move.from_uci("g1f3"))

    def test_is_wild(self):
        headers = chess.pgn.Headers()
        headers["Variant"] = "wild/1"
        self.assertTrue(headers.is_wild())

    def test_my_game_node(self):
        class MyGameNode(chess.pgn.GameNode):
            def add_variation(self, move, *, comment="", starting_comment="", nags=[]):
                return MyChildNode(self, move, comment=comment, starting_comment=starting_comment, nags=nags)

        class MyChildNode(chess.pgn.ChildNode, MyGameNode):
            pass

        class MyGame(chess.pgn.Game, MyGameNode):
            pass

        pgn = io.StringIO("1. e4")
        game = chess.pgn.read_game(pgn, Visitor=MyGame.builder)
        self.assertTrue(isinstance(game, MyGame))
        node = game.variation(chess.Move.from_uci("e2e4"))
        self.assertTrue(isinstance(node, MyGameNode))

    def test_recursion(self):
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        for _ in range(1000):
            board.push(chess.Move(chess.E1, chess.E2))
            board.push(chess.Move(chess.E8, chess.E7))
            board.push(chess.Move(chess.E2, chess.E1))
            board.push(chess.Move(chess.E7, chess.E8))
        game = chess.pgn.Game.from_board(board)
        self.assertTrue(str(game).endswith("2000. Ke1 Ke8 1/2-1/2"))

    def test_annotations(self):
        game = chess.pgn.Game()
        game.comment = "foo [%bar] baz"

        self.assertTrue(game.clock() is None)
        clock = 12345
        game.set_clock(clock)
        self.assertEqual(game.comment, "foo [%bar] baz [%clk 3:25:45]")
        self.assertEqual(game.clock(), clock)

        self.assertTrue(game.eval() is None)
        game.set_eval(chess.engine.PovScore(chess.engine.Cp(-80), chess.WHITE))
        self.assertEqual(game.comment, "foo [%bar] baz [%clk 3:25:45] [%eval -0.80]")
        self.assertEqual(game.eval().white().score(), -80)
        self.assertEqual(game.eval_depth(), None)
        game.set_eval(chess.engine.PovScore(chess.engine.Mate(1), chess.WHITE), 5)
        self.assertEqual(game.comment, "foo [%bar] baz [%clk 3:25:45] [%eval #1,5]")
        self.assertEqual(game.eval().white().mate(), 1)
        self.assertEqual(game.eval_depth(), 5)

        self.assertEqual(game.arrows(), [])
        game.set_arrows([(chess.A1, chess.A1), chess.svg.Arrow(chess.A1, chess.H1, color="red"), chess.svg.Arrow(chess.B1, chess.B8)])
        self.assertEqual(game.comment, "[%csl Ga1][%cal Ra1h1,Gb1b8] foo [%bar] baz [%clk 3:25:45] [%eval #1,5]")
        arrows = game.arrows()
        self.assertEqual(len(arrows), 3)
        self.assertEqual(arrows[0].color, "green")
        self.assertEqual(arrows[1].color, "red")
        self.assertEqual(arrows[2].color, "green")

        self.assertTrue(game.emt() is None)
        emt = 321
        game.set_emt(emt)
        self.assertEqual(game.comment, "[%csl Ga1][%cal Ra1h1,Gb1b8] foo [%bar] baz [%clk 3:25:45] [%eval #1,5] [%emt 0:05:21]")
        self.assertEqual(game.emt(), emt)

        game.set_eval(None)
        self.assertEqual(game.comment, "[%csl Ga1][%cal Ra1h1,Gb1b8] foo [%bar] baz [%clk 3:25:45] [%emt 0:05:21]")

        game.set_emt(None)
        self.assertEqual(game.comment, "[%csl Ga1][%cal Ra1h1,Gb1b8] foo [%bar] baz [%clk 3:25:45]")

        game.set_clock(None)
        game.set_arrows([])
        self.assertEqual(game.comment, "foo [%bar] baz")

    def test_eval(self):
        game = chess.pgn.Game()
        for cp in range(199, 220):
            game.set_eval(chess.engine.PovScore(chess.engine.Cp(cp), chess.WHITE))
            self.assertEqual(game.eval().white().cp, cp)

    def test_float_emt(self):
        game = chess.pgn.Game()
        game.comment = "[%emt 0:00:01.234]"
        self.assertEqual(game.emt(), 1.234)

        game.set_emt(6.54321)
        self.assertEqual(game.comment, "[%emt 0:00:06.543]")
        self.assertEqual(game.emt(), 6.543)

        game.set_emt(-70)
        self.assertEqual(game.comment, "[%emt 0:00:00]")  # Clamped
        self.assertEqual(game.emt(), 0)

    def test_float_clk(self):
        game = chess.pgn.Game()
        game.comment = "[%clk 0:00:01.234]"
        self.assertEqual(game.clock(), 1.234)

        game.set_clock(6.54321)
        self.assertEqual(game.comment, "[%clk 0:00:06.543]")
        self.assertEqual(game.clock(), 6.543)

        game.set_clock(-70)
        self.assertEqual(game.comment, "[%clk 0:00:00]")  # Clamped
        self.assertEqual(game.clock(), 0)

    def test_node_turn(self):
        game = chess.pgn.Game()
        self.assertEqual(game.turn(), chess.WHITE)
        node = game.add_variation(chess.Move.from_uci("a2a3"))
        self.assertEqual(node.turn(), chess.BLACK)
        node = node.add_variation(chess.Move.from_uci("a7a6"))
        self.assertEqual(node.turn(), chess.WHITE)

        game = chess.pgn.Game()
        game.setup("4k3/8/8/8/8/8/8/4K3 b - - 7 6")
        self.assertEqual(game.turn(), chess.BLACK)
        node = game.add_variation(chess.Move.from_uci("e8e7"))
        self.assertEqual(node.turn(), chess.WHITE)
        node = node.add_variation(chess.Move.from_uci("e1e2"))
        self.assertEqual(node.turn(), chess.BLACK)

    def test_skip_inner_variation(self):
        class BlackVariationsOnly(chess.pgn.GameBuilder):
            def begin_variation(self):
                self.skipping = self.variation_stack[-1].turn() != chess.WHITE
                if self.skipping:
                    return chess.pgn.SKIP
                else:
                    return super().begin_variation()

            def end_variation(self):
                if self.skipping:
                    self.skipping = False
                else:
                    return super().end_variation()

        pgn = "1. e4 e5 ( 1... d5 2. exd5 Qxd5 3. Nc3 ( 3. c4 ) 3... Qa5 ) *"
        expected_pgn = "1. e4 e5 ( 1... d5 2. exd5 Qxd5 3. Nc3 Qa5 ) *"

        # Driven by parser.
        game = chess.pgn.read_game(io.StringIO(pgn), Visitor=BlackVariationsOnly)
        self.assertEqual(game.accept(chess.pgn.StringExporter(headers=False)), expected_pgn)

        # Driven by game tree traversal.
        game = chess.pgn.read_game(io.StringIO(pgn)).accept(BlackVariationsOnly())
        self.assertEqual(game.accept(chess.pgn.StringExporter(headers=False)), expected_pgn)


@unittest.skipIf(sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 8, 1), "https://bugs.python.org/issue34679")
class EngineTestCase(unittest.TestCase):

    def test_uci_option_map_equality(self):
        a = chess.engine.UciOptionMap()
        b = chess.engine.UciOptionMap()
        c = chess.engine.UciOptionMap()
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

    def test_uci_option_map_len(self):
        a = chess.engine.UciOptionMap()
        self.assertEqual(len(a), 0)

        a["key"] = "value"
        self.assertEqual(len(a), 1)

        del a["key"]
        self.assertEqual(len(a), 0)

    def test_score_ordering(self):
        order = [
            chess.engine.Mate(-0),
            chess.engine.Mate(-1),
            chess.engine.Mate(-99),
            chess.engine.Cp(-123),
            chess.engine.Cp(-50),
            chess.engine.Cp(0),
            chess.engine.Cp(+30),
            chess.engine.Cp(+800),
            chess.engine.Mate(+77),
            chess.engine.Mate(+1),
            chess.engine.MateGiven,
        ]

        for i, a in enumerate(order):
            for j, b in enumerate(order):
                self.assertEqual(i < j, a < b, f"{a!r} < {b!r}")
                self.assertEqual(i == j, a == b, f"{a!r} == {b!r}")
                self.assertEqual(i <= j, a <= b)
                self.assertEqual(i != j, a != b)
                self.assertEqual(i > j, a > b)
                self.assertEqual(i >= j, a >= b)
                self.assertEqual(i < j, a.score(mate_score=100000) < b.score(mate_score=100000))

                self.assertTrue(not (i < j) or a.wdl().expectation() <= b.wdl().expectation())
                self.assertTrue(not (i < j) or a.wdl().winning_chance() <= b.wdl().winning_chance())
                self.assertTrue(not (i < j) or a.wdl().losing_chance() >= b.wdl().losing_chance())

    def test_score(self):
        # Negation.
        self.assertEqual(-chess.engine.Cp(+20), chess.engine.Cp(-20))
        self.assertEqual(-chess.engine.Mate(+4), chess.engine.Mate(-4))
        self.assertEqual(-chess.engine.Mate(-0), chess.engine.MateGiven)
        self.assertEqual(-chess.engine.MateGiven, chess.engine.Mate(-0))

        # Score.
        self.assertEqual(chess.engine.Cp(-300).score(), -300)
        self.assertEqual(chess.engine.Mate(+5).score(), None)
        self.assertEqual(chess.engine.Mate(+5).score(mate_score=100000), 99995)
        self.assertEqual(chess.engine.Mate(-7).score(mate_score=100000), -99993)

        # Mate.
        self.assertEqual(chess.engine.Cp(-300).mate(), None)
        self.assertEqual(chess.engine.Mate(+5).mate(), 5)

        # Wdl.
        self.assertEqual(chess.engine.MateGiven.wdl().expectation(), 1)
        self.assertEqual(chess.engine.Mate(0).wdl().expectation(), 0)
        self.assertEqual(chess.engine.Cp(0).wdl().expectation(), 0.5)

        for cp in map(chess.engine.Cp, range(-1050, 1100, 50)):
            wdl = cp.wdl()
            self.assertTrue(wdl)
            self.assertAlmostEqual(wdl.winning_chance() + wdl.drawing_chance() + wdl.losing_chance(), 1)

        self.assertFalse(chess.engine.Wdl(0, 0, 0))

    def test_wdl_model(self):
        self.assertEqual(chess.engine.Cp(131).wdl(model="sf12", ply=25), chess.engine.Wdl(524, 467, 9))
        self.assertEqual(chess.engine.Cp(146).wdl(model="sf14", ply=25), chess.engine.Wdl(601, 398, 1))
        self.assertEqual(chess.engine.Cp(40).wdl(model="sf15", ply=25), chess.engine.Wdl(58, 937, 5))
        self.assertEqual(chess.engine.Cp(100).wdl(model="sf15.1", ply=64), chess.engine.Wdl(497, 503, 0))

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_forced_mates(self):
        with chess.engine.SimpleEngine.popen_uci("stockfish", debug=True) as engine:
            epds = [
                "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";",
                "6k1/N1p3pp/2p5/3n1P2/4K3/1P5P/P1Pr1r2/R1R5 b - - bm Rf4+; id \"Clausthal 2014\";",
            ]

            board = chess.Board()

            for epd in epds:
                operations = board.set_epd(epd)
                result = engine.play(board, chess.engine.Limit(mate=5), game=object())
                self.assertIn(result.move, operations["bm"], operations["id"])

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_options(self):
        with chess.engine.SimpleEngine.popen_uci("stockfish", debug=True) as engine:
            self.assertEqual(engine.options["UCI_Chess960"].name, "UCI_Chess960")
            self.assertEqual(engine.options["uci_Chess960"].type, "check")
            self.assertEqual(engine.options["UCI_CHESS960"].default, False)

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_analysis(self):
        with chess.engine.SimpleEngine.popen_uci("stockfish", setpgrp=True, debug=True) as engine:
            board = chess.Board("8/6K1/1p1B1RB1/8/2Q5/2n1kP1N/3b4/4n3 w - - 0 1")
            limit = chess.engine.Limit(depth=40)
            analysis = engine.analysis(board, limit)
            with analysis:
                for info in iter(analysis.next, None):
                    if "score" in info and info["score"].is_mate():
                        break
                else:
                    self.fail("never found a mate score")

                for info in analysis:
                    if "score" in info and info["score"].white() >= chess.engine.Mate(+2):
                        break

            analysis.wait()
            self.assertFalse(analysis.would_block())

            self.assertEqual(analysis.info["score"].relative, chess.engine.Mate(+2))
            self.assertEqual(analysis.multipv[0]["score"].black(), chess.engine.Mate(-2))

            # Exhaust remaining information.
            was_empty = analysis.empty()
            was_really_empty = True
            for info in analysis:
                was_really_empty = False
            self.assertEqual(was_really_empty, was_empty)
            self.assertTrue(analysis.empty())
            self.assertFalse(analysis.would_block())
            for info in analysis:
                self.fail("all info should have been consumed")

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_multipv(self):
        with chess.engine.SimpleEngine.popen_uci("stockfish", debug=True) as engine:
            board = chess.Board("r2qr1k1/pb2npp1/1pn1p2p/8/3P4/P1PQ1N2/B4PPP/R1B1R1K1 w - - 2 15")
            result = engine.analyse(board, chess.engine.Limit(depth=1), multipv=3)
            self.assertEqual(len(result), 3)
            self.assertTrue(result[0]["score"].relative >= result[1]["score"].relative)
            self.assertTrue(result[1]["score"].relative >= result[2]["score"].relative)

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_quit(self):
        engine = chess.engine.SimpleEngine.popen_uci("stockfish", setpgrp=True, debug=True)

        with engine:
            engine.quit()

        with self.assertRaises(chess.engine.EngineTerminatedError), engine:
            engine.ping()

    @catchAndSkip(FileNotFoundError, "need crafty")
    def test_crafty_play_to_mate(self):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory(prefix="crafty") as tmpdir:
                with chess.engine.SimpleEngine.popen_xboard("crafty", setpgrp=True, debug=True, cwd=tmpdir) as engine:
                    board = chess.Board("2bqkbn1/2pppp2/np2N3/r3P1p1/p2N2B1/5Q2/PPPPKPP1/RNB2r2 w KQkq - 0 1")
                    limit = chess.engine.Limit(depth=10)
                    while not board.is_game_over() and len(board.move_stack) < 5:
                        result = engine.play(board, limit, ponder=True)
                        board.push(result.move)
                    self.assertTrue(board.is_checkmate())
                    engine.quit()
        finally:
            logging.disable(logging.NOTSET)

    @catchAndSkip(FileNotFoundError, "need crafty")
    def test_crafty_analyse(self):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory(prefix="crafty") as tmpdir:
                with chess.engine.SimpleEngine.popen_xboard("crafty", debug=True, cwd=tmpdir) as engine:
                    board = chess.Board("2bqkbn1/2pppp2/np2N3/r3P1p1/p2N2B1/5Q2/PPPPKPP1/RNB2r2 w KQkq - 0 1")
                    limit = chess.engine.Limit(depth=7, time=2.0)
                    info = engine.analyse(board, limit)
                    self.assertTrue(info["score"].relative > chess.engine.Cp(1000))
                    engine.quit()
        finally:
            logging.disable(logging.NOTSET)

    @catchAndSkip(FileNotFoundError, "need crafty")
    def test_crafty_ping(self):
        with tempfile.TemporaryDirectory(prefix="crafty") as tmpdir:
            with chess.engine.SimpleEngine.popen_xboard("crafty", debug=True, cwd=tmpdir) as engine:
                engine.ping()
                engine.quit()

    def test_uci_ping(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("uci", ["uciok"])
            await protocol.initialize()
            mock.assert_done()

            mock.expect("isready", ["readyok"])
            await protocol.ping()
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_uci_debug(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("debug on", [])
            protocol.debug()
            mock.assert_done()

            mock.expect("debug off", [])
            protocol.debug(False)
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_uci_go(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", ["uciok"])
            await protocol.initialize()

            # Pondering.
            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos")
            mock.expect("go movetime 123 searchmoves e2e4 d2d4", ["info string searching ...", "bestmove d2d4 ponder d7d5"])
            mock.expect("position startpos moves d2d4 d7d5")
            mock.expect("go ponder movetime 123")
            board = chess.Board()
            result = await protocol.play(board, chess.engine.Limit(time=0.123),
                                         root_moves=[board.parse_san("e4"), board.parse_san("d4")],
                                         ponder=True,
                                         info=chess.engine.INFO_ALL)
            self.assertEqual(result.move, chess.Move.from_uci("d2d4"))
            self.assertEqual(result.ponder, chess.Move.from_uci("d7d5"))
            self.assertEqual(result.info["string"], "searching ...")
            mock.assert_done()

            mock.expect("stop", ["bestmove c2c4"])

            # Limits.
            mock.expect("position startpos")
            mock.expect("go wtime 1 btime 2 winc 3 binc 4 movestogo 5 depth 6 nodes 7 mate 8 movetime 9", ["bestmove d2d4"])
            limit = chess.engine.Limit(white_clock=0.001, black_clock=0.002,
                                       white_inc=0.003, black_inc=0.004,
                                       remaining_moves=5, depth=6, nodes=7,
                                       mate=8, time=0.009)
            result = await protocol.play(board, limit)
            self.assertEqual(result.move, chess.Move.from_uci("d2d4"))
            self.assertEqual(result.ponder, None)
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_iota_log(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", ["uciok"])
            await protocol.initialize()

            # Iota writes invalid \0 character in old version.
            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos moves d2d4")
            mock.expect("go movetime 5000", ["bestmove e7e6\0"])
            board = chess.Board()
            board.push_uci("d2d4")
            with self.assertRaises(chess.engine.EngineError):
                await protocol.play(board, chess.engine.Limit(time=5.0))
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_uci_analyse_mode(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", [
                "option name UCI_AnalyseMode type check default false",
                "uciok",
            ])
            await protocol.initialize()

            # Analyse.
            mock.expect("setoption name UCI_AnalyseMode value true")
            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos")
            mock.expect("go infinite")
            mock.expect("stop", ["bestmove e2e4"])
            result = await protocol.analysis(chess.Board())
            self.assertTrue(result.would_block())
            result.stop()
            best = await result.wait()
            self.assertFalse(result.would_block())
            self.assertEqual(best.move, chess.Move.from_uci("e2e4"))
            self.assertTrue(best.ponder is None)
            mock.assert_done()

            # Explicitly disable.
            mock.expect("setoption name UCI_AnalyseMode value false")
            await protocol.configure({"UCI_AnalyseMode": False})
            mock.assert_done()

            # Analyse again.
            mock.expect("position startpos")
            mock.expect("go infinite")
            mock.expect("stop", ["bestmove e2e4 ponder e7e5"])
            result = await protocol.analysis(chess.Board())
            result.stop()
            best = await result.wait()
            self.assertEqual(best.move, chess.Move.from_uci("e2e4"))
            self.assertEqual(best.ponder, chess.Move.from_uci("e7e5"))
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_uci_play_after_analyse(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", ["uciok"])
            await protocol.initialize()

            # Ponder.
            board = chess.Board()
            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos")
            mock.expect("go depth 20", ["bestmove a2a4 ponder a7a5"])
            info = await protocol.analyse(board, chess.engine.Limit(depth=20))
            self.assertEqual(info, {})

            # Play.
            mock.expect("position startpos")
            mock.expect("go movetime 3000", ["bestmove a2a4 ponder a7a5"])
            await protocol.play(board, chess.engine.Limit(time=3))

            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_uci_ponderhit(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", [
                "option name Hash type spin default 16 min 1 max 33554432",
                "option name Ponder type check default false",
                "option name UCI_Opponent type string",
                "uciok",
            ])
            await protocol.initialize()

            primary_opponent = chess.engine.Opponent("Eliza", None, 3500, True)
            await protocol.send_opponent_information(opponent=primary_opponent)

            # First search.
            mock.expect("setoption name Ponder value true")
            mock.expect("ucinewgame")
            mock.expect("setoption name UCI_Opponent value none 3500 computer Eliza")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos")
            mock.expect("go movetime 1000", ["bestmove d2d4 ponder g8f6"])
            mock.expect("position startpos moves d2d4 g8f6")
            mock.expect("go ponder movetime 1000")
            board = chess.Board()
            result = await protocol.play(board, chess.engine.Limit(time=1), ponder=True)
            self.assertEqual(result.move, chess.Move.from_uci("d2d4"))
            self.assertEqual(result.ponder, chess.Move.from_uci("g8f6"))

            # Ponderhit.
            board.push(result.move)
            board.push(result.ponder)
            mock.expect("ponderhit", ["bestmove c2c4 ponder e7e6"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6")
            mock.expect("go ponder movetime 2000")
            result = await protocol.play(board, chess.engine.Limit(time=2), ponder=True)
            self.assertEqual(result.move, chess.Move.from_uci("c2c4"))
            self.assertEqual(result.ponder, chess.Move.from_uci("e7e6"))

            # Ponderhit prevented by changed option.
            board.push(result.move)
            board.push(result.ponder)
            mock.expect("stop", ["bestmove g2g3 ponder f8b4"])
            mock.expect("setoption name Hash value 32")
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6")
            mock.expect("go movetime 3000", ["bestmove b1c3 ponder f8b4"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4")
            mock.expect("go ponder movetime 3000")
            result = await protocol.play(board, chess.engine.Limit(time=3), ponder=True, options={"Hash": 32})
            self.assertEqual(result.move, chess.Move.from_uci("b1c3"))
            self.assertEqual(result.ponder, chess.Move.from_uci("f8b4"))

            # Ponderhit prevented by reverted option.
            board.push(result.move)
            board.push(result.ponder)
            mock.expect("stop", ["bestmove e2e3 ponder e8g8"])
            mock.expect("setoption name Hash value 16")
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4")
            mock.expect("go movetime 3000", ["bestmove d1c2 ponder d7d5"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5")
            mock.expect("go ponder movetime 3000")
            result = await protocol.play(board, chess.engine.Limit(time=3), ponder=True)
            self.assertEqual(result.move, chess.Move.from_uci("d1c2"))
            self.assertEqual(result.ponder, chess.Move.from_uci("d7d5"))

            # Interject analysis.
            board.push(result.move)
            board.push(result.ponder)
            mock.expect("stop", ["bestmove c4d5 ponder e6d5"])
            mock.expect("setoption name Ponder value false")
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5")
            mock.expect("go movetime 4000", ["bestmove c4d5 ponder e6d5"])
            await protocol.analyse(board, chess.engine.Limit(time=4))

            # Interjected analysis prevents ponderhit.
            mock.expect("setoption name Ponder value true")
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5")
            mock.expect("go movetime 5000", ["bestmove c4d5 ponder e6d5"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5")
            mock.expect("go ponder movetime 5000")
            await protocol.play(board, chess.engine.Limit(time=5), ponder=True)

            # Ponderhit prevented by new opponent, which starts a new game.
            board.push(chess.Move.from_uci("c4d5"))
            board.push(chess.Move.from_uci("e6d5"))
            mock.expect("stop", ["bestmove c1g5 ponder h7h6"])
            mock.expect("ucinewgame")
            mock.expect("setoption name UCI_Opponent value GM 3000 human Guy Chapman")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5")
            mock.expect("go movetime 5000", ["bestmove c1g5 ponder h7h6"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5 c1g5 h7h6")
            mock.expect("go ponder movetime 5000")
            opponent = chess.engine.Opponent("Guy Chapman", "GM", 3000, False)
            await protocol.play(board, chess.engine.Limit(time=5), ponder=True, opponent=opponent)

            # Ponderhit prevented by restoration of previous opponent, which again starts a new game.
            board.push(chess.Move.from_uci("c1g5"))
            board.push(chess.Move.from_uci("h7h6"))
            mock.expect("stop", ["bestmove g5h4 ponder b8c6"])
            mock.expect("ucinewgame")
            mock.expect("setoption name UCI_Opponent value none 3500 computer Eliza")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5 c1g5 h7h6")
            mock.expect("go movetime 5000", ["bestmove g5h4 ponder b8c6"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5 c1g5 h7h6 g5h4 b8c6")
            mock.expect("go ponder movetime 5000")
            await protocol.play(board, chess.engine.Limit(time=5), ponder=True)

            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_uci_info(self):
        # Info: refutation.
        board = chess.Board("8/8/6k1/8/8/8/1K6/3B4 w - - 0 1")
        info = chess.engine._parse_uci_info("refutation d1h5 g6h5", board)
        self.assertEqual(info["refutation"][chess.Move.from_uci("d1h5")], [chess.Move.from_uci("g6h5")])

        info = chess.engine._parse_uci_info("refutation d1h5", board)
        self.assertEqual(info["refutation"][chess.Move.from_uci("d1h5")], [])

        # Info: string.
        info = chess.engine._parse_uci_info("string goes to end no matter score cp 4 what", board)
        self.assertEqual(info["string"], "goes to end no matter score cp 4 what")

        # Info: currline.
        info = chess.engine._parse_uci_info("currline 0 e2e4 e7e5", chess.Board())
        self.assertEqual(info["currline"][0], [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")])

        # Info: ebf.
        info = chess.engine._parse_uci_info("ebf 0.42", board)
        self.assertEqual(info["ebf"], 0.42)

        # Info: depth, seldepth, score mate.
        info = chess.engine._parse_uci_info("depth 7 seldepth 8 score mate 3", board)
        self.assertEqual(info["depth"], 7)
        self.assertEqual(info["seldepth"], 8)
        self.assertEqual(info["score"], chess.engine.PovScore(chess.engine.Mate(+3), chess.WHITE))

        # Info: tbhits, cpuload, hashfull, time, nodes, nps.
        info = chess.engine._parse_uci_info("tbhits 123 cpuload 456 hashfull 789 time 987 nodes 654 nps 321", board)
        self.assertEqual(info["tbhits"], 123)
        self.assertEqual(info["cpuload"], 456)
        self.assertEqual(info["hashfull"], 789)
        self.assertEqual(info["time"], 0.987)
        self.assertEqual(info["nodes"], 654)
        self.assertEqual(info["nps"], 321)

        # Hakkapeliitta double spaces.
        info = chess.engine._parse_uci_info("depth 10 seldepth 9 score cp 22  time 17 nodes 48299 nps 2683000 tbhits 0", board)
        self.assertEqual(info["depth"], 10)
        self.assertEqual(info["seldepth"], 9)
        self.assertEqual(info["score"], chess.engine.PovScore(chess.engine.Cp(22), chess.WHITE))
        self.assertEqual(info["time"], 0.017)
        self.assertEqual(info["nodes"], 48299)
        self.assertEqual(info["nps"], 2683000)
        self.assertEqual(info["tbhits"], 0)

        # Unknown tokens.
        board = chess.Board()
        info = chess.engine._parse_uci_info("depth 1 unkown1 seldepth 2 unknown2 time 16 nodes 1 score cp 72 unknown3 wdl 249 747 4 multipv 1 uknown4 pv g1f3 g8f6 unknown5", board)
        self.assertEqual(info["depth"], 1)
        self.assertEqual(info["seldepth"], 2)
        self.assertEqual(info["time"], 0.016)
        self.assertEqual(info["nodes"], 1)
        self.assertEqual(info["score"], chess.engine.PovScore(chess.engine.Cp(72), chess.WHITE))
        self.assertEqual(info["multipv"], 1)
        self.assertEqual(info["pv"], [chess.Move.from_uci("g1f3"), chess.Move.from_uci("g8f6")])

        # WDL (activated with UCI_ShowWDL).
        info = chess.engine._parse_uci_info("depth 1 seldepth 2 time 16 nodes 1 score cp 72 wdl 249 747 4 hashfull 0 nps 400 tbhits 0 multipv 1", board)
        self.assertEqual(info["wdl"], (249, 747, 4))

    def test_hiarcs_bestmove(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("uci", ["uciok"])
            await protocol.initialize()

            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position fen QN4n1/6r1/3k4/8/b2K4/8/8/8 b - - 0 1")
            mock.expect("go", [
                "info depth 1 seldepth 4 time 793 nodes 187 nps 235 score cp -40 pv g7g4 d4c3 string keep double  space",
                "bestmove g7g4  ponder d4c3 ",
            ])
            result = await protocol.play(chess.Board("QN4n1/6r1/3k4/8/b2K4/8/8/8 b - - 0 1"), chess.engine.Limit(), info=chess.engine.INFO_ALL)
            self.assertEqual(result.move, chess.Move.from_uci("g7g4"))
            self.assertEqual(result.ponder, chess.Move.from_uci("d4c3"))
            self.assertEqual(result.info["pv"], [chess.Move.from_uci("g7g4"), chess.Move.from_uci("d4c3")])
            self.assertEqual(result.info["string"], "keep double  space")
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_xboard_options(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", [
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
                "feature ping=1 setboard=1 done=1",
            ])
            mock.expect("accepted egt")
            await protocol.initialize()
            mock.assert_done()

            self.assertEqual(protocol.options["egtpath syzygy"].type, "path")
            self.assertEqual(protocol.options["egtpath gaviota"].name, "egtpath gaviota")
            self.assertEqual(protocol.options["spinvar"].type, "spin")
            self.assertEqual(protocol.options["spinvar"].default, 50)
            self.assertEqual(protocol.options["spinvar"].min, 0)
            self.assertEqual(protocol.options["spinvar"].max, 100)
            self.assertEqual(protocol.options["combovar"].type, "combo")
            self.assertEqual(protocol.options["combovar"].var, ["HI", "HELLO", "BYE"])
            self.assertEqual(protocol.options["checkvar"].type, "check")
            self.assertEqual(protocol.options["checkvar"].default, False)
            self.assertEqual(protocol.options["stringvar"].type, "string")
            self.assertEqual(protocol.options["filevar"].type, "file")
            self.assertEqual(protocol.options["pathvar"].type, "path")
            self.assertEqual(protocol.options["buttonvar"].type, "button")
            self.assertEqual(protocol.options["resetvar"].type, "reset")
            self.assertEqual(protocol.options["savevar"].type, "save")

            mock.expect("option combovar=HI")
            await protocol.configure({"combovar": "HI"})
            mock.assert_done()

            mock.expect("option spinvar=42")
            await protocol.configure({"spinvar": 42})
            mock.assert_done()

            mock.expect("option checkvar=1")
            await protocol.configure({"checkvar": True})
            mock.assert_done()

            mock.expect("option pathvar=.")
            await protocol.configure({"pathvar": "."})
            mock.assert_done()

            mock.expect("option buttonvar")
            await protocol.configure({"buttonvar": None})
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_xboard_replay(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["feature ping=1 setboard=1 done=1"])
            await protocol.initialize()
            mock.assert_done()

            limit = chess.engine.Limit(time=1.5, depth=17)
            board = chess.Board()
            board.push_san("d4")
            board.push_san("Nf6")
            board.push_san("c4")

            mock.expect("new")
            mock.expect("force")
            mock.expect("d2d4")
            mock.expect("g8f6")
            mock.expect("c2c4")
            mock.expect("st 1.5")
            mock.expect("sd 17")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e7e6"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game")
            self.assertEqual(result.move, board.parse_san("e6"))
            mock.assert_done()

            board.pop()
            mock.expect("force")
            mock.expect("remove")
            mock.expect("st 1.5")
            mock.expect("sd 17")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move c2c4"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game")
            self.assertEqual(result.move, board.parse_san("c4"))
            mock.assert_done()

            board.pop()
            board.pop()
            mock.expect("force")
            mock.expect("remove")
            mock.expect("undo")
            mock.expect("st 1.5")
            mock.expect("sd 17")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move d2d4"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game")
            self.assertEqual(result.move, board.parse_san("d4"))
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_xboard_opponent(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["feature ping=1 setboard=1 name=1 done=1"])
            await protocol.initialize()
            mock.assert_done()

            limit = chess.engine.Limit(time=5)
            board = chess.Board()
            opponent = chess.engine.Opponent("Turk", "Mechanical", 2100, True)
            await protocol.send_opponent_information(opponent=opponent, engine_rating=3600)

            mock.expect("new")
            mock.expect("name Mechanical Turk")
            mock.expect("rating 3600 2100")
            mock.expect("computer")
            mock.expect("force")
            mock.expect("st 5")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e2e4"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game")
            self.assertEqual(result.move, board.parse_san("e4"))
            mock.assert_done()

            new_opponent = chess.engine.Opponent("Turochamp", None, 800, True)
            board.push(result.move)
            mock.expect("new")
            mock.expect("name Turochamp")
            mock.expect("rating 3600 800")
            mock.expect("computer")
            mock.expect("force")
            mock.expect("e2e4")
            mock.expect("st 5")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e7e5"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game", opponent=new_opponent)
            self.assertEqual(result.move, board.parse_san("e5"))
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_xboard_analyse(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", [
                "feature done=0 ping=1 setboard=1",
                "feature exclude=1",
                "feature variants=\"normal,atomic\" done=1",
            ])
            await protocol.initialize()
            mock.assert_done()

            board = chess.variant.AtomicBoard("rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1")
            limit = chess.engine.Limit(depth=1)
            mock.expect("new")
            mock.expect("variant atomic")
            mock.expect("force")
            mock.expect("setboard rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1")
            mock.expect("exclude all")
            mock.expect("include f7f6")
            mock.expect("post")
            mock.expect("analyze", ["4    116      23   2252  1... f6 2. e4 e6"])
            mock.expect(".")
            mock.expect("exit")
            mock.expect_ping()
            info = await protocol.analyse(board, limit, root_moves=[board.parse_san("f6")])
            self.assertEqual(info["depth"], 4)
            self.assertEqual(info["score"], chess.engine.PovScore(chess.engine.Cp(116), chess.BLACK))
            self.assertEqual(info["time"], 0.23)
            self.assertEqual(info["nodes"], 2252)
            self.assertEqual(info["pv"], [chess.Move.from_uci(move) for move in ["f7f6", "e2e4", "e7e6"]])
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_xboard_level(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["feature ping=1 setboard=1 done=1"])
            await protocol.initialize()
            mock.assert_done()

            limit = chess.engine.Limit(black_clock=65, white_clock=100,
                                       black_inc=4, white_inc=8)
            mock.expect("new")
            mock.expect("force")
            mock.expect("level 0 1:40 8")
            mock.expect("time 10000")
            mock.expect("otim 6500")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e2e4"])
            mock.expect_ping()
            result = await protocol.play(chess.Board(), limit)
            self.assertEqual(result.move, chess.Move.from_uci("e2e4"))
            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    def test_xboard_error(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["Error (failed to initialize): Too bad!"])
            with self.assertRaises(chess.engine.EngineError):
                await protocol.initialize()

            with self.assertRaises(chess.engine.EngineError):
                # Trying to use the engine, but it was not successfully initialized.
                await protocol.ping()

            mock.assert_done()

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    @catchAndSkip(FileNotFoundError, "need /bin/bash")
    def test_transport_close_with_pending(self):
        async def main():
            transport, protocol = await chess.engine.popen_uci(["/bin/bash", "-c", "read && echo uciok && sleep 86400"])
            protocol.loop.call_later(0.01, transport.close)
            results = await asyncio.gather(protocol.ping(), protocol.ping(), return_exceptions=True)
            self.assertNotEqual(results[0], None)
            self.assertNotEqual(results[1], None)

        asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
        asyncio.run(main())

    @catchAndSkip(FileNotFoundError, "need /bin/bash")
    def test_quit_timeout(self):
        with chess.engine.SimpleEngine.popen_uci(["/bin/bash", "-c", "read && echo uciok && sleep 86400"], debug=True) as engine:
            engine.timeout = 0.01
            with self.assertRaises(asyncio.TimeoutError):
                engine.quit()

    def test_run_in_background(self):
        class ExpectedError(Exception):
            pass

        async def raise_expected_error(future):
            await asyncio.sleep(0.001)
            raise ExpectedError

        with self.assertRaises(ExpectedError):
            chess.engine.run_in_background(raise_expected_error)

        async def resolve(future):
            await asyncio.sleep(0.001)
            future.set_result("resolved")
            await asyncio.sleep(0.001)

        result = chess.engine.run_in_background(resolve)
        self.assertEqual(result, "resolved")


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
        # Test the number of 6-piece tables.
        self.assertEqual(sum(1 for eg in chess.syzygy.tablenames(one_king=False) if len(eg) == 7), 5754)

    def test_normalize_tablename(self):
        names = set(chess.syzygy.tablenames())
        for name in names:
            self.assertTrue(
                chess.syzygy.normalize_tablename(name) in names,
                f"Already normalized {name}")

            w, b = name.split("v", 1)
            swapped = b + "v" + w
            self.assertTrue(
                chess.syzygy.normalize_tablename(swapped) in names,
                f"Normalized {swapped}")

    def test_normalize_nnvbb(self):
        self.assertEqual(chess.syzygy.normalize_tablename("KNNvKBB"), "KBBvKNN")

    def test_dependencies(self):
        self.assertEqual(set(chess.syzygy.dependencies("KBNvK")), set(["KBvK", "KNvK"]))

    def test_get_wdl_get_dtz(self):
        with chess.syzygy.Tablebase() as tables:
            board = chess.Board()
            self.assertEqual(tables.get_dtz(board, tables.get_wdl(board)), None)

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
        with chess.syzygy.Tablebase(max_fds=2) as tables:
            self.assertGreaterEqual(tables.add_directory("data/syzygy/regular"), 70)

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
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables:
            # Winning KPvKP because of en passant.
            board = chess.Board("8/8/8/k2Pp3/8/8/8/4K3 w - e6 0 2")

            # If there was no en passant, this would be a draw.
            self.assertEqual(tables.probe_wdl_table(board), 0)

            # But it is a win.
            self.assertEqual(tables.probe_wdl(board), 2)

    def test_dtz_ep(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables:
            board = chess.Board("8/8/8/8/2pP4/2K5/4k3/8 b - d3 0 1")
            self.assertEqual(tables.probe_dtz_no_ep(board), -1)
            self.assertEqual(tables.probe_dtz(board), 1)

    def test_testsuite(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables, open("data/endgame.epd") as epds:
            board = chess.Board()

            for line, epd in enumerate(epds):
                extra = board.set_epd(epd)

                wdl_table = tables.probe_wdl_table(board)
                self.assertEqual(
                    wdl_table, extra["wdl_table"],
                    f"Expecting wdl_table {extra['wdl_table']} for {board.fen()}, got {wdl_table} (at line {line + 1})")

                wdl = tables.probe_wdl(board)
                self.assertEqual(
                    wdl, extra["wdl"],
                    f"Expecting wdl {extra['wdl']} for {board.fen()}, got {wdl} (at line {line + 1})")

                dtz = tables.probe_dtz(board)
                self.assertEqual(
                    dtz, extra["dtz"],
                    f"Expecting dtz {extra['dtz']} for {board.fen()}, got {dtz} (at line {line + 1})")

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_stockfish_dtz_bug(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables:
            board = chess.Board("3K4/8/3k4/8/4p3/4B3/5P2/8 w - - 0 5")
            self.assertEqual(tables.probe_dtz(board), 15)

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_issue_93(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables:
            board = chess.Board("4r1K1/6PP/3k4/8/8/8/8/8 w - - 1 64")
            self.assertEqual(tables.probe_wdl(board), 2)
            self.assertEqual(tables.probe_dtz(board), 4)

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_suicide_dtm(self):
        with chess.syzygy.open_tablebase("data/syzygy/suicide", VariantBoard=chess.variant.SuicideBoard) as tables, open("data/suicide-dtm.epd") as epds:
            for epd in epds:
                epd = epd.strip()

                board, solution = chess.variant.SuicideBoard.from_epd(epd)

                wdl = tables.probe_wdl(board)

                expected_wdl = ((solution["max_dtm"] > 0) - (solution["max_dtm"] < 0)) * 2
                self.assertEqual(wdl, expected_wdl, f"Expecting wdl {expected_wdl}, got {wdl} (in {epd})")

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
        with chess.syzygy.open_tablebase("data/syzygy/suicide", VariantBoard=chess.variant.SuicideBoard) as tables, open("data/suicide-dtz.epd") as epds:
            for epd in epds:
                epd = epd.strip()
                if epd.startswith("%") or epd.startswith("#"):
                    continue

                board, solution = chess.variant.SuicideBoard.from_epd(epd)

                dtz = tables.probe_dtz(board)
                self.assertEqual(dtz, solution["dtz"], f"Expecting dtz {solution['dtz']}, got {dtz} (in {epd})")

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_suicide_stats(self):
        board = chess.variant.SuicideBoard()

        with chess.syzygy.open_tablebase("data/syzygy/suicide", VariantBoard=type(board)) as tables, open("data/suicide-stats.epd") as epds:
            for l, epd in enumerate(epds):
                solution = board.set_epd(epd)

                dtz = tables.probe_dtz(board)
                self.assertAlmostEqual(dtz, solution["dtz"], delta=1,
                                       msg=f"Expected dtz {solution['dtz']}, got {dtz} (in l. {l + 1}, fen: {board.fen()})")

    def test_antichess_kvk(self):
        kvk = chess.variant.AntichessBoard("4k3/8/8/8/8/8/8/4K3 w - - 0 1")

        tables = chess.syzygy.Tablebase()
        with self.assertRaises(KeyError):
            tables.probe_dtz(kvk)

        tables = chess.syzygy.Tablebase(VariantBoard=chess.variant.AntichessBoard)
        with self.assertRaises(chess.syzygy.MissingTableError):
            tables.probe_dtz(kvk)


class NativeGaviotaTestCase(unittest.TestCase):

    @unittest.skipUnless(platform.python_implementation() == "CPython", "need CPython for native Gaviota")
    @catchAndSkip((OSError, RuntimeError), "need libgtb")
    def setUp(self):
        self.tablebase = chess.gaviota.open_tablebase_native("data/gaviota")

    def tearDown(self):
        self.tablebase.close()

    def test_native_probe_dtm(self):
        board = chess.Board("6K1/8/8/8/4Q3/8/6k1/8 b - - 0 1")
        self.assertEqual(self.tablebase.probe_dtm(board), -14)

        board = chess.Board("8/3K4/8/8/8/4r3/4k3/8 b - - 0 1")
        self.assertEqual(self.tablebase.get_dtm(board), 21)

    def test_native_probe_wdl(self):
        board = chess.Board("8/8/4K3/2n5/8/3k4/8/8 w - - 0 1")
        self.assertEqual(self.tablebase.probe_wdl(board), 0)

        board = chess.Board("8/8/1p2K3/8/8/3k4/8/8 b - - 0 1")
        self.assertEqual(self.tablebase.get_wdl(board), 1)

    @catchAndSkip(chess.gaviota.MissingTableError, "need KPPvKP.gtb.cp4")
    def test_two_ep(self):
        board = chess.Board("8/8/8/8/5pPp/8/5K1k/8 b - g3 0 61")
        self.assertEqual(self.tablebase.probe_dtm(board), 19)


class GaviotaTestCase(unittest.TestCase):

    @catchAndSkip(ImportError)
    def setUp(self):
        self.tablebase = chess.gaviota.open_tablebase("data/gaviota", LibraryLoader=None)

    def tearDown(self):
        self.tablebase.close()

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
                dtm = self.tablebase.probe_dtm(board)
                self.assertEqual(dtm, expected, f"Expecting dtm {expected} for {board.fen()}, got {dtm} (at line {line + 1})")

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
                dtm = self.tablebase.probe_dtm(board)
                self.assertEqual(dtm, expected, f"Expecting dtm {expected} for {board.fen()}, got {dtm} (at line {line + 1})")

    def test_wdl(self):
        board = chess.Board("8/8/4K3/2n5/8/3k4/8/8 w - - 0 1")
        self.assertEqual(self.tablebase.probe_wdl(board), 0)

        board = chess.Board("8/8/1p2K3/8/8/3k4/8/8 b - - 0 1")
        self.assertEqual(self.tablebase.probe_wdl(board), 1)

    def test_context_manager(self):
        self.assertTrue(self.tablebase.available_tables)

        with self.tablebase:
            pass

        self.assertFalse(self.tablebase.available_tables)

    @catchAndSkip(chess.gaviota.MissingTableError, "need KPPvKP.gtb.cp4")
    def test_two_ep(self):
        board = chess.Board("8/8/8/8/5pPp/8/5K1k/8 b - g3 0 61")
        self.assertEqual(self.tablebase.probe_dtm(board), 19)

        board = chess.Board("K7/8/8/6k1/5pPp/8/8/8 b - g3 0 61")
        self.assertEqual(self.tablebase.probe_dtm(board), 17)


class SvgTestCase(unittest.TestCase):

    def test_svg_board(self):
        svg = chess.BaseBoard("4k3/8/8/8/8/8/8/4KB2")._repr_svg_()
        self.assertIn("white bishop", svg)
        self.assertNotIn("black queen", svg)

    def test_svg_arrows(self):
        svg = chess.svg.board(arrows=[(chess.A1, chess.A1)])
        self.assertIn("<circle", svg)
        self.assertNotIn("<line", svg)

        svg = chess.svg.board(arrows=[chess.svg.Arrow(chess.A1, chess.H8)])
        self.assertNotIn("<circle", svg)
        self.assertIn("<line", svg)

    def test_svg_piece(self):
        svg = chess.svg.piece(chess.Piece.from_symbol("K"))
        self.assertIn("id=\"white-king\"", svg)


class SuicideTestCase(unittest.TestCase):

    def test_parse_san(self):
        board = chess.variant.SuicideBoard()
        board.push_san("e4")
        board.push_san("d5")

        # Capture is mandatory.
        with self.assertRaises(chess.IllegalMoveError):
            board.push_san("Nf3")

    def test_is_legal(self):
        board = chess.variant.SuicideBoard("4k3/8/8/8/8/1r3B2/8/4K3 b - - 0 1")
        Rxf3 = board.parse_san("Rxf3")
        Rb4 = chess.Move.from_uci("b3b4")
        self.assertTrue(board.is_legal(Rxf3))
        self.assertIn(Rxf3, board.generate_legal_moves())
        self.assertFalse(board.is_legal(Rb4))
        self.assertNotIn(Rb4, board.generate_legal_moves())

    def test_suicide_insufficient_material(self):
        # Kings only.
        board = chess.variant.SuicideBoard("8/8/8/2k5/8/8/4K3/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Bishops on the same color.
        board = chess.variant.SuicideBoard("8/8/8/5b2/2B5/1B6/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Opposite-color bishops.
        board = chess.variant.SuicideBoard("4b3/8/8/8/3B4/2B5/8/8 b - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # Pawn not blocked.
        board = chess.variant.SuicideBoard("8/5b2/5P2/8/3B4/2B5/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Pawns blocked, but on wrong color.
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

        # Ignore check to explode the opponent's king.
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
        # Real-world position.
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

        # Only bishops, but no captures possible.
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

        # KQN can win (even KQ could).
        board = chess.variant.AtomicBoard("3Q4/5kKB/8/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

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

        board = chess.variant.AtomicBoard("8/8/8/8/8/8/4k3/R3K2q w Q - 0 1")
        board.push_san("O-O-O")
        self.assertEqual(board.fen(), "8/8/8/8/8/8/4k3/2KR3q b - - 1 1")

        board = chess.variant.AtomicBoard("8/8/8/8/8/8/5k2/R3K2r w Q - 0 1")
        with self.assertRaises(chess.IllegalMoveError):
            board.push_san("O-O-O")

        board = chess.variant.AtomicBoard("8/8/8/8/8/8/6k1/R5Kr w Q - 0 1", chess960=True)
        with self.assertRaises(chess.IllegalMoveError):
            board.push_san("O-O-O")

        board = chess.variant.AtomicBoard("8/8/8/8/8/8/4k3/r2RK2r w D - 0 1", chess960=True)
        with self.assertRaises(chess.IllegalMoveError):
            board.push_san("O-O-O")

    def test_castling_rights_explode_with_king(self):
        board = chess.variant.AtomicBoard("rnb1kbnr/pppppppp/8/4q3/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1")
        board.push_san("Qxe2#")
        self.assertEqual(board.fen(), "rnb1kbnr/pppppppp/8/8/8/8/PPPP1PPP/RNB3NR w kq - 0 2")
        self.assertEqual(board.castling_rights, chess.BB_A8 | chess.BB_H8)

    def test_lone_king_wdl(self):
        tables = chess.syzygy.Tablebase(VariantBoard=chess.variant.AtomicBoard)
        board = chess.variant.AtomicBoard.empty()
        board.set_piece_at(chess.D1, chess.Piece.from_symbol("k"))
        self.assertEqual(tables.probe_wdl(board), -2)

    def test_atomic_validity(self):
        # 14 checkers, the maximum in Atomic chess.
        board = chess.variant.AtomicBoard("3N1NB1/2N1Q1N1/3RkR2/2NP1PN1/3NKN2/8/8/n7 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_VALID)

    def test_atomic960(self):
        pgn = io.StringIO(textwrap.dedent("""\
            [Variant "Atomic"]
            [FEN "rkrbbnnq/pppppppp/8/8/8/8/PPPPPPPP/RKRBBNNQ w KQkq - 0 1"]

            1. g3 d5 2. Nf3 e5 3. Ng5 Bxg5 4. Qf3 Ne6 5. Qa3 a5 6. d4 g6 7. c3 h5 8. h4 Qh6 9. Bd2 Qxd2 10. O-O-O *
            """))
        game = chess.pgn.read_game(pgn)
        self.assertTrue(game.board().chess960)
        self.assertEqual(game.end().parent.board().fen(), "rkr1b1n1/1pp2p2/4n1p1/p2pp2p/3P3P/Q1P3P1/PP2PP2/RK3N2 w Qkq - 0 10")
        self.assertEqual(game.end().board().fen(), "rkr1b1n1/1pp2p2/4n1p1/p2pp2p/3P3P/Q1P3P1/PP2PP2/2KR1N2 b kq - 1 10")

    def test_atomic_king_exploded(self):
        board = chess.variant.AtomicBoard("rn5r/pp4pp/2p3Nn/5p2/1b2P1PP/8/PPP2P2/R1B1KB1R b KQ - 0 9")
        self.assertEqual(board.outcome().winner, chess.WHITE)
        self.assertEqual(board.status(), chess.STATUS_VALID)


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

        # White far away.
        board = chess.variant.RacingKingsBoard("k1q1R2Q/3N4/8/8/5K2/6n1/1b6/1r6 w - - 4 19")
        self.assertTrue(board.is_variant_end())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertFalse(board.is_variant_draw())
        self.assertEqual(board.result(), "0-1")

        # Black near backrank, but cannot move there.
        board = chess.variant.RacingKingsBoard("2KR4/k7/2Q5/4q3/8/8/8/2N5 b - - 0 1")
        self.assertTrue(board.is_variant_end())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertFalse(board.is_variant_draw())
        self.assertEqual(board.result(), "1-0")

        # Black two moves away.
        board = chess.variant.RacingKingsBoard("1r4RK/6R1/k1r5/8/8/8/4N3/q2n1n2 b - - 0 1")
        self.assertTrue(board.is_variant_end())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertFalse(board.is_variant_draw())
        self.assertEqual(board.result(), "1-0")

        # Both sides already reached the backrank.
        board = chess.variant.RacingKingsBoard("kr3NK1/1q2R3/8/8/8/5n2/2N5/1rb2B1R w - - 11 14")
        self.assertTrue(board.is_variant_end())
        self.assertFalse(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_draw())
        self.assertEqual(board.result(), "1/2-1/2")

        # Another draw.
        board = chess.variant.RacingKingsBoard("1knq1RK1/2n5/8/8/3N4/6N1/6B1/8 w - - 23 25")
        self.assertTrue(board.is_variant_end())
        self.assertFalse(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_draw())
        self.assertEqual(board.result(), "1/2-1/2")

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

    def test_racing_kings_status_with_check(self):
        board = chess.variant.RacingKingsBoard("8/8/8/8/R7/8/krbnNB1K/qrbnNBRQ b - - 1 1")
        self.assertFalse(board.is_valid())
        self.assertEqual(board.status(), chess.STATUS_RACE_CHECK | chess.STATUS_TOO_MANY_CHECKERS | chess.STATUS_IMPOSSIBLE_CHECK)


class HordeTestCase(unittest.TestCase):

    def test_status(self):
        board = chess.variant.HordeBoard()
        self.assertEqual(board.status(), chess.STATUS_VALID)

        # Black (non-horde) piece on first rank.
        board = chess.variant.HordeBoard("rnb1kbnr/ppp1pppp/2Pp2PP/1P3PPP/PPP1PPPP/PPP1PPPP/PPP1PPP1/PPPqPP2 w kq - 0 1")
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

        # En passant not possible.
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

    def test_mirror_checks(self):
        fen = "3R4/1p3rpk/p4p1p/2B1n3/8/2P1PP2/bPN4P/6K1 w - - 5 29 +2+0"
        board = chess.variant.ThreeCheckBoard(fen)
        self.assertEqual(board, board.mirror().mirror())

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

        # Lose castling rights.
        move = board.parse_san("Ke7")
        self.assertTrue(board.is_irreversible(move))
        board.push(move)

        # Give check.
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

    def test_three_check_root(self):
        board = chess.variant.ThreeCheckBoard("r1bq1bnr/pppp1kpp/2n5/4p3/4P3/8/PPPP1PPP/RNBQK1NR w KQ - 2+3 0 4")
        self.assertEqual(board.root().remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.root().remaining_checks[chess.BLACK], 3)
        self.assertEqual(board.copy().root().remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.copy().root().remaining_checks[chess.BLACK], 3)

        board.push_san("Qf3+")
        board.push_san("Ke6")
        board.push_san("Qb3+")
        self.assertEqual(board.root().remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.root().remaining_checks[chess.BLACK], 3)
        self.assertEqual(board.copy().root().remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.copy().root().remaining_checks[chess.BLACK], 3)

    def test_three_check_epd(self):
        board, ops = chess.variant.ThreeCheckBoard.from_epd("rnb1kbnr/pppp1ppp/8/8/2B1Pp1q/8/PPPP2PP/RNBQ1KNR b kq - 3+2 hmvc 3; fmvn 4; bm Qf2+")
        self.assertEqual(board.remaining_checks[chess.WHITE], 3)
        self.assertEqual(board.remaining_checks[chess.BLACK], 2)
        self.assertEqual(board.halfmove_clock, 3)
        self.assertEqual(board.fullmove_number, 4)
        self.assertEqual(ops["bm"], [chess.Move.from_uci("h4f2")])


class CrazyhouseTestCase(unittest.TestCase):

    def test_pawn_drop(self):
        board = chess.variant.CrazyhouseBoard("r2q1rk1/ppp2pp1/1bnp3p/3B4/3PP1b1/4PN2/PP4PP/R2Q1RK1[BNPnp] b - - 0 13")
        P_at_e6 = chess.Move.from_uci("P@e6")
        self.assertIn(chess.E6, board.legal_drop_squares())
        self.assertIn(P_at_e6, board.generate_legal_moves())
        self.assertTrue(board.is_pseudo_legal(P_at_e6))
        self.assertTrue(board.is_legal(P_at_e6))
        self.assertEqual(board.uci(P_at_e6), "P@e6")
        self.assertEqual(board.san(P_at_e6), "@e6")

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

    def test_illegal_drop_uci(self):
        board = chess.variant.CrazyhouseBoard()
        with self.assertRaises(chess.IllegalMoveError):
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

    def test_mirror_pockets(self):
        fen = "r1b1k2r/p1pq1ppp/1bBbnp2/8/6N1/5P2/PPP2PPP/R4RK1/PQPPNn w kq - 30 16"
        board = chess.variant.CrazyhouseBoard(fen)
        self.assertEqual(board, board.mirror().mirror())

    def test_root_pockets(self):
        board = chess.variant.CrazyhouseBoard("r2B1rk1/ppp2ppp/3p4/4p3/2B5/2NP1R1P/PPPn2K1/8/QPBQPRNNbp w - - 40 21")
        white_pocket = "qqrbnnpp"
        black_pocket = "bp"
        self.assertEqual(str(board.root().pockets[chess.WHITE]), white_pocket)
        self.assertEqual(str(board.root().pockets[chess.BLACK]), black_pocket)
        self.assertEqual(str(board.copy().root().pockets[chess.WHITE]), white_pocket)
        self.assertEqual(str(board.copy().root().pockets[chess.BLACK]), black_pocket)

        board.push_san("N@h6+")
        board.push_san("Kh8")
        board.push_san("R@g8+")
        board.push_san("Rxg8")
        board.push_san("Nxf7#")
        self.assertEqual(str(board.root().pockets[chess.WHITE]), white_pocket)
        self.assertEqual(str(board.root().pockets[chess.BLACK]), black_pocket)
        self.assertEqual(str(board.copy().root().pockets[chess.WHITE]), white_pocket)
        self.assertEqual(str(board.copy().root().pockets[chess.BLACK]), black_pocket)

    def test_zh_is_irreversible(self):
        board = chess.variant.CrazyhouseBoard("r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1")
        self.assertTrue(board.is_irreversible(board.parse_san("Ra2")))
        self.assertTrue(board.is_irreversible(board.parse_san("O-O-O")))
        self.assertTrue(board.is_irreversible(board.parse_san("Kd1")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxa8")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxh8")))
        self.assertFalse(board.is_irreversible(board.parse_san("Rf1")))
        self.assertFalse(board.is_irreversible(chess.Move.null()))


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
