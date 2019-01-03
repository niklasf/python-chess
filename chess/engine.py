# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2019 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

# TODO: XBoard support
# TODO: Check naming. Is it too UCI specific?
# TODO: Pondering
# TODO: Test coverage

import abc
import asyncio
import collections
import concurrent.futures
import functools
import logging
import enum
import collections
import warnings
import subprocess
import sys
import threading
import os

try:
    # Python 3.7
    from asyncio import get_running_loop as _get_running_loop
except ImportError:
    try:
        from asyncio import _get_running_loop
    except:
        # Python 3.4
        def _get_running_loop():
            return asyncio.get_event_loop()

try:
    # Python 3.7
    from asyncio import all_tasks as _all_tasks
except ImportError:
    _all_tasks = asyncio.Task.all_tasks

try:
    StopAsyncIteration
except NameError:
    # Python 3.4
    class StopAsyncIteration(Exception):
        pass

import chess


LOGGER = logging.getLogger(__name__)

KORK = object()

MANAGED_UCI_OPTIONS = ["uci_chess960", "uci_variant", "uci_analysemode", "multipv", "ponder"]


def setup_event_loop():
    """
    Creates and sets up a new asyncio event loop that is capable of spawning
    and watching subprocesses.

    On Windows: Globally sets a proactor event loop policy.

    On Unix systems: Does nothing, except when not running on the main thread.
    Then it installs a child watcher that uses polling.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    if sys.platform == "win32" or threading.current_thread() == threading.main_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

    class PollingChildWatcher(asyncio.SafeChildWatcher):
        def __init__(self):
            super().__init__()
            self._poll_handle = None

        def attach_loop(self, loop):
            assert loop is None or isinstance(loop, asyncio.AbstractEventLoop)

            if self._loop is not None and loop is None and self._callbacks:
                warnings.warn("A loop is being detached from a child watcher with pending handlers", RuntimeWarning)

            if self._poll_handle is not None:
                self._poll_handle.cancel()

            self._loop = loop
            if loop is not None:
                self._poll_handle = self._loop.call_soon(self._poll)

                # Prevent a race condition in case a child terminated
                # during the switch.
                self._do_waitpid_all()

        def _poll(self):
            if self._loop:
                self._do_waitpid_all()
                self._poll_handle = self._loop.call_later(1.0, self._poll)

    policy = asyncio.get_event_loop_policy()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    watcher = PollingChildWatcher()
    watcher.attach_loop(loop)
    policy.set_child_watcher(watcher)

    return loop


def run_in_background(coroutine):
    """
    Runs ``coroutine(future)`` in a new event loop on a background thread.

    Blocks and returns the *future* result as soon as it is resolved.
    The coroutine and all remaining tasks continue running in the background
    until it is complete.
    """
    assert asyncio.iscoroutinefunction(coroutine)

    future = concurrent.futures.Future()

    def background():
        loop = setup_event_loop()

        try:
            loop.run_until_complete(coroutine(future))
            future.cancel()
        except Exception as exc:
            future.set_exception(exc)
            return
        finally:
            try:
                # Finish all remaining tasks.
                pending = _all_tasks(loop)
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

                # Shutdown async generators.
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except AttributeError:
                    # Before Python 3.6.
                    pass
            finally:
                loop.close()

    threading.Thread(target=background).start()
    return future.result()


class EngineError(RuntimeError):
    """Runtime error caused by a misbehaving engine or incorrect usage."""


class EngineTerminatedError(EngineError):
    """The engine process exited unexpectedly."""


class Option(collections.namedtuple("Option", "name type default min max var")):
    """Information about an available engine option."""

    def parse(self, value):
        if self.type == "check":
            return value and value != "false"
        elif self.type == "spin":
            try:
                value = int(value)
            except ValueError:
                raise EngineError("expected integer for spin option {}, got: {}".format(self.name, repr(value)))
            if self.min is not None and value < self.min:
                raise EngineError("expected value for option {} to be at least {}, got: {}".format(self.name, self.min, value))
            if self.max is not None and self.max < value:
                raise EngineError("expected value for option {} to be at most {}, got: {}".format(self.name, self.max, value))
            return value
        elif self.type == "combo":
            value = str(value)
            if value not in (self.var or []):
                raise EngineError("invalid value for combo option {}, got: {} (available: {})".format(self.name, value, ", ".join(self.var)))
            return value
        elif self.type in ["button", "reset", "save"]:
            return None
        elif self.type in ["string", "file", "path"]:
            value = str(value)
            if "\n" in value or "\r" in value:
                raise EngineError("invalid line-break in string option {}".format(self.name))
            return value
        else:
            raise EngineError("unknown option type: {}", self.type)

    def is_managed_uci(self):
        return self.name.lower() in MANAGED_UCI_OPTIONS


class Limit:
    """Search termination condition."""

    def __init__(self, *, movetime=None, depth=None, nodes=None, mate=None, wtime=None, btime=None, winc=None, binc=None, movestogo=None):
        self.movetime = movetime
        self.depth = depth
        self.nodes = nodes
        self.mate = mate
        self.wtime = wtime
        self.btime = btime
        self.winc = winc
        self.binc = binc
        self.movestogo = movestogo

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ", ".join("{}={}".format(attr, repr(getattr(self, attr)))
                      for attr in ["wtime", "btime", "winc", "binc", "movestogo", "depth", "nodes", "mate", "movetime"]
                      if getattr(self, attr) is not None))


class PlayResult:
    """Returned by :func:`chess.engine.EngineProtocol.play()`."""

    def __init__(self, move, ponder):
        self.move = move
        self.ponder = ponder

    def __repr__(self):
        return "<{} at {} (move={}, ponder={})>".format(type(self).__name__, hex(id(self)), self.move, self.ponder)


class Score(abc.ABC):
    """
    Evaluation of a position.

    The score can be :class:`~chess.engine.Cp` (centi-pawns) or
    :class:`~chess.engine.Mate`. A positive value indicates an advantage.

    There is a total order defined on centi-pawn and mate scores.

    >>> from chess.engine import Cp, Mate
    >>>
    >>> Mate.minus(0) < Mate.minus(1) < Cp(-50) < Cp(200) < Mate.plus(4) < Mate.plus(0)
    True

    Scores are usually given from the point of view of the side to move. They
    can be negated to change the point of view:

    >>> -Cp(20)
    Cp(-20)

    >>> -Mate.from_moves(4)
    Mate.minus(4)
    """

    @abc.abstractmethod
    def score(self, mate_score=None):
        """
        Returns a centi-pawn score or ``None``.

        You can optionally pass a large value to convert mate scores to
        centi-pawn scores.

        >>> from chess.engine import Cp, Mate
        >>>
        >>> cp = Cp(-300)
        >>> cp.score()
        -300
        >>>
        >>> mate = Mate.from_moves(5)
        >>> mate.score() is None
        True
        >>> mate.score(100000)
        99995
        """
        raise NotImplementedError

    @abc.abstractmethod
    def mate(self):
        """
        Returns a mate score or ``None``.

        :warning: This conflates ``Mate.minus(0)`` (we are mated) and
            ``Mate.plus(0)`` (we have given mate) to ``0``.
        """
        raise NotImplementedError

    def is_mate(self):
        """Tests if this is a mate score."""
        return self.mate() is not None

    @abc.abstractmethod
    def __neg__(self):
        raise NotImplementedError


@functools.total_ordering
class Cp(Score):
    """Centi-pawn score."""

    def __init__(self, cp):
        self.cp = cp

    def mate(self):
        return None

    def score(self, mate_score=None):
        return self.cp

    def __repr__(self):
        return "Cp({})".format(self.cp)

    def __str__(self):
        return "+{}".format(self.cp) if self.cp > 0 else str(self.cp)

    def __add__(self, other):
        try:
            return Cp(self.cp + other.cp)
        except AttributeError:
            return NotImplemented

    def __sub__(self, other):
        try:
            return Cp(self.cp - other.cp)
        except AttributeError:
            return NotImplemented

    def __mul__(self, scalar):
        try:
            return Cp(self.cp * scalar)
        except TypeError:
            return NotImplemented

    __rmul__ = __mul__

    def __neg__(self):
        return Cp(-self.cp)

    def __pos__(self):
        return Cp(self.cp)

    def __abs__(self):
        return Cp(abs(self.cp))

    def __eq__(self, other):
        try:
            return self.cp == other.score()
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            return other.winning
        except AttributeError:
            pass

        try:
            return self.cp < other.cp
        except AttributeError:
            pass

        return NotImplemented


@functools.total_ordering
class Mate(Score):
    """Mate score."""

    def __init__(self, moves, winning):
        self.moves = abs(moves)
        self.winning = winning ^ (moves < 0)

    def score(self, mate_score=None):
        if mate_score is None:
            return None
        elif self.winning:
            return mate_score - self.moves
        else:
            return -mate_score + self.moves

    def mate(self):
        # Careful: Conflates Mate.plus(0) and Mate.minus(0)!
        return self.moves if self.winning else -self.moves

    @classmethod
    def from_moves(cls, moves):
        return Mate(abs(moves), moves > 0)

    @classmethod
    def plus(self, moves):
        return Mate(moves, True)

    @classmethod
    def minus(self, moves):
        return Mate(moves, False)

    def __repr__(self):
        if self.winning:
            return "Mate.plus({})".format(self.moves)
        else:
            return "Mate.minus({})".format(self.moves)

    def __str__(self):
        return "#{}".format(self.moves) if self.winning else "#-{}".format(self.moves)

    def __neg__(self):
        return Mate(self.moves, not self.winning)

    def __pos__(self):
        return Mate(self.moves, self.winning)

    def __abs__(self):
        return Mate(self.moves, True)

    def __eq__(self, other):
        try:
            return other.is_mate() and self.moves == other.moves and self.winning == other.winning
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        try:
            if self.winning != other.winning:
                return self.winning < other.winning

            if self.winning:
                return self.moves > other.moves
            else:
                return self.moves < other.moves
        except AttributeError:
            pass

        return other > self


class MockTransport:
    def __init__(self, protocol):
        self.protocol = protocol
        self.expectations = collections.deque()
        self.stdin_buffer = bytearray()

    def expect(self, expectation, responses=[]):
        self.expectations.append((expectation, responses))

    def assert_done(self):
        assert not self.expectations, "pending expectations: {}".format(self.expectations)

    def get_pipe_transport(self, fd):
        assert fd == 0, "expected 0 for stdin, got {}".format(fd)
        return self

    def write(self, data):
        self.stdin_buffer.extend(data)
        while b"\n" in self.stdin_buffer:
            line, self.stdin_buffer = self.stdin_buffer.split(b"\n", 1)
            line = line.decode("utf-8")

            assert self.expectations, "unexpected: {}".format(line)
            expectation, responses = self.expectations.popleft()
            assert expectation == line, "expected {}, got: {}".format(expectation, line)
            self.protocol.loop.call_soon(lambda: self.protocol.pipe_data_received(1, "\n".join(responses).encode("utf-8") + b"\n"))

    def get_pid(self):
        return id(self)

    def get_returncode(self):
        return 0


class EngineProtocol(asyncio.SubprocessProtocol, metaclass=abc.ABCMeta):
    """Protocol for communicating with a chess engine process."""

    def __init__(self):
        self.loop = _get_running_loop()
        self.transport = None

        self.buffer = {
            1: bytearray(),  # stdout
            2: bytearray(),  # stderr
        }

        self.command = None
        self.next_command = None

        self.returncode = asyncio.Future(loop=self.loop)

    def connection_made(self, transport):
        self.transport = transport
        LOGGER.debug("%s: Connection made", self)

    def connection_lost(self, exc):
        code = self.transport.get_returncode()
        LOGGER.debug("%s: Connection lost (exit code: %d, error: %s)", self, code, exc)

        # Terminate commands.
        if self.command is not None:
            self.command._engine_terminated(self, code)
            self.command = None
        if self.next_command is not None:
            self.next_command._engine_terminated(self, code)
            self.next_command = None

        self.returncode.set_result(code)

    def process_exited(self):
        LOGGER.debug("%s: Process exited", self)

    def send_line(self, line):
        LOGGER.debug("%s: << %s", self, line)
        stdin = self.transport.get_pipe_transport(0)
        stdin.write(line.encode("utf-8"))
        stdin.write(b"\n")

    def pipe_data_received(self, fd, data):
        self.buffer[fd].extend(data)
        while b"\n" in self.buffer[fd]:
            line, self.buffer[fd] = self.buffer[fd].split(b"\n", 1)
            line = line.decode("utf-8")
            if fd == 1:
                self._line_received(line)
            else:
                self.error_line_received(line)

    def error_line_received(self, line):
        LOGGER.warning("%s: stderr >> %s", self, line)

    def _line_received(self, line):
        LOGGER.debug("%s: >> %s", self, line)

        self.line_received(line)

        if self.command:
            self.command._line_received(self, line)

    def line_received(self, line):
        pass

    @asyncio.coroutine
    def communicate(self, command_factory):
        command = command_factory(self.loop)

        if self.returncode.done():
            raise EngineTerminatedError("engine process dead (exit code: {})".format(self.returncode.result()))

        assert command.state == CommandState.New

        if self.next_command is not None:
            self.next_command.result.cancel()
            self.next_command.finished.cancel()
            self.next_command._done()

        self.next_command = command

        def previous_command_finished(_):
            if self.command is not None:
                self.command._done()

            self.command, self.next_command = self.next_command, None
            if self.command is not None:
                cmd = self.command
                cmd.result.add_done_callback(lambda result: cmd._cancel(self) if cmd.result.cancelled() else None)
                cmd.finished.add_done_callback(previous_command_finished)
                cmd._start(self)

        if self.command is None:
            previous_command_finished(None)
        elif not self.command.result.done():
            self.command.result.cancel()
        elif not self.command.result.cancelled():
            self.command._cancel(self)

        return (yield from command.result)

    def __repr__(self):
        pid = self.transport.get_pid() if self.transport is not None else None
        return "<{} (pid={})>".format(type(self).__name__, pid)

    @abc.abstractmethod
    @asyncio.coroutine
    def ping(self):
        """
        Pings the engine and waits for a response. Used to ensure the engine
        is still alive and idle.
        """
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def configure(self, options):
        """Configures global engine options."""
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def play(self, board, limit, *, game=None, searchmoves=None, options={}):
        """
        Play a position.

        :param board: The position. The entire move stack will be sent to the
            engine.
        :param limit: An instance of :class:`~chess.engine.Limit` that
            determines when to stop thinking.
        :param game: Optional. An arbitrary object that identifies the game.
            Will automatically clear hashtables if the object is not equal
            to the previous game.
        :param searchmoves: Optional. Consider only root moves from this list.
        :param options: Optional. A dictionary of engine options for the
            analysis. The previous configuration will be restored after the
            analysis is complete. You can permanently apply a configuration
            with :func:`~chess.engine.EngineProtocol.configure()`.
        """
        raise NotImplementedError

    @asyncio.coroutine
    def analyse(self, board, limit, *, multipv=None, game=None, searchmoves=None, options={}):
        """
        Analyses a position and returns an info dictionary.

        :param board: The position to analyse. The entire move stack will be
            sent to the engine.
        :param limit: An instance of :class:`~chess.engine.Limit` that
            determines when to stop the analysis.
        :param multipv: Optional. Analyse multiple root moves. Will return a list of
            at most *multipv* dictionaries rather than just a single
            info dictionary.
        :param game: Optional. An arbitrary object that identifies the game.
            Will automatically clear hashtables if the object is not equal
            to the previous game.
        :param searchmoves: Optional. Limit analysis to a list of root moves.
        :param options: Optional. A dictionary of engine options for the
            analysis. The previous configuration will be restored after the
            analysis is complete. You can permanently apply a configuration
            with :func:`~chess.engine.EngineProtocol.configure()`.
        """
        analysis = yield from self.analysis(board, limit, game=game, searchmoves=searchmoves, options=options)

        with analysis:
            yield from analysis.wait()

        return analysis.info if multipv is None else analysis.multipv

    @abc.abstractmethod
    @asyncio.coroutine
    def analysis(self, board, limit=None, *, multipv=None, game=None, searchmoves=None, options={}):
        """
        Starts analysing a position.

        :param board: The position to analyse. The entire move stack will be
            sent to the engine.
        :param limit: Optional. An instance of :class:`~chess.engine.Limit`
            that determines when to stop the analysis. Analysis is infinite
            by default.
        :param multipv: Optional. Analyse multiple root moves.
        :param game: Optional. An arbitrary object that identifies the game.
            Will automatically clear hashtables if the object is not equal
            to the previous game.
        :param searchmoves: Optional. Limit analysis to a list of root moves.
        :param options: Optional. A dictionary of engine options for the
            analysis. The previous configuration will be restored after the
            analysis is complete. You can permanently apply a configuration
            with :func:`~chess.engine.EngineProtocol.configure()`.

        Returns :class:`~chess.engine.AnalysisResult`, a handle that allows
        asynchronously iterating over the information sent by the engine
        and stopping the the analysis at any time.
        """
        raise NotImplementedError

    @abc.abstractmethod
    @asyncio.coroutine
    def quit(self):
        """Asks the engine to shut down."""
        raise NotImplementedError

    @classmethod
    @asyncio.coroutine
    def popen(cls, command, *, setpgrp=False, **kwargs):
        if not isinstance(command, list):
            command = [command]

        popen_args = {}
        if setpgrp:
            try:
                # Windows.
                popen_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            except AttributeError:
                # Unix.
                popen_args["preexec_fn"] = os.setpgrp
        popen_args.update(kwargs)

        loop = _get_running_loop()
        transport, protocol = yield from loop.subprocess_exec(cls, *command, **popen_args)
        yield from protocol._initialize()
        return transport, protocol


class CommandState(enum.Enum):
    New = 1
    Active = 2
    Cancelling = 3
    Done = 4


class BaseCommand:
    def __init__(self, loop):
        self.state = CommandState.New

        self.loop = loop
        self.result = asyncio.Future(loop=loop)
        self.finished = asyncio.Future(loop=loop)

    def _engine_terminated(self, engine, code):
        exc = EngineTerminatedError("engine process died unexpectedly (exit code: {})".format(type(self).__name__, code))
        self._handle_exception(exc)

        if self.state in [CommandState.Active, CommandState.Cancelling]:
            self.engine_terminated(engine, exc)

    def _handle_exception(self, exc):
        if not self.result.done():
            self.result.set_exception(exc)
        if not self.finished.done():
            self.finished.set_exception(exc)

            # Prevent warning when the exception is not retrieved.
            try:
                self.finished.result()
            except:
                pass

    def set_finished(self):
        assert self.state in [CommandState.Active, CommandState.Cancelling]
        if not self.result.done():
            self.result.set_result(None)
        self.finished.set_result(None)

    def _cancel(self, engine):
        assert self.state == CommandState.Active
        self.state = CommandState.Cancelling
        self.cancel(engine)

    def _start(self, engine):
        assert self.state == CommandState.New
        self.state = CommandState.Active
        try:
            self.start(engine)
        except EngineError as err:
            self._handle_exception(err)

    def _done(self):
        assert self.state != CommandState.Done
        self.state = CommandState.Done

    def _line_received(self, engine, line):
        assert self.state in [CommandState.Active, CommandState.Cancelling]
        self.line_received(engine, line)

    def cancel(self, engine):
        pass

    def start(self, engine):
        raise NotImplementedError

    def line_received(self, engine, line):
        pass

    def engine_terminated(self, engine, exc):
        pass


class UciProtocol(EngineProtocol):
    """
    An implementation of the
    `Universal Chess Interface <https://www.chessprogramming.org/UCI>`_
    protocol.
    """

    def __init__(self):
        super().__init__()
        self.options = UciOptionMap()
        self.config = UciOptionMap()
        self.board = chess.Board()
        self.game = None

    @asyncio.coroutine
    def _initialize(self):
        class Command(BaseCommand):
            def start(self, engine):
                engine.send_line("uci")

            def line_received(self, engine, line):
                if line == "uciok":
                    self.set_finished()
                elif line.startswith("option "):
                    self._option(engine, line.split(" ", 1)[1])

            def _option(self, engine, arg):
                current_parameter = None

                name = []
                type = []
                default = []
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
                            LOGGER.exception("exception parsing option min")
                    elif current_parameter == "max":
                        try:
                            max = int(token)
                        except ValueError:
                            LOGGER.exception("exception parsing option max")

                if current_var is not None:
                    var.append(" ".join(current_var))

                name = " ".join(name)
                type = " ".join(type)
                default = " ".join(default)

                without_default = Option(name, type, None, min, max, var)
                option = Option(name, type, without_default.parse(default), min, max, var)
                engine.options[option.name] = option

        return (yield from self.communicate(Command))

    def _isready(self):
        self.send_line("isready")

    def _ucinewgame(self):
        self.send_line("ucinewgame")

    @asyncio.coroutine
    def ping(self):
        class Command(BaseCommand):
            def start(self, engine):
                engine._isready()

            def line_received(self, engine, line):
                if line == "readyok":
                    self.set_finished()
                else:
                    LOGGER.warning("%s: Unexpected engine output: %s", engine, line)

        return (yield from self.communicate(Command))

    def _getoption(self, option, default=None):
        if option in self.config:
            return self.config[option]
        if option in self.options:
            return self.options[option].default
        return default

    def _setoption(self, name, value):
        try:
            value = self.options[name].parse(value)
        except KeyError:
            raise EngineError("engine does not support option {} (available options: {})".format(name, ", ".join(self.options)))

        if value is None or value != self._getoption(name):
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

    def _configure(self, options):
        for name, value in options.items():
            if name.lower() in MANAGED_UCI_OPTIONS:
                raise EngineError("cannot set {} which is automatically managed".format(name))
            else:
                self._setoption(name, value)

    @asyncio.coroutine
    def configure(self, options):
        class Command(BaseCommand):
            def start(self, engine):
                engine._configure(options)
                self.set_finished()

        return (yield from self.communicate(Command))

    def _position(self, board):
        # Select UCI_Variant and UCI_Chess960.
        uci_variant = type(board).uci_variant
        if uci_variant != self._getoption("UCI_Variant", "chess"):
            if "UCI_Variant" not in self.options:
                raise EngineError("engine does not support UCI_Variant")
            self._setoption("UCI_Variant", uci_variant)

        if board.chess960 != self._getoption("UCI_Chess960", False):
            if "UCI_Chess960" not in self.options:
                raise EngineError("engine does not support UCI_Chess960")
            self._setoption("UCI_Chess960", board.chess960)

        # Send starting position.
        builder = ["position"]
        root = board.root()
        fen = root.fen()
        if uci_variant == "chess" and fen == chess.STARTING_FEN:
            builder.append("startpos")
        else:
            builder.append("fen")
            builder.append(root.shredder_fen() if board.chess960 else fen)

        # Send moves.
        if board.move_stack:
            builder.append("moves")
            builder.extend(move.uci() for move in board.move_stack)

        self.send_line(" ".join(builder))
        self.board = board.copy(stack=False)

    def _go(self, limit, *, searchmoves=None, ponder=False, infinite=False):
        builder = ["go"]

        if ponder:
            builder.append("ponder")

        if limit.wtime is not None:
            builder.append("wtime")
            builder.append(str(int(limit.wtime)))

        if limit.btime is not None:
            builder.append("btime")
            builder.append(str(int(limit.btime)))

        if limit.winc is not None:
            builder.append("winc")
            builder.append(str(int(limit.winc)))

        if limit.binc is not None:
            builder.append("binc")
            builder.append(str(int(limit.binc)))

        if limit.movestogo is not None and int(limit.movestogo) > 0:
            builder.append("movestogo")
            builder.append(str(int(limit.movestogo)))

        if limit.depth is not None:
            builder.append("depth")
            builder.append(str(int(limit.depth)))

        if limit.nodes is not None:
            builder.append("nodes")
            builder.append(str(int(limit.nodes)))

        if limit.mate is not None:
            builder.append("mate")
            builder.append(str(int(limit.mate)))

        if limit.movetime is not None:
            builder.append("movetime")
            builder.append(str(int(limit.movetime)))

        if infinite:
            builder.append("infinite")

        if searchmoves:
            builder.append("searchmoves")
            for move in searchmoves:
                builder.append(self.board.uci(move))

        self.send_line(" ".join(builder))

    @asyncio.coroutine
    def play(self, board, limit, *, game=None, searchmoves=None, options={}):
        previous_config = self.config.copy()

        class Command(BaseCommand):
            def start(self, engine):
                if "UCI_AnalyseMode" in engine.options:
                    engine._setoption("UCI_AnalyseMode", False)

                engine._configure(options)

                if engine.game != game:
                    engine._ucinewgame()
                engine.game = game

                engine._position(board)
                engine._go(limit, searchmoves=searchmoves)

            def line_received(self, engine, line):
                if line.startswith("bestmove "):
                    self._bestmove(engine, line.split(" ", 1)[1])
                elif not line.startswith("info "):
                    LOGGER.warning("%s: Unexpected engine output: %s", engine, line)

            def _bestmove(self, engine, arg):
                try:
                    if not self.result.cancelled():
                        tokens = arg.split(None, 2)

                        bestmove = None
                        if tokens[0] != "(none)":
                            try:
                                bestmove = engine.board.parse_uci(tokens[0])
                            except ValueError as err:
                                self.result.set_exception(EngineError(err))
                                return

                        ponder = None
                        if bestmove is not None and len(tokens) >= 3 and tokens[1] == "ponder" and tokens[2] != "(none)":
                            board.push(bestmove)
                            try:
                                ponder = board.parse_uci(tokens[2])
                            except ValueError as err:
                                LOGGER.exception("engine sent invalid ponder move")
                            finally:
                                board.pop()

                        self.result.set_result(PlayResult(bestmove, ponder))
                finally:
                    for name, value in previous_config.items():
                        engine._setoption(name, value)

                    self.set_finished()

            def cancel(self, engine):
                engine.send_line("stop")

        return (yield from self.communicate(Command))

    @asyncio.coroutine
    def analysis(self, board, limit=None, *, multipv=None, game=None, searchmoves=None, options={}):
        previous_config = self.config.copy()

        class Command(BaseCommand):
            def start(self, engine):
                self.analysis = AnalysisResult(stop=lambda: self.cancel(engine))

                if "UCI_AnalyseMode" in engine.options:
                    engine._setoption("UCI_AnalyseMode", True)

                if multipv and multipv > 1:
                    engine._setoption("MultiPV", multipv)

                engine._configure(options)

                if engine.game != game:
                    engine._ucinewgame()
                engine.game = game

                engine._position(board)

                if limit:
                    engine._go(limit, searchmoves=searchmoves)
                else:
                    engine._go(Limit(), searchmoves=searchmoves, infinite=True)

                self.result.set_result(self.analysis)

            def line_received(self, engine, line):
                if line.startswith("info "):
                    self._info(engine, line.split(" ", 1)[1])
                elif line.startswith("bestmove "):
                    self._bestmove(engine, line.split(" ", 1)[1])
                else:
                    LOGGER.warning("%s: Unexpected engine output: %s", engine, line)

            def _info(self, engine, arg):
                # Initialize parser state.
                info = {}
                board = None
                pv = None
                score_kind = None
                refutation_move = None
                refuted_by = []
                currline_cpunr = None
                currline_moves = []
                string = []

                # Parameters with variable length can only be handled when the
                # next parameter starts or at the end of the line.
                def end_of_parameter():
                    if pv is not None:
                        info["pv"] = pv

                    if refutation_move is not None:
                        if not "refutation" in info:
                            info["refutation"] = {}
                        info["refutation"][refutation_move] = refuted_by

                    if currline_cpunr is not None:
                        if not "currline" in info:
                            info["currline"] = {}
                        info["currline"][currline_cpunr] = currline_moves

                # Parse all other parameters.
                current_parameter = None
                for token in arg.split(" "):
                    if current_parameter == "string":
                        string.append(token)
                    elif not token:
                        # Ignore extra spaces. Those can not be directly discarded,
                        # because they may occur in the string parameter.
                        pass
                    elif token in ["depth", "seldepth", "time", "nodes", "pv", "multipv", "score", "currmove", "currmovenumber", "hashfull", "nps", "tbhits", "cpuload", "refutation", "currline", "ebf", "string"]:
                        end_of_parameter()
                        current_parameter = token

                        pv = None
                        score_kind = None
                        refutation_move = None
                        refuted_by = []
                        currline_cpunr = None
                        currline_moves = []

                        if current_parameter == "pv":
                            pv = []

                        if current_parameter in ["refutation", "pv", "currline"]:
                            board = engine.board.copy(stack=False)
                    elif current_parameter in ["depth", "seldepth", "time", "nodes", "multipv", "currmovenumber", "hashfull", "nps", "tbhits", "cpuload"]:
                        try:
                            info[current_parameter] = int(token)
                        except ValueError:
                            LOGGER.error("exception parsing %s from info: %r", current_parameter, arg)
                    elif current_parameter == "pv":
                        try:
                            pv.append(board.push_uci(token))
                        except ValueError:
                            LOGGER.exception("exception parsing pv from info: %r, position at root: %s", arg, engine.board.fen())
                    elif current_parameter == "score":
                        try:
                            if token in ["cp", "mate"]:
                                score_kind = token
                            elif token == "lowerbound":
                                info["lowerbound"] = True
                            elif token == "upperbound":
                                info["upperbound"] = True
                            elif score_kind == "cp":
                                info["score"] = Cp(int(token))
                            elif score_kind == "mate":
                                info["mate"] = Mate.from_moves(int(token))
                        except ValueError:
                            LOGGER.error("exception parsing score %s from info: %r", score_kind, arg)
                    elif current_parameter == "currmove":
                        try:
                            info[current_parameter] = chess.Move.from_uci(token)
                        except ValueError:
                            LOGGER.error("exception parsing %s from info: %r", current_parameter, arg)
                    elif current_parameter == "refutation":
                        try:
                            if refutation_move is None:
                                refutation_move = board.push_uci(token)
                            else:
                                refuted_by.append(board.push_uci(token))
                        except ValueError:
                            LOGGER.exception("exception parsing refutation from info: %r, position at root: %s", arg, engine.fen())
                    elif current_parameter == "currline":
                        try:
                            if currline_cpunr is None:
                                currline_cpunr = int(token)
                            else:
                                currline_moves.append(board.push_uci(token))
                        except ValueError:
                            LOGGER.exception("exception parsing currline from info: %r, position at root: %s", arg, engine.fen())
                    elif current_parameter == "ebf":
                        try:
                            info[current_parameter] = float(token)
                        except ValueError:
                            LOGGER.error("exception parsing %s from info: %r", current_parameter, arg)

                end_of_parameter()

                if string:
                    info["string"] = " ".join(string)

                self.analysis.post(info)

            def _bestmove(self, engine, arg):
                for name, value in previous_config.items():
                    engine._setoption(name, value)

                self.analysis.set_finished()
                self.set_finished()

            def cancel(self, engine):
                engine.send_line("stop")

        return (yield from self.communicate(Command))

    @asyncio.coroutine
    def quit(self):
        self.send_line("quit")
        yield from self.returncode


class UciOptionMap(collections.abc.MutableMapping):
    """Dictionary with case-insensitive keys."""

    def __init__(self, data=None, **kwargs):
        self._store = dict()
        if data is None:
            data = {}
        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._store.values())

    def __len__(self):
        return len(self._store)

    def __eq__(self, other):
        for key, value in self.items():
            if key not in other or other[key] != value:
                return False

        for key, value in other.items():
            if key not in self or self[key] != value:
                return False

        return True

    def copy(self):
        return type(self)(self._store.values())

    def __copy__(self):
        return self.copy()

    def __repr__(self):
        return "{}({})".format(type(self).__name__, dict(self.items()))


class XBoardProtocol(EngineProtocol):
    """
    An implementation of the
    `XBoard protocol <http://hgm.nubati.net/CECP.html>`_ (CECP).
    """
    pass


class AnalysisResult:
    """
    Handle to ongoing engine analysis.

    Can be used to asynchronously iterate over information sent by the engine.

    Automatically stops the analysis when used as a context manager.

    Returned by :func:`chess.engine.EngineProtocol.analysis()`.
    """
    def __init__(self, stop=None):
        self._stop = stop
        self._queue = asyncio.Queue()
        self._seen_kork = False
        self._finished = asyncio.Event()
        self.multipv = [{}]

    def post(self, info):
        multipv = info.get("multipv", 1)
        while len(self.multipv) < multipv:
            self.multipv.append({})
        self.multipv[multipv - 1].update(info)

        self._queue.put_nowait(info)

    def set_finished(self):
        self._queue.put_nowait(KORK)
        self._finished.set()

    @property
    def info(self):
        return self.multipv[0]

    def stop(self):
        """Stops the analysis as soon as possible."""
        if self._stop and not self._finished.is_set():
            self._stop()
            self._stop = None

    @asyncio.coroutine
    def wait(self):
        """Waits until the analysis is complete (or stopped)."""
        return (yield from self._finished.wait())

    def __aiter__(self):
        return self

    @asyncio.coroutine
    def next(self):
        """
        Waits for the next dictionary of information from the engine and
        returns it. Returns ``None`` if the analysis has been stopped and
        all information has been consumed.

        It might be more convenient to use ``async for info in analysis``
        (requires at least Python 3.5).
        """
        try:
            return (yield from self.__anext__())
        except StopAsyncIteration:
            return None

    @asyncio.coroutine
    def __anext__(self):
        if self._seen_kork:
            raise StopAsyncIteration

        info = yield from self._queue.get()
        if info is KORK:
            self._seen_kork = True
            raise StopAsyncIteration

        return info

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.stop()


@asyncio.coroutine
def popen_uci(command, *, setpgrp=False, **popen_args):
    """
    Spawns and initializes an UCI engine.

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
    return (yield from UciProtocol.popen(command, setpgrp=setpgrp, **popen_args))


