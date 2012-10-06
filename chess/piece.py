class Piece(object):
    """Represents a chess piece."""

    def __init__(self, symbol):
        """Inits a piece with type and color.

        Args:
            symbol: The symbol of the piece as used in FENs.
        """
        if not symbol.lower() in ["p", "b", "n", "r", "k", "q"]:
            raise ValueError("Invalid piece symbol: %s." % repr(symbol))
        self._symbol = symbol

    def get_color(self):
        """Gets the color of the piece.

        Returns:
            "b" for black or "w" for white.
        """
        return "b" if self._symbol.lower() == self._symbol else "w"

    def get_full_color(self):
        """Gets the full color of the piece.

        Returns:
            "black" or "white".
        """
        return "black" if self._symbol.lower() == self._symbol else "white"

    def get_type(self):
        """Gets the type of the piece.

        Returns:
            "p", "b", "n", "r", "k", or "q" for pawn, bishop, knight, rook
            king or queen.
        """
        return self._symbol.lower()

    def get_full_type(self):
        """Gets the full type of the piece.

        Returns:
            "pawn", "bishop", "knight", "rook", "king" or "queen".
        """
        type = self.get_type()
        if type == "p":
            return "pawn"
        elif type == "b":
            return "bishop"
        elif type == "n":
            return "knight"
        elif type == "r":
            return "rook"
        elif type == "k":
            return "king"
        elif type == "q":
            return "queen"

    def get_symbol(self):
        """Gets the symbol representing the piece.

        Returns:
            The symbol of the piece as used in FENs. "p", "b", "n", "r", "k" or
            "q" for a black pawn, bishop, knight, rook, king or queen. "P",
            "B", "N", "R", "K", or "Q" for the corresponding white piece.
        """
        return self._symbol

    def __str__(self):
        return self.get_symbol()

    def __repr__(self):
        return "Piece('%s')" % self.get_symbol()

    def __eq__(self, other):
        if not other:
            return True
        return self.get_symbol() == other.get_symbol()

    def __ne__(self, other):
        if not other:
            return True
        return self.get_symbol() != other.get_symbol()

    def __hash__(self):
        return ord(self.get_symbol())

    @classmethod
    def from_color_and_type(cls, color, type):
        """Parses a piece symbol.

        Args:
            color: "w", "b", "white" or "black".
            type: "p", "pawn", "r", "rook", "n", "knight", "b", "bishop", "q",
                "queen", "k" or "king".

        Returns:
            An object of the Piece class.
        """
        if type in ["p", "pawn"]:
            symbol = "p"
        elif type in ["r", "rook"]:
            symbol = "r"
        elif type in ["n", "knight"]:
            symbol = "n"
        elif type in ["b", "bishop"]:
            symbol = "b"
        elif type in ["q", "queen"]:
            symbol = "q"
        elif type in ["k", "king"]:
            symbol = "k"
        else:
            raise ValueError("Invalid piece type: %s." % repr(type))

        if color in ["w", "white"]:
            return cls(symbol.upper())
        elif color in ["b", "black"]:
            return cls(symbol)
        else:
            raise ValueError("Invalid piece color: %s." % repr(color))
