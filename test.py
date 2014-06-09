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

        a = chess.Bitboard()
        a.push_san("d4")
        b = chess.Bitboard()
        b.push_san("d3")
        self.assertNotEqual(a, b)

    def test_status(self):
        board = chess.Bitboard()
        self.assertEqual(board.status(), chess.STATUS_VALID)

        board.remove_piece_at(chess.H1)
        self.assertTrue(board.status() & chess.STATUS_BAD_CASTLING_RIGHTS)

        board.remove_piece_at(chess.E8)
        self.assertTrue(board.status() & chess.STATUS_NO_BLACK_KING)

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


class LegalMoveGeneratorTestCase(unittest.TestCase):

    def test_list_conversion(self):
        self.assertEqual(len(list(chess.Bitboard().legal_moves)), 20)

    def test_nonzero(self):
        self.assertTrue(chess.Bitboard().legal_moves)

        caro_kann_mate = chess.Bitboard("r1bqkb1r/pp1npppp/2pN1n2/8/3P4/8/PPP1QPPP/R1B1KBNR b KQkq - 4 6")
        self.assertFalse(caro_kann_mate.legal_moves)


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


class PgnTestCase(unittest.TestCase):

    def test_gamenode(self):
        game = chess.pgn.Game()
        game.starting_comment = "Test game:"
        game.result = "*"

        e4 = game.add_variation(game.board().parse_san("e4"))

        e4_d5 = e4.add_variation(e4.board().parse_san("d5"))
        e4_d5.starting_comment = "Scandinavian defense:"

        e4_h5 = e4.add_variation(e4.board().parse_san("h5"))
        e4_h5.nags.append(chess.pgn.NAG_MISTAKE)
        e4_h5.comment = "is nonesense"

        e4_e5 = e4.add_variation(e4.board().parse_san("e5"))
        e4_e5_Qf3 = e4_e5.add_variation(e4_e5.board().parse_san("Qf3"))
        e4_e5_Qf3.nags.append(chess.pgn.NAG_MISTAKE)

        e4_c5 = e4.add_variation(e4.board().parse_san("c5"))
        e4_c5.comment = "Sicilian"

if __name__ == "__main__":
    unittest.main()
