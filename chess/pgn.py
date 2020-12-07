# This file is part of the python-chess library.
# Copyright (C) 2012-2020 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

from __future__ import annotations

import abc
import enum
import itertools
import logging
import re
import typing

import chess
import chess.engine
import chess.svg

from typing import Any, Callable, Dict, Generic, Iterable, Iterator, List, Mapping, MutableMapping, Set, TextIO, Tuple, Type, TypeVar, Optional, Union
from chess import Color, Square

try:
    from typing import Literal
    _TrueLiteral = Literal[True]
except ImportError:
    # Before Python 3.8.
    _TrueLiteral = bool  # type: ignore


LOGGER = logging.getLogger(__name__)


# Reference of Numeric Annotation Glyphs (NAGs):
# https://en.wikipedia.org/wiki/Numeric_Annotation_Glyphs

NAG_NULL = 0

NAG_GOOD_MOVE = 1
"""A good move. Can also be indicated by ``!`` in PGN notation."""

NAG_MISTAKE = 2
"""A mistake. Can also be indicated by ``?`` in PGN notation."""

NAG_BRILLIANT_MOVE = 3
"""A brilliant move. Can also be indicated by ``!!`` in PGN notation."""

NAG_BLUNDER = 4
"""A blunder. Can also be indicated by ``??`` in PGN notation."""

NAG_SPECULATIVE_MOVE = 5
"""A speculative move. Can also be indicated by ``!?`` in PGN notation."""

NAG_DUBIOUS_MOVE = 6
"""A dubious move. Can also be indicated by ``?!`` in PGN notation."""

NAG_FORCED_MOVE = 7
NAG_SINGULAR_MOVE = 8
NAG_WORST_MOVE = 9
NAG_DRAWISH_POSITION = 10
NAG_QUIET_POSITION = 11
NAG_ACTIVE_POSITION = 12
NAG_UNCLEAR_POSITION = 13
NAG_WHITE_SLIGHT_ADVANTAGE = 14
NAG_BLACK_SLIGHT_ADVANTAGE = 15
NAG_WHITE_MODERATE_ADVANTAGE = 16
NAG_BLACK_MODERATE_ADVANTAGE = 17
NAG_WHITE_DECISIVE_ADVANTAGE = 18
NAG_BLACK_DECISIVE_ADVANTAGE = 19

NAG_WHITE_ZUGZWANG = 22
NAG_BLACK_ZUGZWANG = 23

NAG_WHITE_MODERATE_COUNTERPLAY = 132
NAG_BLACK_MODERATE_COUNTERPLAY = 133
NAG_WHITE_DECISIVE_COUNTERPLAY = 134
NAG_BLACK_DECISIVE_COUNTERPLAY = 135
NAG_WHITE_MODERATE_TIME_PRESSURE = 136
NAG_BLACK_MODERATE_TIME_PRESSURE = 137
NAG_WHITE_SEVERE_TIME_PRESSURE = 138
NAG_BLACK_SEVERE_TIME_PRESSURE = 139

NAG_NOVELTY = 146


TAG_REGEX = re.compile(r"^\[([A-Za-z0-9_]+)\s+\"([^\r]*)\"\]\s*$")

TAG_NAME_REGEX = re.compile(r"^[A-Za-z0-9_]+\Z")

MOVETEXT_REGEX = re.compile(r"""
    (
        [NBKRQ]?[a-h]?[1-8]?[\-x]?[a-h][1-8](?:=?[nbrqkNBRQK])?
        |[PNBRQK]?@[a-h][1-8]
        |--
        |Z0
        |0000
        |@@@@
        |O-O(?:-O)?
        |0-0(?:-0)?
    )
    |(\{.*)
    |(;.*)
    |(\$[0-9]+)
    |(\()
    |(\))
    |(\*|1-0|0-1|1/2-1/2)
    |([\?!]{1,2})
    """, re.DOTALL | re.VERBOSE)

SKIP_MOVETEXT_REGEX = re.compile(r""";|\{|\}""")


CLOCK_REGEX = re.compile(r"""\[%clk\s(\d+):(\d+):(\d+)\]""")

EVAL_REGEX = re.compile(r"""
    \[%eval\s(?:
        \#([+-]?\d+)
        |([+-]?(?:\d{0,10}\.\d{1,2}|\d{1,10}\.?))
    )\]
    """, re.VERBOSE)

ARROWS_REGEX = re.compile(r"""
    \[%(?:csl|cal)\s(
        [RGYB][a-h][1-8](?:[a-h][1-8])?
        (?:,[RGYB][a-h][1-8](?:[a-h][1-8])?)*
    )\]
    """, re.VERBOSE)


TAG_ROSTER = ["Event", "Site", "Date", "Round", "White", "Black", "Result"]


class SkipType(enum.Enum):
    SKIP = None

SKIP = SkipType.SKIP


ResultT = TypeVar("ResultT", covariant=True)


class _AcceptFrame:
    def __init__(self, node: ChildNode, *, is_variation: bool = False, sidelines: bool = True):
        self.state = "pre"
        self.node = node
        self.is_variation = is_variation
        self.variations = iter(itertools.islice(node.parent.variations, 1, None) if sidelines else [])
        self.in_variation = False


