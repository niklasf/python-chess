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

from __future__ import print_function
from __future__ import unicode_literals

import chess
import collections
import signal
import subprocess
import threading

try:
    import queue
except ImportError:
    import Queue as queue


POLL_TIMEOUT = 5
STOP_TIMEOUT = 2


class Option(collections.namedtuple("Option", ["name", "type", "default", "min", "max", "var"])):
    """Information about an available option for an UCI engine."""


class Score(collections.namedtuple("Score", ["cp", "mate", "lowerbound", "upperbound"])):
    """A centipawns or mate score sent by an UCI engine."""


class InfoHandler(object):
    def __init__(self):
        self.lock = threading.Lock()

        self.info = {}
        self.info["refutation"] = {}
        self.info["currline"] = {}
        self.info["pv"] = {}

    def depth(self, x):
        """Received search depth in plies."""
        self.info["depth"] = x

    def seldepth(self, x):
        """Received selective search depth in plies."""
        self.info["seldepth"] = x

    def time(self, x):
        """Received new time searched in milliseconds."""
        self.info["time"] = x

    def nodes(self, x):
        """Received number of nodes searched."""
        self.info["nodes"] = x

    def pv(self, moves):
        """
        Received the principal variation as a list of moves.

        In MultiPV mode this is related to the most recent *multipv* number
        sent by the engine.
        """
        self.info["pv"][self.info.get("multipv", 1)] = moves

    def multipv(self, num):
        """Received a new multipv number, starting at 1."""
        self.info["multipv"] = num

    def score(self, cp, mate, lowerbound, upperbound):
        """
        Received a new evaluation in centipawns or a mate score.

        *cp* may be *None* if no score in centipawns is available.

        *mate* may be *None* if no forced mate has been found. A negative
        numbers means the engine thinks it will get mated.

        lowerbound and upperbound are usually *False*. If *True*, the sent
        score are just a lowerbound or upperbound.
        """
        self.info["score"] = Score(cp, mate, lowerbound, upperbound)

    def currmove(self, move):
        """Received a move the engine is currently thinking about."""
        self.info["currmove"] = move

    def currmovenumber(self, x):
        """Received a new currmovenumber."""
        self.info["currmovenumber"] = x

    def hashfull(self, x):
        """
        Received new information about the hashtable.

        The hashtable is x permill full.
        """
        self.info["hashfull"] = x

    def nps(self, x):
        """Received new nodes per second statistic."""
        self.info["nps"] = x

    def tbhits(self, x):
        """Received new information about the number of table base hits."""
        self.info["tbhits"] = x

    def cpuload(self, x):
        """Received new cpuload information in permill."""
        self.info["cpuload"] = x

    def string(self, string):
        """Received a string the engine wants to display."""
        self.info["string"] = string

    def refutation(self, move, refuted_by):
        """
        Received a new refutation of a move.

        *refuted_by* may be a list of moves representing the mainline of the
        refutation or *None* if no refutation has been found.

        Engines should only send refutations if the *UCI_ShowRefutations*
        option has been enabled.
        """
        self.info["refutation"][move] = refuted_by

    def currline(self, cpunr, moves):
        """
        Received a new snapshot of a line a specific CPU is calculating.

        *cpunr* is an integer representing a specific CPU. *moves* is a list
        of moves.
        """
        self.info["currline"][cpunr] = moves

    def pre_info(self, line):
        """
        Received a new info line about to be processed.

        When subclassing remember to call this method of the parent class in
        order to keep the locking in tact.
        """
        self.lock.acquire()

    def post_info(self):
        """
        Processing of a new info line has been finished.

        When subclassing remember to call this method of the parent class in
        order to keep the locking in tact.
        """
        self.lock.release()

    def pre_bestmove(self, line):
        """A new bestmove command is about to be processed."""
        pass

    def on_bestmove(self, bestmove, ponder):
        """A new bestmove and pondermove have been received."""
        pass

    def post_bestmove(self):
        """
        A new bestmove command was processed.

        Since this indicates that the current search has been finished the
        dictionary with the current information will be cleared.
        """
        with self.lock:
            self.info.clear()
            self.info["refutation"] = {}
            self.info["currline"] = {}
            self.info["pv"] = {}

    def acquire(self, blocking=True):
        return self.lock.acquire(blocking)

    def release(self):
        return self.lock.release()

    def __enter__(self):
        self.lock.acquire()
        return self.info

    def __exit__(self, type, value, traceback):
        self.lock.release()


