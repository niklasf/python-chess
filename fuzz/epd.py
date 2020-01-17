import chess

from pythonfuzz.main import PythonFuzz


@PythonFuzz
def fuzz(buf):
    try:
        epd = buf.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        try:
            board, ops = chess.Board.from_epd(epd)
        except ValueError as err:
            pass
        else:
            sanitized_epd = board.epd(**ops)
            sanitized_board, sanitized_ops = chess.Board.from_epd(sanitized_epd)
            assert board == sanitized_board
            assert ops == sanitized_ops, (ops, sanitized_ops)


if __name__ == "__main__":
    fuzz()
