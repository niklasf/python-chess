import chess.binary_fen
from chess.binary_fen import BinaryFen

from pythonfuzz.main import PythonFuzz


@PythonFuzz
def fuzz(buf):
    binary_fen = BinaryFen.parse_from_bytes(buf)
    try:
        board, std_mode = binary_fen.to_board()
    except ValueError:
        pass
    else:
        board.status()
        list(board.legal_moves)
        binary_fen2 = BinaryFen.parse_from_board(board,std_mode=std_mode)
        encoded = binary_fen2.to_bytes()
        board2, std_mode2 = BinaryFen.decode(encoded)
        assert board == board2
        assert binary_fen2 == binary_fen2.to_canonical(), "from_board should be canonical"
        assert binary_fen.to_canonical() == binary_fen2.to_canonical()
        assert std_mode == std_mode2


if __name__ == "__main__":
    fuzz()
