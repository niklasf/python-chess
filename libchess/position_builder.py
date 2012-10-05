import libchess
import re

class PositionBuilder(object):
    """Helper to build a chess position."""

    def __init__(self, fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"):
        """Inits an empty position."""
        self._board = [None] * 128
        self._turn = "w"
        self._castling = ""
        self._ep_file = None
        self._half_moves = 0
        self._move_number = 1
        self.set_fen(fen)

    def get(self, square):
        """Gets the piece on the given square.

        Args:
            square: A Square object.

        Returns:
            A piece object for the piece that is on that square or None if
            there is no piece on the square.
        """
        return self._board[square.get_0x88_index()]

    def set(self, square, piece):
        """Sets the piece on the given square.

        Args:
            square: The square to set the piece on.
            piece: The piece to set. None to clear the square.
        """
        self._board[square.get_0x88_index()] = piece

    def clear_board(self):
        """Removes all the pieces from the board."""
        self._board = [None] * 128

    def reset(self):
        """Resets to the default chess position."""
        self.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 ")

    def get_fen(self):
        """Gets the FEN representation of the position.

        Returns:
            The FEN string representing the position.
        """
        # Board setup.
        empty = 0
        fen = ""
        for y in range(7, -1, -1):
            for x in range(0, 8):
                square = libchess.Square(x, y)

                # Add pieces.
                if not self.get(square):
                    empty += 1
                else:
                    if empty > 0:
                        fen += str(empty)
                        empty = 0
                    fen += self.get(square).get_symbol()

            # Boarder of the board.
            if empty > 0:
                fen += str(empty)
            if not (x == 7 and y == 0):
                fen += "/"
            empty = 0

        # Join the parts together.
        return " ".join([
            fen,
            self.get_turn(),
            self._castling if self._castling else "-",
            self._ep_file + ("3" if self._turn == "b" else "6") if self._ep_file else "-",
            str(self.get_half_moves()),
            str(self.get_ply())])

    def set_fen(self, fen):
        """Sets the position by A FEN.

        Args:
            fen: The FEN.
        """
        # Split into 6 parts.
        tokens = fen.split()
        if len(tokens) != 6:
            raise libchess.FenError("A FEN does not consist of 6 parts.")

        # Check that the position part is valid.
        rows = tokens[0].split("/")
        assert len(rows) == 8
        for row in rows:
            field_sum = 0
            previous_was_number = False
            for char in row:
                if char in "12345678":
                    if previous_was_number:
                        raise libchess.FenError("Position part of the FEN is invalid: Multiple numbers immediately after each other.")
                    field_sum += int(char)
                    previous_was_number = True
                elif char in "pnbrkqPNBRKQ":
                    field_sum += 1
                    previous_was_number = False
                else:
                    raise libchess.FenError("Position part of the FEN is invalid: Invalid character in the position part of the FEN.")

            if field_sum != 8:
                libchess.FenError("Position part of the FEN is invalid: Row with invalid length.")


        # Check that the other parts are valid.
        if not tokens[1] in ["w", "b"]:
            raise libchess.FenError("Turn part of the FEN is invalid: Expected b or w.")
        if not re.compile("^(KQ?k?q?|Qk?q?|kq?|q|-)$").match(tokens[2]):
            raise libchess.FenError("Castling part of the FEN is invalid.")
        if not re.compile("^(-|[a-h][36])$").match(tokens[3]):
            raise libchess.FenError("En-passant part of the FEN is invalid.")
        if not re.compile("^(0|[1-9][0-9]*)$").match(tokens[4]):
            raise libchess.FenError("Half move part of the FEN is invalid.")

        if not re.compile("^[1-9][0-9]*$").match(tokens[5]):
            raise libchess.FenError("Ply part of the FEN is invalid.")

        # Set pieces on the board.
        self._board = [None] * 128
        i = 0
        for symbol in tokens[0]:
            if symbol == "/":
                i += 8
            elif symbol in "12345678":
                i += int(symbol)
            else:
                self._board[i] = libchess.Piece.from_symbol(symbol)
                i += 1

        # Set the turn.
        self._turn = tokens[1]

        # Set the castling rights.
        for type in ["K", "Q", "k", "q"]:
            self.set_castling_right(type, type in tokens[2])

        # Set the en-passant file.
        if tokens[3] == "-":
            self._ep_file = None
        else:
            self._ep_file = tokens[3][0]

        # Set the move counters.
        self._half_moves = int(tokens[4])
        self._ply = int(tokens[5])

    def get_ply(self):
        """Gets the ply.

        Returns:
            The ply.
        """
        return self._ply

    def set_ply(self, ply):
        """Sets the ply.

        Args:
            ply: The new ply, starting at 1 for the first move.
        """
        assert ply >= 1
        self._ply = ply

    def get_half_moves(self):
        """Gets the half move count since the last capture or pawn move.

        Returns:
             The half move count.
        """
        return self._half_moves

    def set_half_moves(self, half_moves):
        """Sets the half move count since the last capture or pawn move.

        Args:
            The new half move count.
        """
        assert half_moves >= 0
        self._half_moves = half_moves

    def get_turn(self):
        """Gets the current turn.

        Returns:
            "w" if it is white's turn, "b" if it is black's turn.
        """
        return self._turn

    def set_turn(self, turn):
        """Sets the current turn.

        Args:
            turn: "w" if it is white's turn, "b" if it is black's turn.
        """
        assert turn in ["w", "b"]
        self._turn = turn

    def toggle_turn(self):
        """Toggles the turn."""
        self._turn = libchess.opposite_color(self._turn)

    def get_ep_file(self):
        """Gets the en-passant file.

        Returns:
            None, "a", "b", "c", "d", "e", "f", "g" or "h".
        """
        return self._ep_file

    def set_ep_file(self, ep_file):
        """Sets the en-passant file.

        Args:
            ep_file: None, "a", "b", "c", "d", "e", "f", "g", "h".
        """
        assert ep_file in [None, "a", "b", "c", "d", "e", "f", "g", "h"]
        self._ep_file = ep_file

    def get_castling_right(self, type):
        """Checks whether a player as a castling right.

        Args:
            type: The castling move to check for. "K" for kinside castling of
                the white player, "Q" for queenside castling of the white player.
                "k" and "q" for the corresponding castling moves of the black
                player.

        Returns:
            A boolean indicating whether the player has that castling right.
        """
        assert type in ["K", "Q", "k", "q"]
        return type in self._castling

    def set_castling_right(self, type, status):
        """Sets a castling right.

        Args:
            type: "K", "Q", "k" or "q" as used by get_castling_right() for the
                castling move types.
            status: A boolean indicating whether that castling right should be
                given or denied.
        """
        assert type in ["K", "Q", "k", "q"]

        castling = ""
        for t in ["K", "Q", "k", "q"]:
            if type == t:
                if status:
                    castling += t
            elif self.get_castling_right(t):
                castling += t
        self._castling = castling

    def get_0x88_board(self):
        """Gets a 0x88 tuple of pieces.

        Returns:
            A tuple with the 0x88 board representation.
        """
        return tuple(self._board)

    def set_0x88_board(self, board):
        """Sets the board by a 0x88 tuple or list of pieces.

        Returns:
            A list or tuple.
        """
        assert len(board) == 128
        for i in range(128):
            self._board[i] = board[i]

    def __str__(self):
        return self.get_fen()

    def __repr__(self):
        return "PositionBuilder(fen=%d)" % repr(self.get_fen())
