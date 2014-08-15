# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import chess
import collections
import copy
import itertools
import re


NAG_NULL = 0
NAG_GOOD_MOVE = 1
NAG_MISTAKE = 2
NAG_BRILLIANT_MOVE = 3
NAG_BLUNDER = 4
NAG_SPECULATIVE_MOVE = 5
NAG_DUBIOUS_MOVE = 6
NAG_FORCED_MOVE = 7
NAG_SINGULAR_MOVE = 8
NAG_WORST_MOVE = 9
NAG_DRAWISH_POSITION = 10
NAG_QUIET_POSITION = 11
NAG_ACTIVE_POSITION = 12
NAG_UNCLEAR_POSITION = 13
NAG_WHITE_SLIGHT_ADVANTAGE = 14
NAG_BLACK_SLIGHT_ADVANTAGE = 15

# TODO: Add more constants for example from
# https://en.wikipedia.org/wiki/Numeric_Annotation_Glyphs

NAG_WHITE_MODERATE_COUNTERPLAY = 132
NAG_BLACK_MODERATE_COUNTERPLAY = 133
NAG_WHITE_DECISIVE_COUNTERPLAY = 134
NAG_BLACK_DECISIVE_COUNTERPLAY = 135
NAG_WHITE_MODERATE_TIME_PRESSURE = 136
NAG_BLACK_MODERATE_TIME_PRESSURE = 137
NAG_WHITE_SEVERE_TIME_PRESSURE = 138
NAG_BLACK_SEVERE_TIME_PRESSURE = 139


TAG_REGEX = re.compile(r"\[([A-Za-z0-9]+)\s+\"(.*)\"\]")

MOVETEXT_REGEX = re.compile(r"""
    (%.*?[\n\r])
    |(\{.*)
    |(\$[0-9]+)
    |(\()
    |(\))
    |(\*|1-0|0-1|1/2-1/2)
    |(
        ([a-hKQRBN][a-hxKQRBN1-8+#=\-]{1,6}
        |--
        |O-O(?:\-O)?)
    )
    |([\?!]{1,2})
    """, re.DOTALL | re.VERBOSE)


class GameNode(object):

    def __init__(self):
        self.parent = None
        self.move = None
        self.nags = set()
        self.starting_comment = ""
        self.comment = ""
        self.variations = []

    def board(self):
        """
        Gets a bitboard with the position of the node.

        Its a copy, so modifying the board will not alter the game.
        """
        board = self.parent.board()
        board.push(self.move)
        return board

    def root(self):
        """Gets the root node, i.e. the game."""
        node = self

        while node.parent:
            node = node.parent

        return node

    def end(self):
        """Follows the main variation to the end and returns the last node."""
        node = self

        while node.variations:
            node = node.variations[0]

        return node

    def starts_variation(self):
        """
        Checks if this node starts a variation (and can thus have a starting
        comment). The beginning of the game is also the start of a variation.
        """
        if not self.parent or not self.parent.variations:
            return True

        return self.parent.variations[0] != self

    def is_main_line(self):
        """Checks if the node is in the main line of the game."""
        node = self

        while node.parent:
            parent = node.parent

            if not parent.variations or parent.variations[0] != node:
                return False

            node = parent

        return True

    def is_main_variation(self):
        """
        Checks if this node is the first variation from the point of view of its
        parent. The root node also is in the main variation.
        """
        if not self.parent:
            return True

        return not self.parent.variations or self.parent.variations[0] == self

    def variation(self, move):
        """
        Gets a child node by move or index.
        """
        for index, variation in enumerate(self.variations):
            if move == variation.move or move == index:
                return variation

        raise KeyError("variation not found")

    def has_variation(self, move):
        """Checks if the given move appears as a variation."""
        return move in (variation.move for variation in self.variations)

    def promote_to_main(self, move):
        """Promotes the given move to the main variation."""
        variation = self.variation(move)
        self.variations.remove(variation)
        self.variations.insert(0, variation)

    def promote(self, move):
        """Moves the given variation one up in the list of variations."""
        variation = self.variation(move)
        i = self.variations.index(variation)
        if i > 0:
            self.variations[i - 1], self.variations[i] = self.variations[i], self.variations[i - 1]

    def demote(self, move):
        """Moves the given variation one down in the list of variations."""
        variation = self.variation(move)
        i = self.variations.index(variation)
        if i < len(self.variations) - 1:
            self.variations[i + 1], self.variations[i] = self.variations[i], self.variations[i + 1]

    def remove_variation(self, move):
        """Removes a variation by move."""
        self.variations.remove(self.variation(move))

    def add_variation(self, move, comment="", starting_comment="", nags=set()):
        """Creates a child node with the given attributes."""
        node = GameNode()
        node.move = move
        node.nags = set(nags)
        node.parent = self
        node.comment = comment
        node.starting_comment = starting_comment
        self.variations.append(node)
        return node

    def add_main_variation(self, move, comment=""):
        """
        Creates a child node with the given attributes and promotes it to the
        main variation.
        """
        node = self.add_variation(move, comment=comment)
        self.promote_to_main(move)
        return node

    def export(self, exporter, comments=True, variations=True, _board=None):
        if _board is None:
            _board = self.board()

        for index, variation in enumerate(self.variations):
            # Open varation.
            if index != 0:
                exporter.start_variation()

            # Append starting comment.
            if comments and variation.starting_comment:
                exporter.put_starting_comment(variation.starting_comment)

            # Append fullmove number.
            exporter.put_fullmove_number(_board.turn, _board.fullmove_number, index != 0)

            # Append SAN.
            exporter.put_move(_board, variation.move)

            # Append NAGs.
            if comments:
                exporter.put_nags(variation.nags)

            # Append the comment.
            if comments and variation.comment:
                exporter.put_comment(variation.comment)

            # Recursively append the next moves.
            _board.push(variation.move)
            variation.export(exporter, comments, variations, _board)
            _board.pop()

            # End variation.
            if index != 0:
                exporter.end_variation()

            # All variations or just the main line.
            if not variations:
                break

    def __str__(self):
        exporter = StringExporter(columns=None)
        self.export(exporter)
        return exporter.__str__()


