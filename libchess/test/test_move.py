import libchess
import unittest

class MoveTestCase(unittest.TestCase):
    """Tests the Move class."""

    def test_equality(self):
        """Tests the custom equality behaviour of the move class."""
        a = libchess.Move(libchess.Square.from_name('a1'), libchess.Square.from_name('a2'))
        b = libchess.Move(libchess.Square.from_name('a1'), libchess.Square.from_name('a2'))
        c = libchess.Move(libchess.Square.from_name('h7'), libchess.Square.from_name('h8'), 'b')
        d = libchess.Move(libchess.Square.from_name('h7'), libchess.Square.from_name('h8'))

        self.assertEqual(a, b)
        self.assertEqual(b, a)

        self.assertNotEqual(a, c)
        self.assertNotEqual(c, d)
        self.assertNotEqual(b, d)

    def test_uci_parsing(self):
        """Tests the UCI move parsing."""
        self.assertEqual(libchess.Move.from_uci('b5c7').get_uci(), 'b5c7')
        self.assertEqual(libchess.Move.from_uci('e7e8q').get_uci(), 'e7e8q')
