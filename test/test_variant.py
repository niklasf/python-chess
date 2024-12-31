import unittest

import textwrap
import io

import chess
import chess.gaviota
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant


class SuicideTestCase(unittest.TestCase):

    def test_parse_san(self):
        board = chess.variant.SuicideBoard()
        board.push_san("e4")
        board.push_san("d5")

        # Capture is mandatory.
        with self.assertRaises(chess.IllegalMoveError):
            board.push_san("Nf3")

    def test_is_legal(self):
        board = chess.variant.SuicideBoard("4k3/8/8/8/8/1r3B2/8/4K3 b - - 0 1")
        Rxf3 = board.parse_san("Rxf3")
        Rb4 = chess.Move.from_uci("b3b4")
        self.assertTrue(board.is_legal(Rxf3))
        self.assertIn(Rxf3, board.generate_legal_moves())
        self.assertFalse(board.is_legal(Rb4))
        self.assertNotIn(Rb4, board.generate_legal_moves())

    def test_suicide_insufficient_material(self):
        # Kings only.
        board = chess.variant.SuicideBoard("8/8/8/2k5/8/8/4K3/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Bishops on the same color.
        board = chess.variant.SuicideBoard("8/8/8/5b2/2B5/1B6/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Opposite-color bishops.
        board = chess.variant.SuicideBoard("4b3/8/8/8/3B4/2B5/8/8 b - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # Pawn not blocked.
        board = chess.variant.SuicideBoard("8/5b2/5P2/8/3B4/2B5/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Pawns blocked, but on wrong color.
        board = chess.variant.SuicideBoard("8/5p2/5P2/8/8/8/3b4/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Stalemate.
        board = chess.variant.SuicideBoard("6B1/6pB/6P1/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Pawns not really locked up.
        board = chess.variant.SuicideBoard("8/8/8/2pp4/2PP4/8/8/8 w - - 0 1")
        self.assertFalse(board.is_insufficient_material())

    def test_king_promotions(self):
        board = chess.variant.SuicideBoard("8/6P1/8/3K1k2/8/8/3p4/8 b - - 0 1")
        d1K = chess.Move.from_uci("d2d1k")
        self.assertIn(d1K, board.generate_legal_moves())
        self.assertTrue(board.is_pseudo_legal(d1K))
        self.assertTrue(board.is_legal(d1K))
        self.assertEqual(board.san(d1K), "d1=K")
        self.assertEqual(board.parse_san("d1=K"), d1K)


class AtomicTestCase(unittest.TestCase):

    def test_atomic_capture(self):
        fen = "rnbqkb1r/pp2pppp/2p2n2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq - 3 4"
        board = chess.variant.AtomicBoard(fen)
        board.push_san("dxc4")
        self.assertEqual(board.fen(), "rnbqkb1r/pp2pppp/2p2n2/8/3P4/5N2/PP2PPPP/R1BQKB1R w KQkq - 0 5")
        board.pop()
        self.assertEqual(board.fen(), fen)

    def test_atomic_mate_legality(self):
        # We are in check. Not just any move will do.
        board = chess.variant.AtomicBoard("8/8/1Q2pk2/8/8/8/3K4/1n6 w - - 0 1")
        self.assertTrue(board.is_check())
        Qa7 = chess.Move.from_uci("b6a7")
        self.assertTrue(board.is_pseudo_legal(Qa7))
        self.assertFalse(board.is_legal(Qa7))
        self.assertNotIn(Qa7, board.generate_legal_moves())

        # Ignore check to explode the opponent's king.
        Qxe6 = board.parse_san("Qxe6#")
        self.assertTrue(board.is_legal(Qxe6))
        self.assertIn(Qxe6, board.generate_legal_moves())

        # Exploding both kings is not a legal check evasion.
        board = chess.variant.AtomicBoard("8/8/8/2K5/2P5/2k1n3/8/2R5 b - - 0 1")
        Nxc4 = chess.Move.from_uci("e3c4")
        self.assertTrue(board.is_pseudo_legal(Nxc4))
        self.assertFalse(board.is_legal(Nxc4))
        self.assertNotIn(Nxc4, board.generate_legal_moves())

    def test_atomic_en_passant(self):
        # Real-world position.
        board = chess.variant.AtomicBoard("rn2kb1r/2p1p2p/p2q1pp1/1pPP4/Q7/4P3/PP3P1P/R3K3 w Qkq b6 0 11")
        board.push_san("cxb6+")
        self.assertEqual(board.fen(), "rn2kb1r/2p1p2p/p2q1pp1/3P4/Q7/4P3/PP3P1P/R3K3 b Qkq - 0 11")

        # Test the explosion radius.
        board = chess.variant.AtomicBoard("3kK3/8/8/2NNNNN1/2NN1pN1/2NN1NN1/2NNPNN1/2NNNNN1 w - - 0 1")
        board.push_san("e4")
        board.push_san("fxe3")
        self.assertEqual(board.fen(), "3kK3/8/8/2NNNNN1/2N3N1/2N3N1/2N3N1/2NNNNN1 w - - 0 2")

    def test_atomic_insufficient_material(self):
        # Starting position.
        board = chess.variant.AtomicBoard()
        self.assertFalse(board.is_insufficient_material())

        # Single rook.
        board = chess.variant.AtomicBoard("8/3k4/8/8/4R3/4K3/8/8 w - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # Only bishops, but no captures possible.
        board = chess.variant.AtomicBoard("7k/4b3/8/8/8/3B4/2B5/K7 w - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # Bishops of both sides on the same color complex.
        board = chess.variant.AtomicBoard("7k/3b4/8/8/8/3B4/2B5/K7 w - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Knights on both sides.
        board = chess.variant.AtomicBoard("8/1n6/1k6/8/8/8/3KN3/8 w - - 0 1")
        self.assertFalse(board.is_insufficient_material())

        # Two knights can not win.
        board = chess.variant.AtomicBoard("8/1nn5/1k6/8/8/8/3K4/8 w - - 0 1")
        self.assertTrue(board.is_insufficient_material())

        # KQN can win (even KQ could).
        board = chess.variant.AtomicBoard("3Q4/5kKB/8/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_insufficient_material())

    def test_castling_uncovered_rank_attack(self):
        board = chess.variant.AtomicBoard("8/8/8/8/8/8/4k3/rR4KR w KQ - 0 1", chess960=True)
        self.assertFalse(board.is_legal(chess.Move.from_uci("g1b1")))

        # Kings are touching at the end.
        board = chess.variant.AtomicBoard("8/8/8/8/8/8/2k5/rR4KR w KQ - 0 1", chess960=True)
        self.assertTrue(board.is_legal(chess.Move.from_uci("g1b1")))

    def test_atomic_castle_with_kings_touching(self):
        board = chess.variant.AtomicBoard("5b1r/1p5p/4ppp1/4Bn2/1PPP1PP1/4P2P/3k4/4K2R w K - 1 1")
        board.push_san("O-O")
        self.assertEqual(board.fen(), "5b1r/1p5p/4ppp1/4Bn2/1PPP1PP1/4P2P/3k4/5RK1 b - - 2 1")

        board = chess.variant.AtomicBoard("8/8/8/8/8/8/4k3/R3K2q w Q - 0 1")
        board.push_san("O-O-O")
        self.assertEqual(board.fen(), "8/8/8/8/8/8/4k3/2KR3q b - - 1 1")

        board = chess.variant.AtomicBoard("8/8/8/8/8/8/5k2/R3K2r w Q - 0 1")
        with self.assertRaises(chess.IllegalMoveError):
            board.push_san("O-O-O")

        board = chess.variant.AtomicBoard("8/8/8/8/8/8/6k1/R5Kr w Q - 0 1", chess960=True)
        with self.assertRaises(chess.IllegalMoveError):
            board.push_san("O-O-O")

        board = chess.variant.AtomicBoard("8/8/8/8/8/8/4k3/r2RK2r w D - 0 1", chess960=True)
        with self.assertRaises(chess.IllegalMoveError):
            board.push_san("O-O-O")

    def test_castling_rights_explode_with_king(self):
        board = chess.variant.AtomicBoard("rnb1kbnr/pppppppp/8/4q3/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1")
        board.push_san("Qxe2#")
        self.assertEqual(board.fen(), "rnb1kbnr/pppppppp/8/8/8/8/PPPP1PPP/RNB3NR w kq - 0 2")
        self.assertEqual(board.castling_rights, chess.BB_A8 | chess.BB_H8)

    def test_lone_king_wdl(self):
        tables = chess.syzygy.Tablebase(VariantBoard=chess.variant.AtomicBoard)
        board = chess.variant.AtomicBoard.empty()
        board.set_piece_at(chess.D1, chess.Piece.from_symbol("k"))
        self.assertEqual(tables.probe_wdl(board), -2)

    def test_atomic_validity(self):
        # 14 checkers, the maximum in Atomic chess.
        board = chess.variant.AtomicBoard("3N1NB1/2N1Q1N1/3RkR2/2NP1PN1/3NKN2/8/8/n7 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_VALID)

    def test_atomic960(self):
        pgn = io.StringIO(textwrap.dedent("""\
            [Variant "Atomic"]
            [FEN "rkrbbnnq/pppppppp/8/8/8/8/PPPPPPPP/RKRBBNNQ w KQkq - 0 1"]

            1. g3 d5 2. Nf3 e5 3. Ng5 Bxg5 4. Qf3 Ne6 5. Qa3 a5 6. d4 g6 7. c3 h5 8. h4 Qh6 9. Bd2 Qxd2 10. O-O-O *
            """))
        game = chess.pgn.read_game(pgn)
        self.assertTrue(game.board().chess960)
        self.assertEqual(game.end().parent.board().fen(), "rkr1b1n1/1pp2p2/4n1p1/p2pp2p/3P3P/Q1P3P1/PP2PP2/RK3N2 w Qkq - 0 10")
        self.assertEqual(game.end().board().fen(), "rkr1b1n1/1pp2p2/4n1p1/p2pp2p/3P3P/Q1P3P1/PP2PP2/2KR1N2 b kq - 1 10")

    def test_atomic_king_exploded(self):
        board = chess.variant.AtomicBoard("rn5r/pp4pp/2p3Nn/5p2/1b2P1PP/8/PPP2P2/R1B1KB1R b KQ - 0 9")
        self.assertEqual(board.outcome().winner, chess.WHITE)
        self.assertEqual(board.status(), chess.STATUS_VALID)


class RacingKingsTestCase(unittest.TestCase):

    def test_variant_end(self):
        board = chess.variant.RacingKingsBoard()
        board.push_san("Nxc2")
        self.assertFalse(board.is_variant_draw())
        self.assertFalse(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())

        # Black is given a chance to catch up.
        board = chess.variant.RacingKingsBoard("1K6/7k/8/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_game_over())

        board.push_san("Kg7")  # ??
        self.assertFalse(board.is_variant_draw())
        self.assertTrue(board.is_variant_win())
        self.assertFalse(board.is_variant_loss())

        # White to move is lost, because black reached the backrank.
        board = chess.variant.RacingKingsBoard("1k6/6K1/8/8/8/8/8/8 w - - 0 1")
        self.assertFalse(board.is_variant_draw())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_loss())

        # Black to move is lost, because they cannot reach the backrank.
        board = chess.variant.RacingKingsBoard("5RK1/1k6/8/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_variant_draw())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_loss())

        # White far away.
        board = chess.variant.RacingKingsBoard("k1q1R2Q/3N4/8/8/5K2/6n1/1b6/1r6 w - - 4 19")
        self.assertTrue(board.is_variant_end())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertFalse(board.is_variant_draw())
        self.assertEqual(board.result(), "0-1")

        # Black near backrank, but cannot move there.
        board = chess.variant.RacingKingsBoard("2KR4/k7/2Q5/4q3/8/8/8/2N5 b - - 0 1")
        self.assertTrue(board.is_variant_end())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertFalse(board.is_variant_draw())
        self.assertEqual(board.result(), "1-0")

        # Black two moves away.
        board = chess.variant.RacingKingsBoard("1r4RK/6R1/k1r5/8/8/8/4N3/q2n1n2 b - - 0 1")
        self.assertTrue(board.is_variant_end())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertFalse(board.is_variant_draw())
        self.assertEqual(board.result(), "1-0")

        # Both sides already reached the backrank.
        board = chess.variant.RacingKingsBoard("kr3NK1/1q2R3/8/8/8/5n2/2N5/1rb2B1R w - - 11 14")
        self.assertTrue(board.is_variant_end())
        self.assertFalse(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_draw())
        self.assertEqual(board.result(), "1/2-1/2")

        # Another draw.
        board = chess.variant.RacingKingsBoard("1knq1RK1/2n5/8/8/3N4/6N1/6B1/8 w - - 23 25")
        self.assertTrue(board.is_variant_end())
        self.assertFalse(board.is_variant_loss())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_draw())
        self.assertEqual(board.result(), "1/2-1/2")

    def test_stalemate(self):
        board = chess.variant.RacingKingsBoard("1Q4R1/5K2/4B3/8/8/3N4/8/k7 b - - 0 1")
        self.assertTrue(board.is_game_over())
        self.assertTrue(board.is_stalemate())
        self.assertFalse(board.is_variant_win())
        self.assertFalse(board.is_variant_draw())
        self.assertFalse(board.is_variant_loss())
        self.assertEqual(board.result(), "1/2-1/2")

        # Here white already reached the backrank.
        board = chess.variant.RacingKingsBoard("4Q1K1/8/7k/4R3/8/5B2/8/3N4 b - - 0 1")
        self.assertTrue(board.is_game_over())
        self.assertFalse(board.is_stalemate())
        self.assertFalse(board.is_variant_win())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_variant_draw())
        self.assertEqual(board.result(), "1-0")

    def test_race_over(self):
        self.assertTrue(chess.variant.RacingKingsBoard().is_valid())

        # This position with black to move and both kings on the backrank is
        # invalid because the race should have been over already.
        board = chess.variant.RacingKingsBoard("3krQK1/8/8/8/1q6/3B1N2/1b6/1R4R1 b - - 0 0")
        self.assertEqual(board.status(), chess.STATUS_RACE_OVER)

    def test_race_material(self):
        board = chess.variant.RacingKingsBoard()

        # Switch color of the black rook.
        board.set_piece_at(chess.B1, chess.Piece.from_symbol("R"))
        self.assertEqual(board.status(), chess.STATUS_RACE_MATERIAL)

    def test_legal_moves_after_end(self):
        board = chess.variant.RacingKingsBoard("1k5b/5b2/8/8/8/8/3N3K/N4B2 w - - 0 1")
        self.assertTrue(board.is_variant_end())
        self.assertTrue(board.is_variant_loss())
        self.assertFalse(board.is_stalemate())
        self.assertFalse(any(board.generate_legal_moves()))

    def test_racing_kings_status_with_check(self):
        board = chess.variant.RacingKingsBoard("8/8/8/8/R7/8/krbnNB1K/qrbnNBRQ b - - 1 1")
        self.assertFalse(board.is_valid())
        self.assertEqual(board.status(), chess.STATUS_RACE_CHECK | chess.STATUS_TOO_MANY_CHECKERS | chess.STATUS_IMPOSSIBLE_CHECK)


class HordeTestCase(unittest.TestCase):

    def test_status(self):
        board = chess.variant.HordeBoard()
        self.assertEqual(board.status(), chess.STATUS_VALID)

        # Black (non-horde) piece on first rank.
        board = chess.variant.HordeBoard("rnb1kbnr/ppp1pppp/2Pp2PP/1P3PPP/PPP1PPPP/PPP1PPPP/PPP1PPP1/PPPqPP2 w kq - 0 1")
        self.assertEqual(board.status(), chess.STATUS_VALID)

    def test_double_pawn_push(self):
        board = chess.variant.HordeBoard("8/8/8/8/8/3k1p2/8/PPPPPPPP w - - 0 1")

        # Double pawn push blocked by king.
        self.assertNotIn(chess.Move.from_uci("d1d3"), board.generate_legal_moves())

        # Double pawn push from backrank possible.
        self.assertIn(chess.Move.from_uci("e1e2"), board.generate_legal_moves())
        self.assertTrue(board.is_legal(board.parse_san("e2")))
        self.assertIn(chess.Move.from_uci("e1e3"), board.generate_legal_moves())
        self.assertTrue(board.is_legal(board.parse_san("e3")))

        # En passant not possible.
        board.push_san("e3")
        self.assertFalse(any(board.generate_pseudo_legal_ep()))

class CrazyhouseTestCase(unittest.TestCase):

    def test_pawn_drop(self):
        board = chess.variant.CrazyhouseBoard("r2q1rk1/ppp2pp1/1bnp3p/3B4/3PP1b1/4PN2/PP4PP/R2Q1RK1[BNPnp] b - - 0 13")
        P_at_e6 = chess.Move.from_uci("P@e6")
        self.assertIn(chess.E6, board.legal_drop_squares())
        self.assertIn(P_at_e6, board.generate_legal_moves())
        self.assertTrue(board.is_pseudo_legal(P_at_e6))
        self.assertTrue(board.is_legal(P_at_e6))
        self.assertEqual(board.uci(P_at_e6), "P@e6")
        self.assertEqual(board.san(P_at_e6), "@e6")

    def test_lichess_pgn(self):
        with open("data/pgn/saturs-jannlee-zh-lichess.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            final_board = game.end().board()
            self.assertEqual(final_board.fen(), "r4r2/ppp2ppk/pb1p1pNp/K2NpP2/3qn3/1B3b2/PP5P/8[QRRBNPP] w - - 8 62")
            self.assertTrue(final_board.is_valid())

        with open("data/pgn/knightvuillaume-jannlee-zh-lichess.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.end().board().move_stack[23], chess.Move.from_uci("N@f3"))

    def test_pawns_in_pocket(self):
        board = chess.variant.CrazyhouseBoard("r2q1rk1/ppp2pp1/1bnp3p/3Bp3/4P1b1/2PPPN2/PP4PP/R2Q1RK1/NBn w - - 22 12")
        board.push_san("d4")
        board.push_san("exd4")
        board.push_san("cxd4")
        self.assertEqual(board.fen(), "r2q1rk1/ppp2pp1/1bnp3p/3B4/3PP1b1/4PN2/PP4PP/R2Q1RK1[BNPnp] b - - 0 13")
        board.push_san("@e6")
        self.assertEqual(board.fen(), "r2q1rk1/ppp2pp1/1bnpp2p/3B4/3PP1b1/4PN2/PP4PP/R2Q1RK1[BNPn] w - - 1 14")

    def test_capture(self):
        board = chess.variant.CrazyhouseBoard("4k3/8/8/1n6/8/3B4/8/4K3 w - - 0 1")
        board.push_san("Bxb5+")
        self.assertEqual(board.fen(), "4k3/8/8/1B6/8/8/8/4K3[N] b - - 0 1")
        board.pop()
        self.assertEqual(board.fen(), "4k3/8/8/1n6/8/3B4/8/4K3[] w - - 0 1")

    def test_capture_with_promotion(self):
        board = chess.variant.CrazyhouseBoard("4k3/8/8/8/8/8/1p6/2R1K3 b - - 0 1")
        move = board.parse_san("bxc1=Q")
        self.assertFalse(board.is_irreversible(move))
        board.push(move)
        self.assertEqual(board.fen(), "4k3/8/8/8/8/8/8/2q~1K3[r] w - - 0 2")
        board.pop()
        self.assertEqual(board.fen(), "4k3/8/8/8/8/8/1p6/2R1K3[] b - - 0 1")

    def test_illegal_drop_uci(self):
        board = chess.variant.CrazyhouseBoard()
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_uci("N@f3")

    def test_crazyhouse_fen(self):
        fen = "r3kb1r/p1pN1ppp/2p1p3/8/2Pn4/3Q4/PP3PPP/R1B2q~K1[] w kq - 0 1"
        board = chess.variant.CrazyhouseBoard(fen)
        self.assertEqual(board.fen(), fen)

    def test_push_pop_ep(self):
        fen = "rnbqkb1r/ppp1pppp/5n2/3pP3/8/8/PPPP1PPP/RNBQKBNR[] w KQkq d6 0 3"
        board = chess.variant.CrazyhouseBoard(fen)
        board.push_san("exd6")
        self.assertEqual(board.fen(), "rnbqkb1r/ppp1pppp/3P1n2/8/8/8/PPPP1PPP/RNBQKBNR[P] b KQkq - 0 3")
        self.assertEqual(board.pop(), chess.Move.from_uci("e5d6"))
        self.assertEqual(board.fen(), fen)

    def test_crazyhouse_insufficient_material(self):
        board = chess.variant.CrazyhouseBoard()
        self.assertFalse(board.is_insufficient_material())

        board = chess.variant.CrazyhouseBoard.empty()
        self.assertTrue(board.is_insufficient_material())

        board.pockets[chess.WHITE].add(chess.PAWN)
        self.assertFalse(board.is_insufficient_material())

    def test_mirror_pockets(self):
        fen = "r1b1k2r/p1pq1ppp/1bBbnp2/8/6N1/5P2/PPP2PPP/R4RK1/PQPPNn w kq - 30 16"
        board = chess.variant.CrazyhouseBoard(fen)
        self.assertEqual(board, board.mirror().mirror())

    def test_root_pockets(self):
        board = chess.variant.CrazyhouseBoard("r2B1rk1/ppp2ppp/3p4/4p3/2B5/2NP1R1P/PPPn2K1/8/QPBQPRNNbp w - - 40 21")
        white_pocket = "qqrbnnpp"
        black_pocket = "bp"
        self.assertEqual(str(board.root().pockets[chess.WHITE]), white_pocket)
        self.assertEqual(str(board.root().pockets[chess.BLACK]), black_pocket)
        self.assertEqual(str(board.copy().root().pockets[chess.WHITE]), white_pocket)
        self.assertEqual(str(board.copy().root().pockets[chess.BLACK]), black_pocket)

        board.push_san("N@h6+")
        board.push_san("Kh8")
        board.push_san("R@g8+")
        board.push_san("Rxg8")
        board.push_san("Nxf7#")
        self.assertEqual(str(board.root().pockets[chess.WHITE]), white_pocket)
        self.assertEqual(str(board.root().pockets[chess.BLACK]), black_pocket)
        self.assertEqual(str(board.copy().root().pockets[chess.WHITE]), white_pocket)
        self.assertEqual(str(board.copy().root().pockets[chess.BLACK]), black_pocket)

    def test_zh_is_irreversible(self):
        board = chess.variant.CrazyhouseBoard("r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1")
        self.assertTrue(board.is_irreversible(board.parse_san("Ra2")))
        self.assertTrue(board.is_irreversible(board.parse_san("O-O-O")))
        self.assertTrue(board.is_irreversible(board.parse_san("Kd1")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxa8")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxh8")))
        self.assertFalse(board.is_irreversible(board.parse_san("Rf1")))
        self.assertFalse(board.is_irreversible(chess.Move.null()))


class GiveawayTestCase(unittest.TestCase):

    def test_antichess_pgn(self):
        with open("data/pgn/antichess-programfox.pgn") as pgn:
            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.end().board().fen(), "8/2k5/8/8/8/8/6b1/8 w - - 0 32")

            game = chess.pgn.read_game(pgn)
            self.assertEqual(game.end().board().fen(), "8/6k1/3K4/8/8/3k4/8/8 w - - 4 33")

