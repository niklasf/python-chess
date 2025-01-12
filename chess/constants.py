"""
Constants used in init file related to board and moves.
"""

import re


FILE_NAMES = ["a", "b", "c", "d", "e", "f", "g", "h"]

RANK_NAMES = ["1", "2", "3", "4", "5", "6", "7", "8"]
RANK_SET = set(RANK_NAMES)

CASTLING_K = {"O-O", "O-O+", "O-O#", "0-0", "0-0+", "0-0#"}
CASTLING_Q = {"O-O-O", "O-O-O+", "O-O-O#", "0-0-0", "0-0-0+", "0-0-0#"}

SAN_NULL_MOVES = {"--", "Z0", "0000", "@@@@"}

OPCODES = {"pv", "am", "bm"}

UNICODE_PIECE_SYMBOLS = {
    "R": "♖", "r": "♜",
    "N": "♘", "n": "♞",
    "B": "♗", "b": "♝",
    "Q": "♕", "q": "♛",
    "K": "♔", "k": "♚",
    "P": "♙", "p": "♟",
}


SAN_REGEX = re.compile(r"^([NBKRQ])?([a-h])?([1-8])?[\-x]?([a-h][1-8])(=?[nbrqkNBRQK])?[\+#]?\Z")

FEN_CASTLING_REGEX = re.compile(r"^(?:-|[KQABCDEFGH]{0,2}[kqabcdefgh]{0,2})\Z")

SPACE_CHARS = {" ", "\n", "\t", "\r"}
