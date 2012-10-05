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

        e4 = libchess.Move.from_uci('e2e4')
        self.assertTrue(e4 in pos.get_legal_moves())
        pos.make_move(e4)

        e5 = libchess.Move.from_uci('e7e5')
        self.assertTrue(e5 in pos.get_legal_moves())
        self.assertFalse(e4 in pos.get_legal_moves())
        pos.make_move(e5)

        Qf3 = libchess.Move.from_uci('d1f3')
        self.assertTrue(Qf3 in pos.get_legal_moves())
        pos.make_move(Qf3)

        Nc6 = libchess.Move.from_uci('b8c6')
        self.assertTrue(Nc6 in pos.get_legal_moves())
        pos.make_move(Nc6)

        Bc4 = libchess.Move.from_uci('f1c4')
        self.assertTrue(Bc4 in pos.get_legal_moves())
        pos.make_move(Bc4)

        Rb8 = libchess.Move.from_uci('a8b8')
        self.assertTrue(Rb8 in pos.get_legal_moves())
        pos.make_move(Rb8)

        self.assertFalse(pos.is_check())
        self.assertFalse(pos.is_checkmate())
        self.assertFalse(pos.is_game_over())
        self.assertFalse(pos.is_stalemate())

        Qf7_mate = libchess.Move.from_uci('f3f7')
        self.assertTrue(Qf7_mate in pos.get_legal_moves())
        pos.make_move(Qf7_mate)

        self.assertTrue(pos.is_check())
        self.assertTrue(pos.is_checkmate())
        self.assertTrue(pos.is_game_over())
        self.assertFalse(pos.is_stalemate())

        self.assertEqual(pos.get_fen(), '1rbqkbnr/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4')

    def test_move_info(self):
        """Tests move info generation."""
        pos = libchess.Position.get_default()
        e4 = pos.get_move_info(libchess.Move.from_uci('e2e4'))
        self.assertEqual(e4.get_san(), 'e4')
        self.assertFalse(e4.is_check())
        self.assertFalse(e4.is_checkmate())
        self.assertFalse(e4.is_castle())

    def test_single_step_pawn_move(self):
        """Tests that single step pawn moves are possible."""
        pos = libchess.Position.get_default()
        a3 = libchess.Move.from_uci('a2a3')
        self.assertTrue(a3 in pos.get_pseudo_legal_moves())
        self.assertTrue(a3 in pos.get_legal_moves())
        pos.get_move_info(a3)
        pos.make_move(a3)

    def test_get_set(self):
        """Tests the get and set methods."""
        pos = libchess.Position.get_default()
        self.assertEqual(pos.get(libchess.Square.from_name('b1')), libchess.Piece.from_symbol('N'))

        pos.set(libchess.Square.from_name('e2'), None)
        self.assertEqual(pos.get(libchess.Square.from_name('e2')), None)

        pos.set(libchess.Square.from_name('e4'), libchess.Piece.from_symbol('r'))
        self.assertEqual(pos.get(libchess.Square.from_name('e4')), libchess.Piece.from_symbol('r'))
