import copy
import textwrap
import unittest

import chess
import chess.gaviota
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant


class SquareTestCase(unittest.TestCase):

    def test_square(self):
        for square in chess.SQUARES:
            file_index = chess.square_file(square)
            rank_index = chess.square_rank(square)
            self.assertEqual(chess.square(file_index, rank_index), square, chess.square_name(square))

    def test_shifts(self):
        shifts = [
            chess.shift_down,
            chess.shift_2_down,
            chess.shift_up,
            chess.shift_2_up,
            chess.shift_right,
            chess.shift_2_right,
            chess.shift_left,
            chess.shift_2_left,
            chess.shift_up_left,
            chess.shift_up_right,
            chess.shift_down_left,
            chess.shift_down_right,
        ]

        for shift in shifts:
            for bb_square in chess.BB_SQUARES:
                shifted = shift(bb_square)
                c = chess.popcount(shifted)
                self.assertLessEqual(c, 1)
                self.assertEqual(c, chess.popcount(shifted & chess.BB_ALL))

    def test_parse_square(self):
        self.assertEqual(chess.parse_square("a1"), 0)
        with self.assertRaises(ValueError):
            self.assertEqual(chess.parse_square("A1"))
        with self.assertRaises(ValueError):
            self.assertEqual(chess.parse_square("a0"))

    def test_square_distance(self):
        self.assertEqual(chess.square_distance(chess.A1, chess.A1), 0)
        self.assertEqual(chess.square_distance(chess.A1, chess.H8), 7)
        self.assertEqual(chess.square_distance(chess.E1, chess.E8), 7)
        self.assertEqual(chess.square_distance(chess.A4, chess.H4), 7)
        self.assertEqual(chess.square_distance(chess.D4, chess.E5), 1)

    def test_square_manhattan_distance(self):
        self.assertEqual(chess.square_manhattan_distance(chess.A1, chess.A1), 0)
        self.assertEqual(chess.square_manhattan_distance(chess.A1, chess.H8), 14)
        self.assertEqual(chess.square_manhattan_distance(chess.E1, chess.E8), 7)
        self.assertEqual(chess.square_manhattan_distance(chess.A4, chess.H4), 7)
        self.assertEqual(chess.square_manhattan_distance(chess.D4, chess.E5), 2)

    def test_square_knight_distance(self):
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.A1), 0)
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.H8), 6)
        self.assertEqual(chess.square_knight_distance(chess.G1, chess.F3), 1)
        self.assertEqual(chess.square_knight_distance(chess.E1, chess.E8), 5)
        self.assertEqual(chess.square_knight_distance(chess.A4, chess.H4), 5)
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.B1), 3)
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.C3), 4)
        self.assertEqual(chess.square_knight_distance(chess.A1, chess.B2), 4)
        self.assertEqual(chess.square_knight_distance(chess.C1, chess.B2), 2)


class MoveTestCase(unittest.TestCase):

    def test_equality(self):
        a = chess.Move(chess.A1, chess.A2)
        b = chess.Move(chess.A1, chess.A2)
        c = chess.Move(chess.H7, chess.H8, chess.BISHOP)
        d1 = chess.Move(chess.H7, chess.H8)
        d2 = chess.Move(chess.H7, chess.H8)

        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertEqual(d1, d2)

        self.assertNotEqual(a, c)
        self.assertNotEqual(c, d1)
        self.assertNotEqual(b, d1)
        self.assertFalse(d1 != d2)

    def test_uci_parsing(self):
        self.assertEqual(chess.Move.from_uci("b5c7").uci(), "b5c7")
        self.assertEqual(chess.Move.from_uci("e7e8q").uci(), "e7e8q")
        self.assertEqual(chess.Move.from_uci("P@e4").uci(), "P@e4")
        self.assertEqual(chess.Move.from_uci("B@f4").uci(), "B@f4")
        self.assertEqual(chess.Move.from_uci("0000").uci(), "0000")

    def test_invalid_uci(self):
        with self.assertRaises(chess.InvalidMoveError):
            chess.Move.from_uci("")

        with self.assertRaises(chess.InvalidMoveError):
            chess.Move.from_uci("N")

        with self.assertRaises(chess.InvalidMoveError):
            chess.Move.from_uci("z1g3")

        with self.assertRaises(chess.InvalidMoveError):
            chess.Move.from_uci("Q@g9")

    def test_xboard_move(self):
        self.assertEqual(chess.Move.from_uci("b5c7").xboard(), "b5c7")
        self.assertEqual(chess.Move.from_uci("e7e8q").xboard(), "e7e8q")
        self.assertEqual(chess.Move.from_uci("P@e4").xboard(), "P@e4")
        self.assertEqual(chess.Move.from_uci("B@f4").xboard(), "B@f4")
        self.assertEqual(chess.Move.from_uci("0000").xboard(), "@@@@")

    def test_copy(self):
        a = chess.Move.from_uci("N@f3")
        b = chess.Move.from_uci("a1h8")
        c = chess.Move.from_uci("g7g8r")
        self.assertEqual(copy.copy(a), a)
        self.assertEqual(copy.copy(b), b)
        self.assertEqual(copy.copy(c), c)


