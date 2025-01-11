import unittest

import os

import chess
import chess.gaviota
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant


class PolyglotTestCase(unittest.TestCase):

    def test_performance_bin(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            pos = chess.Board()

            e4 = next(book.find_all(pos))
            self.assertEqual(e4.move, pos.parse_san("e4"))
            pos.push(e4.move)

            e5 = next(book.find_all(pos))
            self.assertEqual(e5.move, pos.parse_san("e5"))
            pos.push(e5.move)

    def test_mainline(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            board = chess.Board()

            while True:
                entry = book.get(board)
                if entry is None:
                    break

                board.push(entry.move)

            self.assertEqual(board.fen(), "r2q1rk1/4bppp/p2p1n2/np5b/3BP1P1/5N1P/PPB2P2/RN1QR1K1 b - - 0 15")

    def test_lasker_trap(self):
        with chess.polyglot.open_reader("data/polyglot/lasker-trap.bin") as book:
            board = chess.Board("rnbqk1nr/ppp2ppp/8/4P3/1BP5/8/PP2KpPP/RN1Q1BNR b kq - 1 7")
            entry = book.find(board)
            cute_underpromotion = entry.move
            self.assertEqual(cute_underpromotion, board.parse_san("fxg1=N+"))

    def test_castling(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            # White decides between short castling and long castling at this
            # turning point in the Queen's Gambit Declined, Exchange Variation.
            pos = chess.Board("r1bqr1k1/pp1nbppp/2p2n2/3p2B1/3P4/2NBP3/PPQ1NPPP/R3K2R w KQ - 5 10")
            moves = set(entry.move for entry in book.find_all(pos))
            self.assertIn(pos.parse_san("O-O"), moves)
            self.assertIn(pos.parse_san("O-O-O"), moves)
            self.assertIn(pos.parse_san("h3"), moves)
            self.assertEqual(len(moves), 3)

            # Black usually castles long at this point in the Ruy Lopez,
            # Exchange Variation.
            pos = chess.Board("r3k1nr/1pp1q1pp/p1pb1p2/4p3/3PP1b1/2P1BN2/PP1N1PPP/R2Q1RK1 b kq - 4 9")
            moves = set(entry.move for entry in book.find_all(pos))
            self.assertIn(pos.parse_san("O-O-O"), moves)
            self.assertEqual(len(moves), 1)

            # Not a castling move.
            pos = chess.Board("1r1qr1k1/1b2bp1n/p2p2pB/1pnPp2p/P1p1P3/R1P2NNP/1PBQ1PP1/4R1K1 w - - 0 1")
            entry = book.find(pos)
            self.assertEqual(entry.move, chess.Move.from_uci("e1a1"))

    def test_empty_book(self):
        with chess.polyglot.open_reader(os.devnull) as book:
            self.assertEqual(len(book), 0)

            entries = book.find_all(chess.Board())
            self.assertEqual(len(list(entries)), 0)

    def test_reversed(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            # Last is first of reversed.
            self.assertEqual(book[-1], next(reversed(book)))

            # First is last of reversed.
            for last in reversed(book):
                pass
            self.assertEqual(book[0], last)

    def test_random_choice(self):
        class FirstMockRandom:
            @staticmethod
            def randint(first, last):
                assert first <= last
                return first

        class LastMockRandom:
            @staticmethod
            def randint(first, last):
                assert first <= last
                return last

        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            # Uniform choice.
            entry = book.choice(chess.Board(), random=FirstMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("e2e4"))

            entry = book.choice(chess.Board(), random=LastMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("c2c4"))

            # Weighted choice.
            entry = book.weighted_choice(chess.Board(), random=FirstMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("e2e4"))

            entry = book.weighted_choice(chess.Board(), random=LastMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("c2c4"))

            # Weighted choice with excluded move.
            entry = book.weighted_choice(chess.Board(), exclude_moves=[chess.Move.from_uci("e2e4")], random=FirstMockRandom())
            self.assertEqual(entry.move, chess.Move.from_uci("d2d4"))

    def test_find(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            entry = book.find(chess.Board())
            self.assertEqual(entry.move, chess.Move.from_uci("e2e4"))

    def test_exclude_moves(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            entry = book.find(chess.Board(), exclude_moves=[chess.Move.from_uci("e2e4")])
            self.assertEqual(entry.move, chess.Move.from_uci("d2d4"))

    def test_contains(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            for entry in book:
                self.assertIn(entry, book)

    def test_last(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            last_entry = book[len(book) - 1]
            self.assertTrue(any(book.find_all(last_entry.key)))
            self.assertTrue(all(book.find_all(last_entry.key)))

    def test_minimum_weight(self):
        with chess.polyglot.open_reader("data/polyglot/performance.bin") as book:
            with self.assertRaises(IndexError):
                book.find(chess.Board(), minimum_weight=2)


