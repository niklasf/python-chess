#!/usr/bin/python3

import chess
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

        # Let both sides castle.
        bitboard.push(chess.Move.from_uci("e1g1"))
        bitboard.push(chess.Move.from_uci("e8c8"))
        self.assertEqual(bitboard.fen(), "2kr3r/8/8/8/8/8/8/R4RK1 w - - 3 2")

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


if __name__ == "__main__":
    unittest.main()
