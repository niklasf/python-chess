import chess
import unittest

class UtilTestCase(unittest.TestCase):
    """Tests utility functions."""

    def test_opposite_color(self):
        """Tests the opposite color function."""
        self.assertEqual(chess.opposite_color("w"), "b")
        self.assertEqual(chess.opposite_color("b"), "w")
