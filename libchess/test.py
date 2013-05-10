#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import libchess


class CommonTestCase(unittest.TestCase):

    def test_opposite_color(self):
        self.assertEqual(libchess.opposite_color("w"), "b")
        self.assertEqual(libchess.opposite_color("b"), "w")


class PieceTestCase(unittest.TestCase):

    def test(self):
        # Properties of a black piece.
        black_pawn = libchess.Piece("p")
        self.assertEqual(black_pawn.type, "p")
        self.assertEqual(black_pawn.symbol, "p")
        self.assertEqual(black_pawn.color, "b")
        self.assertEqual(black_pawn.full_color, "black")
        self.assertEqual(black_pawn.full_type, "pawn")

        # Properties of a white piece.
        white_queen = libchess.Piece("Q")
        self.assertEqual(white_queen.type, "q")
        self.assertEqual(white_queen.symbol, "Q")
        self.assertEqual(white_queen.color, "w")
        self.assertEqual(white_queen.full_color, "white")
        self.assertEqual(white_queen.full_type, "queen")

        # Comparison.
        self.assertEqual(black_pawn, libchess.Piece("p"))
        self.assertNotEqual(black_pawn, white_queen)
        self.assertNotEqual(black_pawn, None)
        self.assertFalse(black_pawn != libchess.Piece("p"))

        # String representation.
        self.assertEqual(str(black_pawn), "p")

        # Test dictionary with pieces.
        a = dict()
        a[black_pawn] = "foo"
        a[white_queen] = "bar"
        a[libchess.Piece("Q")] = "baz"
        self.assertEqual(a[black_pawn], "foo")
        self.assertEqual(a[white_queen], "baz")

        # Test non-default constructor.
        white_rook = libchess.Piece.from_color_and_type("w", "r")
        self.assertEqual(white_rook.symbol, "R")


class SquareTestCase(unittest.TestCase):

    def test(self):
        # Properties.
        a2 = libchess.Square("a2")
        self.assertEqual(a2.rank, 1)
        self.assertEqual(a2.file, 0)
        self.assertEqual(a2.name, "a2")
        self.assertEqual(a2.file_name, "a")

    def test_x88_index(self):
        f7 = libchess.Square("f7")
        self.assertEqual(f7.x88_index, 21)

        c8 = libchess.Square("c8")
        self.assertEqual(libchess.Square.from_x88_index(2), c8)


class MoveTestCase(unittest.TestCase):

    def test(self):
        # Properties.
        move = libchess.Move.from_uci("e7e8q")
        self.assertEqual(move.source, libchess.Square("e7"))
        self.assertEqual(move.target, libchess.Square("e8"))
        self.assertEqual(move.promotion, "q")
        self.assertEqual(move.full_promotion, "queen")


