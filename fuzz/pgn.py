import io
import logging

import chess.pgn

from pythonfuzz.main import PythonFuzz


# The default parser logs errors for syntax errors.
logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)


@PythonFuzz
def fuzz(buf):
    try:
        pgn = io.StringIO(buf.decode("utf-8"))
    except UnicodeDecodeError:
        pass
    else:
        while True:
            game = chess.pgn.read_game(pgn)
            if game is None:
                break

            repr(game)
            if not game.errors:
                str(game)


if __name__ == "__main__":
    fuzz()
