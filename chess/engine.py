# This file is part of the python-chess library.
# Copyright (C) 2012-2021 Niklas Fiekas <niklas.fiekas@backscattering.de>
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
import asyncio
import collections
import concurrent.futures
import contextlib
import copy
import dataclasses
import enum
import logging
import math
import warnings
import shlex
import subprocess
import sys
import threading
import typing
import os
import re

import chess

from chess import Color
from types import TracebackType
from typing import Any, Callable, Coroutine, Deque, Dict, Generator, Generic, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Tuple, Type, TypeVar, Union

try:
    from typing import Literal
    _WdlModel = Literal["sf12", "lichess"]
except ImportError:
    # Before Python 3.8.
    _WdlModel = str  # type: ignore


T = TypeVar("T")
ProtocolT = TypeVar("ProtocolT", bound="Protocol")

ConfigValue = Union[str, int, bool, None]
ConfigMapping = Mapping[str, ConfigValue]


LOGGER = logging.getLogger(__name__)


MANAGED_OPTIONS = ["uci_chess960", "uci_variant", "multipv", "ponder"]


class EventLoopPolicy(asyncio.AbstractEventLoopPolicy):
    """
    An event loop policy for thread-local event loops and child watchers.
    Ensures each event loop is capable of spawning and watching subprocesses,
    even when not running on the main thread.

    Windows: Uses :class:`~asyncio.ProactorEventLoop`.

    Unix: Uses :class:`~asyncio.SelectorEventLoop`. If available,
    :class:`~asyncio.PidfdChildWatcher` is used to detect subprocess
    termination (Python 3.9+ on Linux 5.3+). Otherwise, the default child
    watcher is used on the main thread and relatively slow eager polling
    is used on all other threads.
    """
    class _Local(threading.local):
        loop: Optional[asyncio.AbstractEventLoop] = None
        set_called = False
        watcher: Optional[asyncio.AbstractChildWatcher] = None

    def __init__(self) -> None:
        self._local = self._Local()

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        if self._local.loop is None and not self._local.set_called and threading.current_thread() is threading.main_thread():
            self.set_event_loop(self.new_event_loop())
        if self._local.loop is None:
            raise RuntimeError(f"no current event loop in thread {threading.current_thread().name!r}")
        return self._local.loop

    def set_event_loop(self, loop: Optional[asyncio.AbstractEventLoop]) -> None:
        assert loop is None or isinstance(loop, asyncio.AbstractEventLoop)
        self._local.set_called = True
        self._local.loop = loop
        if self._local.watcher is not None:
            self._local.watcher.attach_loop(loop)

    def new_event_loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.SelectorEventLoop()  # type: ignore

    def get_child_watcher(self) -> asyncio.AbstractChildWatcher:
        if self._local.watcher is None:
            self._local.watcher = self._init_watcher()
            self._local.watcher.attach_loop(self._local.loop)
        return self._local.watcher

    def set_child_watcher(self, watcher: Optional[asyncio.AbstractChildWatcher]) -> None:
        assert watcher is None or isinstance(watcher, asyncio.AbstractChildWatcher)
        if self._local.watcher is not None:
            self._local.watcher.close()
        self._local.watcher = watcher

    def _init_watcher(self) -> asyncio.AbstractChildWatcher:
        if sys.platform == "win32":
            raise NotImplementedError

        try:
            os.close(os.pidfd_open(os.getpid()))  # type: ignore
            watcher: asyncio.AbstractChildWatcher = asyncio.PidfdChildWatcher()  # type: ignore
            LOGGER.debug("Using PidfdChildWatcher")
            return watcher
        except (AttributeError, OSError):
            # Before Python 3.9 or before Linux 5.3 or the syscall is not
            # permitted.
            pass

        if threading.current_thread() is threading.main_thread():
            try:
                watcher = asyncio.ThreadedChildWatcher()
                LOGGER.debug("Using ThreadedChildWatcher")
                return watcher
            except AttributeError:
                # Before Python 3.8.
                LOGGER.debug("Using SafeChildWatcher")
                return asyncio.SafeChildWatcher()

        class PollingChildWatcher(asyncio.SafeChildWatcher):
            _loop: Optional[asyncio.AbstractEventLoop]
            _callbacks: Dict[int, Any]

            def __init__(self) -> None:
                super().__init__()
                self._poll_handle: Optional[asyncio.Handle] = None
                self._poll_delay = 0.001

            def attach_loop(self, loop: Optional[asyncio.AbstractEventLoop]) -> None:
                assert loop is None or isinstance(loop, asyncio.AbstractEventLoop)

                if self._loop is not None and loop is None and self._callbacks:
                    warnings.warn("A loop is being detached from a child watcher with pending handlers", RuntimeWarning)

                if self._poll_handle is not None:
                    self._poll_handle.cancel()

                self._loop = loop
                if self._loop is not None:
                    self._poll_handle = self._loop.call_soon(self._poll)
                    self._do_waitpid_all()  # type: ignore

            def _poll(self) -> None:
                if self._loop:
                    self._do_waitpid_all()  # type: ignore
                    self._poll_delay = min(self._poll_delay * 2, 1.0)
                    self._poll_handle = self._loop.call_later(self._poll_delay, self._poll)

        LOGGER.debug("Using PollingChildWatcher")
        return PollingChildWatcher()


def run_in_background(coroutine: Callable[[concurrent.futures.Future[T]], Coroutine[Any, Any, None]], *, name: Optional[str] = None, debug: bool = False, _policy_lock: threading.Lock = threading.Lock()) -> T:
    """
    Runs ``coroutine(future)`` in a new event loop on a background thread.

    Blocks on *future* and returns the result as soon as it is resolved.
    The coroutine and all remaining tasks continue running in the background
    until complete.

    Note: This installs a :class:`chess.engine.EventLoopPolicy` for the entire
    process.
    """
    assert asyncio.iscoroutinefunction(coroutine)

    with _policy_lock:
        if not isinstance(asyncio.get_event_loop_policy(), EventLoopPolicy):
            asyncio.set_event_loop_policy(EventLoopPolicy())

    future: concurrent.futures.Future[T] = concurrent.futures.Future()

    def background() -> None:
        try:
            asyncio.run(coroutine(future))
            future.cancel()
        except Exception as exc:
            future.set_exception(exc)

    threading.Thread(target=background, name=name).start()
    return future.result()


class EngineError(RuntimeError):
    """Runtime error caused by a misbehaving engine or incorrect usage."""


class EngineTerminatedError(EngineError):
    """The engine process exited unexpectedly."""


class AnalysisComplete(Exception):
    """
    Raised when analysis is complete, all information has been consumed, but
    further information was requested.
    """


@dataclasses.dataclass(frozen=True)
class Option:
    """Information about an available engine option."""

    name: str
    """The name of the option."""

    type: str
    """
    The type of the option.

    +--------+-----+------+------------------------------------------------+
    | type   | UCI | CECP | value                                          |
    +========+=====+======+================================================+
    | check  | X   | X    | ``True`` or ``False``                          |
    +--------+-----+------+------------------------------------------------+
    | button | X   | X    | ``None``                                       |
    +--------+-----+------+------------------------------------------------+
    | reset  |     | X    | ``None``                                       |
    +--------+-----+------+------------------------------------------------+
    | save   |     | X    | ``None``                                       |
    +--------+-----+------+------------------------------------------------+
    | string | X   | X    | string without line breaks                     |
    +--------+-----+------+------------------------------------------------+
    | file   |     | X    | string, interpreted as the path to a file      |
    +--------+-----+------+------------------------------------------------+
    | path   |     | X    | string, interpreted as the path to a directory |
    +--------+-----+------+------------------------------------------------+
    """

    default: ConfigValue
    """The default value of the option."""

    min: Optional[int]
    """The minimum integer value of a *spin* option."""

    max: Optional[int]
    """The maximum integer value of a *spin* option."""

    var: Optional[List[str]]
    """A list of allowed string values for a *combo* option."""

    def parse(self, value: ConfigValue) -> ConfigValue:
        if self.type == "check":
            return value and value != "false"
        elif self.type == "spin":
            try:
                value = int(value)  # type: ignore
            except ValueError:
                raise EngineError(f"expected integer for spin option {self.name!r}, got: {value!r}")
            if self.min is not None and value < self.min:
                raise EngineError(f"expected value for option {self.name!r} to be at least {self.min}, got: {value}")
            if self.max is not None and self.max < value:
                raise EngineError(f"expected value for option {self.name!r} to be at most {self.max}, got: {value}")
            return value
        elif self.type == "combo":
            value = str(value)
            if value not in (self.var or []):
                raise EngineError("invalid value for combo option {!r}, got: {} (available: {})".format(self.name, value, ", ".join(self.var) if self.var else "-"))
            return value
        elif self.type in ["button", "reset", "save"]:
            return None
        elif self.type in ["string", "file", "path"]:
            value = str(value)
            if "\n" in value or "\r" in value:
                raise EngineError(f"invalid line-break in string option {self.name!r}: {value!r}")
            return value
        else:
            raise EngineError(f"unknown option type: {self.type!r}")

    def is_managed(self) -> bool:
        """
        Some options are managed automatically: ``UCI_Chess960``,
        ``UCI_Variant``, ``MultiPV``, ``Ponder``.
        """
        return self.name.lower() in MANAGED_OPTIONS


@dataclasses.dataclass
class Limit:
    """Search-termination condition."""

    time: Optional[float] = None
    """Search exactly *time* seconds."""

    depth: Optional[int] = None
    """Search *depth* ply only."""

    nodes: Optional[int] = None
    """Search only a limited number of *nodes*."""

    mate: Optional[int] = None
    """Search for a mate in *mate* moves."""

    white_clock: Optional[float] = None
    """Time in seconds remaining for White."""

    black_clock: Optional[float] = None
    """Time in seconds remaining for Black."""

    white_inc: Optional[float] = None
    """Fisher increment for White, in seconds."""

    black_inc: Optional[float] = None
    """Fisher increment for Black, in seconds."""

    remaining_moves: Optional[int] = None
    """
    Number of moves to the next time control. If this is not set, but
    *white_clock* and *black_clock* are, then it is sudden death.
    """

    def __repr__(self) -> str:
        # Like default __repr__, but without None values.
        return "{}({})".format(
            type(self).__name__,
            ", ".join("{}={!r}".format(attr, getattr(self, attr))
                      for attr in ["time", "depth", "nodes", "mate", "white_clock", "black_clock", "white_inc", "black_inc", "remaining_moves"]
                      if getattr(self, attr) is not None))


try:
    class InfoDict(typing.TypedDict, total=False):
        """
        Dictionary of aggregated information sent by the engine.

        Commonly used keys are: ``score`` (a :class:`~chess.engine.PovScore`),
        ``pv`` (a list of :class:`~chess.Move` objects), ``depth``,
        ``seldepth``, ``time`` (in seconds), ``nodes``, ``nps``, ``multipv``
        (``1`` for the mainline).

        Others: ``tbhits``, ``currmove``, ``currmovenumber``, ``hashfull``,
        ``cpuload``, ``refutation``, ``currline``, ``ebf`` (effective branching factor),
        ``wdl`` (a :class:`~chess.engine.PovWdl`), and ``string``.
        """
        score: PovScore
        pv: List[chess.Move]
        depth: int
        seldepth: int
        time: float
        nodes: int
        nps: int
        tbhits: int
        multipv: int
        currmove: chess.Move
        currmovenumber: int
        hashfull: int
        cpuload: int
        refutation: Dict[chess.Move, List[chess.Move]]
        currline: Dict[int, List[chess.Move]]
        ebf: float
        wdl: PovWdl
        string: str
except AttributeError:
    # Before Python 3.8.
    InfoDict = dict  # type: ignore


