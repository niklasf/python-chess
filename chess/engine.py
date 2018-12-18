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
        LOGGER.warn("%s: stderr >> %s", self, line)

    def line_received(self, line):
        LOGGER.debug("%s: >> %s", self, line)

        if self.command:
            self.command.line_received(line)

    async def communicate(self, command):
        previous_command = self.command
        self.command = command
        self.command.prepare(self, previous_command)
        return await self.command.idle

    def __repr__(self):
        pid = self.transport.get_pid() if self.transport is not None else None
        return "<{} at {} (pid={})>".format(type(self).__name__, hex(id(self)), pid)


class Command:
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_running_loop()
        self.idle = self.loop.create_future()
        self.previous_command = None

    def prepare(self, engine, previous_command):
        self.previous_command = previous_command
        if self.previous_command:
            self.previous_command.idle.add_done_callback(lambda _: self.start(engine))
            self.previous_command.cancel()
        else:
            self.start(engine)

    def start(self, engine):
        self.previous_command = None
        engine.send_line("isready")

    def cancel(self):
        pass

    def line_received(self, line):
        if self.previous_command:
            return self.previous_command.line_received(line)

        if line == "readyok":
            self.idle.set_result(None)


class UciProtocol(EngineProtocol):
    pass


async def popen_uci(cmd):
    loop = asyncio.get_running_loop()
    return await loop.subprocess_shell(UciProtocol, cmd)


# TODO: Add unit tests instead
async def main():
    transport, engine = await popen_uci("stockfish")

    result = await engine.communicate(Command())
    print("Command 1:", result)

    result = await engine.communicate(Command())
    print("Command 2:", result)

    await engine.returncode


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
