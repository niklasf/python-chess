import chess

class Game(chess.GameNode):
    def __init__(self, position=chess.Position(), comment=""):
        chess.GameNode.__init__(self, None, None, (), comment)
        self._position = position

    def get_nags(self):
        raise Exception("Game object can not have NAGs.")

    def add_nag(self, nag):
        raise Exception("Game object can not have NAGs.")

    def remove_nag(self, nag):
        raise Exception("Game object can not have NAGs.")
