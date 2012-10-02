import libchess
import unittest

class PieceTestCase(unittest.TestCase):
    """Tests the Piece class."""

    def test_from_symbol(self):
        """Tests symbol parsing."""
        black_queen = libchess.Piece.from_symbol('q')
        self.assertEqual(black_queen.get_symbol(), 'q')

        white_pawn = libchess.Piece.from_symbol('P')
        self.assertEqual(white_pawn.get_symbol(), 'P')

    def test_equality(self):
        """Tests the overriden equality behavior of the Piece class."""
        a = libchess.Piece(type='b', color='w')
        b = libchess.Piece(type='k', color='b')
        c = libchess.Piece(type='k', color='w')
        d = libchess.Piece(type='b', color='w')

        self.assertEqual(a, d)
        self.assertEqual(d, a)

        self.assertNotEqual(a, b)
        self.assertNotEqual(b, c)
        self.assertNotEqual(b, d)
        self.assertNotEqual(a, c)

    def test_simple_properties(self):
        """Tests simple properties."""
        white_knight = libchess.Piece(type='n', color='w')

        self.assertEqual(white_knight.get_color(), 'w')
        self.assertEqual(white_knight.get_full_color(), 'white')

        self.assertEqual(white_knight.get_type(), 'n')
        self.assertEqual(white_knight.get_full_type(), 'knight')
