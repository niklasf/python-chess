Engine communication [experimental]
===================================

UCI and XBoard are protocols for communicating with chess engines. This module
implements an abstraction for playing moves and analysing positions with
both kinds of engines.

:warning: This is an experimental module that may change in semver incompatible
   ways. Please weigh in on the design if the provided APIs do not cover
   your use case.

   The intention is to eventually replace ``chess.uci`` and ``chess.xboard``,
   but not before things have settled down and there has been a transition
   period.

   The XBoard implementation is currently only a skeleton.

The preferred way to use the API is with an
`asyncio <https://docs.python.org/3/library/asyncio.html>`_ event loop.
The examples also show a simple synchronous wrapper
:class:`~chess.engine.SimpleEngine` that automatically spawns an event loop
in the background.

Playing
-------

Example: Let Stockfish play against itself, 100 milliseconds per move.

.. code:: python

    import chess
    import chess.engine

    engine = chess.engine.SimpleEngine.popen_uci("stockfish")

    board = chess.Board()
    while not board.is_game_over():
        result = engine.play(board, chess.engine.Limit(movetime=100))
        board.push(result.move)

    engine.quit()

.. code:: python

    import asyncio
    import chess
    import chess.engine

    async def main():
        transport, engine = await chess.engine.popen_uci("stockfish")

        board = chess.Board()
        while not board.is_game_over():
            result = await engine.play(board, chess.engine.Limit(movetime=100))
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

    .. py:attribute:: black_time

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

        The best move accordig to the engine.

    .. py:attribute:: ponder

        The response that the engine expects after *move*, or ``None``.

    .. py:attribute:: info

        A dictionary of extra information sent by the engine. Known keys are
        ``score``, ``depth``, ``seldepth``, ``time``, ``nodes``, ``pv``,
        ``multipv``, ``currmove``, ``currmovenumber``, ``hashfull``, ``nps``,
        ``tbhits``, ``cpuload``, ``refutation``, ``currline``, ``ebf`` and
        ``string``.

Analysing and evaluating a position
-----------------------------------

Example:

.. code:: python

    import chess
    import chess.engine

    engine = chess.engine.SimpleEngine.popen_uci("stockfish")

    board = chess.Board()
    info = engine.analyse(board, chess.engine.Limit(movetime=100))
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
        transport, engine = await chess.engine.popen_uci("stockfish")

        board = chess.Board()
        info = await engine.analyse(board, chess.engine.Limit(movetime=100))
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

.. autoclass:: chess.engine.Score
    :members:

Indefinite or infinite analysis
-------------------------------

Example: Stream information from the engine and stop on an arbitrary condition.

.. code:: python

    import chess
    import chess.engine

    engine = chess.engine.SimpleEngine.popen_uci("stockfish")

    with engine.analysis(chess.Board()) as analysis:
        for info in analysis:
            print(info.get("score"), info.get("pv"))

            # Unusual stop condition.
            if info.get("hashfull", 0) > 900:
                break

    engine.quit()

.. code:: python

    import asyncio
    import chess
    import chess.engine

    async def main():
        transport, engine = await chess.engine.popen_uci("stockfish")

        with await engine.analysis(chess.Board()) as analysis:
            async for info in analysis:
                print(info.get("score"), info.get("pv"))

                # Unusual stop condition.
                if info.get("hashfull", 0) > 900:
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
>>> engine = chess.engine.SimpleEngine.popen_uci("stockfish")
>>>
>>> # Check available options.
>>> engine.options["Hash"]
Option(name='Hash', type='spin', default=16, min=1, max=131072, var=[])
>>>
>>> # Set an option.
>>> engine.configure({"Hash": 32})

.. code:: python

    import asyncio
    import chess.engine

    async def main():
        transport, protocol = await chess.engine.popen_uci("stockfish")

        # Check available options.
        print(engine.options["Hash"])
        # Option(name='Hash', type='spin', default=16, min=1, max=131072, var=[])

        # Set an option.
        await engine.configure({"Hash": 32})

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

Reference
---------

.. autofunction:: chess.engine.popen_uci

.. autofunction:: chess.engine.popen_xboard

.. autoclass:: chess.engine.EngineProtocol
    :members: ping, quit

    .. py:attribute:: returncode

        Future: Exit code of the process.

.. autoclass:: chess.engine.UciProtocol

.. autoclass:: chess.engine.XBoardProtocol

.. autoclass:: chess.engine.SimpleEngine
    :members:

.. autoclass:: chess.engine.SimpleAnalysisResult
    :members:

.. autofunction:: chess.engine.EventLoopPolicy
