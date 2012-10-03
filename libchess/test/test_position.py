import libchess
import unittest

class PositionTestCase(unittest.TestCase):
    """Tests the position class."""

    def test_default_position(self):
        """Tests the default position."""
        pos = libchess.Position.get_default()
        self.assertEqual(pos.get(libchess.Square.from_name('b1')), libchess.Piece.from_symbol('N'))
        self.assertEqual(pos.get_fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(pos.get_turn(), "w")

    def test_scholars_mate(self):
        """Tests the scholars mate."""
        pos = libchess.Position.get_default()

        e4 = libchess.Move.from_uci_move('e2e4')
        self.assertTrue(e4 in pos.get_legal_moves())
        pos.make_move(e4)

        e5 = libchess.Move.from_uci_move('e7e5')
        self.assertTrue(e5 in pos.get_legal_moves())
        self.assertFalse(e4 in pos.get_legal_moves())
        pos.make_move(e5)

        Qf3 = libchess.Move.from_uci_move('d1f3')
        self.assertTrue(Qf3 in pos.get_legal_moves())
        pos.make_move(Qf3)

        Nc6 = libchess.Move.from_uci_move('b8c6')
        self.assertTrue(Nc6 in pos.get_legal_moves())
        pos.make_move(Nc6)

        Bc4 = libchess.Move.from_uci_move('f1c4')
        self.assertTrue(Bc4 in pos.get_legal_moves())
        pos.make_move(Bc4)

        Rb8 = libchess.Move.from_uci_move('a8b8')
        self.assertTrue(Rb8 in pos.get_legal_moves())
        pos.make_move(Rb8)

        self.assertFalse(pos.is_check())
        self.assertFalse(pos.is_checkmate())
        self.assertFalse(pos.is_game_over())
        self.assertFalse(pos.is_stalemate())

        Qf7_mate = libchess.Move.from_uci_move('f3f7')
        self.assertTrue(Qf7_mate in pos.get_legal_moves())
        pos.make_move(Qf7_mate)

        self.assertTrue(pos.is_check())
        self.assertTrue(pos.is_checkmate())
        self.assertTrue(pos.is_game_over())
        self.assertFalse(pos.is_stalemate())

        self.assertEqual(pos.get_fen(), '1rbqkbnr/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4')