class PlayResult:
    """Returned by :func:`chess.engine.Protocol.play()`."""

    move: Optional[chess.Move]
    """The best move according to the engine, or ``None``."""

    ponder: Optional[chess.Move]
    """The response that the engine expects after *move*, or ``None``."""

    info: InfoDict
    """
    A dictionary of extra :class:`information <chess.engine.InfoDict>`
    sent by the engine, if selected with the *info* argument of
    :func:`~chess.engine.Protocol.play()`.
    """

    draw_offered: bool
    """Whether the engine offered a draw before moving."""

    resigned: bool
    """Whether the engine resigned."""

    def __init__(self,
                 move: Optional[chess.Move],
                 ponder: Optional[chess.Move],
                 info: Optional[InfoDict] = None,
                 *,
                 draw_offered: bool = False,
                 resigned: bool = False) -> None:
        self.move = move
        self.ponder = ponder
        self.info = info or {}
        self.draw_offered = draw_offered
        self.resigned = resigned

    def __repr__(self) -> str:
        return "<{} at {:#x} (move={}, ponder={}, info={}, draw_offered={}, resigned={})>".format(
            type(self).__name__, id(self), self.move, self.ponder, self.info,
            self.draw_offered, self.resigned)


class Info(enum.IntFlag):
    """Used to filter information sent by the chess engine."""
    NONE = 0
    BASIC = 1
    SCORE = 2
    PV = 4
    REFUTATION = 8
    CURRLINE = 16
    ALL = BASIC | SCORE | PV | REFUTATION | CURRLINE

INFO_NONE = Info.NONE
INFO_BASIC = Info.BASIC
INFO_SCORE = Info.SCORE
INFO_PV = Info.PV
INFO_REFUTATION = Info.REFUTATION
INFO_CURRLINE = Info.CURRLINE
INFO_ALL = Info.ALL


class PovScore:
    """A relative :class:`~chess.engine.Score` and the point of view."""

    relative: Score
    """The relative :class:`~chess.engine.Score`."""

    turn: Color
    """The point of view (``chess.WHITE`` or ``chess.BLACK``)."""

    def __init__(self, relative: Score, turn: Color) -> None:
        self.relative = relative
        self.turn = turn

    def white(self) -> Score:
        """Gets the score from White's point of view."""
        return self.pov(chess.WHITE)

    def black(self) -> Score:
        """Gets the score from Black's point of view."""
        return self.pov(chess.BLACK)

    def pov(self, color: Color) -> Score:
        """Gets the score from the point of view of the given *color*."""
        return self.relative if self.turn == color else -self.relative

    def is_mate(self) -> bool:
        """Tests if this is a mate score."""
        return self.relative.is_mate()

    def wdl(self, *, model: _WdlModel = "sf12", ply: int = 30) -> PovWdl:
        """See :func:`~chess.engine.Score.wdl()`."""
        return PovWdl(self.relative.wdl(), self.turn)

    def __repr__(self) -> str:
        return "PovScore({!r}, {})".format(self.relative, "WHITE" if self.turn else "BLACK")

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PovScore):
            return self.white() == other.white()
        else:
            return NotImplemented


class Score(abc.ABC):
    """
    Evaluation of a position.

    The score can be :class:`~chess.engine.Cp` (centi-pawns),
    :class:`~chess.engine.Mate` or :py:data:`~chess.engine.MateGiven`.
    A positive value indicates an advantage.

    There is a total order defined on centi-pawn and mate scores.

    >>> from chess.engine import Cp, Mate, MateGiven
    >>>
    >>> Mate(-0) < Mate(-1) < Cp(-50) < Cp(200) < Mate(4) < Mate(1) < MateGiven
    True

    Scores can be negated to change the point of view:

    >>> -Cp(20)
    Cp(-20)

    >>> -Mate(-4)
    Mate(+4)

    >>> -Mate(0)
    MateGiven
    """

    @typing.overload
    def score(self, *, mate_score: int) -> int: ...
    @typing.overload
    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]: ...
    @abc.abstractmethod
    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]:
        """
        Returns the centi-pawn score as an integer or ``None``.

        You can optionally pass a large value to convert mate scores to
        centi-pawn scores.

        >>> Cp(-300).score()
        -300
        >>> Mate(5).score() is None
        True
        >>> Mate(5).score(mate_score=100000)
        99995
        """

    @abc.abstractmethod
    def mate(self) -> Optional[int]:
        """
        Returns the number of plies to mate, negative if we are getting
        mated, or ``None``.

        .. warning::
            This conflates ``Mate(0)`` (we lost) and ``MateGiven``
            (we won) to ``0``.
        """

    def is_mate(self) -> bool:
        """Tests if this is a mate score."""
        return self.mate() is not None

    @abc.abstractmethod
    def wdl(self, *, model: _WdlModel = "sf12", ply: int = 30) -> Wdl:
        """
        Returns statistics for the expected outcome of this game, based on
        a *model*, given that this score is reached at *ply*.

        Scores have a total order, but it makes little sense to compute
        the difference between two scores. For example, going from
        ``Cp(-100)`` to ``Cp(+100)`` is much more significant than going
        from ``Cp(+300)`` to ``Cp(+500)``. It is better to compute differences
        of the expectation values for the outcome of the game (based on winning
        chances and drawing chances).

        >>> Cp(100).wdl().expectation() - Cp(-100).wdl().expectation()  # doctest: +ELLIPSIS
        0.379...

        >>> Cp(500).wdl().expectation() - Cp(300).wdl().expectation()  # doctest: +ELLIPSIS
        0.015...

        :param model:
            * ``sf12``, the WDL model used by Stockfish 12.
            * ``lichess``, the win rate model used by Lichess.
              Does not use *ply*, and does not consider drawing chances.
        :param ply: The number of half-moves played since the starting
            position. Models may scale scores slightly differently based on
            this. Defaults to middle game.
        """

    @abc.abstractmethod
    def __neg__(self) -> Score:
        ...

    @abc.abstractmethod
    def __pos__(self) -> Score:
        ...

    @abc.abstractmethod
    def __abs__(self) -> Score:
        ...

    def _score_tuple(self) -> Tuple[bool, bool, bool, int, Optional[int]]:
        mate = self.mate()
        return (
            isinstance(self, MateGivenType),
            mate is not None and mate > 0,
            mate is None,
            -(mate or 0),
            self.score(),
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Score):
            return self._score_tuple() == other._score_tuple()
        else:
            return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Score):
            return self._score_tuple() < other._score_tuple()
        else:
            return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Score):
            return self._score_tuple() <= other._score_tuple()
        else:
            return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Score):
            return self._score_tuple() > other._score_tuple()
        else:
            return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Score):
            return self._score_tuple() >= other._score_tuple()
        else:
            return NotImplemented


def _sf12_wins(cp: int, *, ply: int) -> int:
    # https://github.com/official-stockfish/Stockfish/blob/sf_12/src/uci.cpp#L198-L218
    m = min(240, max(ply, 0)) / 64
    a = (((-8.24404295 * m + 64.23892342) * m + -95.73056462) * m) + 153.86478679
    b = (((-3.37154371 * m + 28.44489198) * m + -56.67657741) * m) + 72.05858751
    x = min(1000, max(cp, -1000))
    return int(0.5 + 1000 / (1 + math.exp((a - x) / b)))

def _lichess_raw_wins(cp: int) -> int:
    return round(1000 / (1 + math.exp(-0.004 * cp)))


class Cp(Score):
    """Centi-pawn score."""

    def __init__(self, cp: int) -> None:
        self.cp = cp

    def mate(self) -> None:
        return None

    def score(self, *, mate_score: Optional[int] = None) -> int:
        return self.cp

    def wdl(self, *, model: _WdlModel = "sf12", ply: int = 30) -> Wdl:
        if model == "lichess":
            wins = _lichess_raw_wins(max(-1000, min(self.cp, 1000)))
            losses = 1000 - wins
        else:
            wins = _sf12_wins(self.cp, ply=ply)
            losses = _sf12_wins(-self.cp, ply=ply)
        draws = 1000 - wins - losses
        return Wdl(wins, draws, losses)

    def __str__(self) -> str:
        return f"+{self.cp:d}" if self.cp > 0 else str(self.cp)

    def __repr__(self) -> str:
        return f"Cp({self})"

    def __neg__(self) -> Cp:
        return Cp(-self.cp)

    def __pos__(self) -> Cp:
        return Cp(self.cp)

    def __abs__(self) -> Cp:
        return Cp(abs(self.cp))


class Mate(Score):
    """Mate score."""

    def __init__(self, moves: int) -> None:
        self.moves = moves

    def mate(self) -> int:
        return self.moves

    @typing.overload
    def score(self, *, mate_score: int) -> int: ...
    @typing.overload
    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]: ...
    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]:
        if mate_score is None:
            return None
        elif self.moves > 0:
            return mate_score - self.moves
        else:
            return -mate_score - self.moves

    def wdl(self, *, model: _WdlModel = "sf12", ply: int = 30) -> Wdl:
        if model == "lichess":
            cp = (21 - min(10, abs(self.moves))) * 100
            wins = _lichess_raw_wins(cp)
            return Wdl(wins, 0, 1000 - wins) if self.moves > 0 else Wdl(1000 - wins, 0, wins)
        else:
            return Wdl(1000, 0, 0) if self.moves > 0 else Wdl(0, 0, 1000)

    def __str__(self) -> str:
        return f"#+{self.moves}" if self.moves > 0 else f"#-{abs(self.moves)}"

    def __repr__(self) -> str:
        return "Mate({})".format(str(self).lstrip("#"))

    def __neg__(self) -> Union[MateGivenType, Mate]:
        return MateGiven if not self.moves else Mate(-self.moves)

    def __pos__(self) -> Mate:
        return Mate(self.moves)

    def __abs__(self) -> Union[MateGivenType, Mate]:
        return MateGiven if not self.moves else Mate(abs(self.moves))


class MateGivenType(Score):
    """Winning mate score, equivalent to ``-Mate(0)``."""

    def mate(self) -> int:
        return 0

    @typing.overload
    def score(self, *, mate_score: int) -> int: ...
    @typing.overload
    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]: ...
    def score(self, *, mate_score: Optional[int] = None) -> Optional[int]:
        return mate_score

    def wdl(self, *, model: _WdlModel = "sf12", ply: int = 30) -> Wdl:
        return Wdl(1000, 0, 0)

    def __neg__(self) -> Mate:
        return Mate(0)

    def __pos__(self) -> MateGivenType:
        return self

    def __abs__(self) -> MateGivenType:
        return self

    def __repr__(self) -> str:
        return "MateGiven"

    def __str__(self) -> str:
        return "#+0"

MateGiven = MateGivenType()


class PovWdl:
    """
    Relative :class:`win/draw/loss statistics <chess.engine.Wdl>` and the point
    of view.

    .. deprecated:: 1.2
        Behaves like a tuple
        ``(wdl.relative.wins, wdl.relative.draws, wdl.relative.losses)``
        for backwards compatibility. But it is recommended to use the provided
        fields and methods instead.
    """

    relative: Wdl
    """The relative :class:`~chess.engine.Wdl`."""

    turn: Color
    """The point of view (``chess.WHITE`` or ``chess.BLACK``)."""

    def __init__(self, relative: Wdl, turn: Color) -> None:
        self.relative = relative
        self.turn = turn

    def white(self) -> Wdl:
        """Gets the :class:`~chess.engine.Wdl` from White's point of view."""
        return self.pov(chess.WHITE)

    def black(self) -> Wdl:
        """Gets the :class:`~chess.engine.Wdl` from Black's point of view."""
        return self.pov(chess.BLACK)

    def pov(self, color: Color) -> Wdl:
        """
        Gets the :class:`~chess.engine.Wdl` from the point of view of the given
        *color*.
        """
        return self.relative if self.turn == color else -self.relative

    def __bool__(self) -> bool:
        return bool(self.relative)

    def __repr__(self) -> str:
        return "PovWdl({!r}, {})".format(self.relative, "WHITE" if self.turn else "BLACK")

    # Unfortunately in python-chess v1.1.0, info["wdl"] was a simple tuple
    # of the relative permille values, so we have to support __iter__,
    # __len__, __getitem__, and equality comparisons with other tuples.
    # Never mind the ordering, because that's not a sensible operation, anyway.

    def __iter__(self) -> Iterator[int]:
        yield self.relative.wins
        yield self.relative.draws
        yield self.relative.losses

    def __len__(self) -> int:
        return 3

    def __getitem__(self, idx: int) -> int:
        return (self.relative.wins, self.relative.draws, self.relative.losses)[idx]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PovWdl):
            return self.white() == other.white()
        elif isinstance(other, tuple):
            return (self.relative.wins, self.relative.draws, self.relative.losses) == other
        else:
            return NotImplemented


