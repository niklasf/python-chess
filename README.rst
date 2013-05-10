python-chess: a chess library
=============================

Introduction
------------

This is the scholars mate in python-chess:

::

    pos = chess.Position()
    pos.make_move_from_san("e4")
    pos.make_move_from_san("e5")
    pos.make_move_from_san("Qh5")
    pos.make_move_from_san("Nc6")
    pos.make_move_from_san("Bc4")
    pos.make_move_from_san("Nf6")
    pos.make_move_from_san("Qxf7")
    assert pos.is_checkmate()

Features
--------

* Legal move generator and move validation. This includes all castling
  rules and en-passant captures.

  ::

      assert not chess.Move.from_uci("a8a1") in pos.get_legal_moves()

* Detects checkmates, stalemates and draws by insufficient material.
  Has a half-move clock.

  ::

      assert not pos.is_stalemate()
      assert not pos.is_insufficient_material()
      assert pos.is_game_over()

* Detects checks and can enumerate attackers and defenders of a square.

  ::

      assert pos.is_check()
      assert chess.Square("f7") in pos.get_attackers("w", chess.Square("e8"))

* Parses and creates SAN representation of moves.

  ::

      pos = chess.Position()
      assert "e4" == pos.make_move(chess.Move("e2e4")).san

* Parses and creates FENs.

  ::

      assert pos.fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
      pos = chess.Position("8/8/8/2k5/4K3/8/8/8 w - - 4 45")
      assert pos["c5"] == chess.Piece("k")

* Read Polyglot opening books.

  ::

      book = chess.PolyglotOpeningBook("data/opening-books/performance.bin")
      pos = chess.Position()
      # for entry in book.get_entries_for_position(pos):
      #    assert chess.Move.from_uci("e2e4") == entry["move"]
      #    break

Peformance
----------
python-chess is not intended to be used by chess engines where performance is
critical. The goal is rather to create a simple and highlevel library.

However parts like move generation are in C++ (see the libchess directory) to
improve the performance over pure Python code.

Building
--------
libboost-regex-dev and libboost-python-dev are required.

* With easy_install:

  ::

      sudo easy_install python-chess

* From current source code:

  ::

      python setup.py build
      sudo python setup.py install

License
-------
python-chess is licensed under the GPL3. See the LICENSE file for the
full copyright and license information.
