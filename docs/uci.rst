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

Asynchronous communication
--------------------------

Info handler
------------

.. _Universal Chess Interface: https://chessprogramming.wikispaces.com/UCI