class Game(GameNode):
    """
    The root node of a game with extra information such as headers and the
    starting position.

    By default the following 7 headers are provided in an ordered dictionary:

    >>> game = chess.pgn.Game()
    >>> game.headers["Event"]
    '?'
    >>> game.headers["Site"]
    '?'
    >>> game.headers["Date"]
    '????.??.??'
    >>> game.headers["Round"]
    '?'
    >>> game.headers["White"]
    '?'
    >>> game.headers["Black"]
    '?'
    >>> game.headers["Result"]
    '*'

    Also has all the other properties and methods of `GameNode`.
    """

    def __init__(self):
        super(Game, self).__init__()

        self.headers = collections.OrderedDict()
        self.headers["Event"] = "?"
        self.headers["Site"] = "?"
        self.headers["Date"] = "????.??.??"
        self.headers["Round"] = "?"
        self.headers["White"] = "?"
        self.headers["Black"] = "?"
        self.headers["Result"] = "*"

    def board(self):
        """
        Gets the starting position of the game as a bitboard.

        Unless the `SetUp` and `FEN` header tags are set this is the default
        starting position.
        """
        if "FEN" in self.headers and "SetUp" in self.headers and self.headers["SetUp"] == "1":
            return chess.Bitboard(self.headers["FEN"])
        else:
            return chess.Bitboard()

    def setup(self, board):
        """
        Setup a specific starting position. This sets (or resets) the `SetUp`
        and `FEN` header tags.
        """
        try:
            fen = board.fen()
        except AttributeError:
            fen = chess.Bitboard(board).fen()

        if fen == chess.STARTING_FEN:
            del self.headers["SetUp"]
            del self.headers["FEN"]
        else:
            self.headers["SetUp"] = "1"
            self.headers["FEN"] = fen

    def export(self, exporter, headers=True, comments=True, variations=True):
        exporter.start_game()

        if headers:
            exporter.start_headers()
            for tagname, tagvalue in self.headers.items():
                exporter.put_header(tagname, tagvalue)
            exporter.end_headers()

        if comments and self.starting_comment:
            exporter.put_starting_comment(self.starting_comment)

        super(Game, self).export(exporter, comments=comments, variations=variations)

        exporter.put_result(self.headers["Result"])
        exporter.end_game()