class Command(object):
    """Information about the state of a command."""

    def __init__(self, callback=None):
        self.result = None

        self._callback = callback
        self._event = threading.Event()

    def _notify(self, result):
        self.result = result
        self._event.set()
        self._notify_callback()

    def _notify_callback(self):
        if self._callback and not self._callback is True:
            try:
                iter(self.result)
            except TypeError:
                self._callback(self.result)
                return
            self._callback(*self.result)

    def _wait_or_callback(self):
        if not self._callback:
            return self.wait()
        else:
            return self

    def wait(self, timeout=None):
        """
        Wait for the command to be completed.

        This may wait forever unless a floating point number of seconds is
        specified as the timeout. Raises *TimeoutError* if a timeout is indeed
        encountered.
        """
        if not self._event.wait(timeout):
            raise TimeoutError("waiting for uci command timed out")
        return self.result

    def is_done(self):
        """Checks if the command has been completed yet."""
        return self._event.is_set()


class UciCommand(Command):
    def __init__(self, callback=None):
        super(UciCommand, self).__init__(callback)

    def _execute(self, engine):
        engine.uciok.clear()
        engine._send("uci\n")
        engine.uciok.wait()
        self._notify(())


class DebugCommand(Command):
    def __init__(self, on, callback=None):
        super(DebugCommand, self).__init__(callback)
        self.on = on

    def _execute(self, engine):
        if self.on:
            engine._send("debug on\n")
        else:
            engine._send("debug off\n")
        self._notify(())


class IsReadyCommand(Command):
    def __init__(self, callback=None):
        super(IsReadyCommand, self).__init__(callback)

    def _execute(self, engine):
        engine.readyok.clear()
        engine._send("isready\n")
        engine.readyok.wait()
        self._notify(())


class SetOptionCommand(IsReadyCommand):
    def __init__(self, options, callback=None):
        super(SetOptionCommand, self).__init__(callback)

        builder = []

        for name, value in options.items():
            builder.append("setoption name ")
            builder.append(name)
            builder.append(" value ")
            if value is True:
                builder.append("true")
            elif value is False:
                builder.append("false")
            elif value is None:
                builder.append("none")
            else:
                builder.append(str(value))
            builder.append("\n")

        self.buf = "".join(builder)

    def _execute(self, engine):
        engine._send(self.buf)
        super(SetOptionCommand, self)._execute(engine)


class UciNewGameCommand(IsReadyCommand):
    def __init__(self, callback=None):
        super(UciNewGameCommand, self).__init__(callback)

    def _execute(self, engine):
        engine._send("ucinewgame\n")
        super(UciNewGameCommand, self)._execute(engine)


class PositionCommand(IsReadyCommand):
    def __init__(self, board, callback=None):
        super(PositionCommand, self).__init__(callback)

        builder = []
        builder.append("position")

        switchyard = collections.deque()
        while board.move_stack:
            switchyard.append(board.pop())

        fen = board.fen()
        if fen == chess.STARTING_FEN:
            builder.append("startpos")
        else:
            builder.append("fen")
            builder.append(fen)

        if switchyard:
            builder.append("moves")

            while switchyard:
                move = switchyard.pop()
                builder.append(move.uci())
                board.push(move)

        self.buf = " ".join(builder) + "\n"

    def _execute(self, engine):
        engine._send(self.buf)
        super(PositionCommand, self)._execute(engine)


class GoCommand(Command):
    def __init__(self, searchmoves=None, ponder=False, wtime=None, btime=None, winc=None, binc=None, movestogo=None, depth=None, nodes=None, mate=None, movetime=None, infinite=False, callback=None):
        super(GoCommand, self).__init__(callback)

        builder = []
        builder.append("go")

        if searchmoves:
            builder.append("searchmoves")
            for move in searchmoves:
                builder.append(move.uci())

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

        self.infinite = infinite
        if infinite:
            builder.append("infinite")

        self.buf = " ".join(builder) + "\n"

    def _execute(self, engine):
        engine.bestmove = None
        engine.ponder = None
        engine.bestmove_received.clear()
        engine._send(self.buf)
        if self.infinite:
            self._notify(())
        else:
            engine.bestmove_received.wait()
            self._notify((engine.bestmove, engine.ponder))


