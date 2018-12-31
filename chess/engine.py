import asyncio
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
    from asyncio import get_running_loop
except ImportError:
    from asyncio import _get_running_loop as get_running_loop

import chess


LOGGER = logging.getLogger(__name__)


def setup_event_loop():
    """
    Creates and sets up a new asyncio event loop that is capable of spawning
    and watching subprocesses.

    Uses polling to watch subprocesses when not running in the main thread.

    Note that this sets a global event loop policy.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    else:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

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
    The coroutine continues running in the background until it is complete.
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
                pending = asyncio.Task.all_tasks(loop)
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
        elif self.type == "button":
            return None
        elif self.type == "string":
            value = str(value)
            if "\n" in value or "\r" in value:
                raise EngineError("invalid line-break in string option {}".format(self.name))
            return value
        else:
            # Unknown option type.
            if value is True:
                return "true"
            elif value is False:
                return "false"
            elif value is None:
                return None
            else:
                return str(value)


class PlayResult:
    def __init__(self, move, ponder):
        self.move = move
        self.ponder = ponder

    def __repr__(self):
        return "<{} at {} (move={}, ponder={})>".format(type(self).__name__, hex(id(self)), self.move, self.ponder)


@functools.total_ordering
class Cp:
    def __init__(self, cp):
        self.cp = cp

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

    def __truediv__(self, scalar):
        try:
            return Cp(self.cp / scalar)
        except TypeError:
            return NotImplemented

    def __floordiv__(self, scalar):
        try:
            return Cp(self.cp // scalar)
        except TypeError:
            return NotImplemented

    def __neg__(self):
        return Cp(-self.cp)

    def __pos__(self):
        return Cp(self.cp)

    def __int__(self):
        return self.cp

    def __abs__(self):
        return Cp(abs(self.cp))

    def __float__(self):
        return float(self.cp)

    def __eq__(self, other):
        try:
            return self.cp == other.cp
        except AttributeError:
            pass

        try:
            other.winning
            return False
        except AttributeError:
            pass

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
class Mate:
    def __init__(self, moves, winning):
        self.moves = abs(moves)
        self.winning = winning ^ (moves < 0)

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

    def __int__(self):
        # Careful: Conflates Mate.plus(0) and Mate.minus(0)!
        return self.moves

    def __float__(self):
        return float(int(self))

    def __eq__(self, other):
        try:
            return self.moves == other.moves and self.winning == other.winning
        except AttributeError:
            pass

        try:
            other.cp
            return False
        except AttributeError:
            pass

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


class EngineProtocol(asyncio.SubprocessProtocol):
    def __init__(self):
        self.loop = get_running_loop()
        self.transport = None

        self.buffer = {
            1: bytearray(),  # stdout
            2: bytearray(),  # stderr
        }

        self.command = None
        self.next_command = None

        self.returncode = self.loop.create_future()

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

    async def communicate(self, command_factory):
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

        return await command.result

    def __repr__(self):
        pid = self.transport.get_pid() if self.transport is not None else None
        return "<{} (pid={})>".format(type(self).__name__, pid)

    @classmethod
    async def popen(cls, command, *, setpgrp=False, **kwargs):
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

        loop = get_running_loop()
        transport, protocol = await loop.subprocess_exec(cls, *command, **popen_args)
        await protocol._initialize()
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
        self.result = self.loop.create_future()
        self.finished = self.loop.create_future()

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
    def __init__(self):
        super().__init__()
        self.options = UciOptionMap()
        self.config = UciOptionMap()
        self.board = chess.Board()
        self.game = None

    async def _initialize(self):
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
                engine.options[option.name] = option

        return await self.communicate(Command)

    def _isready(self):
        self.send_line("isready")

    def _ucinewgame(self):
        self.send_line("ucinewgame")

    async def ping(self):
        class Command(BaseCommand):
            def start(self, engine):
                engine._isready()

            def line_received(self, engine, line):
                if line == "readyok":
                    self.set_finished()
                else:
                    LOGGER.warning("%s: Unexpected engine output: %s", engine, line)

        return await self.communicate(Command)

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
            if name.lower() in ["uci_chess960", "uci_variant", "uci_analysemode", "multipv"]:
                raise EngineError("cannot set {} which is automatically managed".format(name))
            else:
                self._setoption(name, value)

    async def configure(self, options):
        class Command(BaseCommand):
            def start(self, engine):
                engine._configure(options)
                self.set_finished()

        return await self.communicate(Command)

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

    def _go(self, *, searchmoves=None, ponder=False, wtime=None, btime=None, winc=None, binc=None, movestogo=None, depth=None, nodes=None, mate=None, movetime=None, infinite=False):
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

        self.send_line(" ".join(builder))

    async def play(self, board, *, game=None, options={}):
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
                engine._go(nodes=10000, movetime=1000)

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

        return await self.communicate(Command)

    async def quit(self):
        self.send_line("quit")
        await self.returncode


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


async def popen_uci(command, **kwargs):
    return await UciProtocol.popen(command, **kwargs)


class SimpleEngine:
    def __init__(self, transport, protocol, *, timeout=10.0):
        self.transport = transport
        self.protocol = protocol
        self.timeout = timeout

    def configure(self, options):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.configure(options), self.timeout), self.protocol.loop).result()

    def ping(self):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.ping(), self.timeout), self.protocol.loop).result()

    def play(self, board, *, game=None, options={}):
        return asyncio.run_coroutine_threadsafe(self.protocol.play(board, game=game, options=options), self.protocol.loop).result()

    def quit(self):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.quit(), self.timeout), self.protocol.loop).result()

    def close(self):
        self.transport.close()

    @classmethod
    def popen_uci(cls, command, *, timeout=10.0, **popen_args):
        async def background(future):
            transport, protocol = await asyncio.wait_for(UciProtocol.popen(command, **popen_args), timeout)
            future.set_result(cls(transport, protocol, timeout=timeout))
            await protocol.returncode

        return run_in_background(background)

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.close()


async def async_main():
    transport, engine = await popen_uci(sys.argv[1:])
    print(engine.options)

    await engine.ping()

    await engine.configure({
        "Contempt": 40,
    })

    import chess.variant
    board = chess.variant.ThreeCheckBoard()
    play_result = await engine.play(board)
    print("PLAYED ASYNC", play_result)

    await engine.quit()


def main():
    with SimpleEngine.popen_uci(sys.argv[1:], setpgrp=True) as engine:
        print(engine.protocol.options)

        #print("PING")
        #try:
        #    engine.ping()
        #except asyncio.TimeoutError:
        #    print("timeout !!!!!")
        #print("PONG")

        #engine.configure({
        #    "Contempt": 40,
        #})

        board = chess.Board()
        while not board.is_game_over():
            play_result = engine.play(board, game="foo") # , config={"Contempt": 20})
            print("PLAYED", play_result)
            board.push(play_result.move)
            break

        engine.protocol.send_line("d")

        engine.quit()
        print("QUIT")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    #main()
    asyncio.run(async_main())
