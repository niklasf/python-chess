import sys

import atheris

with atheris.instrument_imports():
    import chess
    import chess.variant


def key(board: chess.Board) -> tuple[type[chess.Board], str]:
    return type(board), board.fen(en_passant="fen", shredder=True, promoted=True)


def fuzz(buf: bytes) -> None:
    try:
        board = chess.variant.from_packed(buf, chess960=True)
    except ValueError:
        return

    board.status()
    repacked = board.pack(en_passant="fen")
    unpacked = chess.variant.from_packed(repacked, chess960=True)
    assert key(unpacked) == key(board), (key(board), key(unpacked))
    assert unpacked.pack(en_passant="fen") == repacked


if __name__ == "__main__":
    atheris.Setup(sys.argv, fuzz)
    atheris.Fuzz()
