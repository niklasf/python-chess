import asyncio
import concurrent.futures
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
        return "<{} at {} (pid={})>".format(type(self).__name__, hex(id(self)), pid)

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
        exc = EngineTerminatedError("engine process died while running {} (exit code: {})".format(type(self).__name__, code))
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

    def _setoption(self, name, value):
        builder = ["setoption name", name, "value"]
        if value is True:
            builder.append("true")
        elif value is False:
            builder.append("false")
        elif value is None:
            builder.append("none")
        else:
            builder.append(str(value))

        self.send_line(" ".join(builder))
        self.config[name] = value

    async def configure(self, config):
        class Command(BaseCommand):
            def start(self, engine):
                for name, value in config.items():
                    if name not in engine.config:
                        raise EngineError("engine does not support option: {}".format(name))
                    elif name.lower() == "uci_chess960":
                        raise EngineError("cannot set UCI_Chess960 which is automatically managed")
                    elif name.lower() == "uci_variant":
                        raise EngineError("cannot set UCI_Variant which is automatically managed")
                    else:
                        engine._setoption(name, value)

                self.set_finished()

        return await self.communicate(Command)

    def _get_config(self, option, default=None):
        if option in self.config:
            return self.config[option]
        if option in self.options:
            return self.options[option].default
        return default

    def _position(self, board):
        # Select UCI_Variant and UCI_Chess960.
        uci_variant = type(board).uci_variant
        if uci_variant != self._get_config("UCI_Variant", "chess"):
            if "UCI_Variant" not in self.options:
                raise EngineError("engine does not support UCI_Variant")
            self._setoption("UCI_Variant", uci_variant)

        if board.chess960 != self._get_config("UCI_Chess960", False):
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

    async def play(self):
        class Command(BaseCommand):
            def __init__(self, loop, board, movetime=None):
                super().__init__(loop)
                self.fen = board.fen()
                self.movetime = movetime

            def start(self, engine):
                engine.send_line("position fen {}".format(self.fen))
                engine.send_line("go movetime 1000")

            def line_received(self, engine, line):
                if line.startswith("bestmove "):
                    if not self.result.cancelled():
                        self.result.set_result(line)
                    self.set_finished()

            def cancel(self, engine):
                engine.send_line("stop")

        return await self.communicate(Command)


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


class SimpleEngine:
    def __init__(self, transport, protocol, *, timeout=10.0):
        self.transport = transport
        self.protocol = protocol
        self.timeout = timeout

    def configure(self, config):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.configure(config), self.timeout), self.protocol.loop).result()

    def ping(self):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.ping(), self.timeout), self.protocol.loop).result()

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
    transport, engine = await UciProtocol.popen(sys.argv[1])
    await engine.ping()
    try:
        await engine.configure({
            "ContemptB": 40,
        })
    except EngineError:
        print("exception")
    await engine.ping()

    transport.close()
    await engine.returncode


def main():
    with SimpleEngine.popen_uci(sys.argv[1], setpgrp=True) as engine:
        print(engine.protocol.options)
        try:
            engine.configure({
                "Contempt": 40,
            })
        except EngineError:
            print("exception in configure")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
    #asyncio.run(async_main())
