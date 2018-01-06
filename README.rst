python-chess: a pure Python chess library
=========================================

.. image:: https://travis-ci.org/niklasf/python-chess.svg?branch=master
    :target: https://travis-ci.org/niklasf/python-chess

.. image:: https://coveralls.io/repos/github/niklasf/python-chess/badge.svg?branch=master
   :target: https://coveralls.io/github/niklasf/python-chess?branch=master

.. image:: https://badge.fury.io/py/python-chess.svg
    :target: https://pypi.python.org/pypi/python-chess

.. image:: https://readthedocs.org/projects/python-chess/badge/?version=latest
    :target: https://python-chess.readthedocs.io/en/latest/

Introduction
------------

python-chess is a pure Python chess library with move generation, move
validation and support for common formats. This is the Scholar's mate in
python-chess:

.. code:: python

    >>> import chess

    >>> board = chess.Board()

    >>> board.legal_moves  # doctest: +ELLIPSIS
    <LegalMoveGenerator at ... (Nh3, Nf3, Nc3, Na3, h3, g3, f3, e3, d3, c3, ...)>
    >>> chess.Move.from_uci("a8a1") in board.legal_moves
    False

    >>> board.push_san("e4")
    Move.from_uci('e2e4')
    >>> board.push_san("e5")
    Move.from_uci('e7e5')
    >>> board.push_san("Qh5")
    Move.from_uci('d1h5')
    >>> board.push_san("Nc6")
    Move.from_uci('b8c6')
    >>> board.push_san("Bc4")
    Move.from_uci('f1c4')
    >>> board.push_san("Nf6")
    Move.from_uci('g8f6')
    >>> board.push_san("Qxf7")
    Move.from_uci('h5f7')

    >>> board.is_checkmate()
    True

    >>> board
    Board('r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4')

`Documentation <https://python-chess.readthedocs.io/en/latest/>`__
-------------------------------------------------------------------

* `Core <https://python-chess.readthedocs.io/en/latest/core.html>`_
* `PGN parsing and writing <https://python-chess.readthedocs.io/en/latest/pgn.html>`_
* `Polyglot opening book reading <https://python-chess.readthedocs.io/en/latest/polyglot.html>`_
* `Gaviota endgame tablebase probing <https://python-chess.readthedocs.io/en/latest/gaviota.html>`_
* `Syzygy endgame tablebase probing <https://python-chess.readthedocs.io/en/latest/syzygy.html>`_
* `UCI engine communication <https://python-chess.readthedocs.io/en/latest/uci.html>`_
* `Variants <https://python-chess.readthedocs.io/en/latest/variant.html>`_
* `Changelog <https://python-chess.readthedocs.io/en/latest/changelog.html>`_

Features
--------

* Supports Python 2.7, Python 3.3+ and PyPy.

* IPython/Jupyter Notebook integration.
  `SVG rendering docs <https://python-chess.readthedocs.io/en/latest/svg.html>`_.

  .. code:: python

      >>> board  # doctest: +SKIP

  .. image:: https://backscattering.de/web-boardimage/board.png?fen=r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR&lastmove=h5f7&check=e8

* Chess variants: Standard, Chess960, Suicide, Giveaway, Atomic,
  King of the Hill, Racing Kings, Horde, Three-check, Crazyhouse.
  `Variant docs <https://python-chess.readthedocs.io/en/latest/variant.html>`_.

* Make and unmake moves.

  .. code:: python

      >>> Nf3 = chess.Move.from_uci("g1f3")
      >>> board.push(Nf3)  # Make the move

      >>> board.pop()  # Unmake the last move
      Move.from_uci('g1f3')

* Show a simple ASCII board.

  .. code:: python

      >>> board = chess.Board("r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4")
      >>> print(board)
      r . b q k b . r
      p p p p . Q p p
      . . n . . n . .
      . . . . p . . .
      . . B . P . . .
      . . . . . . . .
      P P P P . P P P
      R N B . K . N R

