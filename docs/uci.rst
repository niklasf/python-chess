UCI Engine communication
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

        The author, as sent via *id author*. Just like the name.

    .. py:attribute:: options

        A dictionary of :ref:`options`. The engine should send available options
        when it receives the initial *uci* command.

    .. py:attribute:: uciok

        *threading.Event()* that will be set as soon as *uciok* was received.
        By then name, author and options should be available.

    .. py:attribute:: returncode

        The return code of the operating system process.

    .. py:attribute:: terminated

        *threading.Event()* that will be set as soon as the underyling
        operating system process is terminated and the *returncode* is
        available.

UCI Commands
------------

.. autoclass:: chess.uci.Engine
    :members: uci, debug, isready, setoption, ucinewgame, position, go, stop,
        ponderhit, quit

Asynchronous communication
--------------------------

By default all operations are executed synchronously and their result is
returned. For example

>>> engine.go(movetime=2000)
(Move.from_uci('e2e4'), None)

will take about 2000 milliseconds. All UCI commands have an optional
*async_callback* argument. They will then immediately return information about
the command and continue.

>>> command = engine.go(movetime=2000, async_callback=True)
>>> command.is_done()
False
>>> command.result
None
>>> command.wait() # Synchronously wait for the command to finish
>>> command.is_done()
True
>>> command.result
(Move.from_uci('e2e4'), None)

Instead of just passing *async_callback=True* a callback function may be
passed. It will be invoked **on a different thread** as soon as the command
is completed. Make sure the number of arguments exactly matches the expected
result.

>>> def on_go_finished(bestmove, pondermove):
...     # Will be executed on a different thread.
...     pass
...
>>> command = engine.go(movetime=2000, async_callback=on_go_finished)

All commands are queued and executed in FIFO order (regardless if asynchronous
or not).

.. autoclass:: chess.uci.Command
    :members:

    .. py:attribute:: result

        The result if the command has been completed or *None*.

Info handler
------------

Chess engines may send information about their calculations with the *info*
command. You can register info handlers to be asynchronously notified whenever
the engine sends more information. You would usually subclass the *InfoHandler*
class.

.. autoclass:: chess.uci.Score
    :members:

    .. py:attribute:: cp

        Evaluation is centipawns or *None*.

    .. py:attribute:: mate

        Mate in x or *None*. Negative if the engine thinks it is going to be
        mated.

    .. py:attribute:: lowerbound

        If the score is not exact but only a lowerbound.

    .. py:attribute:: upperbound

        If the score is only an upperbound.

.. autoclass:: chess.uci.InfoHandler
    :members:

    .. py:attribute:: info

        The default implementation stores all received information in this
        dictionary. To get a consistent snapshot use the object as if it were
        a *threading.Lock()*.

        >>> # Register the handler.
        >>> handler = InfoHandler()
        >>> engine.info_handlers.append(handler)

        >>> # Start thinking.
        >>> engine.go(infinite=True)
        ()

        >>> # Wait a moment, then access a consistent snapshot.
        >>> time.sleep(3)
        >>> with handler:
        ...     if "score" in handler.info:
        ...         print("Score: ", handler.info["score"].cp)
        ...         print("Mate: ", handler.info["score"].mate)
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

        Officially documented types are *check* for a boolean value, *spin*
        for an integer value between a minimum and a maximum, *combo* for an
        enumeration of predefined string values (one of which can be selected),
        *button* for an action and *string* for a textfield.

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