class GameNode(abc.ABC):
    parent: Optional[GameNode]
    """The parent node or ``None`` if this is the root node of the game."""

    move: Optional[chess.Move]
    """
    The move leading to this node or ``None`` if this is the root node of the
    game.
    """

    variations: List[ChildNode]
    """A list of child nodes."""

    comment: str
    """
    A comment that goes behind the move leading to this node. Comments
    that occur before any moves are assigned to the root node.
    """

    starting_comment: str
    nags: Set[int]

    def __init__(self, *, comment: str = "") -> None:
        self.parent = None
        self.move = None
        self.variations = []
        self.comment = comment

        # Deprecated: These should be properties of ChildNode, but need to
        # remain here for backwards compatibility.
        self.starting_comment = ""
        self.nags = set()

    @abc.abstractmethod
    def board(self) -> chess.Board:
        """
        Gets a board with the position of the node.

        For the root node, this is the default starting position (for the
        ``Variant``) unless the ``FEN`` header tag is set.

        It's a copy, so modifying the board will not alter the game.
        """

    @abc.abstractmethod
    def ply(self) -> int:
        """
        Returns the number of half-moves up to this node, as indicated by
        fullmove number and turn of the position.
        See :func:`chess.Board.ply()`.

        Usually this is equal to the number of parent nodes, but it may be
        more if the game was started from a custom position.
        """

    def turn(self) -> Color:
        """
        Gets the color to move at this node. See :data:`chess.Board.turn`.
        """
        return self.ply() % 2 == 0

    def root(self) -> GameNode:
        node = self
        while node.parent:
            node = node.parent
        return node

    def game(self) -> Game:
        """Gets the root node, i.e., the game."""
        root = self.root()
        assert isinstance(root, Game), "GameNode not rooted in Game"
        return root

    def end(self) -> GameNode:
        """Follows the main variation to the end and returns the last node."""
        node = self

        while node.variations:
            node = node.variations[0]

        return node

    def is_end(self) -> bool:
        """Checks if this node is the last node in the current variation."""
        return not self.variations

    def starts_variation(self) -> bool:
        """
        Checks if this node starts a variation (and can thus have a starting
        comment). The root node does not start a variation and can have no
        starting comment.

        For example, in ``1. e4 e5 (1... c5 2. Nf3) 2. Nf3``, the node holding
        1... c5 starts a variation.
        """
        if not self.parent or not self.parent.variations:
            return False

        return self.parent.variations[0] != self

    def is_mainline(self) -> bool:
        """Checks if the node is in the mainline of the game."""
        node = self

        while node.parent:
            parent = node.parent

            if not parent.variations or parent.variations[0] != node:
                return False

            node = parent

        return True

    def is_main_variation(self) -> bool:
        """
        Checks if this node is the first variation from the point of view of its
        parent. The root node is also in the main variation.
        """
        if not self.parent:
            return True

        return not self.parent.variations or self.parent.variations[0] == self

    def __getitem__(self, move: Union[int, chess.Move, GameNode]) -> ChildNode:
        try:
            return self.variations[move]  # type: ignore
        except TypeError:
            for variation in self.variations:
                if variation.move == move or variation == move:
                    return variation

        raise KeyError(move)

    def __contains__(self, move: Union[int, chess.Move, GameNode]) -> bool:
        try:
            self[move]
        except KeyError:
            return False
        else:
            return True

    def variation(self, move: Union[int, chess.Move, GameNode]) -> ChildNode:
        """
        Gets a child node by either the move or the variation index.
        """
        return self[move]

    def has_variation(self, move: Union[int, chess.Move, GameNode]) -> bool:
        """Checks if this node has the given variation."""
        return move in self

    def promote_to_main(self, move: Union[int, chess.Move, GameNode]) -> None:
        """Promotes the given *move* to the main variation."""
        variation = self[move]
        self.variations.remove(variation)
        self.variations.insert(0, variation)

    def promote(self, move: Union[int, chess.Move, GameNode]) -> None:
        """Moves a variation one up in the list of variations."""
        variation = self[move]
        i = self.variations.index(variation)
        if i > 0:
            self.variations[i - 1], self.variations[i] = self.variations[i], self.variations[i - 1]

    def demote(self, move: Union[int, chess.Move, GameNode]) -> None:
        """Moves a variation one down in the list of variations."""
        variation = self[move]
        i = self.variations.index(variation)
        if i < len(self.variations) - 1:
            self.variations[i + 1], self.variations[i] = self.variations[i], self.variations[i + 1]

    def remove_variation(self, move: Union[int, chess.Move, GameNode]) -> None:
        """Removes a variation."""
        self.variations.remove(self.variation(move))

    def add_variation(self, move: chess.Move, *, comment: str = "", starting_comment: str = "", nags: Iterable[int] = []) -> ChildNode:
        """Creates a child node with the given attributes."""
        # Instanciate ChildNode only in this method.
        return ChildNode(self, move, comment=comment, starting_comment=starting_comment, nags=nags)

    def add_main_variation(self, move: chess.Move, *, comment: str = "", nags: Iterable[int] = []) -> ChildNode:
        """
        Creates a child node with the given attributes and promotes it to the
        main variation.
        """
        node = self.add_variation(move, comment=comment, nags=nags)
        self.variations.insert(0, self.variations.pop())
        return node

    def next(self) -> Optional[ChildNode]:
        """
        Returns the first node of the mainline after this node, or ``None`` if
        this node does not have any children.
        """
        return self.variations[0] if self.variations else None

    def mainline(self) -> Mainline[ChildNode]:
        """Returns an iterable over the mainline starting after this node."""
        return Mainline(self, lambda node: node)

    def mainline_moves(self) -> Mainline[chess.Move]:
        """Returns an iterable over the main moves after this node."""
        return Mainline(self, lambda node: node.move)

    def add_line(self, moves: Iterable[chess.Move], *, comment: str = "", starting_comment: str = "", nags: Iterable[int] = []) -> GameNode:
        """
        Creates a sequence of child nodes for the given list of moves.
        Adds *comment* and *nags* to the last node of the line and returns it.
        """
        node = self

        # Add line.
        for move in moves:
            node = node.add_variation(move, starting_comment=starting_comment)
            starting_comment = ""

        # Merge comment and NAGs.
        if node.comment:
            node.comment += " " + comment
        else:
            node.comment = comment

        node.nags.update(nags)

        return node

    def eval(self) -> Optional[chess.engine.PovScore]:
        """
        Parses the first valid ``[%eval ...]`` annotation in the comment of
        this node, if any.
        """
        match = EVAL_REGEX.search(self.comment)
        if not match:
            return None

        turn = self.turn()

        if match.group(1):
            mate = int(match.group(1))
            score: chess.engine.Score = chess.engine.Mate(mate)
            if mate == 0:
                # Resolve this ambiguity in the specification in favor of
                # standard chess: The player to move after mate is the player
                # who has been mated.
                return chess.engine.PovScore(score, turn)
        else:
            score = chess.engine.Cp(int(float(match.group(2)) * 100))

        return chess.engine.PovScore(score if turn else -score, turn)

    def set_eval(self, score: Optional[chess.engine.PovScore]) -> None:
        """
        Replaces the first valid ``[%eval ...]`` annotation in the comment of
        this node or adds a new one.
        """
        eval = ""
        if score is not None:
            cp = score.white().score()
            if cp is not None:
                eval = f"[%eval {float(cp) / 100:.2f}]"
            elif score.white().mate():
                eval = f"[%eval #{score.white().mate()}]"

        self.comment, found = EVAL_REGEX.subn(eval, self.comment, count=1)

        if not found and eval:
            if self.comment and not self.comment.endswith(" "):
                self.comment += " "
            self.comment += eval

    def arrows(self) -> List[chess.svg.Arrow]:
        """
        Parses all ``[%csl ...]`` and ``[%cal ...]`` annotations in the comment
        of this node.

        Returns a list of :class:`arrows <chess.svg.Arrow>`.
        """
        arrows = []
        for match in ARROWS_REGEX.finditer(self.comment):
            for group in match.group(1).split(","):
                arrows.append(chess.svg.Arrow.from_pgn(group))

        return arrows

    def set_arrows(self, arrows: Iterable[Union[chess.svg.Arrow, Tuple[Square, Square]]]) -> None:
        """
        Replaces all valid ``[%csl ...]`` and ``[%cal ...]`` annotations in
        the comment of this node or adds new ones.
        """
        csl: List[str] = []
        cal: List[str] = []

        for arrow in arrows:
            try:
                tail, head = arrow  # type: ignore
                arrow = chess.svg.Arrow(tail, head)
            except TypeError:
                pass
            (csl if arrow.tail == arrow.head else cal).append(arrow.pgn())  # type: ignore

        self.comment = ARROWS_REGEX.sub("", self.comment).strip()

        prefix = ""
        if csl:
            prefix += f"[%csl {','.join(csl)}]"
        if cal:
            prefix += f"[%cal {','.join(cal)}]"

        if prefix:
            self.comment = prefix + " " + self.comment if self.comment else prefix

    def clock(self) -> Optional[float]:
        """
        Parses the first valid ``[%clk ...]`` annotation in the comment of
        this node, if any.

        Returns the player's remaining time to the next time control after this
        move, in seconds.
        """
        match = CLOCK_REGEX.search(self.comment)
        if match is None:
            return None
        return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))

    def set_clock(self, seconds: Optional[float]) -> None:
        """
        Replaces the first valid ``[%clk ...]`` annotation in the comment of
        this node or adds a new one.
        """
        clk = ""
        if seconds is not None:
            seconds = max(0, round(seconds))
            hours = seconds // 3600
            minutes = seconds % 3600 // 60
            seconds = seconds % 3600 % 60
            clk = f"[%clk {hours:d}:{minutes:02d}:{seconds:02d}]"

        self.comment, found = CLOCK_REGEX.subn(clk, self.comment, count=1)

        if not found and clk:
            if self.comment and not self.comment.endswith(" "):
                self.comment += " "
            self.comment += clk

    @abc.abstractmethod
    def accept(self, visitor: BaseVisitor[ResultT]) -> ResultT:
        """
        Traverses game nodes in PGN order using the given *visitor*. Starts with
        the move leading to this node. Returns the *visitor* result.
        """

    def accept_subgame(self, visitor: BaseVisitor[ResultT]) -> ResultT:
        """
        Traverses headers and game nodes in PGN order, as if the game was
        starting after this node. Returns the *visitor* result.
        """
        if visitor.begin_game() is not SKIP:
            game = self.game()
            board = self.board()

            dummy_game = Game.without_tag_roster()
            dummy_game.setup(board)

            visitor.begin_headers()

            for tagname, tagvalue in game.headers.items():
                if tagname not in dummy_game.headers:
                    visitor.visit_header(tagname, tagvalue)
            for tagname, tagvalue in dummy_game.headers.items():
                visitor.visit_header(tagname, tagvalue)

            if visitor.end_headers() is not SKIP:
                visitor.visit_board(board)

                if self.variations:
                    self.variations[0]._accept(board, visitor)

                visitor.visit_result(game.headers.get("Result", "*"))

        visitor.end_game()
        return visitor.result()

    def __str__(self) -> str:
        return self.accept(StringExporter(columns=None))


