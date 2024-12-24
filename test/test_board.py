import unittest

import textwrap

import chess
import chess.gaviota
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant

class BoardTestCase(unittest.TestCase):

    def test_default_position(self):
        board = chess.Board()
        self.assertEqual(board.piece_at(chess.B1), chess.Piece.from_symbol("N"))
        self.assertEqual(board.fen(), chess.STARTING_FEN)
        self.assertEqual(board.turn, chess.WHITE)

    def test_empty(self):
        board = chess.Board.empty()
        self.assertEqual(board.fen(), "8/8/8/8/8/8/8/8 w - - 0 1")
        self.assertEqual(board, chess.Board(None))

    def test_ply(self):
        board = chess.Board()
        self.assertEqual(board.ply(), 0)
        board.push_san("d4")
        self.assertEqual(board.ply(), 1)
        board.push_san("d5")
        self.assertEqual(board.ply(), 2)
        board.clear_stack()
        self.assertEqual(board.ply(), 2)
        board.push_san("Nf3")
        self.assertEqual(board.ply(), 3)

    def test_from_epd(self):
        base_epd = "rnbqkb1r/ppp1pppp/5n2/3P4/8/8/PPPP1PPP/RNBQKBNR w KQkq -"
        board, ops = chess.Board.from_epd(base_epd + " ce 55;")
        self.assertEqual(ops["ce"], 55)
        self.assertEqual(board.fen(), base_epd + " 0 1")

    def test_move_making(self):
        board = chess.Board()
        move = chess.Move(chess.E2, chess.E4)
        board.push(move)
        self.assertEqual(board.peek(), move)

    def test_fen(self):
        board = chess.Board()
        self.assertEqual(board.fen(), chess.STARTING_FEN)

        fen = "6k1/pb3pp1/1p2p2p/1Bn1P3/8/5N2/PP1q1PPP/6K1 w - - 0 24"
        board.set_fen(fen)
        self.assertEqual(board.fen(), fen)

        board.push(chess.Move.from_uci("f3d2"))
        self.assertEqual(board.fen(), "6k1/pb3pp1/1p2p2p/1Bn1P3/8/8/PP1N1PPP/6K1 b - - 0 24")

    def test_xfen(self):
        # https://de.wikipedia.org/wiki/Forsyth-Edwards-Notation#Beispiel
        xfen = "rn2k1r1/ppp1pp1p/3p2p1/5bn1/P7/2N2B2/1PPPPP2/2BNK1RR w Gkq - 4 11"
        board = chess.Board(xfen, chess960=True)
        self.assertEqual(board.castling_rights, chess.BB_G1 | chess.BB_A8 | chess.BB_G8)
        self.assertEqual(board.clean_castling_rights(), chess.BB_G1 | chess.BB_A8 | chess.BB_G8)
        self.assertEqual(board.shredder_fen(), "rn2k1r1/ppp1pp1p/3p2p1/5bn1/P7/2N2B2/1PPPPP2/2BNK1RR w Gga - 4 11")
        self.assertEqual(board.fen(), xfen)
        self.assertTrue(board.has_castling_rights(chess.WHITE))
        self.assertTrue(board.has_castling_rights(chess.BLACK))
        self.assertTrue(board.has_kingside_castling_rights(chess.BLACK))
        self.assertTrue(board.has_kingside_castling_rights(chess.WHITE))
        self.assertTrue(board.has_queenside_castling_rights(chess.BLACK))
        self.assertFalse(board.has_queenside_castling_rights(chess.WHITE))

        # Chess960 position #284.
        board = chess.Board("rkbqrbnn/pppppppp/8/8/8/8/PPPPPPPP/RKBQRBNN w - - 0 1", chess960=True)
        board.castling_rights = board.rooks
        self.assertTrue(board.clean_castling_rights() & chess.BB_A1)
        self.assertEqual(board.fen(), "rkbqrbnn/pppppppp/8/8/8/8/PPPPPPPP/RKBQRBNN w KQkq - 0 1")
        self.assertEqual(board.shredder_fen(), "rkbqrbnn/pppppppp/8/8/8/8/PPPPPPPP/RKBQRBNN w EAea - 0 1")

        # Valid en passant square on illegal board.
        fen = "8/8/8/pP6/8/8/8/8 w - a6 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.fen(), fen)

        # Illegal en passant square on illegal board.
        fen = "1r6/8/8/pP6/8/8/8/1K6 w - a6 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.fen(), "1r6/8/8/pP6/8/8/8/1K6 w - - 0 1")

    def test_fen_en_passant(self):
        board = chess.Board()
        board.push_san("e4")
        self.assertEqual(board.fen(en_passant="fen"), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        self.assertEqual(board.fen(en_passant="xfen"), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")

    def test_get_set(self):
        board = chess.Board()
        self.assertEqual(board.piece_at(chess.B1), chess.Piece.from_symbol("N"))

        board.remove_piece_at(chess.E2)
        self.assertEqual(board.piece_at(chess.E2), None)

        board.set_piece_at(chess.E4, chess.Piece.from_symbol("r"))
        self.assertEqual(board.piece_type_at(chess.E4), chess.ROOK)

        board.set_piece_at(chess.F1, None)
        self.assertEqual(board.piece_at(chess.F1), None)

        board.set_piece_at(chess.H7, chess.Piece.from_symbol("Q"), promoted=True)
        self.assertEqual(board.promoted, chess.BB_H7)

        board.set_piece_at(chess.H7, None)
        self.assertEqual(board.promoted, chess.BB_EMPTY)
        self.assertEqual(board.piece_at(chess.H7), None)

    def test_color_at(self):
        board = chess.Board()
        self.assertEqual(board.color_at(chess.A1), chess.WHITE)
        self.assertEqual(board.color_at(chess.G7), chess.BLACK)
        self.assertEqual(board.color_at(chess.E4), None)

    def test_pawn_captures(self):
        board = chess.Board()

        # King's Gambit.
        board.push(chess.Move.from_uci("e2e4"))
        board.push(chess.Move.from_uci("e7e5"))
        board.push(chess.Move.from_uci("f2f4"))

        # Accepted.
        exf4 = chess.Move.from_uci("e5f4")
        self.assertIn(exf4, board.pseudo_legal_moves)
        self.assertIn(exf4, board.legal_moves)
        board.push(exf4)
        board.pop()

    def test_pawn_move_generation(self):
        board = chess.Board("8/2R1P3/8/2pp4/2k1r3/P7/8/1K6 w - - 1 55")
        self.assertEqual(len(list(board.generate_pseudo_legal_moves())), 16)

    def test_single_step_pawn_move(self):
        board = chess.Board()
        a3 = chess.Move.from_uci("a2a3")
        self.assertIn(a3, board.pseudo_legal_moves)
        self.assertIn(a3, board.legal_moves)
        board.push(a3)
        board.pop()
        self.assertEqual(board.fen(), chess.STARTING_FEN)

    def test_castling(self):
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

        # Let white castle short.
        move = board.parse_xboard("O-O")
        self.assertEqual(move, chess.Move.from_uci("e1g1"))
        self.assertEqual(board.san(move), "O-O")
        self.assertEqual(board.xboard(move), "e1g1")
        self.assertIn(move, board.legal_moves)
        board.push(move)

        # Let black castle long.
        move = board.parse_xboard("O-O-O")
        self.assertEqual(board.san(move), "O-O-O")
        self.assertEqual(board.xboard(move), "e8c8")
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.fen(), "2kr3r/8/8/8/8/8/8/R4RK1 w - - 3 2")

        # Undo both castling moves.
        board.pop()
        board.pop()
        self.assertEqual(board.fen(), "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

        # Let white castle long.
        move = board.parse_san("O-O-O")
        self.assertEqual(board.san(move), "O-O-O")
        self.assertIn(move, board.legal_moves)
        board.push(move)

        # Let black castle short.
        move = board.parse_san("O-O")
        self.assertEqual(board.san(move), "O-O")
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.fen(), "r4rk1/8/8/8/8/8/8/2KR3R w - - 3 2")

        # Undo both castling moves.
        board.pop()
        board.pop()
        self.assertEqual(board.fen(), "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 1 1")

    def test_castling_san(self):
        board = chess.Board("4k3/8/8/8/8/8/8/4K2R w K - 0 1")
        self.assertEqual(board.parse_san("O-O"), chess.Move.from_uci("e1g1"))
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_san("Kg1")
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_san("Kh1")

    def test_ninesixty_castling(self):
        fen = "3r1k1r/4pp2/8/8/8/8/8/4RKR1 w Gd - 1 1"
        board = chess.Board(fen, chess960=True)

        # Let white do the kingside swap.
        move = board.parse_san("O-O")
        self.assertEqual(board.san(move), "O-O")
        self.assertEqual(board.xboard(move), "O-O")
        self.assertEqual(move.from_square, chess.F1)
        self.assertEqual(move.to_square, chess.G1)
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.shredder_fen(), "3r1k1r/4pp2/8/8/8/8/8/4RRK1 b d - 2 1")

        # Black can not castle kingside.
        self.assertNotIn(chess.Move.from_uci("e8h8"), board.legal_moves)

        # Let black castle queenside.
        move = board.parse_san("O-O-O")
        self.assertEqual(board.san(move), "O-O-O")
        self.assertEqual(board.xboard(move), "O-O-O")
        self.assertEqual(move.from_square, chess.F8)
        self.assertEqual(move.to_square, chess.D8)
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.shredder_fen(), "2kr3r/4pp2/8/8/8/8/8/4RRK1 w - - 3 2")

        # Restore initial position.
        board.pop()
        board.pop()
        self.assertEqual(board.shredder_fen(), fen)

        fen = "Qr4k1/4pppp/8/8/8/8/8/R5KR w Hb - 0 1"
        board = chess.Board(fen, chess960=True)

        # White can just hop the rook over.
        move = board.parse_san("O-O")
        self.assertEqual(board.san(move), "O-O")
        self.assertEqual(move.from_square, chess.G1)
        self.assertEqual(move.to_square, chess.H1)
        self.assertIn(move, board.legal_moves)
        board.push(move)
        self.assertEqual(board.shredder_fen(), "Qr4k1/4pppp/8/8/8/8/8/R4RK1 b b - 1 1")

        # Black can not castle queenside nor kingside.
        self.assertFalse(any(board.generate_castling_moves()))

        # Restore initial position.
        board.pop()
        self.assertEqual(board.shredder_fen(), fen)

    def test_hside_rook_blocks_aside_castling(self):
        board = chess.Board("4rrk1/pbbp2p1/1ppnp3/3n1pqp/3N1PQP/1PPNP3/PBBP2P1/4RRK1 w Ff - 10 18", chess960=True)
        self.assertNotIn(chess.Move.from_uci("g1f1"), board.legal_moves)
        self.assertNotIn(chess.Move.from_uci("g1e1"), board.legal_moves)
        self.assertNotIn(chess.Move.from_uci("g1c1"), board.legal_moves)
        self.assertNotIn(chess.Move.from_uci("g1a1"), board.legal_moves)
        self.assertIn(chess.Move.from_uci("g1h1"), board.legal_moves)  # Kh1

    def test_selective_castling(self):
        board = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")

        # King not selected.
        self.assertFalse(any(board.generate_castling_moves(chess.BB_ALL & ~board.kings)))

        # Rook on h1 not selected.
        moves = board.generate_castling_moves(chess.BB_ALL, chess.BB_ALL & ~chess.BB_H1)
        self.assertEqual(len(list(moves)), 1)

    def test_castling_right_not_destroyed_bug(self):
        # A rook move from h8 to h1 was only taking white's possible castling
        # rights away.
        board = chess.Board("2r1k2r/2qbbpp1/p2pp3/1p3PP1/Pn2P3/1PN1B3/1P3QB1/1K1R3R b k - 0 22")
        board.push_san("Rxh1")
        self.assertEqual(board.epd(), "2r1k3/2qbbpp1/p2pp3/1p3PP1/Pn2P3/1PN1B3/1P3QB1/1K1R3r w - -")

    def test_invalid_castling_rights(self):
        # KQkq is not valid in this standard chess position.
        board = chess.Board("1r2k3/8/8/8/8/8/8/R3KR2 w KQkq - 0 1")
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)
        self.assertEqual(board.fen(), "1r2k3/8/8/8/8/8/8/R3KR2 w Q - 0 1")
        self.assertTrue(board.has_queenside_castling_rights(chess.WHITE))
        self.assertFalse(board.has_kingside_castling_rights(chess.WHITE))
        self.assertFalse(board.has_queenside_castling_rights(chess.BLACK))
        self.assertFalse(board.has_kingside_castling_rights(chess.BLACK))

        board = chess.Board("4k2r/8/8/8/8/8/8/R1K5 w KQkq - 0 1", chess960=True)
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)
        self.assertEqual(board.fen(), "4k2r/8/8/8/8/8/8/R1K5 w Qk - 0 1")

        board = chess.Board("1r2k3/8/1p6/8/8/5P2/8/1R2KR2 w KQkq - 0 1", chess960=True)
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)
        self.assertEqual(board.fen(), "1r2k3/8/1p6/8/8/5P2/8/1R2KR2 w KQq - 0 1")

    def test_ninesixty_different_king_and_rook_file(self):
        # Theoretically, this position (with castling rights) can not be reached
        # with a series of legal moves from one of the 960 starting positions.
        # Decision: We don't care, neither do Stockfish or lichess.org.
        fen = "1r1k1r2/5p2/8/8/8/8/3N4/R5KR b KQkq - 0 1"
        board = chess.Board(fen, chess960=True)
        self.assertEqual(board.fen(), fen)

    def test_ninesixty_prevented_castle(self):
        board = chess.Board("4k3/8/8/1b6/8/8/8/5RKR w KQ - 0 1", chess960=True)
        self.assertFalse(board.is_legal(chess.Move.from_uci("g1f1")))

    def test_find_move(self):
        board = chess.Board("4k3/1P6/8/8/8/8/3P4/4K2R w K - 0 1")

        # Pawn moves.
        self.assertEqual(board.find_move(chess.D2, chess.D4), chess.Move.from_uci("d2d4"))
        self.assertEqual(board.find_move(chess.B7, chess.B8), chess.Move.from_uci("b7b8q"))
        self.assertEqual(board.find_move(chess.B7, chess.B8, chess.KNIGHT), chess.Move.from_uci("b7b8n"))

        # Illegal moves.
        with self.assertRaises(chess.IllegalMoveError):
            board.find_move(chess.D2, chess.D8)
        with self.assertRaises(chess.IllegalMoveError):
            board.find_move(chess.E1, chess.A1)

        # Castling.
        self.assertEqual(board.find_move(chess.E1, chess.G1), chess.Move.from_uci("e1g1"))
        self.assertEqual(board.find_move(chess.E1, chess.H1), chess.Move.from_uci("e1g1"))
        board.chess960 = True
        self.assertEqual(board.find_move(chess.E1, chess.H1), chess.Move.from_uci("e1h1"))

    def test_clean_castling_rights(self):
        board = chess.Board()
        board.set_board_fen("k6K/8/8/pppppppp/8/8/8/QqQq4")
        self.assertEqual(board.clean_castling_rights(), chess.BB_EMPTY)
        self.assertEqual(board.fen(), "k6K/8/8/pppppppp/8/8/8/QqQq4 w - - 0 1")
        board.push_san("Qxc5")
        self.assertEqual(board.clean_castling_rights(), chess.BB_EMPTY)
        self.assertEqual(board.fen(), "k6K/8/8/ppQppppp/8/8/8/Qq1q4 b - - 0 1")

    def test_insufficient_material(self):
        def _check(board, white, black):
            self.assertEqual(board.has_insufficient_material(chess.WHITE), white)
            self.assertEqual(board.has_insufficient_material(chess.BLACK), black)
            self.assertEqual(board.is_insufficient_material(), white and black)

        # Imperfect implementation.
        false_negative = False

        _check(chess.Board(), False, False)
        _check(chess.Board("k1K1B1B1/8/8/8/8/8/8/8 w - - 7 32"), True, True)
        _check(chess.Board("kbK1B1B1/8/8/8/8/8/8/8 w - - 7 32"), False, False)
        _check(chess.Board("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), True, True)
        _check(chess.Board("8/3k4/8/8/2N5/8/3K4/8 b - - 0 1"), True, True)
        _check(chess.Board("8/4rk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
        _check(chess.Board("8/4qk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
        _check(chess.Board("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
        _check(chess.Board("8/8/3Q4/2bK4/B7/8/1k6/8 w - - 1 68"), False, False)
        _check(chess.Board("8/5k2/8/8/8/4B3/3K1B2/8 w - - 0 1"), True, True)
        _check(chess.Board("5K2/8/8/1B6/8/k7/6b1/8 w - - 0 39"), True, True)
        _check(chess.Board("8/8/8/4k3/5b2/3K4/8/2B5 w - - 0 33"), True, True)
        _check(chess.Board("3b4/8/8/6b1/8/8/R7/K1k5 w - - 0 1"), False, True)

        _check(chess.variant.AtomicBoard("8/3k4/8/8/2N5/8/3K4/8 b - - 0 1"), True, True)
        _check(chess.variant.AtomicBoard("8/4rk2/8/8/8/8/3K4/8 w - - 0 1"), True, True)
        _check(chess.variant.AtomicBoard("8/4qk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
        _check(chess.variant.AtomicBoard("8/1k6/8/2n5/8/3NK3/8/8 b - - 0 1"), False, False)
        _check(chess.variant.AtomicBoard("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), True, True)
        _check(chess.variant.AtomicBoard("4b3/5k2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
        _check(chess.variant.AtomicBoard("3Q4/5kKB/8/8/8/8/8/8 b - - 0 1"), False, True)
        _check(chess.variant.AtomicBoard("8/5k2/8/8/8/8/5K2/4bb2 w - - 0 1"), True, False)
        _check(chess.variant.AtomicBoard("8/5k2/8/8/8/8/5K2/4nb2 w - - 0 1"), True, False)

        _check(chess.variant.GiveawayBoard("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
        _check(chess.variant.GiveawayBoard("4b3/5k2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
        _check(chess.variant.GiveawayBoard("8/8/8/6b1/8/3B4/4B3/5B2 w - - 0 1"), True, True)
        _check(chess.variant.GiveawayBoard("8/8/5b2/8/8/3B4/3B4/8 w - - 0 1"), True, False)
        _check(chess.variant.SuicideBoard("8/5p2/5P2/8/3B4/1bB5/8/8 b - - 0 1"), false_negative, false_negative)
        _check(chess.variant.AntichessBoard("8/8/8/1n2N3/8/8/8/8 w - - 0 32"), True, False)
        _check(chess.variant.AntichessBoard("8/3N4/8/1n6/8/8/8/8 b - - 1 32"), True, False)
        _check(chess.variant.AntichessBoard("6n1/8/8/4N3/8/8/8/8 b - - 0 27"), False, True)
        _check(chess.variant.AntichessBoard("8/8/5n2/4N3/8/8/8/8 w - - 1 28"), False, True)
        _check(chess.variant.AntichessBoard("8/3n4/8/8/8/8/8/8 w - - 0 29"), False, True)

        _check(chess.variant.KingOfTheHillBoard("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), False, False)

        _check(chess.variant.RacingKingsBoard("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), False, False)

        _check(chess.variant.ThreeCheckBoard("8/5k2/8/8/8/8/3K4/8 w - - 3+3 0 1"), True, True)
        _check(chess.variant.ThreeCheckBoard("8/5k2/8/8/8/8/3K2N1/8 w - - 3+3 0 1"), False, True)

        _check(chess.variant.CrazyhouseBoard("8/5k2/8/8/8/8/3K2N1/8[] w - - 0 1"), True, True)
        _check(chess.variant.CrazyhouseBoard("8/5k2/8/8/8/5B2/3KB3/8[] w - - 0 1"), False, False)
        _check(chess.variant.CrazyhouseBoard("8/8/8/8/3k4/3N~4/3K4/8 w - - 0 1"), False, False)

        _check(chess.variant.HordeBoard("8/5k2/8/8/8/4NN2/8/8 w - - 0 1"), True, False)
        _check(chess.variant.HordeBoard("8/1b5r/1P6/1Pk3q1/1PP5/r1P5/P1P5/2P5 b - - 0 52"), False, False)

    def test_promotion_with_check(self):
        board = chess.Board("8/6P1/2p5/1Pqk4/6P1/2P1RKP1/4P1P1/8 w - - 0 1")
        board.push(chess.Move.from_uci("g7g8q"))
        self.assertTrue(board.is_check())
        self.assertEqual(board.fen(), "6Q1/8/2p5/1Pqk4/6P1/2P1RKP1/4P1P1/8 b - - 0 1")

        board = chess.Board("8/8/8/3R1P2/8/2k2K2/3p4/r7 b - - 0 82")
        board.push_san("d1=Q+")
        self.assertEqual(board.fen(), "8/8/8/3R1P2/8/2k2K2/8/r2q4 w - - 0 83")

    def test_ambiguous_move(self):
        board = chess.Board("8/8/1n6/3R1P2/1n6/2k2K2/3p4/r6r b - - 0 82")
        with self.assertRaises(chess.AmbiguousMoveError):
            board.parse_san("Rf1")
        with self.assertRaises(chess.AmbiguousMoveError):
            board.parse_san("Nd5")

    def test_scholars_mate(self):
        board = chess.Board()

        e4 = chess.Move.from_uci("e2e4")
        self.assertIn(e4, board.legal_moves)
        board.push(e4)

        e5 = chess.Move.from_uci("e7e5")
        self.assertIn(e5, board.legal_moves)
        board.push(e5)

        Qf3 = chess.Move.from_uci("d1f3")
        self.assertIn(Qf3, board.legal_moves)
        board.push(Qf3)

        Nc6 = chess.Move.from_uci("b8c6")
        self.assertIn(Nc6, board.legal_moves)
        board.push(Nc6)

        Bc4 = chess.Move.from_uci("f1c4")
        self.assertIn(Bc4, board.legal_moves)
        board.push(Bc4)

        Rb8 = chess.Move.from_uci("a8b8")
        self.assertIn(Rb8, board.legal_moves)
        board.push(Rb8)

        self.assertFalse(board.is_check())
        self.assertFalse(board.is_checkmate())
        self.assertFalse(board.is_game_over())
        self.assertFalse(board.is_stalemate())

        Qf7_mate = chess.Move.from_uci("f3f7")
        self.assertIn(Qf7_mate, board.legal_moves)
        board.push(Qf7_mate)

        self.assertTrue(board.is_check())
        self.assertTrue(board.is_checkmate())
        self.assertTrue(board.is_game_over())
        self.assertTrue(board.is_game_over(claim_draw=True))
        self.assertFalse(board.is_stalemate())

        self.assertEqual(board.fen(), "1rbqkbnr/pppp1Qpp/2n5/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQk - 0 4")

    def test_result(self):
        # Undetermined.
        board = chess.Board()
        self.assertEqual(board.result(claim_draw=True), "*")

        # White checkmated.
        board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        self.assertEqual(board.result(claim_draw=True), "0-1")

        # Stalemate.
        board = chess.Board("7K/7P/7k/8/6q1/8/8/8 w - - 0 1")
        self.assertEqual(board.result(), "1/2-1/2")

        # Insufficient material.
        board = chess.Board("4k3/8/8/8/8/5B2/8/4K3 w - - 0 1")
        self.assertEqual(board.result(), "1/2-1/2")

        # Fiftyseven-move rule.
        board = chess.Board("4k3/8/6r1/8/8/8/2R5/4K3 w - - 369 1")
        self.assertEqual(board.result(), "1/2-1/2")

        # Fifty-move rule.
        board = chess.Board("4k3/8/6r1/8/8/8/2R5/4K3 w - - 120 1")
        self.assertEqual(board.result(), "*")
        self.assertEqual(board.result(claim_draw=True), "1/2-1/2")

    def test_san(self):
        # Castling with check.
        fen = "rnbk1b1r/ppp2pp1/5n1p/4p1B1/2P5/2N5/PP2PPPP/R3KBNR w KQ - 0 7"
        board = chess.Board(fen)
        long_castle_check = chess.Move.from_uci("e1a1")
        self.assertEqual(board.san(long_castle_check), "O-O-O+")
        self.assertEqual(board.fen(), fen)

        # En passant mate.
        fen = "6bk/7b/8/3pP3/8/8/8/Q3K3 w - d6 0 2"
        board = chess.Board(fen)
        fxe6_mate_ep = chess.Move.from_uci("e5d6")
        self.assertEqual(board.san(fxe6_mate_ep), "exd6#")
        self.assertEqual(board.fen(), fen)

        # Test disambiguation.
        fen = "N3k2N/8/8/3N4/N4N1N/2R5/1R6/4K3 w - - 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.san(chess.Move.from_uci("e1f1")), "Kf1")
        self.assertEqual(board.san(chess.Move.from_uci("c3c2")), "Rcc2")
        self.assertEqual(board.san(chess.Move.from_uci("b2c2")), "Rbc2")
        self.assertEqual(board.san(chess.Move.from_uci("a4b6")), "N4b6")
        self.assertEqual(board.san(chess.Move.from_uci("h8g6")), "N8g6")
        self.assertEqual(board.san(chess.Move.from_uci("h4g6")), "Nh4g6")
        self.assertEqual(board.fen(), fen)

        # Test a bug where shakmaty used overly specific disambiguation.
        fen = "8/2KN1p2/5p2/3N1B1k/5PNp/7P/7P/8 w - -"
        board = chess.Board(fen)
        self.assertEqual(board.san(chess.Move.from_uci("d5f6")), "N5xf6#")

        # Do not disambiguate illegal alternatives.
        fen = "8/8/8/R2nkn2/8/8/2K5/8 b - - 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.san(chess.Move.from_uci("f5e3")), "Ne3+")
        self.assertEqual(board.fen(), fen)

        # Promotion.
        fen = "7k/1p2Npbp/8/2P5/1P1r4/3b2QP/3q1pPK/2RB4 b - - 1 29"
        board = chess.Board(fen)
        self.assertEqual(board.san(chess.Move.from_uci("f2f1q")), "f1=Q")
        self.assertEqual(board.san(chess.Move.from_uci("f2f1n")), "f1=N+")
        self.assertEqual(board.fen(), fen)

    def test_lan(self):
        # Normal moves always with origin square.
        fen = "N3k2N/8/8/3N4/N4N1N/2R5/1R6/4K3 w - - 0 1"
        board = chess.Board(fen)
        self.assertEqual(board.lan(chess.Move.from_uci("e1f1")), "Ke1-f1")
        self.assertEqual(board.lan(chess.Move.from_uci("c3c2")), "Rc3-c2")
        self.assertEqual(board.lan(chess.Move.from_uci("a4c5")), "Na4-c5")
        self.assertEqual(board.fen(), fen)

        # Normal capture.
        fen = "rnbq1rk1/ppp1bpp1/4pn1p/3p2B1/2PP4/2N1PN2/PP3PPP/R2QKB1R w KQ - 0 7"
        board = chess.Board(fen)
        self.assertEqual(board.lan(chess.Move.from_uci("g5f6")), "Bg5xf6")
        self.assertEqual(board.fen(), fen)

        # Pawn captures and moves.
        fen = "6bk/7b/8/3pP3/8/8/8/Q3K3 w - d6 0 2"
        board = chess.Board(fen)
        self.assertEqual(board.lan(chess.Move.from_uci("e5d6")), "e5xd6#")
        self.assertEqual(board.lan(chess.Move.from_uci("e5e6")), "e5-e6+")
        self.assertEqual(board.fen(), fen)

    def test_san_newline(self):
        board = chess.Board("rnbqk2r/ppppppbp/5np1/8/8/5NP1/PPPPPPBP/RNBQK2R w KQkq - 2 4")
        with self.assertRaises(chess.InvalidMoveError):
            board.parse_san("O-O\n")
        with self.assertRaises(chess.InvalidMoveError):
            board.parse_san("Nc3\n")

    def test_pawn_capture_san_without_file(self):
        board = chess.Board("2rq1rk1/pb2bppp/1p2p3/n1ppPn2/2PP4/PP3N2/1B1NQPPP/RB3RK1 b - - 4 13")
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_san("c4")
        board = chess.Board("4k3/8/8/4Pp2/8/8/8/4K3 w - f6 0 2")
        with self.assertRaises(chess.IllegalMoveError):
            board.parse_san("f6")

    def test_variation_san(self):
        board = chess.Board()
        self.assertEqual('1. e4 e5 2. Nf3',
                         board.variation_san([chess.Move.from_uci(m) for m in
                                              ['e2e4', 'e7e5', 'g1f3']]))
        self.assertEqual('1. e4 e5 2. Nf3 Nc6 3. Bb5 a6',
                         board.variation_san([chess.Move.from_uci(m) for m in
                                              ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6']]))

        fen = "rn1qr1k1/1p2bppp/p3p3/3pP3/P2P1B2/2RB1Q1P/1P3PP1/R5K1 w - - 0 19"
        board = chess.Board(fen)
        variation = ['d3h7', 'g8h7', 'f3h5', 'h7g8', 'c3g3', 'e7f8', 'f4g5',
                     'e8e7', 'g5f6', 'b8d7', 'h5h6', 'd7f6', 'e5f6', 'g7g6',
                     'f6e7', 'f8e7']
        var_w = board.variation_san([chess.Move.from_uci(m) for m in variation])
        self.assertEqual(("19. Bxh7+ Kxh7 20. Qh5+ Kg8 21. Rg3 Bf8 22. Bg5 Re7 "
                          "23. Bf6 Nd7 24. Qh6 Nxf6 25. exf6 g6 26. fxe7 Bxe7"),
                         var_w)
        self.assertEqual(fen, board.fen(), msg="Board unchanged by variation_san")
        board.push(chess.Move.from_uci(variation.pop(0)))
        var_b = board.variation_san([chess.Move.from_uci(m) for m in variation])
        self.assertEqual(("19...Kxh7 20. Qh5+ Kg8 21. Rg3 Bf8 22. Bg5 Re7 "
                          "23. Bf6 Nd7 24. Qh6 Nxf6 25. exf6 g6 26. fxe7 Bxe7"),
                         var_b)

        illegal_variation = ['d3h7', 'g8h7', 'f3h6', 'h7g8']
        board = chess.Board(fen)
        with self.assertRaises(chess.IllegalMoveError) as err:
            board.variation_san([chess.Move.from_uci(m) for m in illegal_variation])
        message = str(err.exception)
        self.assertIn('illegal move', message.lower(),
                      msg=f"Error [{message}] mentions illegal move")
        self.assertIn('f3h6', message,
                      msg=f"Illegal move f3h6 appears in message [{message}]")

    def test_move_stack_usage(self):
        board = chess.Board()
        board.push_uci("d2d4")
        board.push_uci("d7d5")
        board.push_uci("g1f3")
        board.push_uci("c8f5")
        board.push_uci("e2e3")
        board.push_uci("e7e6")
        board.push_uci("f1d3")
        board.push_uci("f8d6")
        board.push_uci("e1h1")
        san = chess.Board().variation_san(board.move_stack)
        self.assertEqual(san, "1. d4 d5 2. Nf3 Bf5 3. e3 e6 4. Bd3 Bd6 5. O-O")

    def test_is_legal_move(self):
        fen = "3k4/6P1/7P/8/K7/8/8/4R3 w - - 0 1"
        board = chess.Board(fen)

        # Legal moves: Rg1, g8=R+.
        self.assertIn(chess.Move.from_uci("e1g1"), board.legal_moves)
        self.assertIn(chess.Move.from_uci("g7g8r"), board.legal_moves)

        # Impossible promotion: Kb5, h7.
        self.assertNotIn(chess.Move.from_uci("a5b5q"), board.legal_moves)
        self.assertNotIn(chess.Move.from_uci("h6h7n"), board.legal_moves)

        # Missing promotion.
        self.assertNotIn(chess.Move.from_uci("g7g8"), board.legal_moves)

        # Promote to pawn or king.
        self.assertFalse(board.is_legal(chess.Move.from_uci("g7g8p")))
        self.assertFalse(board.is_pseudo_legal(chess.Move.from_uci("g7g8p")))
        self.assertFalse(board.is_legal(chess.Move.from_uci("g7g8k")))
        self.assertFalse(board.is_pseudo_legal(chess.Move.from_uci("g7g8k")))

        self.assertEqual(board.fen(), fen)

    def test_move_count(self):
        board = chess.Board("1N2k3/P7/8/8/3n4/8/2PP4/R3K2R w KQ - 0 1")
        self.assertEqual(board.pseudo_legal_moves.count(), 8 + 4 + 3 + 2 + 1 + 6 + 9)

    def test_polyglot(self):
        # Test Polyglot compatibility using test data from
        # http://hardy.uhasselt.be/Toga/book_format.html. Forfeiting castling
        # rights should not reset the half-move counter, though.

        board = chess.Board()
        self.assertEqual(board.fen(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x463b96181691fc9c)

        board.push_san("e4")
        self.assertEqual(board.fen(), "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x823c9b50fd114196)

        board.push_san("d5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x0756b94461c50fb0)

        board.push_san("e5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x662fafb965db29d4)

        board.push_san("f5")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x22a48b5a8e47ff78)

        board.push_san("Ke2")
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR b kq - 1 3")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x652a607ca3f242c1)

        board.push_san("Kf7")
        self.assertEqual(board.fen(), "rnbq1bnr/ppp1pkpp/8/3pPp2/8/8/PPPPKPPP/RNBQ1BNR w - - 2 4")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x00fdd303c946bdd9)

        board = chess.Board()
        board.push_san("a4")
        board.push_san("b5")
        board.push_san("h4")
        board.push_san("b4")
        board.push_san("c4")
        self.assertEqual(board.fen(), "rnbqkbnr/p1pppppp/8/8/PpP4P/8/1P1PPPP1/RNBQKBNR b KQkq c3 0 3")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x3c8123ea7b067637)

        board.push_san("bxc3")
        board.push_san("Ra3")
        self.assertEqual(board.fen(), "rnbqkbnr/p1pppppp/8/8/P6P/R1p5/1P1PPPP1/1NBQKBNR b Kkq - 1 4")
        self.assertEqual(chess.polyglot.zobrist_hash(board), 0x5c3f9b829b279560)

    def test_castling_move_generation_bug(self):
        # Specific test position right after castling.
        fen = "rnbqkbnr/2pp1ppp/8/4p3/2BPP3/P1N2N2/PB3PPP/2RQ1RK1 b kq - 1 10"
        board = chess.Board(fen)
        illegal_move = chess.Move.from_uci("g1g2")
        self.assertNotIn(illegal_move, board.legal_moves)
        self.assertNotIn(illegal_move, list(board.legal_moves))
        self.assertNotIn(illegal_move, board.pseudo_legal_moves)
        self.assertNotIn(illegal_move, list(board.pseudo_legal_moves))

        # Make a move.
        board.push_san("exd4")

        # Already castled short, can not castle long.
        illegal_move = chess.Move.from_uci("e1c1")
        self.assertNotIn(illegal_move, board.pseudo_legal_moves)
        self.assertNotIn(illegal_move, board.generate_pseudo_legal_moves())
        self.assertNotIn(illegal_move, board.legal_moves)
        self.assertNotIn(illegal_move, list(board.legal_moves))

        # Unmake the move.
        board.pop()

        # Generate all pseudo-legal moves, two moves deep.
        for move in board.pseudo_legal_moves:
            board.push(move)
            for move in board.pseudo_legal_moves:
                board.push(move)
                board.pop()
            board.pop()

        # Check that board is still consistent.
        self.assertEqual(board.fen(), fen)
        self.assertTrue(board.kings & chess.BB_G1)
        self.assertTrue(board.occupied & chess.BB_G1)
        self.assertTrue(board.occupied_co[chess.WHITE] & chess.BB_G1)
        self.assertEqual(board.piece_at(chess.G1), chess.Piece(chess.KING, chess.WHITE))
        self.assertEqual(board.piece_at(chess.C1), chess.Piece(chess.ROOK, chess.WHITE))

    def test_move_generation_bug(self):
        # Specific problematic position.
        fen = "4kb1r/3b1ppp/8/1r2pNB1/6P1/pP2QP2/P6P/4R1K1 w k - 0 27"
        board = chess.Board(fen)

        # Make a move.
        board.push_san("Re2")

        # Check for the illegal move.
        illegal_move = chess.Move.from_uci("e8f8")
        self.assertNotIn(illegal_move, board.pseudo_legal_moves)
        self.assertNotIn(illegal_move, board.generate_pseudo_legal_moves())
        self.assertNotIn(illegal_move, board.legal_moves)
        self.assertNotIn(illegal_move, board.generate_legal_moves())

        # Generate all pseudo-legal moves.
        for a in board.pseudo_legal_moves:
            board.push(a)
            board.pop()

        # Unmake the move.
        board.pop()

        # Check that board is still consistent.
        self.assertEqual(board.fen(), fen)

    def test_stateful_move_generation_bug(self):
        board = chess.Board("r1b1k3/p2p1Nr1/n2b3p/3pp1pP/2BB1p2/P3P2R/Q1P3P1/R3K1N1 b Qq - 0 1")
        count = 0
        for move in board.legal_moves:
            board.push(move)
            list(board.generate_legal_moves())
            count += 1
            board.pop()

        self.assertEqual(count, 26)

    def test_ninesixty_castling_bug(self):
        board = chess.Board("4r3/3k4/8/8/8/8/q5PP/1R1KR3 w Q - 2 2", chess960=True)
        move = chess.Move.from_uci("d1b1")
        self.assertTrue(board.is_castling(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_legal_moves())
        self.assertTrue(board.is_legal(move))
        self.assertEqual(board.parse_san("O-O-O+"), move)
        self.assertEqual(board.san(move), "O-O-O+")

    def test_equality(self):
        self.assertEqual(chess.Board(), chess.Board())
        self.assertFalse(chess.Board() != chess.Board())

        a = chess.Board()
        a.push_san("d4")
        b = chess.Board()
        b.push_san("d3")
        self.assertNotEqual(a, b)
        self.assertFalse(a == b)

    def test_status(self):
        board = chess.Board()
        self.assertEqual(board.status(), chess.STATUS_VALID)
        self.assertTrue(board.is_valid())

        board.remove_piece_at(chess.H1)
        self.assertTrue(board.status() & chess.STATUS_BAD_CASTLING_RIGHTS)

        board.remove_piece_at(chess.E8)
        self.assertTrue(board.status() & chess.STATUS_NO_BLACK_KING)

        # The en passant square should be set even if no capture is actually
        # possible.
        board = chess.Board()
        board.push_san("e4")
        self.assertEqual(board.ep_square, chess.E3)
        self.assertEqual(board.status(), chess.STATUS_VALID)

        # But there must indeed be a pawn there.
        board.remove_piece_at(chess.E4)
        self.assertEqual(board.status(), chess.STATUS_INVALID_EP_SQUARE)

        # King must be between the two rooks.
        board = chess.Board("2rrk3/8/8/8/8/8/3PPPPP/2RK4 w cd - 0 1")
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)

        # Generally valid position, but not valid standard chess position due
        # to non-standard castling rights. Chess960 start position #0.
        board = chess.Board("bbqnnrkr/pppppppp/8/8/8/8/PPPPPPPP/BBQNNRKR w KQkq - 0 1", chess960=True)
        self.assertEqual(board.status(), chess.STATUS_VALID)
        board = chess.Board("bbqnnrkr/pppppppp/8/8/8/8/PPPPPPPP/BBQNNRKR w KQkq - 0 1", chess960=False)
        self.assertEqual(board.status(), chess.STATUS_BAD_CASTLING_RIGHTS)

        # Opposite check.
        board = chess.Board("4k3/8/8/8/8/8/4Q3/4K3 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_OPPOSITE_CHECK)

        # Empty board.
        board = chess.Board(None)
        self.assertEqual(board.status(), chess.STATUS_EMPTY | chess.STATUS_NO_WHITE_KING | chess.STATUS_NO_BLACK_KING)

        # Too many kings.
        board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBKKBNR w KQkq - 0 1")
        self.assertEqual(board.status(), chess.STATUS_TOO_MANY_KINGS)

        # Triple check.
        board = chess.Board("4k3/5P2/3N4/8/8/8/4R3/4K3 b - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_TOO_MANY_CHECKERS | chess.STATUS_IMPOSSIBLE_CHECK)

        # Impossible checker alignment.
        board = chess.Board("3R4/8/q4k2/2B5/1NK5/3b4/8/8 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)
        board = chess.Board("2Nq4/2K5/1b6/8/7R/3k4/7P/8 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)
        board = chess.Board("5R2/2P5/8/4k3/8/3rK2r/8/8 w - - 0 1")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)
        board = chess.Board("8/8/8/1k6/3Pp3/8/8/4KQ2 b - d3 0 1")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)

        # Checkers aligned with opponent king are fine.
        board = chess.Board("8/8/5k2/p1q5/PP1rp1P1/3P1N2/2RK1r2/5nN1 w - - 0 3")
        self.assertEqual(board.status(), chess.STATUS_VALID)

    def test_one_king_movegen(self):
        board = chess.Board.empty()
        board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
        self.assertFalse(board.is_valid())
        self.assertEqual(board.legal_moves.count(), 3)
        self.assertEqual(board.pseudo_legal_moves.count(), 3)
        board.push_san("Kb1")
        self.assertEqual(board.legal_moves.count(), 0)
        self.assertEqual(board.pseudo_legal_moves.count(), 0)
        board.push_san("--")
        self.assertEqual(board.legal_moves.count(), 5)
        self.assertEqual(board.pseudo_legal_moves.count(), 5)

    def test_epd(self):
        # Create an EPD with a move and a string.
        board = chess.Board("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - 0 1")
        epd = board.epd(bm=chess.Move(chess.D6, chess.D1), id="BK.01")
        self.assertIn(epd, [
            "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";",
            "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - id \"BK.01\"; bm Qd1+;"])

        # Create an EPD with a noop.
        board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        self.assertEqual(board.epd(noop=None), "4k3/8/8/8/8/8/8/4K3 w - - noop;")

        # Create an EPD with numbers.
        self.assertEqual(board.epd(pi=3.14), "4k3/8/8/8/8/8/8/4K3 w - - pi 3.14;")

        # Create an EPD with a variation.
        board = chess.Board("k7/8/8/8/8/8/4PPPP/4K1NR w K - 0 1")
        epd = board.epd(pv=[
            chess.Move.from_uci("g1f3"),  # Nf3
            chess.Move.from_uci("a8a7"),  # Ka7
            chess.Move.from_uci("e1h1"),  # O-O
        ])
        self.assertEqual(epd, "k7/8/8/8/8/8/4PPPP/4K1NR w K - pv Nf3 Ka7 O-O;")

        # Create an EPD with a set of moves.
        board = chess.Board("8/8/8/4k3/8/1K6/8/8 b - - 0 1")
        epd = board.epd(bm=[
            chess.Move.from_uci("e5e6"),  # Ke6
            chess.Move.from_uci("e5e4"),  # Ke4
        ])
        self.assertEqual(epd, "8/8/8/4k3/8/1K6/8/8 b - - bm Ke4 Ke6;")

        # Test loading an EPD.
        board = chess.Board()
        operations = board.set_epd("r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - bm f4; id \"BK.24\";")
        self.assertEqual(board.fen(), "r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - 0 1")
        self.assertIn(chess.Move(chess.F2, chess.F4), operations["bm"])
        self.assertEqual(operations["id"], "BK.24")

        # Test loading an EPD with half-move counter operations.
        board = chess.Board()
        operations = board.set_epd("4k3/8/8/8/8/8/8/4K3 b - - fmvn 17; hmvc 13")
        self.assertEqual(board.fen(), "4k3/8/8/8/8/8/8/4K3 b - - 13 17")
        self.assertEqual(operations["fmvn"], 17)
        self.assertEqual(operations["hmvc"], 13)

        # Test context of parsed SANs.
        board = chess.Board()
        operations = board.set_epd("4k3/8/8/2N5/8/8/8/4K3 w - - test Ne4")
        self.assertEqual(operations["test"], chess.Move(chess.C5, chess.E4))

        # Test parsing EPD with a set of moves.
        board = chess.Board()
        operations = board.set_epd("4k3/8/3QK3/8/8/8/8/8 w - - bm Qe7# Qb8#;")
        self.assertEqual(board.fen(), "4k3/8/3QK3/8/8/8/8/8 w - - 0 1")
        self.assertEqual(len(operations["bm"]), 2)
        self.assertIn(chess.Move.from_uci("d6b8"), operations["bm"])
        self.assertIn(chess.Move.from_uci("d6e7"), operations["bm"])

        # Test parsing EPD with a stack of moves.
        board = chess.Board()
        operations = board.set_epd("6k1/1p6/6K1/8/8/8/8/7Q w - - pv Qh7+ Kf8 Qf7#;")
        self.assertEqual(len(operations["pv"]), 3)
        self.assertEqual(operations["pv"][0], chess.Move.from_uci("h1h7"))
        self.assertEqual(operations["pv"][1], chess.Move.from_uci("g8f8"))
        self.assertEqual(operations["pv"][2], chess.Move.from_uci("h7f7"))

        # Test EPD with semicolon.
        board = chess.Board()
        operations = board.set_epd("r2qk2r/ppp1b1pp/2n1p3/3pP1n1/3P2b1/2PB1NN1/PP4PP/R1BQK2R w KQkq - bm Nxg5; c0 \"ERET.095; Queen sacrifice\";")
        self.assertEqual(operations["bm"], [chess.Move.from_uci("f3g5")])
        self.assertEqual(operations["c0"], "ERET.095; Queen sacrifice")

        # Test EPD with string escaping.
        board = chess.Board()
        operations = board.set_epd(r"""4k3/8/8/8/8/8/8/4K3 w - - a "foo\"bar";; ; b "foo\\\\";""")
        self.assertEqual(operations["a"], "foo\"bar")
        self.assertEqual(operations["b"], "foo\\\\")

        # Test EPD with unmatched trailing quotes.
        board = chess.Board()
        operations = board.set_epd("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"")
        self.assertEqual(operations["bm"], [chess.Move.from_uci("d6d1")])
        self.assertEqual(operations["id"], "")
        self.assertEqual(board.epd(**operations), "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"\";")

    def test_eret_epd(self):
        # Too many dashes.
        epd = """r1bqk1r1/1p1p1n2/p1n2pN1/2p1b2Q/2P1Pp2/1PN5/PB4PP/R4RK1 w q - - bm Rxf4; id "ERET 001 - Entlastung";"""
        board, ops = chess.Board.from_epd(epd)
        self.assertEqual(ops["id"], "ERET 001 - Entlastung")
        self.assertEqual(ops["bm"], [chess.Move.from_uci("f1f4")])

    def test_set_fen_as_epd(self):
        board = chess.Board()
        with self.assertRaises(ValueError):
            board.set_epd(board.fen())  # Move numbers are not valid opcodes

    def test_null_moves(self):
        self.assertEqual(str(chess.Move.null()), "0000")
        self.assertEqual(chess.Move.null().uci(), "0000")
        self.assertFalse(chess.Move.null())

        fen = "rnbqkbnr/ppp1pppp/8/2Pp4/8/8/PP1PPPPP/RNBQKBNR w KQkq d6 0 2"
        board = chess.Board(fen)

        self.assertEqual(chess.Move.from_uci("0000"), board.push_san("--"))
        self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/2Pp4/8/8/PP1PPPPP/RNBQKBNR b KQkq - 1 2")

        self.assertEqual(chess.Move.null(), board.pop())
        self.assertEqual(board.fen(), fen)

    def test_attackers(self):
        board = chess.Board("r1b1k2r/pp1n1ppp/2p1p3/q5B1/1b1P4/P1n1PN2/1P1Q1PPP/2R1KB1R b Kkq - 3 10")

        attackers = board.attackers(chess.WHITE, chess.C3)
        self.assertEqual(len(attackers), 3)
        self.assertIn(chess.C1, attackers)
        self.assertIn(chess.D2, attackers)
        self.assertIn(chess.B2, attackers)
        self.assertNotIn(chess.D4, attackers)
        self.assertNotIn(chess.E1, attackers)

    def test_en_passant_attackers(self):
        board = chess.Board("4k3/8/8/8/4pPp1/8/8/4K3 b - f3 0 1")

        # Attacking the en passant square.
        attackers = board.attackers(chess.BLACK, chess.F3)
        self.assertEqual(len(attackers), 2)
        self.assertIn(chess.E4, attackers)
        self.assertIn(chess.G4, attackers)

        # Not attacking the pawn directly.
        attackers = board.attackers(chess.BLACK, chess.F4)
        self.assertEqual(attackers, chess.BB_EMPTY)

    def test_attacks(self):
        board = chess.Board("5rk1/p5pp/2p3p1/1p1pR3/3P2P1/2N5/PP3n2/2KB4 w - - 1 26")

        attacks = board.attacks(chess.E5)
        self.assertEqual(len(attacks), 11)
        self.assertIn(chess.D5, attacks)
        self.assertIn(chess.E1, attacks)
        self.assertIn(chess.F5, attacks)
        self.assertNotIn(chess.E5, attacks)
        self.assertNotIn(chess.C5, attacks)
        self.assertNotIn(chess.F4, attacks)

        pawn_attacks = board.attacks(chess.B2)
        self.assertIn(chess.A3, pawn_attacks)
        self.assertNotIn(chess.B3, pawn_attacks)

        self.assertFalse(board.attacks(chess.G1))

    def test_clear(self):
        board = chess.Board()
        board.clear()

        self.assertEqual(board.turn, chess.WHITE)
        self.assertEqual(board.fullmove_number, 1)
        self.assertEqual(board.halfmove_clock, 0)
        self.assertEqual(board.castling_rights, chess.BB_EMPTY)
        self.assertFalse(board.ep_square)

        self.assertFalse(board.piece_at(chess.E1))
        self.assertEqual(chess.popcount(board.occupied), 0)

    def test_threefold_repetition(self):
        board = chess.Board()

        # Go back and forth with the knights to reach the starting position
        # for a second time.
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Nf3")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Nf6")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Ng1")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Ng8")

        # Once more.
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Nf3")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Nf6")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Ng1")

        # Now black can go back to the starting position (thus reaching it a
        # third time).
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())
        board.push_san("Ng8")

        # They indeed do it. Also, white can now claim.
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertTrue(board.is_repetition())

        # But not after a different move.
        board.push_san("e4")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_repetition())

        # Undo moves and check if everything works backwards.
        board.pop()  # e4
        self.assertTrue(board.can_claim_threefold_repetition())
        board.pop()  # Ng8
        self.assertTrue(board.can_claim_threefold_repetition())
        while board.move_stack:
            board.pop()
            self.assertFalse(board.can_claim_threefold_repetition())

    def test_fivefold_repetition(self):
        fen = "rnbq1rk1/ppp3pp/3bpn2/3p1p2/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 3 7"
        board = chess.Board(fen)

        # Repeat the position up to the fourth time.
        for i in range(3):
            board.push_san("Be2")
            self.assertFalse(board.is_fivefold_repetition())
            board.push_san("Ne4")
            self.assertFalse(board.is_fivefold_repetition())
            board.push_san("Bd3")
            self.assertFalse(board.is_fivefold_repetition())
            board.push_san("Nf6")
            self.assertEqual(board.fen().split()[0], fen.split()[0])
            self.assertFalse(board.is_fivefold_repetition())
            self.assertFalse(board.is_game_over())

        # Repeat it once more. Now it is a fivefold repetition.
        board.push_san("Be2")
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Ne4")
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Bd3")
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Nf6")
        self.assertEqual(board.fen().split()[0], fen.split()[0])
        self.assertTrue(board.is_fivefold_repetition())
        self.assertTrue(board.is_game_over())

        # It is also a threefold repetition.
        self.assertTrue(board.can_claim_threefold_repetition())

        # Now no longer.
        board.push_san("Qc2")
        board.push_san("Qd7")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Qd2")
        board.push_san("Qe7")
        self.assertFalse(board.can_claim_threefold_repetition())
        self.assertFalse(board.is_fivefold_repetition())

        # Give the possibility to repeat.
        board.push_san("Qd1")
        self.assertFalse(board.is_fivefold_repetition())
        self.assertFalse(board.is_game_over())
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertTrue(board.is_game_over(claim_draw=True))

        # Do, in fact, repeat.
        self.assertFalse(board.is_fivefold_repetition())
        board.push_san("Qd8")

        # This is a threefold repetition, and also a fivefold repetition since
        # it no longer has to occur on consecutive moves.
        self.assertTrue(board.can_claim_threefold_repetition())
        self.assertTrue(board.is_fivefold_repetition())
        self.assertEqual(board.fen().split()[0], fen.split()[0])

    def test_trivial_is_repetition(self):
        self.assertTrue(chess.Board().is_repetition(1))

    def test_fifty_moves(self):
        # Test positions from Jan Timman vs. Christopher Lutz (1995).
        board = chess.Board()
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("8/5R2/8/r2KB3/6k1/8/8/8 w - - 19 79")
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("8/8/6r1/4B3/8/4K2k/5R2/8 b - - 68 103")
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())
        board = chess.Board("6R1/7k/8/8/1r3B2/5K2/8/8 w - - 99 119")
        self.assertFalse(board.is_fifty_moves())
        self.assertTrue(board.can_claim_fifty_moves())
        board = chess.Board("8/7k/8/6R1/1r3B2/5K2/8/8 b - - 100 119")
        self.assertTrue(board.is_fifty_moves())
        self.assertTrue(board.can_claim_fifty_moves())
        board = chess.Board("8/7k/8/1r3KR1/5B2/8/8/8 w - - 105 122")
        self.assertTrue(board.is_fifty_moves())
        self.assertTrue(board.can_claim_fifty_moves())

        # Once checkmated, it is too late to claim.
        board = chess.Board("k7/8/NKB5/8/8/8/8/8 b - - 105 176")
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())

        # A stalemate is a draw, but you can not and do not need to claim it by
        # the fifty-move rule.
        board = chess.Board("k7/3N4/1K6/1B6/8/8/8/8 b - - 99 1")
        self.assertTrue(board.is_stalemate())
        self.assertTrue(board.is_game_over())
        self.assertFalse(board.is_fifty_moves())
        self.assertFalse(board.can_claim_fifty_moves())
        self.assertFalse(board.can_claim_draw())

    def test_promoted_comparison(self):
        board = chess.Board()
        board.set_fen("5R2/3P4/8/8/7r/7r/7k/K7 w - - 0 1")
        board.push_san("d8=R")

        same_board = chess.Board(board.fen())
        self.assertEqual(board, same_board)

    def test_ep_legality(self):
        move = chess.Move.from_uci("h5g6")
        board = chess.Board("rnbqkbnr/pppppp2/7p/6pP/8/8/PPPPPPP1/RNBQKBNR w KQkq g6 0 3")
        self.assertTrue(board.is_legal(move))
        board.push_san("Nf3")
        self.assertFalse(board.is_legal(move))
        board.push_san("Nf6")
        self.assertFalse(board.is_legal(move))

        move = chess.Move.from_uci("c4d3")
        board = chess.Board("rnbqkbnr/pp1ppppp/8/8/2pP4/2P2N2/PP2PPPP/RNBQKB1R b KQkq d3 0 3")
        self.assertTrue(board.is_legal(move))
        board.push_san("Qc7")
        self.assertFalse(board.is_legal(move))
        board.push_san("Bd2")
        self.assertFalse(board.is_legal(move))

    def test_pseudo_legality(self):
        sample_moves = [
            chess.Move(chess.A2, chess.A4),
            chess.Move(chess.C1, chess.E3),
            chess.Move(chess.G8, chess.F6),
            chess.Move(chess.D7, chess.D8, chess.QUEEN),
            chess.Move(chess.E5, chess.E4),
        ]

        sample_fens = [
            chess.STARTING_FEN,
            "rnbqkbnr/pp1ppppp/2p5/8/6P1/2P5/PP1PPP1P/RNBQKBNR b KQkq - 0 1",
            "rnb1kbnr/ppq1pppp/2pp4/8/6P1/2P5/PP1PPPBP/RNBQK1NR w KQkq - 0 1",
            "rn2kbnr/p1q1ppp1/1ppp3p/8/4B1b1/2P4P/PPQPPP2/RNB1K1NR w KQkq - 0 1",
            "rnkq1bnr/p3ppp1/1ppp3p/3B4/6b1/2PQ3P/PP1PPP2/RNB1K1NR w KQ - 0 1",
            "rn1q1bnr/3kppp1/2pp3p/pp6/1P2b3/2PQ1N1P/P2PPPB1/RNB1K2R w KQ - 0 1",
            "rnkq1bnr/4pp2/2pQ2pp/pp6/1P5N/2P4P/P2PPP2/RNB1KB1b w Q - 0 1",
            "rn3b1r/1kq1p3/2pQ1npp/Pp6/4b3/2PPP2P/P4P2/RNB1KB2 w Q - 0 1",
            "r4br1/8/k1p2npp/Ppn1p3/P7/2PPP1qP/4bPQ1/RNB1KB2 w Q - 0 1",
            "rnbqk1nr/p2p3p/1p5b/2pPppp1/8/P7/1PPQPPPP/RNB1KBNR w KQkq c6 0 1",
            "rnb1k2r/pp1p1p1p/1q1P4/2pnpPp1/6P1/2N5/PP1BP2P/R2QKBNR w KQkq e6 0 1",
            "1n4kr/2B4p/2nb2b1/ppp5/P1PpP3/3P4/5K2/1N1R4 b - c3 0 1",
            "r2n3r/1bNk2pp/6P1/pP3p2/3pPqnP/1P1P1p1R/2P3B1/Q1B1bKN1 b - e3 0 1",
        ]

        for sample_fen in sample_fens:
            board = chess.Board(sample_fen)

            pseudo_legal_moves = list(board.generate_pseudo_legal_moves())

            # Ensure that all moves generated as pseudo-legal pass the
            # pseudo-legality check.
            for move in pseudo_legal_moves:
                self.assertTrue(board.is_pseudo_legal(move))

            # Check that moves not generated as pseudo-legal do not pass the
            # pseudo-legality check.
            for move in sample_moves:
                if move not in pseudo_legal_moves:
                    self.assertFalse(board.is_pseudo_legal(move))

    def test_pseudo_legal_castling_masks(self):
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        kingside = chess.Move.from_uci("e1g1")
        queenside = chess.Move.from_uci("e1c1")

        moves = list(board.generate_pseudo_legal_moves())
        self.assertIn(kingside, moves)
        self.assertIn(queenside, moves)

        moves = list(board.generate_pseudo_legal_moves(from_mask=chess.BB_RANK_2))
        self.assertEqual(moves, [])

        moves = list(board.generate_pseudo_legal_moves(to_mask=chess.BB_A1))
        self.assertNotIn(kingside, moves)
        self.assertIn(queenside, moves)

    def test_pieces(self):
        board = chess.Board()
        king = board.pieces(chess.KING, chess.WHITE)
        self.assertIn(chess.E1, king)
        self.assertEqual(len(king), 1)

    def test_string_conversion(self):
        board = chess.Board("7k/1p1qn1b1/pB1p1n2/3Pp3/4Pp1p/2QN1B2/PP4PP/6K1 w - - 0 28")

        self.assertEqual(str(board), textwrap.dedent("""\
            . . . . . . . k
            . p . q n . b .
            p B . p . n . .
            . . . P p . . .
            . . . . P p . p
            . . Q N . B . .
            P P . . . . P P
            . . . . . . K ."""))

        self.assertEqual(board.unicode(empty_square="·"), textwrap.dedent("""\
            · · · · · · · ♚
            · ♟ · ♛ ♞ · ♝ ·
            ♟ ♗ · ♟ · ♞ · ·
            · · · ♙ ♟ · · ·
            · · · · ♙ ♟ · ♟
            · · ♕ ♘ · ♗ · ·
            ♙ ♙ · · · · ♙ ♙
            · · · · · · ♔ ·"""))

        self.assertEqual(board.unicode(invert_color=True, borders=True, empty_square="·"), textwrap.dedent("""\
              -----------------
            8 |·|·|·|·|·|·|·|♔|
              -----------------
            7 |·|♙|·|♕|♘|·|♗|·|
              -----------------
            6 |♙|♝|·|♙|·|♘|·|·|
              -----------------
            5 |·|·|·|♟|♙|·|·|·|
              -----------------
            4 |·|·|·|·|♟|♙|·|♙|
              -----------------
            3 |·|·|♛|♞|·|♝|·|·|
              -----------------
            2 |♟|♟|·|·|·|·|♟|♟|
              -----------------
            1 |·|·|·|·|·|·|♚|·|
              -----------------
               a b c d e f g h"""))

    def test_move_info(self):
        board = chess.Board("r1bqkb1r/p3np2/2n1p2p/1p4pP/2pP4/4PQ1N/1P2BPP1/RNB1K2R w KQkq g6 0 11")

        self.assertTrue(board.is_capture(board.parse_xboard("Qxf7+")))
        self.assertFalse(board.is_en_passant(board.parse_xboard("Qxf7+")))
        self.assertFalse(board.is_castling(board.parse_xboard("Qxf7+")))

        self.assertTrue(board.is_capture(board.parse_xboard("hxg6")))
        self.assertTrue(board.is_en_passant(board.parse_xboard("hxg6")))
        self.assertFalse(board.is_castling(board.parse_xboard("hxg6")))

        self.assertFalse(board.is_capture(board.parse_xboard("b3")))
        self.assertFalse(board.is_en_passant(board.parse_xboard("b3")))
        self.assertFalse(board.is_castling(board.parse_xboard("b3")))

        self.assertFalse(board.is_capture(board.parse_xboard("Ra6")))
        self.assertFalse(board.is_en_passant(board.parse_xboard("Ra6")))
        self.assertFalse(board.is_castling(board.parse_xboard("Ra6")))

        self.assertFalse(board.is_capture(board.parse_xboard("O-O")))
        self.assertFalse(board.is_en_passant(board.parse_xboard("O-O")))
        self.assertTrue(board.is_castling(board.parse_xboard("O-O")))

    def test_pin(self):
        board = chess.Board("rnb1k1nr/2pppppp/3P4/8/1b5q/8/PPPNPBPP/RNBQKB1R w KQkq - 0 1")
        self.assertTrue(board.is_pinned(chess.WHITE, chess.F2))
        self.assertTrue(board.is_pinned(chess.WHITE, chess.D2))
        self.assertFalse(board.is_pinned(chess.WHITE, chess.E1))
        self.assertFalse(board.is_pinned(chess.BLACK, chess.H4))
        self.assertFalse(board.is_pinned(chess.BLACK, chess.E8))

        self.assertEqual(board.pin(chess.WHITE, chess.B1), chess.BB_ALL)

        self.assertEqual(board.pin(chess.WHITE, chess.F2), chess.BB_E1 | chess.BB_F2 | chess.BB_G3 | chess.BB_H4)

        self.assertEqual(board.pin(chess.WHITE, chess.D2), chess.BB_E1 | chess.BB_D2 | chess.BB_C3 | chess.BB_B4 | chess.BB_A5)

        self.assertEqual(chess.Board(None).pin(chess.WHITE, chess.F7), chess.BB_ALL)

    def test_pin_in_check(self):
        # The knight on the eighth rank is on the outer side of the rank attack.
        board = chess.Board("1n1R2k1/2b1qpp1/p3p2p/1p6/1P2Q2P/4PNP1/P4PB1/6K1 b - - 0 1")
        self.assertFalse(board.is_pinned(chess.BLACK, chess.B8))

        # The empty square e8 would be considered pinned.
        self.assertTrue(board.is_pinned(chess.BLACK, chess.E8))

    def test_impossible_en_passant(self):
        # Not a pawn there.
        board = chess.Board("1b1b4/8/b1P5/2kP4/8/2b4K/8/8 w - c6 0 1")
        self.assertTrue(board.status() & chess.STATUS_INVALID_EP_SQUARE)

        # Sixth rank square not empty.
        board = chess.Board("5K2/8/2pp2Pp/2PP4/P5Pp/2pP1Ppp/P6p/7k b - g3 0 1")
        self.assertTrue(board.status() & chess.STATUS_INVALID_EP_SQUARE)

        # Seventh rank square not empty.
        board = chess.Board("8/7k/8/7p/8/8/8/K7 w - h6 0 1")
        self.assertTrue(board.status() & chess.STATUS_INVALID_EP_SQUARE)

    def test_horizontally_skewered_en_passant(self):
        # Horizontal pin. Non-evasion.
        board = chess.Board("8/8/8/r2Pp2K/8/8/4k3/8 w - e6 0 1")
        move = chess.Move.from_uci("d5e6")
        self.assertEqual(board.status(), chess.STATUS_VALID)
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertFalse(board.is_legal(move))
        self.assertNotIn(move, board.generate_legal_moves())
        self.assertNotIn(move, board.generate_legal_ep())

    def test_diagonally_skewered_en_passant(self):
        # The capturing pawn is still blocking the diagonal.
        board = chess.Board("2b1r2r/8/5P1k/2p1pP2/5R1P/6PK/4q3/4R3 w - e6 0 1")
        move = chess.Move.from_uci("f5e6")
        self.assertIn(move, board.generate_legal_ep())
        self.assertIn(move, board.generate_legal_moves())

        # Regarding the following positions:
        # Note that the positions under test can not be reached by a sequence
        # of legal moves. The last move must have been a double pawn move,
        # but then the king would have been in check already.

        # Diagonal attack uncovered. Evasion attempt.
        board = chess.Board("8/8/8/5k2/4Pp2/8/2B5/4K3 b - e3 0 1")
        move = chess.Move.from_uci("f4e3")
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertFalse(board.is_legal(move))
        self.assertNotIn(move, board.generate_legal_moves())
        self.assertNotIn(move, board.generate_legal_ep())

        # Diagonal attack uncovered. Non-evasion.
        board = chess.Board("8/8/8/7B/6Pp/8/4k2K/3r4 b - g3 0 1")
        move = chess.Move.from_uci("h4g3")
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertFalse(board.is_legal(move))
        self.assertNotIn(move, board.generate_legal_moves())
        self.assertNotIn(move, board.generate_legal_ep())

    def test_file_pinned_en_passant(self):
        board = chess.Board("8/5K2/8/3k4/3pP3/8/8/3R4 b - e3 0 1")
        move = chess.Move.from_uci("d4e3")
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertFalse(board.is_legal(move))
        self.assertNotIn(move, board.generate_legal_moves())
        self.assertNotIn(move, board.generate_legal_ep())

    def test_en_passant_evasion(self):
        board = chess.Board("8/8/8/2k5/2pP4/8/4K3/8 b - d3 0 1")
        move = chess.Move.from_uci("c4d3")
        self.assertEqual(move, board.parse_san("cxd3"))
        self.assertTrue(board.is_pseudo_legal(move))
        self.assertIn(move, board.generate_pseudo_legal_moves())
        self.assertIn(move, board.generate_pseudo_legal_ep())
        self.assertTrue(board.is_legal(move))
        self.assertIn(move, board.generate_legal_moves())
        self.assertIn(move, board.generate_legal_ep())

    def test_capture_generation(self):
        board = chess.Board("3q1rk1/ppp1p1pp/4b3/3pPp2/3P4/1K1n4/PPQ2PPP/3b1BNR w - f6 0 1")

        # Fully legal captures.
        lc = list(board.generate_legal_captures())
        self.assertIn(board.parse_san("Qxd1"), lc)
        self.assertIn(board.parse_san("exf6"), lc)  # En passant
        self.assertIn(board.parse_san("Bxd3"), lc)
        self.assertEqual(len(lc), 3)

        plc = list(board.generate_pseudo_legal_captures())
        self.assertIn(board.parse_san("Qxd1"), plc)
        self.assertIn(board.parse_san("exf6"), plc)  # En passant
        self.assertIn(board.parse_san("Bxd3"), plc)
        self.assertIn(chess.Move.from_uci("c2c7"), plc)
        self.assertIn(chess.Move.from_uci("c2d3"), plc)
        self.assertEqual(len(plc), 5)

    def test_castling_is_legal(self):
        board = chess.Board("rnbqkbnr/5p2/1pp3pp/p2P4/6P1/2NPpN2/PPP1Q1BP/R3K2R w Qq - 0 11")
        self.assertFalse(board.is_legal(chess.Move.from_uci("e1g1")))
        self.assertFalse(board.is_legal(chess.Move.from_uci("e1h1")))

        board.castling_rights |= chess.BB_H1
        self.assertTrue(board.is_legal(chess.Move.from_uci("e1g1")))
        self.assertTrue(board.is_legal(chess.Move.from_uci("e1h1")))

    def test_from_chess960_pos(self):
        board = chess.Board.from_chess960_pos(909)
        self.assertTrue(board.chess960)
        self.assertEqual(board.fen(), "rkqbrnbn/pppppppp/8/8/8/8/PPPPPPPP/RKQBRNBN w KQkq - 0 1")

    def test_mirror(self):
        board = chess.Board("r1bq1r2/pp2n3/4N2k/3pPppP/1b1n2Q1/2N5/PP3PP1/R1B1K2R w KQ g6 0 15")
        mirrored = chess.Board("r1b1k2r/pp3pp1/2n5/1B1N2q1/3PpPPp/4n2K/PP2N3/R1BQ1R2 b kq g3 0 15")
        self.assertEqual(board.mirror(), mirrored)
        board.apply_mirror()
        self.assertEqual(board, mirrored)

    def test_chess960_pos(self):
        board = chess.Board()

        board.set_chess960_pos(0)
        self.assertEqual(board.board_fen(), "bbqnnrkr/pppppppp/8/8/8/8/PPPPPPPP/BBQNNRKR")
        self.assertEqual(board.chess960_pos(), 0)

        board.set_chess960_pos(631)
        self.assertEqual(board.board_fen(), "rnbkqrnb/pppppppp/8/8/8/8/PPPPPPPP/RNBKQRNB")
        self.assertEqual(board.chess960_pos(), 631)

        board.set_chess960_pos(518)
        self.assertEqual(board.board_fen(), chess.STARTING_BOARD_FEN)
        self.assertEqual(board.chess960_pos(), 518)

        board.set_chess960_pos(959)
        self.assertEqual(board.board_fen(), "rkrnnqbb/pppppppp/8/8/8/8/PPPPPPPP/RKRNNQBB")
        self.assertEqual(board.chess960_pos(), 959)

    def test_is_irreversible(self):
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1")
        self.assertTrue(board.is_irreversible(board.parse_san("Ra2")))
        self.assertTrue(board.is_irreversible(board.parse_san("O-O-O")))
        self.assertTrue(board.is_irreversible(board.parse_san("Kd1")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxa8")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxh8")))
        self.assertFalse(board.is_irreversible(board.parse_san("Rf1")))
        self.assertFalse(board.is_irreversible(chess.Move.null()))

        board.set_castling_fen("kq")
        self.assertFalse(board.is_irreversible(board.parse_san("Ra2")))
        self.assertFalse(board.is_irreversible(board.parse_san("Kd1")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxa8")))
        self.assertTrue(board.is_irreversible(board.parse_san("Rxh8")))
        self.assertFalse(board.is_irreversible(board.parse_san("Rf1")))
        self.assertFalse(board.is_irreversible(chess.Move.null()))

    def test_king_captures_unmoved_rook(self):
        board = chess.Board("8/8/8/B2p3Q/2qPp1P1/b7/2P2PkP/4K2R b K - 0 1")
        move = board.parse_uci("g2h1")
        self.assertFalse(board.is_castling(move))
        self.assertEqual(board.san(move), "Kxh1")
        board.push(move)
        self.assertEqual(board.fen(), "8/8/8/B2p3Q/2qPp1P1/b7/2P2P1P/4K2k w - - 0 2")

    def test_impossible_check_due_to_en_passant(self):
        board = chess.Board("rnbqk1nr/bb3p1p/1q2r3/2pPp3/3P4/7P/1PP1NpPP/R1BQKBNR w KQkq c6")
        self.assertEqual(board.status(), chess.STATUS_IMPOSSIBLE_CHECK)
        self.assertEqual(board.ep_square, chess.C6)
        self.assertTrue(board.has_pseudo_legal_en_passant())
        self.assertFalse(board.has_legal_en_passant())
        self.assertEqual(len(list(board.legal_moves)), 2)

class BaseBoardTestCase(unittest.TestCase):

    def test_set_piece_map(self):
        a = chess.BaseBoard.empty()
        b = chess.BaseBoard()
        a.set_piece_map(b.piece_map())
        self.assertEqual(a, b)
        a.set_piece_map({})
        self.assertNotEqual(a, b)


