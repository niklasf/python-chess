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

Games are represented as a tree of moves. Conceptually each node represents a
position of the game. The tree consists of one root node
(:class:`~chess.pgn.Game`, also holding game headers) and many child
nodes (:class:`~chess.pgn.ChildNode`).
Both extend :class:`~chess.pgn.GameNode`.

.. autoclass:: chess.pgn.GameNode
    :members:

.. autoclass:: chess.pgn.Game
    :members: headers, errors, setup, accept, from_board, without_tag_roster

.. autoclass:: chess.pgn.ChildNode
    :members: parent, move, starting_comment, nags, san, uci, end

Visitors
--------

Visitors are an advanced concept for game tree traversal.

.. autoclass:: chess.pgn.BaseVisitor
    :members:

The following visitors are readily available.

.. autoclass:: chess.pgn.GameBuilder
    :members: handle_error, result

.. autoclass:: chess.pgn.HeadersBuilder

.. autoclass:: chess.pgn.BoardBuilder

.. autoclass:: chess.pgn.SkipVisitor

.. autoclass:: chess.pgn.StringExporter

.. autoclass:: chess.pgn.FileExporter

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

.. autofunction:: chess.pgn.read_headers

.. autofunction:: chess.pgn.skip_game
