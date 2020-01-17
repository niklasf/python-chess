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
        str(chess.pgn.read_game(pgn))


if __name__ == "__main__":
    fuzz()