class PieceTestCase(unittest.TestCase):

    def test_equality(self):
        a = chess.Piece(chess.BISHOP, chess.WHITE)
        b = chess.Piece(chess.KING, chess.BLACK)
        c = chess.Piece(chess.KING, chess.WHITE)
        d1 = chess.Piece(chess.BISHOP, chess.WHITE)
        d2 = chess.Piece(chess.BISHOP, chess.WHITE)

        self.assertEqual(len(set([a, b, c, d1, d2])), 3)

        self.assertEqual(a, d1)
        self.assertEqual(d1, a)
        self.assertEqual(d1, d2)

        self.assertEqual(repr(a), repr(d1))

        self.assertNotEqual(a, b)
        self.assertNotEqual(b, c)
        self.assertNotEqual(b, d1)
        self.assertNotEqual(a, c)
        self.assertFalse(d1 != d2)

        self.assertNotEqual(repr(a), repr(b))
        self.assertNotEqual(repr(b), repr(c))
        self.assertNotEqual(repr(b), repr(d1))
        self.assertNotEqual(repr(a), repr(c))

    def test_from_symbol(self):
        white_knight = chess.Piece.from_symbol("N")

        self.assertEqual(white_knight.color, chess.WHITE)
        self.assertEqual(white_knight.piece_type, chess.KNIGHT)
        self.assertEqual(white_knight.symbol(), "N")
        self.assertEqual(str(white_knight), "N")

        black_queen = chess.Piece.from_symbol("q")

        self.assertEqual(black_queen.color, chess.BLACK)
        self.assertEqual(black_queen.piece_type, chess.QUEEN)
        self.assertEqual(black_queen.symbol(), "q")
        self.assertEqual(str(black_queen), "q")

    def test_hash(self):
        pieces = {chess.Piece.from_symbol(symbol) for symbol in  "pnbrqkPNBRQK"}
        self.assertEqual(len(pieces), 12)
        hashes = {hash(piece) for piece in pieces}
        self.assertEqual(hashes, set(range(12)))

class LegalMoveGeneratorTestCase(unittest.TestCase):

    def test_list_conversion(self):
        self.assertEqual(len(list(chess.Board().legal_moves)), 20)

    def test_nonzero(self):
        self.assertTrue(chess.Board().legal_moves)
        self.assertTrue(chess.Board().pseudo_legal_moves)

        caro_kann_mate = chess.Board("r1bqkb1r/pp1npppp/2pN1n2/8/3P4/8/PPP1QPPP/R1B1KBNR b KQkq - 4 6")
        self.assertFalse(caro_kann_mate.legal_moves)
        self.assertTrue(caro_kann_mate.pseudo_legal_moves)

    def test_string_conversion(self):
        board = chess.Board("r3k1nr/ppq1pp1p/2p3p1/8/1PPR4/2N5/P3QPPP/5RK1 b kq b3 0 16")

        self.assertIn("Qxh2+", str(board.legal_moves))
        self.assertIn("Qxh2+", repr(board.legal_moves))

        self.assertIn("Qxh2+", str(board.pseudo_legal_moves))
        self.assertIn("Qxh2+", repr(board.pseudo_legal_moves))
        self.assertIn("e8d7", str(board.pseudo_legal_moves))
        self.assertIn("e8d7", repr(board.pseudo_legal_moves))

    def test_traverse_once(self):
        class MockBoard:
            def __init__(self):
                self.traversals = 0

            def generate_legal_moves(self):
                self.traversals += 1
                return
                yield

        board = MockBoard()
        gen = chess.LegalMoveGenerator(board)
        list(gen)
        self.assertEqual(board.traversals, 1)