class StringExporter(object):
    """
    Allows exporting a game as a string.

    The export method of `Game` also provides options to include or exclude
    headers, variations or comments. By default everything is included.

    >>> exporter = chess.pgn.StringExporter()
    >>> game.export(exporter, headers=True, variations=True, comments=True)
    >>> pgn_string = str(exporter)

    Only `columns` characters are written per line. If `columns` is `None` then
    the entire movetext will be on a single line. This does not affect header
    tags and comments.

    There will be no newlines at the end of the string.
    """

    def __init__(self, columns=80):
        self.lines = []
        self.columns = columns
        self.current_line = ""

    def flush_current_line(self):
        if self.current_line:
            self.lines.append(self.current_line.rstrip())
        self.current_line = ""

    def write_token(self, token):
        if self.columns is not None and self.columns - len(self.current_line) < len(token):
            self.flush_current_line()
        self.current_line += token

    def write_line(self, line=""):
        self.flush_current_line()
        self.lines.append(line.rstrip())

    def start_game(self):
        pass

    def end_game(self):
        self.write_line()

    def start_headers(self):
        pass

    def put_header(self, tagname, tagvalue):
        self.write_line("[{0} \"{1}\"]".format(tagname, tagvalue))

    def end_headers(self):
        self.write_line()

    def start_variation(self):
        self.write_token("( ")

    def end_variation(self):
        self.write_token(") ")

    def put_starting_comment(self, comment):
        self.put_comment(comment)

    def put_comment(self, comment):
        self.write_token("{ " + comment.replace("}", "").strip() + " } ")

    def put_nags(self, nags):
        for nag in sorted(nags):
            self.put_nag(nag)

    def put_nag(self, nag):
        self.write_token("$" + str(nag) + " ")

    def put_fullmove_number(self, turn, fullmove_number, variation_start):
        if turn == chess.WHITE:
            self.write_token(str(fullmove_number) + ". ")
        elif variation_start:
            self.write_token(str(fullmove_number) + "... ")

    def put_move(self, board, move):
        self.write_token(board.san(move) + " ")

    def put_result(self, result):
        self.write_token(result + " ")

    def __str__(self):
        if self.current_line:
            return "\n".join(itertools.chain(self.lines, [ self.current_line.rstrip() ] )).rstrip()
        else:
            return "\n".join(self.lines).rstrip()


class FileExporter(StringExporter):
    """
    Like a StringExporter, but games are written directly to a text file.

    There will always be a blank line after each game. Handling encodings is up
    to the caller.

    >>> new_pgn = open("new.pgn", "w")
    >>> exporter = chess.pgn.FileExporter(new_pgn)
    >>> game.export(exporter)
    """

    def __init__(self, handle, columns=80):
        super(FileExporter, self).__init__(columns=columns)
        self.handle = handle

    def flush_current_line(self):
        if self.current_line:
            self.handle.write(self.current_line.rstrip())
            self.handle.write("\n")
        self.current_line = ""

    def write_line(self, line=""):
        self.flush_current_line()
        self.handle.write(line.rstrip())
        self.handle.write("\n")


