import libchess
import unittest

class UtilTestCase(unittest.TestCase):
    """Tests utility functions."""

    def test_opposite_color(self):
        """Tests the opposite color function."""
        self.assertEqual(libchess.opposite_color("w"), "b")
        self.assertEqual(libchess.opposite_color("b"), "w")