class SquareSetTestCase(unittest.TestCase):

    def test_equality(self):
        a1 = chess.SquareSet(chess.BB_RANK_4)
        a2 = chess.SquareSet(chess.BB_RANK_4)
        b1 = chess.SquareSet(chess.BB_RANK_5 | chess.BB_RANK_6)
        b2 = chess.SquareSet(chess.BB_RANK_5 | chess.BB_RANK_6)

        self.assertEqual(a1, a2)
        self.assertEqual(b1, b2)
        self.assertFalse(a1 != a2)
        self.assertFalse(b1 != b2)

        self.assertNotEqual(a1, b1)
        self.assertNotEqual(a2, b2)
        self.assertFalse(a1 == b1)
        self.assertFalse(a2 == b2)

        self.assertEqual(chess.SquareSet(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.BB_ALL, chess.SquareSet(chess.BB_ALL))

        self.assertEqual(int(chess.SquareSet(chess.SquareSet(999))), 999)
        self.assertEqual(chess.SquareSet([chess.B8]), chess.BB_B8)

    def test_string_conversion(self):
        expected = textwrap.dedent("""\
            . . . . . . . 1
            . 1 . . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .
            . . . . . . . .
            1 1 1 1 1 1 1 1""")

        bb = chess.SquareSet(chess.BB_H8 | chess.BB_B7 | chess.BB_RANK_1)
        self.assertEqual(str(bb), expected)

    def test_iter(self):
        bb = chess.SquareSet(chess.BB_G7 | chess.BB_G8)
        self.assertEqual(list(bb), [chess.G7, chess.G8])

    def test_reversed(self):
        bb = chess.SquareSet(chess.BB_A1 | chess.BB_B1 | chess.BB_A7 | chess.BB_E1)
        self.assertEqual(list(reversed(bb)), [chess.A7, chess.E1, chess.B1, chess.A1])

    def test_arithmetic(self):
        self.assertEqual(chess.SquareSet(chess.BB_RANK_2) & chess.BB_FILE_D, chess.BB_D2)
        self.assertEqual(chess.SquareSet(chess.BB_ALL) ^ chess.BB_EMPTY, chess.BB_ALL)
        self.assertEqual(chess.SquareSet(chess.BB_C1) | chess.BB_FILE_C, chess.BB_FILE_C)

        bb = chess.SquareSet(chess.BB_EMPTY)
        bb ^= chess.BB_ALL
        self.assertEqual(bb, chess.BB_ALL)
        bb &= chess.BB_E4
        self.assertEqual(bb, chess.BB_E4)
        bb |= chess.BB_RANK_4
        self.assertEqual(bb, chess.BB_RANK_4)

        self.assertEqual(chess.SquareSet(chess.BB_F3) << 1, chess.BB_G3)
        self.assertEqual(chess.SquareSet(chess.BB_C8) >> 2, chess.BB_A8)

        bb = chess.SquareSet(chess.BB_D1)
        bb <<= 1
        self.assertEqual(bb, chess.BB_E1)
        bb >>= 2
        self.assertEqual(bb, chess.BB_C1)

    def test_immutable_set_operations(self):
        examples = [
            chess.BB_EMPTY,
            chess.BB_A1,
            chess.BB_A2,
            chess.BB_RANK_1,
            chess.BB_RANK_2,
            chess.BB_FILE_A,
            chess.BB_FILE_E,
        ]

        for a in examples:
            self.assertEqual(chess.SquareSet(a).copy(), a)

        for a in examples:
            a = chess.SquareSet(a)
            for b in examples:
                b = chess.SquareSet(b)
                self.assertEqual(set(a).isdisjoint(set(b)), a.isdisjoint(b))
                self.assertEqual(set(a).issubset(set(b)), a.issubset(b))
                self.assertEqual(set(a).issuperset(set(b)), a.issuperset(b))
                self.assertEqual(set(a).union(set(b)), set(a.union(b)))
                self.assertEqual(set(a).intersection(set(b)), set(a.intersection(b)))
                self.assertEqual(set(a).difference(set(b)), set(a.difference(b)))
                self.assertEqual(set(a).symmetric_difference(set(b)), set(a.symmetric_difference(b)))

    def test_mutable_set_operations(self):
        squares = chess.SquareSet(chess.BB_A1)
        squares.update(chess.BB_FILE_H)
        self.assertEqual(squares, chess.BB_A1 | chess.BB_FILE_H)

        squares.intersection_update(chess.BB_RANK_8)
        self.assertEqual(squares, chess.BB_H8)

        squares.difference_update(chess.BB_A1)
        self.assertEqual(squares, chess.BB_H8)

        squares.symmetric_difference_update(chess.BB_A1)
        self.assertEqual(squares, chess.BB_A1 | chess.BB_H8)

        squares.add(chess.A3)
        self.assertEqual(squares, chess.BB_A1 | chess.BB_A3 | chess.BB_H8)

        squares.remove(chess.H8)
        self.assertEqual(squares, chess.BB_A1 | chess.BB_A3)

        with self.assertRaises(KeyError):
            squares.remove(chess.H8)

        squares.discard(chess.H8)

        squares.discard(chess.A1)
        self.assertEqual(squares, chess.BB_A3)

        squares.clear()
        self.assertEqual(squares, chess.BB_EMPTY)

        with self.assertRaises(KeyError):
            squares.pop()

        squares.add(chess.C7)
        self.assertEqual(squares.pop(), chess.C7)
        self.assertEqual(squares, chess.BB_EMPTY)

    def test_from_square(self):
        self.assertEqual(chess.SquareSet.from_square(chess.H5), chess.BB_H5)
        self.assertEqual(chess.SquareSet.from_square(chess.C2), chess.BB_C2)

    def test_carry_rippler(self):
        self.assertEqual(sum(1 for _ in chess.SquareSet(chess.BB_D1).carry_rippler()), 2 ** 1)
        self.assertEqual(sum(1 for _ in chess.SquareSet(chess.BB_FILE_B).carry_rippler()), 2 ** 8)

    def test_mirror(self):
        self.assertEqual(chess.SquareSet(0x00a2_0900_0004_a600).mirror(), 0x00a6_0400_0009_a200)
        self.assertEqual(chess.SquareSet(0x1e22_2212_0e0a_1222).mirror(), 0x2212_0a0e_1222_221e)

    def test_flip(self):
        self.assertEqual(chess.flip_vertical(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.flip_horizontal(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.flip_diagonal(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.flip_anti_diagonal(chess.BB_ALL), chess.BB_ALL)

        s = chess.SquareSet(0x1e22_2212_0e0a_1222)  # Letter R
        self.assertEqual(chess.flip_vertical(s), 0x2212_0a0e_1222_221e)
        self.assertEqual(chess.flip_horizontal(s), 0x7844_4448_7050_4844)
        self.assertEqual(chess.flip_diagonal(s), 0x0000_6192_8c88_ff00)
        self.assertEqual(chess.flip_anti_diagonal(s), 0x00ff_1131_4986_0000)

    def test_len_of_complenent(self):
        squares = chess.SquareSet(~chess.BB_ALL)
        self.assertEqual(len(squares), 0)

        squares = ~chess.SquareSet(chess.BB_BACKRANKS)
        self.assertEqual(len(squares), 48)

    def test_int_conversion(self):
        self.assertEqual(int(chess.SquareSet(chess.BB_CENTER)), 0x0000_0018_1800_0000)
        self.assertEqual(hex(chess.SquareSet(chess.BB_CENTER)), "0x1818000000")
        self.assertEqual(bin(chess.SquareSet(chess.BB_CENTER)), "0b1100000011000000000000000000000000000")

    def test_tolist(self):
        self.assertEqual(chess.SquareSet(chess.BB_LIGHT_SQUARES).tolist().count(True), 32)

    def test_flip_ducktyping(self):
        bb = 0x1e22_2212_0e0a_1222
        squares = chess.SquareSet(bb)
        for f in [chess.flip_vertical, chess.flip_horizontal, chess.flip_diagonal, chess.flip_anti_diagonal]:
            self.assertEqual(int(f(squares)), f(bb))
            self.assertEqual(int(squares), bb)  # Not mutated


class ThreeCheckTestCase(unittest.TestCase):

    def test_get_fen(self):
        board = chess.variant.ThreeCheckBoard()
        self.assertEqual(board.fen(), chess.variant.ThreeCheckBoard.starting_fen)
        self.assertEqual(board.epd(), "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 3+3")

        board.push_san("e4")
        board.push_san("e5")
        board.push_san("Qf3")
        board.push_san("Nc6")
        board.push_san("Qxf7+")
        self.assertEqual(board.fen(), "r1bqkbnr/pppp1Qpp/2n5/4p3/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 2+3 0 3")

        lichess_fen = "r1bqkbnr/pppp1Qpp/2n5/4p3/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 0 3 +1+0"
        self.assertEqual(board.fen(), chess.variant.ThreeCheckBoard(lichess_fen).fen())

    def test_copy(self):
        fen = "8/8/1K2p3/3qP2k/8/8/8/8 b - - 2+1 3 57"
        board = chess.variant.ThreeCheckBoard(fen)
        self.assertEqual(board.copy().fen(), fen)

    def test_mirror_checks(self):
        fen = "3R4/1p3rpk/p4p1p/2B1n3/8/2P1PP2/bPN4P/6K1 w - - 5 29 +2+0"
        board = chess.variant.ThreeCheckBoard(fen)
        self.assertEqual(board, board.mirror().mirror())

    def test_lichess_fen(self):
        board = chess.variant.ThreeCheckBoard("8/8/1K2p3/3qP2k/8/8/8/8 b - - 3 57 +1+2")
        self.assertEqual(board.remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.remaining_checks[chess.BLACK], 1)

    def test_set_epd(self):
        epd = "4r3/ppk3p1/4b2p/2ppPp2/5P2/2P3P1/PP1N2P1/3R2K1 w - - 1+3 foo \"bar\";"
        board, extra = chess.variant.ThreeCheckBoard.from_epd(epd)
        self.assertEqual(board.epd(), "4r3/ppk3p1/4b2p/2ppPp2/5P2/2P3P1/PP1N2P1/3R2K1 w - - 1+3")
        self.assertEqual(extra["foo"], "bar")

    def test_check_is_irreversible(self):
        board = chess.variant.ThreeCheckBoard()

        move = board.parse_san("Nf3")
        self.assertFalse(board.is_irreversible(move))
        board.push(move)

        move = board.parse_san("e5")
        self.assertTrue(board.is_irreversible(move))
        board.push(move)

        move = board.parse_san("Nxe5")
        self.assertTrue(board.is_irreversible(move))
        board.push(move)

        # Lose castling rights.
        move = board.parse_san("Ke7")
        self.assertTrue(board.is_irreversible(move))
        board.push(move)

        # Give check.
        move = board.parse_san("Nc6+")
        self.assertTrue(board.is_irreversible(move))

    def test_three_check_eq(self):
        a = chess.variant.ThreeCheckBoard()
        a.push_san("e4")

        b = chess.variant.ThreeCheckBoard("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1 +0+0")
        c = chess.variant.ThreeCheckBoard("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1 +0+1")

        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(b, c)

    def test_three_check_root(self):
        board = chess.variant.ThreeCheckBoard("r1bq1bnr/pppp1kpp/2n5/4p3/4P3/8/PPPP1PPP/RNBQK1NR w KQ - 2+3 0 4")
        self.assertEqual(board.root().remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.root().remaining_checks[chess.BLACK], 3)
        self.assertEqual(board.copy().root().remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.copy().root().remaining_checks[chess.BLACK], 3)

        board.push_san("Qf3+")
        board.push_san("Ke6")
        board.push_san("Qb3+")
        self.assertEqual(board.root().remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.root().remaining_checks[chess.BLACK], 3)
        self.assertEqual(board.copy().root().remaining_checks[chess.WHITE], 2)
        self.assertEqual(board.copy().root().remaining_checks[chess.BLACK], 3)

    def test_three_check_epd(self):
        board, ops = chess.variant.ThreeCheckBoard.from_epd("rnb1kbnr/pppp1ppp/8/8/2B1Pp1q/8/PPPP2PP/RNBQ1KNR b kq - 3+2 hmvc 3; fmvn 4; bm Qf2+")
        self.assertEqual(board.remaining_checks[chess.WHITE], 3)
        self.assertEqual(board.remaining_checks[chess.BLACK], 2)
        self.assertEqual(board.halfmove_clock, 3)
        self.assertEqual(board.fullmove_number, 4)
        self.assertEqual(ops["bm"], [chess.Move.from_uci("h4f2")])


