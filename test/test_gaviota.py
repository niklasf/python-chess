import platform
import unittest

import chess
import chess.gaviota
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant

def catchAndSkip(signature, message=None):
    def _decorator(f):
        def _wrapper(self):
            try:
                return f(self)
            except signature as err:
                raise unittest.SkipTest(message or err)
        return _wrapper
    return _decorator


class NativeGaviotaTestCase(unittest.TestCase):

    @unittest.skipUnless(platform.python_implementation() == "CPython", "need CPython for native Gaviota")
    @catchAndSkip((OSError, RuntimeError), "need libgtb")
    def setUp(self):
        self.tablebase = chess.gaviota.open_tablebase_native("data/gaviota")

    def tearDown(self):
        self.tablebase.close()

    def test_native_probe_dtm(self):
        board = chess.Board("6K1/8/8/8/4Q3/8/6k1/8 b - - 0 1")
        self.assertEqual(self.tablebase.probe_dtm(board), -14)

        board = chess.Board("8/3K4/8/8/8/4r3/4k3/8 b - - 0 1")
        self.assertEqual(self.tablebase.get_dtm(board), 21)

    def test_native_probe_wdl(self):
        board = chess.Board("8/8/4K3/2n5/8/3k4/8/8 w - - 0 1")
        self.assertEqual(self.tablebase.probe_wdl(board), 0)

        board = chess.Board("8/8/1p2K3/8/8/3k4/8/8 b - - 0 1")
        self.assertEqual(self.tablebase.get_wdl(board), 1)

    @catchAndSkip(chess.gaviota.MissingTableError, "need KPPvKP.gtb.cp4")
    def test_two_ep(self):
        board = chess.Board("8/8/8/8/5pPp/8/5K1k/8 b - g3 0 61")
        self.assertEqual(self.tablebase.probe_dtm(board), 19)


class GaviotaTestCase(unittest.TestCase):

    @catchAndSkip(ImportError)
    def setUp(self):
        self.tablebase = chess.gaviota.open_tablebase("data/gaviota", LibraryLoader=None)

    def tearDown(self):
        self.tablebase.close()

    @catchAndSkip(chess.gaviota.MissingTableError)
    def test_dm_4(self):
        with open("data/endgame-dm-4.epd") as epds:
            for line, epd in enumerate(epds):
                # Skip empty lines and comments.
                epd = epd.strip()
                if not epd or epd.startswith("#"):
                    continue

                # Parse EPD.
                board, extra = chess.Board.from_epd(epd)

                # Check DTM.
                if extra["dm"] > 0:
                    expected = extra["dm"] * 2 - 1
                else:
                    expected = extra["dm"] * 2
                dtm = self.tablebase.probe_dtm(board)
                self.assertEqual(dtm, expected, f"Expecting dtm {expected} for {board.fen()}, got {dtm} (at line {line + 1})")

    @catchAndSkip(chess.gaviota.MissingTableError)
    def test_dm_5(self):
        with open("data/endgame-dm-5.epd") as epds:
            for line, epd in enumerate(epds):
                # Skip empty lines and comments.
                epd = epd.strip()
                if not epd or epd.startswith("#"):
                    continue

                # Parse EPD.
                board, extra = chess.Board.from_epd(epd)

                # Check DTM.
                if extra["dm"] > 0:
                    expected = extra["dm"] * 2 - 1
                else:
                    expected = extra["dm"] * 2
                dtm = self.tablebase.probe_dtm(board)
                self.assertEqual(dtm, expected, f"Expecting dtm {expected} for {board.fen()}, got {dtm} (at line {line + 1})")

    def test_wdl(self):
        board = chess.Board("8/8/4K3/2n5/8/3k4/8/8 w - - 0 1")
        self.assertEqual(self.tablebase.probe_wdl(board), 0)

        board = chess.Board("8/8/1p2K3/8/8/3k4/8/8 b - - 0 1")
        self.assertEqual(self.tablebase.probe_wdl(board), 1)

    def test_context_manager(self):
        self.assertTrue(self.tablebase.available_tables)

        with self.tablebase:
            pass

        self.assertFalse(self.tablebase.available_tables)

    @catchAndSkip(chess.gaviota.MissingTableError, "need KPPvKP.gtb.cp4")
    def test_two_ep(self):
        board = chess.Board("8/8/8/8/5pPp/8/5K1k/8 b - g3 0 61")
        self.assertEqual(self.tablebase.probe_dtm(board), 19)

        board = chess.Board("K7/8/8/6k1/5pPp/8/8/8 b - g3 0 61")
        self.assertEqual(self.tablebase.probe_dtm(board), 17)


