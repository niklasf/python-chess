# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2017 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

from chess.engine import EngineTerminatedException
from chess.engine import EngineStateException
from chess.engine import MockProcess
from chess.engine import PopenProcess
from chess.engine import SpurProcess
from chess.engine import LOGGER
from chess.engine import FUTURE_POLL_TIMEOUT

import chess

import concurrent.futures
import threading
import random

try:
    import backport_collections as collections
except ImportError:
    import collections


class PostHandler(object):
    """
    Chess engines may send information about their calculations if enabled
    via the *post* command. Post handlers can be used to aggregate or react
    to this information.

    >>> # Register a standard post handler.
    >>> post_handler = chess.xboard.PostHandler()
    >>> engine.info_handlers.append(post_handler)

    >>> # Start a search.
    >>> engine.setboard(board)
    >>> engine.st(1)
    >>> engine.go()
    TODO: comments below this
    BestMove(bestmove=Move.from_uci('e2e4'), ponder=Move.from_uci('e7e6'))
    >>>
    >>> # Retrieve the score of the mainline (PV 1) after search is completed.
    >>> # Note that the score is relative to the side to move.
    >>> info_handler.info["score"][1]
    Score(cp=34, mate=None, lowerbound=False, upperbound=False) 
    See :attr:`~chess.uci.InfoHandler.info` for a way to access this dictionary
    in a thread-safe way during search.

    If you want to be notified whenever new information is available
    you would usually subclass the *InfoHandler* class:

    >>> class MyHandler(chess.xboard.PostHandler):
    ...     def post_info(self):
    ...         # Called whenever a complete *post* line has been processed.
    ...         super(MyHandler, self).post_info()
    ...         print(self.post)
    """
    def __init__(self):
        self.lock = threading.Lock()

        self.post = {}
        self.post["pv"] = {}

    def depth(self, x):
        """Received depth in plies."""
        self.post["depth"] = x

    def score(self, x):
        """Receieved score in centipawns."""
        self.post["score"] = x

    def time(self, x):
        """Received new time searched in centiseconds."""
        self.post["time"] = x

    def nodes(self, x):
        """Received number of nodes searched."""
        self.post["nodes"] = x

    def pv(self, moves):
        """Received the principal variation as a list of moves."""
        self.post["pv"] = moves

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

    def on_move(self, move):
        """A new move has been received"""
        pass

    def acquire(self, blocking=True):
        return self.lock.acquire(blocking)

    def release(self):
        return self.lock.release()

    def __enter__(self):
        self.acquire()
        return self.post

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


