#!/usr/bin/python

import chess
import chess.syzygy
import unittest

class SyzygyTestCase(unittest.TestCase):
    def test_material_key(self):
        # Only pawns and kings.
        board = chess.Bitboard("4k3/8/3p4/1P2p3/2P2p2/3P4/8/4K3 w - - 0 1")
        self.assertEqual(hex(chess.syzygy.calc_key(board)), hex(12659189409839370109))

        board = chess.Bitboard("8/8/8/5N2/4BK2/2k5/3p4/8 w - - 0 1")
        self.assertEqual(chess.syzygy.calc_key(board), 13105269394936216443)

if __name__ == "__main__":
    unittest.main()
