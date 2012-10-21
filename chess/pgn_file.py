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

tag_regex = re.compile(r"\[([A-Za-z0-9]+)\s+\"(.*)\"\]")
movetext_regex = re.compile(r"""
    (\;.*?[\n\r])
    |(\{.*?[^\\]\})
    |(\$[0-9]+)
    |(\()
    |(\))
    |(\*|1-0|0-1|1/2-1/2)
    |(
        ([a-hKQRBN][a-hxKQRBN1-8+#=\-]{1,6}
        |O-O(?:\-O)?)
        ([\?!]{1,2})*
    )
    """, re.DOTALL | re.VERBOSE)

class PgnFile(object):
    def __init__(self):
        self._games = []

    def add_game(self, game):
        self._games.append(game)

    def __len__(self):
        return len(self._games)

    def __getitem__(self, key):
        return self._games[key]

    def __setitem__(self, key, value):
        self._games[key] = value

    def __delitem__(self, key):
        del self._games[key]

    def __iter__(self):
        for game in self._games:
            yield game

    def __reversed__(self):
        for game in reversed(self._games):
            yield game

    def __contains__(self, game):
        return game in self._games

    @staticmethod
    def __parse_movetext(game, movetext):
        variation_stack = [game]
        for match in movetext_regex.finditer(movetext):
            token = match.group(0)
            if token in ["1-0", "0-1", "1/2-1/2", "*"] and len(variation_stack) == 1:
                game.headers["Result"] = token
            elif token.startswith("%"):
                # Ignore rest of line comments.
                pass
            elif token.startswith("{"):
                # TODO: Do not ignore comments.
                pass
            elif token.startswith("$"):
                # TODO: Do not ignore NAGs.
                pass
            elif token == "(":
                variation_stack.append(variation_stack[-1].previous_node)
            elif token == ")":
                variation_stack.pop()
            else:
                pos = variation_stack[-1].position
                try:
                    variation_stack[-1] = variation_stack[-1].add_variation(pos.get_move_from_san(token))
                except chess.MoveError, e:
                    raise chess.PgnError(e)

    @classmethod
    def open(cls, path):
        pgn_file = PgnFile()
        current_game = None
        in_tags = False

        for line in open(path, 'r'):
            # Decode and strip the line.
            line = line.decode('latin-1').strip()

            # Skip empty lines and comments.
            if not line or line.startswith("%"):
                continue

            # Check for tag lines.
            tag_match = tag_regex.match(line)
            if tag_match:
                tag_name = tag_match.group(1)
                tag_value = tag_match.group(2).replace("\\\\", "\\").replace("\\[", "]").replace("\\\"", "\"")
                if current_game:
                    if in_tags:
                        current_game.headers[tag_name] = tag_value
                    else:
                        cls.__parse_movetext(current_game, movetext)
                        pgn_file.add_game(current_game)
                        current_game = None
                if not current_game:
                    current_game = chess.Game()
                    current_game.headers[tag_name] = tag_value
                    movetext = ""
                in_tags = True
            # Parse movetext lines.
            else:
                if current_game:
                    movetext += "\n" + line
                    pass
                else:
                    raise chess.PgnError("Invalid PGN. Expected header before movetext: %s", repr(line))
                in_tags = False

        if current_game:
            cls.__parse_movetext(current_game, movetext)
            pgn_file.add_game(current_game)

        return pgn_file
