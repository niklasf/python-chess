import asyncio
import logging


LOGGER = logging.getLogger(__name__)


class UciProtocol(asyncio.SubprocessProtocol):
    def __init__(self):
        self.loop = asyncio.get_running_loop()
        self.transport = None

        self.stdout_buffer = bytearray()
        self.stderr_buffer = bytearray()

    def connection_made(self, transport):
        self.transport = transport
        LOGGER.debug("%s: Connection made", self)

    def __repr__(self):
        pid = self.transport.get_pid() if self.transport is not None else None
        return "<{} at {} (pid={})>".format(type(self).__name__, hex(id(self)), pid)


async def popen_uci(cmd):
    loop = asyncio.get_running_loop()
    return await loop.subprocess_shell(UciProtocol, cmd)


# TODO: Add unit tests instead
async def main():
    transport, engine = await popen_uci("stockfish")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
