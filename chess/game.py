import chess
import re

class Game(chess.GameNode):
    def __init__(self, position=chess.Position(), comment=""):
        chess.GameNode.__init__(self, None, None, (), comment)
        self._position = position

        self._headers = {
            "Event": "?",
            "Site": "?",
            "Date": "??.??.??",
            "Round": "1",
            "White": "?",
            "Black": "?",
            "Result": "*"
        }

        self._date_regex = re.compile("^(\\?\\?|[0-9]{4})\\.(\\?\\?|[0-9][0-9])\\.(\\?\\?|[0-9][0-9])$")

        if self._position != chess.Position()
            self._headers["FEN"] = self._position.get_fen()

    def get_nags(self):
        raise Exception("Game object can not have NAGs.")

    def add_nag(self, nag):
        raise Exception("Game object can not have NAGs.")

    def remove_nag(self, nag):
        raise Exception("Game object can not have NAGs.")

    def set_header(self, name, value):
        if name == "Date":
            if not self._date_regex.match(value):
                raise ValueError("Invalid value for Date header: %s." % repr(value))
        elif name == "Round":
            if not re.compile("^[0-9]+$").match(value):
                raise ValueError("Invalid value for Round header: %s." % repr(value))
        elif name == "Result":
            if not value in ["1-0", "0-1", "1/2-1/2", "*"]:
                raise ValueError("Invalid value for Result header: %s." % repr(value))
        self._headers[name] = value

    def get_header(self, name):
        return self._headers[name]

    def remove_header(self, name):
        if name in ["Event", "Site", "Date", "Round", "White", "Black", "Result"]:
            raise KeyError("Can not remove %s header because it is required." % name)
        self._headers.remove(name)
