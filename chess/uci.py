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

    def depth(self, x):
        self.info["depth"] = x

    def seldepth(self, x):
        self.info["seldepth"] = x

    def time(self, x):
        self.info["time"] = x

    def nodes(self, x):
        self.info["nodes"] = x

    def pv(self, moves):
        self.info["pv"] = moves

    def multipv(self, num):
        self.info["multipv"] = num

    def score(self, kind, x, lowerbound, upperbound):
        self.info["score"] = Score(kind, x, lowerbound, upperbound)

    def currmove(self, move):
        self.info["currmove"] = move

    def currmovenumber(self, x):
        self.info["currmovenumber"] = x

    def hashfull(self, x):
        self.info["hashfull"] = x

    def nps(self, x):
        self.info["nps"] = x

    def tbhits(self, x):
        self.info["tbhits"] = x

    def cpuload(self, x):
        self.info["cpuload"] = x

    def string(self, string):
        self.info["string"] = string

    def refutation(self, move, refuted_by):
        self.info["refutation"][move] = refuted_by

    def currline(self, cpunr, moves):
        self.info["currline"][cpunr] = moves

    def pre_info(self, line):
        self.lock.acquire()

    def post_info(self):
        self.lock.release()

    def pre_bestmove(self, line):
        pass

    def on_bestmove(self, bestmove, ponder):
        pass

    def post_bestmove(self):
        with self.lock:
            self.info.clear()
            self.info["refutation"] = {}
            self.info["currline"] = {}


class Command(object):
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
                iter(result)
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
        if not self._event.wait(timeout):
            raise TimeoutError("waiting for uci command timed out")
        return self.result

    def is_done(self):
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
    def __init__(self, debug, callback=None):
        super(DebugCommand, self).__init__(callback)
        self.debug = debug

    def _execute(self, engine):
        if self.debug:
            engine._send("debug true\n")
        else:
            engine._send("debug false\n")
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
        self.name_received = threading.Event()

        self.author = None
        self.author_received = threading.Event()

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
        print(">>>", buf.rstrip())
        self.process.stdin.write(buf)

    def _received(self, buf):
        print("<<<", buf)

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

        self._terminated()

    def _stdout_thread_target(self):
        while self.is_alive():
            line = self.process.stdout.readline()
            if not line:
                continue

            line = line.rstrip()
            self._received(line)

        self._terminated()

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
        score_mate = None
        score_cp = None
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
                if not refuted_by:
                    refuted_by = None
                for info_handler in self.info_handlers:
                    info_handler.refutation(refutation_move, refuted_by)

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
                    score_kind = "cp"
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
                handler_move_token(token, lambda handler, val: handler.currmove(val))
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
                    if cpunr is None:
                        cpunr = int(token)
                    else:
                        currline.append(chess.Move.from_uci(token))
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
                except:
                    ValueError
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
        return self.queue_command(UciCommand(async_callback))

    def debug(self, debug, async_callback=None):
        return self.queue_command(DebugCommand(debug, async_callback))

    def isready(self, async_callback=None):
        return self.queue_command(IsReadyCommand(async_callback))

    def setoption(self, options, async_callback=None):
        return self.queue_command(SetOptionCommand(options, async_callback))

    # TODO: Implement register command

    def ucinewgame(self, async_callback=None):
        return self.queue_command(UciNewGameCommand(async_callback))

    def position(self, board, async_callback=None):
        return self.queue_command(PositionCommand(board, async_callback))

    def go(self, searchmoves=None, ponder=False, wtime=None, btime=None, winc=None, binc=None, movestogo=None, depth=None, nodes=None, mate=None, movetime=None, infinite=False, async_callback=None):
        return self.queue_command(GoCommand(searchmoves, ponder, wtime, btime, winc, binc, movestogo, depth, nodes, mate, movetime, infinite, async_callback))

    def stop(self, async_callback=None):
        return self.queue_command(StopCommand(async_callback))

    def ponderhit(self, async_callback=None):
        return self.queue_command(PonderhitCommand(async_callback))

    def quit(self, async_callback=None):
        return self.queue_command(QuitCommand(self, async_callback))

    def terminate(self, async=None):
        self.process.terminate()
        promise = QuitCommand(self)
        if async:
            return promise
        else:
            return promise.wait()

    def kill(self, async=False):
        self.process.kill()
        promise = QuitCommand(self)
        if async:
            return promise
        else:
            return promise.wait()

    def is_alive(self):
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
        print(">>>", buf.rstrip())
        self.process.stdin_write(buf.encode("utf-8"))

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
    return cls(subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, bufsize=1, universal_newlines=True))


def spur_spawn_engine(shell, command, cls=SpurEngine):
    return cls(shell, command)


if __name__ == "__main__":
    import sys
    import spur

    shell = spur.SshShell(hostname="localhost",missing_host_key=spur.ssh.MissingHostKey.warn)
    engine = spur_spawn_engine(shell, ["stockfish"])

    #engine = popen_engine("stockfish")

    engine.uci()
    print(engine.name)
    print(engine.author)

    print(engine.setoption({
        "foo": "bar"
    }))

    print(engine.options)

    engine.debug(True)

    print(engine.ucinewgame())

    class MyInfoHandler(InfoHandler):
        def post_info(self):
            print(self.info)
            super(MyInfoHandler, self).post_info()

    engine.info_handlers.append(MyInfoHandler())

    board = chess.Bitboard("rnbqkbnr/pppp1ppp/4p3/8/5PP1/8/PPPPP2P/RNBQKBNR b KQkq g3 0 2")
    print(engine.position(board))
    print(engine.go(mate=5))

    print(engine.quit())
