import re
import libchess

class Move(object):
    def __init__(self, source, target, promotion = None):
        """Inits a move.

        Args:
            source: Source square.
            target: Target square.
            promotion: The piece type the pawn has been promoted to, if any.
        """
        self._source = source
        self._target = target
        self._promotion = promotion

        if promotion:
            assert target.is_backrank()
            assert promotion in "rnbq"

    def get_uci_move(self):
        """Gets an UCI move.

        Returns:
            A string like "a1a2" or "b7b8q".
        """
        promotion = ""
        if self._promotion:
            promotion = self._promotion
        return self._source.get_name() + self._target.get_name() + promotion

    def get_source(self):
        """Gets the source square.

        Returns:
            The source square.
        """
        return self._source

    def get_target(self):
        """Gets the target square.

        Returns:
            The target square.
        """
        return self._target

    def get_promotion(self):
        """Gets the promotion type.

        Returns:
            None, "r", "n", "b" or "q".
        """
        if not self._promotion:
            return None
        else:
            return self._promotion

    def __str__(self):
        return self.get_uci_move()

    def __repr__(self):
        return "Move.from_uci_move('%s')" % self.get_uci_move()

    def __eq__(self, other):
        return self.get_uci_move() == other.get_uci_move()

    def __ne__(self, other):
        return self.get_uci_move() != other.get_uci_move()

    def __hash__(self):
        return hash(self.get_uci_move())

    @staticmethod
    def from_uci_move(move):
        """Parses an UCI move like "a1a2" or "b7b8q

        Returns:
            A new move object.
        """
        uci_move_regex = re.compile("^([a-h][1-8])([a-h][1-8])([rnbq]?)$")
        match = uci_move_regex.match(move)
        return Move(libchess.Square.from_name(match.group(1)), libchess.Square.from_name(match.group(2)), match.group(3))
