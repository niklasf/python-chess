import inspect

from chess.piece import Piece
from chess.square import Square
from chess.move import Move
from chess.move_info import MoveInfo
from chess.position import Position
from chess.zobrist_hasher import ZobristHasher

from chess.exceptions import FenError

def opposite_color(color):
    """Gets the opposite color.

    Args:
        color: "w" for white or "b" for black.

    Returns:
        The opposite color as "w" for white or "b" for black.
    """
    assert color in ["w", "b"]
    if color == "w":
        return "b"
    elif color == "b":
        return "w"

__all__ = [ name for name, obj in locals().items() if not inspect.ismodule(obj) ]
