#!/usr/bin/env python3

# Almost all tests adapted from https://github.com/lichess-org/scalachess/blob/8c94e2087f83affb9718fd2be19c34866c9a1a22/test-kit/src/test/scala/format/BinaryFenTest.scala#L1

import asyncio
import copy
import csv
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

    _VARIANT_CLASSES = {
        "standard": lambda fen: chess.Board(fen=fen, chess960=False),
        "chess960": lambda fen: chess.Board(fen=fen, chess960=True),
        "koth": lambda fen: chess.variant.KingOfTheHillBoard(fen=fen),
        "three_check": lambda fen: chess.variant.ThreeCheckBoard(fen=fen),
        "antichess": lambda fen: chess.variant.AntichessBoard(fen=fen),
        "atomic": lambda fen: chess.variant.AtomicBoard(fen=fen),
        "horde": lambda fen: chess.variant.HordeBoard(fen=fen),
        "racing_kings": lambda fen: chess.variant.RacingKingsBoard(fen=fen),
        "crazyhouse": lambda fen: chess.variant.CrazyhouseBoard(fen=fen),
    }

    def _run_case(self, binary_fen_hex, canonical_hex, fen, variant_name):
        expected_board = self._VARIANT_CLASSES[variant_name](fen)

        decoded_board, std_mode = BinaryFen.decode(bytes.fromhex(binary_fen_hex))

        encoded_hex = BinaryFen.encode(expected_board, std_mode=std_mode).hex()
        self.assertEqual(
            encoded_hex, canonical_hex, "encode(board) must equal canonical_binary_fen"
        )

        self.assertEqual(
            decoded_board,
            expected_board,
            "decode(canonical_binary_fen) must equal board from FEN",
        )

        parsed = BinaryFen.parse_from_bytes(bytes.fromhex(binary_fen_hex))
        self.assertEqual(
            parsed.to_canonical().to_bytes().hex(),
            canonical_hex,
            "parse_from_bytes(binary_fen).to_canonical() must equal canonical_binary_fen",
        )

    def test_data_driven(self):
        csv_path = os.path.join(os.path.dirname(__file__), "data/test_binary_fen_cases.csv")
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                with self.subTest(
                    binary_fen=row["binary_fen"], fen=row["fen"], variant=row["variant"]
                ):
                    self._run_case(
                        binary_fen_hex=row["binary_fen"],
                        canonical_hex=row["canonical_binary_fen"],
                        fen=row["fen"],
                        variant_name=row["variant"] or "standard",
                    )

    def test_fuzz_fails(self):
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
            "d8805347e76003102228687fffff41b19e2bff00000100020220c6",
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

def dbg(a, b):
    from pprint import pprint
    from deepdiff import DeepDiff
    pprint(DeepDiff(a, b),indent=2)

if __name__ == "__main__":
    print("#"*80)
    unittest.main()