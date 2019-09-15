UCI/XBoard engine communication
===============================

UCI and XBoard are protocols for communicating with chess engines. This module
implements an abstraction for playing moves and analysing positions with
both kinds of engines.

The preferred way to use the API is with an
`asyncio <https://docs.python.org/3/library/asyncio.html>`_ event loop.
The examples also show a synchronous wrapper
:class:`~chess.engine.SimpleEngine` that automatically spawns an event loop
in the background.

Playing
-------

Example: Let Stockfish play against itself, 100 milliseconds per move.

.. code:: python

    import chess
    import chess.engine

    engine = chess.engine.SimpleEngine.popen_uci("/usr/bin/stockfish")

    board = chess.Board()
    while not board.is_game_over():
        result = engine.play(board, chess.engine.Limit(time=0.100))
        board.push(result.move)

    engine.quit()

.. code:: python

    import asyncio
    import chess
    import chess.engine

    async def main():
        transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")

        board = chess.Board()
        while not board.is_game_over():
            result = await engine.play(board, chess.engine.Limit(time=0.100))
            board.push(result.move)

        await engine.quit()

    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())

.. autoclass:: chess.engine.EngineProtocol
    :members: play

.. autoclass:: chess.engine.Limit
    :members:

    .. py:attribute:: time

        Search exactly *time* seconds.

    .. py:attribute:: depth

        Search *depth* ply only.

    .. py:attribute:: nodes

        Search only a limited number of *nodes*.

    .. py:attribute:: mate

        Search for a mate in *mate* moves.

    .. py:attribute:: white_clock

        Time in seconds remaining for White.

    .. py:attribute:: black_clock

        Time in seconds remaining for Black.

    .. py:attribute:: white_inc

        Fisher increment for White, in seconds.

    .. py:attribute:: black_inc

        Fisher increment for Black, in seconds.

    .. py:attribute:: remaining_moves

        Number of moves to the next time control. If this is not set, but
        *white_clock* and *black_clock* are, then it is sudden death.

.. autoclass:: chess.engine.PlayResult
    :members:

    .. py:attribute:: move

        The best move accordig to the engine, or ``None``.

    .. py:attribute:: ponder

        The response that the engine expects after *move*, or ``None``.

    .. py:attribute:: info

        A dictionary of extra information sent by the engine. Commonly used
        keys are: ``score`` (a :class:`~chess.engine.PovScore`),
        ``pv`` (a list of :class:`~chess.Move` objects),
        ``depth``, ``seldepth``, ``time`` (in seconds), ``nodes``, ``nps``,
        ``tbhits``, ``multipv``.

        Others: ``currmove``, ``currmovenumber``, ``hashfull``,
        ``cpuload``, ``refutation``, ``currline``, ``ebf`` and ``string``.

    .. py:attribute:: draw_offered

        Whether the engine offered a draw before moving.

    .. py:attribute:: resigned

        Whether the engine resigned.

Analysing and evaluating a position
-----------------------------------

Example:

.. code:: python

    import chess
    import chess.engine

    engine = chess.engine.SimpleEngine.popen_uci("/usr/bin/stockfish")

    board = chess.Board()
    info = engine.analyse(board, chess.engine.Limit(time=0.100))
    print("Score:", info["score"])
    # Score: +20

    board = chess.Board("r1bqkbnr/p1pp1ppp/1pn5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 2 4")
    info = engine.analyse(board, chess.engine.Limit(depth=20))
    print("Score:", info["score"])
    # Score: #1

    engine.quit()

.. code:: python

    import asyncio
    import chess
    import chess.engine

    async def main():
        transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")

        board = chess.Board()
        info = await engine.analyse(board, chess.engine.Limit(time=0.100))
        print(info["score"])
        # Score: +20

        board = chess.Board("r1bqkbnr/p1pp1ppp/1pn5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 2 4")
        info = await engine.analyse(board, chess.engine.Limit(depth=20))
        print(info["score"])
        # Score: #1

        await engine.quit()

    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())

.. autoclass:: chess.engine.EngineProtocol
    :members: analyse

.. autoclass:: chess.engine.PovScore
    :members:

    .. py:attribute:: relative

        The relative :class:`~chess.engine.Score`.

    .. py:attribute:: turn

        The point of view (``chess.WHITE`` or ``chess.BLACK``).

.. autoclass:: chess.engine.Score
    :members:

Indefinite or infinite analysis
-------------------------------

Example: Stream information from the engine and stop on an arbitrary condition.

.. code:: python

    import chess
    import chess.engine

    engine = chess.engine.SimpleEngine.popen_uci("/usr/bin/stockfish")

    with engine.analysis(chess.Board()) as analysis:
        for info in analysis:
            print(info.get("score"), info.get("pv"))

            # Arbitrary stop condition.
            if info.get("seldepth", 0) > 20:
                break

    engine.quit()

