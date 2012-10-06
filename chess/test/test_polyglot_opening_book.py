import chess
import unittest

class PolyglotOpeningBookTestCase(unittest.TestCase):
    def test_performance_bin(self):
        pos = chess.Position()
        book = chess.PolyglotOpeningBook("data/opening-books/performance.bin")

        e4 = book.get_entries_for_position(pos).next()
        self.assertEqual(e4["move"], pos.get_move_from_san("e4"))
        pos.make_move(e4["move"])

        e5 = book.get_entries_for_position(pos).next()
        self.assertEqual(e5["move"], pos.get_move_from_san("e5"))
        pos.make_move(e5["move"])
