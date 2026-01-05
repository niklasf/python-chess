#!/usr/bin/env python3

# Almost all tests adapted from https://github.com/lichess-org/scalachess/blob/8c94e2087f83affb9718fd2be19c34866c9a1a22/test-kit/src/test/scala/format/BinaryFenTest.scala#L1

import asyncio
import copy
import logging
import os
import os.path
import platform
import sys
import tempfile
import textwrap
import unittest
import io

import chess
import chess.variant
import chess.binary_fen

from dataclasses import asdict

from chess import Board
from chess.binary_fen import BinaryFen, ChessHeader, VariantHeader

KOTH = chess.variant.KingOfTheHillBoard
THREE_CHECKS = chess.variant.ThreeCheckBoard
ANTI = chess.variant.AntichessBoard
ATOMIC = chess.variant.AtomicBoard
HORDE =  chess.variant.HordeBoard
RK = chess.variant.RacingKingsBoard
ZH = chess.variant.CrazyhouseBoard

class BinaryFenTestCase(unittest.TestCase):

    def test_nibble_roundtrip(self):
        for lo in range(16):
            for hi in range(16):
                data = bytearray()
                chess.binary_fen._write_nibbles(data, lo, hi)
                read_lo, read_hi = chess.binary_fen._read_nibbles(iter(data))
                self.assertEqual(lo, read_lo)
                self.assertEqual(hi, read_hi)

    def test_std_mode_eq(self):
        self.assertEqual(ChessHeader.STANDARD,ChessHeader.from_int_opt(0))

    def test_bitboard_roundtrip(self):
        test_bitboards = [
            0x0000000000000000,
            0xFFFFFFFFFFFFFFFF,
            0x1234567890ABCDEF,
            0x0F0F0F0F0F0F0F0F,
            0xF0F0F0F0F0F0F0F0,
            0x8000000000000001,
            0x7FFFFFFFFFFFFFFE,
        ]
        for bb in test_bitboards:
            data = bytearray()
            chess.binary_fen._write_bitboard(data, bb)
            read_bb = chess.binary_fen._read_bitboard(iter(data))
            self.assertEqual(bb, read_bb)

    def test_leb128_roundtrip(self):
        test_values = [
            0,
            1,
            3,
            127,
            128,
            255,
            16384,
            2097151,
            268435455,
            2147483647,
        ]
        for value in test_values:
            data = bytearray()
            chess.binary_fen._write_leb128(data, value)
            read_value = chess.binary_fen._read_leb128(iter(data))
            self.assertEqual(value, read_value)

    def test_to_canonical_1(self):
        # illegal position, but it should not matter
        canon = BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [15, 15, 15],
            halfmove_clock=3,
            plies=5,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None,
            )
        cases = [BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [11, 15, 11],
            halfmove_clock=3,
            plies=4,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None
            ),
        BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [15, 15, 11],
            halfmove_clock=3,
            plies=4,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None
            ),
        BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [11, 15, 15],
            halfmove_clock=3,
            plies=4,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None
            ),
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertNotEqual(canon, case)
                canon_case = case.to_canonical()
                self.assertEqual(canon, canon_case)

    def test_to_canonical_2(self):
        # illegal position, but it should not matter
        canon = BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [15, 15, 15],
            halfmove_clock=3,
            plies=5,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None,
            )
        cases = [BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [11, 15, 11],
            halfmove_clock=3,
            plies=5,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None
            ),
        BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [15, 15, 11],
            halfmove_clock=3,
            plies=5,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None
            ),
        BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [11, 15, 15],
            halfmove_clock=3,
            plies=5,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None
            ),
        BinaryFen(
            occupied=chess.BB_A1 | chess.BB_B1 | chess.BB_C1,
            nibbles = [11, 11, 11],
            halfmove_clock=3,
            plies=5,
            variant_header=ChessHeader.STANDARD.value,
            variant_data=None
            ),
        ]
        for case in cases:
            with self.subTest(case=case):
                self.assertNotEqual(canon, case)
                canon_case = case.to_canonical()
                self.assertEqual(canon, canon_case)

    def test_binary_fen_roundtrip(self):
        cases = [
            Board(fen="8/8/8/8/8/8/8/8 w - - 0 1"),
            Board(fen="8/8/8/8/8/8/8/8 b - - 0 1"),
            Board(fen="8/8/8/8/8/8/8/7k b - - 0 1"),
            Board(fen="8/8/8/8/8/8/8/8 w - - 0 2"),
            Board(fen="8/8/8/8/8/8/8/8 b - - 0 2"),
            Board(fen="8/8/8/8/8/8/8/8 b - - 100 432"),
            Board(fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"),
            Board(fen="4nrk1/1pp3pp/p4p2/4P3/2BB1n2/8/PP3P1P/2K3R1 b - - 1 25"),
            Board(fen="4nrk1/1pp3pp/p4p2/4P3/2BB1n2/8/PP3P1P/2K3R1 b - - 1 25"),
            Board(fen="5k2/6p1/8/1Pp5/6P1/8/8/3K4 w - c6 0 1"),
            Board(fen="4k3/8/8/8/3pP3/8/6N1/7K b - e3 0 1"),
            Board(fen="r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"),
            Board(fen="r1k1r2q/p1ppp1pp/8/8/8/8/P1PPP1PP/R1K1R2Q w KQkq - 0 1",chess960=True),
            Board(fen="r1k2r1q/p1ppp1pp/8/8/8/8/P1PPP1PP/R1K2R1Q w KQkq - 0 1", chess960=True),
            Board(fen="8/8/8/4B2b/6nN/8/5P2/2R1K2k w Q - 1 1",  chess960=True),
            Board(fen="2r5/8/8/8/8/8/6PP/k2KR3 w K - 0 2",  chess960=True),
            Board(fen="4r3/3k4/8/8/8/8/6PP/qR1K1R2 w KQ - 2 1", chess960=True),
            Board(fen="4rrk1/pbbp2p1/1ppnp3/3n1pqp/3N1PQP/1PPNP3/PBBP2P1/4RRK1 w Ff - 0 3",  chess960=True),
            Board(fen="8/8/8/1k6/3Pp3/8/8/4KQ2 b - d3 3 1"),
            Board(fen="r2r3k/p7/3p4/8/8/P6P/8/R3K2R b KQq - 0 4",chess960=True),
            Board(fen="rn2k1r1/ppp1pp1p/3p2p1/5bn1/P7/2N2B2/1PPPPP2/2BNK1RR w Gkq - 4 11", chess960=True),
            Board(fen="8/8/8/8/8/8/2Rk4/1K6 w - - 0 1"),

            HORDE(fen="rn1qkb1r/3bn1p1/2p3P1/pPP2P2/P1PPP1P1/P1PP1PPP/PPPPPPPP/PPPPPPPP w kq a6 0 12"),

            ANTI("8/2p1p2p/2Q1N2B/8/p7/N7/PPP1P1PP/R4B1R b - - 0 13"),
            ANTI("8/p6p/4p3/1P4P1/Pp4p1/3P4/7P/8 b - a3 0 1"),
            ANTI("8/p6p/4p3/1P4P1/1p4pP/3P4/P7/8 b - h3 0 1"),
            ANTI("8/7p/4p3/pP4P1/1p1P2p1/8/P6P/8 w - a6 0 2"),
            ANTI("8/p7/4p3/1P4Pp/1p1P2p1/8/P6P/8 w - h6 0 2"),

            ATOMIC(fen="rnbq3r/ppp1p1pp/5p2/3p4/8/8/PPPPPPPP/RNBQKB1R b KQ - 0 4"),
            ATOMIC(fen="8/6pp/2p2p1n/3p4/4P3/B6P/3P1PP1/1r2K2R b K - 0 17"),

            RK(fen="8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1"),
            RK(fen="8/8/8/8/8/6K1/krbnNBR1/qrbnNBRQ b - - 1 1"),

            KOTH(fen="rnbq1bnr/ppp2ppp/3k4/4p2Q/3PK3/8/PPP2PPP/RNB2BNR b - - 0 7"),

            THREE_CHECKS(fen="1r3rk1/pbp1N1pp/3p1q2/1p2bp2/7P/2PBB1P1/PP3Q1R/R5K1 b - - 3 21 +2+1"),

            ZH(fen="1r3Q1n/p1kp3p/1p2ppq1/2p2b2/8/3P2P1/PPP1PPBP/R4RK1/NRpnnbb w - - 2 28"),
            ZH(fen="b2nkbnQ~/p1pppp1p/pP1q2p1/r7/8/R5PR/P1PP1P1P/1NBQ1BNK/R w - - 1 2"),
            ZH(fen="8/8/8/8/8/8/8/8/ w - - 0 1"),
            ZH(fen="r~n~b~q~kb~n~r~/pppppppp/8/8/8/8/PPPPPPPP/RN~BQ~KB~NR/ w KQkq - 0 1"),
        ]
        for case in cases:
            case_fen = case.fen()
            with self.subTest(fen=case_fen):
                bin_fen = BinaryFen.parse_from_board(case)
                bin_fen2 = BinaryFen.parse_from_bytes(bin_fen.to_bytes())
                self.assertEqual(bin_fen2, bin_fen2.to_canonical(), "from_bytes should produce canonical value")
                self.assertEqual(bin_fen.to_canonical(), bin_fen2.to_canonical())
                decoded, _ = bin_fen2.to_board()
                self.assertEqual(case, decoded)


    # tests that failed the fuzzer at some point
    def test_fuzzer_fail(self):
        fuzz_fails = [
        "23d7",
        "e17f11efd84522d34878ffffffa600000000ce1b23ffff000943",
        "20f7076f1718f99824a5020724b3cfc1020146ae00004f85ae28aebc",
        "edf9b3c5cb7fa5008000004081c83e4092a7e63dd95a",
        "f7cef6e64ed47a4ede172a100000009b004c909b",
        "bb7cb00cc3f31dc3f325b8",
        "4584aced8100da50a20bd7251705a15b108000251705",
        "77ff05111f77111f4214e803647fff6429f0a2f65933310185016400000045bf1e8be6b013ed02",
        "55d648e9a20fd600400000e9a29c0010043b26fb41d50a50",
        "d8805347e76003102228687fffff41b19e2bff00000100020220c6"
        ]
        for fuzz_fail in fuzz_fails:
            with self.subTest(fuzz_fail=fuzz_fail):
                data = bytes.fromhex(fuzz_fail)
                binary_fen = BinaryFen.parse_from_bytes(data)
                try:
                    board, std_mode = binary_fen.to_board()
                except ValueError:
                    continue
                # print("binary_fen", binary_fen)
                # print("ep square", board.ep_square)
                # print("fullmove", board.fullmove_number)
                # print("halfmove_clock", board.halfmove_clock)
                # print("fen", board.fen())
                # print()
                # should not error
                board.status()
                list(board.legal_moves)
                binary_fen2 = BinaryFen.parse_from_board(board,std_mode=std_mode)
                # print("encoded", binary_fen2.to_bytes().hex())
                # print("binary_fen2", binary_fen2)
                # dbg(binary_fen, binary_fen2)
                # print("CANONICAL")
                # dbg(binary_fen.to_canonical(), binary_fen)
                self.assertEqual(binary_fen2, binary_fen2.to_canonical(), "from board should produce canonical value")
                self.assertEqual(binary_fen.to_canonical(), binary_fen2.to_canonical())
                board2, std_mode2 = binary_fen2.to_board()
                self.assertEqual(board, board2)
                self.assertEqual(std_mode, std_mode2)


    def test_read_binary_fen_std(self):
        test_cases = [
            ("0000000000000000", "8/8/8/8/8/8/8/8 w - - 0 1"),
            ("00000000000000000001", "8/8/8/8/8/8/8/8 b - - 0 1"),
            ("000000000000000064df06", "8/8/8/8/8/8/8/8 b - - 100 432"),
            ("ffff00001000efff2d844ad200000000111111113e955fe3", "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"),
            ("20400006400000080ac0b1", "5k2/6p1/8/1Pp5/6P1/8/8/3K4 w - c6 0 1"),
            ("10000000180040802ac10f", "4k3/8/8/8/3pP3/8/6N1/7K b - e3 0 1"),
            # TODO FIXME, this is encoded with `standard` variant but with chess960 castling
            # should this be accepted? for now basing on scalachess behavior
            ("8901080000810091ad0d10e1f70007", "r2r3k/p7/3p4/8/8/P6P/8/R3K2R b KQq - 0 4"),

            ("95dd00000000dd95ad8d000000111111be9e", "r1k1r2q/p1ppp1pp/8/8/8/8/P1PPP1PP/R1K1R2Q w KQkq - 0 1"),
            ("00000002180000308a1c0f030103", "8/8/8/1k6/3Pp3/8/8/4KQ2 b - d3 3 1")
        ]
        for binary_fen, expected_fen in test_cases:
            with self.subTest(binary_fen=binary_fen, expected_fen=expected_fen):
                self.check_binary(binary_fen, expected_fen)


    # for python-chess, 960 is handled the same as std
    def test_read_binary_fen_960(self):
        test_cases = [("704f1ee8e81e4f70d60a44000002020813191113511571be000402", "4rrk1/pbbp2p1/1ppnp3/3n1pqp/3N1PQP/1PPNP3/PBBP2P1/4RRK1 w Ff - 0 3")]
        for binary_fen, expected_fen in test_cases:
            with self.subTest(binary_fen=binary_fen, expected_fen=expected_fen):
                self.check_binary(binary_fen, expected_fen)

    def test_read_binary_fen_variants(self):
        test_cases = [("ffff00000000ffff2d844ad200000000111111113e955be3000004", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", KOTH),
        ("ffff00000000ffff2d844ad200000000111111113e955be363000501", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 99 1 +0+1", THREE_CHECKS),
        ("00800000000008001a000106", "8/7p/8/8/8/8/3K4/8 b - - 0 1", ANTI),
        ("ffff00000000ffff2d844ad200000000111111113e955be3020407", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 2 3", ATOMIC),
        ("ffff0066ffffffff000000000000000000000000000000000000111111113e955be3000008", "rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1", HORDE),
        ("000000000000ffff793542867b3542a6000009", "8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1", RK),
        ("ffff00000000ffff2d844ad200000000111111113e955be300e407010000000000ef0000000000002a", "r~n~b~q~kb~n~r~/pppppppp/8/8/8/8/PPPPPPPP/RN~BQ~KB~NR/ w KQkq - 0 499", ZH),
        ("ffff00000000ffff2d844ad200000000111111113e955be30000010000000000", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR/ w KQkq - 0 1", ZH)
        ]
        for binary_fen_str, expected_fen, variant in test_cases:
            with self.subTest(binary_fen=binary_fen_str, expected_fen=expected_fen, variant=variant):
                self.check_binary(binary_fen_str, expected_fen, variant)


    def check_binary(self, binary_fen_str, expected_fen, variant = None):
        compressed = bytes.fromhex(binary_fen_str)
        board, std_mode = BinaryFen.decode(compressed)
        binary_fen1 = BinaryFen.parse_from_bytes(compressed)
        from_fen = chess.Board(fen=expected_fen, chess960=True) if variant is None else variant(fen=expected_fen)
        encoded = BinaryFen.encode(board,std_mode=std_mode)
        binary_fen2 = BinaryFen.parse_from_board(board,std_mode=std_mode)
        self.maxDiff = None
        self.assertEqual(binary_fen2, binary_fen2.to_canonical(), "from board should produce canonical value")
        self.assertEqual(binary_fen1.to_canonical(), binary_fen2.to_canonical())
        self.assertEqual(board, from_fen)
        self.assertEqual(encoded.hex(), compressed.hex())

def dbg(a, b):
    from pprint import pprint
    from deepdiff import DeepDiff
    pprint(DeepDiff(a, b),indent=2)

if __name__ == "__main__":
    print("#"*80)
    unittest.main()