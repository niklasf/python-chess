import chess
import unittest
import random

class ZobristHasherTestCase(unittest.TestCase):
    """Tests the ZobristHasher class."""

    def test_polyglot_hashing(self):
        """Tests zobrist hashing against the polyglot reference examples given
        on http://hardy.uhasselt.be/Toga/book_format.html."""
        hasher = chess.ZobristHasher(chess.ZobristHasher.POLYGLOT_RANDOM_ARRAY)

        pos = chess.Position()
        self.assertEqual(hasher.hash_position(pos), 0x463b96181691fc9c)

        pos = chess.Position("rnbqkbnr/p1pppppp/8/8/P6P/R1p5/1P1PPPP1/1NBQKBNR b Kkq - 0 4")
        self.assertEqual(hasher.hash_position(pos), 0x5c3f9b829b279560)

        pos = chess.Position("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        self.assertEqual(hasher.hash_position(pos), 0x823c9b50fd114196)

        pos = chess.Position("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
        self.assertEqual(hasher.hash_position(pos), 0x0756b94461c50fb0)

        pos = chess.Position("rnbq1bnr/ppp1pkpp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR w - - 0 4")
        self.assertEqual(hasher.hash_position(pos), 0x00fdd303c946bdd9)

        # Real en-passant possible.
        pos = chess.Position("rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3")
        self.assertEqual(hasher.hash_position(pos), 0x22a48b5a8e47ff78)

    def test_random_hasher(self):
        """Tests zobrist hashing with a random field."""
        random.seed(3456789)
        hasher = chess.ZobristHasher.create_random()

        a = chess.Position()

        b = chess.Position()
        b.make_move(chess.Move.from_uci("e2e4"))

        self.assertNotEqual(hasher.hash_position(a), hasher.hash_position(b))
