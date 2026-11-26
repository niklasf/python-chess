import sys

import atheris

with atheris.instrument_imports():
    import chess


def fuzz(buf: bytes) -> None:
    try:
        epd = buf.decode("utf-8")
    except UnicodeDecodeError:
        return

    try:
        board, ops = chess.Board.from_epd(epd)
    except ValueError:
        return

    sanitized_epd = board.epd(**ops)
    sanitized_board, sanitized_ops = chess.Board.from_epd(sanitized_epd)
    assert board == sanitized_board
    assert ops == sanitized_ops, (ops, sanitized_ops)


if __name__ == "__main__":
    atheris.Setup(sys.argv, fuzz)
    atheris.Fuzz()
