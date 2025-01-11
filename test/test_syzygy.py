import unittest

import chess
import chess.gaviota
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant

from .helpers import catchAndSkip

class SyzygyTestCase(unittest.TestCase):

    def test_calc_key(self):
        board = chess.Board("8/8/8/5N2/5K2/2kB4/8/8 b - - 0 1")
        key_from_board = chess.syzygy.calc_key(board)
        key_from_filename = chess.syzygy.normalize_tablename("KBNvK")
        self.assertEqual(key_from_board, key_from_filename)

    def test_tablenames(self):
        self.assertIn("KPPvKN", chess.syzygy.tablenames())
        self.assertIn("KNNPvKN", chess.syzygy.tablenames())
        self.assertIn("KQRNvKR", chess.syzygy.tablenames())
        self.assertIn("KRRRvKR", chess.syzygy.tablenames())
        self.assertIn("KRRvKRR", chess.syzygy.tablenames())
        self.assertIn("KRNvKRP", chess.syzygy.tablenames())
        self.assertIn("KRPvKP", chess.syzygy.tablenames())

    def test_suicide_tablenames(self):
        # Test the number of 6-piece tables.
        self.assertEqual(sum(1 for eg in chess.syzygy.tablenames(one_king=False) if len(eg) == 7), 5754)

    def test_normalize_tablename(self):
        names = set(chess.syzygy.tablenames())
        for name in names:
            self.assertTrue(
                chess.syzygy.normalize_tablename(name) in names,
                f"Already normalized {name}")

            w, b = name.split("v", 1)
            swapped = b + "v" + w
            self.assertTrue(
                chess.syzygy.normalize_tablename(swapped) in names,
                f"Normalized {swapped}")

    def test_normalize_nnvbb(self):
        self.assertEqual(chess.syzygy.normalize_tablename("KNNvKBB"), "KBBvKNN")

    def test_dependencies(self):
        self.assertEqual(set(chess.syzygy.dependencies("KBNvK")), set(["KBvK", "KNvK"]))

    def test_get_wdl_get_dtz(self):
        with chess.syzygy.Tablebase() as tables:
            board = chess.Board()
            self.assertEqual(tables.get_dtz(board, tables.get_wdl(board)), None)

    def test_probe_pawnless_wdl_table(self):
        wdl = chess.syzygy.WdlTable("data/syzygy/regular/KBNvK.rtbw")
        wdl.init_table_wdl()

        board = chess.Board("8/8/8/5N2/5K2/2kB4/8/8 b - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), -2)

        board = chess.Board("7B/5kNK/8/8/8/8/8/8 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        board = chess.Board("N7/8/2k5/8/7K/8/8/B7 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        board = chess.Board("8/8/1NkB4/8/7K/8/8/8 w - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 0)

        board = chess.Board("8/8/8/2n5/2b1K3/2k5/8/8 w - - 0 1")
        self.assertEqual(wdl.probe_wdl_table(board), -2)

        wdl.close()

    def test_probe_wdl_table(self):
        wdl = chess.syzygy.WdlTable("data/syzygy/regular/KRvKP.rtbw")
        wdl.init_table_wdl()

        board = chess.Board("8/8/2K5/4P3/8/8/8/3r3k b - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 0)

        board = chess.Board("8/8/2K5/8/4P3/8/8/3r3k b - - 1 1")
        self.assertEqual(wdl.probe_wdl_table(board), 2)

        wdl.close()

    def test_probe_dtz_table_piece(self):
        dtz = chess.syzygy.DtzTable("data/syzygy/regular/KRvKN.rtbz")
        dtz.init_table_dtz()

        # Pawnless position with white to move.
        board = chess.Board("7n/6k1/4R3/4K3/8/8/8/8 w - - 0 1")
        self.assertEqual(dtz.probe_dtz_table(board, 2), (0, -1))

        # Same position with black to move.
        board = chess.Board("7n/6k1/4R3/4K3/8/8/8/8 b - - 1 1")
        self.assertEqual(dtz.probe_dtz_table(board, -2), (8, 1))

        dtz.close()

    def test_probe_dtz_table_pawn(self):
        dtz = chess.syzygy.DtzTable("data/syzygy/regular/KNvKP.rtbz")
        dtz.init_table_dtz()

        board = chess.Board("8/1K6/1P6/8/8/8/6n1/7k w - - 0 1")
        self.assertEqual(dtz.probe_dtz_table(board, 2), (2, 1))

        dtz.close()

    def test_probe_wdl_tablebase(self):
        with chess.syzygy.Tablebase(max_fds=2) as tables:
            self.assertGreaterEqual(tables.add_directory("data/syzygy/regular"), 70)

            # Winning KRvKB.
            board = chess.Board("7k/6b1/6K1/8/8/8/8/3R4 b - - 12 7")
            self.assertEqual(tables.probe_wdl_table(board), -2)

            # Drawn KBBvK.
            board = chess.Board("7k/8/8/4K3/3B4/4B3/8/8 b - - 12 7")
            self.assertEqual(tables.probe_wdl_table(board), 0)

            # Winning KBBvK.
            board = chess.Board("7k/8/8/4K2B/8/4B3/8/8 w - - 12 7")
            self.assertEqual(tables.probe_wdl_table(board), 2)

    def test_wdl_ep(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables:
            # Winning KPvKP because of en passant.
            board = chess.Board("8/8/8/k2Pp3/8/8/8/4K3 w - e6 0 2")

            # If there was no en passant, this would be a draw.
            self.assertEqual(tables.probe_wdl_table(board), 0)

            # But it is a win.
            self.assertEqual(tables.probe_wdl(board), 2)

    def test_dtz_ep(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables:
            board = chess.Board("8/8/8/8/2pP4/2K5/4k3/8 b - d3 0 1")
            self.assertEqual(tables.probe_dtz_no_ep(board), -1)
            self.assertEqual(tables.probe_dtz(board), 1)

    def test_testsuite(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables, open("data/endgame.epd") as epds:
            board = chess.Board()

            for line, epd in enumerate(epds):
                extra = board.set_epd(epd)

                wdl_table = tables.probe_wdl_table(board)
                self.assertEqual(
                    wdl_table, extra["wdl_table"],
                    f"Expecting wdl_table {extra['wdl_table']} for {board.fen()}, got {wdl_table} (at line {line + 1})")

                wdl = tables.probe_wdl(board)
                self.assertEqual(
                    wdl, extra["wdl"],
                    f"Expecting wdl {extra['wdl']} for {board.fen()}, got {wdl} (at line {line + 1})")

                dtz = tables.probe_dtz(board)
                self.assertEqual(
                    dtz, extra["dtz"],
                    f"Expecting dtz {extra['dtz']} for {board.fen()}, got {dtz} (at line {line + 1})")

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_stockfish_dtz_bug(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables:
            board = chess.Board("3K4/8/3k4/8/4p3/4B3/5P2/8 w - - 0 5")
            self.assertEqual(tables.probe_dtz(board), 15)

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_issue_93(self):
        with chess.syzygy.open_tablebase("data/syzygy/regular") as tables:
            board = chess.Board("4r1K1/6PP/3k4/8/8/8/8/8 w - - 1 64")
            self.assertEqual(tables.probe_wdl(board), 2)
            self.assertEqual(tables.probe_dtz(board), 4)

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_suicide_dtm(self):
        with chess.syzygy.open_tablebase("data/syzygy/suicide", VariantBoard=chess.variant.SuicideBoard) as tables, open("data/suicide-dtm.epd") as epds:
            for epd in epds:
                epd = epd.strip()

                board, solution = chess.variant.SuicideBoard.from_epd(epd)

                wdl = tables.probe_wdl(board)

                expected_wdl = ((solution["max_dtm"] > 0) - (solution["max_dtm"] < 0)) * 2
                self.assertEqual(wdl, expected_wdl, f"Expecting wdl {expected_wdl}, got {wdl} (in {epd})")

                dtz = tables.probe_dtz(board)

                if wdl > 0:
                    self.assertGreaterEqual(dtz, chess.syzygy.dtz_before_zeroing(wdl))
                    self.assertLessEqual(dtz, 2 * solution["max_dtm"])
                elif wdl == 0:
                    self.assertEqual(dtz, 0)
                else:
                    self.assertLessEqual(dtz, chess.syzygy.dtz_before_zeroing(wdl))
                    self.assertGreaterEqual(dtz, 2 * solution["max_dtm"])

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_suicide_dtz(self):
        with chess.syzygy.open_tablebase("data/syzygy/suicide", VariantBoard=chess.variant.SuicideBoard) as tables, open("data/suicide-dtz.epd") as epds:
            for epd in epds:
                epd = epd.strip()
                if epd.startswith("%") or epd.startswith("#"):
                    continue

                board, solution = chess.variant.SuicideBoard.from_epd(epd)

                dtz = tables.probe_dtz(board)
                self.assertEqual(dtz, solution["dtz"], f"Expecting dtz {solution['dtz']}, got {dtz} (in {epd})")

    @catchAndSkip(chess.syzygy.MissingTableError)
    def test_suicide_stats(self):
        board = chess.variant.SuicideBoard()

        with chess.syzygy.open_tablebase("data/syzygy/suicide", VariantBoard=type(board)) as tables, open("data/suicide-stats.epd") as epds:
            for l, epd in enumerate(epds):
                solution = board.set_epd(epd)

                dtz = tables.probe_dtz(board)
                self.assertAlmostEqual(dtz, solution["dtz"], delta=1,
                                       msg=f"Expected dtz {solution['dtz']}, got {dtz} (in l. {l + 1}, fen: {board.fen()})")

    def test_antichess_kvk(self):
        kvk = chess.variant.AntichessBoard("4k3/8/8/8/8/8/8/4K3 w - - 0 1")

        tables = chess.syzygy.Tablebase()
        with self.assertRaises(KeyError):
            tables.probe_dtz(kvk)

        tables = chess.syzygy.Tablebase(VariantBoard=chess.variant.AntichessBoard)
        with self.assertRaises(chess.syzygy.MissingTableError):
            tables.probe_dtz(kvk)


