# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2017 Manik Charan <mkchan2951@gmail.com>
# Copyright (C) 2017 Cash Costello <cash.costello@gmail.com>
# Copyright (C) 2017 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

import concurrent.futures
import threading
import random

from chess.engine import EngineTerminatedException
from chess.engine import EngineStateException
from chess.engine import Option
from chess.engine import OptionMap
from chess.engine import LOGGER
from chess.engine import FUTURE_POLL_TIMEOUT
from chess.engine import _popen_engine
from chess.engine import _spur_spawn_engine

import chess


RESULTS = [DRAW, WHITE_WIN, BLACK_WIN] = ["1/2-1/2", "1-0", "0-1"]


class DrawHandler(object):
    """
    Chess engines may send a draw offer after playing it's move and may recieve
    one during an offer during it's calculations. A draw handler can be used to
    send, or react to, this information.

    >>> # Register a standard draw handler.
    >>> draw_handler = chess.xboard.DrawHandler()
    >>> engine.draw_handler = draw_handler

    >>> # Start a search.
    >>> engine.setboard(board)
    >>> engine.st(1)
    >>> engine.go()
    e2e4
    offer draw
    >>>
    >>> # Do some relevant work.
    >>> # Check if a draw offer is pending at any given time.
    >>> draw_handler.pending_offer
    True

    See :attr:`~chess.xboard.DrawHandler.pending_offer` for a way to access
    this flag in a thread-safe way during search.

    If you want to be notified whenever new information is available
    you would usually subclass the *DrawHandler* class:

    >>> class MyHandler(chess.xboard.DrawHandler):
    ...     def offer_draw(self):
    ...         # Called whenever `offer draw` has been processed.
    ...         super(MyHandler, self).offer_draw()
    ...         print(self.pending_offer)
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.pending_offer = False

    def pre_offer(self):
        """
        Received a new draw offer about to be processed.

        When subclassing remember to call this method of the parent class in
        order to keep the locking in tact.
        """
        self.lock.acquire()

    def post_offer(self):
        """
        Processing of a draw offer has been finished.

        When subclassing remember to call this method of the parent class in
        order to keep the locking in tact.
        """
        self.lock.release()

    def offer_draw(self):
        """A draw has been offered."""
        with self.lock:
            self.pending_offer = True

    def clear_offer(self):
        """The draw offer has expired."""
        with self.lock:
            self.pending_offer = False

    def acquire(self, blocking=True):
        return self.lock.acquire(blocking)

    def release(self):
        return self.lock.release()

    def __enter__(self):
        self.acquire()
        return self.pending_offer

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


class PostHandler(object):
    """
    Chess engines may send information about their calculations if enabled
    via the *post* command. Post handlers can be used to aggregate or react
    to this information.

    >>> # Register a standard post handler.
    >>> post_handler = chess.xboard.PostHandler()
    >>> engine.post_handlers.append(post_handler)

    >>> # Start a search.
    >>> engine.setboard(board)
    >>> engine.st(1)
    >>> engine.go()
    e2e4
    >>>
    >>> # Retrieve the score of the mainline (PV 1) after search is completed.
    >>> # Note that the score is relative to the side to move.
    >>> post_handler.post["score"]
    34

    See :attr:`~chess.xboard.PostHandler.post` for a way to access this dictionary
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

    def depth(self, depth):
        """Received depth in plies."""
        self.post["depth"] = depth

    def score(self, score):
        """Receieved score in centipawns."""
        self.post["score"] = score

    def time(self, time):
        """Received new time searched in centiseconds."""
        self.post["time"] = time

    def nodes(self, nodes):
        """Received number of nodes searched."""
        self.post["nodes"] = nodes

    def pv(self, moves):
        """Received the principal variation as a list of moves."""
        self.post["pv"] = moves

    def pre_info(self):
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
        """A new move has been received."""
        pass

    def on_go(self):
        """A go command is being sent."""
        with self.lock:
            self.post.clear()
            self.post["pv"] = {}

    def acquire(self, blocking=True):
        return self.lock.acquire(blocking)

    def release(self):
        return self.lock.release()

    def __enter__(self):
        self.acquire()
        return self.post

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


