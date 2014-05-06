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


if __name__ == "__main__":
    unittest.main()