class ChildNode(GameNode):
    """
    A child node of a game, with the move leading to it.
    Extends :class:`~chess.pgn.GameNode`.
    """

    parent: GameNode
    """The parent node."""

    move: chess.Move
    """The move leading to this node."""

    starting_comment: str
    """
    A comment for the start of a variation. Only nodes that
    actually start a variation (:func:`~chess.pgn.GameNode.starts_variation()`
    checks this) can have a starting comment. The root node can not have
    a starting comment.
    """

    nags: Set[int]
    """
    A set of NAGs as integers. NAGs always go behind a move, so the root
    node of the game will never have NAGs.
    """

    def __init__(self, parent: GameNode, move: chess.Move, *, comment: str = "", starting_comment: str = "", nags: Iterable[int] = []) -> None:
        super().__init__(comment=comment)
        self.parent = parent
        self.move = move
        self.parent.variations.append(self)

        self.nags.update(nags)
        self.starting_comment = starting_comment

    def board(self) -> chess.Board:
        stack: List[chess.Move] = []
        node: GameNode = self

        while node.move is not None and node.parent is not None:
            stack.append(node.move)
            node = node.parent

        board = node.game().board()

        while stack:
            board.push(stack.pop())

        return board

    def ply(self) -> int:
        ply = 0
        node: GameNode = self
        while node.parent is not None:
            ply += 1
            node = node.parent
        return node.game().ply() + ply

    def san(self) -> str:
        """
        Gets the standard algebraic notation of the move leading to this node.
        See :func:`chess.Board.san()`.

        Do not call this on the root node.
        """
        return self.parent.board().san(self.move)

    def uci(self, *, chess960: Optional[bool] = None) -> str:
        """
        Gets the UCI notation of the move leading to this node.
        See :func:`chess.Board.uci()`.

        Do not call this on the root node.
        """
        return self.parent.board().uci(self.move, chess960=chess960)

    def end(self) -> ChildNode:
        """Follows the main variation to the end and returns the last node."""
        return typing.cast(ChildNode, super().end())

    def _accept_node(self, parent_board: chess.Board, visitor: BaseVisitor[ResultT]) -> None:
        if self.starting_comment:
            visitor.visit_comment(self.starting_comment)

        visitor.visit_move(parent_board, self.move)

        parent_board.push(self.move)
        visitor.visit_board(parent_board)
        parent_board.pop()

        for nag in sorted(self.nags):
            visitor.visit_nag(nag)

        if self.comment:
            visitor.visit_comment(self.comment)

    def _accept(self, parent_board: chess.Board, visitor: BaseVisitor[ResultT], *, sidelines: bool = True) -> None:
        stack = [_AcceptFrame(self, sidelines=sidelines)]

        while stack:
            top = stack[-1]

            if top.in_variation:
                top.in_variation = False
                visitor.end_variation()

            if top.state == "pre":
                top.node._accept_node(parent_board, visitor)
                top.state = "variations"
            elif top.state == "variations":
                try:
                    variation = next(top.variations)
                except StopIteration:
                    if top.node.variations:
                        parent_board.push(top.node.move)
                        stack.append(_AcceptFrame(top.node.variations[0], sidelines=True))
                        top.state = "post"
                    else:
                        top.state = "end"
                else:
                    if visitor.begin_variation() is not SKIP:
                        stack.append(_AcceptFrame(variation, sidelines=False, is_variation=True))
                    top.in_variation = True
            elif top.state == "post":
                parent_board.pop()
                top.state = "end"
            else:
                stack.pop()

    def accept(self, visitor: BaseVisitor[ResultT]) -> ResultT:
        self._accept(self.parent.board(), visitor, sidelines=False)
        return visitor.result()

    def __repr__(self) -> str:
        try:
            parent_board = self.parent.board()
        except ValueError:
            return f"<{type(self).__name__} at {id(self):#x} (dangling: {self.move})>"
        else:
            return "<{} at {:#x} ({}{} {} ...)>".format(
                type(self).__name__,
                id(self),
                parent_board.fullmove_number,
                "." if parent_board.turn == chess.WHITE else "...",
                parent_board.san(self.move))


