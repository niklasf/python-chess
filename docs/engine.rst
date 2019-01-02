Experimental Engine API
=======================

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

.. autoclass:: chess.engine.Score
    :members:

Reference
---------

http://hgm.nubati.net/CECP.html
https://www.chessprogramming.org/UCI

.. autofunction:: chess.engine.popen_uci

.. autoclass:: chess.engine.EngineProtocol
    :members:

.. autoclass:: chess.engine.UciProtocol
    :members:

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
