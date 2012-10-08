import chess
import unittest

class PgnFileTestCase(unittest.TestCase):
    def test(self):
        games = chess.PgnFile.open('data/games/kasparov-deep-blue-1997.pgn')
        self.assertEqual(len(games), 6)

        first_game = games[0]
        self.assertEqual(first_game.get_header("Event"), "IBM Man-Machine, New York USA")
        self.assertEqual(first_game.get_header("Site"), "01")
        self.assertEqual(first_game.get_header("Date"), "1997.??.??")
        self.assertEqual(first_game.get_header("EventDate"), "?")
        self.assertEqual(first_game.get_header("Round"), "?")
        self.assertEqual(first_game.get_header("Result"), "1-0")
        self.assertEqual(first_game.get_header("White"), "Garry Kasparov")
        self.assertEqual(first_game.get_header("Black"), "Deep Blue (Computer)")
        self.assertEqual(first_game.get_header("ECO"), "A06")
