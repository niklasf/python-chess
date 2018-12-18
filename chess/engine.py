import asyncio
import logging
import enum
import collections


LOGGER = logging.getLogger(__name__)


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
        if command.state != CommandState.New:
            raise RuntimeError("command with invalid state passed to communicate")

        if self.next_command is not None:
            self.next_command.result.cancel()
            self.next_command.finished.cancel()

        self.next_command = command

        def previous_command_finished(_):
            self.command = self.next_command
            if self.command is not None:
                self.command.finished.add_done_callback(previous_command_finished)
                self.command.start()

        if self.command is None:
            previous_command_finished(None)
        else:
            self.command.cancel()

        return await command.result

    def __repr__(self):
        pid = self.transport.get_pid() if self.transport is not None else None
        return "<{} at {} (pid={})>".format(type(self).__name__, hex(id(self)), pid)


class CommandState(enum.Enum):
    New = 1
    Started = 2
    Cancelling = 3
    Finished = 4


class BaseCommand:
    def __init__(self, loop=None):
        self.state = CommandState.New

        self.loop = loop or asyncio.get_running_loop()
        self.result = self.loop.create_future()
        self.finished = self.loop.create_future()

    def _cancel(self, engine):
        if self.state != CommandState.Finished:
            assert self.state != CommandState.New
            if self.result.done():
            else:
                self.result.cancel()
            self.finished.set_result(None)

    def _prepare(self, engine, previous_command):
        assert self.state == CommandState.New
        self.state = CommandState.Prepared

        def on_result(result):
            if result.cancelled():
                if self.state == CommandState.Sending:
                    self.state = CommandState.Cancelling
                    self.cancel()

        def on_idle(_):
            self.state = CommandState.Finished

        def on_previous_command_idle(_):
            assert self._previous_command is None or self._previous_command.state == CommandState.Finished
            self._previous_command = None

            assert self.state == CommandState.New

            if self.result.cancelled():
                self.idle.set_result(None)
            else:
                self.state = CommandState.Started
                self.send(engine)

        self.result.add_done_callback(on_result)
        self.idle.add_done_callback(on_idle)

        if not self._previous_command or self._previous_command.state == CommandState.Finished:
            on_previous_command_idle(None)
        else:
            self._previous_command.idle.add_done_callback(on_previous_command_idle)
            self._previous_command.result.cancel()


        if not previous_command or previous_command.state == CommandState.Finished:
            on_previous_command_idle(None)
        elif previous_command.state == CommandState.New:
            previous_command.result.cancel()
            previous_command.state = CommandState.Finished
            after_previous_command(None)
        elif previous_command.state == CommandState.Started:
            self._previous_command = previous_command
            self._previous_command.idle.add_done_callback(after_previous_command)
            self._previous_command.cancel(engine)

    def _line_received(self, engine, line):
        assert self.state in [CommandState.Sending, CommandState.Cancelling]
        self.line_received(engine, line)

    def send(self, engine):
        pass

    def cancel(self, engine):
        pass

    def line_received(self, engine, line):
        pass


class IsReady(BaseCommand):
    def send(self, engine):
        engine.send_line("isready")

    def line_received(self, engine, line):
        if line == "readyok":
            if not self.result.cancelled():
                self.result.set_result(None)
            self.idle.set_result(None)
        else:
            LOGGER.warning("%s: Unexpected engine output: %s", engine, line)


class UciProtocol(EngineProtocol):
    pass


async def popen_uci(cmd):
    loop = asyncio.get_running_loop()
    return await loop.subprocess_shell(UciProtocol, cmd)


# TODO: Add unit tests instead
async def main():
    transport, engine = await popen_uci("./engine.sh")

    try:
        await asyncio.wait_for(engine.communicate(IsReady()), 2)
    except asyncio.TimeoutError:
        print("timed out")

    await engine.communicate(IsReady())
    print("got second readyok")

    await engine.returncode


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