GameT = TypeVar("GameT", bound="Game")

class Game(GameNode):
    """
    The root node of a game with extra information such as headers and the
    starting position. Extends :class:`~chess.pgn.GameNode`.
    """

    headers: Headers
    """
    A mapping of headers. By default, the following 7 headers are provided
    (Seven Tag Roster):

    >>> import chess.pgn
    >>>
    >>> game = chess.pgn.Game()
    >>> game.headers
    Headers(Event='?', Site='?', Date='????.??.??', Round='?', White='?', Black='?', Result='*')
    """

    errors: List[Exception]
    """
    A list of errors (such as illegal or ambiguous moves) encountered while
    parsing the game.
    """

    def __init__(self, headers: Optional[Union[Mapping[str, str], Iterable[Tuple[str, str]]]] = None) -> None:
        super().__init__()
        self.headers = Headers(headers)
        self.errors = []

    def board(self) -> chess.Board:
        return self.headers.board()

    def ply(self) -> int:
        # Optimization: Parse FEN only for custom starting positions.
        return self.board().ply() if "FEN" in self.headers else 0

    def setup(self, board: Union[chess.Board, str]) -> None:
        """
        Sets up a specific starting position. This sets (or resets) the
        ``FEN``, ``SetUp``, and ``Variant`` header tags.
        """
        try:
            fen = board.fen()  # type: ignore
            setup = typing.cast(chess.Board, board)
        except AttributeError:
            setup = chess.Board(board)  # type: ignore
            setup.chess960 = setup.has_chess960_castling_rights()
            fen = setup.fen()

        if fen == type(setup).starting_fen:
            self.headers.pop("SetUp", None)
            self.headers.pop("FEN", None)
        else:
            self.headers["SetUp"] = "1"
            self.headers["FEN"] = fen

        if type(setup).aliases[0] == "Standard" and setup.chess960:
            self.headers["Variant"] = "Chess960"
        elif type(setup).aliases[0] != "Standard":
            self.headers["Variant"] = type(setup).aliases[0]
            self.headers["FEN"] = fen
        else:
            self.headers.pop("Variant", None)

    def accept(self, visitor: BaseVisitor[ResultT]) -> ResultT:
        """
        Traverses the game in PGN order using the given *visitor*. Returns
        the *visitor* result.
        """
        if visitor.begin_game() is not SKIP:
            for tagname, tagvalue in self.headers.items():
                visitor.visit_header(tagname, tagvalue)
            if visitor.end_headers() is not SKIP:
                board = self.board()
                visitor.visit_board(board)

                if self.comment:
                    visitor.visit_comment(self.comment)

                if self.variations:
                    self.variations[0]._accept(board, visitor)

                visitor.visit_result(self.headers.get("Result", "*"))

        visitor.end_game()
        return visitor.result()

    @classmethod
    def from_board(cls: Type[GameT], board: chess.Board) -> GameT:
        """Creates a game from the move stack of a :class:`~chess.Board()`."""
        # Setup the initial position.
        game = cls()
        game.setup(board.root())
        node: GameNode = game

        # Replay all moves.
        for move in board.move_stack:
            node = node.add_variation(move)

        game.headers["Result"] = board.result()
        return game

    @classmethod
    def without_tag_roster(cls: Type[GameT]) -> GameT:
        """Creates an empty game without the default Seven Tag Roster."""
        return cls(headers={})

    @classmethod
    def builder(cls: Type[GameT]) -> GameBuilder[GameT]:
        return GameBuilder(Game=cls)

    def __repr__(self) -> str:
        return "<{} at {:#x} ({!r} vs. {!r}, {!r}{})>".format(
            type(self).__name__,
            id(self),
            self.headers.get("White", "?"),
            self.headers.get("Black", "?"),
            self.headers.get("Date", "????.??.??"),
            f", {len(self.errors)} errors" if self.errors else "")


HeadersT = TypeVar("HeadersT", bound="Headers")

