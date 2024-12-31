import logging
import textwrap
import unittest
import io

import chess
import chess.gaviota
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant


class PgnTestCase(unittest.TestCase):

    def test_exporter(self):
        game = chess.pgn.Game()
        game.comments = ["Test game:"]
        game.headers["Result"] = "*"
        game.headers["VeryLongHeader"] = "This is a very long header, much wider than the 80 columns that PGNs are formatted with by default"

        e4 = game.add_variation(game.board().parse_san("e4"))
        e4.comments = ["Scandinavian Defense:"]

        e4_d5 = e4.add_variation(e4.board().parse_san("d5"))

        e4_h5 = e4.add_variation(e4.board().parse_san("h5"))
        e4_h5.nags.add(chess.pgn.NAG_MISTAKE)
        e4_h5.starting_comments = ["This"]
        e4_h5.comments = ["is nonsense"]

        e4_e5 = e4.add_variation(e4.board().parse_san("e5"))
        e4_e5_Qf3 = e4_e5.add_variation(e4_e5.board().parse_san("Qf3"))
        e4_e5_Qf3.nags.add(chess.pgn.NAG_MISTAKE)

        e4_c5 = e4.add_variation(e4.board().parse_san("c5"))
        e4_c5.comments = ["Sicilian"]

        e4_d5_exd5 = e4_d5.add_main_variation(e4_d5.board().parse_san("exd5"))
        e4_d5_exd5.comments = ["Best", "and the end of this {example}"]

        # Test string exporter with various options.
        exporter = chess.pgn.StringExporter(headers=False, comments=False, variations=False)
        game.accept(exporter)
        self.assertEqual(str(exporter), "1. e4 d5 2. exd5 *")

        exporter = chess.pgn.StringExporter(headers=False, comments=False)
        game.accept(exporter)
        self.assertEqual(str(exporter), "1. e4 d5 ( 1... h5 ) ( 1... e5 2. Qf3 ) ( 1... c5 ) 2. exd5 *")

        exporter = chess.pgn.StringExporter()
        game.accept(exporter)
        pgn = textwrap.dedent("""\
            [Event "?"]
            [Site "?"]
            [Date "????.??.??"]
            [Round "?"]
            [White "?"]
            [Black "?"]
            [Result "*"]
            [VeryLongHeader "This is a very long header, much wider than the 80 columns that PGNs are formatted with by default"]

            { Test game: } 1. e4 { Scandinavian Defense: } 1... d5 ( { This } 1... h5 $2
            { is nonsense } ) ( 1... e5 2. Qf3 $2 ) ( 1... c5 { Sicilian } ) 2. exd5
            { Best } { and the end of this example } *""")
        self.assertEqual(str(exporter), pgn)

        # Test file exporter.
        virtual_file = io.StringIO()
        exporter = chess.pgn.FileExporter(virtual_file)
        game.accept(exporter)
        self.assertEqual(virtual_file.getvalue(), pgn + "\n\n")

    def test_game_without_tag_roster(self):
        game = chess.pgn.Game.without_tag_roster()
        self.assertEqual(str(game), "*")

    def test_setup(self):
        game = chess.pgn.Game()
        self.assertEqual(game.board(), chess.Board())
        self.assertNotIn("FEN", game.headers)
        self.assertNotIn("SetUp", game.headers)
        self.assertNotIn("Variant", game.headers)

        fen = "rnbqkbnr/pp1ppp1p/6p1/8/3pP3/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 4"
        game.setup(fen)
        self.assertEqual(game.headers["FEN"], fen)
        self.assertEqual(game.headers["SetUp"], "1")
        self.assertNotIn("Variant", game.headers)

        game.setup(chess.STARTING_FEN)
        self.assertNotIn("FEN", game.headers)
        self.assertNotIn("SetUp", game.headers)
        self.assertNotIn("Variant", game.headers)

        # Setup again, while starting FEN is already set.
        game.setup(chess.STARTING_FEN)
        self.assertNotIn("FEN", game.headers)
        self.assertNotIn("SetUp", game.headers)
        self.assertNotIn("Variant", game.headers)

        game.setup(chess.Board(fen))
        self.assertEqual(game.headers["FEN"], fen)
        self.assertEqual(game.headers["SetUp"], "1")
        self.assertNotIn("Variant", game.headers)

        # Chess960 starting position #283.
        fen = "rkbqrnnb/pppppppp/8/8/8/8/PPPPPPPP/RKBQRNNB w KQkq - 0 1"
        game.setup(fen)
        self.assertEqual(game.headers["FEN"], fen)
        self.assertEqual(game.headers["SetUp"], "1")
        self.assertEqual(game.headers["Variant"], "Chess960")
        board = game.board()
        self.assertTrue(board.chess960)
        self.assertEqual(board.fen(), fen)

    def test_promote_to_main(self):
        e4 = chess.Move.from_uci("e2e4")
        d4 = chess.Move.from_uci("d2d4")

        node = chess.pgn.Game()
        node.add_variation(e4)
        node.add_variation(d4)
        self.assertEqual(list(variation.move for variation in node.variations), [e4, d4])

        node.promote_to_main(d4)
        self.assertEqual(list(variation.move for variation in node.variations), [d4, e4])

    def test_read_game(self):
        with open("data/pgn/kasparov-deep-blue-1997.pgn") as pgn:
            first_game = chess.pgn.read_game(pgn)
            second_game = chess.pgn.read_game(pgn)
            third_game = chess.pgn.read_game(pgn)
            fourth_game = chess.pgn.read_game(pgn)
            fifth_game = chess.pgn.read_game(pgn)
            sixth_game = chess.pgn.read_game(pgn)
            self.assertTrue(chess.pgn.read_game(pgn) is None)

        self.assertEqual(first_game.headers["Event"], "IBM Man-Machine, New York USA")
        self.assertEqual(first_game.headers["Site"], "01")
        self.assertEqual(first_game.headers["Result"], "1-0")

        self.assertEqual(second_game.headers["Event"], "IBM Man-Machine, New York USA")
        self.assertEqual(second_game.headers["Site"], "02")

        self.assertEqual(third_game.headers["ECO"], "A00")

        self.assertEqual(fourth_game.headers["PlyCount"], "111")

        self.assertEqual(fifth_game.headers["Result"], "1/2-1/2")

        self.assertEqual(sixth_game.headers["White"], "Deep Blue (Computer)")
        self.assertEqual(sixth_game.headers["Result"], "1-0")

    def test_read_game_with_multicomment_move(self):
        pgn = io.StringIO("1. e4 {A common opening} 1... e5 {A common response} {An uncommon comment}")
        game = chess.pgn.read_game(pgn)
        first_move = game.variation(0)
        self.assertEqual(first_move.comments, ["A common opening"])
        second_move = first_move.variation(0)
        self.assertEqual(second_move.comments, ["A common response", "An uncommon comment"])

    def test_comment_at_eol(self):
        pgn = io.StringIO(textwrap.dedent("""\
            1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d3 d6 6. Nbd2 a6 $6 (6... Bb6 $5 {
            /\\ Ne7, c6}) *"""))

        game = chess.pgn.read_game(pgn)

        # Seek the node after 6.Nbd2 and before 6...a6.
        node = game
        while node.variations and not node.has_variation(chess.Move.from_uci("a7a6")):
            node = node[0]

        # Make sure the comment for the second variation is there.
        self.assertIn(5, node[1].nags)
        self.assertEqual(node[1].comments, ["\n/\\ Ne7, c6"])

    def test_promotion_without_equals(self):
        # Example game from https://github.com/rozim/ChessData as originally
        # reported.
        pgn = io.StringIO(textwrap.dedent("""\
            [Event "It (open)"]
            [Site "Aschach (Austria)"]
            [Date "2011.12.26"]
            [Round "1"]
            [White "Ennsberger Ulrich (AUT)"]
            [Black "Koller Hans-Juergen (AUT)"]
            [Result "0-1"]
            [ECO "A45"]
            [WhiteElo "2373"]
            [BlackElo "2052"]
            [ID ""]
            [FileName ""]
            [Annotator ""]
            [Source ""]
            [Remark ""]

            1.d4 Nf6 2.Bg5 c5 3.d5 Ne4 4.Bf4 Qb6 5.Nd2 Nxd2 6.Bxd2 e6 7.Bc3
            d6 8.e4 e5 9.a4 Be7 10.a5 Qc7 11.f4 f6 12.f5 g6 13.Bb5+ Bd7 14.Bc4
            gxf5 15.Qh5+ Kd8 16.exf5 Qc8 17.g4 Na6 18.Ne2 b5 19.axb6 axb6
            20.O-O Nc7 21.Qf7 h5 22.Qg7 Rf8 23.gxh5 Ne8 24.Rxa8 Nxg7 25.Rxc8+
            Kxc8 26.Ng3 Rh8 27.Be2 Be8 28.Be1 Nxh5 29.Bxh5 Bxh5 30.Nxh5 Rxh5
            31.h4 Bf8 32.c4 Bh6 33.Bg3 Be3+ 34.Kg2 Kb7 35.Kh3 b5 36.b3 b4
            37.Kg4 Rh8 38.Kf3 Bh6 39.Bf2 Ra8 40.Kg4 Bf4 41.Kh5 Ra3 42.Kg6
            Rxb3 43.h5 Rf3 44.h6 Bxh6 45.Kxh6 Rxf5 46.Kg6 Rf4 47.Kf7 e4 48.Re1
            Rxf2 49.Ke6 Kc7 50.Rh1 b3 51.Rh7+ Kb6 52.Kxd6 b2 53.Rh1 Rd2 54.Rh8
            e3 55.Rb8+ Ka5 56.Kxc5 Ka4 57.d6 e2 58.Re8 b1Q 0-1"""))

        game = chess.pgn.read_game(pgn)

        # Make sure the last move is a promotion.
        last_node = game.end()
        self.assertEqual(last_node.move.uci(), "b2b1q")

    def test_header_with_paren(self):
        with open("data/pgn/stockfish-learning.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Opening"], "St. George (Baker) defense")
        self.assertEqual(game.end().board(), chess.Board("8/2p2k2/1pR3p1/1P1P4/p1P2P2/P4K2/8/5r2 w - - 7 78"))

    def test_special_tag_names(self):
        pgn = io.StringIO("""[BlackType: "program"]""")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["BlackType:"], "program")

        with self.assertRaises(ValueError):
            game.headers["~"] = "foo"

        game.headers["Equals="] = "bar"

    def test_chess960_without_fen(self):
        pgn = io.StringIO(textwrap.dedent("""\
            [Variant "Chess960"]

            1. e4 *
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game[0].move, chess.Move.from_uci("e2e4"))

    def test_variation_stack(self):
        # Survive superfluous closing brackets.
        pgn = io.StringIO("1. e4 (1. d4))) !? *")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(game[0].san(), "e4")
        self.assertEqual(game[0].uci(), "e2e4")
        self.assertEqual(game[1].san(), "d4")
        self.assertEqual(game[1].uci(), "d2d4")
        self.assertEqual(len(game.errors), 0)

        # Survive superfluous opening brackets.
        pgn = io.StringIO("((( 1. c4 *")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(game[0].san(), "c4")
        self.assertEqual(len(game.errors), 0)

    def test_game_starting_comment(self):
        pgn = io.StringIO("{ Game starting comment } 1. d3")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comments, ["Game starting comment"])
        self.assertEqual(game[0].san(), "d3")

        pgn = io.StringIO("{ Empty game, but has a comment }")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comments, ["Empty game, but has a comment"])

    def test_game_starting_variation(self):
        pgn = io.StringIO(textwrap.dedent("""\
            {Start of game} 1. e4 ({Start of variation} 1. d4) 1... e5
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.comments, ["Start of game"])

        node = game[0]
        self.assertEqual(node.move, chess.Move.from_uci("e2e4"))
        self.assertFalse(node.comments)
        self.assertFalse(node.starting_comments)

        node = game[1]
        self.assertEqual(node.move, chess.Move.from_uci("d2d4"))
        self.assertFalse(node.comments)
        self.assertEqual(node.starting_comments, ["Start of variation"])

    def test_annotation_symbols(self):
        pgn = io.StringIO("1. b4?! g6 2. Bb2 Nc6? 3. Bxh8!!")
        game = chess.pgn.read_game(pgn)

        node = game.variation(chess.Move.from_uci("b2b4"))
        self.assertIn(chess.pgn.NAG_DUBIOUS_MOVE, node.nags)
        self.assertEqual(len(node.nags), 1)

        node = node[0]
        self.assertEqual(len(node.nags), 0)

        node = node[0]
        self.assertEqual(len(node.nags), 0)

        node = node[0]
        self.assertIn(chess.pgn.NAG_MISTAKE, node.nags)
        self.assertEqual(len(node.nags), 1)

        node = node[0]
        self.assertIn(chess.pgn.NAG_BRILLIANT_MOVE, node.nags)
        self.assertEqual(len(node.nags), 1)

    def test_tree_traversal(self):
        game = chess.pgn.Game()
        node = game.add_variation(chess.Move(chess.E2, chess.E4))
        alternative_node = game.add_variation(chess.Move(chess.D2, chess.D4))
        end_node = node.add_variation(chess.Move(chess.E7, chess.E5))

        self.assertEqual(game.root(), game)
        self.assertEqual(node.root(), game)
        self.assertEqual(alternative_node.root(), game)
        self.assertEqual(end_node.root(), game)

        self.assertEqual(game.end(), end_node)
        self.assertEqual(node.end(), end_node)
        self.assertEqual(end_node.end(), end_node)
        self.assertEqual(alternative_node.end(), alternative_node)

        self.assertTrue(game.is_mainline())
        self.assertTrue(node.is_mainline())
        self.assertTrue(end_node.is_mainline())
        self.assertFalse(alternative_node.is_mainline())

        self.assertFalse(game.starts_variation())
        self.assertFalse(node.starts_variation())
        self.assertFalse(end_node.starts_variation())
        self.assertTrue(alternative_node.starts_variation())

        self.assertFalse(game.is_end())
        self.assertFalse(node.is_end())
        self.assertTrue(alternative_node.is_end())
        self.assertTrue(end_node.is_end())

    def test_promote_demote(self):
        game = chess.pgn.Game()
        a = game.add_variation(chess.Move(chess.A2, chess.A3))
        b = game.add_variation(chess.Move(chess.B2, chess.B3))

        self.assertTrue(a.is_main_variation())
        self.assertFalse(b.is_main_variation())
        self.assertEqual(game[0], a)
        self.assertEqual(game[1], b)

        game.promote(b)
        self.assertTrue(b.is_main_variation())
        self.assertFalse(a.is_main_variation())
        self.assertEqual(game[0], b)
        self.assertEqual(game[1], a)

        game.demote(b)
        self.assertTrue(a.is_main_variation())

        c = game.add_main_variation(chess.Move(chess.C2, chess.C3))
        self.assertTrue(c.is_main_variation())
        self.assertFalse(a.is_main_variation())
        self.assertFalse(b.is_main_variation())
        self.assertEqual(game[0], c)
        self.assertEqual(game[1], a)
        self.assertEqual(game[2], b)

    def test_skip_game(self):
        with open("data/pgn/kasparov-deep-blue-1997.pgn") as pgn:
            offsets = []
            while True:
                offset = pgn.tell()
                if chess.pgn.skip_game(pgn):
                    offsets.append(offset)
                else:
                    break
            self.assertEqual(len(offsets), 6)

            pgn.seek(offsets[0])
            first_game = chess.pgn.read_game(pgn)
            self.assertEqual(first_game.headers["Event"], "IBM Man-Machine, New York USA")
            self.assertEqual(first_game.headers["Site"], "01")

            pgn.seek(offsets[5])
            sixth_game = chess.pgn.read_game(pgn)
            self.assertEqual(sixth_game.headers["Event"], "IBM Man-Machine, New York USA")
            self.assertEqual(sixth_game.headers["Site"], "06")

    def test_tricky_skip_game(self):
        raw_pgn = textwrap.dedent("""
            1. a3 ; { ; }

            1. b3 { ;
            % {
            1... g6 ; {

            1. c3 { }
            % {
            1... f6 ; { } {{{

            1. d3""")
        pgn = io.StringIO(raw_pgn)

        offsets = []
        while True:
            offset = pgn.tell()
            if chess.pgn.skip_game(pgn):
                offsets.append(offset)
            else:
                break

        self.assertEqual(len(offsets), 3)

        pgn.seek(offsets[0])
        self.assertEqual(chess.pgn.read_game(pgn).next().move, chess.Move.from_uci("a2a3"))
        pgn.seek(offsets[1])
        self.assertEqual(chess.pgn.read_game(pgn).next().move, chess.Move.from_uci("b2b3"))
        pgn.seek(offsets[2])
        self.assertEqual(chess.pgn.read_game(pgn).next().move, chess.Move.from_uci("d2d3"))
        self.assertEqual(chess.pgn.read_game(pgn), None)

    def test_read_headers(self):
        with open("data/pgn/kasparov-deep-blue-1997.pgn") as pgn:
            offsets = []

            while True:
                offset = pgn.tell()
                headers = chess.pgn.read_headers(pgn)
                if headers is None:
                    break
                elif headers.get("Result", "*") == "1/2-1/2":
                    offsets.append(offset)

            pgn.seek(offsets[0])
            first_drawn_game = chess.pgn.read_game(pgn)
            self.assertEqual(first_drawn_game.headers["Site"], "03")
            self.assertEqual(first_drawn_game[0].move, chess.Move.from_uci("d2d3"))

    def test_parse_time_control(self):
        with open("data/pgn/nepomniachtchi-liren-game1.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            tc = game.time_control()

            self.assertEqual(tc, chess.pgn.parse_time_control(game.headers["TimeControl"]))

            self.assertEqual(tc.type, chess.pgn.TimeControlType.STANDARD)
            self.assertEqual(len(tc.parts), 3)

            tcp1, tcp2, tcp3 = tc.parts

            self.assertEqual(tcp1, chess.pgn.TimeControlPart(40, 7200))
            self.assertEqual(tcp2, chess.pgn.TimeControlPart(20, 3600))
            self.assertEqual(tcp3, chess.pgn.TimeControlPart(0, 900, 30))

        self.assertEqual(chess.pgn.TimeControlType.BULLET, chess.pgn.parse_time_control("60").type)
        self.assertEqual(chess.pgn.TimeControlType.BULLET, chess.pgn.parse_time_control("60+1").type)

        self.assertEqual(chess.pgn.TimeControlType.BLITZ, chess.pgn.parse_time_control("60+2").type)
        self.assertEqual(chess.pgn.TimeControlType.BLITZ, chess.pgn.parse_time_control("300").type)
        self.assertEqual(chess.pgn.TimeControlType.BLITZ, chess.pgn.parse_time_control("300+3").type)

        self.assertEqual(chess.pgn.TimeControlType.RAPID, chess.pgn.parse_time_control("300+10").type)
        self.assertEqual(chess.pgn.TimeControlType.RAPID, chess.pgn.parse_time_control("1800").type)
        self.assertEqual(chess.pgn.TimeControlType.RAPID, chess.pgn.parse_time_control("1800+10").type)

        self.assertEqual(chess.pgn.TimeControlType.STANDARD, chess.pgn.parse_time_control("1800+30").type)
        self.assertEqual(chess.pgn.TimeControlType.STANDARD, chess.pgn.parse_time_control("5400").type)
        self.assertEqual(chess.pgn.TimeControlType.STANDARD, chess.pgn.parse_time_control("5400+30").type)

        with self.assertRaises(ValueError):
            chess.pgn.parse_time_control("300+a")

        with self.assertRaises(ValueError):
            chess.pgn.parse_time_control("300+ad")

        with self.assertRaises(ValueError):
            chess.pgn.parse_time_control("600:20/180")

        with self.assertRaises(ValueError):
            chess.pgn.parse_time_control("abc")

        with self.assertRaises(ValueError):
            chess.pgn.parse_time_control("40/abc")


    def test_visit_board(self):
        class TraceVisitor(chess.pgn.BaseVisitor):
            def __init__(self):
                self.trace = []

            def visit_board(self, board):
                self.trace.append(board.fen())

            def visit_move(self, board, move):
                self.trace.append(board.san(move))

            def result(self):
                return self.trace

        pgn = io.StringIO(textwrap.dedent("""\
            [FEN "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"]

            1... e5 (1... d5 2. exd5) (1... c5) 2. Nf3 Nc6
            """))

        trace = [
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            "e5",
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "d5",
            "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "exd5",
            "rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2",
            "c5",
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "Nf3",
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
            "Nc6",
            "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        ]

        self.assertEqual(trace, chess.pgn.read_game(pgn, Visitor=TraceVisitor))

        pgn.seek(0)
        self.assertEqual(trace, chess.pgn.read_game(pgn).accept(TraceVisitor()))

        pgn.seek(0)
        self.assertEqual(chess.Board(trace[-1]), chess.pgn.read_game(pgn, Visitor=chess.pgn.BoardBuilder))

    def test_black_to_move(self):
        game = chess.pgn.Game()
        game.setup("8/8/4k3/8/4P3/4K3/8/8 b - - 0 17")
        node = game
        node = node.add_main_variation(chess.Move.from_uci("e6d6"))
        node = node.add_main_variation(chess.Move.from_uci("e3d4"))
        node = node.add_main_variation(chess.Move.from_uci("d6e6"))

        expected = textwrap.dedent("""\
            [Event "?"]
            [Site "?"]
            [Date "????.??.??"]
            [Round "?"]
            [White "?"]
            [Black "?"]
            [Result "*"]
            [FEN "8/8/4k3/8/4P3/4K3/8/8 b - - 0 17"]
            [SetUp "1"]

            17... Kd6 18. Kd4 Ke6 *""")

        self.assertEqual(str(game), expected)

    def test_result_termination_marker(self):
        pgn = io.StringIO("1. d4 1-0")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Result"], "1-0")

    def test_missing_setup_tag(self):
        pgn = io.StringIO(textwrap.dedent("""\
            [Event "Test position"]
            [Site "Black to move "]
            [Date "1997.10.26"]
            [Round "?"]
            [White "Pos  16"]
            [Black "VA33.EPD"]
            [Result "1-0"]
            [FEN "rbb1N1k1/pp1n1ppp/8/2Pp4/3P4/4P3/P1Q2PPq/R1BR1K2 b - - 0 1"]

            {Houdini 1.5 x64: 1)} 1... Nxc5 ({Houdini 1.5 x64: 2)} 1... Qh1+ 2. Ke2 Qxg2 3.
            Kd2 Nxc5 4. Qxc5 Bg4 5. Ba3 Qxf2+ 6. Kc3 Qxe3+ 7. Kb2 Qxe8 8. Re1 Be6 9. Rh1 a5
            10. Rag1 Ba7 11. Qc3 g6 12. Bc5 Qb5+ 13. Qb3 Qe2+ 14. Qc2 Qxc2+ 15. Kxc2 Bxc5
            16. dxc5 Rc8 17. Kd2 {-2.39/22}) 2. dxc5 Bg4 3. f3 Bxf3 4. Qf2 Bxd1 5. Nd6 Bxd6
            6. cxd6 Qxd6 7. Bb2 Ba4 8. Qf4 Bb5+ 9. Kf2 Qg6 10. Bd4 f6 11. Qc7 Bc6 12. a4 a6
            13. Qg3 Qxg3+ 14. Kxg3 Rc8 15. Rc1 Kf7 16. a5 h5 17. Rh1 {-2.63/23}
            1-0"""))

        game = chess.pgn.read_game(pgn)
        self.assertIn("FEN", game.headers)
        self.assertNotIn("SetUp", game.headers)

        board = chess.Board("rbb1N1k1/pp1n1ppp/8/2Pp4/3P4/4P3/P1Q2PPq/R1BR1K2 b - - 0 1")
        self.assertEqual(game.board(), board)

    def test_chessbase_empty_line(self):
        with open("data/pgn/chessbase-empty-line.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.headers["Event"], "AlphaZero vs. Stockfish")
            self.assertEqual(game.headers["Round"], "1")
            self.assertEqual(game.next().move, chess.Move.from_uci("e2e4"))

            self.assertTrue(chess.pgn.read_game(pgn) is None)

    def test_game_from_board(self):
        setup = "3k4/8/4K3/8/8/8/8/2R5 b - - 0 1"
        board = chess.Board(setup)
        board.push_san("Ke8")
        board.push_san("Rc8#")

        game = chess.pgn.Game.from_board(board)
        self.assertEqual(game.headers["FEN"], setup)

        end_node = game.end()
        self.assertEqual(end_node.move, chess.Move.from_uci("c1c8"))
        self.assertEqual(end_node.parent.move, chess.Move.from_uci("d8e8"))

        self.assertEqual(game.headers["Result"], "1-0")

    def test_errors(self):
        pgn = io.StringIO("""
            1. e4 Qa1 e5 2. Qxf8

            1. a3""")
        logging.disable(logging.ERROR)
        game = chess.pgn.read_game(pgn)
        logging.disable(logging.NOTSET)
        self.assertEqual(len(game.errors), 1)
        self.assertEqual(game.end().board().fen(), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.end().board().fen(), "rnbqkbnr/pppppppp/8/8/8/P7/1PPPPPPP/RNBQKBNR b KQkq - 0 1")

    def test_add_line(self):
        game = chess.pgn.Game()
        game.add_variation(chess.Move.from_uci("e2e4"))

        moves = [chess.Move.from_uci("g1f3"), chess.Move.from_uci("d7d5")]

        tail = game.add_line(moves, starting_comment="start", comment="end", nags=(17, 42))

        self.assertEqual(tail.parent.move, chess.Move.from_uci("g1f3"))
        self.assertEqual(tail.parent.starting_comments, ["start"])
        self.assertEqual(tail.parent.comments, [])
        self.assertEqual(len(tail.parent.nags), 0)

        self.assertEqual(tail.move, chess.Move.from_uci("d7d5"))
        self.assertEqual(tail.comments, ["end"])
        self.assertIn(42, tail.nags)

    def test_mainline(self):
        moves = [chess.Move.from_uci(uci) for uci in ["d2d3", "g8f6", "e2e4"]]

        game = chess.pgn.Game()
        game.add_line(moves)

        self.assertEqual(list(game.mainline_moves()), moves)
        self.assertTrue(game.mainline_moves())
        self.assertEqual(list(reversed(game.mainline_moves())), list(reversed(moves)))
        self.assertEqual(str(game.mainline_moves()), "1. d3 Nf6 2. e4")

    def test_lan(self):
        pgn = io.StringIO("1. e2-e4")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.end().move, chess.Move.from_uci("e2e4"))

    def test_variants(self):
        pgn = io.StringIO(textwrap.dedent("""\
            [Variant "Atomic"]
            [FEN "8/8/1b6/8/3Nk3/4K3/8/8 w - - 0 1"]

            1. Ne6
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.end().board().fen(), "8/8/1b2N3/8/4k3/4K3/8/8 b - - 1 1")

        game.setup(chess.variant.SuicideBoard())
        self.assertEqual(game.headers["Variant"], "Suicide")

        game.setup(chess.Board())
        self.assertNotIn("Variant", game.headers)

    def test_cutechess_fischerrandom(self):
        with open("data/pgn/cutechess-fischerrandom.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            board = game.board()
            self.assertTrue(board.chess960)
            self.assertEqual(board.fen(), "nbbrknrq/pppppppp/8/8/8/8/PPPPPPPP/NBBRKNRQ w KQkq - 0 1")

    def test_z0(self):
        with open("data/pgn/anastasian-lewis.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            board = game.end().board()
            self.assertEqual(board.fen(), "5rk1/2p1R2p/p5pb/2PPR3/8/2Q2B2/5P2/4K2q w - - 3 43")

    def test_uci_moves(self):
        with open("data/pgn/uci-moves.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            board = game.end().board()
            self.assertEqual(board.fen(), "8/8/2B5/4k3/4Pp2/1b6/1P3K2/8 b - - 0 57")

    def test_wierd_header(self):
        pgn = io.StringIO(r"""[Black "[=0040.34h5a4]"]""")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Black"], "[=0040.34h5a4]")

    def test_semicolon_comment(self):
        pgn = io.StringIO("1. e4 ; e5")
        game = chess.pgn.read_game(pgn)
        node = game.next()
        self.assertEqual(node.move, chess.Move.from_uci("e2e4"))
        self.assertTrue(node.is_end())

    def test_empty_game(self):
        pgn = io.StringIO(" \n\n   ")
        game = chess.pgn.read_game(pgn)
        self.assertTrue(game is None)

    def test_no_movetext(self):
        pgn = io.StringIO(textwrap.dedent("""
            [Event "A"]


            [Event "B"]
            """))

        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Event"], "A")
        game = chess.pgn.read_game(pgn)
        self.assertEqual(game.headers["Event"], "B")

        self.assertTrue(chess.pgn.read_game(pgn) is None)

    def test_subgame(self):
        pgn = io.StringIO("1. d4 d5 (1... Nf6 2. c4 (2. Nf3 g6 3. g3))")
        game = chess.pgn.read_game(pgn)
        node = game.next().variations[1]
        subgame = node.accept_subgame(chess.pgn.GameBuilder())
        self.assertEqual(subgame.headers["FEN"], "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2")
        self.assertEqual(subgame.next().move, chess.Move.from_uci("c2c4"))
        self.assertEqual(subgame.variations[1].move, chess.Move.from_uci("g1f3"))

    def test_is_wild(self):
        headers = chess.pgn.Headers()
        headers["Variant"] = "wild/1"
        self.assertTrue(headers.is_wild())

    def test_my_game_node(self):
        class MyGameNode(chess.pgn.GameNode):
            def add_variation(self, move, *, comment="", starting_comment="", nags=[]):
                return MyChildNode(self, move, comment=comment, starting_comment=starting_comment, nags=nags)

        class MyChildNode(chess.pgn.ChildNode, MyGameNode):
            pass

        class MyGame(chess.pgn.Game, MyGameNode):
            pass

        pgn = io.StringIO("1. e4")
        game = chess.pgn.read_game(pgn, Visitor=MyGame.builder)
        self.assertTrue(isinstance(game, MyGame))
        node = game.variation(chess.Move.from_uci("e2e4"))
        self.assertTrue(isinstance(node, MyGameNode))

    def test_recursion(self):
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        for _ in range(1000):
            board.push(chess.Move(chess.E1, chess.E2))
            board.push(chess.Move(chess.E8, chess.E7))
            board.push(chess.Move(chess.E2, chess.E1))
            board.push(chess.Move(chess.E7, chess.E8))
        game = chess.pgn.Game.from_board(board)
        self.assertTrue(str(game).endswith("2000. Ke1 Ke8 1/2-1/2"))

    def test_annotations(self):
        game = chess.pgn.Game()
        game.comments = ["foo [%bar] baz"]

        self.assertTrue(game.clock() is None)
        clock = 12345
        game.set_clock(clock)
        self.assertEqual(game.comments, ["foo [%bar] baz", "[%clk 3:25:45]"])
        self.assertEqual(game.clock(), clock)

        self.assertTrue(game.eval() is None)
        game.set_eval(chess.engine.PovScore(chess.engine.Cp(-80), chess.WHITE))
        self.assertEqual(game.comments, ["foo [%bar] baz", "[%clk 3:25:45]", "[%eval -0.80]"])
        self.assertEqual(game.eval().white().score(), -80)
        self.assertEqual(game.eval_depth(), None)
        game.set_eval(chess.engine.PovScore(chess.engine.Mate(1), chess.WHITE), 5)
        self.assertEqual(game.comments, ["foo [%bar] baz", "[%clk 3:25:45]", "[%eval #1,5]"])
        self.assertEqual(game.eval().white().mate(), 1)
        self.assertEqual(game.eval_depth(), 5)

        self.assertEqual(game.arrows(), [])
        game.set_arrows([(chess.A1, chess.A1), chess.svg.Arrow(chess.A1, chess.H1, color="red"), chess.svg.Arrow(chess.B1, chess.B8)])
        self.assertEqual(game.comments, ["[%csl Ga1][%cal Ra1h1,Gb1b8]", "foo [%bar] baz", "[%clk 3:25:45]", "[%eval #1,5]"])
        arrows = game.arrows()
        self.assertEqual(len(arrows), 3)
        self.assertEqual(arrows[0].color, "green")
        self.assertEqual(arrows[1].color, "red")
        self.assertEqual(arrows[2].color, "green")

        self.assertTrue(game.emt() is None)
        emt = 321
        game.set_emt(emt)
        self.assertEqual(game.comments, ["[%csl Ga1][%cal Ra1h1,Gb1b8]", "foo [%bar] baz", "[%clk 3:25:45]", "[%eval #1,5]", "[%emt 0:05:21]"])
        self.assertEqual(game.emt(), emt)

        game.set_eval(None)
        self.assertEqual(game.comments, ["[%csl Ga1][%cal Ra1h1,Gb1b8]", "foo [%bar] baz", "[%clk 3:25:45]", "[%emt 0:05:21]"])

        game.set_emt(None)
        self.assertEqual(game.comments, ["[%csl Ga1][%cal Ra1h1,Gb1b8]", "foo [%bar] baz", "[%clk 3:25:45]"])

        game.set_clock(None)
        game.set_arrows([])
        self.assertEqual(game.comments, ["foo [%bar] baz"])

    def test_eval(self):
        game = chess.pgn.Game()
        for cp in range(199, 220):
            game.set_eval(chess.engine.PovScore(chess.engine.Cp(cp), chess.WHITE))
            self.assertEqual(game.eval().white().cp, cp)

    def test_float_emt(self):
        game = chess.pgn.Game()
        game.comments = ["[%emt 0:00:01.234]"]
        self.assertEqual(game.emt(), 1.234)

        game.set_emt(6.54321)
        self.assertEqual(game.comments, ["[%emt 0:00:06.543]"])
        self.assertEqual(game.emt(), 6.543)

        game.set_emt(-70)
        self.assertEqual(game.comments, ["[%emt 0:00:00]"])  # Clamped
        self.assertEqual(game.emt(), 0)

    def test_float_clk(self):
        game = chess.pgn.Game()
        game.comments = ["[%clk 0:00:01.234]"]
        self.assertEqual(game.clock(), 1.234)

        game.set_clock(6.54321)
        self.assertEqual(game.comments, ["[%clk 0:00:06.543]"])
        self.assertEqual(game.clock(), 6.543)

        game.set_clock(-70)
        self.assertEqual(game.comments, ["[%clk 0:00:00]"])  # Clamped
        self.assertEqual(game.clock(), 0)

    def test_node_turn(self):
        game = chess.pgn.Game()
        self.assertEqual(game.turn(), chess.WHITE)
        node = game.add_variation(chess.Move.from_uci("a2a3"))
        self.assertEqual(node.turn(), chess.BLACK)
        node = node.add_variation(chess.Move.from_uci("a7a6"))
        self.assertEqual(node.turn(), chess.WHITE)

        game = chess.pgn.Game()
        game.setup("4k3/8/8/8/8/8/8/4K3 b - - 7 6")
        self.assertEqual(game.turn(), chess.BLACK)
        node = game.add_variation(chess.Move.from_uci("e8e7"))
        self.assertEqual(node.turn(), chess.WHITE)
        node = node.add_variation(chess.Move.from_uci("e1e2"))
        self.assertEqual(node.turn(), chess.BLACK)

    def test_skip_inner_variation(self):
        class BlackVariationsOnly(chess.pgn.GameBuilder):
            def begin_variation(self):
                self.skipping = self.variation_stack[-1].turn() != chess.WHITE
                if self.skipping:
                    return chess.pgn.SKIP
                else:
                    return super().begin_variation()

            def end_variation(self):
                if self.skipping:
                    self.skipping = False
                else:
                    return super().end_variation()

        pgn = "1. e4 e5 ( 1... d5 2. exd5 Qxd5 3. Nc3 ( 3. c4 ) 3... Qa5 ) *"
        expected_pgn = "1. e4 e5 ( 1... d5 2. exd5 Qxd5 3. Nc3 Qa5 ) *"

        # Driven by parser.
        game = chess.pgn.read_game(io.StringIO(pgn), Visitor=BlackVariationsOnly)
        self.assertEqual(game.accept(chess.pgn.StringExporter(headers=False)), expected_pgn)

        # Driven by game tree traversal.
        game = chess.pgn.read_game(io.StringIO(pgn)).accept(BlackVariationsOnly())
        self.assertEqual(game.accept(chess.pgn.StringExporter(headers=False)), expected_pgn)

    def test_utf8_bom(self):
        not_utf8_sig = "utf-8"
        with open("data/pgn/utf8-bom.pgn", encoding=not_utf8_sig) as pgn:
            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.headers["Event"], "A")

            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.headers["Event"], "B")

            game = chess.pgn.read_game(pgn)
            self.assertEqual(game, None)



