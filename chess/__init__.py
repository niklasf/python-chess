# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import inspect

# Import from libchess.
from libchess import START_FEN
from libchess import Square
from libchess import Piece
from libchess import Move
from libchess import Position

# Stable.
from chess.exceptions import FenError
from chess.exceptions import PgnError
from chess.exceptions import MoveError
from chess.zobrist_hasher import ZobristHasher
from chess.game_header_bag import GameHeaderBag

# Design phase.
from chess.polyglot_opening_book import PolyglotOpeningBook
from chess.game_node import GameNode
from chess.game import Game
from chess.pgn_file import PgnFile


def opposite_color(color):
    """:return: The opposite color.

    :param color:
        "w" for white or "b" for black.
    """
    if color == "w":
        return "b"
    elif color == "b":
        return "w"
    else:
        raise ValueError("Invalid color: %s. Expected 'w' or 'b'." % repr(color))

__all__ = [ name for name, obj in locals().items() if not inspect.ismodule(obj) ]