class Headers(MutableMapping[str, str]):
    def __init__(self, data: Optional[Union[Mapping[str, str], Iterable[Tuple[str, str]]]] = None, **kwargs: str) -> None:
        self._tag_roster: Dict[str, str] = {}
        self._others: Dict[str, str] = {}

        if data is None:
            data = {
                "Event": "?",
                "Site": "?",
                "Date": "????.??.??",
                "Round": "?",
                "White": "?",
                "Black": "?",
                "Result": "*"
            }

        self.update(data, **kwargs)

    def is_chess960(self) -> bool:
        return self.get("Variant", "").lower() in [
            "chess960",
            "chess 960",
            "fischerandom",  # Cute Chess
            "fischerrandom",
            "fischer random",
        ]

    def is_wild(self) -> bool:
        # http://www.freechess.org/Help/HelpFiles/wild.html
        return self.get("Variant", "").lower() in [
            "wild/0", "wild/1", "wild/2", "wild/3", "wild/4", "wild/5",
            "wild/6", "wild/7", "wild/8", "wild/8a"]

    def variant(self) -> Type[chess.Board]:
        if "Variant" not in self or self.is_chess960() or self.is_wild():
            return chess.Board
        else:
            from chess.variant import find_variant
            return find_variant(self["Variant"])

    def board(self) -> chess.Board:
        VariantBoard = self.variant()
        fen = self.get("FEN", VariantBoard.starting_fen)
        board = VariantBoard(fen, chess960=self.is_chess960())
        board.chess960 = board.chess960 or board.has_chess960_castling_rights()
        return board

    def __setitem__(self, key: str, value: str) -> None:
        if key in TAG_ROSTER:
            self._tag_roster[key] = value
        elif not TAG_NAME_REGEX.match(key):
            raise ValueError(f"non-alphanumeric pgn header tag: {key!r}")
        elif "\n" in value or "\r" in value:
            raise ValueError(f"line break in pgn header {key}: {value!r}")
        else:
            self._others[key] = value

    def __getitem__(self, key: str) -> str:
        if key in TAG_ROSTER:
            return self._tag_roster[key]
        else:
            return self._others[key]

    def __delitem__(self, key: str) -> None:
        if key in TAG_ROSTER:
            del self._tag_roster[key]
        else:
            del self._others[key]

    def __iter__(self) -> Iterator[str]:
        for key in TAG_ROSTER:
            if key in self._tag_roster:
                yield key

        yield from sorted(self._others)

    def __len__(self) -> int:
        return len(self._tag_roster) + len(self._others)

    def copy(self: HeadersT) -> HeadersT:
        return type(self)(self)

    def __copy__(self: HeadersT) -> HeadersT:
        return self.copy()

    def __repr__(self) -> str:
        return "{}({})".format(
            type(self).__name__,
            ", ".join("{}={!r}".format(key, value) for key, value in self.items()))

    @classmethod
    def builder(cls: Type[HeadersT]) -> HeadersBuilder[HeadersT]:
        return HeadersBuilder(Headers=cls)


MainlineMapT = TypeVar("MainlineMapT")

class Mainline(Generic[MainlineMapT]):
    def __init__(self, start: GameNode, f: Callable[[ChildNode], MainlineMapT]) -> None:
        self.start = start
        self.f = f

    def __bool__(self) -> bool:
        return bool(self.start.variations)

    def __iter__(self) -> Iterator[MainlineMapT]:
        node = self.start
        while node.variations:
            node = node.variations[0]
            yield self.f(node)

    def __reversed__(self) -> ReverseMainline[MainlineMapT]:
        return ReverseMainline(self.start, self.f)

    def accept(self, visitor: BaseVisitor[ResultT]) -> ResultT:
        node = self.start
        board = self.start.board()
        while node.variations:
            node = node.variations[0]
            node._accept_node(board, visitor)
            board.push(node.move)
        return visitor.result()

    def __str__(self) -> str:
        return self.accept(StringExporter(columns=None))

    def __repr__(self) -> str:
        return f"<Mainline at {id(self):#x} ({self.accept(StringExporter(columns=None, comments=False))})>"


class ReverseMainline(Generic[MainlineMapT]):
    def __init__(self, stop: GameNode, f: Callable[[ChildNode], MainlineMapT]) -> None:
        self.stop = stop
        self.f = f

        self.length = 0
        node = stop
        while node.variations:
            node = node.variations[0]
            self.length += 1
        self.end = node

    def __len__(self) -> int:
        return self.length

    def __iter__(self) -> Iterator[MainlineMapT]:
        node = self.end
        while node.parent and node != self.stop:
            yield self.f(typing.cast(ChildNode, node))
            node = node.parent

    def __reversed__(self) -> Mainline[MainlineMapT]:
        return Mainline(self.stop, self.f)

    def __repr__(self) -> str:
        return "<ReverseMainline at {:#x} ({})>".format(
            id(self),
            " ".join(ReverseMainline(self.stop, lambda node: node.move.uci())))


class BaseVisitor(abc.ABC, Generic[ResultT]):
    """
    Base class for visitors.

    Use with :func:`chess.pgn.Game.accept()` or
    :func:`chess.pgn.GameNode.accept()` or :func:`chess.pgn.read_game()`.

    The methods are called in PGN order.
    """

    def begin_game(self) -> Optional[SkipType]:
        """Called at the start of a game."""
        pass

    def begin_headers(self) -> Optional[Headers]:
        """Called before visiting game headers."""
        pass

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        """Called for each game header."""
        pass

    def end_headers(self) -> Optional[SkipType]:
        """Called after visiting game headers."""
        pass

    def parse_san(self, board: chess.Board, san: str) -> chess.Move:
        """
        When the visitor is used by a parser, this is called to parse a move
        in standard algebraic notation.

        You can override the default implementation to work around specific
        quirks of your input format.

        .. deprecated:: 1.1
            This method is very limited, because it is only called on moves
            that the parser recognizes in the first place. Instead of adding
            workarounds here, please report common quirks so that
            they can be handled for everyone.
        """
        return board.parse_san(san)

    def visit_move(self, board: chess.Board, move: chess.Move) -> None:
        """
        Called for each move.

        *board* is the board state before the move. The board state must be
        restored before the traversal continues.
        """
        pass

    def visit_board(self, board: chess.Board) -> None:
        """
        Called for the starting position of the game and after each move.

        The board state must be restored before the traversal continues.
        """
        pass

    def visit_comment(self, comment: str) -> None:
        """Called for each comment."""
        pass

    def visit_nag(self, nag: int) -> None:
        """Called for each NAG."""
        pass

    def begin_variation(self) -> Optional[SkipType]:
        """
        Called at the start of a new variation. It is not called for the
        mainline of the game.
        """
        pass

    def end_variation(self) -> None:
        """Concludes a variation."""
        pass

    def visit_result(self, result: str) -> None:
        """
        Called at the end of a game with the value from the ``Result`` header.
        """
        pass

    def end_game(self) -> None:
        """Called at the end of a game."""
        pass

    @abc.abstractmethod
    def result(self) -> ResultT:
        """Called to get the result of the visitor."""

    def handle_error(self, error: Exception) -> None:
        """Called for encountered errors. Defaults to raising an exception."""
        raise error


