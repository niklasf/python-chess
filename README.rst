python-chess: a pure Python chess library
=========================================

.. image:: https://travis-ci.org/niklasf/python-chess.svg?branch=master
    :target: https://travis-ci.org/niklasf/python-chess

Introduction
------------

This is the scholars mate in python-chess:

::

    board = chess.Bitboard()
    board.push_san("e4")
    board.push_san("e5")
    board.push_san("Qh5")
    board.push_san("Nc6")
    board.push_san("Bc4")
    board.push_san("Nf6")
    board.push_san("Qxf7")
    assert board.is_checkmate()

Documentation
-------------

http://pythonhosted.org/python-chess/core.html

Features
--------

* Legal move generator and move validation. This includes all castling
  rules and en-passant captures.

  ::

      assert not chess.Move.from_uci("a8a1") in board.legal_moves

* Detects checkmates, stalemates and draws by insufficient material.
  Has a half-move clock.

  ::

      assert not board.is_stalemate()
      assert not board.is_insufficient_material()
      assert board.is_game_over()

* Detects checks and attacks.

  ::

      assert board.is_check()
      assert board.is_attacked_by(chess.WHITE, chess.E8)

* Parses and creates SAN representation of moves.

  ::

      board = chess.Bitboard()
      assert "e4" == board.san(chess.Move(chess.E2, chess.E4))

* Parses and creates FENs.

  ::

      assert board.fen() == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
      board = chess.Bitboard("8/8/8/2k5/4K3/8/8/8 w - - 4 45")
      assert board.piece_at(chess.C5) == chess.Piece.from_symbol("k")

* Parses and creates EPDs.

  ::

      assert board.epd(bm=chess.Move.from_uci("d2d4")) == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - bm d4"

      ops = board.set_epd("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";")
      assert ops["id"] == "BK.01"
      assert ops["bm"] == chess.Move(chess.D6, chess.D1)

* Read Polyglot opening books.

  ::

      import chess.polyglot

      with chess.polyglot.open_reader("data/opening-books/performance.bin") as book:
          board = chess.Bitboard()

          for entry in book.get_entries_for_position(board):
               assert chess.Move.from_uci("e2e4") == entry.move()
               break

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
