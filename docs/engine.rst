UCI/XBoard engine communication
===============================

UCI and XBoard are protocols for communicating with chess engines. This module
implements an abstraction for playing moves and analysing positions with
both kinds of engines.

.. warning::
    Many popular chess engines make no guarantees, not even memory
    safety, when parameters and positions are not completely
    :func:`valid <chess.Board.is_valid()>`. This module tries to deal with
    benign misbehaving engines, but ultimately they are executables running
    on your system.

The preferred way to use the API is with an
`asyncio <https://docs.python.org/3/library/asyncio.html>`_ event loop
(examples show usage with Python 3.7 or later).
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
        result = engine.play(board, chess.engine.Limit(time=0.1))
        board.push(result.move)

    engine.quit()

.. code:: python

    import asyncio
    import chess
    import chess.engine

    async def main() -> None:
        transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")

        board = chess.Board()
        while not board.is_game_over():
            result = await engine.play(board, chess.engine.Limit(time=0.1))
            board.push(result.move)

        await engine.quit()

    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())

.. autoclass:: chess.engine.Protocol
    :members: play

.. autoclass:: chess.engine.Limit
    :members:

    .. py:attribute:: time
        :type: Optional[float]

        Search exactly *time* seconds.

    .. py:attribute:: depth
        :type: Optional[int]

        Search *depth* ply only.

    .. py:attribute:: nodes
        :type: Optional[int]

        Search only a limited number of *nodes*.

    .. py:attribute:: mate
        :type: Optional[int]

        Search for a mate in *mate* moves.

    .. py:attribute:: white_clock
        :type: Optional[float]

        Time in seconds remaining for White.

    .. py:attribute:: black_clock
        :type: Optional[float]

        Time in seconds remaining for Black.

    .. py:attribute:: white_inc
        :type: Optional[float]

        Fisher increment for White, in seconds.

    .. py:attribute:: black_inc
        :type: Optional[float]

        Fisher increment for Black, in seconds.

    .. py:attribute:: remaining_moves
        :type: Optional[int]

        Number of moves to the next time control. If this is not set, but
        *white_clock* and *black_clock* are, then it is sudden death.

.. autoclass:: chess.engine.PlayResult
    :members:

    .. py:attribute:: move
        :type: Optional[chess.Move]

        The best move according to the engine, or ``None``.

    .. py:attribute:: ponder
        :type: Optional[chess.Move]

        The response that the engine expects after *move*, or ``None``.

    .. py:attribute:: info
        :type: chess.engine.InfoDict

        A dictionary of extra information sent by the engine. Commonly used
        keys are: ``score`` (a :class:`~chess.engine.PovScore`),
        ``pv`` (a list of :class:`~chess.Move` objects),
        ``depth``, ``seldepth``, ``time`` (in seconds), ``nodes``, ``nps``,
        ``tbhits``, ``multipv``.

        Others: ``currmove``, ``currmovenumber``, ``hashfull``, ``cpuload``,
        ``refutation``, ``currline``, ``ebf``, ``wdl``, and ``string``.

    .. py:attribute:: draw_offered
        :type: bool

        Whether the engine offered a draw before moving.

    .. py:attribute:: resigned
        :type: bool

        Whether the engine resigned.

Analysing and evaluating a position
-----------------------------------

Example:

.. code:: python

    import chess
    import chess.engine

    engine = chess.engine.SimpleEngine.popen_uci("/usr/bin/stockfish")

    board = chess.Board()
    info = engine.analyse(board, chess.engine.Limit(time=0.1))
    print("Score:", info["score"])
    # Score: +20

    board = chess.Board("r1bqkbnr/p1pp1ppp/1pn5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 2 4")
    info = engine.analyse(board, chess.engine.Limit(depth=20))
    print("Score:", info["score"])
    # Score: #+1

    engine.quit()