class FeatureMap(object):
    def __init__(self):
        # Populated with defaults to begin with
        self._features = {
            "ping" : 0, # TODO: Remove dependency of xboard module on ping
            "setboard" : 0,
            "playother" : 0,
            "san" : 0,
            "usermove" : 0,
            "time" : 1,
            "draw" : 1,
            "sigint" : 1,
            "sigterm" : 1,
            "reuse" : 1,
            "analyze" : 1,
            "myname" : None,
            "variants" : None,
            "colors" : 1,
            "ics" : 0,
            "name" : None,
            "pause" : 0,
            "nps" : 1,
            "debug" : 0,
            "memory" : 0,
            "smp" : 0,
            "egt" : 0,
            "option" : OptionMap(),
            "done" : None
            }

    def set_feature(self, key, value):
        try:
            value = int(value)
        except ValueError:
            pass

        try:
            self._features[key] = value
        except KeyError:
            LOGGER.exception("exception looking up feature")

    def get_option(self, key):
        try:
            return self._features["option"][key]
        except KeyError:
            LOGGER.exception("exception looking up option")

    def set_option(self, key, value):
        try:
            self._features["option"][key] = value
        except KeyError:
            LOGGER.exception("exception looking up option")

    def get(self, key):
        try:
            return self._features[key]
        except KeyError:
            LOGGER.exception("exception looking up feature")

    def supports(self, key):
        return self.get(key) == 1


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
        self.features = FeatureMap()
        self.pong = threading.Event()
        self.ping_num = 123
        self.pong_received = threading.Condition()
        self.auto_force = False
        self.in_force = False
        self.end_result = None

        self.move = None
        self.move_received = threading.Event()

        self.return_code = None
        self.terminated = threading.Event()

        self.post_handlers = []
        self.draw_handler = None
        self.engine_offered_draw = False

        self.pool = Executor(max_workers=3)
        self.process = None

    def on_process_spawned(self, process):
        self.process = process

    def send_line(self, line):
        LOGGER.debug("%s << %s", self.process, line)
        return self.process.send_line(line)

    def on_line_received(self, buf):
        LOGGER.debug("%s >> %s", self.process, buf)

        # Not too happy with this quasi-hack to prevent splitting within
        # options' space-separated values
        if buf.startswith("feature"):
            return self._feature(buf[8:])

        command_and_args = buf.split()
        if not command_and_args:
            return

        if command_and_args[0] == "#":
            pass
        elif len(command_and_args) == 2:
            if command_and_args[0] == "pong":
                return self._pong(command_and_args[1])
            elif command_and_args[0] == "move":
                return self._move(command_and_args[1])
            elif command_and_args[0] == "offer" and command_and_args[1] == "draw":
                return self._offer_draw()
        elif len(command_and_args) >= 5:
            return self._post(buf)

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

    def _offer_draw(self):
        if self.draw_handler:
            if self.draw_handler.pending_offer and not self.engine_offered_draw:
                self._end_game(DRAW)
            else:
                self.engine_offered_draw = True
                self.draw_handler.offer_draw()

    def _feature(self, features):
        """
        Does not conform to CECP spec regarding `done` and instead reads all
        features atomically.
        """
        if features.startswith("option"):
            features = features.replace("\"", "")
            params = features.split("=")[1].split()
            name = params[0]
            type = params[1][1:]
            min = None
            max = None
            var = []
            if type == "combo":
                choices = params[2:]
                for choice in choices:
                    if choice == "///":
                        continue
                    elif choice[0] == "*":
                        default = choice[1:]
                        var.append(choice[1:])
                    else:
                        var.append(choice)
                print(var)
                print(default)
            else:
                default = int(params[2])
                min = int(params[3])
                max = int(params[4])
            option = Option(name, type, default, min, max, var)
            self.features.set_option(option.name, option)
            return

        features = features.split()
        feature_map = [feature.split("=") for feature in features]
        for (key, value) in feature_map:
            value = value.strip("\"")
            if key == "variant":
                self.features.set_feature(key, value.split(","))
            else:
                self.features.set_feature(key, value)

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
            self.move = self.board.parse_uci(arg)
        except ValueError:
            try:
                self.move = self.board.parse_san(arg)
            except ValueError:
                LOGGER.exception("exception parsing move")

        self.move_received.set()
        if self.draw_handler:
            self.draw_handler.clear_offer()
            self.engine_offered_draw = False
        for post_handler in self.post_handlers:
            post_handler.on_move(self.move)

    def _post(self, arg):
        if not self.post_handlers:
            return

        # Notify post handlers of start.
        for post_handler in self.post_handlers:
            post_handler.pre_info()

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
        tokens = arg.split()
        # Order: <score> <depth> <time> <nodes> <pv>
        handle_integer_token(tokens[0], lambda handler, val: handler.depth(val))
        handle_integer_token(tokens[1], lambda handler, val: handler.score(val))
        handle_integer_token(tokens[2], lambda handler, val: handler.time(val))
        handle_integer_token(tokens[3], lambda handler, val: handler.nodes(val))
        for token in tokens[4:]:
            # Ignore move number(for example 1. Nf3 Nf6 -> Nf3 Nf6)
            if '.' in token or '<' in token:
                continue
            try:
                pv.append(board.push_uci(token))
            except ValueError:
                try:
                    pv.append(board.push_san(token))
                except ValueError:
                    LOGGER.exception("exception parsing pv")

        if pv is not None:
            for post_handler in self.post_handlers:
                post_handler.pv(pv)

        # Notify post handlers of end.
        for post_handler in self.post_handlers:
            post_handler.post_info()

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

    def _assert_supports_feature(self, feature_name):
        if not self.features.supports(feature_name):
            raise EngineStateException("engine does not support the '{}' feature", feature_name)

    def _assert_not_busy(self, cmd):
        with self.state_changed:
            if not self.idle:
                raise EngineStateException("{} command while engine is busy", cmd)

    def _end_game(self, result):
        self.end_result = result
        self.stop()

    def command(self, msg):
        def cmd():
            with self.semaphore:
                self.send_line(msg)

                if self.terminated.is_set():
                    raise EngineTerminatedException
        return cmd

    def ping(self, async_callback=None):
        """
        Command used to synchronize with the engine.

        The engine will respond as soon as it has handled all other queued
        commands.

        :return: Nothing
        """
        def command():
            with self.semaphore:
                with self.pong_received:
                    self.send_line("ping " + str(self.ping_num))
                    self.pong_received.wait()

                    if self.terminated.is_set():
                        raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def draw(self, async_callback=None):
        """
        Command used to offer the engine a draw.

        The engine may respond with `offer draw` to agree and may ignore the
        offer to disagree.

        :return: Nothing
        """
        self._assert_supports_feature("draw")
        if self.draw_handler:
            self.draw_handler.offer_draw()
            command = self.command("draw")
            return self._queue_command(command, async_callback)

    def pondering(self, ponder, async_callback=None):
        """
        Tell the engine whether to ponder or not.

        :param ponder: set pondering to on or off
        Defaults to off

        :return: Nothing
        """
        if ponder:
            msg = "hard"
        else:
            msg = "easy"

        command = self.command(msg)
        return self._queue_command(command, async_callback)

    def easy(self, async_callback=None):
        """
        Tell the engine not to ponder.
        """
        return self.pondering(False, async_callback)

    def hard(self, async_callback=None):
        """
        Tell the engine to ponder.
        TODO: pondering not yet supported.
        """
        return self.pondering(True, async_callback)

    def set_post(self, flag, async_callback=None):
        """
        Command used to tell the engine whether to output it's analysis or not.

        :param flag: True or False to set post on or off.

        :return: Nothing
        """
        if flag:
            msg = "post"
        else:
            msg = "nopost"

        command = self.command(msg)
        return self._queue_command(command, async_callback)

    def post(self, async_callback=None):
        """
        Command used to tell the engine to output it's analysis.

        :return: Nothing
        """
        return self.set_post(True, async_callback)

    def nopost(self, async_callback=None):
        """
        Command used to tell the engine to not output it's analysis.

        :return: Nothing
        """
        return self.set_post(False, async_callback)

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
                self.send_line("protover 2")

                if self.terminated.is_set():
                    raise EngineTerminatedException()

            # TODO: Remove perhaps?
            self.post()
            self.easy()
            self.ping()

        return self._queue_command(command, async_callback)

    def option(self, options, async_callback=None):
        """
        Set values for the engines available options.

        :param options: A dictionary with option names as keys.

        :return: Nothing
        """
        option_lines = []

        for name, value in options.items():
            # Building string manually to avoid spaces
            option_string = "option " + name
            option = self.features.get_option(name)
            has_value = option.type in \
                    ("spin", "check", "combo", "string")
            if has_value and value is not None:
                value = str(value)
                option_string += "=" + value
                option_lines.append(option_string)
            elif not has_value and value is None:
                option_lines.append(option_string)

        def command():
            with self.semaphore:
                with self.pong_received:
                    for option_line in option_lines:
                        self.send_line(option_line)

                    if self.terminated.is_set():
                        raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def new(self, async_callback=None):
        """
        Reset the board to the standard chess starting position.
        Set White on move.
        Leave force mode and set the engine to play Black.
        Associate the engines clock with Black and the opponent's clock
        with White.
        Reset clocks and time controls to the start of a new game.
        Use wall clock for time measurement.
        Stop clocks.
        Do not ponder on this move, even if pondering is on.
        Remove any search depth limit previously set by the sd command.

        :return: Nothing
        """
        self._assert_not_busy("new")
        command = self.command("new")
        return self._queue_command(command, async_callback)

    def setboard(self, board, async_callback=None):
        """
        Set up a given board position.

        :param board: A *chess.Board*.

        :return: Nothing

        :raises: :exc:`~chess.engine.EngineStateException` if the engine is still
            calculating.
        """
        self._assert_not_busy("setboard")

        # Setboard should be sent after force.
        self.force()

        builder = []
        builder.append("setboard")
        builder.append(board.fen())

        self.board = board.copy(stack=False)

        command = self.command(" ".join(builder))
        return self._queue_command(command, async_callback)

    def undo(self, async_callback=None):
        """
        Puts the engine in force mode and takes back one move.

        :return: Nothing
        """
        self._assert_not_busy("undo")

        # Undo should be sent after force.
        self.force()

        self.board.pop()

        command = self.command("undo")
        return self._queue_command(command, async_callback)

    def remove(self, async_callback=None):
        """
        Tells the engine to retract two moves (one from each side).

        :return: Nothing
        """
        self._assert_not_busy("remove")

        self.board.pop()
        self.board.pop()

        command = self.command("remove")
        return self._queue_command(command, async_callback)

    def memory(self, amount, async_callback=None):
        """
        Set the maximum memory of the engines hash/pawn/bitbase/etc tables.

        :param amount: Maximum amount of memory to use in MegaBytes

        :return: Nothing
        """
        self._assert_supports_feature("memory")
        self._assert_not_busy("memory")

        command = self.command("memory " + str(amount))
        return self._queue_command(command, async_callback)

    def cores(self, num, async_callback=None):
        """
        Set the maximum number of processors the engine is allowed to use.
        That is, the number of search threads for an SMP engine.

        :param num: The number of processors

        :return: Nothing
        """
        self._assert_supports_feature("smp")
        self._assert_not_busy("cores")

        command = self.command("cores " + str(num))
        return self._queue_command(command, async_callback)

    def playother(self, async_callback=None):
        """
        Set the engine to play the side whose turn it is NOT to move.

        :return: Nothing
        """
        self._assert_supports_feature("playother")
        self._assert_not_busy("playother")

        self.in_force = False
        command = self.command("playother")
        return self._queue_command(command, async_callback)

    def set_side_to_move(self, color, async_callback=None):
        """
        Set the side to move, set the engine to move for the opposite side
        and exit force mode.

        :param color: The desired side to move.

        :return: Nothing
        """
        self._assert_supports_feature("colors")
        side = chess.COLOR_NAMES[color]
        self._assert_not_busy(side)

        self.in_force = False
        command = self.command(side)
        return self._queue_command(command, async_callback)

    def white(self, async_callback=None):
        """
        Set the side to move to be white, engine to play as black and
        exit force mode.

        :return: Nothing
        """
        self.set_side_to_move(chess.WHITE, async_callback)

    def black(self, async_callback=None):
        """
        Set the side to move to be black, engine to play as white and
        exit force mode.

        :return: Nothing
        """
        self.set_side_to_move(chess.BLACK, async_callback)

    def random(self, async_callback=None):
        """
        Toggles random mode.

        In random mode, the engine may choose to add a random factor to it's
        evaluation of any given position prompting variation in play or may
        ignore it entirely.

        :return: Nothing
        """
        self._assert_not_busy("random")

        command = self.command("random")
        return self._queue_command(command, async_callback)

    def nps(self, target_nps, async_callback=None):
        """
        Tell the engine to limit it's speed of search in terms of
        Nodes Per Second to the provided value.

        :param target_nps: The limiting Nodes Per Second value

        :return: Nothing
        """
        self._assert_supports_feature("nps")
        self._assert_not_busy("nps")

        command = self.command("nps " + str(target_nps))
        return self._queue_command(command, async_callback)

    def st(self, time, async_callback=None):
        """
        Set maximum time the engine is to search for.

        :param time: Time to search for in seconds

        :return: Nothing
        """
        self._assert_not_busy("st")

        command = self.command("st " + str(time))
        return self._queue_command(command, async_callback)

    def sd(self, depth, async_callback=None):
        """
        Set maximum depth the engine is to search for.

        :param depth: Depth to search for

        :return: Nothing
        """
        self._assert_not_busy("sd")

        command = self.command("sd " + str(depth))
        return self._queue_command(command, async_callback)

    def time(self, time, async_callback=None):
        """
        Synchronize the engines clock with the total amount of time left.

        :param time: The total time left in centiseconds

        :return: Nothing
        """
        self._assert_supports_feature("time")
        self._assert_not_busy("time")

        command = self.command("time " + str(time))
        return self._queue_command(command, async_callback)

    def otim(self, time, async_callback=None):
        """
        Synchronize the engines clock with the total amount of time left.

        :param time: The total time left in centiseconds

        :return: Nothing
        """
        self._assert_supports_feature("time")
        self._assert_not_busy("otim")

        command = self.command("otim " + str(time))
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
        self._assert_not_busy("level")

        builder = []
        builder.append("level")
        builder.append(str(int(movestogo)))

        if seconds is not None:
            builder.append(str(int(minutes)) + ":" + str(int(seconds)))
        else:
            builder.append(str(int(minutes)))

        builder.append(str(int(inc)))

        command = self.command(" ".join(builder))
        return self._queue_command(command, async_callback)

    def set_auto_force(self, flag):
        """
        Set the XBoard engine to not start thinking immediately
        after a call to usermove().

        :param flag: Set to true to set this mode. Set to False
            to resume normal XBoard function.

        :return: Nothing
        """
        self.auto_force = flag

    def force(self, async_callback=None):
        """
        Tell the XBoard engine to enter force mode. That means
        the engine will not start thinking by itself unless a
        go() command is sent.

        :return: Nothing
        """
        self.in_force = True
        command = self.command("force")
        return self._queue_command(command, async_callback)

    def go(self, async_callback=None):
        """
        Set engine to move on the current side to play.
        Start calculating on the current position.

        :return: the best move according to the engine.

        :raises: :exc:`~chess.engine.EngineStateException` if the engine is
            already calculating.
        """
        self._assert_not_busy("go")

        with self.state_changed:
            self.idle = False
            self.search_started.clear()
            self.move_received.clear()
            self.state_changed.notify_all()

        for post_handler in self.post_handlers:
            post_handler.on_go()

        def command():
            with self.semaphore:
                self.send_line("go")
                self.search_started.set()

            self.move_received.wait()

            with self.state_changed:
                self.idle = True
                self.state_changed.notify_all()

            if self.terminated.is_set():
                raise EngineTerminatedException()

            if self.auto_force:
                self.force()

            try:
                self.board.push_uci(str(self.move))
            except ValueError:
                try:
                    self.board.push_san(str(self.move))
                except ValueError:
                    LOGGER.exception("exception parsing move")

            return self.move

        return self._queue_command(command, async_callback)

    def stop(self, async_callback=None):
        """
        Stop calculating as soon as possible. The actual XBoard command is `?`.

        :return: Nothing.
        """
        # Only send stop when the engine is actually searching.
        def command():
            with self.semaphore:
                with self.state_changed:
                    if not self.idle:
                        self.search_started.wait()

                    backoff = 0.5
                    while not self.move_received.is_set() and not self.terminated.is_set():
                        if self.idle:
                            break
                        else:
                            self.send_line("?")
                        self.move_received.wait(backoff)
                        backoff *= 2

                    self.idle = True
                    self.state_changed.notify_all()

                if self.terminated.is_set():
                    raise EngineTerminatedException()

        return self._queue_command(command, async_callback)

    def usermove(self, move, async_callback=None):
        """
        Tell the XBoard engine to make a move on it's internal
        board.
        If auto_force is set to True, the engine will not start
        thinking about it's next move immediately after.

        :param move: The move to play in XBoard notation.

        :return: Nothing
        """
        builder = []
        if self.features.supports("usermove"):
            builder.append("usermove")

        if self.draw_handler:
            self.draw_handler.clear_offer()
            self.engine_offered_draw = False

        if self.auto_force:
            self.force()
        elif not self.in_force:
            with self.state_changed:
                if not self.idle:
                    raise EngineStateException("usermove command while engine is already busy")

                self.idle = False
                self.search_started.clear()
                self.move_received.clear()
                self.state_changed.notify_all()

            for post_handler in self.post_handlers:
                post_handler.on_go()

        try:
            self.board.push_uci(str(move))
        except ValueError:
            try:
                self.board.push_san(str(move))
            except ValueError:
                LOGGER.exception("exception parsing move")

        builder.append(str(move))
        def command():
            # Use the join(builder) once we parse usermove=1 feature
            move_str = " ".join(builder)
            if self.in_force:
                with self.semaphore:
                    self.send_line(move_str)

                if self.terminated.is_set():
                    raise EngineTerminatedException()
            else:
                with self.semaphore:
                    self.send_line(move_str)
                    self.search_started.set()

                self.move_received.wait()

                with self.state_changed:
                    self.idle = True
                    self.state_changed.notify_all()

                if self.terminated.is_set():
                    raise EngineTerminatedException()

                try:
                    self.board.push_uci(str(self.move))
                except ValueError:
                    try:
                        self.board.push_san(str(self.move))
                    except ValueError:
                        LOGGER.exception("exception parsing move")

                return self.move

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

        This is not an XBoard command. It instead tries to terminate the engine
        on operating system level, for example by sending SIGTERM on Unix
        systems. If possible, first try the *quit* command.

        :return: The return code of the engine process (or a Future).
        """
        self.process.terminate()
        return self._queue_termination(async_callback)

    def kill(self, async_callback=None):
        """
        Kill the engine.

        Forcefully kill the engine process, for example by sending SIGKILL.

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
    mandatory *xboard* command.

    >>> engine = chess.xboard.popen_engine("/usr/games/crafty")
    >>> engine.xboard()

    :param setpgrp: Open the engine process in a new process group. This will
        stop signals (such as keyboards interrupts) from propagating from the
        parent process. Defaults to ``False``.
    """
    return _popen_engine(command, engine_cls, setpgrp, _popen_lock, **kwargs)


def spur_spawn_engine(shell, command, engine_cls=Engine):
    """
    Spawns a remote engine using a `Spur`_ shell.

    >>> import spur
    >>> shell = spur.SshShell(hostname="localhost", username="username", password="pw")
    >>> engine = chess.xboard.spur_spawn_engine(shell, ["/usr/games/crafty"])
    >>> engine.xboard()

    .. _Spur: https://pypi.python.org/pypi/spur
    """
    return _spur_spawn_engine(shell, command, engine_cls)
