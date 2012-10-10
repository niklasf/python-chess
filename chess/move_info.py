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

import chess

class MoveInfo(object):
    """MoveInfo objects hold context sensitive information about moves.

    All parameters are optional and match properties that can be
    set after the object has been created.

    :param move:
        The move object.
    :param piece:
        The piece that has been moved.
    :param san:
        The standard algebraic notation of the move.
    :param captured:
        The piece that has been captured or `None`.
    :param is_enpassant:
        A boolean indicating if the move is an en-passant capture.
    :param is_king_sidle_castle:
        Whether it is a king-side castling move.
    :param is_queen_side_castle:
        Whether it is a queen-side castling move.
    :param is_check:
        Whether the move gives check.
    :param is_checkmate:
        Whether the move gives checkmate.

    If all these properties of two MoveInfo objects are identical, they
    compare as equal.
    """
    def __init__(self, move=None, piece=None, san=None, captured=None,
                 is_enpassant=False, is_king_side_castle=False,
                 is_queen_side_castle=False, is_check=False,
                 is_checkmate=False):
        self.move = move
        self.piece = piece
        self.captured = captured
        self.san = san
        self.is_enpassant = is_enpassant
        self.is_king_side_castle = is_king_side_castle
        self.is_queen_side_castle = is_queen_side_castle
        self.is_check = is_check
        self.is_checkmate = is_checkmate

    def is_castle(self):
        """:return: Whether it is a castling move."""
        return self.is_king_side_castle or self.is_queen_side_castle

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        return (self.move == other.move
            and self.piece == other.piece
            and self.capured == other.captured
            and self.san == other.san
            and self.is_enpassant == other.is_enpassant
            and self.is_king_side_castle == other.is_king_side_castle
            and self.is_queen_side_castle == other.is_queen_side_castle
            and self.is_check == other.is_check
            and self.is_checkmate == other.is_checkmate)

    def __ne__(self, other):
       return not self.__eq__(other)

    def __str__(self):
        return self.san

    def __repr__(self):
        return (
            "MoveInfo(move=%s, piece=%s, san=%s, captured=%s, is_enpassant=%s, "
            "is_king_side_castle=%s, is_queen_side_castle=%s, is_check=%s, "
            "is_checkmate=%s)") % (
                repr(self.move), repr(self.piece), repr(self.san),
                repr(self.captured), repr(self.is_enpassant),
                repr(self.is_king_side_castle), repr(self.is_queen_side_castle),
                repr(self.is_check), repr(self.is_checkmate))
