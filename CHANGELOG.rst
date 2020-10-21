Changelog for python-chess
==========================

New in v1.1.0
-------------

New features:

* Added `chess.svg.board(..., orientation)`. This is a more idiomatic way to
  set the board orientation than `flipped`.
* Added `chess.svg.Arrow.pgn()` and `chess.svg.Arrow.from_pgn()`.

Changes:

* Further relaxed `chess.Board.parse_san()`. Now accepts fully specified moves
  like `e2e4`, even if that is not a pawn move, castling notation with zeros,
  null moves in UCI notation, and null moves in XBoard notation.

New in v1.0.1
-------------

Bugfixes:

* `chess.svg`: Restore SVG Tiny compatibility by splitting colors like
  `#rrggbbaa` into a solid color and opacity.

New in v1.0.0
-------------

See ``CHANGELOG-OLD.rst`` for changes up to v1.0.0.
