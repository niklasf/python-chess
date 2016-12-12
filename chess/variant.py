# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2016 Niklas Fiekas <niklas.fiekas@backscattering.de>
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
import copy
import itertools


class SuicideBoard(chess.Board):

    aliases = ["Suicide", "Suicide chess"]
    uci_variant = "suicide"

    tbw_suffix = ".stbw"
    tbz_suffix = ".stbz"
    tbw_magic = [0x7b, 0xf6, 0x93, 0x15]
    tbz_magic = [0xe4, 0xcf, 0xe7, 0x23]
    pawnless_tbw_suffix = ".gtbw"
    pawnless_tbz_suffix = ".gtbz"
    pawnless_tbw_magic = [0xBC, 0x55, 0xBC, 0x21]
    pawnless_tbz_magic = [0xD6, 0xF5, 0x1B, 0x50]
    connected_kings = True
    one_king = False
    captures_compulsory = True

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
        # Enough material.
        if self.knights or self.rooks or self.queens or self.kings:
            return False

        # Must have bishops.
        if not (self.occupied_co[chess.WHITE] & self.bishops and self.occupied_co[chess.BLACK] & self.bishops):
            return False

        # All pawns must be blocked.
        w_pawns = self.pawns & self.occupied_co[chess.WHITE]
        b_pawns = self.pawns & self.occupied_co[chess.BLACK]

        b_blocked_pawns = chess.shift_up(w_pawns) & b_pawns
        w_blocked_pawns = chess.shift_down(b_pawns) & w_pawns

        if (b_blocked_pawns | w_blocked_pawns) != self.pawns:
            return False

        turn = self.turn
        turn = chess.WHITE
        if any(self.generate_pseudo_legal_moves(self.pawns)):
            return False
        turn = chess.BLACK
        if any(self.generate_pseudo_legal_moves(self.pawns)):
            return False
        self.turn = turn

        # Bishop and pawns of each side are on distinct color complexes.
        if self.occupied_co[chess.WHITE] & chess.BB_DARK_SQUARES == 0:
            return self.occupied_co[chess.BLACK] & chess.BB_LIGHT_SQUARES == 0
        elif self.occupied_co[chess.WHITE] & chess.BB_LIGHT_SQUARES == 0:
            return self.occupied_co[chess.BLACK] & chess.BB_DARK_SQUARES == 0
        else:
            return False

    def generate_pseudo_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        for move in super(SuicideBoard, self).generate_pseudo_legal_moves(from_mask, to_mask):
            # Add king promotions.
            if move.promotion == chess.QUEEN:
                yield chess.Move(move.from_square, move.to_square, chess.KING)

            yield move

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

    def is_legal(self, move):
        if not super(SuicideBoard, self).is_legal(move):
            return False

        if self.is_capture(move):
            return True
        else:
            return not any(self.generate_pseudo_legal_captures())

    def status(self):
        status = super(SuicideBoard, self).status()
        status &= ~chess.STATUS_NO_WHITE_KING
        status &= ~chess.STATUS_NO_BLACK_KING
        status &= ~chess.STATUS_TOO_MANY_KINGS
        status &= ~chess.STATUS_OPPOSITE_CHECK
        return status


class GiveawayBoard(SuicideBoard):

    aliases = ["Giveaway", "Giveaway chess", "Anti", "Antichess", "Anti chess"]
    uci_variant = "giveaway"
    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"

    tbw_suffix = ".gtbw"
    tbz_suffix = ".gtbz"
    tbw_magic = [0xBC, 0x55, 0xBC, 0x21]
    tbz_magic = [0xD6, 0xF5, 0x1B, 0x50]
    pawnless_tbw_suffix = ".stbw"
    pawnless_tbz_suffix = ".stbz"
    pawnless_tbw_magic = [0x7b, 0xf6, 0x93, 0x15]
    pawnless_tbz_magic = [0xe4, 0xcf, 0xe7, 0x23]

    def __init__(self, fen=starting_fen, chess960=False):
        super(GiveawayBoard, self).__init__(fen, chess960)

    def reset(self):
        super(GiveawayBoard, self).reset()
        self.castling_rights = chess.BB_VOID

    def is_variant_win(self):
        return not self.occupied_co[self.turn] or self.is_stalemate()

    def is_variant_loss(self):
        return False

    def is_variant_draw(self):
        return False