@dataclasses.dataclass
class Wdl:
    """Win/draw/loss statistics."""

    wins: int
    """The number of wins."""

    draws: int
    """The number of draws."""

    losses: int
    """The number of losses."""

    def total(self) -> int:
        """
        Returns the total number of games. Usually, ``wdl`` reported by engines
        is scaled to 1000 games.
        """
        return self.wins + self.draws + self.losses

    def winning_chance(self) -> float:
        """Returns the relative frequency of wins."""
        return self.wins / self.total()

    def drawing_chance(self) -> float:
        """Returns the relative frequency of draws."""
        return self.draws / self.total()

    def losing_chance(self) -> float:
        """Returns the relative frequency of losses."""
        return self.losses / self.total()

    def expectation(self) -> float:
        """
        Returns the expectation value, where a win is valued 1, a draw is
        valued 0.5, and a loss is valued 0.
        """
        return (self.wins + 0.5 * self.draws) / self.total()

    def __bool__(self) -> bool:
        return bool(self.total())

    def __iter__(self) -> Iterator[int]:
        yield self.wins
        yield self.draws
        yield self.losses

    def __reversed__(self) -> Iterator[int]:
        yield self.losses
        yield self.draws
        yield self.wins

    def __pos__(self) -> Wdl:
        return self

    def __neg__(self) -> Wdl:
        return Wdl(self.losses, self.draws, self.wins)


class MockTransport(asyncio.SubprocessTransport, asyncio.WriteTransport):
    def __init__(self, protocol: Protocol) -> None:
        super().__init__()
        self.protocol = protocol
        self.expectations: Deque[Tuple[str, List[str]]] = collections.deque()
        self.expected_pings = 0
        self.stdin_buffer = bytearray()
        self.protocol.connection_made(self)

    def expect(self, expectation: str, responses: List[str] = []) -> None:
        self.expectations.append((expectation, responses))

    def expect_ping(self) -> None:
        self.expected_pings += 1

    def assert_done(self) -> None:
        assert not self.expectations, f"pending expectations: {self.expectations}"

    def get_pipe_transport(self, fd: int) -> Optional[asyncio.BaseTransport]:
        assert fd == 0, f"expected 0 for stdin, got {fd}"
        return self

    def write(self, data: bytes) -> None:
        self.stdin_buffer.extend(data)
        while b"\n" in self.stdin_buffer:
            line_bytes, self.stdin_buffer = self.stdin_buffer.split(b"\n", 1)
            line = line_bytes.decode("utf-8")

            if line.startswith("ping ") and self.expected_pings:
                self.expected_pings -= 1
                self.protocol.pipe_data_received(1, line.replace("ping ", "pong ").encode("utf-8") + b"\n")
            else:
                assert self.expectations, f"unexpected: {line!r}"
                expectation, responses = self.expectations.popleft()
                assert expectation == line, f"expected {expectation}, got: {line}"
                if responses:
                    self.protocol.pipe_data_received(1, "\n".join(responses).encode("utf-8") + b"\n")

    def get_pid(self) -> int:
        return id(self)

    def get_returncode(self) -> Optional[int]:
        return None if self.expectations else 0


