# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2018 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

from chess.engine import EngineTerminatedException
from chess.engine import EngineStateException
from chess.engine import MockProcess
from chess.engine import PopenProcess
from chess.engine import SpurProcess
from chess.engine import Option
from chess.engine import OptionMap
from chess.engine import LOGGER
from chess.engine import FUTURE_POLL_TIMEOUT
from chess.engine import _popen_engine
from chess.engine import _spur_spawn_engine

import collections
import concurrent.futures
import threading


class Score(collections.namedtuple("Score", "cp mate")):
    """A *cp* (centipawns) or *mate* score sent by an UCI engine."""
    __slots__ = ()


class BestMove(collections.namedtuple("BestMove", "bestmove ponder")):
    """A *bestmove* and *ponder* move sent by an UCI engine."""
    __slots__ = ()


class InfoHandler(object):
    """
    Chess engines may send information about their calculations with the
    *info* command. An :class:`~chess.uci.InfoHandler` instance can be used
    to aggregate or react to this information.

    >>> import chess.uci
    >>>
    >>> engine = chess.uci.popen_engine("stockfish")
    >>>
    >>> # Register a standard info handler.
    >>> info_handler = chess.uci.InfoHandler()
    >>> engine.info_handlers.append(info_handler)
    >>>
    >>> # Start a search.
    >>> engine.position(chess.Board())
    >>> engine.go(movetime=1000)
    BestMove(bestmove=Move.from_uci('e2e4'), ponder=Move.from_uci('e7e6'))
    >>>
    >>> # Retrieve the score of the mainline (PV 1) after search is completed.
    >>> # Note that the score is relative to the side to move.
    >>> info_handler.info["score"][1]
    Score(cp=34, mate=None)

    See :attr:`~chess.uci.InfoHandler.info` for a way to access this dictionary
    in a thread-safe way during search.

    If you want to be notified whenever new information is available,
    you would usually subclass the :class:`~chess.uci.InfoHandler` class:

    >>> class MyHandler(chess.uci.InfoHandler):
    ...     def post_info(self):
    ...         # Called whenever a complete info line has been processed.
    ...         print(self.info)
    ...         super(MyHandler, self).post_info()  # Release the lock
    """
    def __init__(self):
        self.lock = threading.Lock()

        self.info = {"refutation": {}, "currline": {}, "pv": {}, "score": {}}

    def depth(self, x):
        """Receives the search depth in plies."""
        self.info["depth"] = x

    def seldepth(self, x):
        """Receives the selective search depth in plies."""
        self.info["seldepth"] = x

    def time(self, x):
        """Receives a new time searched in milliseconds."""
        self.info["time"] = x

    def nodes(self, x):
        """Receives the number of nodes searched."""
        self.info["nodes"] = x

    def pv(self, moves):
        """
        Receives the principal variation as a list of moves.

        In *MultiPV* mode, this is related to the most recent *multipv* number
        sent by the engine.
        """
        self.info["pv"][self.info.get("multipv", 1)] = moves

    def multipv(self, num):
        """
        Receives a new *multipv* number, starting at 1.

        If *multipv* occurs in an info line, this is guaranteed to be called
        before *score* or *pv*.
        """
        self.info["multipv"] = num

    def score(self, cp, mate, lowerbound, upperbound):
        """
        Receives a new evaluation in *cp* (centipawns) or a *mate* score.

        *cp* may be ``None`` if no score in centipawns is available.

        *mate* may be ``None`` if no forced mate has been found. A negative
        number means the engine thinks it will get mated.

        *lowerbound* and *upperbound* are usually ``False``. If ``True``,
        the sent score is just a *lowerbound* or *upperbound*.

        In *MultiPV* mode, this is related to the most recent *multipv* number
        sent by the engine.
        """
        if not lowerbound and not upperbound:
            self.info["score"][self.info.get("multipv", 1)] = Score(cp, mate)

    def currmove(self, move):
        """
        Receives a move the engine is currently thinking about.

        The move comes directly from the engine, so the castling move
        representation depends on the *UCI_Chess960* option of the engine.
        """
        self.info["currmove"] = move

    def currmovenumber(self, x):
        """Receives a new current move number."""
        self.info["currmovenumber"] = x

    def hashfull(self, x):
        """
        Receives new information about the hash table.

        The hash table is *x* permill full.
        """
        self.info["hashfull"] = x

    def nps(self, x):
        """Receives a new nodes per second (nps) statistic."""
        self.info["nps"] = x

    def tbhits(self, x):
        """Receives a new information about the number of tablebase hits."""
        self.info["tbhits"] = x

    def cpuload(self, x):
        """Receives a new *cpuload* information in permill."""
        self.info["cpuload"] = x

    def string(self, string):
        """Receives a string the engine wants to display."""
        self.info["string"] = string

    def refutation(self, move, refuted_by):
        """
        Receives a new refutation of a move.

        *refuted_by* may be a list of moves representing the mainline of the
        refutation or ``None`` if no refutation has been found.

        Engines should only send refutations if the *UCI_ShowRefutations*
        option has been enabled.
        """
        self.info["refutation"][move] = refuted_by

    def currline(self, cpunr, moves):
        """
        Receives a new snapshot of a line that a specific CPU is calculating.

        *cpunr* is an integer representing a specific CPU and *moves* is a list
        of moves.
        """
        self.info["currline"][cpunr] = moves

    def ebf(self, ebf):
        """Receives the effective branching factor."""
        self.info["ebf"] = ebf

    def pre_info(self, line):
        """
        Receives new info lines before they are processed.

        When subclassing, remember to call this method on the parent class
        to keep the locking intact.
        """
        self.lock.acquire()
        self.info.pop("multipv", None)

    def post_info(self):
        """
        Processing of a new info line has been finished.

        When subclassing, remember to call this method on the parent class
        to keep the locking intact.
        """
        self.lock.release()

    def on_bestmove(self, bestmove, ponder):
        """Receives a new *bestmove* and a new *ponder* move."""
        pass

    def on_go(self):
        """
        Notified when a *go* command is beeing sent.

        Since information about the previous search is invalidated, the
        dictionary with the current information will be cleared.
        """
        with self.lock:
            self.info.clear()
            self.info["refutation"] = {}
            self.info["currline"] = {}
            self.info["pv"] = {}
            self.info["score"] = {}

    def acquire(self, blocking=True):
        return self.lock.acquire(blocking)

    def release(self):
        return self.lock.release()

    def __enter__(self):
        self.acquire()
        return self.info

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


