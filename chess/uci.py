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

import subprocess
import threading

try:
    import queue
except ImportError:
    import Queue as queue


POLL_TIMEOUT = 5


class Command(object):
    def __init__(self, callback=None):
        self.result = None

        self._callback = callback
        self._event = threading.Event()

    def _notify(self, result):
        self.result = result
        self._event.set()

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
        if not self._event.wait(timeout):
            raise TimeoutError("waiting for uci command timed out")
        return self.result

    def is_done(self):
        return self._event.is_set()


class QuitCommand(Command):
    def __init__(self, engine, callback=None):
        self.engine = engine
        self._callback = callback

    def _execute(self, engine):
        assert self.engine == engine
        engine.process.stdin.write("quit\n")
        engine.terminated.wait()
        self._notify(self.result)

    @property
    def result(self):
        return self.engine.process.returncode

    def wait(self, timeout=None):
        if not self.engine.terminated.wait(timeout):
            raise TimeoutError("waiting for engine termination timed out")
        return self.result

    def is_done(self):
        return self.engine.process.terminated.is_set()


class UciCommand(Command):
    def __init__(self, callback=None):
        super(UciCommand, self).__init__(callback)

    def _execute(self, engine):
        engine.uciok.clear()
        engine.process.stdin.write("uci\n")
        engine.uciok.wait()
        self._notify(())


class IsReadyCommand(Command):
    def __init__(self, callback=None):
        super(IsReadyCommand, self).__init__(callback)

    def _execute(self, engine):
        engine.readyok.clear()
        engine.process.stdin.write("isready\n")
        engine.readyok.wait()
        self._notify(())


class UciNewGameCommand(IsReadyCommand):
    def __init__(self, callback=None):
        super(UciNewGameCommand, self).__init__(callback)

    def _execute(self, engine):
        engine.process.stdin.write("ucinewgame\n")
        super(UciNewGameCommand, self)._execute(engine)


class DebugCommand(IsReadyCommand):
    def __init__(self, debug, callback=None):
        self.debug = debug
        super(DebugCommand, self).__init__(callback)

    def _execute(self, engine):
        if self.debug:
            engine.process.stdin.write("debug true\n")
        else:
            engine.process.stdin.write("debug false\n")
        super(DebugCommand, self)._execute(engine)


class PonderhitCommand(IsReadyCommand):
    def __init__(self, debug, callback=None):
        super(PonderhitCommand, self).__init__(callback)

    def _execute(self, engine):
        engine.process.stdin.write("ponderhit\n")
        super(PonderhitCommand, self)._execute(engine)


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

    def _stdin_thread_target(self):
        while self.is_alive():
            try:
                command = self.queue.get(True, POLL_TIMEOUT)
            except queue.Empty:
                continue

            command._execute(self)
            self.queue.task_done()

        self.terminated.set()

    def _stdout_thread_target(self):
        while self.is_alive():
            line = self.process.stdout.readline()
            if not line:
                continue

            line = line.rstrip()

            #print "<<<", line

            command_and_args = line.split(None, 1)
            if not command_and_args:
                continue

            if len(command_and_args) >= 1:
                if command_and_args[0] == "readyok":
                    self._readyok()
                    continue
                elif command_and_args[0] == "uciok":
                    self._uciok()
                    continue

            if len(command_and_args) >= 2:
                if command_and_args[0] == "id":
                    self._id(command_and_args[1])
                    continue

            #print "Command not found!"

        self.terminated.set()

    def _readyok(self):
        self.readyok.set()

    def _uciok(self):
        self.uciok.set()

    def _id(self, arg):
        property_and_arg = arg.split(None, 1)
        #print "||||", arg
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

        #print "Property not found!"

    def uci(self, async_callback=None):
        command = UciCommand(async_callback)
        self.queue.put(command)
        return command._wait_or_callback()

    def isready(self, async_callback=None):
        command = IsReadyCommand(async_callback)
        self.queue.put(command)
        return command._wait_or_callback()

    def ucinewgame(self, async_callback=None):
        command = UciNewGameCommand(async_callback)
        self.queue.put(command)
        return command._wait_or_callback()

    def debug(self, debug, async_callback=None):
        command = DebugCommand(debug, async_callback)
        self.queue.put(command)
        return command._wait_or_callback()

    def ponderhit(self, async_callback=None):
        command = PonderhitCommand(async_callback)
        self.queue.put(command)
        return command._wait_or_callback()

    def quit(self, async_callback=None):
        command = QuitCommand(self, async_callback)
        self.queue.put(command)
        return command._wait_or_callback()

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
    return Engine(subprocess.Popen(path, stdout=subprocess.PIPE, stdin=subprocess.PIPE))


if __name__ == "__main__":
    engine = popen_engine("stockfish")

    engine.debug(True)

    engine.uci()

    print(engine.name)
    print(engine.author)

    print(engine.ucinewgame())
    print(engine.ponderhit())

    print(engine.quit())