class Protocol(asyncio.SubprocessProtocol, metaclass=abc.ABCMeta):
    """Protocol for communicating with a chess engine process."""

    options: MutableMapping[str, Option]
    """Dictionary of available options."""

    id: Dict[str, str]
    """
    Dictionary of information about the engine. Common keys are ``name``
    and ``author``.
    """

    returncode: asyncio.Future[int]
    """Future: Exit code of the process."""

    def __init__(self: ProtocolT) -> None:
        self.loop = asyncio.get_running_loop()
        self.transport: Optional[asyncio.SubprocessTransport] = None

        self.buffer = {
            1: bytearray(),  # stdout
            2: bytearray(),  # stderr
        }

        self.command: Optional[BaseCommand[ProtocolT, Any]] = None
        self.next_command: Optional[BaseCommand[ProtocolT, Any]] = None

        self.initialized = False
        self.returncode: asyncio.Future[int] = asyncio.Future()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        # SubprocessTransport expected, but not checked to allow duck typing.
        self.transport = transport  # type: ignore
        LOGGER.debug("%s: Connection made", self)

    def connection_lost(self: ProtocolT, exc: Optional[Exception]) -> None:
        assert self.transport is not None
        code = self.transport.get_returncode()
        assert code is not None, "connect lost, but got no returncode"
        LOGGER.debug("%s: Connection lost (exit code: %d, error: %s)", self, code, exc)

        # Terminate commands.
        if self.command is not None:
            self.command._engine_terminated(self, code)
            self.command = None
        if self.next_command is not None:
            self.next_command._engine_terminated(self, code)
            self.next_command = None

        self.returncode.set_result(code)

    def process_exited(self) -> None:
        LOGGER.debug("%s: Process exited", self)

    def send_line(self, line: str) -> None:
        LOGGER.debug("%s: << %s", self, line)
        assert self.transport is not None, "cannot send line before connection is made"
        stdin = self.transport.get_pipe_transport(0)
        # WriteTransport expected, but not checked to allow duck typing.
        stdin.write(line.encode("utf-8"))  # type: ignore
        stdin.write(b"\n")  # type: ignore

    def pipe_data_received(self, fd: int, data: Union[bytes, str]) -> None:
        self.buffer[fd].extend(data)  # type: ignore
        while b"\n" in self.buffer[fd]:
            line_bytes, self.buffer[fd] = self.buffer[fd].split(b"\n", 1)
            if line_bytes.endswith(b"\r"):
                line_bytes = line_bytes[:-1]
            try:
                line = line_bytes.decode("utf-8")
            except UnicodeDecodeError as err:
                LOGGER.warning("%s: >> %r (%s)", self, bytes(line_bytes), err)
            else:
                if fd == 1:
                    self.loop.call_soon(self._line_received, line)
                else:
                    self.loop.call_soon(self.error_line_received, line)

    def error_line_received(self, line: str) -> None:
        LOGGER.warning("%s: stderr >> %s", self, line)

    def _line_received(self: ProtocolT, line: str) -> None:
        LOGGER.debug("%s: >> %s", self, line)

        self.line_received(line)

        if self.command:
            self.command._line_received(self, line)

    def line_received(self, line: str) -> None:
        pass

    async def communicate(self: ProtocolT, command_factory: Callable[[], BaseCommand[ProtocolT, T]]) -> T:
        command = command_factory()

        if self.returncode.done():
            raise EngineTerminatedError(f"engine process dead (exit code: {self.returncode.result()})")

        assert command.state == CommandState.New

        if self.next_command is not None:
            self.next_command.result.cancel()
            self.next_command.finished.cancel()
            self.next_command._done()

        self.next_command = command

        def previous_command_finished(_: Optional[asyncio.Future[None]]) -> None:
            if self.command is not None:
                self.command._done()

            self.command, self.next_command = self.next_command, None
            if self.command is not None:
                cmd = self.command

                def cancel_if_cancelled(result: asyncio.Future[T]) -> None:
                    if result.cancelled():
                        cmd._cancel(self)

                cmd.result.add_done_callback(cancel_if_cancelled)
                cmd.finished.add_done_callback(previous_command_finished)
                cmd._start(self)

        if self.command is None:
            previous_command_finished(None)
        elif not self.command.result.done():
            self.command.result.cancel()
        elif not self.command.result.cancelled():
            self.command._cancel(self)

        return await command.result

    def __repr__(self) -> str:
        pid = self.transport.get_pid() if self.transport is not None else "?"
        return f"<{type(self).__name__} (pid={pid})>"

    @abc.abstractmethod
    async def initialize(self) -> None:
        """Initializes the engine."""

    @abc.abstractmethod
    async def ping(self) -> None:
        """
        Pings the engine and waits for a response. Used to ensure the engine
        is still alive and idle.
        """

    @abc.abstractmethod
    async def configure(self, options: ConfigMapping) -> None:
        """
        Configures global engine options.

        :param options: A dictionary of engine options where the keys are
            names of :data:`~chess.engine.Protocol.options`. Do not set options
            that are managed automatically
            (:func:`chess.engine.Option.is_managed()`).
        """

    @abc.abstractmethod
    async def play(self, board: chess.Board, limit: Limit, *, game: object = None, info: Info = INFO_NONE, ponder: bool = False, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> PlayResult:
        """
        Plays a position.

        :param board: The position. The entire move stack will be sent to the
            engine.
        :param limit: An instance of :class:`chess.engine.Limit` that
            determines when to stop thinking.
        :param game: Optional. An arbitrary object that identifies the game.
            Will automatically inform the engine if the object is not equal
            to the previous game (e.g., ``ucinewgame``, ``new``).
        :param info: Selects which additional information to retrieve from the
            engine. ``INFO_NONE``, ``INFO_BASE`` (basic information that is
            trivial to obtain), ``INFO_SCORE``, ``INFO_PV``,
            ``INFO_REFUTATION``, ``INFO_CURRLINE``, ``INFO_ALL`` or any
            bitwise combination. Some overhead is associated with parsing
            extra information.
        :param ponder: Whether the engine should keep analysing in the
            background even after the result has been returned.
        :param root_moves: Optional. Consider only root moves from this list.
        :param options: Optional. A dictionary of engine options for the
            analysis. The previous configuration will be restored after the
            analysis is complete. You can permanently apply a configuration
            with :func:`~chess.engine.Protocol.configure()`.
        """

    @typing.overload
    async def analyse(self, board: chess.Board, limit: Limit, *, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> InfoDict: ...
    @typing.overload
    async def analyse(self, board: chess.Board, limit: Limit, *, multipv: int, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> List[InfoDict]: ...
    @typing.overload
    async def analyse(self, board: chess.Board, limit: Limit, *, multipv: Optional[int] = None, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> Union[List[InfoDict], InfoDict]: ...
    async def analyse(self, board: chess.Board, limit: Limit, *, multipv: Optional[int] = None, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> Union[List[InfoDict], InfoDict]:
        """
        Analyses a position and returns a dictionary of
        :class:`information <chess.engine.InfoDict>`.

        :param board: The position to analyse. The entire move stack will be
            sent to the engine.
        :param limit: An instance of :class:`chess.engine.Limit` that
            determines when to stop the analysis.
        :param multipv: Optional. Analyse multiple root moves. Will return
            a list of at most *multipv* dictionaries rather than just a single
            info dictionary.
        :param game: Optional. An arbitrary object that identifies the game.
            Will automatically inform the engine if the object is not equal
            to the previous game (e.g., ``ucinewgame``, ``new``).
        :param info: Selects which information to retrieve from the
            engine. ``INFO_NONE``, ``INFO_BASE`` (basic information that is
            trivial to obtain), ``INFO_SCORE``, ``INFO_PV``,
            ``INFO_REFUTATION``, ``INFO_CURRLINE``, ``INFO_ALL`` or any
            bitwise combination. Some overhead is associated with parsing
            extra information.
        :param root_moves: Optional. Limit analysis to a list of root moves.
        :param options: Optional. A dictionary of engine options for the
            analysis. The previous configuration will be restored after the
            analysis is complete. You can permanently apply a configuration
            with :func:`~chess.engine.Protocol.configure()`.
        """
        analysis = await self.analysis(board, limit, multipv=multipv, game=game, info=info, root_moves=root_moves, options=options)

        with analysis:
            await analysis.wait()

        return analysis.info if multipv is None else analysis.multipv

    @abc.abstractmethod
    async def analysis(self, board: chess.Board, limit: Optional[Limit] = None, *, multipv: Optional[int] = None, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> AnalysisResult:
        """
        Starts analysing a position.

        :param board: The position to analyse. The entire move stack will be
            sent to the engine.
        :param limit: Optional. An instance of :class:`chess.engine.Limit`
            that determines when to stop the analysis. Analysis is infinite
            by default.
        :param multipv: Optional. Analyse multiple root moves.
        :param game: Optional. An arbitrary object that identifies the game.
            Will automatically inform the engine if the object is not equal
            to the previous game (e.g., ``ucinewgame``, ``new``).
        :param info: Selects which information to retrieve from the
            engine. ``INFO_NONE``, ``INFO_BASE`` (basic information that is
            trivial to obtain), ``INFO_SCORE``, ``INFO_PV``,
            ``INFO_REFUTATION``, ``INFO_CURRLINE``, ``INFO_ALL`` or any
            bitwise combination. Some overhead is associated with parsing
            extra information.
        :param root_moves: Optional. Limit analysis to a list of root moves.
        :param options: Optional. A dictionary of engine options for the
            analysis. The previous configuration will be restored after the
            analysis is complete. You can permanently apply a configuration
            with :func:`~chess.engine.Protocol.configure()`.

        Returns :class:`~chess.engine.AnalysisResult`, a handle that allows
        asynchronously iterating over the information sent by the engine
        and stopping the analysis at any time.
        """

    @abc.abstractmethod
    async def quit(self) -> None:
        """Asks the engine to shut down."""

    @classmethod
    async def popen(cls: Type[ProtocolT], command: Union[str, List[str]], *, setpgrp: bool = False, **kwargs: Any) -> Tuple[asyncio.SubprocessTransport, ProtocolT]:
        if not isinstance(command, list):
            command = [command]

        popen_args = {}
        if setpgrp:
            try:
                # Windows.
                popen_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore
            except AttributeError:
                # Unix.
                popen_args["preexec_fn"] = os.setpgrp
        popen_args.update(kwargs)

        return await asyncio.get_running_loop().subprocess_exec(cls, *command, **popen_args)  # type: ignore


class CommandState(enum.Enum):
    New = 1
    Active = 2
    Cancelling = 3
    Done = 4


class BaseCommand(Generic[ProtocolT, T]):
    def __init__(self) -> None:
        self.state = CommandState.New

        self.result: asyncio.Future[T] = asyncio.Future()
        self.finished: asyncio.Future[None] = asyncio.Future()

    def _engine_terminated(self, engine: ProtocolT, code: int) -> None:
        exc = EngineTerminatedError(f"engine process died unexpectedly (exit code: {code})")
        if self.state == CommandState.Active:
            self.engine_terminated(engine, exc)
        elif self.state == CommandState.Cancelling:
            self.finished.set_result(None)
        elif self.state == CommandState.New:
            self._handle_exception(engine, exc)

    def _handle_exception(self, engine: ProtocolT, exc: Exception) -> None:
        if not self.result.done():
            self.result.set_exception(exc)
        else:
            engine.loop.call_exception_handler({
                "message": f"{type(self).__name__} failed after returning preliminary result ({self.result!r})",
                "exception": exc,
                "protocol": engine,
                "transport": engine.transport,
            })

        if not self.finished.done():
            self.finished.set_result(None)

    def set_finished(self) -> None:
        assert self.state in [CommandState.Active, CommandState.Cancelling]
        if not self.result.done():
            self.result.set_exception(EngineError(f"engine command finished before returning result: {self!r}"))
        self.finished.set_result(None)

    def _cancel(self, engine: ProtocolT) -> None:
        assert self.state == CommandState.Active
        self.state = CommandState.Cancelling
        self.cancel(engine)

    def _start(self, engine: ProtocolT) -> None:
        assert self.state == CommandState.New
        self.state = CommandState.Active
        try:
            self.check_initialized(engine)
            self.start(engine)
        except EngineError as err:
            self._handle_exception(engine, err)

    def _done(self) -> None:
        assert self.state != CommandState.Done
        self.state = CommandState.Done

    def _line_received(self, engine: ProtocolT, line: str) -> None:
        assert self.state in [CommandState.Active, CommandState.Cancelling]
        try:
            self.line_received(engine, line)
        except EngineError as err:
            self._handle_exception(engine, err)

    def cancel(self, engine: ProtocolT) -> None:
        pass

    def check_initialized(self, engine: ProtocolT) -> None:
        if not engine.initialized:
            raise EngineError("tried to run command, but engine is not initialized")

    def start(self, engine: ProtocolT) -> None:
        raise NotImplementedError

    def line_received(self, engine: ProtocolT, line: str) -> None:
        pass

    def engine_terminated(self, engine: ProtocolT, exc: Exception) -> None:
        self._handle_exception(engine, exc)

    def __repr__(self) -> str:
        return "<{} at {:#x} (state={}, result={}, finished={}>".format(type(self).__name__, id(self), self.state, self.result, self.finished)


class UciProtocol(Protocol):
    """
    An implementation of the
    `Universal Chess Interface <https://www.chessprogramming.org/UCI>`_
    protocol.
    """

    def __init__(self) -> None:
        super().__init__()
        self.options: UciOptionMap[Option] = UciOptionMap()
        self.config: UciOptionMap[ConfigValue] = UciOptionMap()
        self.target_config: UciOptionMap[ConfigValue] = UciOptionMap()
        self.id = {}
        self.board = chess.Board()
        self.game: object = None
        self.first_game = True

    async def initialize(self) -> None:
        class UciInitializeCommand(BaseCommand[UciProtocol, None]):
            def check_initialized(self, engine: UciProtocol) -> None:
                if engine.initialized:
                    raise EngineError("engine already initialized")

            def start(self, engine: UciProtocol) -> None:
                engine.send_line("uci")

            def line_received(self, engine: UciProtocol, line: str) -> None:
                if line == "uciok" and not self.result.done():
                    engine.initialized = True
                    self.result.set_result(None)
                    self.set_finished()
                elif line.startswith("option "):
                    self._option(engine, line.split(" ", 1)[1])
                elif line.startswith("id "):
                    self._id(engine, line.split(" ", 1)[1])

            def _option(self, engine: UciProtocol, arg: str) -> None:
                current_parameter = None

                name: List[str] = []
                type: List[str] = []
                default: List[str] = []
                min = None
                max = None
                current_var = None
                var = []

                for token in arg.split(" "):
                    if token == "name" and not name:
                        current_parameter = "name"
                    elif token == "type" and not type:
                        current_parameter = "type"
                    elif token == "default" and not default:
                        current_parameter = "default"
                    elif token == "min" and min is None:
                        current_parameter = "min"
                    elif token == "max" and max is None:
                        current_parameter = "max"
                    elif token == "var":
                        current_parameter = "var"
                        if current_var is not None:
                            var.append(" ".join(current_var))
                        current_var = []
                    elif current_parameter == "name":
                        name.append(token)
                    elif current_parameter == "type":
                        type.append(token)
                    elif current_parameter == "default":
                        default.append(token)
                    elif current_parameter == "var":
                        current_var.append(token)
                    elif current_parameter == "min":
                        try:
                            min = int(token)
                        except ValueError:
                            LOGGER.exception("Exception parsing option min")
                    elif current_parameter == "max":
                        try:
                            max = int(token)
                        except ValueError:
                            LOGGER.exception("Exception parsing option max")

                if current_var is not None:
                    var.append(" ".join(current_var))

                without_default = Option(" ".join(name), " ".join(type), None, min, max, var)
                option = Option(without_default.name, without_default.type, without_default.parse(" ".join(default)), min, max, var)
                engine.options[option.name] = option

                if option.default is not None:
                    engine.config[option.name] = option.default
                if option.default is not None and not option.is_managed() and option.name.lower() != "uci_analysemode":
                    engine.target_config[option.name] = option.default

            def _id(self, engine: UciProtocol, arg: str) -> None:
                key, value = arg.split(" ", 1)
                engine.id[key] = value

        return await self.communicate(UciInitializeCommand)

    def _isready(self) -> None:
        self.send_line("isready")

    def _ucinewgame(self) -> None:
        self.send_line("ucinewgame")
        self.first_game = False

    def debug(self, on: bool = True) -> None:
        """
        Switches debug mode of the engine on or off. This does not interrupt
        other ongoing operations.
        """
        if on:
            self.send_line("debug on")
        else:
            self.send_line("debug off")

    async def ping(self) -> None:
        class UciPingCommand(BaseCommand[UciProtocol, None]):
            def start(self, engine: UciProtocol) -> None:
                engine._isready()

            def line_received(self, engine: UciProtocol, line: str) -> None:
                if line == "readyok":
                    self.result.set_result(None)
                    self.set_finished()
                else:
                    LOGGER.warning("%s: Unexpected engine output: %r", engine, line)

        return await self.communicate(UciPingCommand)

    def _setoption(self, name: str, value: ConfigValue) -> None:
        try:
            value = self.options[name].parse(value)
        except KeyError:
            raise EngineError("engine does not support option {} (available options: {})".format(name, ", ".join(self.options)))

        if value is None or value != self.config.get(name):
            builder = ["setoption name", name]
            if value is False:
                builder.append("value false")
            elif value is True:
                builder.append("value true")
            elif value is not None:
                builder.append("value")
                builder.append(str(value))

            self.send_line(" ".join(builder))
            self.config[name] = value

    def _configure(self, options: ConfigMapping) -> None:
        for name, value in collections.ChainMap(options, self.target_config).items():
            if name.lower() in MANAGED_OPTIONS:
                raise EngineError("cannot set {} which is automatically managed".format(name))
            self._setoption(name, value)

    async def configure(self, options: ConfigMapping) -> None:
        class UciConfigureCommand(BaseCommand[UciProtocol, None]):
            def start(self, engine: UciProtocol) -> None:
                engine._configure(options)
                engine.target_config.update({name: value for name, value in options.items() if value is not None})
                self.result.set_result(None)
                self.set_finished()

        return await self.communicate(UciConfigureCommand)

    def _position(self, board: chess.Board) -> None:
        # Select UCI_Variant and UCI_Chess960.
        uci_variant = type(board).uci_variant
        if "UCI_Variant" in self.options:
            self._setoption("UCI_Variant", uci_variant)
        elif uci_variant != "chess":
            raise EngineError("engine does not support UCI_Variant")

        if "UCI_Chess960" in self.options:
            self._setoption("UCI_Chess960", board.chess960)
        elif board.chess960:
            raise EngineError("engine does not support UCI_Chess960")

        # Send starting position.
        builder = ["position"]
        safe_history = all(board.move_stack)
        root = board.root() if safe_history else board
        fen = root.fen(shredder=board.chess960, en_passant="fen")
        if uci_variant == "chess" and fen == chess.STARTING_FEN:
            builder.append("startpos")
        else:
            builder.append("fen")
            builder.append(fen)

        # Send moves.
        if not safe_history:
            LOGGER.warning("Not transmitting history with null moves to UCI engine")
        elif board.move_stack:
            builder.append("moves")
            builder.extend(move.uci() for move in board.move_stack)

        self.send_line(" ".join(builder))
        self.board = board.copy(stack=False)

    def _go(self, limit: Limit, *, root_moves: Optional[Iterable[chess.Move]] = None, ponder: bool = False, infinite: bool = False) -> None:
        builder = ["go"]
        if ponder:
            builder.append("ponder")
        if limit.white_clock is not None:
            builder.append("wtime")
            builder.append(str(max(1, int(limit.white_clock * 1000))))
        if limit.black_clock is not None:
            builder.append("btime")
            builder.append(str(max(1, int(limit.black_clock * 1000))))
        if limit.white_inc is not None:
            builder.append("winc")
            builder.append(str(int(limit.white_inc * 1000)))
        if limit.black_inc is not None:
            builder.append("binc")
            builder.append(str(int(limit.black_inc * 1000)))
        if limit.remaining_moves is not None and int(limit.remaining_moves) > 0:
            builder.append("movestogo")
            builder.append(str(int(limit.remaining_moves)))
        if limit.depth is not None:
            builder.append("depth")
            builder.append(str(max(1, int(limit.depth))))
        if limit.nodes is not None:
            builder.append("nodes")
            builder.append(str(max(1, int(limit.nodes))))
        if limit.mate is not None:
            builder.append("mate")
            builder.append(str(max(1, int(limit.mate))))
        if limit.time is not None:
            builder.append("movetime")
            builder.append(str(max(1, int(limit.time * 1000))))
        if infinite:
            builder.append("infinite")
        if root_moves is not None:
            builder.append("searchmoves")
            if root_moves:
                builder.extend(move.uci() for move in root_moves)
            else:
                # Work around searchmoves followed by nothing.
                builder.append("0000")
        self.send_line(" ".join(builder))

    async def play(self, board: chess.Board, limit: Limit, *, game: object = None, info: Info = INFO_NONE, ponder: bool = False, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> PlayResult:
        class UciPlayCommand(BaseCommand[UciProtocol, PlayResult]):
            def start(self, engine: UciProtocol) -> None:
                self.info: InfoDict = {}
                self.pondering = False
                self.sent_isready = False

                if "UCI_AnalyseMode" in engine.options and "UCI_AnalyseMode" not in engine.target_config and all(name.lower() != "uci_analysemode" for name in options):
                    engine._setoption("UCI_AnalyseMode", False)
                if "Ponder" in engine.options:
                    engine._setoption("Ponder", ponder)
                if "MultiPV" in engine.options:
                    engine._setoption("MultiPV", engine.options["MultiPV"].default)

                engine._configure(options)

                if engine.first_game or engine.game != game:
                    engine.game = game
                    engine._ucinewgame()
                    self.sent_isready = True
                    engine._isready()
                else:
                    self._readyok(engine)

            def line_received(self, engine: UciProtocol, line: str) -> None:
                if line.startswith("info "):
                    self._info(engine, line.split(" ", 1)[1])
                elif line.startswith("bestmove "):
                    self._bestmove(engine, line.split(" ", 1)[1])
                elif line == "readyok" and self.sent_isready:
                    self._readyok(engine)
                else:
                    LOGGER.warning("%s: Unexpected engine output: %r", engine, line)

            def _readyok(self, engine: UciProtocol) -> None:
                self.sent_isready = False
                engine._position(board)
                engine._go(limit, root_moves=root_moves)

            def _info(self, engine: UciProtocol, arg: str) -> None:
                if not self.pondering:
                    self.info.update(_parse_uci_info(arg, engine.board, info))

            def _bestmove(self, engine: UciProtocol, arg: str) -> None:
                if self.pondering:
                    self.pondering = False
                elif not self.result.cancelled():
                    best = _parse_uci_bestmove(engine.board, arg)
                    self.result.set_result(PlayResult(best.move, best.ponder, self.info))

                    if ponder and best.move and best.ponder:
                        self.pondering = True
                        engine.board.push(best.move)
                        engine.board.push(best.ponder)
                        engine._position(engine.board)
                        engine._go(limit, ponder=True)

                if not self.pondering:
                    self.end(engine)

            def end(self, engine: UciProtocol) -> None:
                self.set_finished()

            def cancel(self, engine: UciProtocol) -> None:
                engine.send_line("stop")

            def engine_terminated(self, engine: UciProtocol, exc: Exception) -> None:
                # Allow terminating engine while pondering.
                if not self.result.done():
                    super().engine_terminated(engine, exc)

        return await self.communicate(UciPlayCommand)

    async def analysis(self, board: chess.Board, limit: Optional[Limit] = None, *, multipv: Optional[int] = None, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> AnalysisResult:
        class UciAnalysisCommand(BaseCommand[UciProtocol, AnalysisResult]):
            def start(self, engine: UciProtocol) -> None:
                self.analysis = AnalysisResult(stop=lambda: self.cancel(engine))
                self.sent_isready = False

                if "UCI_AnalyseMode" in engine.options and "UCI_AnalyseMode" not in engine.target_config and all(name.lower() != "uci_analysemode" for name in options):
                    engine._setoption("UCI_AnalyseMode", True)
                if "MultiPV" in engine.options or (multipv and multipv > 1):
                    engine._setoption("MultiPV", 1 if multipv is None else multipv)

                engine._configure(options)

                if engine.first_game or engine.game != game:
                    engine.game = game
                    engine._ucinewgame()
                    self.sent_isready = True
                    engine._isready()
                else:
                    self._readyok(engine)

            def line_received(self, engine: UciProtocol, line: str) -> None:
                if line.startswith("info "):
                    self._info(engine, line.split(" ", 1)[1])
                elif line.startswith("bestmove "):
                    self._bestmove(engine, line.split(" ", 1)[1])
                elif line == "readyok" and self.sent_isready:
                    self._readyok(engine)
                else:
                    LOGGER.warning("%s: Unexpected engine output: %r", engine, line)

            def _readyok(self, engine: UciProtocol) -> None:
                self.sent_isready = False
                engine._position(board)

                if limit:
                    engine._go(limit, root_moves=root_moves)
                else:
                    engine._go(Limit(), root_moves=root_moves, infinite=True)

                self.result.set_result(self.analysis)

            def _info(self, engine: UciProtocol, arg: str) -> None:
                self.analysis.post(_parse_uci_info(arg, engine.board, info))

            def _bestmove(self, engine: UciProtocol, arg: str) -> None:
                if not self.result.done():
                    raise EngineError("was not searching, but engine sent bestmove")
                best = _parse_uci_bestmove(engine.board, arg)
                self.set_finished()
                self.analysis.set_finished(best)

            def cancel(self, engine: UciProtocol) -> None:
                engine.send_line("stop")

            def engine_terminated(self, engine: UciProtocol, exc: Exception) -> None:
                LOGGER.debug("%s: Closing analysis because engine has been terminated (error: %s)", engine, exc)
                self.analysis.set_exception(exc)

        return await self.communicate(UciAnalysisCommand)

    async def quit(self) -> None:
        self.send_line("quit")
        await asyncio.shield(self.returncode)


UCI_REGEX = re.compile(r"^[a-h][1-8][a-h][1-8][pnbrqk]?|[PNBRQK]@[a-h][1-8]|0000\Z")

def _parse_uci_info(arg: str, root_board: chess.Board, selector: Info = INFO_ALL) -> InfoDict:
    info: InfoDict = {}
    if not selector:
        return info

    tokens = arg.split(" ")
    while tokens:
        parameter = tokens.pop(0)

        if parameter == "string":
            info["string"] = " ".join(tokens)
            break
        elif parameter in ["depth", "seldepth", "nodes", "multipv", "currmovenumber", "hashfull", "nps", "tbhits", "cpuload"]:
            try:
                info[parameter] = int(tokens.pop(0))  # type: ignore
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing %s from info: %r", parameter, arg)
        elif parameter == "time":
            try:
                info["time"] = int(tokens.pop(0)) / 1000.0
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing %s from info: %r", parameter, arg)
        elif parameter == "ebf":
            try:
                info["ebf"] = float(tokens.pop(0))
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing %s from info: %r", parameter, arg)
        elif parameter == "score" and selector & INFO_SCORE:
            try:
                kind = tokens.pop(0)
                value = tokens.pop(0)
                if tokens and tokens[0] in ["lowerbound", "upperbound"]:
                    info[tokens.pop(0)] = True  # type: ignore
                if kind == "cp":
                    info["score"] = PovScore(Cp(int(value)), root_board.turn)
                elif kind == "mate":
                    info["score"] = PovScore(Mate(int(value)), root_board.turn)
                else:
                    LOGGER.error("Unknown score kind %r in info (expected cp or mate): %r", kind, arg)
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing score from info: %r", arg)
        elif parameter == "currmove":
            try:
                info["currmove"] = chess.Move.from_uci(tokens.pop(0))
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing currmove from info: %r", arg)
        elif parameter == "currline" and selector & INFO_CURRLINE:
            try:
                if "currline" not in info:
                    info["currline"] = {}

                cpunr = int(tokens.pop(0))
                currline: List[chess.Move] = []
                info["currline"][cpunr] = currline

                board = root_board.copy(stack=False)
                while tokens and UCI_REGEX.match(tokens[0]):
                    currline.append(board.push_uci(tokens.pop(0)))
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing currline from info: %r, position at root: %s", arg, root_board.fen())
        elif parameter == "refutation" and selector & INFO_REFUTATION:
            try:
                if "refutation" not in info:
                    info["refutation"] = {}

                board = root_board.copy(stack=False)
                refuted = board.push_uci(tokens.pop(0))

                refuted_by: List[chess.Move] = []
                info["refutation"][refuted] = refuted_by

                while tokens and UCI_REGEX.match(tokens[0]):
                    refuted_by.append(board.push_uci(tokens.pop(0)))
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing refutation from info: %r, position at root: %s", arg, root_board.fen())
        elif parameter == "pv" and selector & INFO_PV:
            try:
                pv: List[chess.Move] = []
                info["pv"] = pv
                board = root_board.copy(stack=False)
                while tokens and UCI_REGEX.match(tokens[0]):
                    pv.append(board.push_uci(tokens.pop(0)))
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing pv from info: %r, position at root: %s", arg, root_board.fen())
        elif parameter == "wdl":
            try:
                info["wdl"] = PovWdl(Wdl(int(tokens.pop(0)), int(tokens.pop(0)), int(tokens.pop(0))), root_board.turn)
            except (ValueError, IndexError):
                LOGGER.error("Exception parsing wdl from info: %r", arg)

    return info

def _parse_uci_bestmove(board: chess.Board, args: str) -> BestMove:
    tokens = args.split(None, 2)

    move = None
    ponder = None

    if tokens[0] not in ["(none)", "NULL"]:
        try:
            # AnMon 5.75 uses uppercase letters to denote promotion types.
            move = board.push_uci(tokens[0].lower())
        except ValueError as err:
            raise EngineError(err)

        try:
            # Houdini 1.5 sends NULL instead of skipping the token.
            if len(tokens) >= 3 and tokens[1] == "ponder" and tokens[2] not in ["(none)", "NULL"]:
                ponder = board.parse_uci(tokens[2].lower())
        except ValueError:
            LOGGER.exception("Engine sent invalid ponder move")
        finally:
            board.pop()

    return BestMove(move, ponder)


class UciOptionMap(MutableMapping[str, T]):
    """Dictionary with case-insensitive keys."""

    def __init__(self, data: Optional[Union[Iterable[Tuple[str, T]]]] = None, **kwargs: T) -> None:
        self._store: Dict[str, Tuple[str, T]] = {}
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key: str, value: T) -> None:
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key: str) -> T:
        return self._store[key.lower()][1]

    def __delitem__(self, key: str) -> None:
        del self._store[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def __eq__(self, other: object) -> bool:
        try:
            for key, value in self.items():
                if key not in other or other[key] != value:  # type: ignore
                    return False

            for key, value in other.items():  # type: ignore
                if key not in self or self[key] != value:
                    return False

            return True
        except (TypeError, AttributeError):
            return NotImplemented

    def copy(self) -> UciOptionMap[T]:
        return type(self)(self._store.values())

    def __copy__(self) -> UciOptionMap[T]:
        return self.copy()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({dict(self.items())!r})"


XBOARD_ERROR_REGEX = re.compile(r"^\s*(Error|Illegal move)(\s*\([^()]+\))?\s*:")


class XBoardProtocol(Protocol):
    """
    An implementation of the
    `XBoard protocol <http://hgm.nubati.net/CECP.html>`_ (CECP).
    """

    def __init__(self) -> None:
        super().__init__()
        self.features: Dict[str, Union[int, str]] = {}
        self.id = {}
        self.options = {
            "random": Option("random", "check", False, None, None, None),
            "computer": Option("computer", "check", False, None, None, None),
        }
        self.config: Dict[str, ConfigValue] = {}
        self.target_config: Dict[str, ConfigValue] = {}
        self.board = chess.Board()
        self.game: object = None
        self.first_game = True

    async def initialize(self) -> None:
        class XBoardInitializeCommand(BaseCommand[XBoardProtocol, None]):
            def check_initialized(self, engine: XBoardProtocol) -> None:
                if engine.initialized:
                    raise EngineError("engine already initialized")

            def start(self, engine: XBoardProtocol) -> None:
                engine.send_line("xboard")
                engine.send_line("protover 2")
                self.timeout_handle = engine.loop.call_later(2.0, lambda: self.timeout(engine))

            def timeout(self, engine: XBoardProtocol) -> None:
                LOGGER.error("%s: Timeout during initialization", engine)
                self.end(engine)

            def line_received(self, engine: XBoardProtocol, line: str) -> None:
                if line.startswith("#"):
                    pass
                elif line.startswith("feature "):
                    self._feature(engine, line.split(" ", 1)[1])
                elif XBOARD_ERROR_REGEX.match(line):
                    raise EngineError(line)

            def _feature(self, engine: XBoardProtocol, arg: str) -> None:
                for feature in shlex.split(arg):
                    key, value = feature.split("=", 1)
                    if key == "option":
                        option = _parse_xboard_option(value)
                        if option.name not in ["random", "computer", "cores", "memory"]:
                            engine.options[option.name] = option
                    else:
                        try:
                            engine.features[key] = int(value)
                        except ValueError:
                            engine.features[key] = value

                if "done" in engine.features:
                    self.timeout_handle.cancel()
                if engine.features.get("done"):
                    self.end(engine)

            def end(self, engine: XBoardProtocol) -> None:
                if not engine.features.get("ping", 0):
                    self.result.set_exception(EngineError("xboard engine did not declare required feature: ping"))
                    self.set_finished()
                    return
                if not engine.features.get("setboard", 0):
                    self.result.set_exception(EngineError("xboard engine did not declare required feature: setboard"))
                    self.set_finished()
                    return

                if not engine.features.get("reuse", 1):
                    LOGGER.warning("%s: Rejecting feature reuse=0", engine)
                    engine.send_line("rejected reuse")
                if not engine.features.get("sigterm", 1):
                    LOGGER.warning("%s: Rejecting feature sigterm=0", engine)
                    engine.send_line("rejected sigterm")
                if engine.features.get("usermove", 0):
                    LOGGER.warning("%s: Rejecting feature usermove=1", engine)
                    engine.send_line("rejected usermove")
                if engine.features.get("san", 0):
                    LOGGER.warning("%s: Rejecting feature san=1", engine)
                    engine.send_line("rejected san")

                if "myname" in engine.features:
                    engine.id["name"] = str(engine.features["myname"])

                if engine.features.get("memory", 0):
                    engine.options["memory"] = Option("memory", "spin", 16, 1, None, None)
                    engine.send_line("accepted memory")
                if engine.features.get("smp", 0):
                    engine.options["cores"] = Option("cores", "spin", 1, 1, None, None)
                    engine.send_line("accepted smp")
                if engine.features.get("egt"):
                    for egt in str(engine.features["egt"]).split(","):
                        name = f"egtpath {egt}"
                        engine.options[name] = Option(name, "path", None, None, None, None)
                    engine.send_line("accepted egt")

                for option in engine.options.values():
                    if option.default is not None:
                        engine.config[option.name] = option.default
                    if option.default is not None and not option.is_managed():
                        engine.target_config[option.name] = option.default

                engine.initialized = True
                self.result.set_result(None)
                self.set_finished()

        return await self.communicate(XBoardInitializeCommand)

    def _ping(self, n: int) -> None:
        self.send_line(f"ping {n}")

    def _variant(self, variant: Optional[str]) -> None:
        variants = str(self.features.get("variants", "")).split(",")
        if not variant or variant not in variants:
            raise EngineError("unsupported xboard variant: {} (available: {})".format(variant, ", ".join(variants)))

        self.send_line(f"variant {variant}")

    def _new(self, board: chess.Board, game: object, options: ConfigMapping) -> None:
        self._configure(options)

        # Set up starting position.
        root = board.root()
        new_options = "random" in options or "computer" in options
        new_game = self.first_game or self.game != game or new_options or root != self.board.root()
        self.game = game
        self.first_game = False
        if new_game:
            self.board = root
            self.send_line("new")

            variant = type(board).xboard_variant
            if variant == "normal" and board.chess960:
                self._variant("fischerandom")
            elif variant != "normal":
                self._variant(variant)

            if self.config.get("random"):
                self.send_line("random")
            if self.config.get("computer"):
                self.send_line("computer")

        self.send_line("force")

        if new_game:
            fen = root.fen(shredder=board.chess960, en_passant="fen")
            if variant != "normal" or fen != chess.STARTING_FEN or board.chess960:
                self.send_line(f"setboard {fen}")

        # Undo moves until common position.
        common_stack_len = 0
        if not new_game:
            for left, right in zip(self.board.move_stack, board.move_stack):
                if left == right:
                    common_stack_len += 1
                else:
                    break

            while len(self.board.move_stack) > common_stack_len + 1:
                self.send_line("remove")
                self.board.pop()
                self.board.pop()

            while len(self.board.move_stack) > common_stack_len:
                self.send_line("undo")
                self.board.pop()

        # Play moves from board stack.
        for move in board.move_stack[common_stack_len:]:
            if not move:
                LOGGER.warning("Null move (in %s) may not be supported by all XBoard engines", self.board.fen())
            self.send_line(self.board.xboard(move))
            self.board.push(move)

    async def ping(self) -> None:
        class XBoardPingCommand(BaseCommand[XBoardProtocol, None]):
            def start(self, engine: XBoardProtocol) -> None:
                n = id(self) & 0xffff
                self.pong = f"pong {n}"
                engine._ping(n)

            def line_received(self, engine: XBoardProtocol, line: str) -> None:
                if line == self.pong:
                    self.result.set_result(None)
                    self.set_finished()
                elif not line.startswith("#"):
                    LOGGER.warning("%s: Unexpected engine output: %r", engine, line)
                elif XBOARD_ERROR_REGEX.match(line):
                    raise EngineError(line)

        return await self.communicate(XBoardPingCommand)

    async def play(self, board: chess.Board, limit: Limit, *, game: object = None, info: Info = INFO_NONE, ponder: bool = False, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> PlayResult:
        if root_moves is not None:
            raise EngineError("play with root_moves, but xboard supports 'include' only in analysis mode")

        class XBoardPlayCommand(BaseCommand[XBoardProtocol, PlayResult]):
            def start(self, engine: XBoardProtocol) -> None:
                self.play_result = PlayResult(None, None)
                self.stopped = False
                self.pong_after_move: Optional[str] = None
                self.pong_after_ponder: Optional[str] = None

                # Set game, position and configure.
                engine._new(board, game, options)

                # Limit or time control.
                increment = limit.white_inc if board.turn else limit.black_inc
                if limit.remaining_moves or increment:
                    base_mins, base_secs = divmod(int((limit.white_clock if board.turn else limit.black_clock) or 0), 60)
                    engine.send_line(f"level {limit.remaining_moves or 0} {base_mins}:{base_secs:02d} {increment}")

                if limit.nodes is not None:
                    if limit.time is not None or limit.white_clock is not None or limit.black_clock is not None or increment is not None:
                        raise EngineError("xboard does not support mixing node limits with time limits")

                    if "nps" not in engine.features:
                        LOGGER.warning("%s: Engine did not declare explicit support for node limits (feature nps=?)")
                    elif not engine.features["nps"]:
                        raise EngineError("xboard engine does not support node limits (feature nps=0)")

                    engine.send_line("nps 1")
                    engine.send_line(f"st {max(1, int(limit.nodes))}")
                if limit.depth is not None:
                    engine.send_line(f"sd {max(1, int(limit.depth))}")
                if limit.time is not None:
                    engine.send_line(f"st {max(0.01, limit.time)}")
                if limit.white_clock is not None:
                    engine.send_line("{} {}".format("time" if board.turn else "otim", max(1, int(limit.white_clock * 100))))
                if limit.black_clock is not None:
                    engine.send_line("{} {}".format("otim" if board.turn else "time", max(1, int(limit.black_clock * 100))))

                # Start thinking.
                engine.send_line("post" if info else "nopost")
                engine.send_line("hard" if ponder else "easy")
                engine.send_line("go")

            def line_received(self, engine: XBoardProtocol, line: str) -> None:
                if line.startswith("move "):
                    self._move(engine, line.split(" ", 1)[1])
                elif line.startswith("Hint: "):
                    self._hint(engine, line.split(" ", 1)[1])
                elif line == self.pong_after_move:
                    if not self.result.done():
                        self.result.set_result(self.play_result)
                    if not ponder:
                        self.set_finished()
                elif line == self.pong_after_ponder:
                    if not self.result.done():
                        self.result.set_result(self.play_result)
                    self.set_finished()
                elif line == "offer draw":
                    if not self.result.done():
                        self.play_result.draw_offered = True
                    self._ping_after_move(engine)
                elif line == "resign":
                    if not self.result.done():
                        self.play_result.resigned = True
                    self._ping_after_move(engine)
                elif line.startswith("1-0") or line.startswith("0-1") or line.startswith("1/2-1/2"):
                    self._ping_after_move(engine)
                elif line.startswith("#"):
                    pass
                elif XBOARD_ERROR_REGEX.match(line):
                    engine.first_game = True  # Board state might no longer be in sync
                    raise EngineError(line)
                elif len(line.split()) >= 4 and line.lstrip()[0].isdigit():
                    self._post(engine, line)
                else:
                    LOGGER.warning("%s: Unexpected engine output: %r", engine, line)

            def _post(self, engine: XBoardProtocol, line: str) -> None:
                if not self.result.done():
                    self.play_result.info = _parse_xboard_post(line, engine.board, info)

            def _move(self, engine: XBoardProtocol, arg: str) -> None:
                if not self.result.done() and self.play_result.move is None:
                    try:
                        self.play_result.move = engine.board.push_xboard(arg)
                    except ValueError as err:
                        self.result.set_exception(EngineError(err))
                    else:
                        self._ping_after_move(engine)
                else:
                    try:
                        engine.board.push_xboard(arg)
                    except ValueError:
                        LOGGER.exception("Exception playing unexpected move")

            def _hint(self, engine: XBoardProtocol, arg: str) -> None:
                if not self.result.done() and self.play_result.move is not None and self.play_result.ponder is None:
                    try:
                        self.play_result.ponder = engine.board.parse_xboard(arg)
                    except ValueError:
                        LOGGER.exception("Exception parsing hint")
                else:
                    LOGGER.warning("Unexpected hint: %r", arg)

            def _ping_after_move(self, engine: XBoardProtocol) -> None:
                if self.pong_after_move is None:
                    n = id(self) & 0xffff
                    self.pong_after_move = f"pong {n}"
                    engine._ping(n)

            def cancel(self, engine: XBoardProtocol) -> None:
                if self.stopped:
                    return
                self.stopped = True

                if self.result.cancelled():
                    engine.send_line("?")

                if ponder:
                    engine.send_line("easy")

                    n = (id(self) + 1) & 0xffff
                    self.pong_after_ponder = f"pong {n}"
                    engine._ping(n)

            def engine_terminated(self, engine: XBoardProtocol, exc: Exception) -> None:
                # Allow terminating engine while pondering.
                if not self.result.done():
                    super().engine_terminated(engine, exc)

        return await self.communicate(XBoardPlayCommand)

    async def analysis(self, board: chess.Board, limit: Optional[Limit] = None, *, multipv: Optional[int] = None, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> AnalysisResult:
        if multipv is not None:
            raise EngineError("xboard engine does not support multipv")

        if limit is not None and (limit.white_clock is not None or limit.black_clock is not None):
            raise EngineError("xboard analysis does not support clock limits")

        class XBoardAnalysisCommand(BaseCommand[XBoardProtocol, AnalysisResult]):
            def start(self, engine: XBoardProtocol) -> None:
                self.stopped = False
                self.best_move: Optional[chess.Move] = None
                self.analysis = AnalysisResult(stop=lambda: self.cancel(engine))
                self.final_pong: Optional[str] = None

                engine._new(board, game, options)

                if root_moves is not None:
                    if not engine.features.get("exclude", 0):
                        raise EngineError("xboard engine does not support root_moves (feature exclude=0)")

                    engine.send_line("exclude all")
                    for move in root_moves:
                        engine.send_line(f"include {engine.board.xboard(move)}")

                engine.send_line("post")
                engine.send_line("analyze")

                self.result.set_result(self.analysis)

                if limit is not None and limit.time is not None:
                    self.time_limit_handle: Optional[asyncio.Handle] = engine.loop.call_later(limit.time, lambda: self.cancel(engine))
                else:
                    self.time_limit_handle = None

            def line_received(self, engine: XBoardProtocol, line: str) -> None:
                if line.startswith("#"):
                    pass
                elif len(line.split()) >= 4 and line.lstrip()[0].isdigit():
                    self._post(engine, line)
                elif line == self.final_pong:
                    self.end(engine)
                elif XBOARD_ERROR_REGEX.match(line):
                    engine.first_game = True  # Board state might no longer be in sync
                    raise EngineError(line)
                else:
                    LOGGER.warning("%s: Unexpected engine output: %r", engine, line)

            def _post(self, engine: XBoardProtocol, line: str) -> None:
                post_info = _parse_xboard_post(line, engine.board, info)
                self.analysis.post(post_info)

                pv = post_info.get("pv")
                if pv:
                    self.best_move = pv[0]

                if limit is not None:
                    if limit.time is not None and post_info.get("time", 0) >= limit.time:
                        self.cancel(engine)
                    elif limit.nodes is not None and post_info.get("nodes", 0) >= limit.nodes:
                        self.cancel(engine)
                    elif limit.depth is not None and post_info.get("depth", 0) >= limit.depth:
                        self.cancel(engine)
                    elif limit.mate is not None and "score" in post_info:
                        if post_info["score"].relative >= Mate(limit.mate):
                            self.cancel(engine)

            def end(self, engine: XBoardProtocol) -> None:
                if self.time_limit_handle:
                    self.time_limit_handle.cancel()

                self.set_finished()
                self.analysis.set_finished(BestMove(self.best_move, None))

            def cancel(self, engine: XBoardProtocol) -> None:
                if self.stopped:
                    return
                self.stopped = True

                engine.send_line(".")
                engine.send_line("exit")

                n = id(self) & 0xffff
                self.final_pong = f"pong {n}"
                engine._ping(n)

            def engine_terminated(self, engine: XBoardProtocol, exc: Exception) -> None:
                LOGGER.debug("%s: Closing analysis because engine has been terminated (error: %s)", engine, exc)

                if self.time_limit_handle:
                    self.time_limit_handle.cancel()

                self.analysis.set_exception(exc)

        return await self.communicate(XBoardAnalysisCommand)

    def _setoption(self, name: str, value: ConfigValue) -> None:
        if value is not None and value == self.config.get(name):
            return

        try:
            option = self.options[name]
        except KeyError:
            raise EngineError(f"unsupported xboard option or command: {name}")

        self.config[name] = value = option.parse(value)

        if name in ["random", "computer"]:
            # Applied in _new.
            pass
        elif name in ["memory", "cores"] or name.startswith("egtpath "):
            self.send_line(f"{name} {value}")
        elif value is None:
            self.send_line(f"option {name}")
        elif value is True:
            self.send_line(f"option {name}=1")
        elif value is False:
            self.send_line(f"option {name}=0")
        else:
            self.send_line(f"option {name}={value}")

    def _configure(self, options: ConfigMapping) -> None:
        for name, value in collections.ChainMap(options, self.target_config).items():
            if name.lower() in MANAGED_OPTIONS:
                raise EngineError(f"cannot set {name} which is automatically managed")
            self._setoption(name, value)

    async def configure(self, options: ConfigMapping) -> None:
        class XBoardConfigureCommand(BaseCommand[XBoardProtocol, None]):
            def start(self, engine: XBoardProtocol) -> None:
                engine._configure(options)
                engine.target_config.update({name: value for name, value in options.items() if value is not None})
                self.result.set_result(None)
                self.set_finished()

        return await self.communicate(XBoardConfigureCommand)

    async def quit(self) -> None:
        self.send_line("quit")
        await asyncio.shield(self.returncode)


def _parse_xboard_option(feature: str) -> Option:
    params = feature.split()

    name = params[0]
    type = params[1][1:]
    default: Optional[ConfigValue] = None
    min = None
    max = None
    var = None

    if type == "combo":
        var = []
        choices = params[2:]
        for choice in choices:
            if choice == "///":
                continue
            elif choice[0] == "*":
                default = choice[1:]
                var.append(choice[1:])
            else:
                var.append(choice)
    elif type == "check":
        default = int(params[2])
    elif type in ["string", "file", "path"]:
        if len(params) > 2:
            default = params[2]
        else:
            default = ""
    elif type == "spin":
        default = int(params[2])
        min = int(params[3])
        max = int(params[4])

    return Option(name, type, default, min, max, var)


def _parse_xboard_post(line: str, root_board: chess.Board, selector: Info = INFO_ALL) -> InfoDict:
    # Format: depth score time nodes [seldepth [nps [tbhits]]] pv
    info: InfoDict = {}

    # Split leading integer tokens from pv.
    pv_tokens = line.split()
    integer_tokens = []
    while pv_tokens:
        token = pv_tokens.pop(0)
        try:
            integer_tokens.append(int(token))
        except ValueError:
            pv_tokens.insert(0, token)
            break

    if len(integer_tokens) < 4:
        return info

    # Required integer tokens.
    info["depth"] = integer_tokens.pop(0)
    cp = integer_tokens.pop(0)
    info["time"] = int(integer_tokens.pop(0)) / 100
    info["nodes"] = int(integer_tokens.pop(0))

    # Score.
    if cp <= -100000:
        score: Score = Mate(cp + 100000)
    elif cp == 100000:
        score = MateGiven
    elif cp >= 100000:
        score = Mate(cp - 100000)
    else:
        score = Cp(cp)
    info["score"] = PovScore(score, root_board.turn)

    # Optional integer tokens.
    if integer_tokens:
        info["seldepth"] = integer_tokens.pop(0)
    if integer_tokens:
        info["nps"] = integer_tokens.pop(0)

    while len(integer_tokens) > 1:
        # Reserved for future extensions.
        integer_tokens.pop(0)

    if integer_tokens:
        info["tbhits"] = integer_tokens.pop(0)

    # Principal variation.
    pv = []
    board = root_board.copy(stack=False)
    for token in pv_tokens:
        if token.rstrip(".").isdigit():
            continue

        try:
            pv.append(board.push_xboard(token))
        except ValueError:
            break

        if not (selector & INFO_PV):
            break
    info["pv"] = pv

    return info


class BestMove:
    """Returned by :func:`chess.engine.AnalysisResult.wait()`."""

    move: Optional[chess.Move]
    """The best move according to the engine, or ``None``."""

    ponder: Optional[chess.Move]
    """The response that the engine expects after *move*, or ``None``."""

    def __init__(self, move: Optional[chess.Move], ponder: Optional[chess.Move]):
        self.move = move
        self.ponder = ponder

    def __repr__(self) -> str:
        return "<{} at {:#x} (move={}, ponder={}>".format(
            type(self).__name__, id(self), self.move, self.ponder)


class AnalysisResult:
    """
    Handle to ongoing engine analysis.
    Returned by :func:`chess.engine.Protocol.analysis()`.

    Can be used to asynchronously iterate over information sent by the engine.

    Automatically stops the analysis when used as a context manager.
    """

    multipv: List[chess.engine.InfoDict]
    """
    A list of dictionaries with aggregated information sent by the engine.
    One item for each root move.
    """

    def __init__(self, stop: Optional[Callable[[], None]] = None):
        self._stop = stop
        self._queue: asyncio.Queue[InfoDict] = asyncio.Queue()
        self._posted_kork = False
        self._seen_kork = False
        self._finished: asyncio.Future[BestMove] = asyncio.Future()
        self.multipv = [{}]

    def post(self, info: InfoDict) -> None:
        # Empty dictionary reserved for kork.
        if not info:
            return

        multipv = info.get("multipv", 1)
        while len(self.multipv) < multipv:
            self.multipv.append({})
        self.multipv[multipv - 1].update(info)

        self._queue.put_nowait(info)

    def _kork(self) -> None:
        if not self._posted_kork:
            self._posted_kork = True
            self._queue.put_nowait({})

    def set_finished(self, best: BestMove) -> None:
        if not self._finished.done():
            self._finished.set_result(best)
        self._kork()

    def set_exception(self, exc: Exception) -> None:
        self._finished.set_exception(exc)
        self._kork()

    @property
    def info(self) -> InfoDict:
        """
        A dictionary of aggregated information sent by the engine. This is
        actually an alias for ``multipv[0]``.
        """
        return self.multipv[0]

    def stop(self) -> None:
        """Stops the analysis as soon as possible."""
        if self._stop and not self._posted_kork:
            self._stop()
            self._stop = None

    async def wait(self) -> BestMove:
        """Waits until the analysis is complete (or stopped)."""
        return await self._finished

    async def get(self) -> InfoDict:
        """
        Waits for the next dictionary of information from the engine and
        returns it.

        It might be more convenient to use ``async for info in analysis: ...``.

        :raises: :exc:`chess.engine.AnalysisComplete` if the analysis is
            complete (or has been stopped) and all information has been
            consumed. Use :func:`~chess.engine.AnalysisResult.next()` if you
            prefer to get ``None`` instead of an exception.
        """
        if self._seen_kork:
            raise AnalysisComplete()

        info = await self._queue.get()
        if not info:
            # Empty dictionary marks end.
            self._seen_kork = True
            await self._finished
            raise AnalysisComplete()

        return info

    def empty(self) -> bool:
        """
        Checks if all information has been consumed.

        If the queue is empty, but the analysis is still ongoing, then further
        information can become available in the future.

        If the queue is not empty, then the next call to
        :func:`~chess.engine.AnalysisResult.get()` will return instantly.
        """
        return self._seen_kork or self._queue.qsize() <= self._posted_kork

    async def next(self) -> Optional[InfoDict]:
        try:
            return await self.get()
        except AnalysisComplete:
            return None

    def __aiter__(self) -> AnalysisResult:
        return self

    async def __anext__(self) -> InfoDict:
        try:
            return await self.get()
        except AnalysisComplete:
            raise StopAsyncIteration

    def __enter__(self) -> AnalysisResult:
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.stop()


async def popen_uci(command: Union[str, List[str]], *, setpgrp: bool = False, **popen_args: Any) -> Tuple[asyncio.SubprocessTransport, UciProtocol]:
    """
    Spawns and initializes a UCI engine.

    :param command: Path of the engine executable, or a list including the
        path and arguments.
    :param setpgrp: Open the engine process in a new process group. This will
        stop signals (such as keyboard interrupts) from propagating from the
        parent process. Defaults to ``False``.
    :param popen_args: Additional arguments for
        `popen <https://docs.python.org/3/library/subprocess.html#popen-constructor>`_.
        Do not set ``stdin``, ``stdout``, ``bufsize`` or
        ``universal_newlines``.

    Returns a subprocess transport and engine protocol pair.
    """
    transport, protocol = await UciProtocol.popen(command, setpgrp=setpgrp, **popen_args)
    try:
        await protocol.initialize()
    except:
        transport.close()
        raise
    return transport, protocol


async def popen_xboard(command: Union[str, List[str]], *, setpgrp: bool = False, **popen_args: Any) -> Tuple[asyncio.SubprocessTransport, XBoardProtocol]:
    """
    Spawns and initializes an XBoard engine.

    :param command: Path of the engine executable, or a list including the
        path and arguments.
    :param setpgrp: Open the engine process in a new process group. This will
        stop signals (such as keyboard interrupts) from propagating from the
        parent process. Defaults to ``False``.
    :param popen_args: Additional arguments for
        `popen <https://docs.python.org/3/library/subprocess.html#popen-constructor>`_.
        Do not set ``stdin``, ``stdout``, ``bufsize`` or
        ``universal_newlines``.

    Returns a subprocess transport and engine protocol pair.
    """
    transport, protocol = await XBoardProtocol.popen(command, setpgrp=setpgrp, **popen_args)
    try:
        await protocol.initialize()
    except:
        transport.close()
        raise
    return transport, protocol


class SimpleEngine:
    """
    Synchronous wrapper around a transport and engine protocol pair. Provides
    the same methods and attributes as :class:`chess.engine.Protocol`
    with blocking functions instead of coroutines.

    You may not concurrently modify objects passed to any of the methods. Other
    than that, :class:`~chess.engine.SimpleEngine` is thread-safe. When sending
    a new command to the engine, any previous running command will be cancelled
    as soon as possible.

    Methods will raise :class:`asyncio.TimeoutError` if an operation takes
    *timeout* seconds longer than expected (unless *timeout* is ``None``).

    Automatically closes the transport when used as a context manager.
    """

    def __init__(self, transport: asyncio.SubprocessTransport, protocol: Protocol, *, timeout: Optional[float] = 10.0) -> None:
        self.transport = transport
        self.protocol = protocol
        self.timeout = timeout

        self._shutdown_lock = threading.Lock()
        self._shutdown = False
        self.shutdown_event = asyncio.Event()

        self.returncode: concurrent.futures.Future[int] = concurrent.futures.Future()

    def _timeout_for(self, limit: Optional[Limit]) -> Optional[float]:
        if self.timeout is None or limit is None or limit.time is None:
            return None
        return self.timeout + limit.time

    @contextlib.contextmanager
    def _not_shut_down(self) -> Generator[None, None, None]:
        with self._shutdown_lock:
            if self._shutdown:
                raise EngineTerminatedError("engine event loop dead")
            yield

    @property
    def options(self) -> MutableMapping[str, Option]:
        async def _get() -> MutableMapping[str, Option]:
            return copy.copy(self.protocol.options)

        with self._not_shut_down():
            future = asyncio.run_coroutine_threadsafe(_get(), self.protocol.loop)
        return future.result()

    @property
    def id(self) -> Mapping[str, str]:
        async def _get() -> Mapping[str, str]:
            return self.protocol.id.copy()

        with self._not_shut_down():
            future = asyncio.run_coroutine_threadsafe(_get(), self.protocol.loop)
        return future.result()

    def communicate(self, command_factory: Callable[[], BaseCommand[Protocol, T]]) -> T:
        with self._not_shut_down():
            coro = self.protocol.communicate(command_factory)
            future = asyncio.run_coroutine_threadsafe(coro, self.protocol.loop)
        return future.result()

    def configure(self, options: ConfigMapping) -> None:
        with self._not_shut_down():
            coro = asyncio.wait_for(self.protocol.configure(options), self.timeout)
            future = asyncio.run_coroutine_threadsafe(coro, self.protocol.loop)
        return future.result()

    def ping(self) -> None:
        with self._not_shut_down():
            coro = asyncio.wait_for(self.protocol.ping(), self.timeout)
            future = asyncio.run_coroutine_threadsafe(coro, self.protocol.loop)
        return future.result()

    def play(self, board: chess.Board, limit: Limit, *, game: object = None, info: Info = INFO_NONE, ponder: bool = False, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> PlayResult:
        with self._not_shut_down():
            coro = asyncio.wait_for(
                self.protocol.play(board, limit, game=game, info=info, ponder=ponder, root_moves=root_moves, options=options),
                self._timeout_for(limit))
            future = asyncio.run_coroutine_threadsafe(coro, self.protocol.loop)
        return future.result()

    @typing.overload
    def analyse(self, board: chess.Board, limit: Limit, *, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> InfoDict: ...
    @typing.overload
    def analyse(self, board: chess.Board, limit: Limit, *, multipv: int, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> List[InfoDict]: ...
    @typing.overload
    def analyse(self, board: chess.Board, limit: Limit, *, multipv: Optional[int] = None, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> Union[InfoDict, List[InfoDict]]: ...
    def analyse(self, board: chess.Board, limit: Limit, *, multipv: Optional[int] = None, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> Union[InfoDict, List[InfoDict]]:
        with self._not_shut_down():
            coro = asyncio.wait_for(
                self.protocol.analyse(board, limit, multipv=multipv, game=game, info=info, root_moves=root_moves, options=options),
                self._timeout_for(limit))
            future = asyncio.run_coroutine_threadsafe(coro, self.protocol.loop)
        return future.result()

    def analysis(self, board: chess.Board, limit: Optional[Limit] = None, *, multipv: Optional[int] = None, game: object = None, info: Info = INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options: ConfigMapping = {}) -> SimpleAnalysisResult:
        with self._not_shut_down():
            coro = asyncio.wait_for(
                self.protocol.analysis(board, limit, multipv=multipv, game=game, info=info, root_moves=root_moves, options=options),
                self.timeout)  # Timeout until analysis is *started*
            future = asyncio.run_coroutine_threadsafe(coro, self.protocol.loop)
        return SimpleAnalysisResult(self, future.result())

    def quit(self) -> None:
        with self._not_shut_down():
            coro = asyncio.wait_for(self.protocol.quit(), self.timeout)
            future = asyncio.run_coroutine_threadsafe(coro, self.protocol.loop)
        return future.result()

    def close(self) -> None:
        """
        Closes the transport and the background event loop as soon as possible.
        """
        def _shutdown() -> None:
            self.transport.close()
            self.shutdown_event.set()

        with self._shutdown_lock:
            if not self._shutdown:
                self._shutdown = True
                self.protocol.loop.call_soon_threadsafe(_shutdown)

    @classmethod
    def popen(cls, Protocol: Type[Protocol], command: Union[str, List[str]], *, timeout: Optional[float] = 10.0, debug: bool = False, setpgrp: bool = False, **popen_args: Any) -> SimpleEngine:
        async def background(future: concurrent.futures.Future[SimpleEngine]) -> None:
            transport, protocol = await Protocol.popen(command, setpgrp=setpgrp, **popen_args)
            threading.current_thread().name = f"{cls.__name__} (pid={transport.get_pid()})"
            simple_engine = cls(transport, protocol, timeout=timeout)
            try:
                await asyncio.wait_for(protocol.initialize(), timeout)
                future.set_result(simple_engine)
                returncode = await protocol.returncode
                simple_engine.returncode.set_result(returncode)
            finally:
                simple_engine.close()
            await simple_engine.shutdown_event.wait()

        return run_in_background(background, name=f"{cls.__name__} (command={command!r})", debug=debug)

    @classmethod
    def popen_uci(cls, command: Union[str, List[str]], *, timeout: Optional[float] = 10.0, debug: bool = False, setpgrp: bool = False, **popen_args: Any) -> SimpleEngine:
        """
        Spawns and initializes a UCI engine.
        Returns a :class:`~chess.engine.SimpleEngine` instance.
        """
        return cls.popen(UciProtocol, command, timeout=timeout, debug=debug, setpgrp=setpgrp, **popen_args)

    @classmethod
    def popen_xboard(cls, command: Union[str, List[str]], *, timeout: Optional[float] = 10.0, debug: bool = False, setpgrp: bool = False, **popen_args: Any) -> SimpleEngine:
        """
        Spawns and initializes an XBoard engine.
        Returns a :class:`~chess.engine.SimpleEngine` instance.
        """
        return cls.popen(XBoardProtocol, command, timeout=timeout, debug=debug, setpgrp=setpgrp, **popen_args)

    def __enter__(self) -> SimpleEngine:
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.close()

    def __repr__(self) -> str:
        pid = self.transport.get_pid()  # This happens to be thread-safe
        return f"<{type(self).__name__} (pid={pid})>"


class SimpleAnalysisResult:
    """
    Synchronous wrapper around :class:`~chess.engine.AnalysisResult`. Returned
    by :func:`chess.engine.SimpleEngine.analysis()`.
    """

    def __init__(self, simple_engine: SimpleEngine, inner: AnalysisResult) -> None:
        self.simple_engine = simple_engine
        self.inner = inner

    @property
    def info(self) -> InfoDict:
        async def _get() -> InfoDict:
            return self.inner.info.copy()

        with self.simple_engine._not_shut_down():
            future = asyncio.run_coroutine_threadsafe(_get(), self.simple_engine.protocol.loop)
        return future.result()

    @property
    def multipv(self) -> List[InfoDict]:
        async def _get() -> List[InfoDict]:
            return [info.copy() for info in self.inner.multipv]

        with self.simple_engine._not_shut_down():
            future = asyncio.run_coroutine_threadsafe(_get(), self.simple_engine.protocol.loop)
        return future.result()

    def stop(self) -> None:
        with self.simple_engine._not_shut_down():
            self.simple_engine.protocol.loop.call_soon_threadsafe(self.inner.stop)

    def wait(self) -> BestMove:
        with self.simple_engine._not_shut_down():
            future = asyncio.run_coroutine_threadsafe(self.inner.wait(), self.simple_engine.protocol.loop)
        return future.result()

    def empty(self) -> bool:
        async def _empty() -> bool:
            return self.inner.empty()

        with self.simple_engine._not_shut_down():
            future = asyncio.run_coroutine_threadsafe(_empty(), self.simple_engine.protocol.loop)
        return future.result()

    def get(self) -> InfoDict:
        with self.simple_engine._not_shut_down():
            future = asyncio.run_coroutine_threadsafe(self.inner.get(), self.simple_engine.protocol.loop)
        return future.result()

    def next(self) -> Optional[InfoDict]:
        with self.simple_engine._not_shut_down():
            future = asyncio.run_coroutine_threadsafe(self.inner.next(), self.simple_engine.protocol.loop)
        return future.result()

    def __iter__(self) -> Iterator[InfoDict]:
        with self.simple_engine._not_shut_down():
            self.simple_engine.protocol.loop.call_soon_threadsafe(self.inner.__aiter__)
        return self

    def __next__(self) -> InfoDict:
        try:
            with self.simple_engine._not_shut_down():
                future = asyncio.run_coroutine_threadsafe(self.inner.__anext__(), self.simple_engine.protocol.loop)
            return future.result()
        except StopAsyncIteration:
            raise StopIteration

    def __enter__(self) -> SimpleAnalysisResult:
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        self.stop()
