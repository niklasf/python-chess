# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2015 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import chess


SUICIDE_STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class SuicideBoard(chess.Board):

    def pin_mask(self, color, square):
        return chess.BB_ALL

    def _attacked_for_king(self, path):
        return False

    def _ep_skewered(self, capturer_mask):
        return False

    def is_check(self):
        return False

    def is_into_check(self, move):
        return False

    def was_into_check(self, move):
        return False

    def _material_balance(self):
        return (chess.pop_count(self.occupied_co[self.turn]) -
                chess.pop_count(self.occupied_co[not self.turn]))

    def is_variant_win(self):
        if not self.occupied_co[self.turn]:
            return True
        else:
            return self.is_stalemate() and self._material_balance() < 0

    def is_variant_loss(self):
        if not self.occupied_co[self.turn]:
            return False
        else:
            return self.is_stalemate() and self._material_balance() > 0

    def is_variant_draw(self):
        if not self.occupied_co[self.turn]:
            return False
        else:
            return self.is_stalemate() and self._material_balance() == 0

    def is_insufficient_material(self):
        # TODO
        return False

    def generate_evasions(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        return
        yield

    def generate_non_evasions(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        # Generate captures first.
        found_capture = False
        for move in self.generate_pseudo_legal_captures():
            if chess.BB_SQUARES[move.from_square] & from_mask and chess.BB_SQUARES[move.to_square] & to_mask:
                yield move
            found_capture = True

        # Captures are mandatory. Stop here if any were found.
        if not found_capture:
            not_them = to_mask & ~self.occupied_co[not self.turn]
            for move in self.generate_pseudo_legal_moves(from_mask, not_them):
                if not self.is_en_passant(move):
                    yield move

    def status(self):
        status = super(SuicideBoard, self).status()
        status &= ~chess.STATUS_NO_WHITE_KING
        status &= ~chess.STATUS_NO_BLACK_KING
        status &= ~chess.STATUS_TOO_MANY_KINGS
        status &= ~chess.STATUS_OPPOSITE_CHECK
        return status


GIVEAWAY_STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"

class GiveawayBoard(SuicideBoard):

    def __init__(self, fen=GIVEAWAY_STARTING_FEN, chess960=False):
        super(GiveawayBoard, self).__init__(fen, chess960)

        # Give back castling rights that were removed when resetting.
        if fen == chess.STARTING_FEN:
            self.castling_rights = chess.BB_A1 | chess.BB_H1 | chess.BB_A8 | chess.BB_H8

    def reset(self):
        super(GiveawayBoard, self).reset()
        self.castling_rights = chess.BB_VOID

    def is_variant_win(self):
        return not self.occupied_co[self.turn] or self.is_stalemate()

    def is_variant_loss(self):
        return False

    def is_variant_draw(self):
        return False
