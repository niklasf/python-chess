PGN parsing and writing
=======================

Game model
----------

Games are represented as a tree of moves. Each `GameNode` can have extra
information such as comments. The root node of a game
(`Game` extends `GameNode`) also holds general information, such as game
headers.

.. autoclass:: chess.pgn.Game
    :members:

    .. py:attribute:: headers

        A `collections.OrderedDict()` of game headers.

.. autoclass:: chess.pgn.GameNode
    :members:

    .. py:attribute:: parent

        The parent node or `None` if this is the root node of the game.

    .. py:attribute:: move

        The move leading to this node or `None` if this is the root node of the
        game.

    .. py:attribute:: nags
        :annotation: = set()

        A set of NAGs as integers. NAGs always go behind a move, so the root
        node of the game can have none.

    .. py:attribute:: comment
        :annotation: = ''

        A comment that goes behind the move leading to this node. The root
        node of the game can have no comment.

    .. py:attribute:: starting_comment
        :annotation: = ''

        A comment for the start of a variation or the game. Only nodes that
        actually start a variation (`starts_variation()`) and the game itself
        can have a starting comment.

    .. py:attribute:: variations

        A list of child nodes.

Parsing
-------

.. autofunction:: chess.pgn.read_game

.. autofunction:: chess.pgn.scan_offsets

Writing
-------

Exporter objects are used to allow extensible formatting of PGN like data.

.. autoclass:: chess.pgn.StringExporter
    :members:

.. autoclass:: chess.pgn.FileExporter
    :members:

NAGs
----

Numeric anotation glyphs describe moves and positions using standardized codes
that are understood by many chess programs.

.. py:data:: NAG_NULL
    :annotation: = 0
.. py:data:: NAG_GOOD_MOVE
    :annotation: = 1
.. py:data:: NAG_MISTAKE
    :annotation: = 2
.. py:data:: NAG_BRILLIANT_MOVE
    :annotation: = 3
.. py:data:: NAG_BLUNDER
    :annotation: = 4
.. py:data:: NAG_SPECULATIVE_MOVE
    :annotation: = 5
.. py:data:: NAG_DUBIOUS_MOVE
    :annotation: = 6
