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
import collections
import itertools
import re
import types

# TODO!
date_regex = 
round_regex =
time_control_regex = 
time_regex = 

class GameHeaderBag(collections.MutableMapping):

    KNOWN_HEADERS = [
        "Event", "Site", "Date", "Round", "White", "Black", "Result",
        "Annotator", "PlyCount", "TimeControl", "Time", "Termination", "Mode",
        "FEN"]

    def __init__(self, game=None):
        self.__game = game
        self.__headers = {
            "Event": "?",
            "Site": "?",
            "Date": "????.??.??",
            "Round": "?",
            "White": "?",
            "Black": "?",
            "Result": "*",
        }

    def __normalize_key(key):
        if type(key) is not types.StringType:
            raise TypeError(
                "Expected string for GameHeaderBag key, got: %s." % repr(key))
        for header in itertools.chain(KNOWN_HEADERS, self.__headers):
            if header.lower() == key.lower():
                return header
        return key

    def __len__(self):
        i = 0
        for header in self:
            i += 1
        return i

    def __iter__(self):
        for known_header in KNOWN_HEADERS:
            if known_header in self:
                yield known_header
        for header in self:
            if not header in KNOWN_HEADERS:
                yield header

    def __getitem__(self, key):
        key = self.__normalize_key(key)
        if self.__game and key == "PlyCount":
            return self.__game.ply
        elif key in self.__headers:
            return self.__headers[key]
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        key = self.__normalize_key(key)
        if type(value) is not types.StringType:
            raise TypeError(
                "Expected value to be a string, got: %s." % repr(value))

        if key == "Date":
            if not date_regex.match(value):
                raise ValueError(
                    "Invalid value for Date header: %s." % repr(value))
        elif key == "Round":
            if not round_regex.match(value):
                raise ValueError(
                    "Invalid value for Round header: %s." % repr(value))
        elif key == "Result":
            if not value in ["1-0", "0-1", "1/2-1/2", "*"]:
                raise ValueError(
                    "Invalid value for Result header: %s." % repr(value))
        elif key == "PlyCount":
            if not value.isdigit():
                raise ValueError(
                    "Invalid value for PlyCount header: %s." % repr(value))
            else:
                value = str(int(vakue))
        elif key == "TimeControl":
            if not time_control_regex.match(value):
                raise ValueError(
                    "Invalid value for TimeControl header: %s." % repr(value))
        elif key == "Time":
            if not time_regex.match(value):
                raise ValueError(
                    "Invalid value for Time header: %s." % repr(value))
        elif key == "Termination":
            value = value.lower()
            if not value in ["abandoned", "adjudication", "death", "emergency",
                             "normal", "rules infraction", "time forfeit",
                             "unterminated"]:
                raise ValueError(
                    "Invalid value for Termination header: %s." % repr(value))
        elif key == "Mode":
            value = value.upper()
            if not value in ["OTB", "ICS"]:
                raise ValueError(
                    "Invalid value for Mode header: %s." % repr(value))
        elif key == "FEN":
            value = chess.Position(value).fen

            if value == chess.Position.START_FEN:
                if not "FEN" in self:
                    return
            else:
                if "FEN" in self and self["FEN"] == value:
                    return

            if self.__game and self.__game.ply > 0:
                raise ValueError(
                    "FEN header can not be set, when there are already moves.")

            if value == chess.Position.START_FEN:
                del self["FEN"]
                return

        self.__headers[key] = value

    def __delitem__(self, key):
        k = self.__normalize_key(key)
        if k in ["Event", "Site", "Date", "Round", "White", "Black", "Result"]:
            raise KeyError(
                "The %s key can not be deleted because it is required." % k)
        del self.__headers[k]

    def __contains__(self, key):
        key = self.__normalize_key(key)
        if self.__game and key == "PlyCount":
            return True
        else:
            return self.__normalize_key(key) in self.__headers
