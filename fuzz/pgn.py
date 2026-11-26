import io
import logging
import sys

import atheris

with atheris.instrument_imports():
    import chess.pgn


# The default parser logs errors for syntax errors.
logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)


def fuzz(buf: bytes) -> None:
    try:
        pgn = io.StringIO(buf.decode("utf-8"))
    except UnicodeDecodeError:
        return

    while True:
        game = chess.pgn.read_game(pgn)
        if game is None:
            break

        repr(game)
        if not game.errors:
            str(game)


if __name__ == "__main__":
    atheris.Setup(sys.argv, fuzz)
    atheris.Fuzz()
