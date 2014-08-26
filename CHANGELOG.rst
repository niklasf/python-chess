Changelog for python-chess
==========================

This project is pretty young and maturing only slowly. At the current stage it
is more important to get things right, than to be consistent with previous
versions. Use this changelog to see what changed in a new release, because this
might include API breaking changes.

New in v0.4.1
-------------

* Fix `is_fivefold_repitition()`: The new fivefold repitition rule requires
  the repititions to occur on *alternating consecutive* moves.

* Minor testing related improvements: Close PGN files, allow running via
  setuptools.

* Add recently introduced features to README.

New in v0.4.0
-------------

* Introduce `can_claim_draw()`, `can_claim_fifty_moves()` and
  `can_claim_threefold_repitition()`.

* Since the first of July 2014 a game is also over (even without claim by one
  of the players) if there were 75 moves without a pawn move or capture or
  a fivefold repitition. Let `is_game_over()` respect that. Introduce
  `is_seventyfive_moves()` and `is_fivefold_repitition()`. Other means of
  ending a game take precedence.

* Threefold repitition checking requires efficient hashing of positions
  to build the table. So performance improvements were needed there. The
  default polyglot compatible zobrist hashes are now built incrementally.

* Fix low level rotation operations `l90()`, `l45()` and `r45()`. There was
  no problem in core because correct versions of the functions were inlined.

* Fix equality and inequality operators for `Bitboard`, `Move` and `Piece`.
  Also make them robust against comparisons with incompatible types.

* Provide equality and inequality operators for `SquareSet` and
  `polyglot.Entry`.

* Fix return values of incremental arithmetical operations for `SquareSet`.

* Make `polyglot.Entry` a `collections.namedtuple`.

* Determine and improve test coverage.

* Minor coding style fixes.

New in v0.3.1
-------------

* `Bitboard.status()` now correctly detects `STATUS_INVALID_EP_SQUARE`,
  instead of errors or false reports.

* Polyglot opening book reader now correctly handles knight underpromotions.

* Minor coding style fixes, including removal of unused imports.

New in v0.3.0
-------------

* Rename property `half_moves` of `Bitboard` to `halfmove_clock`.

* Rename property `ply` of `Bitboard` to `fullmove_number`.

* Let PGN parser handle symbols like `!`, `?`, `!?` and so on by converting
  them to NAGs.

* Add a human readable string representation for Bitboards.

  .. code:: python

      >>> print(chess.Bitboard())
      r n b q k b n r
      p p p p p p p p
      . . . . . . . .
      . . . . . . . .
      . . . . . . . .
      . . . . . . . .
      P P P P P P P P
      R N B Q K B N R

* Various documentation improvements.

New in v0.2.0
-------------

* Implement PGN parsing and writing.
* Hugely improve test coverage and use Travis CI for continuous integration and
  testing.
* Create an API documentation.
* Improve Polyglot opening-book handling.

New in v0.1.0
-------------

Apply the lessons learned from the previous releases, redesign the API and
implement it in pure Python.

New in v0.0.4
-------------

Implement the basics in C++ and provide bindings for Python. Obviously
performance was a lot better - but at the expense of having to compile
code for the target platform.

Pre v0.0.4
----------

First experiments with a way too slow pure Python API, creating way too many
objects for basic operations.
