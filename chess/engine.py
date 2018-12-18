import asyncio
import logging
import enum
import collections


LOGGER = logging.getLogger(__name__)


class EngineTerminatedError(RuntimeError):
    pass


class EngineProtocol(asyncio.SubprocessProtocol):
    def __init__(self):
        self.loop = asyncio.get_running_loop()
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
        if exc is None:
            exc = EngineTerminatedError("engine process died (exit code: {})".format(code))
        if self.command is not None:
            self.command._engine_terminated(self, exc)
            self.command = None
        if self.next_command is not None:
            self.next_command._engine_terminated(self, exc)
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

        if self.command:
            self.command._line_received(self, line)

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

        self.loop = loop or asyncio.get_running_loop()
        self.result = self.loop.create_future()
        self.finished = self.loop.create_future()

    def _engine_terminated(self, engine, exc):
        if not self.result.done():
            self.result.set_exception(exc)
        if not self.finished.done():
            self.finished.set_exception(exc)
            try:
                self.finished.result()
            except:
                pass

        if self.state in [CommandState.Active, CommandState.Cancelling]:
            self.engine_terminated(self, engine, exc)

    def set_finished(self):
        assert self.state in [CommandState.Active, CommandState.Cancelling]
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
    async def isready(self):
        return await self.communicate(IsReady())

    async def play(self, board):
        return await self.communicate(Go(board))


class IsReady(BaseCommand):
    def start(self, engine):
        engine.send_line("isready")

    def line_received(self, engine, line):
        if line == "readyok":
            if not self.result.cancelled():
                self.result.set_result(None)
            self.set_finished()
        else:
            LOGGER.warning("%s: Unexpected engine output: %s", engine, line)


class Go(BaseCommand):
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
    loop = asyncio.get_running_loop()
    return await loop.subprocess_shell(UciProtocol, cmd)


class SimpleEngine:
    def __init__(self, transport, protocol):
        self.transport = transport
        self.protocol = protocol

    def isready(self):
        self.protocol.loop.run_until_complete(self.protocol.isready())

    def close(self):
        self.transport.close()
        self.protocol.loop.run_until_complete(self.protocol.returncode)

    @classmethod
    def popen_uci(cls, cmd):
        loop = asyncio.get_event_loop()
        transport, protocol = loop.run_until_complete(popen_uci(cmd))
        return cls(transport, protocol)


def main():
    engine = SimpleEngine.popen_uci("stockfish")
    engine.isready()
    print("all good")
    engine.close()


# TODO: Add unit tests instead
async def async_main():
    import chess

    #transport, engine = await popen_uci("./engine.sh")
    transport, engine = await popen_uci("stockfish")

    try:
        await asyncio.wait_for(engine.isready(), 2)
    except asyncio.TimeoutError:
        print("timed out")
    else:
        print("got readyok")

    board = chess.Board()
    move = await engine.play(board)
    print("played", move)

    await engine.returncode


logging.basicConfig(level=logging.DEBUG)
if __name__ == "__main__":
    main()
elif __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(async_main())
    finally:
        loop.close()
