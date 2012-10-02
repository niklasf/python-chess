import libchess

class Position(object):
    """Represents a chess position."""

    def __init__(self):
        """Inits an empty position."""
        self._board = [None] * 128
        self._turn = "w"
        self._castling = ""
        self._ep_file = None
        self._half_moves = 0
        self._move_number = 1

    def copy(self):
        """Gets a copy of the position. The copy will not change when the
        original instance is changed.

        Returns:
            An exact copy of the positon.
        """
        return Position.from_fen(self.get_fen())

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
        """Sets a piece on the given square.

        Args:
            square: The square to set the piece on.
            piece: The piece to set. None to clear the square.
        """
        self._board[square.get_0x88_index()] = piece

        # Update castling rights.
        for type in ["K", "Q", "k", "q"]:
            if not self.get_theoretical_castling_right(type):
               self.set_castling_right(type, False)

    def clear(self):
        """Removes all pieces from the board."""
        self._board = [None] * 128
        self._castling = ""

    def reset(self):
        """Resets to the default chess position."""
        self.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def get_turn(self):
        """Gets whos turn it is.

        Returns:
            "w" if it is white's turn. "b" if it is black's turn.
        """
        return self._turn

    def set_turn(self, turn):
        """Sets whos turn it is.

        Args:
            turn: "w" if it is white's turn. "b" is it is black's turn.
        """
        assert turn in ["w", "b"]
        self._turn = turn

    def toggle_turn(self):
        """Toggles whos turn it is."""
        self.set_turn(libchess.opposite_color(self._turn))

    def get_castling_right(self, type):
        """Checks the castling rights.

        Args:
            type: The castling move to check for. "K" for kingside castling of
                white player, "Q" for queenside castling of the white player.
                "k" and "q" for the corresponding castling moves of the black
                 player.

        Returns:
            A boolean indicating whether the player has that castling right.
        """
        assert type in ["K", "Q", "k", "q"]
        return type in self._castling

    def get_theoretical_castling_right(self, type):
        """Checks if a player could have a castling right in theory from
        looking just at the piece positions.

        Args:
            type: The castling move to check for. "K", "Q", "k" or "q" as used
                by get_castling_right().

        Returns:
            A boolean indicating whether the player could theoretically have
            that castling right.
        """
        assert type in ["K", "Q", "k", "q"]
        if type == "K" or type == "Q":
            if self.get(libchess.Square.from_name('e1')) != libchess.Piece('w', 'k'):
                return False
            if type == "K":
                return self.get(libchess.Square.from_name('h1')) == libchess.Piece('w', 'r')
            elif type == "Q":
                return self.get(libchess.Square.from_name('a1')) == libchess.Piece('w', 'r')
        elif type == "k" or type == "q":
            if self.get(libchess.Square.from_name('e8')) != libchess.Piece('b', 'l'):
                return False
            if type == "k":
                return self.get(libchess.Square.from_name('h8')) == libchess.Piece('b', 'r')
            elif type == "q":
                return self.get(libchess.Square.from_name('a8')) == libchess.Piece('b', 'r')

    def set_castling_right(self, type, status):
        """Sets a castling right.

        Args:
            type: "K", "Q", "k" or "q" as used by get_castling_right() for the
                castling move types.
            status: A boolean indicating whether that castling right should be
                given or denied.
        """
        assert type in ["K", "Q", "k", "q"]
        assert not status or self.get_theoretical_castling_right(type)

        castling = ""
        for t in ["K", "Q", "k", "q"]:
            if type == t:
                if status:
                    castling += t
            elif self.get_castling_right(self, t):
                castling += t
        self._castling = castling

    def get_ep_file(self):
        """The en-passant file.

        Returns:
            The file on which a pawn has just moved two steps forward as "a",
            "b", "c", "d", "e", "f", "g", "h" or None, if there is no such
            file.
        """
        return self._ep_file

    def set_ep_file(self, file):
        """Sets the en-passant file.

        Args:
            file: The file on which a pawn has just moved two steps forward as
                "a", "b", "c", "d", "e", "f", "g", "h" or None, if there is no
                such file.
        """
        assert file in ["a", "b", "c", "d", "e", "f", "g", "h", None]
        self._ep_file = file

    def get_half_moves(self):
        """Gets the number of half-moves since the last capture or pawn move.

        Returns:
            An integer.
        """
        return self._half_moves

    def set_half_moves(self, half_moves):
        """Sets the number of half-moves since the last capture or pawn move.

        Args:
            half_moves: An integer.
        """
        half_moves = int(half_moves)
        assert half_moves >= 0
        self._half_moves = half_moves

    def get_move_number(self):
        """Gets the number of this move. The game starts at 1 and the counter
        is incremented every time white moves.

        Returns:
            An integer.
        """
        return self._move_number

    def set_move_number(self, move_number):
        """Sets the move number.

        Args:
            move_number: An integer.
        """
        return self._move_number

    def get_piece_counts(self, color = "wb"):
        """Gets a dictionary keyed by "p", "b", "n", "r", "k" and "q" with the
        counts of pawns, bishops, knights, rooks, kings and queens on the
        board.

        Args:
            color: A color to filter the pieces by. Defaults to "wb" for both
                black and white pieces. Valid arguments are "w", "b", "wb" and
                "bw".

        Returns:
            A dictionary of piece counts.
        """
        assert color in ["w", "b", "wb", "bw"]
        counts = {
            "p": 0,
            "b": 0,
            "n": 0,
            "r": 0,
            "k": 0,
            "q": 0,
        }
        for piece in self._board:
            if piece and piece.get_color() in color:
                counts[piece.get_type()] += 1
        return counts

    def get_king(self, color):
        """Gets the square of the king.

        Args:
            color: "w" for the white players king. "b" for the black players
                king.

        Returns:
            The square of the king or None if that player has no king.
        """
        assert color in ["w", "b"]
        for piece in self._board:
            if piece and piece.get_color() == color and piece.get_type() == 'k':
                return piece

    def get_fen(self):
        """Gets the FEN representation of the position.

        Returns:
            The fen string representing the position.
        """
        # Board setup.
        empty = 0
        fen = ""
        for y in range(7, -1, -1):
            for x in range(0, 8):
                i = libchess.Square(x, y).get_0x88_index()
                # Add pieces.
                if not self._board[i]:
                    empty += 1
                else:
                    if empty > 0:
                        fen += str(empty)
                        empty = 0
                    fen += self._board[i].get_symbol()

            # Border of the board.
            if empty > 0:
                fen += str(empty)
            if not (x == 7 and y == 0):
                fen += "/"
            empty = 0

        # Castling.
        castling_flag = "-"
        if self._castling:
            castling_flag = self._castling

        # En-passant.
        ep_flag = "-"
        if self._ep_file:
            self.ep_flag = self._ep_file
            if self._turn == "w":
                ep_flag += "6"
            else:
                ep_flag += "3"

        return " ".join([fen, self._turn, castling_flag, ep_flag, str(self._half_moves), str(self._move_number)])

    def set_fen(self, fen):
        """Sets the position by a FEN.

        Args:
            fen: The FEN.
        """
        # Split into 6 parts.
        tokens = fen.split()
        assert len(tokens) == 6

        # Check that every row is valid.
        rows = tokens[0].split("/")
        assert len(rows) == 8
        for row in rows:
            field_sum = 0
            previous_was_number = False
            for char in row:
                assert char in "12345678pnbrkqPNBRKQ"
                if char in "12345678":
                    assert not previous_was_number
                    field_sum += int(char)
                    previous_was_number = True
                else:
                    field_sum += 1
                    previous_was_number = False
            assert field_sum == 8

        # Assertions.
        assert tokens[1] in ["w", "b"]
        assert re.compile("^(KQ?k?q?|Qk?q?|kq?|q|-)$").match(tokens[2])
        assert re.compile("^(-|[a-h][36])$").match(tokens[3])

        # Set the move counters.
        half_moves = int(tokens[4])
        assert half_moves >= 0
        move_number = int(tokens[5])
        assert move_number >= 1
        self._half_moves = half_moves
        self._move_number = move_number

        # Set the en-passant file.
        if tokens[3] == "-":
            self._ep_file = None
        else:
            self._ep_file = tokens[3][0]

        # Set the castling.
        if tokens[2] == "-":
            self._castling = ""
        else:
            self._castling = tokens[2]

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

        # Update castling rights.
        for type in ["K", "Q", "k", "q"]:
            if not self.get_theoretical_castling_right(type):
               self.set_castling_right(type, False)

    def validate():
        """Validates the position. Castling rights are automatically corrected,
        invalid en-passant flags are ignored. Players can have more attackers
        on their king than is possible through discovery.

        Raises:
            - Missing black king.
            - Missing white king.
            - Too many black kings.
            - Too many white kings.
            - Too many black pawns.
            - Too many white pawns.
            - Too many black pieces.
            - Too many white pieces.
            - Both sides in check.
            - Opposite king in check.
        """
        for color in ["white", "black"]:
            piece_counts = self.get_piece_counts(color[0])
            if piece_counts["k"] == 0:
                raise "Missing %s king." % color
            elif piece_counts["k"] > 1:
                raise "Too many %s kings." % color

            if piece_counts["p"] > 8:
                raise "Too many %s pawns." % color

            if sum(piece_counts) > 16:
                raise "Too many %s pieces." % color

        if self.is_king_attacked("w") and self.is_king_attacked("b"):
            raise "Both sides in check."

        if self.is_king_attacked(libchess.opposite_color(self.get_turn())):
            raise "Opposite king in check."


    @staticmethod
    def get_default():
        """Gets the default position.

        Returns:
            A new position, initialized to the default chess position.
        """
        default_position = Position()
        default_position.reset()
        return default_position

    @staticmethod
    def from_fen(fen):
        """Gets a position from a FEN.

        Args:
            fen: The FEN.

        Returns:
            A new position created from the fen.
        """
        position = Position()
        position.set_fen(fen)
        return position
