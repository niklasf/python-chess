python-chess: a chess library
=============================

Introduction
------------

This is the scholars mate in python-chess:

```python
pos = chess.Position()
pos.make_move(pos.get_move_from_san("e4"))
pos.make_move(pos.get_move_from_san("e5"))
pos.make_move(pos.get_move_from_san("Qh5"))
pos.make_move(pos.get_move_from_san("Nc6"))
pos.make_move(pos.get_move_from_san("Bc4"))
pos.make_move(pos.get_move_from_san("Nf6"))
pos.make_move(pos.get_move_from_san("Qxf7"))
assert pos.is_checkmate()
```

Features
--------

* Legal move generator and move validation. This includes all castling
  rules and en-passant captures.
* Detects checkmates, stalemates and draws by insufficient material.
  Has a half-move clock.
* Detects checks and can enumerate attackers and defenders of a square.
* Read Polyglot opening books.

License
-------
python-chess is licensed under the GPL3. See the LICENSE file for the
full copyright and license information.