* Detects checkmates, stalemates and draws by insufficient material.

  .. code:: python

      >>> board.is_stalemate()
      False
      >>> board.is_insufficient_material()
      False
      >>> board.is_game_over()
      True

* Detects repetitions. Has a half-move clock.

  .. code:: python

      >>> board.can_claim_threefold_repetition()
      False
      >>> board.halfmove_clock
      0
      >>> board.can_claim_fifty_moves()
      False
      >>> board.can_claim_draw()
      False

  With the new rules from July 2014, a game ends as a draw (even without a
  claim) once a fivefold repetition occurs or if there are 75 moves without
  a pawn push or capture. Other ways of ending a game take precedence.

  .. code:: python

      >>> board.is_fivefold_repetition()
      False
      >>> board.is_seventyfive_moves()
      False

* Detects checks and attacks.

  .. code:: python

      >>> board.is_check()
      True
      >>> board.is_attacked_by(chess.WHITE, chess.E8)
      True

      >>> attackers = board.attackers(chess.WHITE, chess.F3)
      >>> attackers
      SquareSet(0x0000000000004040)
      >>> chess.G2 in attackers
      True
      >>> print(attackers)
      . . . . . . . .
      . . . . . . . .
      . . . . . . . .
      . . . . . . . .
      . . . . . . . .
      . . . . . . . .
      . . . . . . 1 .
      . . . . . . 1 .

* Parses and creates SAN representation of moves.

  .. code:: python

      >>> board = chess.Board()
      >>> board.san(chess.Move(chess.E2, chess.E4))
      'e4'
      >>> board.parse_san('Nf3')
      Move.from_uci('g1f3')
      >>> board.variation_san([chess.Move.from_uci(m) for m in ["e2e4", "e7e5", "g1f3"]])
      '1. e4 e5 2. Nf3'

* Parses and creates FENs, extended FENs and Shredder FENs.

  .. code:: python

      >>> board.fen()
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
      >>> board.shredder_fen()
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w HAha - 0 1'
      >>> board = chess.Board("8/8/8/2k5/4K3/8/8/8 w - - 4 45")
      >>> board.piece_at(chess.C5)
      Piece.from_symbol('k')

