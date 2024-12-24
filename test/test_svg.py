import unittest

import chess
import chess.svg

class SvgTestCase(unittest.TestCase):

    def test_svg_board(self):
        svg = chess.BaseBoard("4k3/8/8/8/8/8/8/4KB2")._repr_svg_()
        self.assertIn("white bishop", svg)
        self.assertNotIn("black queen", svg)

    def test_svg_arrows(self):
        svg = chess.svg.board(arrows=[(chess.A1, chess.A1)])
        self.assertIn("<circle", svg)
        self.assertNotIn("<line", svg)

        svg = chess.svg.board(arrows=[chess.svg.Arrow(chess.A1, chess.H8)])
        self.assertNotIn("<circle", svg)
        self.assertIn("<line", svg)

    def test_svg_piece(self):
        svg = chess.svg.piece(chess.Piece.from_symbol("K"))
        self.assertIn("id=\"white-king\"", svg)


