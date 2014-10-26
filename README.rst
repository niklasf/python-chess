python-chess: a pure Python chess library
=========================================

.. image:: https://travis-ci.org/niklasf/python-chess.svg?branch=master
    :target: https://travis-ci.org/niklasf/python-chess

.. image:: https://coveralls.io/repos/niklasf/python-chess/badge.png
    :target: https://coveralls.io/r/niklasf/python-chess

.. image:: https://landscape.io/github/niklasf/python-chess/master/landscape.png
    :target: https://landscape.io/github/niklasf/python-chess/master

.. image:: https://pypip.in/version/python-chess/badge.svg
    :target: https://pypi.python.org/pypi/python-chess

Introduction
------------

This is the scholars mate in python-chess:

.. code:: python

    >>> import chess

    >>> board = chess.Bitboard()

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

Documentation
-------------

.. image:: https://readthedocs.org/projects/python-chess/badge/?version=latest
    :target: https://python-chess.readthedocs.org/en/latest/

https://python-chess.readthedocs.org/en/latest/

Features
--------

* Supports Python 2.7 and Python 3.

* Legal move generator and move validation. This includes all castling
  rules and en-passant captures.

  .. code:: python

      >>> chess.Move.from_uci("a8a1") in board.legal_moves
      False

* Make and unmake moves.

  .. code:: python

      >>> Qf7 = board.pop() # Unmake last move (Qf7#)
      >>> Qf7
      Move.from_uci('h5f7')

      >>> board.push(Qf7) # Restore

* Detects checkmates, stalemates and draws by insufficient material.

  .. code:: python

      >>> board.is_stalemate()
      False
      >>> board.is_insufficient_material()
      False
      >>> board.is_game_over()
      True
      >>> board.halfmove_clock
      0

* Detects repititions. Has a half move clock.

  .. code:: python

      >>> board.can_claim_threefold_repitition()
      False
      >>> board.halfmove_clock
      0
      >>> board.can_claim_fifty_moves()
      False
      >>> board.can_claim_draw()
      False

  With the new rules from July 2014 a game ends drawn (even without a claim)
  once a fivefold repitition occurs or if there are 75 moves without a pawn
  push or capture. Other ways of ending a game take precedence.

  .. code:: python

      >>> board.is_fivefold_repitition()
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
      SquareSet(0b100000001000000)
      >>> chess.G2 in attackers
      True


* Parses and creates SAN representation of moves.

  .. code:: python

      >>> board = chess.Bitboard()
      >>> board.san(chess.Move(chess.E2, chess.E4))
      'e4'

* Parses and creates FENs.

  .. code:: python

      >>> board.fen()
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
      >>> board = chess.Bitboard("8/8/8/2k5/4K3/8/8/8 w - - 4 45")
      >>> board.piece_at(chess.C5)
      Piece.from_symbol('k')

* Parses and creates EPDs.

  .. code:: python

      >>> board = chess.Bitboard()
      >>> board.epd(bm=chess.Move.from_uci("d2d4"))
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - bm d4;'

      >>> ops = board.set_epd("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";")
      >>> ops == {'bm': chess.Move.from_uci('d6d1'), 'id': 'BK.01'}
      True

* Read Polyglot opening books.

  .. code:: python

      >>> import chess.polyglot

      >>> book = chess.polyglot.open_reader("data/opening-books/performance.bin")
      >>> board = chess.Bitboard()
      >>> first_entry = next(book.get_entries_for_position(board))
      >>> first_entry.move()
      Move.from_uci('e2e4')
      >>> first_entry.learn
      0
      >>> first_entry.weight
      1

      >>> book.close()

* Read and write PGNs. Supports headers, comments, NAGs and a tree of
  variations.

  .. code:: python

      >>> import chess.pgn

      >>> from __future__ import print_function # Python 2 compability for
      >>>                                       # this example.

      >>> pgn = open("data/games/molinari-bordais-1979.pgn")
      >>> first_game = chess.pgn.read_game(pgn)
      >>> pgn.close()

      >>> first_game.headers["White"]
      'Molinari'
      >>> first_game.headers["Black"]
      'Bordais'

      >>> # Iterate through the mainline of this embarrasingly short game.
      >>> node = first_game
      >>> while node.variations:
      ...     next_node = node.variation(0)
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

Peformance
----------
python-chess is not intended to be used by serious chess engines where
performance is critical. The goal is rather to create a simple and relatively
highlevel library.

You can install the `gmpy2` or `gmpy` (https://code.google.com/p/gmpy/) modules
in order to get a slight performance boost on basic operations like bit scans
and population counts.

python-chess will only ever import very basic general (non-chess-related)
operations from native libraries. All logic is pure Python. There will always
be pure Python fallbacks.

Installing
----------

* With pip:

  ::

      sudo pip install python-chess

* From current source code:

  ::

      python setup.py build
      sudo python setup.py install

License
-------
python-chess is licensed under the GPL3. See the LICENSE file for the
full copyright and license information.

Thanks to the developers of http://chessx.sourceforge.net/. Some of the core
bitboard move generation parts are ported from there.
