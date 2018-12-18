import asyncio


class UciProtocol(asyncio.SubprocessProtocol):
    pass


async def popen_uci(cmd):
    loop = asyncio.get_running_loop()
    return await loop.subprocess_shell(UciProtocol, cmd)


# TODO: Add unit tests instead
async def main():
    transport, engine = await popen_uci("stockfish")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
