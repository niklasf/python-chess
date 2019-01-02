Experimental Engine API
=======================

Evaluate a position
-------------------

>>> import chess.engine
>>>
>>> engine = chess.engine.SimpleEngine.popen_uci("stockfish")
>>>
>>> board = chess.Board()
>>> info = engine.analyse(board, chess.engine.Limit(movetime=100))
>>> info["score"]
Cp(20)
>>>
>>> board = chess.Board("r1bqkbnr/p1pp1ppp/1pn5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 2 4")
>>> info = engine.analyse(board, chess.engine.Limit(depth=20))
>>> info["score"]
Mate.plus(1)

.. autoclass:: chess.engine.EngineProtocol
    :members: analyse

.. autoclass:: chess.engine.Score
    :members:

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

Reference
---------

.. autofunction:: chess.engine.popen_uci

.. autofunction:: chess.engine.popen_xboard

.. autoclass:: chess.engine.EngineProtocol
    :members: configure, play, analyse, analysis, ping

    .. py:attribute:: options

        Dictionary of available options.

    .. py:attribute:: returncode

        Exit code of the process. Future.

.. autoclass:: chess.engine.UciProtocol

.. autoclass:: chess.engine.XBoardProtocol

.. autoclass:: chess.engine.PlayResult
    :members:

.. autoclass:: chess.engine.AnalysisResult
    :members:

.. autoclass:: chess.engine.SimpleEngine
    :members:

.. autoclass:: chess.engine.SimpleAnalysisResult
    :members:

.. autofunction:: chess.engine.setup_event_loop

.. autofunction:: chess.engine.run_in_background
