import asyncio
import concurrent.futures
import logging
import enum
import collections
import warnings
import sys
import threading

try:
    from asyncio import get_running_loop
except ImportError:
    from asyncio import _get_running_loop as get_running_loop


LOGGER = logging.getLogger(__name__)


def setup_loop():
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

    Returns the *future* result as soon as it is resolved. The coroutine
    continues running in the background until it is complete.
    """
    future = concurrent.futures.Future()

    def background():
        loop = setup_loop()

        try:
            loop.run_until_complete(coroutine(future))
            future.cancel()
        except Exception as exc:
            future.set_exception(exc)
            return
        finally:
            try:
                # Cancel all remaining tasks.
                pending = asyncio.Task.all_tasks(loop)
                for task in pending:
                    task.cancel()

                loop.run_until_complete(asyncio.gather(*pending, loop=loop, return_exceptions=True))

                for task in pending:
                    if task.cancelled():
                        continue

                    if task.exception() is not None:
                        loop.call_exception_handler({
                            "message": "unhandled exception during background event loop shutdown",
                            "exception": task.exception(),
                            "task": task,
                        })

                # Shutdown async generators.
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except AttributeError:
                    pass  # < Python 3.6
            finally:
                loop.close()

    threading.Thread(target=background).start()
    return future.result()


class EngineTerminatedError(RuntimeError):
    pass


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
                self.line_received(line)
            else:
                self.error_line_received(line)

    def error_line_received(self, line):
        LOGGER.warning("%s: stderr >> %s", self, line)

    def line_received(self, line):
        LOGGER.debug("%s: >> %s", self, line)

        self._line_received(line)

        if self.command:
            self.command._line_received(self, line)

    def _line_received(self, line):
        pass

    async def communicate(self, command):
        if self.returncode.done():
            raise EngineTerminatedError("engine process dead (exit code: {})".format(self.returncode.result()))

        if command.state != CommandState.New:
            raise RuntimeError("command with invalid state passed to communicate")

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


class CommandState(enum.Enum):
    New = 1
    Active = 2
    Cancelling = 3
    Done = 4


class BaseCommand:
    def __init__(self, loop=None):
        self.state = CommandState.New

        self.loop = loop or get_running_loop()
        self.result = self.loop.create_future()
        self.finished = self.loop.create_future()

    def _engine_terminated(self, engine, code):
        exc = EngineTerminatedError("engine process died while running {} (exit code: {})".format(repr(self), code))

        if not self.result.done():
            self.result.set_exception(exc)
        if not self.finished.done():
            self.finished.set_exception(exc)

            # Prevent warning when the exception is not retrieved.
            try:
                self.finished.result()
            except:
                pass

        if self.state in [CommandState.Active, CommandState.Cancelling]:
            self.engine_terminated(engine, exc)

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
        self.start(engine)

    def _done(self):
        assert self.state != CommandState.Done
        self.state = CommandState.Done

    def _line_received(self, engine, line):
        assert self.state in [CommandState.Active, CommandState.Cancelling]
        self.line_received(engine, line)

    def cancel(self, engine):
        pass

    def start(self, engine):
        pass

    def line_received(self, engine, line):
        pass

    def engine_terminated(self, engine, exc):
        pass


class UciProtocol(EngineProtocol):
    def __init__(self):
        super().__init__()
        self.options = UciOptionMap()
        self.config = UciOptionMap()

    def _line_received(self, line):
        command_and_args = line.split(None, 1)
        if len(command_and_args) >= 2:
            if command_and_args[0] == "option":
                self._option(command_and_args[1])

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

    async def isready(self):
        return await self.communicate(_IsReady())

    async def configure(self, config):
        return await self.communicate(UciConfigure(config))


class UciOptionMap(collections.abc.MutableMapping):
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


class UciInit(BaseCommand):
    def start(self, engine):
        engine.send_line("uci")

    def line_received(self, engine, line):
        if line == "uciok":
            self.set_finished()


class UciConfigure(BaseCommand):
    def __init__(self, options):
        super().__init__()
        self.options = options

    def start(self, engine):
        for name, value in self.options.items():
            if name not in engine.options:
                raise ValueError("engine does not support option: {}".format(name))
            elif name.lower() == "uci_chess960":
                raise ValueError("cannot set UCI_Chess960 which is automatically managed")
            elif name.lower() == "uci_variant":
                raise ValueError("cannot set UCI_Variant which is automatically managed")

            builder = ["setoption name", name, "value"]
            if value is True:
                builder.append("true")
            elif value is False:
                builder.append("false")
            elif value is None:
                builder.append("none")
            else:
                builder.append(str(value))

            engine.send_line(" ".join(builder))

        self.set_finished()


class _IsReady(BaseCommand):
    def start(self, engine):
        engine.send_line("isready")

    def line_received(self, engine, line):
        if line == "readyok":
            if not self.result.cancelled():
                self.result.set_result(None)
            self.set_finished()
        else:
            LOGGER.warning("%s: Unexpected engine output: %s", engine, line)


class _Go(BaseCommand):
    def __init__(self, board):
        super().__init__()
        self.fen = board.fen()

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


async def popen_uci(cmd):
    loop = get_running_loop()
    transport, protocol = await loop.subprocess_shell(UciProtocol, cmd)
    await protocol.communicate(UciInit())
    return transport, protocol


class SimpleEngine:
    def __init__(self, transport, protocol, *, timeout=10.0):
        self.transport = transport
        self.protocol = protocol
        self.timeout = timeout

    def isready(self):
        return asyncio.run_coroutine_threadsafe(asyncio.wait_for(self.protocol.isready(), self.timeout), self.protocol.loop).result()

    def close(self):
        self.transport.close()

    @classmethod
    def popen_uci(cls, cmd, *, timeout=10.0):
        async def background(future):
            transport, protocol = await asyncio.wait_for(popen_uci(cmd), timeout)
            future.set_result(cls(transport, protocol, timeout=timeout))
            await protocol.returncode

        return run_in_background(background)


async def async_main():
    import chess

    #transport, engine = await popen_uci("./engine.sh")
    transport, engine = await popen_uci("stockfish")

    await engine.configure({
        "Contempt": 20,
        "ContemptA": 20,
    })

    print(engine.options)

    await engine.returncode


def main():
    engine_a = SimpleEngine.popen_uci(sys.argv[1])
    engine_a.isready()

    engine_b = SimpleEngine.popen_uci(sys.argv[1])
    engine_b.isready()

    engine_a.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
    #asyncio.run(async_main())
