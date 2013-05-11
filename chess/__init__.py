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

__author__ = "Niklas Fiekas"
__copyright__ = "Copyright 2013, Niklas Fiekas"
__license__ = "GPL"
__version__ = "0.0.4"
__maintainer__ = "Niklas Fiekas"
__email__ = "niklas.fiekas@tu-clausthal.de"
__status__ = "Development"

import inspect

# Import from libchess.
from libchess import START_FEN
from libchess import opposite_color
from libchess import Square
from libchess import Piece
from libchess import Move
from libchess import Position
from libchess import PolyglotOpeningBookEntry

# Stable.
from chess.game_header_bag import GameHeaderBag

# Design phase.
from chess.polyglot_opening_book import PolyglotOpeningBook
from chess.game_node import GameNode
from chess.game import Game
from chess.pgn_file import PgnFile

__all__ = [ name for name, obj in locals().items() if not inspect.ismodule(obj) ]
