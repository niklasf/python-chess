import chess
import chess.variant

from pythonfuzz.main import PythonFuzz


def key(board):
    return type(board), board.fen(en_passant="fen", shredder=True, promoted=True)


@PythonFuzz
def fuzz(buf):
    try:
        board = chess.variant.from_packed(buf, chess960=True)
    except ValueError:
        pass
    else:
        board.status()
        repacked = board.pack(en_passant="fen")
        unpacked = chess.variant.from_packed(repacked, chess960=True)
        assert key(unpacked) == key(board), (key(board), key(unpacked))
        assert unpacked.pack(en_passant="fen") == repacked


if __name__ == "__main__":
    fuzz()