* Parses and creates EPDs.

  .. code:: python

      >>> board = chess.Board()
      >>> board.epd(bm=board.parse_uci("d2d4"))
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - bm d4;'

      >>> ops = board.set_epd("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";")
      >>> ops == {'bm': [chess.Move.from_uci('d6d1')], 'id': 'BK.01'}
      True

* Detects `absolute pins and their directions <https://python-chess.readthedocs.io/en/latest/core.html#chess.Board.pin>`_.

* Reads Polyglot opening books.
  `Docs <https://python-chess.readthedocs.io/en/latest/polyglot.html>`__.

  .. code:: python

      >>> import chess.polyglot

      >>> book = chess.polyglot.open_reader("data/polyglot/performance.bin")

      >>> board = chess.Board()
      >>> main_entry = book.find(board)
      >>> main_entry.move()
      Move.from_uci('e2e4')
      >>> main_entry.weight
      1
      >>> main_entry.learn
      0

      >>> book.close()

* Reads and writes PGNs. Supports headers, comments, NAGs and a tree of
  variations.
  `Docs <https://python-chess.readthedocs.io/en/latest/pgn.html>`__.

  .. code:: python

      >>> import chess.pgn

      >>> with open("data/pgn/molinari-bordais-1979.pgn") as pgn:
      ...     first_game = chess.pgn.read_game(pgn)

      >>> first_game.headers["White"]
      'Molinari'
      >>> first_game.headers["Black"]
      'Bordais'

      >>> # Get the main line as a list of moves.
      >>> moves = first_game.main_line()
      >>> first_game.board().variation_san(moves)
      '1. e4 c5 2. c4 Nc6 3. Ne2 Nf6 4. Nbc3 Nb4 5. g3 Nd3#'

      >>> # Iterate through the main line of this embarrassingly short game.
      >>> node = first_game
      >>> while not node.is_end():
      ...     next_node = node.variations[0]
      ...     print(node.board().san(next_node.move))
      ...     node = next_node
      e4
      c5
      c4
      Nc6
      Ne2
      Nf6
      Nbc3
      Nb4
      g3
      Nd3#

      >>> first_game.headers["Result"]
      '0-1'

* Probe Gaviota endgame tablebases (DTM, WDL).
  `Docs <https://python-chess.readthedocs.io/en/latest/gaviota.html>`__.

* Probe Syzygy endgame tablebases (DTZ, WDL).
  `Docs <https://python-chess.readthedocs.io/en/latest/syzygy.html>`__.

  .. code:: python

      >>> import chess.syzygy

      >>> tablebases = chess.syzygy.open_tablebases("data/syzygy/regular")

      >>> # Black to move is losing in 53 half moves (distance to zero) in this
      >>> # KNBvK endgame.
      >>> board = chess.Board("8/2K5/4B3/3N4/8/8/4k3/8 b - - 0 1")
      >>> tablebases.probe_dtz(board)
      -53

      >>> tablebases.close()

* Communicate with an UCI engine.
  `Docs <https://python-chess.readthedocs.io/en/latest/uci.html>`__.

  .. code:: python

      >>> import chess.uci

      >>> engine = chess.uci.popen_engine("stockfish")
      >>> engine.uci()
      >>> engine.author  # doctest: +SKIP
      'Tord Romstad, Marco Costalba and Joona Kiiski'

      >>> # Synchronous mode.
      >>> board = chess.Board("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - 0 1")
      >>> engine.position(board)
      >>> engine.go(movetime=2000)  # Gets a tuple of bestmove and ponder move
      BestMove(bestmove=Move.from_uci('d6d1'), ponder=Move.from_uci('c1d1'))

      >>> # Asynchronous mode.
      >>> def callback(command):
      ...    bestmove, ponder = command.result()
      ...    assert bestmove == chess.Move.from_uci('d6d1')
      ...
      >>> command = engine.go(movetime=2000, async_callback=callback)
      >>> command.done()
      False
      >>> command.result()
      BestMove(bestmove=Move.from_uci('d6d1'), ponder=Move.from_uci('c1d1'))
      >>> command.done()
      True

      >>> # Quit.
      >>> engine.quit()
      0

Installing
----------

Download and install the latest release:

::

    pip install python-chess[engine,gaviota]

Selected use cases
------------------

If you like, let me know if you are creating something intresting with
python-chess, for example:

* a stand-alone chess computer based on DGT board – http://www.picochess.org/
* a website to probe Syzygy endgame tablebases – https://syzygy-tables.info/
* a GUI to play against UCI chess engines – http://johncheetham.com/projects/jcchess/
* an HTTP microservice to render board images – https://github.com/niklasf/web-boardimage
* a bot to play chess on Telegram – https://github.com/cxjdavin/tgchessbot
* a command-line PGN annotator – https://github.com/rpdelaney/python-chess-annotator
* an UCI chess engine – https://github.com/flok99/feeks

Acknowledgements
----------------

Thanks to the Stockfish authors and thanks to Sam Tannous for publishing his
approach to `avoid rotated bitboards with direct lookup (PDF) <http://arxiv.org/pdf/0704.3773.pdf>`_
alongside his GPL2+ engine `Shatranj <https://github.com/stannous/shatranj>`_.
Some move generation ideas are taken from these sources.

Thanks to Ronald de Man for his
`Syzygy endgame tablebases <https://github.com/syzygy1/tb>`_.
The probing code in python-chess is very directly ported from his C probing code.

Thanks to Miguel A. Ballicora for his
`Gaviota tablebases <https://github.com/michiguel/Gaviota-Tablebases>`_.
(I wish the generating code was free software.)

License
-------

python-chess is licensed under the GPL 3 (or any later version at your option).
Check out LICENSE.txt for the full text.
