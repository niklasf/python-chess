import libchess
import unittest

class SquareTestCase(unittest.TestCase):
    """Tests the Square class."""

    def test_equality(self):
        """Tests the overriden equality behaviour of the Square class."""
        a = libchess.Square.from_name('b4')
        b = libchess.Square.from_name('b4')
        c = libchess.Square.from_name('b3')
        d = libchess.Square.from_name('f3')

        self.assertEqual(a, b)
        self.assertEqual(b, a)

        self.assertNotEqual(a, c)
        self.assertNotEqual(a, d)
        self.assertNotEqual(c, d)

    def test_simple_properties(self):
        """Tests simple properties of Square objects."""
        f7 = libchess.Square.from_name('f7')
        self.assertFalse(f7.is_dark())
        self.assertTrue(f7.is_light())
        self.assertEqual(f7.get_rank(), 7)
        self.assertEqual(f7.get_file(), 'f')
        self.assertEqual(f7.get_name(), 'f7')
        self.assertEqual(f7.get_0x88_index(), 101)
        self.assertEqual(f7.get_x(), 5)
        self.assertEqual(f7.get_y(), 6)
        self.assertFalse(f7.is_backrank())

    def test_creation(self):
        """Tests creation of Square instances."""
        self.assertEqual(libchess.Square(3, 5), libchess.Square.from_name('d6'))
        self.assertEqual(libchess.Square.from_0x88_index(2), libchess.Square.from_name('c1'))
        self.assertEqual(libchess.Square.from_rank_and_file(rank=2, file='g'), libchess.Square.from_name('g2'))
