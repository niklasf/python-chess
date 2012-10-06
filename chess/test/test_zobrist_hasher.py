import chess
import unittest

class ZobristHasherTestCase(unittest.TestCase):
    """Tests the ZobristHasher class."""

    def test_polyglot_hashing(self):
        hasher = chess.ZobristHasher()

        pos = chess.Position()
        self.assertEqual(hasher.hash_position(pos), 0x463b96181691fc9c)

        pos = chess.Position("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        self.assertEqual(hasher.hash_position(pos), 0x823c9b50fd114196)

        pos = chess.Position("rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2")
        self.assertEqual(hasher.hash_position(pos), 0x0756b94461c50fb0)
