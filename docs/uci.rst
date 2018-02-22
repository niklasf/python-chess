UCI engine communication
========================

The `Universal Chess Interface`_ is a protocol for communicating with engines.

.. autofunction:: chess.uci.popen_engine

.. autofunction:: chess.uci.spur_spawn_engine

.. autoclass:: chess.uci.Engine
    :members: terminate, kill, is_alive

    .. py:attribute:: process

        The underlying operating system process.

    .. py:attribute:: name

        The name of the engine. Conforming engines should send this as
        *id name* when they receive the initial *uci* command.

    .. py:attribute:: author

        The author of the engine. Conforming engines should send this as
        *id author* after the initial *uci* command.

    .. py:attribute:: options

        A case-insensitive dictionary of :ref:`options`. The engine should send
        available options when it receives the initial *uci* command.

    .. py:attribute:: uciok

        :class:`threading.Event()` that will be set as soon as *uciok* was
        received. By then :data:`~chess.uci.Engine.name`,
        :data:`~chess.uci.Engine.author` and :data:`~chess.uci.Engine.options`
        should be available.

    .. py:attribute:: return_code

        The return code of the operating system process.

    .. py:attribute:: terminated

        :class:`threading.Event()` that will be set as soon as the underyling
        operating system process is terminated and the
        :data:`~chess.uci.Engine.return_code` is available.

UCI commands
------------

.. autoclass:: chess.uci.Engine
    :members: uci, debug, isready, setoption, ucinewgame, position, go, stop,
        ponderhit, quit

:exc:`~chess.uci.EngineTerminatedException` is raised if the engine process is
no longer alive.

Asynchronous communication
--------------------------

By default, all operations are executed synchronously and their result is
returned. For example

>>> import chess.uci
>>>
>>> engine = chess.uci.popen_engine("stockfish")
>>>
>>> engine.go(movetime=2000)
BestMove(bestmove=Move.from_uci('e2e4'), ponder=None)

will take about 2000 milliseconds. All UCI commands have an optional
*async_callback* argument. They will then immediately return a `Future`_
and continue.

>>> command = engine.go(movetime=2000, async_callback=True)
>>> command.done()
False
>>> command.result()  # Synchronously wait for the command to finish
BestMove(bestmove=Move.from_uci('e2e4'), ponder=None)
>>> command.done()
True

Instead of just passing *async_callback=True*, a callback function may be
passed. It will be invoked **possibly on a different thread** as soon as the
command is completed. It takes the command future as a single argument.

>>> def on_go_finished(command):
...     # Will likely be executed on a different thread.
...     bestmove, ponder = command.result()
...
>>> command = engine.go(movetime=2000, async_callback=on_go_finished)

Note about castling moves
-------------------------

There are different ways castling moves may be encoded. The normal way to do it
is ``e1g1`` for short castling. The same move would be ``e1h1`` in
*UCI_Chess960* mode.

This is abstracted away by the :mod:`chess.uci` module, but if the engine
supports it, it is recommended to enable *UCI_Chess960* mode.

>>> engine.setoption({"UCI_Chess960": True})

Info handler
------------

.. autoclass:: chess.uci.Score
    :members:

    .. py:attribute:: cp

        Evaluation in centipawns or ``None``.

    .. py:attribute:: mate

        Mate in x or ``None``. Negative number if the engine thinks it is going
        to be mated.

.. autoclass:: chess.uci.InfoHandler
    :members:

    .. py:attribute:: info

        The default implementation stores all received information in this
        dictionary. To get a consistent snapshot, use the object as if it were
        a :class:`threading.Lock()`.

        >>> # Start thinking.
        >>> engine.go(infinite=True, async_callback=True)

        >>> # Wait a moment, then access a consistent snapshot.
        >>> time.sleep(3)
        >>> with info_handler:
        ...     if 1 in info_handler.info["score"]:
        ...         print("Score: ", info_handler.info["score"][1].cp)
        ...         print("Mate: ", info_handler.info["score"][1].mate)
        Score: 34
        Mate: None

.. _options:

Options
-------

.. autoclass:: chess.uci.Option

    .. py:attribute:: name

        The name of the option.

    .. py:attribute:: type

        The type of the option.

        Officially documented types are ``check`` for a boolean value, ``spin``
        for an integer value between a minimum and a maximum, ``combo`` for an
        enumeration of predefined string values (one of which can be selected),
        ``button`` for an action and ``string`` for a text field.

    .. py:attribute:: default

        The default value of the option.

        There is no need to send a *setoption* command with the defaut value.

    .. py:attribute:: min

        The minimum integer value of a *spin* option.

    .. py:attribute:: max

        The maximum integer value of a *spin* option.

    .. py:attribute:: var

        A list of allows string values for a *combo* option.


.. _Universal Chess Interface: https://chessprogramming.wikispaces.com/UCI
.. _Future: https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future