class GameBuilder(BaseVisitor[GameT]):
    """
    Creates a game model. Default visitor for :func:`~chess.pgn.read_game()`.
    """

    @typing.overload
    def __init__(self: GameBuilder[Game]) -> None: ...
    @typing.overload
    def __init__(self: GameBuilder[GameT], *, Game: Type[GameT]) -> None: ...
    def __init__(self, *, Game: Any = Game) -> None:
        self.Game = Game

    def begin_game(self) -> None:
        self.game: GameT = self.Game()

        self.variation_stack: List[GameNode] = [self.game]
        self.starting_comment = ""
        self.in_variation = False

    def begin_headers(self) -> Headers:
        return self.game.headers

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        self.game.headers[tagname] = tagvalue

    def visit_nag(self, nag: int) -> None:
        self.variation_stack[-1].nags.add(nag)

    def begin_variation(self) -> None:
        parent = self.variation_stack[-1].parent
        assert parent is not None, "begin_variation called, but root node on top of stack"
        self.variation_stack.append(parent)
        self.in_variation = False

    def end_variation(self) -> None:
        self.variation_stack.pop()

    def visit_result(self, result: str) -> None:
        if self.game.headers.get("Result", "*") == "*":
            self.game.headers["Result"] = result

    def visit_comment(self, comment: str) -> None:
        if self.in_variation or (self.variation_stack[-1].parent is None and self.variation_stack[-1].is_end()):
            # Add as a comment for the current node if in the middle of
            # a variation. Add as a comment for the game if the comment
            # starts before any move.
            new_comment = [self.variation_stack[-1].comment, comment]
            self.variation_stack[-1].comment = "\n".join(new_comment).strip()
        else:
            # Otherwise, it is a starting comment.
            new_comment = [self.starting_comment, comment]
            self.starting_comment = "\n".join(new_comment).strip()

    def visit_move(self, board: chess.Board, move: chess.Move) -> None:
        self.variation_stack[-1] = self.variation_stack[-1].add_variation(move)
        self.variation_stack[-1].starting_comment = self.starting_comment
        self.starting_comment = ""
        self.in_variation = True

    def handle_error(self, error: Exception) -> None:
        """
        Populates :data:`chess.pgn.Game.errors` with encountered errors and
        logs them.

        You can silence the log and handle errors yourself after parsing:

        >>> import chess.pgn
        >>> import logging
        >>>
        >>> logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)
        >>>
        >>> pgn = open("data/pgn/kasparov-deep-blue-1997.pgn")
        >>>
        >>> game = chess.pgn.read_game(pgn)
        >>> game.errors  # List of exceptions
        []

        You can also override this method to hook into error handling:

        >>> import chess.pgn
        >>>
        >>> class MyGameBuilder(chess.pgn.GameBuilder):
        >>>     def handle_error(self, error: Exception) -> None:
        >>>         pass  # Ignore error
        >>>
        >>> pgn = open("data/pgn/kasparov-deep-blue-1997.pgn")
        >>>
        >>> game = chess.pgn.read_game(pgn, Visitor=MyGameBuilder)
        """
        LOGGER.exception("error during pgn parsing")
        self.game.errors.append(error)

    def result(self) -> GameT:
        """
        Returns the visited :class:`~chess.pgn.Game()`.
        """
        return self.game


class HeadersBuilder(BaseVisitor[HeadersT]):
    """Collects headers into a dictionary."""

    @typing.overload
    def __init__(self: HeadersBuilder[Headers]) -> None: ...
    @typing.overload
    def __init__(self: HeadersBuilder[HeadersT], *, Headers: Type[Headers]) -> None: ...
    def __init__(self, *, Headers: Any = Headers) -> None:
        self.Headers = Headers

    def begin_headers(self) -> HeadersT:
        self.headers: HeadersT = self.Headers({})
        return self.headers

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        self.headers[tagname] = tagvalue

    def end_headers(self) -> SkipType:
        return SKIP

    def result(self) -> HeadersT:
        return self.headers


class BoardBuilder(BaseVisitor[chess.Board]):
    """
    Returns the final position of the game. The mainline of the game is
    on the move stack.
    """

    def begin_game(self) -> None:
        self.skip_variation_depth = 0

    def begin_variation(self) -> SkipType:
        self.skip_variation_depth += 1
        return SKIP

    def end_variation(self) -> None:
        self.skip_variation_depth = max(self.skip_variation_depth - 1, 0)

    def visit_board(self, board: chess.Board) -> None:
        if not self.skip_variation_depth:
            self.board = board

    def result(self) -> chess.Board:
        return self.board


class SkipVisitor(BaseVisitor[_TrueLiteral]):
    """Skips a game."""

    def begin_game(self) -> SkipType:
        return SKIP

    def end_headers(self) -> SkipType:
        return SKIP

    def begin_variation(self) -> SkipType:
        return SKIP

    def result(self) -> _TrueLiteral:
        return True


class StringExporterMixin:
    def __init__(self, *, columns: Optional[int] = 80, headers: bool = True, comments: bool = True, variations: bool = True):
        self.columns = columns
        self.headers = headers
        self.comments = comments
        self.variations = variations

        self.found_headers = False

        self.force_movenumber = True

        self.lines: List[str] = []
        self.current_line = ""
        self.variation_depth = 0

    def flush_current_line(self) -> None:
        if self.current_line:
            self.lines.append(self.current_line.rstrip())
        self.current_line = ""

    def write_token(self, token: str) -> None:
        if self.columns is not None and self.columns - len(self.current_line) < len(token):
            self.flush_current_line()
        self.current_line += token

    def write_line(self, line: str = "") -> None:
        self.flush_current_line()
        self.lines.append(line.rstrip())

    def end_game(self) -> None:
        self.write_line()

    def begin_headers(self) -> None:
        self.found_headers = False

    def visit_header(self, tagname: str, tagvalue: str) -> None:
        if self.headers:
            self.found_headers = True
            self.write_line(f"[{tagname} \"{tagvalue}\"]")

    def end_headers(self) -> None:
        if self.found_headers:
            self.write_line()

    def begin_variation(self) -> Optional[SkipType]:
        self.variation_depth += 1

        if self.variations:
            self.write_token("( ")
            self.force_movenumber = True
            return None
        else:
            return SKIP

    def end_variation(self) -> None:
        self.variation_depth -= 1

        if self.variations:
            self.write_token(") ")
            self.force_movenumber = True

    def visit_comment(self, comment: str) -> None:
        if self.comments and (self.variations or not self.variation_depth):
            self.write_token("{ " + comment.replace("}", "").strip() + " } ")
            self.force_movenumber = True

    def visit_nag(self, nag: int) -> None:
        if self.comments and (self.variations or not self.variation_depth):
            self.write_token("$" + str(nag) + " ")

    def visit_move(self, board: chess.Board, move: chess.Move) -> None:
        if self.variations or not self.variation_depth:
            # Write the move number.
            if board.turn == chess.WHITE:
                self.write_token(str(board.fullmove_number) + ". ")
            elif self.force_movenumber:
                self.write_token(str(board.fullmove_number) + "... ")

            # Write the SAN.
            self.write_token(board.san(move) + " ")

            self.force_movenumber = False

    def visit_result(self, result: str) -> None:
        self.write_token(result + " ")