class PositionTestCase(unittest.TestCase):

    def test_board(self):
        position = libchess.Position()

        # Read.
        self.assertEqual(position[libchess.Square("a1")], libchess.Piece("R"))
        self.assertEqual(position[libchess.Square("e8")], libchess.Piece("k"))
        self.assertTrue(position[libchess.Square("h3")] is None)

        # Write.
        e2 = libchess.Square("e2")
        e4 = libchess.Square("e4")
        position[e4] = position[e2]
        del position[e2]
        self.assertEqual(position[e4], libchess.Piece("P"))
        self.assertTrue(position[e2] is None)

    def test_board_shorthand(self):
        position = libchess.Position()

        self.assertEqual(position["f8"], libchess.Piece("b"))

        del position["a1"]
        self.assertTrue(position["a1"] is None)

        position["h8"] = libchess.Piece("q")
        self.assertEqual(position["h8"], libchess.Piece("q"))

    def test_ep_file(self):
        position = libchess.Position()
        self.assertTrue(position.ep_file is None)
        position.ep_file = "e"
        self.assertEqual(position.ep_file, "e")
        position.ep_file = None
        self.assertTrue(position.ep_file is None)

        position = libchess.Position()
        self.assertTrue(position.get_ep_square() is None)
        position["e4"] = libchess.Piece("P")
        position.ep_file = "e"
        self.assertTrue(position.get_ep_square() is None)
        position.turn = "b"
        self.assertEqual(position.get_ep_square(), libchess.Square("e3"))
        del position["e2"]
        position["e3"] = libchess.Piece("N")
        self.assertTrue(position.get_ep_square() is None)

    def test_turn(self):
        position = libchess.Position()
        self.assertEqual(position.turn, "w")
        position.turn = "b"
        self.assertEqual(position.turn, "b")
        position.toggle_turn()
        self.assertEqual(position.turn, "w")

    def test_hash(self):
        position = libchess.Position()
        self.assertEqual(hash(position), 0x463b96181691fc9c)

    def test_fen(self):
        position = libchess.Position()
        self.assertEqual(position.fen, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

        position.fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2";
        self.assertEqual(position["h1"], libchess.Piece("R"))
        self.assertEqual(position.turn, "w")
        self.assertEqual(position.get_ep_square(), libchess.Square("d6"))
        self.assertEqual(position.half_moves, 0)
        self.assertEqual(position.ply, 2)

    def test_get_king(self):
        pos = libchess.Position()
        self.assertEqual(pos.get_king("w"), libchess.Square("e1"))
        self.assertEqual(pos.get_king("b"), libchess.Square("e8"))

    def test_checks(self):
        pos = libchess.Position("rnbqk1nr/ppp2ppp/4p3/3p4/1bPP4/5N2/PP2PPPP/RNBQKB1R w KQkq - 2 4")
        self.assertTrue(pos.is_king_attacked("w"))
        self.assertFalse(pos.is_king_attacked("b"))
        self.assertTrue(pos.is_check())

    def test_checkmate(self):
        pos = libchess.Position()
        self.assertFalse(pos.is_checkmate())

        pos.fen = "r1bqkbnr/p1pp1Qpp/2n5/1p2p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        self.assertTrue(pos.is_checkmate())

        pos.fen = "r1bqkb1r/pppp1Qpp/2n4n/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        self.assertFalse(pos.is_checkmate())

        pos.fen = "3k1R2/8/3K4/8/8/8/8/8 b - - 11 6"
        self.assertTrue(pos.is_checkmate())

    def test_stalemate(self):
        pos = libchess.Position()
        self.assertFalse(pos.is_stalemate())

        pos.fen = "4k3/4P3/4K3/8/8/8/8/8 b - - 4 9"
        self.assertTrue(pos.is_stalemate())

        pos.toggle_turn()
        self.assertFalse(pos.is_stalemate())

    def test_move_making(self):
        # Play fast: 1.e4 e5 2.Bc4.
        pos = libchess.Position()
        pos.make_move_fast(libchess.Move.from_uci("e2e4"))
        pos.make_move_fast(libchess.Move.from_uci("e7e5"))
        pos.make_move_fast(libchess.Move.from_uci("f1c4"))
        self.assertEqual(pos.fen, "rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 1 2")

        # Get move info for 2...Nf6.
        Nf6 = pos.make_move(libchess.Move.from_uci("g8f6"))
        self.assertEqual(Nf6.san, "Nf6")

    def test_castling(self):
        # Black can castle.
        pos = libchess.Position("rnbqk2r/ppppbppp/5n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R b KQkq - 5 4")
        self.assertTrue(pos.has_kingside_castling_right("b"))
        self.assertTrue(pos.could_have_kingside_castling_right("b"))
        castle = pos.make_move(libchess.Move.from_uci("e8g8"))
        self.assertEqual(pos.fen, "rnbq1rk1/ppppbppp/5n2/4p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQ - 6 5")
        self.assertEqual(castle.san, "o-o")
        self.assertTrue(castle.is_kingside_castle)
        self.assertFalse(castle.is_queenside_castle)

        # White can not castle kingside because of blacks rook.
        # White has no queenside castling rights.
        pos = libchess.Position("4kr2/8/8/8/8/8/8/R3K2R w K - 0 1")
        self.assertTrue(pos.has_kingside_castling_right("w"))
        self.assertFalse(libchess.Move.from_uci("e1g1") in pos.get_legal_moves())
        self.assertFalse(pos.has_queenside_castling_right("w"))
        self.assertFalse(libchess.Move.from_uci("e1c1") in pos.get_legal_moves())

        # Black could not even have castling rights.
        self.assertFalse(pos.could_have_kingside_castling_right("b"))
        self.assertFalse(pos.could_have_queenside_castling_right("b"))

    def test_san_disambiguation(self):
        pos = libchess.Position("4krN1/8/8/3N4/8/8/8/4K3 w - - 0 1")
        Ndf6 = pos.make_move(libchess.Move.from_uci("d5f6"))
        self.assertTrue(Ndf6.is_check)
        self.assertFalse(Ndf6.is_checkmate)
        self.assertEqual(Ndf6.san, "Ndf6+")

    def test_get_move_from_san(self):
        pos = libchess.Position()
        pos.make_move(pos.get_move_from_san("e4"))
        pos.make_move(pos.get_move_from_san("e5"))
        pos.make_move(pos.get_move_from_san("Nf3"))
        pos.make_move_from_san("Nc6")
        pos.make_move_from_san("Bb5")
        pos.make_move_from_san("Nf6")
        pos.make_move_from_san("o-o")
        self.assertEqual(pos.fen, "r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 5 4")


class PseudoLegalMoveGeneratorTestCase(unittest.TestCase):

    def test(self):
        # Get the number of moves in the initial position.
        pos = libchess.Position()
        self.assertEqual(len(pos.get_pseudo_legal_moves()), 20)

    def test_pawn_moves(self):
        # Single step.
        pos = libchess.Position()
        self.assertTrue(libchess.Move.from_uci("e2e4") in pos.get_pseudo_legal_moves())
        self.assertTrue(libchess.Move.from_uci("h2h3") in pos.get_pseudo_legal_moves())

        # Pawn captures after 1.e4 d5.
        pos = libchess.Position("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
        self.assertTrue(libchess.Move.from_uci("e4d5") in pos.get_pseudo_legal_moves())
        self.assertFalse(libchess.Move.from_uci("d5e4") in pos.get_pseudo_legal_moves())
        pos.toggle_turn()
        self.assertTrue(libchess.Move.from_uci("d5e4") in pos.get_pseudo_legal_moves())

    def test_knight_moves(self):
        pos = libchess.Position()
        self.assertTrue(libchess.Move.from_uci("g1f3") in pos.get_pseudo_legal_moves())

    def test_rook_moves(self):
        pos = libchess.Position()
        pos.turn = "b"
        del pos["h7"]
        self.assertTrue(libchess.Move.from_uci("h8h5") in pos.get_pseudo_legal_moves())
        self.assertTrue(libchess.Move.from_uci("h8h2") in pos.get_pseudo_legal_moves())
        self.assertFalse(libchess.Move.from_uci("h8h1") in pos.get_pseudo_legal_moves())


class MoveInfoTestCase(unittest.TestCase):

    def test(self):
        info = libchess.MoveInfo(libchess.Move.from_uci("e2e4"), libchess.Piece("P"))
        self.assertEqual(info.move, libchess.Move.from_uci("e2e4"))
        self.assertEqual(info.piece, libchess.Piece("P"))
        self.assertFalse(info.is_check)
        self.assertFalse(info.is_checkmate)
        self.assertFalse(info.is_castle)


class AttackerGeneratorTestCase(unittest.TestCase):

    def test_knight_and_pawn_attack(self):
        pos = libchess.Position()
        f6 = libchess.Square("f6")
        e3 = libchess.Square("e3")
        e5 = libchess.Square("e5")
        self.assertEqual(len(pos.get_attackers("b", f6)), 3)
        self.assertEqual(len(pos.get_attackers("w", e3)), 2)
        self.assertFalse(pos.get_attackers("b", e5))

    def test_allocation(self):
        pos = libchess.Position()
        attackers = pos.get_attackers("w", libchess.Square("a3"))
        self.assertEqual(attackers.__len__(), 2)
        del pos
        self.assertEqual(attackers.__len__(), 2)


class LegalMoveGeneratorTestCase(unittest.TestCase):

    def test_pseudo_legal_moves(self):
        # Test a move that is pseudo legal anyway.
        pos = libchess.Position()
        legal_moves = pos.get_legal_moves()
        self.assertEqual(len(legal_moves), 20)
        self.assertTrue(libchess.Move.from_uci("e2e4") in legal_moves)

        # Move generation did not change the position.
        self.assertEqual(pos, libchess.Position())


class PolyglotOpeningBookEntryTestCase(unittest.TestCase):

    def test(self):
        # Test legal moves in the position after 1.e4 e5 2.Nf3 Nc6 3.Bb5 Nf5
        # can be hashed and unhashed correctly.
        pos = libchess.Position("r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4")
        for move in pos.get_legal_moves():
            book_entry = libchess.PolyglotOpeningBookEntry(pos, move, 1, 0)
            self.assertEqual(move, book_entry.move)


if __name__ == "__main__":
    unittest.main()
