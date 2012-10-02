import inspect

from libchess.piece import Piece
from libchess.square import Square

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