class AtomicBoard(chess.Board):

    aliases = ["Atomic", "Atom", "Atomic chess"]
    uci_variant = "atomic"

    tbw_suffix = ".atbw"
    tbz_suffix = ".atbz"
    tbw_magic = [0x55, 0x8D, 0xA4, 0x49]
    tbz_magic = [0x91, 0xA9, 0x5E, 0xEB]
    connected_kings = True
    one_king = True

    def is_variant_win(self):
        return self.kings and not self.kings & self.occupied_co[not self.turn]

    def is_variant_loss(self):
        return self.kings and not self.kings & self.occupied_co[self.turn]

    def is_insufficient_material(self):
        if self.is_variant_loss() or self.is_variant_win():
            return False

        if self.pawns or self.queens:
            return False

        if chess.pop_count(self.KNIGHT | self.BISHOP | self.ROOK) == 1:
            return True

        # Only knights.
        if self.occupied == (self.kings | self.knights):
            return chess.pop_count(self.knights) <= 2

        # Only bishops.
        if self.occupied == (self.kings | self.bishops):
            # All bishops on opposite colors.
            if not self.pieces_mask(chess.BISHOP, chess.WHITE) & chess.BB_DARK_SQUARES:
                return not self.pieces_mask(chess.BISHOP, chess.BLACK) & chess.BB_LIGHT_SQUARES
            if not self.pieces_mask(chess.BISHOP, chess.WHITE) & chess.BB_LIGHT_SQUARES:
                return not self.pieces_mask(chess.BISHOP, chess.BLACK) & chess.BB_DARK_SQUARES

        return False

    def _attacked_for_king(self, path):
        # Can castle onto attacked squares if they are connected to the
        # enemy king.
        enemy_kings = self.kings & self.occupied_co[not self.turn]
        enemy_king = chess.bit_scan(enemy_kings)
        while enemy_king != -1 and enemy_king is not None:
            path &= ~chess.BB_KING_ATTACKS[enemy_king]
            enemy_king = chess.bit_scan(enemy_kings, enemy_king + 1)

        return super(AtomicBoard, self)._attacked_for_king(path)

    def _kings_connected(self):
        kings = self.kings & self.occupied_co[chess.WHITE]
        king_square = chess.bit_scan(kings)
        while king_square != -1 and king_square is not None:
            if chess.BB_KING_ATTACKS[king_square] & self.kings & self.occupied_co[chess.BLACK]:
                return True

            king_square = chess.bit_scan(kings, king_square + 1)

        return False

    def _push_capture(self, move, capture_square, piece_type, was_promoted):
        # Explode the capturing piece.
        self._remove_piece_at(move.to_square)

        # Explode all non pawns around.
        explosion_radius = chess.BB_KING_ATTACKS[move.to_square] & ~self.pawns
        explosion = chess.bit_scan(explosion_radius)
        while explosion != -1 and explosion is not None:
            self._remove_piece_at(explosion)
            explosion = chess.bit_scan(explosion_radius, explosion + 1)

        # Destroy castling rights.
        self.castling_rights &= ~explosion_radius

    def is_check(self):
        return not self._kings_connected() and super(AtomicBoard, self).is_check()

    def was_into_check(self):
        return not self._kings_connected() and super(AtomicBoard, self).was_into_check()

    def is_into_check(self, move):
        self.push(move)
        was_into_check = self.was_into_check()
        self.pop()
        return was_into_check

    def is_legal(self, move):
        if not self.is_pseudo_legal(move):
            return False

        self.push(move)
        legal = self.kings and not self.is_variant_win() and (self.is_variant_loss() or not self.was_into_check())
        self.pop()

        return legal

    def is_stalemate(self):
        return not self.is_variant_loss() and super(AtomicBoard, self).is_stalemate()

    def generate_legal_moves(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        for move in self.generate_pseudo_legal_moves(from_mask, to_mask):
            if self.is_legal(move):
                yield move

    generate_evasions = generate_non_evasions = generate_legal_moves

    def status(self):
        status = super(SuicideBoard, self).status()
        status &= ~chess.STATUS_OPPOSITE_CHECK
        if self.turn == chess.WHITE:
            status &= ~chess.STATUS_NO_WHITE_KING
        else:
            status &= ~chess.STATUS_NO_BLACK_KING
        return status


BB_HILL = chess.BB_E4 | chess.BB_D4 | chess.BB_E5 | chess.BB_D5

class KingOfTheHillBoard(chess.Board):

    aliases = ["King of the Hill", "KOTH"]
    uci_variant = "kingofthehill"

    tbw_suffix = tbz_suffix = None
    tbw_magic = tbz_magic = None

    def is_variant_win(self):
        return self.kings & self.occupied_co[self.turn] & BB_HILL

    def is_variant_loss(self):
        return self.kings & self.occupied_co[not self.turn] & BB_HILL

    def is_insufficient_material(self):
        return False


class RacingKingsBoard(chess.Board):

    aliases = ["Racing Kings", "Racing", "Race", "racingkings"]
    uci_variant = "racingkings"
    starting_fen = "8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1"

    tbw_suffix = tbz_suffix = None
    tbw_magic = tbz_magic = None

    def __init__(self, fen=starting_fen, chess960=False):
        super(RacingKingsBoard, self).__init__(fen, chess960)

    def reset(self):
        self.set_fen(type(self).starting_fen)

    def _gives_check(self, move):
        self.push(move)
        gives_check = self.is_check()
        self.pop()
        return gives_check

    def is_legal(self, move):
        return super(RacingKingsBoard, self).is_legal(move) and not self._gives_check(move)

    def generate_evasions(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        for move in super(RacingKingsBoard, self).generate_evasions(from_mask, to_mask):
            if not self._gives_check(move):
                yield move

    def generate_non_evasions(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        for move in super(RacingKingsBoard, self).generate_non_evasions(from_mask, to_mask):
            if not self._gives_check(move):
                yield move

    def is_variant_draw(self):
        in_goal = self.kings & chess.BB_RANK_8
        return in_goal & self.occupied_co[chess.WHITE] and in_goal & self.occupied_co[chess.BLACK]

    def is_variant_loss(self):
        if self.is_variant_draw():
            return False

        if self.turn == chess.WHITE:
            return self.kings & self.occupied_co[chess.BLACK] & chess.BB_RANK_8
        else:
            if not self.kings & self.occupied_co[chess.WHITE] & chess.BB_RANK_8:
                return False

            # Black can not reach the backrank on the next move.
            return not any(move for move in self.generate_legal_moves(self.kings, chess.BB_RANK_8))

    def is_variant_win(self):
        if self.is_variant_draw():
            return False

        return self.kings & self.occupied_co[self.turn] & chess.BB_RANK_8

    def is_insufficient_material(self):
        return False

    def status(self):
        status = super(RacingKingsBoard, self).status()
        if self.is_check():
            status |= chess.STATUS_ILLEGAL_CHECK
        return status


class HordeBoard(chess.Board):

    aliases = ["Horde", "Horde chess"]
    uci_variant = "horde"
    starting_fen = "rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1"

    tbw_suffix = tbz_suffix = None
    tbw_magic = tbz_magic = None

    def __init__(self, fen=starting_fen, chess960=False):
        super(HordeBoard, self).__init__(fen, chess960)

    def reset(self):
        self.set_fen(type(self).starting_fen)

    def is_variant_draw(self):
        return not self.occupied

    def is_variant_loss(self):
        return self.occupied and not self.occupied_co[self.turn]

    def is_variant_win(self):
        return self.occupied and not self.occupied_co[not self.turn]

    def is_insufficient_material(self):
        return False

    def status(self):
        status = super(HordeBoard, self).status()
        status &= ~chess.STATUS_NO_WHITE_KING

        if chess.pop_count(self.occupied_co[chess.WHITE]) <= 36:
            status &= ~chess.STATUS_TOO_MANY_WHITE_PIECES
            status &= ~chess.STATUS_TOO_MANY_WHITE_PAWNS

        if not self.pawns & chess.BB_RANK_8 and not self.occupied_co[chess.BLACK] & chess.BB_RANK_1:
            status &= ~chess.STATUS_PAWNS_ON_BACKRANK

        if self.occupied_co[chess.WHITE] & self.kings:
            status |= chess.STATUS_TOO_MANY_KINGS

        return status


THREE_CHECK_POLYGLOT_RANDOM_ARRAY = [
    0x1d6dc0ee61ce803e, 0xc6284b653d38e96a,
    0x803f5fb0d2f97fae, 0xb183ccc9e73df9ed,
    0xfdeef11602d6b443, 0x1b0ce4198b3801a6,
]

class ThreeCheckBoard(chess.Board):

    aliases = ["Three-check", "Three check", "Threecheck", "Three check chess"]
    uci_variant = "threecheck"
    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 3+3 0 1"

    tbw_suffix = tbz_suffix = None
    tbw_magic = tbz_magic = None

    def __init__(self, fen=starting_fen, chess960=False):
        self.remaining_checks = [3, 3]
        super(ThreeCheckBoard, self).__init__(fen, chess960)

    def reset_board(self):
        super(ThreeCheckBoard, self).reset_board()
        self.remaining_checks[chess.WHITE] = 3
        self.remaining_checks[chess.BLACK] = 3

    def clear_board(self):
        super(ThreeCheckBoard, self).clear_board()
        self.remaining_checks[chess.WHITE] = 3
        self.remaining_checks[chess.BLACK] = 3

    def push(self, move):
        super(ThreeCheckBoard, self).push(move)
        if self.is_check():
            self.remaining_checks[not self.turn] -= 1

    def pop(self):
        was_in_check = self.is_check()
        move = super(ThreeCheckBoard, self).pop()
        if was_in_check:
            self.remaining_checks[self.turn] += 1
        return move

    def is_insufficient_material(self):
        return self.occupied == self.kings

    def zobrist_hash(self, array=None, three_check_array=None):
        zobrist_hash = super(ThreeCheckBoard, self).zobrist_hash(array)

        if three_check_array is None:
            three_check_array = THREE_CHECK_POLYGLOT_RANDOM_ARRAY

        white_count = min(3, 3 - self.remaining_checks[chess.WHITE])
        black_count = min(3, 3 - self.remaining_checks[chess.BLACK])

        if white_count > 0:
            zobrist_hash ^= three_check_array[black_count - 1]
        if black_count > 0:
            zobrist_hash ^= three_check_array[white_count + 2]

        return zobrist_hash

    def set_epd(self, epd):
        # Split into 5 or 6 parts.
        parts = epd.strip().rstrip(";").split(None, 5)
        if len(parts) < 5:
            raise ValueError("three-check epd should consist of at least 5 parts: {0}".format(repr(epd)))

        # Parse ops.
        if len(parts) > 5:
            operations = self._parse_epd_ops(parts.pop(), lambda: type(self)(" ".join(parts + " 0 1")))
        else:
            operations = {}

        # Create a full FEN an parse it.
        parts.append(str(operations["hmvc"]) if "hmvc" in operations else "0")
        parts.append(str(operations["fmvn"]) if "fmvn" in operations else "1")
        self.set_fen(" ".join(parts))

        return operations

    def set_fen(self, fen):
        parts = fen.split()
        if len(parts) != 7:
            raise ValueError("three-check fen should consist of 7 parts: {0}".format(repr(fen)))

        # Extract check part.
        if "+" == parts[6][0]:
            check_part = parts.pop()[1:]
            try:
                w, b = check_part.split("+", 1)
                wc, bc = 3 - int(w), 3 - int(b)
            except ValueError:
                raise ValueError("invalid check part in lichess three-check fen: {0}".format(repr(check_part)))
        else:
            check_part = parts.pop(4)
            try:
                w, b = check_part.split("+", 1)
                wc, bc = int(w), int(b)
            except ValueError:
                raise ValueError("invalid check part in three-check fen: {0}".format(repr(check_part)))

        # Set fen.
        super(ThreeCheckBoard, self).set_fen(" ".join(parts))
        self.remaining_checks[chess.WHITE] = wc
        self.remaining_checks[chess.BLACK] = bc

    def epd(self, shredder_fen=False, promoted=False, **operations):
        epd = []
        epd.append(super(ThreeCheckBoard, self).epd(shredder_fen=shredder_fen, promoted=promoted))
        epd.append("%d+%d" % (max(self.remaining_checks[chess.WHITE], 0), max(self.remaining_checks[chess.BLACK], 0)))
        if operations:
            epd.append(self._epd_operations(operations))
        return " ".join(epd)

    def is_variant_draw(self):
        return self.remaining_checks[chess.WHITE] <= 0 and self.remaining_checks[chess.BLACK] <= 0

    def is_variant_loss(self):
        return self.remaining_checks[not self.turn] <= 0 and self.remaining_checks[self.turn] > 0

    def is_variant_win(self):
        return self.remaining_checks[self.turn] <= 0 and self.remaining_checks[not self.turn] > 0

    def copy(self, stack=True):
        board = super(ThreeCheckBoard, self).copy(stack=stack)
        board.remaining_checks[chess.WHITE] = self.remaining_checks[chess.WHITE]
        board.remaining_checks[chess.BLACK] = self.remaining_checks[chess.BLACK]
        return board


class CrazyhousePocket(object):

    def __init__(self, symbols=""):
        self.pieces = {}
        for symbol in symbols:
            self.add(chess.PIECE_SYMBOLS.index(symbol))

    def add(self, pt):
        self.pieces[pt] = self.pieces.get(pt, 0) + 1

    def remove(self, pt):
        self.pieces[pt] -= 1

    def count(self, piece_type):
        return self.pieces.get(piece_type, 0)

    def reset(self):
        self.pieces.clear()

    def __str__(self):
        return "".join(chess.PIECE_SYMBOLS[pt] * self.count(pt) for pt in reversed(chess.PIECE_TYPES))

    def __len__(self):
        return sum(self.pieces.values())

    def __repr__(self):
        return "CrazyhousePocket('{0}')".format(str(self))

    def copy(self):
        pocket = type(self)()
        pocket.pieces = copy.copy(self.pieces)
        return pocket

class CrazyhouseBoard(chess.Board):

    aliases = ["Crazyhouse", "Crazy House", "House", "ZH"]
    uci_variant = "crazyhouse"
    starting_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR[] w KQkq - 0 1"

    tbw_suffix = tbz_suffix = None
    tbw_magic = tbz_magic = None

    def __init__(self, fen=starting_fen, chess960=False):
        self.pockets = [CrazyhousePocket(), CrazyhousePocket()]
        super(CrazyhouseBoard, self).__init__(fen, chess960)

    def reset_board(self):
        super(CrazyhouseBoard, self).reset_board()
        self.pockets[chess.WHITE].reset()
        self.pockets[chess.BLACK].reset()

    def clear_board(self):
        super(CrazyhouseBoard, self).clear_board()
        self.pockets[chess.WHITE].reset()
        self.pockets[chess.BLACK].reset()

    def push(self, move):
        if move.drop:
            self.pockets[self.turn].remove(move.drop)

        super(CrazyhouseBoard, self).push(move)

    def pop(self):
        move = super(CrazyhouseBoard, self).pop()
        if move.drop:
            self.pockets[self.turn].add(move.drop)
        elif self.is_capture(move):
            if chess.BB_SQUARES[move.to_square] & self.promoted:
                self.pockets[self.turn].remove(chess.PAWN)
            else:
                self.pockets[self.turn].remove(self.piece_type_at(move.to_square))

    def _push_capture(self, move, capture_square, piece_type, was_promoted):
        if was_promoted:
            self.pockets[self.turn].add(chess.PAWN)
        else:
            self.pockets[self.turn].add(piece_type)

    def can_claim_fifty_moves(self):
        return False

    def is_seventyfive_moves(self):
        return False

    def is_zeroing(self, move):
        return False

    def legal_drop_squares_mask(self):
        king_bb = self.kings & self.occupied_co[self.turn]
        king_square = chess.bit_scan(king_bb)
        if king_square is None or king_square == -1:
            return ~self.occupied

        king_attackers = self.attackers_mask(not self.turn, king_square)
        num_attackers = chess.pop_count(king_attackers)

        if num_attackers == 0:
            return ~self.occupied
        elif num_attackers == 1:
            king_rank_mask = chess.RANK_MASK[king_bb]
            king_file_mask = chess.FILE_MASK[king_bb]
            king_diag_ne = chess.DIAG_MASK_NE[king_bb]
            king_diag_nw = chess.DIAG_MASK_NW[king_bb]

            if king_rank_mask == chess.RANK_MASK[king_attackers]:
                rank_pieces = king_rank_mask & self.occupied
                return chess.RANK_ATTACKS[king_bb][rank_pieces] & ~self.occupied & chess.RANK_ATTACKS[king_attackers][rank_pieces]
            elif king_file_mask == chess.FILE_MASK[king_attackers]:
                file_pieces = king_file_mask & self.occupied
                return chess.FILE_ATTACKS[king_bb][file_pieces] & ~self.occupied & chess.FILE_ATTACKS[king_attackers][file_pieces]
            elif king_diag_ne == chess.DIAG_MASK_NE[king_attackers]:
                ne_pieces = king_diag_ne & self.occupied
                return chess.DIAG_ATTACKS_NE[king_bb][ne_pieces] & ~self.occupied & chess.DIAG_ATTACKS_NE[king_attackers][ne_pieces]
            elif king_diag_nw == chess.DIAG_MASK_NW[king_attackers]:
                nw_pieces = king_diag_nw & self.occupied
                return chess.DIAG_ATTACKS_NW[king_bb][nw_pieces] & ~self.occupied & chess.DIAG_ATTACKS_NW[king_attackers][nw_pieces]

        return chess.BB_VOID

    def legal_drop_squares(self):
        return chess.SquareSet(self.legal_drop_squares_mask())

    def is_pseudo_legal(self, move):
        if move.drop and move.from_square == move.to_square:
            if move.drop == chess.KING:
                return False

            if chess.BB_SQUARES[move.to_square] & self.occupied:
                return False

            if move.drop == chess.PAWN and chess.BB_SQUARES[move.to_square] & chess.BB_BACKRANKS:
                return False

            return self.pockets[self.turn].count(move.drop) >= 0
        else:
            return super(CrazyhouseBoard, self).is_pseudo_legal(move)

    def is_legal(self, move):
        if move.drop:
            return self.is_pseudo_legal(move) and self.legal_drop_squares_mask() & chess.BB_SQUARES[move.to_square]
        else:
            return super(CrazyhouseBoard, self).is_legal(move)

    def generate_pseudo_legal_drops(self, to_mask=chess.BB_ALL):
        to_mask = to_mask & ~self.occupied
        to_square = chess.bit_scan(to_mask)
        while to_square != -1 and to_square is not None:
            for pt, count in self.pockets[self.turn].pieces.items():
                if count and (pt != chess.PAWN or not chess.BB_BACKRANKS & chess.BB_SQUARES[to_square]):
                    yield chess.Move(to_square, to_square, drop=pt)
            to_square = chess.bit_scan(to_mask, to_square + 1)

    def generate_legal_drops(self, to_mask=chess.BB_ALL):
        return self.generate_pseudo_legal_drops(to_mask=self.legal_drop_squares_mask() & to_mask)

    def generate_non_evasions(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        return itertools.chain(
            super(CrazyhouseBoard, self).generate_non_evasions(from_mask, to_mask),
            self.generate_legal_drops(from_mask & to_mask))

    def generate_evasions(self, from_mask=chess.BB_ALL, to_mask=chess.BB_ALL):
        return itertools.chain(
            super(CrazyhouseBoard, self).generate_evasions(from_mask, to_mask),
            self.generate_legal_drops(from_mask & to_mask))

    # TODO: zobrist_hash

    def parse_san(self, san):
        if "@" in san:
            uci = san.rstrip("+# ")
            if uci[0] == "@":
                uci = "P" + uci
            move = chess.Move.from_uci(uci)
            if not self.is_legal(move):
                raise ValueError("illegal drop san: {0} in {1}".format(repr(san), self.fen()))
            return move
        else:
            return super(CrazyhouseBoard, self).parse_san(san)

    def is_insufficient_material(self):
        return False

    def set_fen(self, fen):
        position_part, info_part = fen.split(None, 1)

        # Transform to lichess-style ZH FEN.
        if position_part.endswith("]"):
            if position_part.count("/") != 7:
                raise ValueError("expected 8 rows in position part of zh fen: {0}", format(repr(fen)))
            position_part = position_part[:-1].replace("[", "/", 1)

        # Split off pocket part.
        if position_part.count("/") == 8:
            position_part, pocket_part = position_part.rsplit("/", 1)
        else:
            pocket_part = ""

        # Parse pocket.
        white_pocket = CrazyhousePocket(c.lower() for c in pocket_part if c.isupper())
        black_pocket = CrazyhousePocket(c for c in pocket_part if not c.isupper())

        # Set FEN and pockets.
        super(CrazyhouseBoard, self).set_fen(position_part + " " + info_part)
        self.pockets[chess.WHITE] = white_pocket
        self.pockets[chess.BLACK] = black_pocket

    def fen(self, promoted=True):
        return super(CrazyhouseBoard, self).fen(promoted=promoted)

    def shredder_fen(self, promoted=True):
        return super(CrazyhouseBoard, self).shredder_fen(promoted=promoted)

    def epd(self, shredder_fen=False, promoted=True, **operations):
        epd = super(CrazyhouseBoard, self).epd(shredder_fen=shredder_fen, promoted=promoted)
        board_part, info_part = epd.split(" ", 1)
        return "%s[%s%s] %s" % (board_part, str(self.pockets[chess.WHITE]).upper(), str(self.pockets[chess.BLACK]), info_part)

    def copy(self, stack=True):
        board = super(CrazyhouseBoard, self).copy(stack=stack)
        board.pockets[chess.WHITE] = self.pockets[chess.WHITE].copy()
        board.pockets[chess.BLACK] = self.pockets[chess.BLACK].copy()
        return board

    def status(self):
        status = super(CrazyhouseBoard, self).status()

        if chess.pop_count(self.pawns) + self.pockets[chess.WHITE].count(chess.PAWN) + self.pockets[chess.BLACK].count(chess.PAWN) <= 16:
            status &= ~chess.STATUS_TOO_MANY_BLACK_PAWNS
            status &= ~chess.STATUS_TOO_MANY_WHITE_PAWNS

        if chess.pop_count(self.occupied) + len(self.pockets[chess.WHITE]) + len(self.pockets[chess.BLACK]) <= 32:
            status &= ~chess.STATUS_TOO_MANY_BLACK_PIECES
            status &= ~chess.STATUS_TOO_MANY_WHITE_PIECES

        return status


VARIANTS = [
    chess.Board,
    SuicideBoard, GiveawayBoard,
    AtomicBoard,
    KingOfTheHillBoard,
    RacingKingsBoard,
    HordeBoard,
    ThreeCheckBoard,
    CrazyhouseBoard,
]


def find_variant(name):
    """Looks for a variant board class by variant name."""
    for variant in VARIANTS:
        if any(alias.lower() == name.lower() for alias in variant.aliases):
            return variant
    raise ValueError("unsupported variant: {0}".format(name))
