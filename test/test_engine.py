import asyncio
import logging
import sys
import tempfile
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

@unittest.skipIf(sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 8, 1), "https://bugs.python.org/issue34679")
class EngineTestCase(unittest.TestCase):
    def test_uci_option_map_equality(self):
        a = chess.engine.UciOptionMap()
        b = chess.engine.UciOptionMap()
        c = chess.engine.UciOptionMap()
        self.assertEqual(a, b)

        a["fOO"] = "bAr"
        b["foo"] = "bAr"
        c["fOo"] = "bar"
        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertNotEqual(a, c)
        self.assertNotEqual(c, a)
        self.assertNotEqual(b, c)

        b["hello"] = "world"
        self.assertNotEqual(a, b)
        self.assertNotEqual(b, a)

    def test_uci_option_map_len(self):
        a = chess.engine.UciOptionMap()
        self.assertEqual(len(a), 0)

        a["key"] = "value"
        self.assertEqual(len(a), 1)

        del a["key"]
        self.assertEqual(len(a), 0)

    def test_score_ordering(self):
        order = [
            chess.engine.Mate(-0),
            chess.engine.Mate(-1),
            chess.engine.Mate(-99),
            chess.engine.Cp(-123),
            chess.engine.Cp(-50),
            chess.engine.Cp(0),
            chess.engine.Cp(+30),
            chess.engine.Cp(+800),
            chess.engine.Mate(+77),
            chess.engine.Mate(+1),
            chess.engine.MateGiven,
        ]

        for i, a in enumerate(order):
            for j, b in enumerate(order):
                self.assertEqual(i < j, a < b, f"{a!r} < {b!r}")
                self.assertEqual(i == j, a == b, f"{a!r} == {b!r}")
                self.assertEqual(i <= j, a <= b)
                self.assertEqual(i != j, a != b)
                self.assertEqual(i > j, a > b)
                self.assertEqual(i >= j, a >= b)
                self.assertEqual(i < j, a.score(mate_score=100000) < b.score(mate_score=100000))

                for model in ["sf12", "sf14", "sf15", "sf15.1", "sf16", "sf16.1"]:
                    self.assertTrue(not (i < j) or a.wdl(model=model).expectation() <= b.wdl(model=model).expectation())
                    self.assertTrue(not (i < j) or a.wdl(model=model).winning_chance() <= b.wdl(model=model).winning_chance())
                    self.assertTrue(not (i < j) or a.wdl(model=model).losing_chance() >= b.wdl(model=model).losing_chance())

    def test_score(self):
        # Negation.
        self.assertEqual(-chess.engine.Cp(+20), chess.engine.Cp(-20))
        self.assertEqual(-chess.engine.Mate(+4), chess.engine.Mate(-4))
        self.assertEqual(-chess.engine.Mate(-0), chess.engine.MateGiven)
        self.assertEqual(-chess.engine.MateGiven, chess.engine.Mate(-0))

        # Score.
        self.assertEqual(chess.engine.Cp(-300).score(), -300)
        self.assertEqual(chess.engine.Mate(+5).score(), None)
        self.assertEqual(chess.engine.Mate(+5).score(mate_score=100000), 99995)
        self.assertEqual(chess.engine.Mate(-7).score(mate_score=100000), -99993)

        # Mate.
        self.assertEqual(chess.engine.Cp(-300).mate(), None)
        self.assertEqual(chess.engine.Mate(+5).mate(), 5)

        # Wdl.
        self.assertEqual(chess.engine.MateGiven.wdl().expectation(), 1)
        self.assertEqual(chess.engine.Mate(0).wdl().expectation(), 0)
        self.assertEqual(chess.engine.Cp(0).wdl().expectation(), 0.5)

        for cp in map(chess.engine.Cp, range(-1050, 1100, 50)):
            wdl = cp.wdl()
            self.assertTrue(wdl)
            self.assertAlmostEqual(wdl.winning_chance() + wdl.drawing_chance() + wdl.losing_chance(), 1)

        self.assertFalse(chess.engine.Wdl(0, 0, 0))

    def test_wdl_model(self):
        self.assertEqual(chess.engine.Cp(131).wdl(model="sf12", ply=25), chess.engine.Wdl(524, 467, 9))
        self.assertEqual(chess.engine.Cp(146).wdl(model="sf14", ply=25), chess.engine.Wdl(601, 398, 1))
        self.assertEqual(chess.engine.Cp(40).wdl(model="sf15", ply=25), chess.engine.Wdl(58, 937, 5))
        self.assertEqual(chess.engine.Cp(100).wdl(model="sf15.1", ply=64), chess.engine.Wdl(497, 503, 0))
        self.assertEqual(chess.engine.Cp(-52).wdl(model="sf16", ply=63), chess.engine.Wdl(0, 932, 68))
        self.assertEqual(chess.engine.Cp(51).wdl(model="sf16.1", ply=158), chess.engine.Wdl(36, 964, 0))

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_forced_mates(self):
        with chess.engine.SimpleEngine.popen_uci("stockfish", debug=True) as engine:
            epds = [
                "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";",
                "6k1/N1p3pp/2p5/3n1P2/4K3/1P5P/P1Pr1r2/R1R5 b - - bm Rf4+; id \"Clausthal 2014\";",
            ]

            board = chess.Board()

            for epd in epds:
                operations = board.set_epd(epd)
                result = engine.play(board, chess.engine.Limit(mate=5), game=object())
                self.assertIn(result.move, operations["bm"], operations["id"])

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_options(self):
        with chess.engine.SimpleEngine.popen_uci("stockfish", debug=True) as engine:
            self.assertEqual(engine.options["UCI_Chess960"].name, "UCI_Chess960")
            self.assertEqual(engine.options["uci_Chess960"].type, "check")
            self.assertEqual(engine.options["UCI_CHESS960"].default, False)

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_analysis(self):
        with chess.engine.SimpleEngine.popen_uci("stockfish", setpgrp=True, debug=True) as engine:
            board = chess.Board("8/6K1/1p1B1RB1/8/2Q5/2n1kP1N/3b4/4n3 w - - 0 1")
            limit = chess.engine.Limit(depth=40)
            analysis = engine.analysis(board, limit)
            with analysis:
                for info in iter(analysis.next, None):
                    if "score" in info and info["score"].is_mate():
                        break
                else:
                    self.fail("never found a mate score")

                for info in analysis:
                    if "score" in info and info["score"].white() >= chess.engine.Mate(+2):
                        break

            analysis.wait()
            self.assertFalse(analysis.would_block())

            self.assertEqual(analysis.info["score"].relative, chess.engine.Mate(+2))
            self.assertEqual(analysis.multipv[0]["score"].black(), chess.engine.Mate(-2))

            # Exhaust remaining information.
            was_empty = analysis.empty()
            was_really_empty = True
            for info in analysis:
                was_really_empty = False
            self.assertEqual(was_really_empty, was_empty)
            self.assertTrue(analysis.empty())
            self.assertFalse(analysis.would_block())
            for info in analysis:
                self.fail("all info should have been consumed")

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_multipv(self):
        with chess.engine.SimpleEngine.popen_uci("stockfish", debug=True) as engine:
            board = chess.Board("r2qr1k1/pb2npp1/1pn1p2p/8/3P4/P1PQ1N2/B4PPP/R1B1R1K1 w - - 2 15")
            result = engine.analyse(board, chess.engine.Limit(depth=1), multipv=3)
            self.assertEqual(len(result), 3)
            self.assertTrue(result[0]["score"].relative >= result[1]["score"].relative)
            self.assertTrue(result[1]["score"].relative >= result[2]["score"].relative)

    @catchAndSkip(FileNotFoundError, "need stockfish")
    def test_sf_quit(self):
        engine = chess.engine.SimpleEngine.popen_uci("stockfish", setpgrp=True, debug=True)

        with engine:
            engine.quit()

        with self.assertRaises(chess.engine.EngineTerminatedError), engine:
            engine.ping()

    @catchAndSkip(FileNotFoundError, "need fairy-stockfish")
    def test_fairy_sf_initialize(self):
        with chess.engine.SimpleEngine.popen_uci("fairy-stockfish", setpgrp=True, debug=True):
            pass

    def test_uci_option_parse(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("uci", ["option name UCI_Variant type combo default chess var bughouse var chess var mini var minishogi var threekings", "uciok"])
            await protocol.initialize()
            mock.assert_done()

            mock.expect("isready", ["readyok"])
            await protocol.ping()
            mock.assert_done()

        asyncio.run(main())

    @catchAndSkip(FileNotFoundError, "need crafty")
    def test_crafty_play_to_mate(self):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory(prefix="crafty") as tmpdir:
                with chess.engine.SimpleEngine.popen_xboard("crafty", setpgrp=True, debug=True, cwd=tmpdir) as engine:
                    board = chess.Board("2bqkbn1/2pppp2/np2N3/r3P1p1/p2N2B1/5Q2/PPPPKPP1/RNB2r2 w KQkq - 0 1")
                    limit = chess.engine.Limit(depth=10)
                    while not board.is_game_over() and len(board.move_stack) < 5:
                        result = engine.play(board, limit, ponder=True)
                        board.push(result.move)
                    self.assertTrue(board.is_checkmate())
                    engine.quit()
        finally:
            logging.disable(logging.NOTSET)

    @catchAndSkip(FileNotFoundError, "need crafty")
    def test_crafty_analyse(self):
        logging.disable(logging.WARNING)
        try:
            with tempfile.TemporaryDirectory(prefix="crafty") as tmpdir:
                with chess.engine.SimpleEngine.popen_xboard("crafty", debug=True, cwd=tmpdir) as engine:
                    board = chess.Board("2bqkbn1/2pppp2/np2N3/r3P1p1/p2N2B1/5Q2/PPPPKPP1/RNB2r2 w KQkq - 0 1")
                    limit = chess.engine.Limit(depth=7, time=2.0)
                    info = engine.analyse(board, limit)
                    self.assertTrue(info["score"].relative > chess.engine.Cp(1000))
                    engine.quit()
        finally:
            logging.disable(logging.NOTSET)

    @catchAndSkip(FileNotFoundError, "need crafty")
    def test_crafty_ping(self):
        with tempfile.TemporaryDirectory(prefix="crafty") as tmpdir:
            with chess.engine.SimpleEngine.popen_xboard("crafty", debug=True, cwd=tmpdir) as engine:
                engine.ping()
                engine.quit()

    def test_uci_ping(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("uci", ["uciok"])
            await protocol.initialize()
            mock.assert_done()

            mock.expect("isready", ["readyok"])
            await protocol.ping()
            mock.assert_done()

        asyncio.run(main())

    def test_uci_debug(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("debug on", [])
            protocol.debug()
            mock.assert_done()

            mock.expect("debug off", [])
            protocol.debug(False)
            mock.assert_done()

        asyncio.run(main())

    def test_uci_go(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", ["uciok"])
            await protocol.initialize()

            # Pondering.
            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos")
            mock.expect("go movetime 123 searchmoves e2e4 d2d4", ["info string searching ...", "bestmove d2d4 ponder d7d5"])
            mock.expect("position startpos moves d2d4 d7d5")
            mock.expect("go ponder movetime 123")
            board = chess.Board()
            result = await protocol.play(board, chess.engine.Limit(time=0.123),
                                         root_moves=[board.parse_san("e4"), board.parse_san("d4")],
                                         ponder=True,
                                         info=chess.engine.INFO_ALL)
            self.assertEqual(result.move, chess.Move.from_uci("d2d4"))
            self.assertEqual(result.ponder, chess.Move.from_uci("d7d5"))
            self.assertEqual(result.info["string"], "searching ...")
            mock.assert_done()

            mock.expect("stop", ["bestmove c2c4"])

            # Limits.
            mock.expect("position startpos")
            mock.expect("go wtime 1 btime 2 winc 3 binc 4 movestogo 5 depth 6 nodes 7 mate 8 movetime 9", ["bestmove d2d4"])
            limit = chess.engine.Limit(white_clock=0.001, black_clock=0.002,
                                       white_inc=0.003, black_inc=0.004,
                                       remaining_moves=5, depth=6, nodes=7,
                                       mate=8, time=0.009)
            result = await protocol.play(board, limit)
            self.assertEqual(result.move, chess.Move.from_uci("d2d4"))
            self.assertEqual(result.ponder, None)
            mock.assert_done()

        asyncio.run(main())

    def test_iota_log(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", ["uciok"])
            await protocol.initialize()

            # Iota writes invalid \0 character in old version.
            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos moves d2d4")
            mock.expect("go movetime 5000", ["bestmove e7e6\0"])
            board = chess.Board()
            board.push_uci("d2d4")
            with self.assertRaises(chess.engine.EngineError):
                await protocol.play(board, chess.engine.Limit(time=5.0))
            mock.assert_done()

        asyncio.run(main())

    def test_uci_analyse_mode(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", [
                "option name UCI_AnalyseMode type check default false",
                "uciok",
            ])
            await protocol.initialize()

            # Analyse.
            mock.expect("setoption name UCI_AnalyseMode value true")
            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos")
            mock.expect("go infinite")
            mock.expect("stop", ["bestmove e2e4"])
            result = await protocol.analysis(chess.Board())
            self.assertTrue(result.would_block())
            result.stop()
            best = await result.wait()
            self.assertFalse(result.would_block())
            self.assertEqual(best.move, chess.Move.from_uci("e2e4"))
            self.assertTrue(best.ponder is None)
            mock.assert_done()

            # Explicitly disable.
            mock.expect("setoption name UCI_AnalyseMode value false")
            await protocol.configure({"UCI_AnalyseMode": False})
            mock.assert_done()

            # Analyse again.
            mock.expect("position startpos")
            mock.expect("go infinite")
            mock.expect("stop", ["bestmove e2e4 ponder e7e5"])
            result = await protocol.analysis(chess.Board())
            result.stop()
            best = await result.wait()
            self.assertEqual(best.move, chess.Move.from_uci("e2e4"))
            self.assertEqual(best.ponder, chess.Move.from_uci("e7e5"))
            mock.assert_done()

        asyncio.run(main())

    def test_uci_play_after_analyse(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", ["uciok"])
            await protocol.initialize()

            # Ponder.
            board = chess.Board()
            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos")
            mock.expect("go depth 20", ["bestmove a2a4 ponder a7a5"])
            info = await protocol.analyse(board, chess.engine.Limit(depth=20))
            self.assertEqual(info, {})

            # Play.
            mock.expect("position startpos")
            mock.expect("go movetime 3000", ["bestmove a2a4 ponder a7a5"])
            await protocol.play(board, chess.engine.Limit(time=3))

            mock.assert_done()

        asyncio.run(main())

    def test_uci_ponderhit(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            # Initialize.
            mock.expect("uci", [
                "option name Hash type spin default 16 min 1 max 33554432",
                "option name Ponder type check default false",
                "option name UCI_Opponent type string",
                "uciok",
            ])
            await protocol.initialize()

            primary_opponent = chess.engine.Opponent("Eliza", None, 3500, True)
            await protocol.send_opponent_information(opponent=primary_opponent)

            # First search.
            mock.expect("setoption name Ponder value true")
            mock.expect("ucinewgame")
            mock.expect("setoption name UCI_Opponent value none 3500 computer Eliza")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos")
            mock.expect("go movetime 1000", ["bestmove d2d4 ponder g8f6"])
            mock.expect("position startpos moves d2d4 g8f6")
            mock.expect("go ponder movetime 1000")
            board = chess.Board()
            result = await protocol.play(board, chess.engine.Limit(time=1), ponder=True)
            self.assertEqual(result.move, chess.Move.from_uci("d2d4"))
            self.assertEqual(result.ponder, chess.Move.from_uci("g8f6"))

            # Ponderhit.
            board.push(result.move)
            board.push(result.ponder)
            mock.expect("ponderhit", ["bestmove c2c4 ponder e7e6"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6")
            mock.expect("go ponder movetime 2000")
            result = await protocol.play(board, chess.engine.Limit(time=2), ponder=True)
            self.assertEqual(result.move, chess.Move.from_uci("c2c4"))
            self.assertEqual(result.ponder, chess.Move.from_uci("e7e6"))

            # Ponderhit prevented by changed option.
            board.push(result.move)
            board.push(result.ponder)
            mock.expect("stop", ["bestmove g2g3 ponder f8b4"])
            mock.expect("setoption name Hash value 32")
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6")
            mock.expect("go movetime 3000", ["bestmove b1c3 ponder f8b4"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4")
            mock.expect("go ponder movetime 3000")
            result = await protocol.play(board, chess.engine.Limit(time=3), ponder=True, options={"Hash": 32})
            self.assertEqual(result.move, chess.Move.from_uci("b1c3"))
            self.assertEqual(result.ponder, chess.Move.from_uci("f8b4"))

            # Ponderhit prevented by reverted option.
            board.push(result.move)
            board.push(result.ponder)
            mock.expect("stop", ["bestmove e2e3 ponder e8g8"])
            mock.expect("setoption name Hash value 16")
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4")
            mock.expect("go movetime 3000", ["bestmove d1c2 ponder d7d5"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5")
            mock.expect("go ponder movetime 3000")
            result = await protocol.play(board, chess.engine.Limit(time=3), ponder=True)
            self.assertEqual(result.move, chess.Move.from_uci("d1c2"))
            self.assertEqual(result.ponder, chess.Move.from_uci("d7d5"))

            # Interject analysis.
            board.push(result.move)
            board.push(result.ponder)
            mock.expect("stop", ["bestmove c4d5 ponder e6d5"])
            mock.expect("setoption name Ponder value false")
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5")
            mock.expect("go movetime 4000", ["bestmove c4d5 ponder e6d5"])
            await protocol.analyse(board, chess.engine.Limit(time=4))

            # Interjected analysis prevents ponderhit.
            mock.expect("setoption name Ponder value true")
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5")
            mock.expect("go movetime 5000", ["bestmove c4d5 ponder e6d5"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5")
            mock.expect("go ponder movetime 5000")
            await protocol.play(board, chess.engine.Limit(time=5), ponder=True)

            # Ponderhit prevented by new opponent, which starts a new game.
            board.push(chess.Move.from_uci("c4d5"))
            board.push(chess.Move.from_uci("e6d5"))
            mock.expect("stop", ["bestmove c1g5 ponder h7h6"])
            mock.expect("ucinewgame")
            mock.expect("setoption name UCI_Opponent value GM 3000 human Guy Chapman")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5")
            mock.expect("go movetime 5000", ["bestmove c1g5 ponder h7h6"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5 c1g5 h7h6")
            mock.expect("go ponder movetime 5000")
            opponent = chess.engine.Opponent("Guy Chapman", "GM", 3000, False)
            await protocol.play(board, chess.engine.Limit(time=5), ponder=True, opponent=opponent)

            # Ponderhit prevented by restoration of previous opponent, which again starts a new game.
            board.push(chess.Move.from_uci("c1g5"))
            board.push(chess.Move.from_uci("h7h6"))
            mock.expect("stop", ["bestmove g5h4 ponder b8c6"])
            mock.expect("ucinewgame")
            mock.expect("setoption name UCI_Opponent value none 3500 computer Eliza")
            mock.expect("isready", ["readyok"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5 c1g5 h7h6")
            mock.expect("go movetime 5000", ["bestmove g5h4 ponder b8c6"])
            mock.expect("position startpos moves d2d4 g8f6 c2c4 e7e6 b1c3 f8b4 d1c2 d7d5 c4d5 e6d5 c1g5 h7h6 g5h4 b8c6")
            mock.expect("go ponder movetime 5000")
            await protocol.play(board, chess.engine.Limit(time=5), ponder=True)

            mock.assert_done()

        asyncio.run(main())

    def test_uci_info(self):
        # Info: refutation.
        board = chess.Board("8/8/6k1/8/8/8/1K6/3B4 w - - 0 1")
        info = chess.engine._parse_uci_info("refutation d1h5 g6h5", board)
        self.assertEqual(info["refutation"][chess.Move.from_uci("d1h5")], [chess.Move.from_uci("g6h5")])

        info = chess.engine._parse_uci_info("refutation d1h5", board)
        self.assertEqual(info["refutation"][chess.Move.from_uci("d1h5")], [])

        # Info: string.
        info = chess.engine._parse_uci_info("string goes to end no matter score cp 4 what", board)
        self.assertEqual(info["string"], "goes to end no matter score cp 4 what")

        # Info: currline.
        info = chess.engine._parse_uci_info("currline 0 e2e4 e7e5", chess.Board())
        self.assertEqual(info["currline"][0], [chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")])

        # Info: ebf.
        info = chess.engine._parse_uci_info("ebf 0.42", board)
        self.assertEqual(info["ebf"], 0.42)

        # Info: depth, seldepth, score mate.
        info = chess.engine._parse_uci_info("depth 7 seldepth 8 score mate 3", board)
        self.assertEqual(info["depth"], 7)
        self.assertEqual(info["seldepth"], 8)
        self.assertEqual(info["score"], chess.engine.PovScore(chess.engine.Mate(+3), chess.WHITE))

        # Info: tbhits, cpuload, hashfull, time, nodes, nps, movesleft.
        info = chess.engine._parse_uci_info("tbhits 123 cpuload 456 hashfull 789 movesleft 42 time 987 nodes 654 nps 321", board)
        self.assertEqual(info["tbhits"], 123)
        self.assertEqual(info["cpuload"], 456)
        self.assertEqual(info["hashfull"], 789)
        self.assertEqual(info["time"], 0.987)
        self.assertEqual(info["nodes"], 654)
        self.assertEqual(info["nps"], 321)
        self.assertEqual(info["movesleft"], 42)

        # Hakkapeliitta double spaces.
        info = chess.engine._parse_uci_info("depth 10 seldepth 9 score cp 22  time 17 nodes 48299 nps 2683000 tbhits 0", board)
        self.assertEqual(info["depth"], 10)
        self.assertEqual(info["seldepth"], 9)
        self.assertEqual(info["score"], chess.engine.PovScore(chess.engine.Cp(22), chess.WHITE))
        self.assertEqual(info["time"], 0.017)
        self.assertEqual(info["nodes"], 48299)
        self.assertEqual(info["nps"], 2683000)
        self.assertEqual(info["tbhits"], 0)

        # Unknown tokens.
        board = chess.Board()
        info = chess.engine._parse_uci_info("depth 1 unkown1 seldepth 2 unknown2 time 16 nodes 1 score cp 72 unknown3 wdl 249 747 4 multipv 1 uknown4 pv g1f3 g8f6 unknown5", board)
        self.assertEqual(info["depth"], 1)
        self.assertEqual(info["seldepth"], 2)
        self.assertEqual(info["time"], 0.016)
        self.assertEqual(info["nodes"], 1)
        self.assertEqual(info["score"], chess.engine.PovScore(chess.engine.Cp(72), chess.WHITE))
        self.assertEqual(info["multipv"], 1)
        self.assertEqual(info["pv"], [chess.Move.from_uci("g1f3"), chess.Move.from_uci("g8f6")])

        # WDL (activated with UCI_ShowWDL).
        info = chess.engine._parse_uci_info("depth 1 seldepth 2 time 16 nodes 1 score cp 72 wdl 249 747 4 hashfull 0 nps 400 tbhits 0 multipv 1", board)
        self.assertEqual(info["wdl"].white(), chess.engine.Wdl(249, 747, 4))

    def test_uci_result(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("uci", ["uciok"])
            await protocol.initialize()
            mock.assert_done()

            limit = chess.engine.Limit(time=5)
            checkmate_board = chess.Board("k7/7R/6R1/8/8/8/8/K7 w - - 0 1")

            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position fen k7/7R/6R1/8/8/8/8/K7 w - - 0 1")
            mock.expect("go movetime 5000", ["bestmove g6g8"])
            result = await protocol.play(checkmate_board, limit, game="checkmate")
            self.assertEqual(result.move, checkmate_board.parse_uci("g6g8"))
            checkmate_board.push(result.move)
            self.assertTrue(checkmate_board.is_checkmate())
            await protocol.send_game_result(checkmate_board)
            mock.assert_done()

        asyncio.run(main())

    def test_uci_output_after_command(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("uci", [
                "Arasan v24.0.0-10-g367aa9f Copyright 1994-2023 by Jon Dart.",
                "All rights reserved.",
                "id name Arasan v24.0.0-10-g367aa9f",
                "uciok",
                "info string out of do_all_pending, list size=0"
            ])
            await protocol.initialize()

            mock.assert_done()

        asyncio.run(main())

    def test_hiarcs_bestmove(self):
        async def main():
            protocol = chess.engine.UciProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("uci", ["uciok"])
            await protocol.initialize()

            mock.expect("ucinewgame")
            mock.expect("isready", ["readyok"])
            mock.expect("position fen QN4n1/6r1/3k4/8/b2K4/8/8/8 b - - 0 1")
            mock.expect("go", [
                "info depth 1 seldepth 4 time 793 nodes 187 nps 235 score cp -40 pv g7g4 d4c3 string keep double  space",
                "bestmove g7g4  ponder d4c3 ",
            ])
            result = await protocol.play(chess.Board("QN4n1/6r1/3k4/8/b2K4/8/8/8 b - - 0 1"), chess.engine.Limit(), info=chess.engine.INFO_ALL)
            self.assertEqual(result.move, chess.Move.from_uci("g7g4"))
            self.assertEqual(result.ponder, chess.Move.from_uci("d4c3"))
            self.assertEqual(result.info["pv"], [chess.Move.from_uci("g7g4"), chess.Move.from_uci("d4c3")])
            self.assertEqual(result.info["string"], "keep double  space")
            mock.assert_done()

        asyncio.run(main())

    def test_xboard_options(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", [
                "feature egt=syzygy,gaviota",
                "feature option=\"spinvar -spin 50 0 100\"",
                "feature option=\"combovar -combo HI /// HELLO /// BYE\"",
                "feature option=\"checkvar -check 0\"",
                "feature option=\"stringvar -string \"\"\"",
                "feature option=\"filevar -file \"\"\"",
                "feature option=\"pathvar -path \"\"\"",
                "feature option=\"buttonvar -button\"",
                "feature option=\"resetvar -reset\"",
                "feature option=\"savevar -save\"",
                "feature ping=1 setboard=1 done=1",
            ])
            mock.expect("accepted egt")
            await protocol.initialize()
            mock.assert_done()

            self.assertEqual(protocol.options["egtpath syzygy"].type, "path")
            self.assertEqual(protocol.options["egtpath gaviota"].name, "egtpath gaviota")
            self.assertEqual(protocol.options["spinvar"].type, "spin")
            self.assertEqual(protocol.options["spinvar"].default, 50)
            self.assertEqual(protocol.options["spinvar"].min, 0)
            self.assertEqual(protocol.options["spinvar"].max, 100)
            self.assertEqual(protocol.options["combovar"].type, "combo")
            self.assertEqual(protocol.options["combovar"].var, ["HI", "HELLO", "BYE"])
            self.assertEqual(protocol.options["checkvar"].type, "check")
            self.assertEqual(protocol.options["checkvar"].default, False)
            self.assertEqual(protocol.options["stringvar"].type, "string")
            self.assertEqual(protocol.options["filevar"].type, "file")
            self.assertEqual(protocol.options["pathvar"].type, "path")
            self.assertEqual(protocol.options["buttonvar"].type, "button")
            self.assertEqual(protocol.options["resetvar"].type, "reset")
            self.assertEqual(protocol.options["savevar"].type, "save")

            mock.expect("option combovar=HI")
            await protocol.configure({"combovar": "HI"})
            mock.assert_done()

            mock.expect("option spinvar=42")
            await protocol.configure({"spinvar": 42})
            mock.assert_done()

            mock.expect("option checkvar=1")
            await protocol.configure({"checkvar": True})
            mock.assert_done()

            mock.expect("option pathvar=.")
            await protocol.configure({"pathvar": "."})
            mock.assert_done()

            mock.expect("option buttonvar")
            await protocol.configure({"buttonvar": None})
            mock.assert_done()

        asyncio.run(main())

    def test_xboard_replay(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["feature ping=1 setboard=1 done=1"])
            await protocol.initialize()
            mock.assert_done()

            limit = chess.engine.Limit(time=1.5, depth=17)
            board = chess.Board()
            board.push_san("d4")
            board.push_san("Nf6")
            board.push_san("c4")

            mock.expect("new")
            mock.expect("force")
            mock.expect("d2d4")
            mock.expect("g8f6")
            mock.expect("c2c4")
            mock.expect("st 1.5")
            mock.expect("sd 17")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e7e6"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game")
            self.assertEqual(result.move, board.parse_san("e6"))
            mock.assert_done()

            board.pop()
            mock.expect("force")
            mock.expect("remove")
            mock.expect("st 1.5")
            mock.expect("sd 17")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move c2c4"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game")
            self.assertEqual(result.move, board.parse_san("c4"))
            mock.assert_done()

            board.pop()
            board.pop()
            mock.expect("force")
            mock.expect("remove")
            mock.expect("undo")
            mock.expect("st 1.5")
            mock.expect("sd 17")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move d2d4"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game")
            self.assertEqual(result.move, board.parse_san("d4"))
            mock.assert_done()

        asyncio.run(main())

    def test_xboard_opponent(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["feature ping=1 setboard=1 name=1 done=1"])
            await protocol.initialize()
            mock.assert_done()

            limit = chess.engine.Limit(time=5)
            board = chess.Board()
            opponent = chess.engine.Opponent("Turk", "Mechanical", 2100, True)
            await protocol.send_opponent_information(opponent=opponent, engine_rating=3600)

            mock.expect("new")
            mock.expect("name Mechanical Turk")
            mock.expect("rating 3600 2100")
            mock.expect("computer")
            mock.expect("force")
            mock.expect("st 5")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e2e4"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game")
            self.assertEqual(result.move, board.parse_san("e4"))
            mock.assert_done()

            new_opponent = chess.engine.Opponent("Turochamp", None, 800, True)
            board.push(result.move)
            mock.expect("new")
            mock.expect("name Turochamp")
            mock.expect("rating 3600 800")
            mock.expect("computer")
            mock.expect("force")
            mock.expect("e2e4")
            mock.expect("st 5")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e7e5"])
            mock.expect_ping()
            result = await protocol.play(board, limit, game="game", opponent=new_opponent)
            self.assertEqual(result.move, board.parse_san("e5"))
            mock.assert_done()

            bad_opponent = chess.engine.Opponent("New\nLine", "GM", 1, False)
            with self.assertRaises(chess.engine.EngineError):
                await protocol.send_opponent_information(opponent=bad_opponent)
            mock.assert_done()

            with self.assertRaises(chess.engine.EngineError):
                result = await protocol.play(board, limit, game="bad game", opponent=bad_opponent)
            mock.assert_done()

        asyncio.run(main())

    def test_xboard_result(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["feature ping=1 setboard=1 done=1"])
            await protocol.initialize()
            mock.assert_done()

            limit = chess.engine.Limit(time=5)
            checkmate_board = chess.Board("k7/7R/6R1/8/8/8/8/K7 w - - 0 1")

            mock.expect("new")
            mock.expect("force")
            mock.expect("setboard k7/7R/6R1/8/8/8/8/K7 w - - 0 1")
            mock.expect("st 5")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move g6g8"])
            mock.expect_ping()
            mock.expect("force")
            mock.expect("result 1-0 {White mates}")
            result = await protocol.play(checkmate_board, limit, game="checkmate")
            self.assertEqual(result.move, checkmate_board.parse_uci("g6g8"))
            checkmate_board.push(result.move)
            self.assertTrue(checkmate_board.is_checkmate())
            await protocol.send_game_result(checkmate_board)
            mock.assert_done()

            unfinished_board = chess.Board()
            mock.expect("new")
            mock.expect("force")
            mock.expect("st 5")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e2e4"])
            mock.expect_ping()
            mock.expect("force")
            mock.expect("result *")
            result = await protocol.play(unfinished_board, limit, game="unfinished")
            self.assertEqual(result.move, unfinished_board.parse_uci("e2e4"))
            unfinished_board.push(result.move)
            await protocol.send_game_result(unfinished_board, game_complete=False)
            mock.assert_done()

            timeout_board = chess.Board()
            mock.expect("new")
            mock.expect("force")
            mock.expect("st 5")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e2e4"])
            mock.expect_ping()
            mock.expect("force")
            mock.expect("result 0-1 {Time forfeiture}")
            result = await protocol.play(timeout_board, limit, game="timeout")
            self.assertEqual(result.move, timeout_board.parse_uci("e2e4"))
            timeout_board.push(result.move)
            await protocol.send_game_result(timeout_board, chess.BLACK, "Time forfeiture")
            mock.assert_done()

            error_board = chess.Board()
            mock.expect("new")
            mock.expect("force")
            mock.expect("st 5")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e2e4"])
            mock.expect_ping()
            result = await protocol.play(error_board, limit, game="error")
            self.assertEqual(result.move, error_board.parse_uci("e2e4"))
            error_board.push(result.move)
            for c in "\n\r{}":
                with self.assertRaises(chess.engine.EngineError):
                    await protocol.send_game_result(error_board, chess.BLACK, f"Time{c}forfeiture")
            mock.assert_done()

            material_board = chess.Board("k7/8/8/8/8/8/8/K7 b - - 0 1")
            self.assertTrue(material_board.is_insufficient_material())
            mock.expect("new")
            mock.expect("force")
            mock.expect("setboard k7/8/8/8/8/8/8/K7 b - - 0 1")
            mock.expect("result 1/2-1/2 {Insufficient material}")
            await protocol.send_game_result(material_board)
            mock.assert_done()

        asyncio.run(main())

    def test_xboard_analyse(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", [
                "feature done=0 ping=1 setboard=1",
                "feature exclude=1",
                "feature variants=\"normal,atomic\" done=1",
            ])
            await protocol.initialize()
            mock.assert_done()

            board = chess.variant.AtomicBoard("rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1")
            limit = chess.engine.Limit(depth=1)
            mock.expect("new")
            mock.expect("variant atomic")
            mock.expect("force")
            mock.expect("setboard rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1")
            mock.expect("exclude all")
            mock.expect("include f7f6")
            mock.expect("post")
            mock.expect("analyze", ["4    116      23   2252  1... f6 2. e4 e6"])
            mock.expect(".")
            mock.expect("exit")
            mock.expect_ping()
            info = await protocol.analyse(board, limit, root_moves=[board.parse_san("f6")])
            self.assertEqual(info["depth"], 4)
            self.assertEqual(info["score"], chess.engine.PovScore(chess.engine.Cp(116), chess.BLACK))
            self.assertEqual(info["time"], 0.23)
            self.assertEqual(info["nodes"], 2252)
            self.assertEqual(info["pv"], [chess.Move.from_uci(move) for move in ["f7f6", "e2e4", "e7e6"]])
            mock.assert_done()

        asyncio.run(main())

    def test_xboard_level(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["feature ping=1 setboard=1 done=1"])
            await protocol.initialize()
            mock.assert_done()

            limit = chess.engine.Limit(black_clock=65, white_clock=100,
                                       black_inc=4, white_inc=8,
                                       clock_id="xboard level")
            board = chess.Board()
            mock.expect("new")
            mock.expect("force")
            mock.expect("level 0 1:40 8")
            mock.expect("time 10000")
            mock.expect("otim 6500")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move e2e4"])
            mock.expect_ping()
            result = await protocol.play(board, limit)
            self.assertEqual(result.move, chess.Move.from_uci("e2e4"))
            mock.assert_done()

            board.push(result.move)
            board.push_uci("e7e5")

            mock.expect("force")
            mock.expect("e7e5")
            mock.expect("time 10000")
            mock.expect("otim 6500")
            mock.expect("nopost")
            mock.expect("easy")
            mock.expect("go", ["move d2d4"])
            mock.expect_ping()
            result = await protocol.play(board, limit)
            self.assertEqual(result.move, chess.Move.from_uci("d2d4"))
            mock.assert_done()

        asyncio.run(main())

    def test_xboard_error(self):
        async def main():
            protocol = chess.engine.XBoardProtocol()
            mock = chess.engine.MockTransport(protocol)

            mock.expect("xboard")
            mock.expect("protover 2", ["Error (failed to initialize): Too bad!"])
            with self.assertRaises(chess.engine.EngineError):
                await protocol.initialize()

            with self.assertRaises(chess.engine.EngineError):
                # Trying to use the engine, but it was not successfully initialized.
                await protocol.ping()

            mock.assert_done()

        asyncio.run(main())

    @catchAndSkip(FileNotFoundError, "need /bin/bash")
    def test_transport_close_with_pending(self):
        async def main():
            transport, protocol = await chess.engine.popen_uci(["/bin/bash", "-c", "read && echo uciok && sleep 86400"])
            protocol.loop.call_later(0.01, transport.close)
            results = await asyncio.gather(protocol.ping(), protocol.ping(), return_exceptions=True)
            self.assertNotEqual(results[0], None)
            self.assertNotEqual(results[1], None)

        asyncio.run(main())

    @catchAndSkip(FileNotFoundError, "need /bin/bash")
    def test_quit_timeout(self):
        with chess.engine.SimpleEngine.popen_uci(["/bin/bash", "-c", "read && echo uciok && sleep 86400"], debug=True) as engine:
            engine.timeout = 0.01
            with self.assertRaises(asyncio.TimeoutError):
                engine.quit()

    def test_run_in_background(self):
        class ExpectedError(Exception):
            pass

        async def raise_expected_error(future):
            await asyncio.sleep(0.001)
            raise ExpectedError

        with self.assertRaises(ExpectedError):
            chess.engine.run_in_background(raise_expected_error)

        async def resolve(future):
            await asyncio.sleep(0.001)
            future.set_result("resolved")
            await asyncio.sleep(0.001)

        result = chess.engine.run_in_background(resolve)
        self.assertEqual(result, "resolved")


