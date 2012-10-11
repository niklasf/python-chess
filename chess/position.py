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
import collections
import re
import types

# TODO: Find a sane order for the members.

san_regex = re.compile('^([NBKRQ])?([a-h])?([1-8])?x?([a-h][1-8])(=[NBRQ])?$')

MoveInfo = collections.namedtuple("MoveInfo", [
    "move",
    "piece",
    "captured",
    "san",
    "is_enpassant",
    "is_king_side_castle",
    "is_queen_side_castle",
    "is_castle",
    "is_check",
    "is_checkmate"])


class Position(object):
    """Represents a chess position.

    :param fen:
        Optional. The FEN of the position. Defaults to the standard
        chess start position.

    Squares can be accessed via their name, a square object and their
    x88 index:

    >>> import chess
    >>> pos = chess.Position()
    >>> pos["e4"] = Piece("Q")
    >>> pos[chess.Square("e4")]
    Piece('Q')
    >>> del pos["a8"]
    >>> pos[0] # 0 is the x88 index of a8.
    None

    Equal position compare as equal.

    `START_FEN`:
        The FEN of the standard chess start position.
    """

    START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def __init__(self, fen=START_FEN):
        self.__castling = "KQkq"
        self.fen = fen

    def copy(self):
        """Gets a copy of the position. The copy will not change when the
        original instance is changed.

        :return:
            An exact copy of the positon.
        """
        return Position(self.fen)

    def __get_square_index(self, square_or_int):
        if type(square_or_int) is types.IntType:
            # Validate the index by passing it through the constructor.
            return chess.Square.from_x88(square_or_int).x88
        elif type(square_or_int) is types.StringType:
            return chess.Square(square_or_int).x88
        elif type(square_or_int) is chess.Square:
            return square_or_int.x88
        else:
            raise TypeError(
                "Expected integer or Square, got: %s." % repr(square_or_int))

    def __getitem__(self, key):
        return self.__board[self.__get_square_index(key)]

    def __setitem__(self, key, value):
        if value is None or type(value) is chess.Piece:
            self.__board[self.__get_square_index(key)] = value
        else:
            raise TypeError("Expected Piece or None, got: %s." % repr(value))

    def __delitem__(self, key):
        self.__board[self.__get_square_index(key)] = None

    def clear_board(self):
        """Removes all pieces from the board."""
        self.__board = [None] * 128

    def reset(self):
        """Resets to the standard chess start position."""
        self.set_fen(START_FEN)

    def __get_disambiguator(self, move):
        same_rank = False
        same_file = False
        piece = self[move.source]

        for m in self.get_legal_moves():
            ambig_piece = self[m.source]
            if (piece == ambig_piece and move.source != m.source and
                move.target == m.target):
                if move.source.rank == m.source.rank:
                    same_rank = True

                if move.source.file == m.source.file:
                    same_file = True

                if same_rank and same_file:
                    break

        if same_rank and same_file:
            return move.source.name
        elif same_file:
            return str(move.source.rank)
        elif same_rank:
            return move.source.file
        else:
            return ""

    def get_move_from_san(self, san):
        """Gets a move from standard algebraic notation.

        :param san:
            A move string in standard algebraic notation.

        :return:
            A Move object.

        :raise MoveError:
            If not exactly one legal move matches.
        """
        # Castling moves.
        if san == "o-o" or san == "o-o-o":
            # TODO: Support Chess960, check the castling moves are valid.
            rank = 1 if self.turn == "w" else 8
            if san == "o-o":
                return chess.Move(
                    source=chess.Square.from_rank_and_file(rank, 'e'),
                    target=chess.Square.from_rank_and_file(rank, 'g'))
            else:
                return chess.Move(
                    source=chess.Square.from_rank_and_file(rank, 'e'),
                    target=chess.Square.from_rank_and_file(rank, 'c'))
        # Regular moves.
        else:
            matches = san_regex.match(san)
            if not matches:
                raise ValueError("Invalid SAN: %s." % repr(san))

            piece = chess.Piece.from_color_and_type(
                color=self.turn,
                type=matches.group(1).lower() if matches.group(1) else 'p')
            target = chess.Square(matches.group(4))

            source = None
            for m in self.get_legal_moves():
                if self[m.source] != piece or m.target != target:
                    continue

                if matches.group(2) and matches.group(2) != m.source.file:
                    continue
                if matches.group(3) and matches.group(3) != str(m.source.rank):
                    continue

                # Move matches. Assert it is not ambiguous.
                if source:
                    raise chess.MoveError(
                        "Move is ambiguous: %s matches %s and %s."
                            % san, source, m)
                source = m.source

            if not source:
                raise chess.MoveError("No legal move matches %s." % san)

            return chess.Move(source, target, matches.group(5) or None)

    def get_move_info(self, move):
        """Gets information about a move.

        :param move:
            The move to get information about.

        :return:
            A named tuple with these properties:

            `move`:
                The move object.
            `piece`:
                The piece that has been moved.
            `san`:
                The standard algebraic notation of the move.
            `captured`:
                The piece that has been captured or `None`.
            `is_enpassant`:
                A boolean indicating if the move is an en-passant
                capture.
            `is_king_side_castle`:
                Whether it is a king-side castling move.
            `is_queen_side_castle`:
                Whether it is a queen-side castling move.
            `is_castle`:
                Whether it is a castling move.
            `is_check`:
                Whether the move gives check.
            `is_checkmate`:
                Whether the move gives checkmate.

        :raise MoveError:
            If the move is not legal in the position.
        """
        resulting_position = self.copy().make_move(move)

        capture = self[move.target]
        piece = self[move.source]

        # Pawn moves.
        enpassant = False
        if piece.type == "p":
            # En-passant.
            if move.target.file != move.source.file and not capture:
                enpassant = True
                capture = chess.Piece.from_color_and_type(
                    color=resulting_position.turn, type='p')

        # Castling.
        # TODO: Support Chess960.
        # TODO: Validate the castling move.
        if piece.type == "k":
            is_king_side_castle = move.target.x - move.source.x == 2
            is_queen_side_castle = move.target.x - move.source.x == -2
        else:
            is_king_side_castle = is_queen_side_castle = False

        # Checks.
        is_check = resulting_position.is_check()
        is_checkmate = resulting_position.is_checkmate()

        # Generate the SAN.
        san = ""
        if is_king_side_castle:
            san += "o-o"
        elif is_queen_side_castle:
            san += "o-o-o"
        else:
            if piece.type != 'p':
                san += piece.type.upper()

            san += self.__get_disambiguator(move)

            if capture:
                if piece.type == 'p':
                    san += move.source.file
                san += "x"
            san += move.target.name

            if move.promotion:
                san += "="
                san += move.promotion.upper()

        if is_checkmate:
            san += "#"
        elif is_check:
            san += "+"

        if enpassant:
            san += " (e.p.)"

        # Return the named tuple.
        return MoveInfo(
            move=move,
            piece=piece,
            captured=capture,
            san=san,
            is_enpassant=enpassant,
            is_king_side_castle=is_king_side_castle,
            is_queen_side_castle=is_queen_side_castle,
            is_castle=is_king_side_castle or is_queen_side_castle,
            is_check=is_check,
            is_checkmate=is_checkmate)

    def make_move(self, move, validate=True):
        """Makes a move.

        :param move:
            The move to make.
        :param validate:
            Defaults to `True`. Whether the move should be validated.

        :return:
            Making a move changes the position object. The same
            (changed) object is returned for chainability.

        :raise MoveError:
            If the validate parameter is `True` and the move is not
            legal in the position.
        """
        if validate and not move in self.get_legal_moves():
            raise chess.MoveError(
                "%s is not a legal move in the position %s." % (move, self.fen))

        piece = self[move.source]
        capture = self[move.target]

        # Move the piece.
        self[move.target] = self[move.source]
        del self[move.source]

        # It is the next players turn.
        self.toggle_turn()

        # Pawn moves.
        self.ep_file = None
        if piece.type == "p":
            # En-passant.
            if move.target.file != move.source.file and not capture:
                if self.turn == "b":
                    self[move.target.x88 - 16] = None
                else:
                    self[move.target.x88 + 16] = None
                capture = True
            # If big pawn move, set the en-passant file.
            if abs(move.target.rank - move.source.rank) == 2:
                if self.get_theoretical_ep_right(move.target.file):
                    self.ep_file = move.target.file

        # Promotion.
        if move.promotion:
            self[move.target] = chess.Piece.from_color_and_type(
                color=piece.color, type=move.promotion)

        # Potential castling.
        if piece.type == "k":
            steps = move.target.x - move.source.x
            if abs(steps) == 2:
                # Queen-side castling.
                if steps == -2:
                    rook_target = move.target.x88 + 1
                    rook_source = move.target.x88 - 2
                # King-side castling.
                else:
                    rook_target = move.target.x88 - 1
                    rook_source = move.target.x88 + 1
                self[rook_target] = self[rook_source]
                del self[rook_source]

        # Increment the half move counter.
        if piece.type == "p" or capture:
            self.half_moves = 0
        else:
            self.half_moves += 1

        # Increment the move number.
        if self.turn == "w":
            self.ply += 1

        # Update castling rights.
        for type in ["K", "Q", "k", "q"]:
            if not self.get_theoretical_castling_right(type):
                self.set_castling_right(type, False)

        return self

    @property
    def turn(self):
        """Whos turn it is as `"w"` or `"b"`."""
        return self.__turn

    @turn.setter
    def turn(self, value):
        if not value in ["w", "b"]:
            raise ValueError(
                "Expected 'w' or 'b' for turn, got: %s." % repr(value))
        self.__turn = value

    def toggle_turn(self):
        """Toggles whos turn it is."""
        self.turn = chess.opposite_color(self.turn)

    def get_castling_right(self, type):
        """Checks the castling rights.

        :param type:
            The castling move to check. "K" for king-side castling of
            the white player, "Q" for queen-side castling of the white
            player. "k" and "q" for the corresponding castling moves of
            the black player.

        :return:
            A boolean indicating whether the player has that castling
            right.
        """
        if not type in ["K", "Q", "k", "q"]:
            raise KeyError(
                "Expected 'K', 'Q', 'k' or 'q' as a castling type, got: %s."
                    % repr(type))
        return type in self.__castling

    def get_theoretical_castling_right(self, type):
        """Checks if a player could have a castling right in theory from
        looking just at the piece positions.

        :param type:
            The castling move to check. See
            `Position.get_castling_right(type)` for values.

        :return:
            A boolean indicating whether the player could theoretically
            have that castling right.
        """
        if not type in ["K", "Q", "k", "q"]:
            raise KeyError(
                "Expected 'K', 'Q', 'k' or 'q' as a castling type, got: %s."
                    % repr(type))
        # TODO: Support Chess960.
        if type == "K" or type == "Q":
            if self["e1"] != chess.Piece("K"):
                return False
            if type == "K":
                return self["h1"] == chess.Piece("R")
            elif type == "Q":
                return self["a1"] == chess.Piece("R")
        elif type == "k" or type == "q":
            if self["e8"] != chess.Piece("k"):
                return False
            if type == "k":
                return self["h8"] == chess.Piece("r")
            elif type == "q":
                return self["a8"] == chess.Piece("r")

    def get_theoretical_ep_right(self, file):
        """Checks if a player could have an ep-move in theory from
        looking just at the piece positions.

        :param file:
            The file to check as a letter between `"a"` and `"h"`.

        :return:
            A boolean indicating whether the player could theoretically
            have that en-passant move.
        """
        if not file in ["a", "b", "c", "d", "e", "f", "g", "h"]:
            raise KeyError(
                "Expected a letter between 'a' and 'h' for the file, got: %s."
                    % repr(file))

        # Check there is a pawn.
        pawn_square = chess.Square.from_rank_and_file(
            rank=4 if self.turn == "b" else 5, file=file)
        opposite_color_pawn = chess.Piece.from_color_and_type(
            color=chess.opposite_color(self.turn), type="p")
        if self[pawn_square] != opposite_color_pawn:
            return False

        # Check the square below is empty.
        square_below = chess.Square.from_rank_and_file(
            rank=3 if self.turn == "b" else 6, file=file)
        if self[square_below]:
            return False

        # Check there is a pawn of the other color on a neighbor file.
        f = ord(file) - ord("a")
        p = chess.Piece("p")
        P = chess.Piece("P")
        if self.turn == "b":
            if f > 0 and self[chess.Square.from_x_and_y(f - 1, 3)] == p:
                return True
            elif f < 7 and self[chess.Square.from_x_and_y(f + 1, 3)] == p:
                return True
        else:
            if f > 0 and self[chess.Square.from_x_and_y(f - 1, 4)] == P:
                return True
            elif f < 7 and self[chess.Square.from_x_and_y(f + 1, 4)] == P:
                return True
        return False

    def set_castling_right(self, type, status):
        """Sets a castling right.

        :param type:
            `"K"`, `"Q"`, `"k"`, or `"q"` as used by
            `Position.get_castling_right(type)`.
        :param status:
            A boolean indicating whether that castling right should be
            granted or denied.
        """
        if not type in ["K", "Q", "k", "q"]:
            raise KeyError(
                "Expected 'K', 'Q', 'k' or 'q' as a castling type, got: %s."
                    % repr(type))

        castling = ""
        for t in ["K", "Q", "k", "q"]:
            if type == t:
                if status:
                    castling += t
            elif self.get_castling_right(t):
                castling += t
        self.__castling = castling

    @property
    def ep_file(self):
        """The en-passant file as a lowercase letter between `"a"` and
        `"h"` or `None`."""
        return self.__ep_file

    @ep_file.setter
    def ep_file(self, value):
        if not value in ["a", "b", "c", "d", "e", "f", "g", "h", None]:
            raise ValueError(
                "Expected None or a letter between 'a' and 'h' for the "
                "en-passant file, got: %s." % repr(value))

        self.__ep_file = value

    @property
    def half_moves(self):
        """The number of half-moves since the last capture or pawn move."""
        return self.__half_moves

    @half_moves.setter
    def half_moves(self, value):
        if type(value) is not types.IntType:
            raise TypeError(
                "Expected integer for half move count, got: %s." % repr(value))
        if value < 0:
            raise ValueError("Half move count must be >= 0.")

        self.__half_moves = value

    @property
    def ply(self):
        """The number of this move. The game starts at 1 and the counter
        is incremented every time white moves.
        """
        return self.__ply

    @ply.setter
    def ply(self, value):
        if type(value) is not types.IntType:
            raise TypeError(
                "Expected integer for ply count, got: %s." % repr(value))
        if value < 1:
            raise ValueError("Ply count must be >= 1.")
        self.__ply = value

    def get_piece_counts(self, color = "wb"):
        """Counts the pieces on the board.

        :param color:
            Defaults to `"wb"`. A color to filter the pieces by. Valid
            values are "w", "b", "wb" and "bw".

        :return:
            A dictionary of piece counts, keyed by lowercase piece type
            letters.
        """
        if not color in ["w", "b", "wb", "bw"]:
            raise KeyError(
                "Expected color filter to be one of 'w', 'b', 'wb', 'bw', "
                "got: %s." % repr(color))

        counts = {
            "p": 0,
            "b": 0,
            "n": 0,
            "r": 0,
            "k": 0,
            "q": 0,
        }
        for piece in self.__board:
            if piece and piece.color in color:
                counts[piece.type] += 1
        return counts

    def get_king(self, color):
        """Gets the square of the king.

        :param color:
            `"w"` for the white players king. `"b"` for the black
            players king.

        :return:
            The first square with a matching king or `None` if that
            player has no king.
        """
        if not color in ["w", "b"]:
            raise KeyError("Invalid color: %s." % repr(color))

        for square in chess.Square.get_all():
            piece = self[square]
            if piece and piece.color == color and piece.type == "k":
                return square

    @property
    def fen(self):
        """The FEN string representing the position."""
        # Board setup.
        empty = 0
        fen = ""
        for y in range(7, -1, -1):
            for x in range(0, 8):
                square = chess.Square.from_x_and_y(x, y)

                # Add pieces.
                if not self[square]:
                    empty += 1
                else:
                    if empty > 0:
                        fen += str(empty)
                        empty = 0
                    fen += self[square].symbol

            # Boarder of the board.
            if empty > 0:
                fen += str(empty)
            if not (x == 7 and y == 0):
                fen += "/"
            empty = 0

        if self.ep_file and self.get_theoretical_ep_right(self.ep_file):
            ep_square = self.ep_file + ("3" if self.turn == "b" else "6")
        else:
            ep_square = "-"

        # Join the parts together.
        return " ".join([
            fen,
            self.turn,
            self.__castling if self.__castling else "-",
            ep_square,
            str(self.half_moves),
            str(self.__ply)])

    @fen.setter
    def fen(self, fen):
        # Split into 6 parts.
        tokens = fen.split()
        if len(tokens) != 6:
            raise chess.FenError("A FEN does not consist of 6 parts.")

        # Check that the position part is valid.
        rows = tokens[0].split("/")
        assert len(rows) == 8
        for row in rows:
            field_sum = 0
            previous_was_number = False
            for char in row:
                if char in "12345678":
                    if previous_was_number:
                        raise chess.FenError(
                            "Position part of the FEN is invalid: "
                            "Multiple numbers immediately after each other.")
                    field_sum += int(char)
                    previous_was_number = True
                elif char in "pnbrkqPNBRKQ":
                    field_sum += 1
                    previous_was_number = False
                else:
                    raise chess.FenError(
                        "Position part of the FEN is invalid: "
                        "Invalid character in the position part of the FEN.")

            if field_sum != 8:
                chess.FenError(
                    "Position part of the FEN is invalid: "
                    "Row with invalid length.")


        # Check that the other parts are valid.
        if not tokens[1] in ["w", "b"]:
            raise chess.FenError(
                "Turn part of the FEN is invalid: Expected b or w.")
        if not re.compile("^(KQ?k?q?|Qk?q?|kq?|q|-)$").match(tokens[2]):
            raise chess.FenError("Castling part of the FEN is invalid.")
        if not re.compile("^(-|[a-h][36])$").match(tokens[3]):
            raise chess.FenError("En-passant part of the FEN is invalid.")
        if not re.compile("^(0|[1-9][0-9]*)$").match(tokens[4]):
            raise chess.FenError("Half move part of the FEN is invalid.")
        if not re.compile("^[1-9][0-9]*$").match(tokens[5]):
            raise chess.FenError("Ply part of the FEN is invalid.")

        # Set pieces on the board.
        self.__board = [None] * 128
        i = 0
        for symbol in tokens[0]:
            if symbol == "/":
                i += 8
            elif symbol in "12345678":
                i += int(symbol)
            else:
                self.__board[i] = chess.Piece(symbol)
                i += 1

        # Set the turn.
        self.__turn = tokens[1]

        # Set the castling rights.
        for type in ["K", "Q", "k", "q"]:
            self.set_castling_right(type, type in tokens[2])

        # Set the en-passant file.
        if tokens[3] == "-":
            self.__ep_file = None
        else:
            self.__ep_file = tokens[3][0]

        # Set the move counters.
        self.__half_moves = int(tokens[4])
        self.__ply = int(tokens[5])

    def __validate():
        # TODO: Rewrite and make public.
        for color in ["white", "black"]:
            piece_counts = self.get_piece_counts(color[0])
            if piece_counts["k"] == 0:
                raise "Missing %s king." % color
            elif piece_counts["k"] > 1:
                raise "Too many %s kings." % color

            if piece_counts["p"] > 8:
                raise "Too many %s pawns." % color

            if sum(piece_counts.values()) > 16:
                raise "Too many %s pieces." % color

        if self.is_king_attacked("w") and self.is_king_attacked("b"):
            raise "Both sides in check."

        if self.is_king_attacked(chess.opposite_color(self.turn)):
            raise "Opposite king in check."

    def is_king_attacked(self, color):
        """:return: Whether the king of the given color is attacked.

        :param color: `"w"` or `"b"`.
        """
        square = self.get_king(color)
        if square:
            return self.is_attacked(chess.opposite_color(color), square)
        else:
            return False

    def get_pseudo_legal_moves(self):
        """:yield: Pseudo legal moves in the current position."""
        # TODO: Maximum line length should be 80 characters.
        PAWN_OFFSETS = {
            "b": [16, 32, 17, 15],
            "w": [-16, -32, -17, -15]
        }

        PIECE_OFFSETS = {
            "n": [-18, -33, -31, -14, 18, 33, 31, 14],
            "b": [-17, -15, 17, 15],
            "r": [-16, 1, 16, -1],
            "q": [-17, -16, -15, 1, 17, 16, 15, -1],
            "k": [-17, -16, -15, 1, 17, 16, 15, -1]
        }

        for square in chess.Square.get_all():
            # Skip pieces of the opponent.
            piece = self[square]
            if not piece or piece.color != self.turn:
                continue

            # Pawn moves.
            if piece.type == "p":
                # Single square ahead. Do not capture.
                target = chess.Square.from_x88(square.x88 + PAWN_OFFSETS[self.turn][0])
                if not self[target]:
                    # Promotion.
                    if target.is_backrank():
                        for promote_to in "bnrq":
                            yield chess.Move(square, target, promote_to)
                    else:
                        yield chess.Move(square, target)

                    # Two squares ahead. Do not capture.
                    target = chess.Square.from_x88(square.x88 + PAWN_OFFSETS[self.turn][1])
                    if (self.turn == "w" and square.rank == 2) or (self.turn == "b" and square.rank == 7) and not self[target]:
                        yield chess.Move(square, target)

                # Pawn captures.
                for j in [2, 3]:
                   target_index = square.x88 + PAWN_OFFSETS[self.turn][j]
                   if target_index & 0x88:
                       continue
                   target = chess.Square.from_x88(target_index)
                   if self[target] and self[target].color != self.turn:
                       # Promotion.
                       if target.is_backrank():
                           for promote_to in "bnrq":
                               yield chess.Move(square, target, promote_to)
                       else:
                           yield chess.Move(square, target)
                   # En-passant.
                   elif not self[target] and target.file == self.ep_file:
                       yield chess.Move(square, target)
            # Other pieces.
            else:
                for offset in PIECE_OFFSETS[piece.type]:
                    target_index = square.x88
                    while True:
                        target_index += offset
                        if target_index & 0x88:
                            break
                        target = chess.Square.from_x88(target_index)
                        if not self[target]:
                            yield chess.Move(square, target)
                        else:
                            if self[target].color == self.turn:
                                break
                            yield chess.Move(square, target)
                            break

                        # Knight and king do not go multiple times in their
                        # direction.
                        if piece.type in ["n", "k"]:
                            break

        opponent = chess.opposite_color(self.turn)

        # King-side castling.
        k = "k" if self.turn == "b" else "K"
        if self.get_castling_right(k):
            of = self.get_king(self.turn).x88
            to = of + 2
            if not self[of + 1] and not self[to] and not self.is_check() and not self.is_attacked(opponent, chess.Square.from_x88(of + 1)) and not self.is_attacked(opponent, chess.Square.from_x88(to)):
                yield chess.Move(chess.Square.from_x88(of), chess.Square.from_x88(to))

        # Queen-side castling
        q = "q" if self.turn == "b" else "Q"
        if self.get_castling_right(q):
            of = self.get_king(self.turn).x88
            to = of - 2

            if not self[of - 1] and not self[of - 2] and not self[of - 3] and not self.is_check() and not self.is_attacked(opponent, chess.Square.from_x88(of - 1)) and not self.is_attacked(opponent, chess.Square.from_x88(to)):
                yield chess.Move(chess.Square.from_x88(of), chess.Square.from_x88(to))

    def get_legal_moves(self):
        """:yield: All legal moves in the current position."""
        for move in self.get_pseudo_legal_moves():
            potential_position = self.copy()
            potential_position.make_move(move, False)
            if not potential_position.is_king_attacked(self.turn):
                yield move

    def get_attackers(self, color, square):
        """Gets the attackers of a specific square.

        :param color:
            Filter attackers by this piece color.
        :param square:
            The square to check for.

        :yield:
            Source squares of the attack.
        """
        if not color in ["b", "w"]:
            raise KeyError("Invalid color: %s." % repr(color))

        ATTACKS = [
            20, 0, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 0, 20, 0,
            0, 20, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 20, 0, 0,
            0, 0, 20, 0, 0, 0, 0, 24, 0, 0, 0, 0, 20, 0, 0, 0,
            0, 0, 0, 20, 0, 0, 0, 24, 0, 0, 0, 20, 0, 0, 0, 0,
            0, 0, 0, 0, 20, 0, 0, 24, 0, 0, 20, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 20, 2, 24, 2, 20, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 2, 53, 56, 53, 2, 0, 0, 0, 0, 0, 0,
            24, 24, 24, 24, 24, 24, 56, 0, 56, 24, 24, 24, 24, 24, 24, 0,
            0, 0, 0, 0, 0, 2, 53, 56, 53, 2, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 20, 2, 24, 2, 20, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 20, 0, 0, 24, 0, 0, 20, 0, 0, 0, 0, 0,
            0, 0, 0, 20, 0, 0, 0, 24, 0, 0, 0, 20, 0, 0, 0, 0,
            0, 0, 20, 0, 0, 0, 0, 24, 0, 0, 0, 0, 20, 0, 0, 0,
            0, 20, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 20, 0, 0,
            20, 0, 0, 0, 0, 0, 0, 24, 0, 0, 0, 0, 0, 0, 20
        ]

        RAYS = [
            17, 0, 0, 0, 0, 0, 0, 16, 0, 0, 0, 0, 0, 0, 15, 0,
            0, 17, 0, 0, 0, 0, 0, 16, 0, 0, 0, 0, 0, 15, 0, 0,
            0, 0, 17, 0, 0, 0, 0, 16, 0, 0, 0, 0, 15, 0, 0, 0,
            0, 0, 0, 17, 0, 0, 0, 16, 0, 0, 0, 15, 0, 0, 0, 0,
            0, 0, 0, 0, 17, 0, 0, 16, 0, 0, 15, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 17, 0, 16, 0, 15, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 17, 16, 15, 0, 0, 0, 0, 0, 0, 0,
            1, 1, 1, 1, 1, 1, 1, 0, -1, -1, -1, -1, -1, -1, -1, 0,
            0, 0, 0, 0, 0, 0, -15, -16, -17, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, -15, 0, -16, 0, -17, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, -15, 0, 0, -16, 0, 0, -17, 0, 0, 0, 0, 0,
            0, 0, 0, -15, 0, 0, 0, -16, 0, 0, 0, -17, 0, 0, 0, 0,
            0, 0, -15, 0, 0, 0, 0, -16, 0, 0, 0, 0, -17, 0, 0, 0,
            0, -15, 0, 0, 0, 0, 0, -16, 0, 0, 0, 0, 0, -17, 0, 0,
            -15, 0, 0, 0, 0, 0, 0, -16, 0, 0, 0, 0, 0, 0, -17
        ]

        SHIFTS = {
            "p": 0,
            "n": 1,
            "b": 2,
            "r": 3,
            "q": 4,
            "k": 5
        }

        for source in chess.Square.get_all():
            piece = self[source]
            if not piece or piece.color != color:
                continue

            difference = source.x88 - square.x88
            index = difference + 119

            if ATTACKS[index] & (1 << SHIFTS[piece.type]):
                # Handle pawns.
                if piece.type == "p":
                    if difference > 0:
                        if piece.color == "w":
                            yield source
                    else:
                        if piece.color == "b":
                            yield source
                    continue

                # Handle knights and king.
                if piece.type in ["n", "k"]:
                    yield source

                # Handle the others.
                offset = RAYS[index]
                j = source.x88 + offset
                blocked = False
                while j != square.x88:
                    if self[j]:
                        blocked = True
                        break
                    j += offset
                if not blocked:
                    yield source

    def is_attacked(self, color, square):
        """Checks whether a square is attacked.

        :param color:
            Check if this player is attacking.
        :param square:
            The square the player might be attacking.

        :return:
            A boolean indicating whether the given square is attacked
            by the player of the given color.
        """
        try:
            self.get_attackers(color, square).next()
            return True
        except StopIteration:
            return False

    def is_check(self):
        """:return: Whether the current player is in check."""
        return self.is_king_attacked(self.turn)

    def is_checkmate(self):
        """:return: Whether the current player has been checkmated."""
        if not self.is_check():
            return False
        else:
            try:
                self.get_legal_moves().next()
                return False
            except StopIteration:
                return True

    def is_stalemate(self):
        """:return: Whether the current player is in stalemate."""
        if self.is_check():
            return False
        else:
            try:
                self.get_legal_moves().next()
                return False
            except StopIteration:
                return True

    def is_insufficient_material(self):
        """Checks if there is sufficient material to mate.

        Mating is impossible in:

        * A king versus king endgame.
        * A king with bishop versus king endgame.
        * A king with knight versus king endgame.
        * A king with bishop versus king with bishop endgame, where both
          bishops are on the same color. Same goes for additional
          bishops on the same color.

        Assumes that the position is valid and each player has exactly
        one king.

        :return:
            Whether there is insufficient material to mate.
        """
        piece_counts = self.get_piece_counts()
        if sum(piece_counts.values()) == 2:
            # King versus king.
            return True
        elif sum(piece_counts.values()) == 3:
            # King and knight or bishop versus king.
            if piece_counts["b"] == 1 or piece_counts["n"] == 1:
                return True
        elif sum(piece_counts.values()) == 2 + piece_counts["b"]:
            # Each player with only king and any number of bishops, where all
            # bishops are on the same color.
            white_has_bishop = self.get_piece_counts("w")["b"] != 0
            black_has_bishop = self.get_piece_counts("b")["b"] != 0
            if white_has_bishop and black_has_bishop:
                color = None
                for square in chess.Square.get_all():
                    if self[square] and self[square].type == "b":
                        if color != None and color != square.is_light():
                            return False
                        color = square.is_light()
                return True
        return False

    def is_game_over(self):
        """Checks if the game is over.

        :return:
            Whether the game is over by the rules of chess,
            disregarding that players can agree on a draw, claim a draw
            or resign.
        """
        return (self.is_checkmate() or self.is_stalemate() or
                self.is_insufficient_material())

    def __str__(self):
        return self.fen

    def __repr__(self):
        return "Position.from_fen(%s)" % repr(self.fen)

    def __eq__(self, other):
        return self.fen == other.fen

    def __ne__(self, other):
        return self.fen != other.fen

    def __hash__(self):
        hasher = chess.ZobristHasher(chess.ZobristHasher.POLYGLOT_RANDOM_ARRAY)
        return hasher.hash_position(self)