def read_game(handle):
    """
    Reads a game from a file opened in text mode.

    By using text mode the parser does not need to handle encodings. It is the
    callers responsibility to open the file with the correct encoding.
    According to the specification PGN files should be ASCII. Also UTF-8 is
    common. So this is usually not a problem.

    >>> pgn = open("data/games/kasparov-deep-blue-1997.pgn")
    >>> first_game = chess.pgn.read_game(pgn)
    >>> second_game = chess.pgn.read_game(pgn)
    >>>
    >>> first_game.headers["Event"]
    'IBM Man-Machine, New York USA'

    Use `StringIO` to parse games from a string.

    >>> pgn_string = "1. e4 e5 2. Nf3 *"
    >>>
    >>> try:
    >>>     from StringIO import StringIO # Python 2
    >>> except ImportError:
    >>>     from io import StringIO # Python 3
    >>>
    >>> pgn = StringIO(pgn_string)
    >>> game = chess.pgn.read_game(pgn)

    The end of a game is determined by a completely blank line or the end of
    the file. (Of course blank lines in comments are possible.)

    According to the standard at least the usual 7 header tags are required
    for a valid game. This parser also handles games without any headers just
    fine.

    Raises `ValueError` if invalid moves are encountered in the movetext.

    Returns the parsed game or `None` if the EOF is reached.
    """
    game = Game()
    found_game = False

    line = handle.readline()

    # Parse game headers.
    while line:
        # Skip empty lines and comments.
        if not line.strip() or line.strip().startswith("%"):
            line = handle.readline()
            continue

        found_game = True

        # Read header tags.
        tag_match = TAG_REGEX.match(line)
        if tag_match:
            game.headers[tag_match.group(1)] = tag_match.group(2)
        else:
            break

        line = handle.readline()

    # Get the next non-empty line.
    while not line.strip() and line:
        line = handle.readline()

    # Movetext parser state.
    start_comment = ""
    variation_stack = collections.deque([ game ])
    board_stack = collections.deque([ game.board() ])
    in_variation = False

    # Parse movetext.
    while line:
        read_next_line = True

        # An empty line is the end of a game.
        if not line.strip() and found_game:
            return game

        for match in MOVETEXT_REGEX.finditer(line):
            token = match.group(0)

            if token.startswith("%"):
                # Ignore the rest of the line.
                line = handle.readline()
                continue

            found_game = True

            if token.startswith("{"):
                # Consume until the end of the comment.
                line = token[1:]
                comment_lines = [ ]
                while line and "}" not in line:
                    comment_lines.append(line.rstrip())
                    line = handle.readline()
                end_index = line.find("}")
                comment_lines.append(line[:end_index])
                if "}" in line:
                    line = line[end_index:]
                else:
                    line = ""

                # Add the comment.
                if in_variation:
                    variation_stack[-1].comment = "\n".join(comment_lines).strip()
                elif len(variation_stack) == 1:
                    variation_stack[0].start_comment = "\n".join(comment_lines).strip()
                else:
                    start_comment += "\n".join(comment_lines)

                # Continue with the current or the next line.
                if line:
                    read_next_line = False
                break
            elif token.startswith("$"):
                # Found a NAG.
                variation_stack[-1].nags.add(int(token[1:]))
            elif token == "?":
                variation_stack[-1].nags.add(NAG_MISTAKE)
            elif token == "??":
                variation_stack[-1].nags.add(NAG_BLUNDER)
            elif token == "!":
                variation_stack[-1].nags.add(NAG_GOOD_MOVE)
            elif token == "!!":
                variation_stack[-1].nags.add(NAG_BRILLIANT_MOVE)
            elif token == "!?":
                variation_stack[-1].nags.add(NAG_SPECULATIVE_MOVE)
            elif token == "?!":
                variation_stack[-1].nags.add(NAG_DUBIOUS_MOVE)
            elif token == "(":
                # Found a start variation token.
                variation_stack.append(variation_stack[-1].parent)

                board = copy.deepcopy(board_stack[-1])
                board.pop()
                board_stack.append(board)

                in_variation = False
            elif token == ")":
                # Found a close variation token.
                variation_stack.pop()
                board_stack.pop()
            elif token in ["1-0", "0-1", "1/2-1/2", "*"] and len(variation_stack) == 1:
                # Found a result token.
                if "Result" not in game.headers:
                    game.headers["Result"] = token
            else:
                # Found a SAN token.
                in_variation = True
                board = board_stack[-1]
                variation_stack[-1] = variation_stack[-1].add_variation(board.parse_san(token))
                variation_stack[-1].start_comment = start_comment.strip()
                board_stack[-1].push(variation_stack[-1].move)
                start_comment = ""

        if read_next_line:
            line = handle.readline()

    if found_game:
        return game


def scan_offsets(handle):
    """
    Scan a PGN file opened in text mode.

    Yields the starting offsets of all the games, so that they can be seeked
    later. Since actually parsing many games from a big file is relatively
    expensive, this is a better way to read only a specific game.

    >>> pgn = open("mega.pgn")
    >>> offsets = chess.pgn.scan_offsets(pgn)
    >>> first_game_offset = next(offsets)
    >>> second_game_offset = next(offsets)
    >>> pgn.seek(second_game_offset)
    >>> second_game = chess.pgn.read_game(pgn)

    The PGN standard requires each game to start with an Event-tag. So does this
    scanner.
    """
    in_comment = False

    last_pos = handle.tell()
    line = handle.readline()

    while line:
        if not in_comment and line.startswith("[Event \""):
            yield last_pos
        elif (not in_comment and "{" in line) or (in_comment and "}" in line):
            if line.rfind("{") < line.rfind("}"):
                in_comment = False
            else:
                in_comment = True

        last_pos = handle.tell()
        line = handle.readline()
