import asyncio
import logging


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
        previous_command = self.command
        self.command = command
        self.command._prepare(self, previous_command)
        return await self.command.result

    def __repr__(self):
        pid = self.transport.get_pid() if self.transport is not None else None
        return "<{} at {} (pid={})>".format(type(self).__name__, hex(id(self)), pid)


class BaseCommand:
    def __init__(self, loop=None):
        self._previous_command = None
        self._started = False

        self.loop = loop or asyncio.get_running_loop()
        self.result = self.loop.create_future()
        self.idle = self.loop.create_future()

    def _prepare(self, engine, previous_command):
        def after_previous_command(_):
            assert self._previous_command is None or self._previous_command.idle.done()
            self._previous_command = None
            self._started = True
            self.send(engine)

        if previous_command and previous_command._started:
            self._previous_command = previous_command
            self._previous_command.idle.add_done_callback(after_previous_command)
            self._previous_command.cancel(engine)
        else:
            after_previous_command(None)

    def _line_received(self, engine, line):
        if self._previous_command:
            self._previous_command._line_received(engine, line)
        else:
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
    transport, engine = await popen_uci("stockfish")

    await engine.communicate(IsReady())

    await engine.returncode


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