class StopCommand(Command):
    def __init__(self, callback=None):
        super(StopCommand, self).__init__(callback)

    def _execute(self, engine):
        engine.readyok.clear()
        engine._send("stop\n")
        engine._send("isready\n")
        engine.readyok.wait()
        engine.bestmove_received.wait(STOP_TIMEOUT)
        self._notify((engine.bestmove, engine.ponder))


class PonderhitCommand(IsReadyCommand):
    def __init__(self, debug, callback=None):
        super(PonderhitCommand, self).__init__(callback)

    def _execute(self, engine):
        engine._send("ponderhit\n")
        super(PonderhitCommand, self)._execute(engine)


class QuitCommand(Command):
    def __init__(self, engine, callback=None):
        self.engine = engine
        self._callback = callback

    def _execute(self, engine):
        assert self.engine == engine
        engine._send("quit\n")
        engine.terminated.wait()
        engine._close_fds()
        self._notify_callback()

    @property
    def result(self):
        return self.engine.returncode

    def wait(self, timeout=None):
        if not self.engine.terminated.wait(timeout):
            raise TimeoutError("waiting for engine termination timed out")
        return self.result

    def is_done(self):
        return self.engine.terminated.is_set()


class Engine(object):
    def __init__(self, process):
        super(Engine, self).__init__()
        self.process = process

        self.name = None
        self.author = None
        self.options = {}
        self.uciok = threading.Event()

        self.readyok = threading.Event()

        self.bestmove = None
        self.ponder = None
        self.bestmove_received = threading.Event()

        self.queue = queue.Queue()
        self.stdin_thread = threading.Thread(target=self._stdin_thread_target)
        self.stdin_thread.daemon = True
        self.stdin_thread.start()

        self.stdout_thread = threading.Thread(target=self._stdout_thread_target)
        self.stdout_thread.daemon = True
        self.stdout_thread.start()

        self.returncode = None
        self.terminated = threading.Event()

        self.info_handlers = []

    def _send(self, buf):
        self.process.stdin.write(buf)
        self.process.stdin.flush()

    def _received(self, buf):
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

    def _stdin_thread_target(self):
        while self.is_alive():
            try:
                command = self.queue.get(True, POLL_TIMEOUT)
            except queue.Empty:
                continue

            if not self.is_alive():
                break

            command._execute(self)
            self.queue.task_done()

        self._close_fds()
        self._terminated()

    def _stdout_thread_target(self):
        while self.is_alive():
            line = self.process.stdout.readline()
            if not line:
                continue

            line = line.rstrip()
            self._received(line)

        self._close_fds()
        self._terminated()

    def _close_fds(self):
        self.process.stdin.close()
        self.process.stdout.close()

    def _terminated(self):
        self.returncode = self.process.returncode
        self.terminated.set()

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
        self.uciok.set()

    def _readyok(self):
        self.readyok.set()

    def _bestmove(self, arg):
        for info_handler in self.info_handlers:
            info_handler.pre_bestmove(arg)

        tokens = arg.split(None, 2)
        self.bestmove = chess.Move.from_uci(tokens[0])
        if len(tokens) >= 3 and tokens[1] == "ponder" and tokens[2] != "(none)":
            self.ponder = chess.Move.from_uci(tokens[2])
        else:
            self.ponder = None
        self.bestmove_received.set()

        for info_handler in self.info_handlers:
            info_handler.on_bestmove(self.bestmove, self.ponder)

        for info_handler in self.info_handlers:
            info_handler.post_bestmove()


    def _copyprotection(self, arg):
        # TODO: Implement copyprotection
        pass

    def _registration(self, arg):
        # TODO: Implement registration
        pass

    def _info(self, arg):
        if not self.info_handlers:
            return

        for info_handler in self.info_handlers:
            info_handler.pre_info(arg)

        current_parameter = None

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
                return

            for info_handler in self.info_handlers:
                fn(info_handler, intval)

        def handle_move_token(token, fn):
            try:
                move = chess.Move.from_uci(token)
            except ValueError:
                return

            for info_handler in self.info_handlers:
                fn(info_handler, move)

        for token in arg.split(" "):
            if current_parameter == "string":
                string.append(token)
            elif token in ("depth", "seldepth", "time", "nodes", "pv", "multipv", "score", "currmove", "currmovenumber", "hashfull", "nps", "tbhits", "cpuload", "refutation", "currline"):
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
                    pv.append(chess.Move.from_uci(token))
                except ValueError:
                    pass
            elif current_parameter == "multipv":
                handle_integer_token(token, lambda handler, val: handler.multipv(val))
            elif current_parameter == "score":
                if token in ("cp", "mate"):
                    score_kind = token
                elif token == "lowerbound":
                    score_lowerbound = True
                elif token == "upperbound":
                    score_upperbound = True
                elif score_kind == "cp":
                    try:
                        score_cp = int(token)
                    except ValueError:
                        pass
                elif score_kind == "mate":
                    try:
                        score_mate = int(token)
                    except ValueError:
                        pass
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
                        refutation_move = chess.Move.from_uci(token)
                    else:
                        refuted_by.append(chess.Move.from_uci(token))
                except ValueError:
                    pass
            elif current_parameter == "currline":
                try:
                    if currline_cpunr is None:
                        currline_cpunr = int(token)
                    else:
                        currline_moves.append(chess.Move.from_uci(token))
                except ValueError:
                    pass

        end_of_parameter()

        if string:
            for info_handler in self.info_handlers:
                info_handler.string(" ".join(string))

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
            elif current_parameter == "min":
                try:
                    min = int(token)
                except ValueError:
                    pass
            elif current_parameter == "max":
                try:
                    max = int(token)
                except ValueError:
                    pass
            elif current_parameter == "default":
                default.append(token)
            elif current_parameter == "var":
                current_var.append(token)

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
                default = None

        option = Option(" ".join(name), type, default, min, max, var)
        self.options[option.name] = option

    def queue_command(self, command):
        if self.terminated.is_set():
            raise RuntimeError('can not queue command for terminated uci engine')
        self.queue.put(command)
        return command._wait_or_callback()

    def uci(self, async_callback=None):
        """
        Tells the engine to use the UCI interface.

        This is mandatory before any other command. A conforming engine will
        send its name, authors and available options.
        """
        return self.queue_command(UciCommand(async_callback))

    def debug(self, on, async_callback=None):
        """
        Switch the debug mode on or off.

        In debug mode the engine should send additional infos to the GUI to
        help debugging. This mode should be switched off by default.

        :param on: bool

        :return: ()
        """
        return self.queue_command(DebugCommand(on, async_callback))

    def isready(self, async_callback=None):
        """
        Command used to synchronize with the engine.

        The engine will respond as soon as it has handled all other queued
        commands.

        :return: ()
        """
        return self.queue_command(IsReadyCommand(async_callback))

    def setoption(self, options, async_callback=None):
        """
        Set a values for the engines available options.

        :param options: A dictionary with option names as keys.

        :return: ()
        """
        return self.queue_command(SetOptionCommand(options, async_callback))

    # TODO: Implement register command

    def ucinewgame(self, async_callback=None):
        """
        Tell the engine that the next search will be from a different game.

        This can be a new game the engine should play or if the engine should
        analyse a position from a different game. Using this command is
        recommended but not required.

        :return: ()
        """
        return self.queue_command(UciNewGameCommand(async_callback))

    def position(self, board, async_callback=None):
        """
        Set up a given position.

        Instead of just the final FEN, the initial FEN and all moves leading
        up to the position will be sent, so that the engine can detect
        repititions.

        If the position is from a new game it is recommended to use the
        *ucinewgame* command before the *position* command.

        :param board: A *chess.Bitboard*.

        :return: ()
        """
        return self.queue_command(PositionCommand(board, async_callback))

    def go(self, searchmoves=None, ponder=False, wtime=None, btime=None, winc=None, binc=None, movestogo=None, depth=None, nodes=None, mate=None, movetime=None, infinite=False, async_callback=None):
        """
        Start calculating on the current position.

        All parameters are optional, but there should be at least one of
        *depth*, *nodes*, *mate*, *infinite* or some time control settings,
        so that the engine knows how long to calculate.

        :param searchmoves: Restrict search to moves in this list.
        :param ponder: Bool to enable pondering mode.
        :param wtime: Integer of milliseconds white has left on the clock.
        :param btime: Integer of milliseconds black has left on the clock.
        :param winc: Integer of white Fisher increment.
        :param binc: Integer of black Fisher increment.
        :param movestogo: Number of moves to the next time control. If this is
            not set, but wtime or btime are, then it is sudden death.
        :param depth: Search *depth* ply only.
        :param nodes: Search *nodes* only.
        :param mate: Search for a mate in *mate* moves.
        :param movetime: Integer. Search exactly *movetime* milliseconds.
        :param infinite: Search in the backgorund until a *stop* command is
            received.

        :return: **In normal search mode** a tuple of two elements. The first
            is the best move according to the engine. The second is the ponder
            move. This is the reply expected by the engine. Either of the
            elements may be *None*. **In infinite search mode** the result is
            () instead.
        """
        return self.queue_command(GoCommand(searchmoves, ponder, wtime, btime, winc, binc, movestogo, depth, nodes, mate, movetime, infinite, async_callback))

    def stop(self, async_callback=None):
        """
        Stop calculating as soon as possible.

        :return: A tuple of the latest best move and the ponder move. See the
            *go* command. Results of infinite searches will also be available
            here.
        """
        return self.queue_command(StopCommand(async_callback))

    def ponderhit(self, async_callback=None):
        """
        May be sent if the expected ponder move has been played.

        The engine should continue searching but should switch from pondering
        to normal search.

        :return: ()
        """
        return self.queue_command(PonderhitCommand(async_callback))

    def quit(self, async_callback=None):
        """
        Quit the engine as soon as possible.

        :return: The return code of the engine process.
        """
        return self.queue_command(QuitCommand(self, async_callback))

    def terminate(self, async=None):
        """
        Terminate the engine.

        This is not an UCI command. It instead tries to terminate the engine
        on operating system level, for example by sending SIGTERM on Unix
        systems. If possible, first try the *quit* command.

        :return: The return code of the engine process.
        """
        self._close_fds()
        self.process.terminate()
        promise = QuitCommand(self)
        if async:
            return promise
        else:
            return promise.wait()

    def kill(self, async=False):
        """
        Kill the engine.

        Forcefully kill the engine process, for example by sending SIGKILL.

        :return: The return code of the engine process.
        """
        self._close_fds()
        self.process.kill()
        promise = QuitCommand(self)
        if async:
            return promise
        else:
            return promise.wait()

    def is_alive(self):
        """Poll the engine process to check if it is alive."""
        return self.process.poll() is None


