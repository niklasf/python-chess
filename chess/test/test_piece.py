import chess
import unittest

class PieceTestCase(unittest.TestCase):
    """Tests the Piece class."""

    def test_from_symbol(self):
        """Tests symbol parsing."""
        black_queen = chess.Piece.from_symbol('q')
        self.assertEqual(black_queen.get_symbol(), 'q')

        white_pawn = chess.Piece.from_symbol('P')
        self.assertEqual(white_pawn.get_symbol(), 'P')

    def test_equality(self):
        """Tests the overriden equality behavior of the Piece class."""
        a = chess.Piece(type='b', color='w')
        b = chess.Piece(type='k', color='b')
        c = chess.Piece(type='k', color='w')
        d = chess.Piece(type='b', color='w')

        self.assertEqual(a, d)
        self.assertEqual(d, a)

        self.assertEqual(repr(a), repr(d))

        self.assertNotEqual(a, b)
        self.assertNotEqual(b, c)
        self.assertNotEqual(b, d)
        self.assertNotEqual(a, c)

    def test_simple_properties(self):
        """Tests simple properties."""
        white_knight = chess.Piece(type='n', color='w')

        self.assertEqual(white_knight.get_color(), 'w')
        self.assertEqual(white_knight.get_full_color(), 'white')

        self.assertEqual(white_knight.get_type(), 'n')
        self.assertEqual(white_knight.get_full_type(), 'knight')
