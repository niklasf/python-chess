Changelog for python-chess
==========================

This project is pretty young and maturing only slowly. At the current stage it
is more important to get things right, than to be consistent with previous
versions. Use this changelog to see what changed in a new release, because this
might include API breaking changes.

New in v0.8.2
-------------

Bugfixes:

* `pgn.Game.setup()` with the standard starting position was failing when the
  standard starting position was already set. Thanks to Jordan Bray for
  reporting this.

Optimizations:

* Remove `bswap()` from Syzygy decompression hot path. Directly read integers
  with the correct endianness.

New in v0.8.1
-------------

* Fixed pondering mode in uci module. For example `ponderhit()` was blocking
  indefinitely. Thanks to Valeriy Huz for reporting this.

* Patch by Richard C. Gerkin: Moved searchmoves to the end of the UCI go
  command, where it will not cause other command parameters to be ignored.

* Added missing check or checkmate suffix to castling SANs, e.g. `O-O-O#`.

* Fixed off-by-one error in polyglot opening book binary search. This would
  not have caused problems for real opening books.

* Fixed Python 3 support for reverse polyglot opening book iteration.

* Bestmoves may be literally `(none)` in UCI protocol, for example in
  checkmate positions. Fix parser and return `None` as the bestmove in this
  case.

* Fixed spelling of repetition (was repitition).
  `can_claim_threefold_repetition()` and `is_fivefold_repetition()` are the
  affected method names. Aliases are there for now, but will be removed in the
  next release. Thanks to Jimmy Patrick for reporting this.

* Added `SquareSet.__reversed__()`.

* Use containerized tests on Travis CI, test against Stockfish 6, improved
  test coverage amd various minor clean-ups.

New in v0.8.0
-------------

* **Implement Syzygy endgame tablebase probing.**
  `https://syzygy-tables.info <https://syzygy-tables.info/apidoc?fen=6N1/5KR1/2n5/8/8/8/2n5/1k6%20w%20-%20-%200%201>`_
  is an example project that provides a public API using the new features.

* The interface for aynchronous UCI command has changed to mimic
  `concurrent.futures`. `is_done()` is now just `done()`. Callbacks will
  receive the command object as a single argument instead of the result.
  The `result` property and `wait()` have been removed in favor of a
  synchronously waiting `result()` method.

* The result of the `stop` and `go` UCI commands are now named tuples (instead
  of just normal tuples).

* Add alias `Board` for `Bitboard`.

* Fixed race condition during UCI engine startup. Lines received during engine
  startup sometimes needed to be processed before the Engine object was fully
  initialized.

New in v0.7.0
-------------

* **Implement UCI engine communication.**

* Patch by Matthew Lai: `Add caching for gameNode.board()`.

New in v0.6.0
-------------

* If there are comments in a game before the first move, these are now assigned
  to `Game.comment` instead of `Game.starting_comment`. `Game.starting_comment`
  is ignored from now on. `Game.starts_variation()` is no longer true.
  The first child node of a game can no longer have a starting comment.
  It is possible to have a game with `Game.comment` set, that is otherwise
  completely empty.

* Fix export of games with variations. Previously the moves were exported in
  an unusual (i.e. wrong) order.

* Install `gmpy2` or `gmpy` if you want to use slightly faster binary
  operations.

* Ignore superfluous variation opening brackets in PGN files.

* Add `GameNode.san()`.

* Remove `sparse_pop_count()`. Just use `pop_count()`.

* Remove `next_bit()`. Now use `bit_scan()`.

New in v0.5.0
-------------

* PGN parsing is now more robust: `read_game()` ignores invalid tokens.
  Still exceptions are going to be thrown on illegal or ambiguous moves, but
  this behaviour can be changed by passing an `error_handler` argument.

  .. code:: python

      >>> # Raises ValueError:
      >>> game = chess.pgn.read_game(file_with_illegal_moves)

  .. code:: python

      >>> # Silently ignores errors and continues parsing:
      >>> game = chess.pgn.read_game(file_with_illegal_moves, None)

  .. code:: python

      >>> # Logs the error, continues parsing:
      >>> game = chess.pgn.read_game(file_with_illegal_moves, logger.exception)

  If there are too many closing brackets this is now ignored.

  Castling moves like 0-0 (with zeros) are now accepted in PGNs.
  The `Bitboard.parse_san()` method remains strict as always, though.

  Previously the parser was strictly following the PGN spefification in that
  empty lines terminate a game. So a game like

  ::

      [Event "?"]

      { Starting comment block }

      1. e4 e5 2. Nf3 Nf6 *

  would have ended directly after the starting comment. To avoid this, the
  parser will now look ahead until it finds at least one move or a termination
  marker like `*`, `1-0`, `1/2-1/2` or `0-1`.

* Introduce a new function `scan_headers()` to quickly scan a PGN file for
  headers without having to parse the full games.

* Minor testcoverage improvements.

New in v0.4.2
-------------

* Fix bug where `pawn_moves_from()` and consequently `is_legal()` weren't
  handling en-passant correctly. Thanks to Norbert Naskov for reporting.

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

* **Implement PGN parsing and writing.**
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