class StringExporter(StringExporterMixin, BaseVisitor[str]):
    """
    Allows exporting a game as a string.

    >>> import chess.pgn
    >>>
    >>> game = chess.pgn.Game()
    >>>
    >>> exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    >>> pgn_string = game.accept(exporter)

    Only *columns* characters are written per line. If *columns* is ``None``,
    then the entire movetext will be on a single line. This does not affect
    header tags and comments.

    There will be no newline characters at the end of the string.
    """

    def result(self) -> str:
        if self.current_line:
            return "\n".join(itertools.chain(self.lines, [self.current_line.rstrip()])).rstrip()
        else:
            return "\n".join(self.lines).rstrip()

    def __str__(self) -> str:
        return self.result()


class FileExporter(StringExporterMixin, BaseVisitor[int]):
    """
    Acts like a :class:`~chess.pgn.StringExporter`, but games are written
    directly into a text file.

    There will always be a blank line after each game. Handling encodings is up
    to the caller.

    >>> import chess.pgn
    >>>
    >>> game = chess.pgn.Game()
    >>>
    >>> new_pgn = open("/dev/null", "w", encoding="utf-8")
    >>> exporter = chess.pgn.FileExporter(new_pgn)
    >>> game.accept(exporter)
    """

    def __init__(self, handle: TextIO, *, columns: Optional[int] = 80, headers: bool = True, comments: bool = True, variations: bool = True):
        super().__init__(columns=columns, headers=headers, comments=comments, variations=variations)
        self.handle = handle

    def begin_game(self) -> None:
        self.written: int = 0
        super().begin_game()

    def flush_current_line(self) -> None:
        if self.current_line:
            self.written += self.handle.write(self.current_line.rstrip())
            self.written += self.handle.write("\n")
        self.current_line = ""

    def write_line(self, line: str = "") -> None:
        self.flush_current_line()
        self.written += self.handle.write(line.rstrip())
        self.written += self.handle.write("\n")

    def result(self) -> int:
        return self.written

    def __repr__(self) -> str:
        return f"<FileExporter at {id(self):#x}>"

    def __str__(self) -> str:
        return self.__repr__()