.. code:: python

    import asyncio
    import chess
    import chess.engine

    async def main() -> None:
        transport, engine = await chess.engine.popen_uci("/usr/bin/stockfish")

        board = chess.Board()
        info = await engine.analyse(board, chess.engine.Limit(time=0.1))
        print(info["score"])
        # Score: +20

        board = chess.Board("r1bqkbnr/p1pp1ppp/1pn5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 2 4")
        info = await engine.analyse(board, chess.engine.Limit(depth=20))
        print(info["score"])
        # Score: #+1

        await engine.quit()

    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())

.. autoclass:: chess.engine.Protocol
    :members: analyse

.. autoclass:: chess.engine.PovScore
    :members:

    .. py:attribute:: relative
        :type: chess.engine.Score

        The relative :class:`~chess.engine.Score`.

    .. py:attribute:: turn
        :type: chess.Color

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

    async def main() -> None:
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

.. autoclass:: chess.engine.Protocol
    :members: analysis

.. autoclass:: chess.engine.AnalysisResult
    :members:

    .. py:attribute:: info
        :type: chess.engine.InfoDict

        A dictionary of aggregated information sent by the engine. This is
        actually an alias for ``multipv[0]``.

    .. py:attribute:: multipv
        :type: List[chess.engine.InfoDict]

        A list of dictionaries with aggregated information sent by the engine.
        One item for each root move.

.. autoclass:: chess.engine.BestMove
    :members:

    .. py:attribute:: move
        :type: Optional[chess.Move]

        The best move according to the engine, or ``None``.

    .. py:attribute:: ponder
        :type: Optional[chess.Move]

        The response that the engine expects after *move*, or ``None``.

Options
-------

:func:`~chess.Protocol.configure()`,
:func:`~chess.Protocol.play()`,
:func:`~chess.Protocol.analyse()` and
:func:`~chess.Protocol.analysis()` accept a dictionary of options.

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

    async def main() -> None:
        transport, protocol = await chess.engine.popen_uci("/usr/bin/stockfish")

        # Check available options.
        print(engine.options["Hash"])
        # Option(name='Hash', type='spin', default=16, min=1, max=131072, var=[])

        # Set an option.
        await engine.configure({"Hash": 32})

        # [...]

    asyncio.set_event_loop_policy(chess.engine.EventLoopPolicy())
    asyncio.run(main())

.. autoclass:: chess.engine.Protocol
    :members: configure

    .. py:attribute:: options
        :type: MutableMapping[str, chess.engine.Option]

        Dictionary of available options.

.. autoclass:: chess.engine.Option
    :members: is_managed

    .. py:attribute:: name
        :type: str

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
        :type: chess.engine.ConfigValue

        The default value of the option.

    .. py:attribute:: min
        :type: Optional[int]

        The minimum integer value of a *spin* option.

    .. py:attribute:: max
        :type: Optional[int]

        The maximum integer value of a *spin* option.

    .. py:attribute:: var
        :type: Optional[List[str]]

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

:class:`chess.engine.Protocol` can also be used with
`AsyncSSH <https://asyncssh.readthedocs.io/en/latest/>`_ (since 1.16.0)
to communicate with an engine on a remote computer.

.. code:: python

    import asyncio
    import asyncssh
    import chess
    import chess.engine

    async def main() -> None:
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

.. autoclass:: chess.engine.Protocol
    :members: initialize, ping, quit

    .. py:attribute:: returncode
        :type: asyncio.Future[int]

        Future: Exit code of the process.

    .. py:attribute:: id
        :type: Dict[str, str]

        Dictionary of information about the engine. Common keys are ``name``
        and ``author``.

.. autoclass:: chess.engine.UciProtocol

.. autoclass:: chess.engine.XBoardProtocol

.. autoclass:: chess.engine.SimpleEngine
    :members:

.. autoclass:: chess.engine.SimpleAnalysisResult
    :members:

.. autofunction:: chess.engine.EventLoopPolicy
