python-chess: a pure Python chess library
=========================================

.. image:: https://travis-ci.org/niklasf/python-chess.svg?branch=master
    :target: https://travis-ci.org/niklasf/python-chess

Introduction
------------

This is the scholars mate in python-chess:

::

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

http://pythonhosted.org/python-chess/core.html

Features
--------

* Legal move generator and move validation. This includes all castling
  rules and en-passant captures.

  ::

      >>> chess.Move.from_uci("a8a1") in board.legal_moves
      False

* Make and unmake moves.

  ::

      >>> Qf7 = board.pop() # Unmake last move (Qf7#)
      >>> Qf7
      Move.from_uci('h5f7')

      >>> board.push(Qf7) # Restore

* Detects checkmates, stalemates and draws by insufficient material.
  Has a half-move clock.

  ::

      >>> board.is_stalemate()
      False
      >>> board.is_insufficient_material()
      False
      >>> board.is_game_over()
      True
      >>> board.half_moves
      0

* Detects checks and attacks.

  ::

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

  ::

      >>> board = chess.Bitboard()
      >>> board.san(chess.Move(chess.E2, chess.E4))
      'e4'

* Parses and creates FENs.

  ::

      >>> board.fen()
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
      >>> board = chess.Bitboard("8/8/8/2k5/4K3/8/8/8 w - - 4 45")
      >>> board.piece_at(chess.C5)
      Piece.from_symbol('k')

* Parses and creates EPDs.

  ::

      >>> board = chess.Bitboard()
      >>> board.epd(bm=chess.Move.from_uci("d2d4"))
      'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - bm d4;'

      >>> ops = board.set_epd("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";")
      >>> ops == {'bm': chess.Move.from_uci('d6d1'), 'id': 'BK.01'}
      True

* Read Polyglot opening books.

  ::

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

* Read and write PGNs.

  ::

      >>> import chess.pgn

      >>> pgn = open("data/games/kasparov-deep-blue-1997.pgn")
      >>> first_game = chess.pgn.read_game(pgn)
      >>> pgn.close()

      >>> first_game.headers["White"]
      'Garry Kasparov'
      >>> first_game.headers["Result"]
      '1-0'

Peformance
----------
python-chess is not intended to be used by serious chess engines where
performance is critical. The goal is rather to create a simple and relatively
highlevel library.

However, even though bit fiddling in Python is not as fast as in C or C++,
the current version is still much faster than previous attempts including
the naive x88 move generation from libchess.

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
