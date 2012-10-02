class Piece(object):
    """Represents a chess piece."""

    def __init__(self, type, color):
        """Inits a piece with type and color.

        Args:
            type: The type of the piece (pawn, bishop, knight, rook, king or
                queen) as "p", "b", "n", "r", "k", or "q".
            color: The color of the piece as "w" for white or "b" for black.
        """
        assert type in ["p", "b", "n", "r", "k", "q"]
        self._type = type
        assert color in ["w", "b"]
        self._color = color

    def get_color(self):
        """Gets the color of the piece.

        Returns:
            "b" for black or "w" for white.
        """
        return self._color

    def get_full_color(self):
        """Gets the full color of the piece.

        Returns:
            "black" or "white".
        """
        if self._color == "w":
            return "white"
        else:
            return "black"

    def get_type(self):
        """Gets the type of the piece.

        Returns:
            "p", "b", "n", "r", "k", or "q" for pawn, bishop, knight, rook
            king or queen.
        """
        return self._type

    def get_full_type(self):
        """Gets the full type of the piece.

        Returns:
            "pawn", "bishop", "knight", "rook", "king" or "queen".
        """
        if self._type == "p":
            return "pawn"
        elif self._type == "b":
            return "bishop"
        elif self._type == "n":
            return "knight"
        elif self._type == "r":
            return "rook"
        elif self._type == "k":
            return "king"
        elif self._type == "q":
            return "queen"

    def get_symbol(self):
        """Gets the symbol representing the piece.

        Returns:
            The symbol of the piece as used in FENs. "p", "b", "n", "r", "k" or
            "q" for a black pawn, bishop, knight, rook, king or queen. "P",
            "B", "N", "R", "K", or "Q" for the corresponding white piece.
        """
        if self._color == "w":
            return self._type.upper()
        else:
            return self._type

    def __str__(self):
        return self.get_symbol()

    def __repr__(self):
        return "Piece.parse_symbol('%s')" % get_symbol()

    def __eq__(self, other):
        return self.get_symbol() == other.get_symbol()

    def __ne__(self, other):
        return self.get_symbol() != other.get_symbol()

    @staticmethod
    def parse_symbol(symbol):
        """Parses a piece symbol.

        Args:
            symbol: The symbol of the piece as used in FENs. "p", "b", "n",
            "r", "k" for a black pawn, bishop, knight, rook or king. "P", "B",
            "N", "R", "K" or "Q" for the corresponding white piece.

        Returns:
            An object of the Piece class.
        """
        type = symbol.lower()
        if type == symbol:
            return Piece(type, "b")
        else:
            return Piece(type, "w")
