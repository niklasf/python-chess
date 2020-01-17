import asyncio
import logging

import chess.engine

from pythonfuzz.main import PythonFuzz


logging.getLogger("chess.engine").setLevel(logging.CRITICAL)
asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())


@PythonFuzz
def fuzz(buf):
    lines = buf.split(b"!")

    class FuzzTransport:
        def __init__(self, protocol):
            self.protocol = protocol
            self.protocol.connection_made(self)

        def get_pipe_transport(self, fd):
            assert fd == 0, f"expected 0 for stdin, got {fd}"
            return self

        def write(self, data):
            if lines:
                self.protocol.pipe_data_received(1, lines.pop(0))

        def get_pid(self) -> int:
            return id(self)

        def get_returncode(self):
            return 0

    async def main():
        protocol = chess.engine.UciProtocol()
        transport = FuzzTransport(protocol)
        await asyncio.wait_for(protocol.initialize(), 0.1)
        await asyncio.wait_for(protocol.ping(), 0.1)
        await asyncio.wait_for(protocol.analysis(chess.Board(), chess.engine.Limit(nodes=1)), 0.1)

    try:
        asyncio.run(main())
    except asyncio.TimeoutError:
        pass
    except UnicodeDecodeError:
        pass
    except chess.engine.EngineError:
        pass


if __name__ == "__main__":
    fuzz()
