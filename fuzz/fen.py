import sys

import atheris

with atheris.instrument_imports():
    import chess


def fuzz(buf: bytes) -> None:
    try:
        fen = buf.decode("utf-8")
    except UnicodeDecodeError:
        return

    try:
        board = chess.Board(fen)
    except ValueError:
        return

    sanitized_fen = board.fen()
    board.status()
    list(board.legal_moves)
    sanitized_board = chess.Board(sanitized_fen)
    assert sanitized_board.fen() == sanitized_fen


if __name__ == "__main__":
    atheris.Setup(sys.argv, fuzz)
    atheris.Fuzz()
