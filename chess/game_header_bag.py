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
import datetime
import itertools
import re
import types

date_regex = re.compile(r"^(\?{4}|[0-9]{4})\.(\?\?|[0-9]{2})\.(\?\?|[0-9]{2})$")
round_regex = re.compile(r"^(\?|[0-9]+)$")
time_control_regex = re.compile(r"^([0-9]+)\/([0-9]+):([0-9]+)$")
time_regex = re.compile(r"^([0-9]{2}):([0-9]{2}):([0-9]{2})$")

class GameHeaderBag(collections.MutableMapping):
    """A glorified dictionary of game headers as used in PGNs.

    :param game:
        Defaults to `None`. If bound to a game, any value set for
        `"PlyCount"` is ignored and instead the real ply count of the
        game is the value.
        Aditionally the `"FEN"` header can not be modified if the game
        already contains a move.

    These headers are required by the PGN standard and can not be
    removed:

    `"Event`":
        The name of the tournament or match event. Default is `"?"`.
    `"Site`":
        The location of the event. Default is `"?"`.
    `"Date`":
        The starting date of the game. Defaults to `"????.??.??"`. Must
        be a valid date of the form YYYY.MM.DD. `"??"` can be used as a
        placeholder for unknown month or day. `"????"` can be used as a
        placeholder for an unknown year.
    `"Round`":
        The playing round ordinal of the game within the event. Must be
        digits only or `"?"`. Defaults to `"?"`.
    `"White`":
        The player of the white pieces. Defaults to `"?"`.
    `"Black`":
        The player of the black pieces. Defaults to `"?"`.
    `"Result`":
        Defaults to `"*"`. Other values are `"1-0"` (white won),
        `"0-1"` (black won) and `"1/2-1/2"` (drawn).

    These additional headers are known:

    `"Annotator"`:
        The person providing notes to the game.
    `"PlyCount"`:
        The total moves played. Must be digits only. If a `game`
        parameter is given any value set will be ignored and the real
        ply count of the game will be used as the value.
    `"TimeControl"`:
        For example `"40/7200:3600"` (moves per seconds : sudden death
        seconds). Validated to be of this form.
    `"Time"`:
        Time the game started as a valid HH:MM:SS string.
    `"Termination"`:
        Can be one of `"abandoned"`, `"adjudication"`, `"death"`,
        `"emergency"`, `"normal"`, `"rules infraction"`,
        `"time forfeit"` or `"unterminated"`.
    `"Mode"`:
        Can be `"OTB"` (over-the-board) or `"ICS"` (Internet chess
        server).
    `"FEN"`:
        The initial position if the board as a FEN. If a game parameter
        was given and the game already contains moves, this header can
        not be set. The header will be deleted when set to the standard
        chess start FEN.
    `"SetUp"`:
        Any value set is ignored. Instead the value is `"1"` is the
        `"FEN"` header is set. Otherwise this header does not exist.

    An arbitrary amount of other headers can be set. The capitalization
    of the first occurence of a new header is used to normalize all
    further occurences to it. Additional headers are not validated.

    >>> import chess
    >>> bag = chess.GameHeaderBag()
    >>> bag["Annotator"] = "Alekhine"
    >>> bag["annOTator"]
    'Alekhine'
    >>> del bag["Annotator"]
    >>> "Annotator" in bag
    False

    `KNOWN_HEADERS`:
        The known headers in the order they will appear (if set) when
        iterating over the keys.
    """

    KNOWN_HEADERS = [
        "Event", "Site", "Date", "Round", "White", "Black", "Result",
        "Annotator", "PlyCount", "TimeControl", "Time", "Termination", "Mode",
        "FEN", "SetUp"]

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

    def __normalize_key(self, key):
        if not isinstance(key, basestring):
            raise TypeError(
                "Expected string for GameHeaderBag key, got: %s." % repr(key))
        for header in itertools.chain(self.KNOWN_HEADERS, self.__headers):
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
        elif key == "SetUp":
            return "1" if "FEN" in self else "0"
        elif key in self.__headers:
            return self.__headers[key]
        else:
            raise KeyError(key)

    def __setitem__(self, key, value):
        key = self.__normalize_key(key)
        if not isinstance(value, basestring):
            raise TypeError(
                "Expected value to be a string, got: %s." % repr(value))

        if key == "Date":
            matches = date_regex.match(value)
            if not matches:
                raise ValueError(
                    "Invalid value for Date header: %s." % repr(value))
            year = matches.group(1) if matches.group(1) != "????" else "2000"
            month = int(matches.group(2)) if matches.group(2) != "??" else "10"
            day = int(matches.group(3)) if matches.group(3) != "??" else "1"
            datetime.date(int(year), int(month), int(day))
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
                value = str(int(value))
        elif key == "TimeControl":
            if not time_control_regex.match(value):
                raise ValueError(
                    "Invalid value for TimeControl header: %s." % repr(value))
        elif key == "Time":
            matches = time_regex.match(value)
            if (not matches or
                int(matches.group(1)) < 0 or int(matches.group(1)) >= 24 or
                int(matches.group(2)) < 0 or int(matches.group(2)) >= 60 or
                int(matches.group(3)) < 0 or int(matches.group(3)) >= 60):
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
                del self["SetUp"]
                return
            else:
                self["SetUp"] = "1"

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
        elif key == "SetUp":
            return "FEN" in self
        else:
            return self.__normalize_key(key) in self.__headers
