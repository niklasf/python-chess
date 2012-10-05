import libchess
import unittest

class PositionBuilderTestCase(unittest.TestCase):
    """Tests the position builder class."""

    def test_fens(self):
        """Tests FEN parsing and generating."""
        builder = libchess.PositionBuilder()
        self.assertEqual(builder.get_fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

        builder.set_fen("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        self.assertEqual(builder.get_fen(), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