class Engine(object):
    def __init__(self, Executor=concurrent.futures.ThreadPoolExecutor):
        self.idle = True
        self.state_changed = threading.Condition()
        self.semaphore = threading.Semaphore()
        self.search_started = threading.Event()

        self.board = chess.Board()
        self.chess960 = None
        self.variant = None

        self.name = None
        self.author = None
        #self.options = OptionMap()
        self.pong = threading.Event()
        self.ping_num = None # TODO: Make this a pong Event local instead of data member
        self.pong_received = threading.Condition()

        self.move = None
        self.move_received = threading.Event()

        self.return_code = None
        self.terminated = threading.Event()

        self.post_handlers = []

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

        if len(command_and_args) >= 2:
            if command_and_args[0] == "pong":
                return self._pong(command_and_args[1])
            elif command_and_args[0] == "move":
                return self._move(command_and_args[1])

    def on_terminated(self):
        self.return_code = self.process.wait_for_return_code()
        self.pool.shutdown(wait=False)
        self.terminated.set()

        # Wake up waiting commands.
        self.move_received.set()
        with self.pong_received:
            self.pong_received.notify_all()
        with self.state_changed:
            self.state_changed.notify_all()

    def _pong(self, pong_arg):
        try:
            pong_num = int(pong_arg)
        except ValueError:
                LOGGER.exception("exception parsing pong")

        if self.ping_num == pong_num:
            self.pong.set()
            with self.pong_received:
                self.pong_received.notify_all()

    def _move(self, arg):
        self.move = None
        try:
            self.move = self.board.parse_pacn(arg)
        except ValueError:
            LOGGER.exception("exception parsing move")

        self.move_received.set()
        for post_handler in self.post_handlers:
            post_handler.on_move(self.move)

    def _post(self, arg):
        if not self.post_handlers:
            return

        # Notify post handlers of start.
        for post_handler in self.post_handlers:
            post_handler.pre_info(arg)

        def handle_integer_token(token, fn):
            try:
                intval = int(token)
            except ValueError:
                LOGGER.exception("exception parsing integer token")
                return

            for post_handler in self.post_handlers:
                fn(post_handler, intval)

        pv = []
        board = self.board.copy(stack=False)
        tokens = arg.split(" ")
        # Order: <score> <depth> <time> <nodes> <pv>
        handle_integer_token(tokens[0], lambda handler, val: handler.depth(val))
        handle_integer_token(tokens[1], lambda handler, val: handler.score(val))
        handle_integer_token(tokens[2], lambda handler, val: handler.time(val))
        handle_integer_token(tokens[3], lambda handler, val: handler.nodes(val))
        try:
            pv.append(board.push_pacn(token))
        except ValueError:
            LOGGER.exception("exception parsing pv")
        if pv is not None:
            for post_handler in self.post_handlers:
                post_handler.pv(pv)

        # Notify post handlers of end.
        for post_handler in self.post_handlers:
            post_handler.post_info(arg)

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

    def ping(self, num, async_callback=None):
        """
        Command used to synchronize with the engine.

        The engine will respond as soon as it has handled all other queued
        commands.

        The engine will respond with *pong <num>*.

        :param options: A number to send along with ping.

        :return: Nothing
        """
        with self.pong_received:
            self.ping_num = num
            self.send_line("ping " + str(num))
            self.pong_received.wait()

    def xboard(self, async_callback=None):
        """
        Tells the engine to use the XBoard interface.

        This is mandatory before any other command. A conforming engine may
        quietly enter the XBoard state or may send some output which
        is currently ignored.
        TODO: Handle said output

        :return: Nothing
        """
        def command():
            with self.semaphore:
                self.send_line("xboard")
                self.ping(random.randint(0, 100))

                if self.terminated.is_set():
                    raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def new(self, board, async_callback=None):
        """
        Reset the board to the standard chess starting position.
        Set White on move.
        Leave force mode and set the engine to play Black.
        Associate the engine's clock with Black and the opponent's clock
        with White.
        Reset clocks and time controls to the start of a new game.
        Use wall clock for time measurement.
        Stop clocks.
        Do not ponder on this move, even if pondering is on.
        Remove any search depth limit previously set by the sd command.

        :return: Nothing
        """
        with self.state_changed:
            if not self.idle:
                raise EngineStateException("new command while engine is busy")

        def command():
            with self.semaphore:
                self.send_line("new")

                if self.terminated.is_set():
                    raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def st(self, time, async_callback=None):
        """
        Set maximum time the engine is to search for.

        :param time: Time to search for in seconds

        :return: Nothing
        """
        with self.state_changed:
            if not self.idle:
                raise EngineStateException("st command while engine is busy")

        def command():
            with self.semaphore:
                self.send_line("st " + str(time))

                if self.terminated.is_set():
                    raise EngineTerminatedException

        return self._queue_command(command, async_callback)

    def sd(self, depth, async_callback=None):
        """
        Set maximum depth the engine is to search for.

        :param depth: Depth to search for

        :return: Nothing
        """
        with self.state_changed:
            if not self.idle:
                raise EngineStateException("sd command while engine is busy")

        def command():
            with self.semaphore:
                self.send_line("sd " + str(depth))

                if self.terminated.is_set():
                    raise EngineTerminatedException

        return self._queue_command(command, async_callback)

    def level(self, movestogo=0, minutes=5, seconds=None, inc=0, async_callback=None):
        """
        Set the time controls for the game.

        :param movestogo: The number of moves to be played before the time
            control repeats.
            Defaults to 0 (in order to play the whole game in the given time control).
        :param minutes: The number of minutes for the whole game or until
            *movestogo* moves are played. In addition to seconds.
            Defaults to 5.
        :param seconds: The number of seconds for the whole game or until
            *movestogo* moves are played. In addition to minutes.
            Defaults to 0.
        :param inc: The amount of increment(in seconds) to be provided
            after each move is played.
            Defaults to 0.

        :return: Nothing
        """
        with self.state_changed:
            if not self.idle:
                raise EngineStateException("level command while engine is busy")

        builder = []
        builder.append("level")
        builder.append(str(int(movestogo)))
        builder.append(str(int(minutes)))

        if seconds is not None:
            builder.append(":")
            builder.append(str(int(seconds)))

        builder.append(str(int(inc)))

        def command():
            with self.semaphore:
                self.send_line(" ".join(builder))

                if self.terminated.is_set():
                    raise EngineTerminatedException

        return self._queue_command(command, async_callback)
