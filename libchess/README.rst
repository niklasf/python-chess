libchess: a high level chess library for Python and C++
=======================================================

Introduction
------------

This is the scholars mate in libchess:

::

    pos = libchess.Position()
    pos.make_move_from_san("e4")
    pos.make_move_from_san("e5")
    pos.make_move_from_san("Qh5")
    pos.make_move_from_san("Nc6")
    pos.make_move_from_san("Nf6")
    pos.make_move_from_san("Qxf7")
    assert pos.is_checkmate()

Features
--------

* Legal move generator and move validation. This includes all castling
  rules and en-passant captures.

  ::

      assert not chess.Move.from_uci("a8a1") in pos.get_legal_moves()

* Detects checkmates and stalemates.

  ::

      assert not pos.is_stalemate()

* Detects checks and can enumerate attackers and defenders of a square.

  ::

      assert pos.is_check()
      assert libchess.Square("f7") in pos.get_attackers("w", libchess.Square("e8"))

* Parses and creates SAN representation of moves.

  ::

      pos = libchess.Position()
      move_info = pos.make_move(libchess.Move.from_uci("e2e4"))
      assert "e4" == move_info.san

* Parses and creates FENs.

  ::

      pos = libchess.Position()
      assert pos.fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

      pos = libchess.Position("8/8/8/2k5/4K3/8/8/8 w - - 4 45")
      assert pos["c5"] == libchess.Piece("k")

Building
--------
cmake, libboost-regex-dev and libboost-python-dev are required.

::

    cmake .
    make
    python setup.py install

Performance
-----------
libchess is not intended to be used by chess engines where performance
is critical. The goal is rather to create a simple and highlevel library.

That said: Large parts are in C++ for a reason. libchess generates, validates
and plays moves about 50 times faster than https://github.com/niklasf/python-chess/.

License
-------
python-chess is licensed under the GPL3. See the LICENSE file for the
full copyright and license information.