.. code:: python

    import asyncio
    import chess
    import chess.engine

    async def main():
        transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")

        with await engine.analysis(chess.Board()) as analysis:
            async for info in analysis:
                print(info.get("score"), info.get("pv"))

                # Arbitrary stop condition.
                if info.get("seldepth", 0) > 20:
                    break

        await engine.quit()

    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())

.. autoclass:: chess.engine.EngineProtocol
    :members: analysis

.. autoclass:: chess.engine.AnalysisResult
    :members:

    .. py:attribute:: info

        A dictionary of aggregated information sent by the engine. This is
        actually an alias for ``multipv[0]``.

    .. py:attribute:: multipv

        A list of dictionaries with aggregated information sent by the engine.
        One item for each root move.

Options
-------

:func:`~chess.EngineProtocol.configure()`,
:func:`~chess.EngineProtocol.play()`,
:func:`~chess.EngineProtocol.analyse()` and
:func:`~chess.EngineProtocol.analysis()` accept a dictionary of options.

>>> import chess.engine
>>>
>>> engine = chess.engine.SimpleEngine.popen_uci("/usr/bin/stockfish")
>>>
>>> # Check available options.
>>> engine.options["Hash"]
Option(name='Hash', type='spin', default=16, min=1, max=131072, var=[])
>>>
>>> # Set an option.
>>> engine.configure({"Hash": 32})
>>>
>>> # [...]

.. code:: python

    import asyncio
    import chess.engine

    async def main():
        transport, protocol = await chess.engine.popen_uci("/usr/bin/stockfish")

        # Check available options.
        print(engine.options["Hash"])
        # Option(name='Hash', type='spin', default=16, min=1, max=131072, var=[])

        # Set an option.
        await engine.configure({"Hash": 32})

        # [...]

    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())

.. autoclass:: chess.engine.EngineProtocol
    :members: configure

    .. py:attribute:: options

        Dictionary of available options.

.. autoclass:: chess.engine.Option
    :members:

    .. py:attribute:: name

        The name of the option.

    .. py:attribute:: type

        The type of the option.

        +--------+-----+------+------------------------------------------------+
        | type   | UCI | CECP | value                                          |
        +========+=====+======+================================================+
        | check  | X   | X    | ``True`` or ``False``                          |
        +--------+-----+------+------------------------------------------------+
        | button | X   | X    | ``None``                                       |
        +--------+-----+------+------------------------------------------------+
        | reset  |     | X    | ``None``                                       |
        +--------+-----+------+------------------------------------------------+
        | save   |     | X    | ``None``                                       |
        +--------+-----+------+------------------------------------------------+
        | string | X   | X    | string without line breaks                     |
        +--------+-----+------+------------------------------------------------+
        | file   |     | X    | string, interpreted as the path to a file      |
        +--------+-----+------+------------------------------------------------+
        | path   |     | X    | string, interpreted as the path to a directory |
        +--------+-----+------+------------------------------------------------+

    .. py:attribute:: default

        The default value of the option.

    .. py:attribute:: min

        The minimum integer value of a *spin* option.

    .. py:attribute:: max

        The maximum integer value of a *spin* option.

    .. py:attribute:: var

        A list of allowed string values for a *combo* option.

Logging
-------

Communication is logged with debug level on a logger named ``chess.engine``.
Debug logs are useful while troubleshooting. Please also provide them
when submitting bug reports.

.. code:: python

    import logging

    # Enable debug logging.
    logging.basicConfig(level=logging.DEBUG)

AsyncSSH
--------

:class:`~chess.engine.EngineProtocol` can also be used with
`AsyncSSH <https://asyncssh.readthedocs.io/en/latest/>`_ (since 1.16.0)
to communicate with an engine on a remote computer.

.. code:: python

    import asyncio
    import asyncssh
    import chess
    import chess.engine

    async def main():
        async with asyncssh.connect("localhost") as conn:
            channel, engine = await conn.create_subprocess(chess.engine.UciProtocol, "/usr/bin/stockfish")
            await engine.initialize()

            # Play, analyse, ...
            await engine.ping()

    asyncio.run(main())

Reference
---------

.. autoclass:: chess.engine.EngineError

.. autoclass:: chess.engine.EngineTerminatedError

.. autoclass:: chess.engine.AnalysisComplete

.. autofunction:: chess.engine.popen_uci

.. autofunction:: chess.engine.popen_xboard

.. autoclass:: chess.engine.EngineProtocol
    :members: initialize, ping, quit

    .. py:attribute:: returncode

        Future: Exit code of the process.

    .. py:attribute:: id

        Dictionary of information about the engine. Common keys are ``name``
        and ``author``.

.. autoclass:: chess.engine.UciProtocol

.. autoclass:: chess.engine.XBoardProtocol

.. autoclass:: chess.engine.SimpleEngine
    :members:

.. autoclass:: chess.engine.SimpleAnalysisResult
    :members:

.. autofunction:: chess.engine.EventLoopPolicy