class SpurEngine(Engine):
    class StdoutHandler(object):
        def __init__(self, engine):
            self.engine = engine
            self.buf = []

        def write(self, byte):
            byte = byte.decode("utf-8")

            if byte == "\r":
                pass
            elif byte == "\n":
                self.engine._received("".join(self.buf))
                del self.buf[:]
            else:
                self.buf.append(byte)

    def __init__(self, shell, command):
        process = shell.spawn(command, store_pid=True, allow_error=True, stdout=self.StdoutHandler(self))
        super(SpurEngine, self).__init__(process)

    def _send(self, buf):
        self.process.stdin_write(buf.encode("utf-8"))

    def _close_fds(self):
        # TODO: Check if this is required.
        pass

    def _terminated(self):
        self.returncode = self.process.wait_for_result().return_code
        self.terminated.set()

    def _stdout_thread_target(self):
        self.process.wait_for_result()
        self._terminated()

    def terminate(self, async=False):
        self.process.send_signal(signal.SIGTERM)
        promise = QuitCommand(self)
        if async:
            return promise
        else:
            return promise.wait()

    def kill(self, async=False):
        self.process.send_signal(signal.SIGKILL)
        promise = QuitCommand(self)
        if async:
            return promise
        else:
            return promise.wait()

    def is_alive(self):
        return self.process.is_running()


def popen_engine(command, cls=Engine):
    """
    Opens a local chess engine process.

    No initialization commands are sent, so do not forget to send the
    mandatory *uci* command.

    >>> engine = chess.uci.popen_engine("/usr/games/stockfish")
    >>> engine.uci()
    ()
    >>> engine.name
    'Stockfish 230814 64'
    >>> engine.author
    'Tord Romstad, Marco Costalba and Joona Kiiski'

    The input and input streams will be linebuffered and able both Windows
    and Unix newlines.
    """
    return cls(subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, bufsize=1, universal_newlines=True))


def spur_spawn_engine(shell, command, cls=SpurEngine):
    """
    Spwans a remote engine using a `Spur`_ shell.

    >>> import spur
    >>> shell = spur.SshShell(hostname="localhost", username="username", password="pw")
    >>> engine = chess.uci.spur_spwan_engine(shell, ["/usr/games/stockfish"])
    >>> engine.uci()
    ()

    .. _Spur: https://pypi.python.org/pypi/spur
    """
    return cls(shell, command)