@asyncio.coroutine
def popen_xboard(command, *, setpgrp=False, **popen_args):
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
    return (yield from XBoardProtocol.popen(command, setpgrp=setpgrp, **popen_args))


class SimpleEngine:
    """
    Synchronous wrapper around a transport and engine protocol pair. Provides
    the same methods and attributes as :class:`~chess.engine.EngineProtocol`,
    with blocking functions instead of coroutines.

    Methods will raise :class:`asyncio.TimeoutError` if an operation takes
    *timeout* seconds longer than expected (unless *timeout* is ``None``).

    Automatically closes the transport when used as a context manager.
    """

    def __init__(self, transport, protocol, *, timeout=10.0):
        self.transport = transport
        self.protocol = protocol
        self.timeout = timeout

    @property
    def options(self):
        @asyncio.coroutine
        def _get():
            return self.protocol.options.copy()
        return asyncio.run_coroutine_threadsafe(_get(), self.protocol.loop).result()

    def configure(self, options):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.configure(options), self.timeout), self.protocol.loop).result()

    def ping(self):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.ping(), self.timeout), self.protocol.loop).result()

    def play(self, board, limit, *, game=None, searchmoves=None, options={}):
        return asyncio.run_coroutine_threadsafe(self.protocol.play(board, limit, game=game, searchmoves=searchmoves, options=options), self.protocol.loop).result()

    def analyse(self, board, limit, *, multipv=None, game=None, searchmoves=None, options={}):
        return asyncio.run_coroutine_threadsafe(self.protocol.analyse(board, limit, multipv=multipv, game=game, searchmoves=searchmoves, options=options), self.protocol.loop).result()

    def analysis(self, board, limit=None, *, multipv=None, game=None, searchmoves=None, options={}):
        return SimpleAnalysisResult(
            asyncio.run_coroutine_threadsafe(self.protocol.analysis(board, limit, multipv=multipv, game=game, searchmoves=searchmoves, options=options), self.protocol.loop).result(),
            self.protocol.loop)

    def quit(self):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.quit(), self.timeout), self.protocol.loop).result()

    def close(self):
        """Closes the transport."""
        if self.protocol.loop.is_running():
            @asyncio.coroutine
            def close():
                LOGGER.debug("%s: Closing transport ...", self.protocol)
                self.transport.close()
                yield from self.protocol.returncode
            return asyncio.run_coroutine_threadsafe(close(), self.protocol.loop).result()
        else:
            self.transport.close()

    @classmethod
    def popen_uci(cls, command, *, timeout=10.0, setpgrp=False, **popen_args):
        """
        Spawns and initializes an UCI engine.
        Returns a :class:`~chess.engine.SimpleEngine` instance.
        """
        @asyncio.coroutine
        def background(future):
            transport, protocol = yield from asyncio.wait_for(UciProtocol.popen(command, setpgrp=setpgrp, **popen_args), timeout)
            future.set_result(cls(transport, protocol, timeout=timeout))
            yield from protocol.returncode

        return run_in_background(background)

    @classmethod
    def popen_xboard(cls, command, *, timeout=10.0, setpgrp=False, **popen_args):
        """
        Spawns and initializes an XBoard engine.
        Returns a :class:`~chess.engine.SimpleEngine` instance.
        """
        @asyncio.coroutine
        def background(future):
            transport, protocol = yield from asyncio.wait_for(XBoardProtocol.popen(command, setpgrp=setpgrp, **popen_args), timeout)
            future.set_result(cls(transport, protocol, timeout=timeout))
            yield from protocol.returncode

        return run_in_background(background)

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.close()