class Engine(object):
    def __init__(self, Executor=concurrent.futures.ThreadPoolExecutor):
        self.idle = True
        self.pondering = False
        self.state_changed = threading.Condition()
        self.semaphore = threading.Semaphore()
        self.search_started = threading.Event()

        self.board = chess.Board()
        self.uci_chess960 = None
        self.uci_variant = None

        self.name = None
        self.author = None
        self.options = OptionMap()
        self.uciok = threading.Event()
        self.uciok_received = threading.Condition()

        self.readyok_received = threading.Condition()

        self.bestmove = None
        self.ponder = None
        self.bestmove_received = threading.Event()

        self.return_code = None
        self.terminated = threading.Event()

        self.info_handlers = []

        self.pool = Executor(max_workers=3)
        self.process = None

    def on_process_spawned(self, process):
        self.process = process

    def send_line(self, line):
        LOGGER.debug("%s << %s", self.process, line)
        return self.process.send_line(line)

    def on_line_received(self, buf):
        LOGGER.debug("%s >> %s", self.process, buf)

        command_and_args = buf.split(None, 1)
        if not command_and_args:
            return

        if len(command_and_args) >= 1:
            if command_and_args[0] == "uciok":
                return self._uciok()
            elif command_and_args[0] == "readyok":
                return self._readyok()

        if len(command_and_args) >= 2:
            if command_and_args[0] == "id":
                return self._id(command_and_args[1])
            elif command_and_args[0] == "bestmove":
                return self._bestmove(command_and_args[1])
            elif command_and_args[0] == "copyprotection":
                return self._copyprotection(command_and_args[1])
            elif command_and_args[0] == "registration":
                return self._registration(command_and_args[1])
            elif command_and_args[0] == "info":
                return self._info(command_and_args[1])
            elif command_and_args[0] == "option":
                return self._option(command_and_args[1])

    def on_terminated(self):
        self.return_code = self.process.wait_for_return_code()
        self.pool.shutdown(wait=False)
        self.terminated.set()

        # Wake up waiting commands.
        self.bestmove_received.set()
        with self.uciok_received:
            self.uciok_received.notify_all()
        with self.readyok_received:
            self.readyok_received.notify_all()
        with self.state_changed:
            self.state_changed.notify_all()

    def _id(self, arg):
        property_and_arg = arg.split(None, 1)
        if property_and_arg[0] == "name":
            if len(property_and_arg) >= 2:
                self.name = property_and_arg[1]
            else:
                self.name = ""
            return
        elif property_and_arg[0] == "author":
            if len(property_and_arg) >= 2:
                self.author = property_and_arg[1]
            else:
                self.author = ""
            return

    def _uciok(self):
        # Set UCI_Chess960 and UCI_Variant default value.
        if self.uci_chess960 is None and "UCI_Chess960" in self.options:
            self.uci_chess960 = self.options["UCI_Chess960"].default
        if self.uci_variant is None and "UCI_Variant" in self.options:
            self.uci_variant = self.options["UCI_Variant"].default

        self.uciok.set()

        with self.uciok_received:
            self.uciok_received.notify_all()

    def _readyok(self):
        with self.readyok_received:
            self.readyok_received.notify_all()

    def _bestmove(self, arg):
        tokens = arg.split(None, 2)

        self.bestmove = None
        if tokens[0] != "(none)":
            try:
                self.bestmove = self.board.parse_uci(tokens[0])
            except ValueError:
                LOGGER.exception("exception parsing bestmove")

        self.ponder = None
        if self.bestmove is not None and len(tokens) >= 3 and tokens[1] == "ponder" and tokens[2] != "(none)":
            # The ponder move must be legal after the bestmove. Generally, we
            # trust the engine on this. But we still have to convert
            # non-UCI_Chess960 castling moves.
            try:
                self.ponder = chess.Move.from_uci(tokens[2])
                if self.ponder.from_square in [chess.E1, chess.E8] and self.ponder.to_square in [chess.C1, chess.C8, chess.G1, chess.G8]:
                    # Make a copy of the board to avoid race conditions.
                    board = self.board.copy(stack=False)
                    board.push(self.bestmove)
                    self.ponder = board.parse_uci(tokens[2])
            except ValueError:
                LOGGER.exception("exception parsing bestmove ponder")
                self.ponder = None

        self.bestmove_received.set()

        for info_handler in self.info_handlers:
            info_handler.on_bestmove(self.bestmove, self.ponder)

    def _copyprotection(self, arg):
        LOGGER.error("engine copyprotection not supported")

    def _registration(self, arg):
        LOGGER.error("engine registration not supported")

    def _info(self, arg):
        if not self.info_handlers:
            return

        # Notify info handlers of start.
        for info_handler in self.info_handlers:
            info_handler.pre_info(arg)

        # Initialize parser state.
        board = None
        pv = None
        score_kind = None
        score_cp = None
        score_mate = None
        score_lowerbound = False
        score_upperbound = False
        refutation_move = None
        refuted_by = []
        currline_cpunr = None
        currline_moves = []
        string = []

        def end_of_parameter():
            # Parameters with variable length can only be handled when the
            # next parameter starts or at the end of the line.

            if pv is not None:
                for info_handler in self.info_handlers:
                    info_handler.pv(pv)

            if score_cp is not None or score_mate is not None:
                for info_handler in self.info_handlers:
                    info_handler.score(score_cp, score_mate, score_lowerbound, score_upperbound)

            if refutation_move is not None:
                if refuted_by:
                    for info_handler in self.info_handlers:
                        info_handler.refutation(refutation_move, refuted_by)
                else:
                    for info_handler in self.info_handlers:
                        info_handler.refutation(refutation_move, None)

            if currline_cpunr is not None:
                for info_handler in self.info_handlers:
                    info_handler.currline(currline_cpunr, currline_moves)

        def handle_integer_token(token, fn):
            try:
                intval = int(token)
            except ValueError:
                LOGGER.exception("exception parsing integer token from info: %r", arg)
                return

            for info_handler in self.info_handlers:
                fn(info_handler, intval)

        def handle_float_token(token, fn):
            try:
                floatval = float(token)
            except ValueError:
                LOGGER.exception("exception parsing float token from info: %r", arg)

            for info_handler in self.info_handlers:
                fn(info_handler, floatval)

        def handle_move_token(token, fn):
            try:
                move = chess.Move.from_uci(token)
            except ValueError:
                LOGGER.exception("exception parsing move token from info: %r", arg)
                return

            for info_handler in self.info_handlers:
                fn(info_handler, move)

        # Find multipv parameter first.
        if "multipv" in arg:
            current_parameter = None
            for token in arg.split(" "):
                if token == "string":
                    break

                if current_parameter == "multipv":
                    handle_integer_token(token, lambda handler, val: handler.multipv(val))

                current_parameter = token

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
                score_mate = None
                score_cp = None
                score_lowerbound = False
                score_upperbound = False
                refutation_move = None
                refuted_by = []
                currline_cpunr = None
                currline_moves = []

                if current_parameter == "pv":
                    pv = []

                if current_parameter in ["refutation", "pv", "currline"]:
                    board = self.board.copy(stack=False)
            elif current_parameter == "depth":
                handle_integer_token(token, lambda handler, val: handler.depth(val))
            elif current_parameter == "seldepth":
                handle_integer_token(token, lambda handler, val: handler.seldepth(val))
            elif current_parameter == "time":
                handle_integer_token(token, lambda handler, val: handler.time(val))
            elif current_parameter == "nodes":
                handle_integer_token(token, lambda handler, val: handler.nodes(val))
            elif current_parameter == "pv":
                try:
                    pv.append(board.push_uci(token))
                except ValueError:
                    LOGGER.exception("exception parsing pv from info: %r, position at root: %s", arg, self.board.fen())
            elif current_parameter == "multipv":
                # Ignore multipv. It was already parsed before anything else.
                pass
            elif current_parameter == "score":
                if token in ["cp", "mate"]:
                    score_kind = token
                elif token == "lowerbound":
                    score_lowerbound = True
                elif token == "upperbound":
                    score_upperbound = True
                elif score_kind == "cp":
                    try:
                        score_cp = int(token)
                    except ValueError:
                        LOGGER.exception("exception parsing score cp value from info: %r", arg)
                elif score_kind == "mate":
                    try:
                        score_mate = int(token)
                    except ValueError:
                        LOGGER.exception("exception parsing score mate value from info: %r", arg)
            elif current_parameter == "currmove":
                handle_move_token(token, lambda handler, val: handler.currmove(val))
            elif current_parameter == "currmovenumber":
                handle_integer_token(token, lambda handler, val: handler.currmovenumber(val))
            elif current_parameter == "hashfull":
                handle_integer_token(token, lambda handler, val: handler.hashfull(val))
            elif current_parameter == "nps":
                handle_integer_token(token, lambda handler, val: handler.nps(val))
            elif current_parameter == "tbhits":
                handle_integer_token(token, lambda handler, val: handler.tbhits(val))
            elif current_parameter == "cpuload":
                handle_integer_token(token, lambda handler, val: handler.cpuload(val))
            elif current_parameter == "refutation":
                try:
                    if refutation_move is None:
                        refutation_move = board.push_uci(token)
                    else:
                        refuted_by.append(board.push_uci(token))
                except ValueError:
                    LOGGER.exception("exception parsing refutation from info: %r, position at root: %s", arg, self.board.fen())
            elif current_parameter == "currline":
                try:
                    if currline_cpunr is None:
                        currline_cpunr = int(token)
                    else:
                        currline_moves.append(board.push_uci(token))
                except ValueError:
                    LOGGER.exception("exception parsing currline from info: %r, position at root: %s", arg, self.board.fen())
            elif current_parameter == "ebf":
                handle_float_token(token, lambda handler, val: handler.ebf(val))

        end_of_parameter()

        if string:
            for info_handler in self.info_handlers:
                info_handler.string(" ".join(string))

        # Notify info handlers of end.
        for info_handler in self.info_handlers:
            info_handler.post_info()

    def _option(self, arg):
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

        type = " ".join(type)

        default = " ".join(default)
        if type == "check":
            if default == "true":
                default = True
            elif default == "false":
                default = False
            else:
                default = None
        elif type == "spin":
            try:
                default = int(default)
            except ValueError:
                LOGGER.exception("exception parsing option spin default")
                default = None

        option = Option(" ".join(name), type, default, min, max, var)
        self.options[option.name] = option

    def _queue_command(self, command, async_callback):
        try:
            future = self.pool.submit(command)
        except RuntimeError:
            raise EngineTerminatedException()

        if async_callback is True:
            return future
        elif async_callback:
            future.add_done_callback(async_callback)
            return future
        else:
            # Avoid calling future.result() without a timeout. In Python 2
            # such a call cannot be interrupted.
            while True:
                try:
                    return future.result(timeout=FUTURE_POLL_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    pass

    def uci(self, async_callback=None):
        """
        Tells the engine to use the UCI interface.

        This is mandatory before any other command. A conforming engine will
        send its name, authors and available options.

        :return: Nothing
        """
        def command():
            with self.semaphore:
                with self.uciok_received:
                    self.send_line("uci")
                    self.uciok_received.wait()

                    if self.terminated.is_set():
                        raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def debug(self, on, async_callback=None):
        """
        Switch the debug mode on or off.

        In debug mode, the engine should send additional information to the
        GUI to help with the debugging. Usually, this mode is off by default.

        :param on: bool

        :return: Nothing
        """
        def command():
            with self.semaphore:
                if on:
                    self.send_line("debug on")
                else:
                    self.send_line("debug off")

        return self._queue_command(command, async_callback)

    def isready(self, async_callback=None):
        """
        Command used to synchronize with the engine.

        The engine will respond as soon as it has handled all other queued
        commands.

        :return: Nothing
        """
        def command():
            with self.semaphore:
                with self.readyok_received:
                    self.send_line("isready")
                    self.readyok_received.wait()

                    if self.terminated.is_set():
                        raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def _setoption(self, options):
        option_lines = []

        for name, value in options.items():
            if name.lower() == "uci_chess960":
                self.uci_chess960 = value
            if name.lower() == "uci_variant":
                self.uci_variant = value.lower()

            builder = ["setoption name", name, "value"]
            if value is True:
                builder.append("true")
            elif value is False:
                builder.append("false")
            elif value is None:
                builder.append("none")
            else:
                builder.append(str(value))

            option_lines.append(" ".join(builder))

        return option_lines

    def setoption(self, options, async_callback=None):
        """
        Set values for the engine's available options.

        :param options: A dictionary with option names as keys.

        :return: Nothing
        """
        option_lines = self._setoption(options)

        def command():
            with self.semaphore:
                with self.readyok_received:
                    for option_line in option_lines:
                        self.send_line(option_line)

                    self.send_line("isready")
                    self.readyok_received.wait()

                    if self.terminated.is_set():
                        raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def ucinewgame(self, async_callback=None):
        """
        Tell the engine that the next search will be from a different game.

        This can be a new game the engine should play or if the engine should
        analyse a position from a different game. Using this command is
        recommended, but not required.

        :return: Nothing
        """
        # Warn if this is called while the engine is still calculating.
        with self.state_changed:
            if not self.idle:
                LOGGER.warning("ucinewgame while engine is busy")

        def command():
            with self.semaphore:
                with self.readyok_received:
                    self.send_line("ucinewgame")

                    self.send_line("isready")
                    self.readyok_received.wait()

                    if self.terminated.is_set():
                        raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def position(self, board, async_callback=None):
        """
        Set up a given position.

        Rather than sending just the final FEN, the initial FEN and all moves
        leading up to the position will be sent. This will allow the engine
        to use the move history (for example to detect repetitions).

        If the position is from a new game, it is recommended to use the
        *ucinewgame* command before the *position* command.

        :param board: A *chess.Board*.

        :return: Nothing

        :raises: :exc:`~chess.uci.EngineStateException` if the engine is still
            calculating.
        """
        # Raise if this is called while the engine is still calculating.
        with self.state_changed:
            if not self.idle:
                raise EngineStateException("position command while engine is busy")

        # Set UCI_Variant and UCI_Chess960.
        options = {}

        uci_variant = type(board).uci_variant
        if uci_variant != (self.uci_variant or "chess"):
            if self.uci_variant is None:
                LOGGER.warning("engine may not support UCI_Variant or has not been initialized with 'uci' command")
            options["UCI_Variant"] = type(board).uci_variant

        if bool(self.uci_chess960) != board.chess960:
            if self.uci_chess960 is None:
                LOGGER.warning("engine may not support UCI_Chess960 or has not been initialized with 'uci' command")
            options["UCI_Chess960"] = board.chess960

        option_lines = self._setoption(options)

        # Send starting position.
        builder = ["position"]
        root = board.root()
        fen = root.fen()
        if uci_variant == "chess" and fen == chess.STARTING_FEN:
            builder.append("startpos")
        else:
            builder.append("fen")
            builder.append(root.shredder_fen() if self.uci_chess960 else fen)

        # Send moves.
        if board.move_stack:
            builder.append("moves")
            builder.extend(move.uci() for move in board.move_stack)

        self.board = board.copy(stack=False)

        def command():
            with self.semaphore:
                for option_line in option_lines:
                    self.send_line(option_line)

                self.send_line(" ".join(builder))

                if self.terminated.is_set():
                    raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def go(self, searchmoves=None, ponder=False, wtime=None, btime=None, winc=None, binc=None, movestogo=None, depth=None, nodes=None, mate=None, movetime=None, infinite=False, async_callback=None):
        """
        Start calculating on the current position.

        All parameters are optional, but there should be at least one of
        *depth*, *nodes*, *mate*, *infinite* or some time control settings,
        so that the engine knows how long to calculate.

        Note that when using *infinite* or *ponder*, the engine will not stop
        until it is told to.

        :param searchmoves: Restrict search to moves in this list.
        :param ponder: Bool to enable pondering mode. The engine will not stop
            pondering in the background until a *stop* command is received.
        :param wtime: Integer of milliseconds White has left on the clock.
        :param btime: Integer of milliseconds Black has left on the clock.
        :param winc: Integer of white Fisher increment.
        :param binc: Integer of black Fisher increment.
        :param movestogo: Number of moves to the next time control. If this is
            not set, but wtime or btime are, then it is sudden death.
        :param depth: Search *depth* ply only.
        :param nodes: Search so many *nodes* only.
        :param mate: Search for a mate in *mate* moves.
        :param movetime: Integer. Search exactly *movetime* milliseconds.
        :param infinite: Search in the background until a *stop* command is
            received.

        :return: A tuple of two elements. The first is the best move according
            to the engine. The second is the ponder move. This is the reply
            as sent by the engine. Either of the elements may be ``None``.

        :raises: :exc:`~chess.uci.EngineStateException` if the engine is
            already calculating.
        """
        with self.state_changed:
            if not self.idle:
                raise EngineStateException("go command while engine is already busy")

            self.idle = False
            self.search_started.clear()
            self.bestmove_received.clear()
            self.pondering = ponder
            self.state_changed.notify_all()

        for info_handler in self.info_handlers:
            info_handler.on_go()

        builder = ["go"]

        if ponder:
            builder.append("ponder")

        if wtime is not None:
            builder.append("wtime")
            builder.append(str(int(wtime)))

        if btime is not None:
            builder.append("btime")
            builder.append(str(int(btime)))

        if winc is not None:
            builder.append("winc")
            builder.append(str(int(winc)))

        if binc is not None:
            builder.append("binc")
            builder.append(str(int(binc)))

        if movestogo is not None and movestogo > 0:
            builder.append("movestogo")
            builder.append(str(int(movestogo)))

        if depth is not None:
            builder.append("depth")
            builder.append(str(int(depth)))

        if nodes is not None:
            builder.append("nodes")
            builder.append(str(int(nodes)))

        if mate is not None:
            builder.append("mate")
            builder.append(str(int(mate)))

        if movetime is not None:
            builder.append("movetime")
            builder.append(str(int(movetime)))

        if infinite:
            builder.append("infinite")

        if searchmoves:
            builder.append("searchmoves")
            for move in searchmoves:
                builder.append(self.board.uci(move))

        def command():
            with self.semaphore:
                self.send_line(" ".join(builder))
                self.search_started.set()

            self.bestmove_received.wait()

            with self.state_changed:
                self.idle = True
                self.state_changed.notify_all()

            if self.terminated.is_set():
                raise EngineTerminatedException()

            return BestMove(self.bestmove, self.ponder)

        return self._queue_command(command, async_callback)

    def stop(self, async_callback=None):
        """
        Stop calculating as soon as possible.

        :return: Nothing.
        """
        # Only send stop when the engine is actually searching.
        def command():
            with self.semaphore:
                with self.state_changed:
                    if not self.idle:
                        self.search_started.wait()

                    backoff = 0.5
                    while not self.bestmove_received.is_set() and not self.terminated.is_set():
                        if self.idle:
                            break
                        else:
                            self.send_line("stop")
                        self.bestmove_received.wait(backoff)
                        backoff *= 2

                    self.idle = True
                    self.state_changed.notify_all()

                if self.terminated.is_set():
                    raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def ponderhit(self, async_callback=None):
        """
        May be sent if the expected ponder move has been played.

        The engine should continue searching, but should switch from pondering
        to normal search.

        :return: Nothing.

        :raises: :exc:`~chess.uci.EngineStateException` if the engine is not
            currently searching in ponder mode.
        """
        with self.state_changed:
            if self.idle:
                raise EngineStateException("ponderhit but not searching")
            if not self.pondering:
                raise EngineStateException("ponderhit but not pondering")

            self.pondering = False
            self.state_changed.notify_all()

        def command():
            self.search_started.wait()
            with self.semaphore:
                self.send_line("ponderhit")

        return self._queue_command(command, async_callback)

    def quit(self, async_callback=None):
        """
        Quit the engine as soon as possible.

        :return: The return code of the engine process.
        """
        def command():
            with self.semaphore:
                self.send_line("quit")

                self.terminated.wait()
                return self.return_code

        return self._queue_command(command, async_callback)

    def _queue_termination(self, async_callback):
        def wait():
            self.terminated.wait()
            return self.return_code

        try:
            return self._queue_command(wait, async_callback)
        except EngineTerminatedException:
            assert self.terminated.is_set()

            future = concurrent.futures.Future()
            future.set_result(self.return_code)
            if async_callback is True:
                return future
            elif async_callback:
                future.add_done_callback(async_callback)
            else:
                return future.result()

    def terminate(self, async_callback=None):
        """
        Terminate the engine.

        This is not an UCI command. It instead tries to terminate the engine
        on operating system level, like sending SIGTERM on Unix
        systems. If possible, first try the *quit* command.

        :return: The return code of the engine process (or a Future).
        """
        self.process.terminate()
        return self._queue_termination(async_callback)

    def kill(self, async_callback=None):
        """
        Kill the engine.

        Forcefully kill the engine process, like by sending SIGKILL.

        :return: The return code of the engine process (or a Future).
        """
        self.process.kill()
        return self._queue_termination(async_callback)

    def is_alive(self):
        """Poll the engine process to check if it is alive."""
        return self.process.is_alive()


def popen_engine(command, engine_cls=Engine, setpgrp=False, _popen_lock=threading.Lock(), **kwargs):
    """
    Opens a local chess engine process.

    No initialization commands are sent, so do not forget to send the
    mandatory *uci* command.

    >>> engine = chess.uci.popen_engine("/usr/bin/stockfish")
    >>> engine.uci()
    >>> engine.name
    'Stockfish 8 64 POPCNT'
    >>> engine.author
    'T. Romstad, M. Costalba, J. Kiiski, G. Linscott'

    :param command:
    :param engine_cls:
    :param setpgrp: Open the engine process in a new process group. This will
        stop signals (such as keyboard interrupts) from propagating from the
        parent process. Defaults to ``False``.
    """
    return _popen_engine(command, engine_cls, setpgrp, _popen_lock, **kwargs)


def spur_spawn_engine(shell, command, engine_cls=Engine):
    """
    Spawns a remote engine using a `Spur`_ shell.

    >>> import spur
    >>>
    >>> shell = spur.SshShell(hostname="localhost", username="username", password="pw")
    >>> engine = chess.uci.spur_spawn_engine(shell, ["/usr/bin/stockfish"])
    >>> engine.uci()

    .. _Spur: https://pypi.python.org/pypi/spur
    """
    return _spur_spawn_engine(shell, command, engine_cls)
