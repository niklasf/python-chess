import chess

class MoveInfo(object):
    """Represents information about a move that depend on its context."""

    def __init__(self, move, piece, san, captured, is_enpassant, is_king_side_castle, is_queen_side_castle, is_check, is_checkmate):
        """Inits a move info object.

        Args:
            move: The corresponding move.
            piece: The piece that has been moved.
            san: The moves standard algebraic notation.
            captured: The piece that has been captured, if any.
            is_enpassant: Whether the move is en passant.
            is_king_side_castle: Whether it is a king-side-castling move.
            is_queen_side_castle: Whether it is a queen-side-castling move.
            is_check: Whether the move gives check.
            is_checkmate: Whether the move gives checkmate.
        """
        self._move = move
        self._piece = piece
        self._captured = captured
        self._san = san
        self._is_enpassant = is_enpassant
        self._is_king_side_castle = is_king_side_castle
        self._is_queen_side_castle = is_queen_side_castle
        self._is_check = is_check
        self._is_checkmate = is_checkmate

    def get_move(self):
        """Gets the move object.

        Returns:
            The move object.
        """
        return self._move

    def get_piece(self):
        """Gets the moved piece.

        Returns:
            The moved piece.
        """
        return self._piece

    def get_captured(self):
        """Gets the captured piece.

        Returns:
            The captured piece or None.
        """
        return self._captured

    def get_san(self):
        """Gets the standard algebraic notation of the move.

        Returns:
            The moves SAN.
        """
        return self._san

    def is_enpassant(self):
        """Gets whether it is an en-passant move.

        Returns:
            A boolean indicating if it is an enpassant move.
        """
        return self._is_enpassant

    def is_king_side_castle(self):
        """Gets whether it is a king-side-castling move.

        Returns:
            A boolean indicating whether it is a king-side-castling move.
        """
        return self._is_king_side_castle

    def is_queen_side_castle(self):
        """Gets whether it is a queen-side-castling move.

        Returns:
            A boolean indicating whether it is a queen-side-castling move.
        """
        return self._is_queen_side_castle

    def is_castle(self):
        """Gets whether it is a castling move.

        Returns:
            A boolean indicating whether it is a castling move.
        """
        return self._is_king_side_castle or self._is_queen_side_castle

    def is_check(self):
        """Gets whether it is a checking move.

        Returns:
            A boolean indicating whether the move gives check.
        """
        return self._is_check

    def is_checkmate(self):
        """Gets whether it is a checkmating move.

        Returns:
            A boolean indicating whether the move gives checkmate.
        """
        return self._is_checkmate

    def is_legal(self):
        """Checks if the move is legal.

        Returns:
            A boolean indicating whether the move is legal in its context.
        """
        return self._is_legal

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        return self.get_move() == other.get_move()
            and self.get_piece() == other.get_piece()
            and self.get_capured() == other.get_captured()
            and self.get_san() == other.get_san()
            and self.is_enpassant() == other.is_enpassant()
            and self.is_king_side_castle() == other.is_king_side_castle()
            and self.is_queen_side_castle() == other.is_queen_side_castle()
            and self.is_check() == other.is_check()
            and self.is_checkmate() == other.is_checkmate()

    def __ne__(self, other):
       return not self.__eq__(other)

    def __str__(self):
        return self.get_san()

    def __repr__(self):
        return "MoveInfo(move=%s, piece=%s, san=%s, captured=%s, is_enpassant=%s, is_king_side_castle=%s, is_queen_side_castle=%s, is_check=%s, is_checkmate=%s)" % repr(self.get_move()), repr(self.get_piece()), repr(self.get_san()), repr(self.get_captured()), repr(self.is_enpassant()), repr(self.is_king_side_castle()), repr(self.is_queen_side_castle()), repr(self.is_check()), repr(self.is_checkmate())
