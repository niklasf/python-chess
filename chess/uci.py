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
import subprocess
import threading
import time

try:
    import queue
except ImportError:
    import Queue as queue


POLL_TIMEOUT = 5
STOP_TIMEOUT = 2


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
            builder.append(value)
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
        return self.engine.process.returncode

    def wait(self, timeout=None):
        if not self.engine.terminated.wait(timeout):
            raise TimeoutError("waiting for engine termination timed out")
        return self.result

    def is_done(self):
        return self.engine.process.terminated.is_set()


class Engine(object):
    def __init__(self, process):
        super(Engine, self).__init__()
        self.process = process

        self.name = None
        self.name_received = threading.Event()

        self.author = None
        self.author_received = threading.Event()

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

        self.terminated = threading.Event()

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

        self.terminated.set()
        print("Terminated (stdin)!")

    def _stdout_thread_target(self):
        while self.is_alive():
            line = self.process.stdout.readline()
            if not line:
                continue

            line = line.rstrip()
            self._received(line)

        self.terminated.set()
        print("Terminated (stdout)!")

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
        tokens = arg.split(None, 2)
        self.bestmove = chess.Move.from_uci(tokens[0])
        if len(tokens) >= 3 and tokens[1] == "ponder" and tokens[2] != "(none)":
            self.ponder = chess.Move.from_uci(tokens[2])
        else:
            self.ponder = None
        self.bestmove_received.set()

    def _copyprotection(self, arg):
        # TODO: Implement
        pass

    def _registration(self, arg):
        # TODO: Implement
        pass

    def _info(self, arg):
        # TODO: Implement
        pass

    def _option(self, arg):
        # TODO: Implement
        pass

    def queue_command(self, command):
        if self.terminated.is_set():
            raise ChildProcessError('can not queue command for terminated uci engine')
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


def popen_engine(path):
    return Engine(subprocess.Popen(path, stdout=subprocess.PIPE, stdin=subprocess.PIPE, bufsize=1, universal_newlines=True))


# TODO: Support remote engines via SSH


if __name__ == "__main__":
    engine = popen_engine("stockfish")
    engine.uci()
    print(engine.name)
    print(engine.author)

    print(engine.setoption({
        "foo": "bar"
    }))

    engine.debug(True)

    print(engine.ucinewgame())

    board = chess.Bitboard("rnbqkbnr/pppp1ppp/4p3/8/5PP1/8/PPPPP2P/RNBQKBNR b KQkq g3 0 2")
    print(engine.position(board))
    print(engine.go(mate=5))

    print(engine.quit())

    print(engine.ucinewgame())