@typing.overload
def read_game(handle: TextIO) -> Optional[Game]: ...
@typing.overload
def read_game(handle: TextIO, *, Visitor: Callable[[], BaseVisitor[ResultT]]) -> Optional[ResultT]: ...
def read_game(handle: TextIO, *, Visitor: Any = GameBuilder) -> Any:
    """
    Reads a game from a file opened in text mode.

    >>> import chess.pgn
    >>>
    >>> pgn = open("data/pgn/kasparov-deep-blue-1997.pgn")
    >>>
    >>> first_game = chess.pgn.read_game(pgn)
    >>> second_game = chess.pgn.read_game(pgn)
    >>>
    >>> first_game.headers["Event"]
    'IBM Man-Machine, New York USA'
    >>>
    >>> # Iterate through all moves and play them on a board.
    >>> board = first_game.board()
    >>> for move in first_game.mainline_moves():
    ...     board.push(move)
    ...
    >>> board
    Board('4r3/6P1/2p2P1k/1p6/pP2p1R1/P1B5/2P2K2/3r4 b - - 0 45')

    By using text mode, the parser does not need to handle encodings. It is the
    caller's responsibility to open the file with the correct encoding.
    PGN files are usually ASCII or UTF-8 encoded, sometimes with BOM (which
    this parser automatically ignores).

    >>> pgn = open("data/pgn/kasparov-deep-blue-1997.pgn", encoding="utf-8")

    Use :class:`~io.StringIO` to parse games from a string.

    >>> import io
    >>>
    >>> pgn = io.StringIO("1. e4 e5 2. Nf3 *")
    >>> game = chess.pgn.read_game(pgn)

    The end of a game is determined by a completely blank line or the end of
    the file. (Of course, blank lines in comments are possible).

    According to the PGN standard, at least the usual seven header tags are
    required for a valid game. This parser also handles games without any
    headers just fine.

    The parser is relatively forgiving when it comes to errors. It skips over
    tokens it can not parse. By default, any exceptions are logged and
    collected in :data:`Game.errors <chess.pgn.Game.errors>`. This behavior can
    be :func:`overridden <chess.pgn.GameBuilder.handle_error>`.

    Returns the parsed game or ``None`` if the end of file is reached.
    """
    visitor = Visitor()

    found_game = False
    skipping_game = False
    managed_headers: Optional[Headers] = None
    unmanaged_headers: Optional[Headers] = None

    # Ignore leading empty lines and comments.
    line = handle.readline().lstrip("\ufeff")
    while line.isspace() or line.startswith("%") or line.startswith(";"):
        line = handle.readline()

    # Parse game headers.
    consecutive_empty_lines = 0
    while line:
        # Ignore comments.
        if line.startswith("%") or line.startswith(";"):
            line = handle.readline()
            continue

        # Ignore up to one consecutive empty line between headers.
        if consecutive_empty_lines < 1 and line.isspace():
            consecutive_empty_lines += 1
            line = handle.readline()
            continue

        # First token of the game.
        if not found_game:
            found_game = True
            skipping_game = visitor.begin_game() is SKIP
            if not skipping_game:
                managed_headers = visitor.begin_headers()
                if not isinstance(managed_headers, Headers):
                    unmanaged_headers = Headers({})

        if not line.startswith("["):
            break

        consecutive_empty_lines = 0

        if not skipping_game:
            tag_match = TAG_REGEX.match(line)
            if tag_match:
                visitor.visit_header(tag_match.group(1), tag_match.group(2))
                if unmanaged_headers is not None:
                    unmanaged_headers[tag_match.group(1)] = tag_match.group(2)
            else:
                break

        line = handle.readline()

    if not found_game:
        return None

    if not skipping_game:
        skipping_game = visitor.end_headers() is SKIP

    if not skipping_game:
        # Chess variant.
        headers = managed_headers if unmanaged_headers is None else unmanaged_headers
        assert headers is not None, "got neither managed nor unmanaged headers"
        try:
            VariantBoard = headers.variant()
        except ValueError as error:
            visitor.handle_error(error)
            VariantBoard = chess.Board

        # Initial position.
        fen = headers.get("FEN", VariantBoard.starting_fen)
        try:
            board = VariantBoard(fen, chess960=headers.is_chess960())
        except ValueError as error:
            visitor.handle_error(error)
            skipping_game = True
        else:
            board.chess960 = board.chess960 or board.has_chess960_castling_rights()
            board_stack = [board]
            visitor.visit_board(board)

    # Fast path: Skip entire game.
    if skipping_game:
        in_comment = False

        while line:
            if not in_comment:
                if line.isspace():
                    break
                elif line.startswith("%"):
                    line = handle.readline()
                    continue

            for match in SKIP_MOVETEXT_REGEX.finditer(line):
                token = match.group(0)
                if token == "{":
                    in_comment = True
                elif not in_comment and token == ";":
                    break
                elif token == "}":
                    in_comment = False

            line = handle.readline()

        visitor.end_game()
        return visitor.result()

    # Parse movetext.
    skip_variation_depth = 0
    while line:
        read_next_line = True

        # Ignore comments.
        if line.startswith("%") or line.startswith(";"):
            line = handle.readline()
            continue

        # An empty line means the end of a game.
        if line.isspace():
            visitor.end_game()
            return visitor.result()

        for match in MOVETEXT_REGEX.finditer(line):
            token = match.group(0)

            if token.startswith("{"):
                # Consume until the end of the comment.
                line = token[1:]
                comment_lines = []
                while line and "}" not in line:
                    comment_lines.append(line.rstrip())
                    line = handle.readline()
                end_index = line.find("}")
                comment_lines.append(line[:end_index])
                if "}" in line:
                    line = line[end_index:]
                else:
                    line = ""

                if not skip_variation_depth:
                    visitor.visit_comment("\n".join(comment_lines).strip())

                # Continue with the current or the next line.
                if line:
                    read_next_line = False
                break
            elif token == "(":
                if skip_variation_depth:
                    skip_variation_depth += 1
                elif board_stack[-1].move_stack:
                    if visitor.begin_variation() is SKIP:
                        skip_variation_depth = 1
                    else:
                        board = board_stack[-1].copy()
                        board.pop()
                        board_stack.append(board)
            elif token == ")":
                if skip_variation_depth:
                    skip_variation_depth -= 1
                if len(board_stack) > 1:
                    visitor.end_variation()
                    board_stack.pop()
            elif skip_variation_depth:
                continue
            elif token.startswith(";"):
                break
            elif token.startswith("$"):
                # Found a NAG.
                visitor.visit_nag(int(token[1:]))
            elif token == "?":
                visitor.visit_nag(NAG_MISTAKE)
            elif token == "??":
                visitor.visit_nag(NAG_BLUNDER)
            elif token == "!":
                visitor.visit_nag(NAG_GOOD_MOVE)
            elif token == "!!":
                visitor.visit_nag(NAG_BRILLIANT_MOVE)
            elif token == "!?":
                visitor.visit_nag(NAG_SPECULATIVE_MOVE)
            elif token == "?!":
                visitor.visit_nag(NAG_DUBIOUS_MOVE)
            elif token in ["1-0", "0-1", "1/2-1/2", "*"] and len(board_stack) == 1:
                visitor.visit_result(token)
            else:
                # Parse SAN tokens.
                try:
                    move = visitor.parse_san(board_stack[-1], token)
                except ValueError as error:
                    visitor.handle_error(error)
                    skip_variation_depth = 1
                else:
                    visitor.visit_move(board_stack[-1], move)
                    board_stack[-1].push(move)
                visitor.visit_board(board_stack[-1])

        if read_next_line:
            line = handle.readline()

    visitor.end_game()
    return visitor.result()


def read_headers(handle: TextIO) -> Optional[Headers]:
    """
    Reads game headers from a PGN file opened in text mode. Skips the rest of
    the game.

    Since actually parsing many games from a big file is relatively expensive,
    this is a better way to look only for specific games and then seek and
    parse them later.

    This example scans for the first game with Kasparov as the white player.

    >>> import chess.pgn
    >>>
    >>> pgn = open("data/pgn/kasparov-deep-blue-1997.pgn")
    >>>
    >>> kasparov_offsets = []
    >>>
    >>> while True:
    ...     offset = pgn.tell()
    ...
    ...     headers = chess.pgn.read_headers(pgn)
    ...     if headers is None:
    ...         break
    ...
    ...     if "Kasparov" in headers.get("White", "?"):
    ...         kasparov_offsets.append(offset)

    Then it can later be seeked and parsed.

    >>> for offset in kasparov_offsets:
    ...     pgn.seek(offset)
    ...     chess.pgn.read_game(pgn)  # doctest: +ELLIPSIS
    0
    <Game at ... ('Garry Kasparov' vs. 'Deep Blue (Computer)', 1997.??.??)>
    1436
    <Game at ... ('Garry Kasparov' vs. 'Deep Blue (Computer)', 1997.??.??)>
    3067
    <Game at ... ('Garry Kasparov' vs. 'Deep Blue (Computer)', 1997.??.??)>
    """
    return read_game(handle, Visitor=HeadersBuilder)


def skip_game(handle: TextIO) -> bool:
    """
    Skips a game. Returns ``True`` if a game was found and skipped.
    """
    return bool(read_game(handle, Visitor=SkipVisitor))
