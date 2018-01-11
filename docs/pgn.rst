PGN parsing and writing
=======================

Parsing
-------

.. autofunction:: chess.pgn.read_game

Writing
-------

If you want to export your game with all headers, comments and variations,
you can do it like this:

>>> import chess
>>> import chess.pgn
>>>
>>> game = chess.pgn.Game()
>>> game.headers["Event"] = "Example"
>>> node = game.add_variation(chess.Move.from_uci("e2e4"))
>>> node = node.add_variation(chess.Move.from_uci("e7e5"))
>>> node.comment = "Comment"
>>>
>>> print(game)
[Event "Example"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "*"]
<BLANKLINE>
1. e4 e5 { Comment } *

Remember that games in files should be separated with extra blank lines.

>>> print(game, file=open("/dev/null", "w"), end="\n\n")

Use the :class:`~chess.pgn.StringExporter()` or
:class:`~chess.pgn.FileExporter()` visitors if you need more control.

Game model
----------

Games are represented as a tree of moves. Each :class:`~chess.pgn.GameNode` can have extra
information, such as comments. The root node of a game
(:class:`~chess.pgn.Game` extends the :class:`~chess.pgn.GameNode`) also
holds general information, such as game headers.

.. autoclass:: chess.pgn.Game
    :members:

    .. py:attribute:: headers

        A mapping of headers. By default, the following 7 headers are provided:

        >>> import chess.pgn
        >>>
        >>> game = chess.pgn.Game()
        >>> game.headers["Event"]
        '?'
        >>> game.headers["Site"]
        '?'
        >>> game.headers["Date"]
        '????.??.??'
        >>> game.headers["Round"]
        '?'
        >>> game.headers["White"]
        '?'
        >>> game.headers["Black"]
        '?'
        >>> game.headers["Result"]
        '*'

    .. py:attribute:: errors

        A list of illegal or ambiguous move errors encountered while parsing
        the game.

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

        A comment that goes behind the move leading to this node. Comments
        that occur before any move are assigned to the root node.

    .. py:attribute:: starting_comment
        :annotation: = ''

        A comment for the start of a variation. Only nodes that
        actually start a variation (:func:`~chess.pgn.GameNode.starts_variation()`
        checks this) can have a starting comment. The root node can not have
        a starting comment.

    .. py:attribute:: variations

        A list of child nodes.

Visitors
--------

Visitors are an advanced concept for game tree traversal.

.. autoclass:: chess.pgn.BaseVisitor
    :members:

The following visitors are readily available.

.. autoclass:: chess.pgn.GameModelCreator
    :members:

.. autoclass:: chess.pgn.StringExporter
    :members:

.. autoclass:: chess.pgn.FileExporter
    :members:

NAGs
----

Numeric anotation glyphs describe moves and positions using standardized codes
that are understood by many chess programs. During PGN parsing, annotations
like ``!``, ``?``, ``!!``, etc., are also converted to NAGs.

.. autodata:: chess.pgn.NAG_GOOD_MOVE
.. autodata:: chess.pgn.NAG_MISTAKE
.. autodata:: chess.pgn.NAG_BRILLIANT_MOVE
.. autodata:: chess.pgn.NAG_BLUNDER
.. autodata:: chess.pgn.NAG_SPECULATIVE_MOVE
.. autodata:: chess.pgn.NAG_DUBIOUS_MOVE

Skimming
--------

These functions allow for quickly skimming games without fully parsing them.

.. autofunction:: chess.pgn.scan_headers

.. autofunction:: chess.pgn.scan_offsets
