class Square(object):
    """Represents a square on the chess board."""

    def __init__(self, name):
        """Inits a square with via its name.

        Args:
            x: The x-coordinate, starting with 0 for the a-file.
            y: The y-coordinate, starting with 0 for the first rank.
        """
        assert len(name) == 2
        assert name[0] in ["a", "b", "c", "d", "e", "f", "g", "h"]
        assert name[1] in ["1", "2", "3", "4", "5", "6", "7", "8"]
        self._name = name

    def get_x(self):
        """Gets the x-coordinate, starting with 0 for the a-file.

        Returns:
            An integer between 0 and 7.
        """
        return ord(self._name[0]) - ord("a")

    def get_y(self):
        """Gets the y-coordinate, starting with 0 for the first rank.

        Returns:
            An integer between 0 and 7.
        """
        return ord(self._name[1]) - ord("1")

    def is_dark(self):
        """Checks the color of the square.

        Returns:
            A boolean indicating if the square is dark.
        """
        return (ord(self._name[0]) - ord(self._name[1])) % 2 == 0

    def is_light(self):
        """Checks the color of the square.

        Returns:
            A boolean indicating if the square is light.
        """
        return not self.is_dark()

    def get_rank(self):
        """Gets the rank.

        Returns:
            An integer between 1 and 8, where 1 is the first rank.
        """
        return self.get_y() + 1

    def get_file(self):
        """Gets the file.

        Returns:
            "a", "b", "c", "d", "e", "f", "g" or "h".
        """
        return self._name[0]

    def get_name(self):
        """Gets the algebraic name.

        Returns:
            An algebraic name like "a1".
        """
        return self._name

    def get_0x88_index(self):
        """Gets the index of the square in 0x88 board representation.

        Returns:
            An integer between 0 and 119.
        """
        return self.get_x() + 16 * (7 - self.get_y())

    def is_backrank(self):
        """Checks whether the square is on the backrank of either side.

        Returns:
            A boolean indicating if it is a backrank square.
        """
        return self._name[1] in ["1", "8"]

    def __str__(self):
        return self.get_name()

    def __repr__(self):
        return "Square('%s')" % self.get_name()

    def __eq__(self, other):
        return self.get_x() == other.get_x() and self.get_y() == other.get_y()

    def __ne__(self, other):
        return self.get_x() != other.get_x() or self.get_y() != other.get_y()

    def __hash__(self):
        return self.get_0x88_index()

    @classmethod
    def from_0x88_index(cls, index):
        """Gets a square from a 0x88 index.

        Args:
            index: An index of the 0x88 board representation.

        Returns:
            An object of the Square class.
        """
        index = int(index)
        assert index >= 0 and index <= 128
        assert not index & 0x88 # On the board.
        return cls("abcdefgh"[index & 7] + "87654321"[index >> 4])

    @classmethod
    def from_rank_and_file(cls, rank, file):
        """Gets a square from rank and file.

        Args:
            rank: An integer between 1 and 8 for the rank.
            file: "a", "b", "c", "d", "e", "f", "g" or "h".

        Returns:
            An object of the Square class.
        """
        rank = int(rank)
        assert rank >= 1 and rank <= 8
        assert file in ["a", "b", "c", "d", "e", "f", "g", "h"]
        return cls(file + str(rank))

    @classmethod
    def from_x_and_y(cls, x, y):
        assert x >= 0 and x <= 7
        assert y >= 0 and y <= 7
        return cls("abcdefgh"[x] + "12345678"[y])

    @classmethod
    def get_all(cls):
        """Gets all squares.

        Yields:
            All squares.
        """
        for x in range(0, 8):
            for y in range(0, 8):
                yield cls.from_x_and_y(x, y)