class SimpleAnalysisResult:
    """
    Synchronous wrapper around :class:`~chess.engine.AnalysisResult`. Returned
    by :func:`chess.engine.SimpleEngine.analysis()`.
    """

    def __init__(self, inner, loop):
        self.inner = inner
        self.loop = loop

    @property
    def info(self):
        @asyncio.coroutine
        def _get():
            return self.inner.info.copy()
        return asyncio.run_coroutine_threadsafe(_get(), self.loop).result()

    @property
    def multipv(self):
        @asyncio.coroutine
        def _get():
            return [info.copy() for info in self.inner.multipv]
        return asyncio.run_coroutine_threadsafe(_get(), self.loop).result()

    def stop(self):
        self.loop.call_soon_threadsafe(self.inner.stop)

    def wait(self):
        return asyncio.run_coroutine_threadsafe(self.inner.wait(), self.loop).result()

    def next(self):
        return asyncio.run_coroutine_threadsafe(self.inner.next(), self.loop).result()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return asyncio.run_coroutine_threadsafe(self.inner.__anext__(), self.loop).result()
        except StopAsyncIteration:
            raise StopIteration

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.stop()


@asyncio.coroutine
def async_main():
    transport, engine = yield from popen_uci(sys.argv[1:])
    print(engine.options)

    yield from engine.ping()

    yield from engine.configure({
        "Contempt": 40,
    })

    import chess.variant

    board = chess.Board()
    limit = Limit(depth=20)

    #with yield from engine.analysis(board) as analysis:
    #    async for info in analysis:
    #        print("!", info)
    #        if "123" in info:
    #            break
    yield from analysis.wait()

    #try:
    #    analysis = await asyncio.wait_for(engine.analyse(board, limit), 0.1)
    #    print("ANALYSIS", analysis)
    #except asyncio.TimeoutError:
    #    print("TIMEOUT ERROR")

    #move = await engine.play(board, limit)
    #print("PLAY", move)

    yield from engine.quit()


def main():
    with SimpleEngine.popen_uci(sys.argv[1:], setpgrp=True) as engine:
        print(engine.protocol.options)

        board = chess.Board()
        with engine.analysis(board, Limit(movetime=3000)) as analysis:
            for info in analysis:
                print("!!!", analysis.multipv)
                if "123" in info:
                    break

        engine.quit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
    #asyncio.run(async_main())
