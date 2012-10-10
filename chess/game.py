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
import re

class Game(chess.GameNode):
    def __init__(self, position=None, comment=""):
        chess.GameNode.__init__(self, None, None, (), comment)

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

        if position and position != chess.Position():
            self._headers["FEN"] = self._position.get_fen()

    def get_position(self):
        if "FEN" in self._headers:
            return chess.Position(self._headers["FEN"])
        else:
            return chess.Position()

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
            if not re.compile("^\\?|[0-9]+$").match(value):
                raise ValueError("Invalid value for Round header: %s." % repr(value))
        elif name == "Result":
            if not value in ["1-0", "0-1", "1/2-1/2", "*"]:
                raise ValueError("Invalid value for Result header: %s." % repr(value))
        elif name == "FEN":
            if self._variations and value != self.get_position().get_fen():
                raise KeyError("Can not set FEN header when the game already has moves.")
            if value == chess.Position().get_fen():
                return self.remove_header("FEN")
        self._headers[name] = value

    def get_header(self, name):
        return self._headers[name]

    def remove_header(self, name):
        if name in ["Event", "Site", "Date", "Round", "White", "Black", "Result"]:
            raise KeyError("Can not remove %s header because it is required." % name)
        self._headers.remove(name)
