import chess
import unittest

class PositionTestCase(unittest.TestCase):
    """Tests the position class."""

    def test_default_position(self):
        """Tests the default position."""
        pos = chess.Position()
        self.assertEqual(pos.get(chess.Square('b1')), chess.Piece('N'))
        self.assertEqual(pos.get_fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(pos.get_turn(), "w")

    def test_scholars_mate(self):
        """Tests the scholars mate."""
        pos = chess.Position()

        e4 = chess.Move.from_uci('e2e4')
        self.assertTrue(e4 in pos.get_legal_moves())
        pos.make_move(e4)

        e5 = chess.Move.from_uci('e7e5')
        self.assertTrue(e5 in pos.get_legal_moves())
        self.assertFalse(e4 in pos.get_legal_moves())
        pos.make_move(e5)

        Qf3 = chess.Move.from_uci('d1f3')
        self.assertTrue(Qf3 in pos.get_legal_moves())
        pos.make_move(Qf3)

        Nc6 = chess.Move.from_uci('b8c6')
        self.assertTrue(Nc6 in pos.get_legal_moves())
        pos.make_move(Nc6)

        Bc4 = chess.Move.from_uci('f1c4')
        self.assertTrue(Bc4 in pos.get_legal_moves())
        pos.make_move(Bc4)

        Rb8 = chess.Move.from_uci('a8b8')
        self.assertTrue(Rb8 in pos.get_legal_moves())
        pos.make_move(Rb8)

        self.assertFalse(pos.is_check())
        self.assertFalse(pos.is_checkmate())
        self.assertFalse(pos.is_game_over())
        self.assertFalse(pos.is_stalemate())

        Qf7_mate = chess.Move.from_uci('f3f7')
        self.assertTrue(Qf7_mate in pos.get_legal_moves())
        pos.make_move(Qf7_mate)

        self.assertTrue(pos.is_check())
        self.assertTrue(pos.is_checkmate())
        self.assertTrue(pos.is_game_over())
        self.assertFalse(pos.is_stalemate())

        self.assertEqual(pos.get_fen(), '1rbqkbnr/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4')

    def test_move_info(self):
        """Tests move info generation."""
        pos = chess.Position()
        e4 = pos.get_move_info(chess.Move.from_uci('e2e4'))
        self.assertEqual(e4.get_san(), 'e4')
        self.assertFalse(e4.is_check())
        self.assertFalse(e4.is_checkmate())
        self.assertFalse(e4.is_castle())

    def test_single_step_pawn_move(self):
        """Tests that single step pawn moves are possible."""
        pos = chess.Position()
        a3 = chess.Move.from_uci('a2a3')
        self.assertTrue(a3 in pos.get_pseudo_legal_moves())
        self.assertTrue(a3 in pos.get_legal_moves())
        pos.get_move_info(a3)
        pos.make_move(a3)

    def test_get_set(self):
        """Tests the get and set methods."""
        pos = chess.Position()
        self.assertEqual(pos.get(chess.Square("b1")), chess.Piece("N"))

        pos.set(chess.Square("e2"), None)
        self.assertEqual(pos.get(chess.Square("e2")), None)

        pos.set(chess.Square("e4"), chess.Piece("r"))
        self.assertEqual(pos.get(chess.Square("e4")), chess.Piece("r"))

    def test_san_moves(self):
        """Tests making moves from SANs."""
        pos = chess.Position()

        pos.make_move(pos.get_move_from_san('Nc3'))
        pos.make_move(pos.get_move_from_san('c5'))

        pos.make_move(pos.get_move_from_san('e4'))
        pos.make_move(pos.get_move_from_san('g6'))

        pos.make_move(pos.get_move_from_san('Nge2'))
        pos.make_move(pos.get_move_from_san('Bg7'))

        pos.make_move(pos.get_move_from_san('d3'))
        pos.make_move(pos.get_move_from_san('Bxc3'))

        pos.make_move(pos.get_move_from_san('bxc3'))

        self.assertEqual(pos.get_fen(), 'rnbqk1nr/pp1ppp1p/6p1/2p5/4P3/2PP4/P1P1NPPP/R1BQKB1R b KQkq - 0 5')
