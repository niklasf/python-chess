PGN parsing and writing
=======================

Game model
----------

.. autoclass:: chess.pgn.Game
    :members:

.. autoclass:: chess.pgn.GameNode
    :members:

Parsing
-------

.. autofunction:: chess.pgn.read_game

.. autofunction:: chess.pgn.scan_offsets

Writing
-------



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
