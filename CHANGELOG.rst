Changelog for python-chess
==========================

New in v0.23.5
--------------

Bugfixes:

* Atomic chess: KNvKN is not insufficient material.
* Crazyhouse: Detect insufficient material. This can not happen unless the
  game was started with insufficient material.

Changes:

* Better error messages when parsing info from UCI engine fails.
* Better error message for `b.set_board_fen(b.fen())`.

New in v0.23.4
--------------

New features:

* XBoard: Support pondering. Thanks Manik Charan.
* UCI: Support unofficial `info ebf`.

Bugfixes:

* Implement 16 bit DTZ mapping, which is required for some of the longest
  7 piece endgames.

New in v0.23.3
--------------

New features:

* XBoard: Support `variant`. Thanks gbtami.

New in v0.23.2
--------------

Bugfixes:

* XBoard: Handle multiple features and features with spaces. Thanks gbtami.
* XBoard: Ignore debug output prefixed with `#`. Thanks Dan Ravensloft and
  Manik Charan.

New in v0.23.1
--------------

Bugfixes:

* Fix DTZ in case of mate in 1. This is a cosmetic fix, as the previous
  behavior was only off by one (which is allowed by design).

New in v0.23.0
--------------

New features:

* Experimental support for 7 piece Syzygy tablebases.

Changes:

* `chess.syzygy.filenames()` was renamed to `tablenames()` and
  gained an optional `piece_count=6` argument.
* `chess.syzygy.normalize_filename()` was renamed to `normalize_tablename()`.
* The undocumented constructors of `chess.syzygy.WdlTable` and
  `chess.syzygy.DtzTable` have been changed.

New in v0.22.2
--------------

Bugfixes:

* In standard chess promoted pieces were incorrectly considered as
  distinguishable from normal pieces with regard to position equality
  and threefold repetition. Thanks to kn-sq-tb for reporting.

Changes:

* The PGN `game.headers` are now a custom mutable mapping that validates the
  validity of tag names.
* Basic attack and pin methods moved to `BaseBoard`.
* Documentation fixes and improvements.

New features:

* Added `Board.lan()` for long algebraic notation.

New in v0.22.1
--------------

New features:

* Added `Board.mirror()`, `SquareSet.mirror()` and `bswap()`.
* Added `chess.pgn.GameNode.accept_subgame()`.
* XBoard: Added `resign`, `analyze`, `exit`, `name`, `rating`, `computer`,
  `egtpath`, `pause`, `resume`. Completed option parsing.

Changes:

* `chess.pgn`: Accept FICS wilds without warning.
* XBoard: Inform engine about game results.

Bugfixes:

* `chess.pgn`: Allow games without movetext.
* XBoard: Fixed draw handling.

New in v0.22.0
--------------

Changes:

* `len(board.legal_moves)` **replaced by** `board.legal_moves.count()`.
  Previously `list(board.legal_moves)` was generating moves twice, resulting in
  a considerable slowdown. Thanks to Martin C. Doege for reporting.
* **Dropped Python 2.6 support.**
* XBoard: `offer_draw` renamed to `draw`.

New features:

* XBoard: Added `DrawHandler`.

New in v0.21.2
--------------

Changes:

* `chess.svg` is now fully SVG Tiny 1.2 compatible. Removed
  `chess.svg.DEFAULT_STYLE` which would from now on be always empty.

New in v0.21.1
--------------

Bugfixes:

* `Board.set_piece_at()` no longer shadows optional `promoted`
  argument from `BaseBoard`.
* Fixed `ThreeCheckBoard.is_irreversible()` and
  `ThreeCheckBoard._transposition_key()`.

New features:

* Added `Game.without_tag_roster()`. `chess.pgn.StringExporter()` can now
  handle games without any headers.
* XBoard: `white`, `black`, `random`, `nps`, `otim`, `undo`, `remove`. Thanks
  to Manik Charan.

Changes:

* Documentation fixes and tweaks by Boštjan Mejak.
* Changed unicode character for empty squares in `Board.unicode()`.

New in v0.21.0
--------------

Release yanked.

New in v0.20.1
--------------

Bugfixes:

* Fix arrow positioning on SVG boards.
* Documentation fixes and improvements, making most doctests runnable.

New in v0.20.0
--------------

Bugfixes:

* Some XBoard commands were not returning futures.
* Support semicolon comments in PGNs.

Changes:

* Changed FEN and EPD formatting options. It is now possible to include en
  passant squares in FEN and X-FEN style, or to include only strictly relevant
  en passant squares.
* Relax en passant square validation in `Board.set_fen()`.
* Ensure `is_en_passant()`, `is_capture()`, `is_zeroing()` and
  `is_irreversible()` strictly return bools.
* Accept `Z0` as a null move in PGNs.

New features:

* XBoard: Add `memory`, `core`, `stop` and `movenow` commands.
  Abstract `post`/`nopost`. Initial `FeatureMap` support. Support `usermove`.
* Added `Board.has_pseudo_legal_en_passant()`.
* Added `Board.piece_map()`.
* Added `SquareSet.carry_rippler()`.
* Factored out some (unstable) low level APIs: `BB_CORNERS`,
  `_carry_rippler()`, `_edges()`.

New in v0.19.0
--------------

New features:

* **Experimental XBoard engine support.** Thanks to Manik Charan and
  Cash Costello. Expect breaking changes in future releases.
* Added an undocumented `chess.polyglot.ZobristHasher` to make Zobrist hashing
  easier to extend.

Bugfixes:

* Merely pseudo-legal en passant does no longer count for repetitions.
* Fixed repetition detection in Three-Check and Crazyhouse. (Previously
  check counters and pockets were ignored.)
* Checking moves in Three-Check are now considered as irreversible by
  `ThreeCheckBoard.is_irreversible()`.
* `chess.Move.from_uci("")` was raising `IndexError` instead of `ValueError`.
  Thanks Jonny Balls.

Changes:

* `chess.syzygy.Tablebases` constructor no longer supports directly opening
  a directory. Use `chess.syzygy.open_tablebases()`.
* `chess.gaviota.PythonTablebases` and `NativeTablebases` constructors
  no longer support directly opening a directory.
  Use `chess.gaviota.open_tablebases()`.
* `chess.Board` instances are now compared by the position they represent,
  not by exact match of the internal data structures (or even move history).
* Relaxed castling right validation in Chess960: Kings/rooks of opposing sites
  are no longer required to be on the same file.
* Removed misnamed `Piece.__unicode__()` and `BaseBoard.__unicode__()`. Use
  `Piece.unicode_symbol()` and `BaseBoard.unicode()` instead.
* Changed `chess.SquareSet.__repr__()`.
* Support `[Variant "normal"]` in PGNs.
* `pip install python-chess[engine]` instead of `python-chess[uci]` (since
  the extra dependencies are required for both UCI and XBoard engines).
* Mixed documentation fixes and improvements.

New in v0.18.4
--------------

Changes:

* Support `[Variant "fischerandom"]` in PGNs for Cutechess compability.
  Thanks to Steve Maughan for reporting.

New in v0.18.3
--------------

Bugfixes:

* `chess.gaviota.NativeTablebases.get_dtm()` and `get_wdl()` were missing.

New in v0.18.2
--------------

Bugfixes:

* Fixed castling in atomic chess when there is a rank attack.
* The halfmove clock in Crazyhouse is no longer incremented unconditionally.
  `CrazyhouseBoard.is_zeroing(move)` now considers pawn moves and captures as
  zeroing. Added `Board.is_irreversible(move)` that can be used instead.
* Fixed an inconsistency where the `chess.pgn` tokenizer accepts long algebraic
  notation but `Board.parse_san()` did not.

Changes:

* Added more NAG constants in `chess.pgn`.

New in v0.18.1
--------------

Bugfixes:

* Crazyhouse drops were accepted as pseudo legal (and legal) even if the
  respective piece was not in the pocket.
* `CrazyhouseBoard.pop()` was failing to undo en passant moves.
* `CrazyhouseBoard.pop()` was always returning `None`.
* `Move.__copy__()` was failing to copy Crazyhouse drops.
* Fix ~ order (marker for promoted pieces) in FENs.
* Promoted pieces in Crazyhouse were not communicated with UCI engines.

Changes:

* `ThreeCheckBoard.uci_variant` changed from `threecheck` to `3check`.

New in v0.18.0
--------------

Bugfixes:

* Fixed `Board.parse_uci()` for crazyhouse drops. Thanks to Ryan Delaney.
* Fixed `AtomicBoard.is_insufficient_material()`.
* Fixed signature of `SuicideBoard.was_into_check()`.
* Explicitly close input and output streams when a `chess.uci.PopenProcess`
  terminates.
* The documentation of `Board.attackers()` was wrongly stating that en passant
  capturable pawns are considered attacked.

Changes:

* `chess.SquareSet` is no longer hashable (since it is mutable).
* Removed functions and constants deprecated in v0.17.0.
* Dropped `gmpy2` and `gmpy` as optional dependencies. They were no longer
  improving performance.
* Various tweaks and optimizations for 5% improvement in PGN parsing and perft
  speed. (Signature of `_is_safe` and `_ep_skewered` changed).
* Rewritten `chess.svg.board()` using `xml.etree`. No longer supports *pre* and
  *post*. Use an XML parser if you need to modify the SVG. Now only inserts
  actually used piece defintions.
* Untangled UCI process and engine instanciation, changing signatures of
  constructors and allowing arbitrary arguments to `subprocess.Popen`.
* Coding style and documentation improvements.

New features:

* `chess.svg.board()` now supports arrows. Thanks to @rheber for implementing
  this feature.
* Let `chess.uci.PopenEngine` consistently handle Ctrl+C across platforms
  and Python versions. `chess.uci.popen_engine()` now supports a `setpgrp`
  keyword argument to start the engine process in a new process group.
  Thanks to @dubiousjim.
* Added `board.king(color)` to find the (royal) king of a given side.
* SVGs now have `viewBox` and `chess.svg.board(size=None)` supports and
  defaults to `None` (i.e. scaling to the size of the container).

New in v0.17.0
--------------

Changes:

* Rewritten move generator, various performance tweaks, code simplications
  (500 lines removed) amounting to **doubled PGN parsing and perft speed**.
* Removed `board.generate_evasions()` and `board.generate_non_evasions()`.
* Removed `board.transpositions`. Transpositions are now counted on demand.
* `file_index()`, `rank_index()`, and `pop_count()` have been renamed to
  `square_file()`, `square_rank()` and `popcount()` respectively. Aliases will
  be removed in some future release.
* `STATUS_ILLEGAL_CHECK` has been renamed to `STATUS_RACE_CHECK`. The alias
  will be removed in a future release.
* Removed `DIAG_ATTACKS_NE`, `DIAG_ATTACKS_NW`, `RANK_ATTACKS` and
  `FILE_ATTACKS` as well as the corresponding masks. New attack tables
  `BB_DIAG_ATTACKS` (combined both diagonal tables), `BB_RANK_ATTACKS` and
  `BB_FILE_ATTACKS` are indexed by square instead of mask.
* `board.push()` no longer requires pseudo-legality.
* Documentation improvements.

Bugfixes:

* **Positions in variant end are now guaranteed to have no legal moves.**
  `board.is_variant_end()` has been added to test for special variant end
  conditions. Thanks to salvador-dali.
* `chess.svg`: Fixed a typo in the class names of black queens. Fixed fill
  color for black rooks and queens. Added SVG Tiny support. These combined
  changes fix display in a number of applications, including
  Jupyter Qt Console. Thanks to Alexander Meshcheryakov.
* `board.ep_square` was not consistently `None` instead of `0`.
* Detect invalid racing kings positions: `STATUS_RACE_OVER`,
  `STATUS_RACE_MATERIAL`.
* `SAN_REGEX`, `FEN_CASTLING_REGEX` and `TAG_REGEX` now try to match the
  entire string and no longer accept newlines.
* Fixed `Move.__hash__()` for drops.

New features:

* `board.remove_piece_at()` now returns the removed piece.
* Added `square_distance()` and `square_mirror()`.
* Added `msb()`, `lsb()`, `scan_reversed()` and `scan_forward()`.
* Added `BB_RAYS` and `BB_BETWEEN`.

New in v0.16.2
--------------

Changes:

* `board.move_stack` now contains the exact move objects added with
  `Board.push()` (instead of normalized copies for castling moves).
  This ensures they can be used with `Board.variation_san()` amongst others.
* `board.ep_square` is now `None` instead of `0` for no en passant square.
* `chess.svg`: Better vector graphics for knights. Thanks to ProgramFox.
* Documentation improvements.

New in v0.16.1
--------------

Bugfixes:

* Explosions in atomic chess were not destroying castling rights. Thanks to
  ProgramFOX for finding this issue.

New in v0.16.0
--------------

Bugfixes:

* `pin_mask()`, `pin()` and `is_pinned()` make more sense when already
  in check. Thanks to Ferdinand Mosca.

New features:

* **Variant support: Suicide, Giveaway, Atomic, King of the Hill, Racing Kings,
  Horde, Three-check, Crazyhouse.** `chess.Move` now supports drops.
* More fine grained dependencies. Use *pip install python-chess[uci,gaviota]* to
  install dependencies for the full feature set.
* Added `chess.STATUS_EMPTY` and `chess.STATUS_ILLEGAL_CHECK`.
* The `board.promoted` mask keeps track of promoted pieces.
* Optionally copy boards without the move stack: `board.copy(stack=False)`.
* `examples/bratko_kopec` now supports avoid move (am), variants and
  displays fractional scores immidiately. Thanks to Daniel Dugovic.
* `perft.py` rewritten with multi-threading support and moved to
  `examples/perft`.
* `chess.syzygy.dependencies()`, `chess.syzygy.all_dependencies()` to generate
  Syzygy tablebase dependencies.

Changes:

* **Endgame tablebase probing (Syzygy, Gaviota):** `probe_wdl()` **,**
  `probe_dtz()` **and** `probe_dtm()` **now raise** `KeyError` **or**
  `MissingTableError` **instead of returning** *None*. If you prefer getting
  `None` in case  of an error use `get_wdl()`, `get_dtz()` and `get_dtm()`.
* `chess.pgn.BaseVisitor.result()` returns `True` by default and is no longer
  used by `chess.pgn.read_game()` if no game was found.
* Non-fast-forward update of the Git repository to reduce size (old binary
  test assets removed).
* `board.pop()` now uses a boardstate stack to undo moves.
* `uci.engine.position()` will send the move history only until the latest
  zeroing move.
* Optimize `board.clean_castling_rights()` and micro-optimizations improving
  PGN parser performance by around 20%.
* Syzygy tables now directly use the endgame name as hash keys.
* Improve test performance (especially on Travis CI).
* Documentation updates and improvements.

New in v0.15.4
--------------

New features:

* Highlight last move and checks when rendering board SVGs.

New in v0.15.3
--------------

Bugfixes:

* `pgn.Game.errors` was not populated as documented. Thanks to Ryan Delaney
  for reporting.

New features:

* Added `pgn.GameNode.add_line()` and `pgn.GameNode.main_line()` which make
  it easier to work with lists of moves as variations.

New in v0.15.2
--------------

Bugfixes:

* Fix a bug where `shift_right()` and `shift_2_right()` were producing
  integers larger than 64bit when shifting squares off the board. This is
  very similar to the bug fixed in v0.15.1. Thanks to piccoloprogrammatore
  for reporting.

New in v0.15.1
--------------

Bugfixes:

* Fix a bug where `shift_up_right()` and `shift_up_left()` were producing
  integers larger than 64bit when shifting squares off the board.

New features:

* Replaced __html__ with experimental SVG rendering for IPython.

New in v0.15.0
--------------

Changes:

* `chess.uci.Score` **no longer has** `upperbound` **and** `lowerbound`
  **attributes**. Previously these were always *False*.

* Significant improvements of move generation speed, around **2.3x faster
  PGN parsing**. Removed the following internal attributes and methods of
  the `Board` class: `attacks_valid`, `attacks_to`, `attacks_from`,
  `_pinned()`, `attacks_valid_stack`, `attacks_from_stack`, `attacks_to_stack`,
  `generate_attacks()`.

* UCI: Do not send *isready* directly after *go*. Though allowed by the UCI
  protocol specification it is just not nescessary and many engines were having
  trouble with this.

* Polyglot: Use less memory for uniform random choices from big opening books
  (reservoir sampling).

* Documentation improvements.

Bugfixes:

* Allow underscores in PGN header tags. Found and fixed by Bajusz Tamás.

New features:

* Added `Board.chess960_pos()` to identify the Chess960 starting position
  number of positions.

* Added `chess.BB_BACKRANKS` and `chess.BB_PAWN_ATTACKS`.

New in v0.14.1
--------------

Bugfixes:

* Backport Bugfix for Syzygy DTZ related to en-passant.
  See official-stockfish/Stockfish@6e2ca97d93812b2.

Changes:

* Added optional argument *max_fds=128* to `chess.syzygy.open_tablebases()`.
  An LRU cache is used to keep at most *max_fds* files open. This allows using
  many tables without running out of file descriptors.
  Previously all tables were opened at once.

* Syzygy and Gaviota now store absolute tablebase paths, in case you change
  the working directory of the process.

* The default implementation of `chess.uci.InfoHandler.score()` will no longer
  store score bounds in `info["score"]`, only real scores.

* Added `Board.set_chess960_pos()`.

* Documentation improvements.

New in v0.14.0
--------------

Changes:

* `Board.attacker_mask()` **has been renamed to** `Board.attackers_mask()` for
  consistency.

* **The signature of** `Board.generate_legal_moves()` **and**
  `Board.generate_pseudo_legal_moves()` **has been changed.** Previously it
  was possible to select piece types for selective move generation:

  `Board.generate_legal_moves(castling=True, pawns=True, knights=True, bishops=True, rooks=True, queens=True, king=True)`

  Now it is possible to select arbitrary sets of origin and target squares.
  `to_mask` uses the corresponding rook squares for castling moves.

  `Board.generate_legal_moves(from_mask=BB_ALL, to_mask=BB)`

  To generate all knight and queen moves do:

  `board.generate_legal_moves(board.knights | board.queens)`

  To generate only castling moves use:

  `Board.generate_castling_moves(from_mask=BB_ALL, to_mask=BB_ALL)`

* Additional hardening has been added on top of the bugfix from v0.13.3.
  Diagonal skewers on the last double pawn move are now handled correctly,
  even though such positions can not be reached with a sequence of legal moves.

* `chess.syzygy` now uses the more efficient selective move generation.

New features:

* The following move generation methods have been added:
  `Board.generate_pseudo_legal_ep(from_mask=BB_ALL, to_mask=BB_ALL)`,
  `Board.generate_legal_ep(from_mask=BB_ALL, to_mask=BB_ALL)`,
  `Board.generate_pseudo_legal_captures(from_mask=BB_ALL, to_mask=BB_ALL)`,
  `Board.generate_legal_captures(from_mask=BB_ALL, to_mask=BB_ALL)`.


New in v0.13.3
--------------

**This is a bugfix release for a move generation bug.** Other than the bugfix
itself there are only minimal fully backwardscompatible changes.
You should update immediately.

Bugfixes:

* When capturing en passant, both the capturer and the captured pawn disappear
  from the fourth or fifth rank. If those pawns were covering a horizontal
  attack on the king, then capturing en passant should not have been legal.

  `Board.generate_legal_moves()` and `Board.is_into_check()` have been fixed.

  The same principle applies for diagonal skewers, but nothing has been done
  in this release: If the last double pawn move covers a diagonal attack, then
  the king would have already been in check.

  v0.14.0 adds additional hardening for all cases. It is recommended you
  upgrade to v0.14.0 as soon as you can deal with the
  non-backwards compatible changes.

Changes:

* `chess.uci` now uses `subprocess32` if applicable (and available).
  Additionally a lock is used to work around a race condition in Python 2, that
  can occur when spawning engines from multiple threads at the same time.

* Consistently handle tabs in UCI engine output.

New in v0.13.2
--------------

Changes:

* `chess.syzygy.open_tablebases()` now raises if the given directory
  does not exist.

* Allow visitors to handle invalid `FEN` tags in PGNs.

* Gaviota tablebase probing fails faster for piece counts > 5.

Minor new features:

* Added `chess.pgn.Game.from_board()`.

New in v0.13.1
--------------

Changes:

* Missing *SetUp* tags in PGNs are ignored.

* Incompatible comparisons on `chess.Piece`, `chess.Move`, `chess.Board`
  and `chess.SquareSet` now return *NotImplemented* instead of *False*.

Minor new features:

* Factored out basic board operations to `chess.BaseBoard`. This is inherited
  by `chess.Board` and extended with the usual move generation features.

* Added optional *claim_draw* argument to `chess.Base.is_game_over()`.

* Added `chess.Board.result(claim_draw=False)`.

* Allow `chess.Board.set_piece_at(square, None)`.

* Added `chess.SquareSet.from_square(square)`.

New in v0.13.0
--------------

* `chess.pgn.Game.export()` and `chess.pgn.GameNode.export()` have been
  removed and replaced with a new visitor concept.

* `chess.pgn.read_game()` no longer takes an `error_handler` argument. Errors
  are now logged. Use the new visitor concept to change this behaviour.

New in v0.12.5
--------------

Bugfixes:

* Context manager support for pure Python Gaviota probing code. Various
  documentation fixes for Gaviota probing. Thanks to Jürgen Précour for
  reporting.

* PGN variation start comments for variations on the very first move were
  assigned to the game. Thanks to Norbert Räcke for reporting.

New in v0.12.4
--------------

Bugfixes:

* Another en passant related Bugfix for pure Python Gaviota tablebase probing.

New features:

* Added `pgn.GameNode.is_end()`.

Changes:

* Big speedup for `pgn` module. Boards are cached less agressively. Board
  move stacks are copied faster.

* Added tox.ini to specify test suite and flake8 options.

New in v0.12.3
--------------

Bugfixes:

* Some invalid castling rights were silently ignored by `Board.set_fen()`. Now
  it is ensured information is stored for retrieval using `Board.status()`.

New in v0.12.2
--------------

Bugfixes:

* Some Gaviota probe results were incorrect for positions where black could
  capture en passant.

New in v0.12.1
--------------

Changes:

* Robust handling of invalid castling rights. You can also use the new
  method `Board.clean_castling_rights()` to get the subset of strictly valid
  castling rights.

New in v0.12.0
--------------

New features:

* Python 2.6 support. Patch by vdbergh.

* Pure Python Gaviota tablebase probing. Thanks to Jean-Noël Avila.

New in v0.11.1
--------------

Bugfixes:

* `syzygy.Tablebases.probe_dtz()` has was giving wrong results for some
  positions with possible en passant capturing. This was found and fixed
  upstream: https://github.com/official-stockfish/Stockfish/issues/394.

* Ignore extra spaces in UCI `info` lines, as for example sent by the
  Hakkapeliitta engine. Thanks to Jürgen Précour for reporting.

New in v0.11.0
--------------

Changes:

* **Chess960** support and the **representation of castling moves** has been
  changed.

  The constructor of board has a new `chess960` argument, defaulting to
  `False`: `Board(fen=STARTING_FEN, chess960=False)`. That property is
  available as `Board.chess960`.

  In Chess960 mode the behaviour is as in the previous release. Castling moves
  are represented as a king move to the corresponding rook square.

  In the default standard chess mode castling moves are represented with
  the standard UCI notation, e.g. `e1g1` for king-side castling.

  `Board.uci(move, chess960=None)` creates UCI representations for moves.
  Unlike `Move.uci()` it can convert them in the context of the current
  position.

  `Board.has_chess960_castling_rights()` has been added to test for castling
  rights that are impossible in standard chess.

  The modules `chess.polyglot`, `chess.pgn` and `chess.uci` will transparently
  handle both modes.

* In a previous release `Board.fen()` has been changed to only display an
  en passant square if a legal en passant move is indeed possible. This has
  now also been adapted for `Board.shredder_fen()` and `Board.epd()`.

New features:

* Get individual FEN components: `Board.board_fen()`, `Board.castling_xfen()`,
  `Board.castling_shredder_fen()`.

* Use `Board.has_legal_en_passant()` to test if a position has a legal
  en passant move.

* Make `repr(board.legal_moves)` human readable.

New in v0.10.1
--------------

Bugfixes:

* Fix use-after-free in Gaviota tablebase initialization.

New in v0.10.0
--------------

New dependencies:

* If you are using Python < 3.2 you have to install `futures` in order to
  use the `chess.uci` module.

Changes:

* There are big changes in the UCI module. Most notably in async mode multiple
  commands can be executed at the same time (e.g. `go infinite`  and then
  `stop` or `go ponder` and then `ponderhit`).

  `go infinite` and `go ponder` will now wait for a result, i.e. you may have
  to call `stop` or `ponderhit` from a different thread or run the commands
  asynchronously.

  `stop` and `ponderhit` no longer have a result.

* The values of the color constants `chess.WHITE` and `chess.BLACK` have been
  changed. Previously `WHITE` was `0`, `BLACK` was `1`. Now `WHITE` is `True`,
  `BLACK` is `False`. The recommended way to invert `color` is using
  `not color`.

* The pseudo piece type `chess.NONE` has been removed in favor of just using
  `None`.

* Changed the `Board(fen)` constructor. If the optional `fen` argument is not
  given behavior did not change. However if `None` is passed explicitly an
  empty board is created. Previously the starting position would have been
  set up.

* `Board.fen()` will now only show completely legal en passant squares.

* `Board.set_piece_at()` and `Board.remove_piece_at()` will now clear the
  move stack, because the old moves may not be valid in the changed position.

* `Board.parse_uci()` and `Board.push_uci()` will now accept null moves.

* Changed shebangs from `#!/usr/bin/python` to `#!/usr/bin/env python` for
  better virtualenv support.

* Removed unused game data files from repository.

Bugfixes:

* PGN: Prefer the game result from the game termination marker over `*` in the
  header. These should be identical in standard compliant PGNs. Thanks to
  Skyler Dawson for reporting this.

* Polyglot: `minimum_weight` for `find()`, `find_all()` and `choice()` was
  not respected.

* Polyglot: Negative indexing of opening books was raising `IndexError`.

* Various documentation fixes and improvements.

New features:

* Experimental probing of Gaviota tablebases via libgtb.

* New methods to construct boards:

  .. code:: python

      >>> chess.Board.empty()
      Board('8/8/8/8/8/8/8/8 w - - 0 1')

      >>> board, ops = chess.Board.from_epd("4k3/8/8/8/8/8/8/4K3 b - - fmvn 17; hmvc 13")
      >>> board
      Board('4k3/8/8/8/8/8/8/4K3 b - - 13 17')
      >>> ops
      {'fmvn': 17, 'hmvc': 13}

* Added `Board.copy()` and hooks to let the copy module to the right thing.

* Added `Board.has_castling_rights(color)`,
  `Board.has_kingside_castling_rights(color)` and
  `Board.has_queenside_castling_rights(color)`.

* Added `Board.clear_stack()`.

* Support common set operations on `chess.SquareSet()`.

New in v0.9.1
-------------

Bugfixes:

* UCI module could not handle castling ponder moves. Thanks to Marco Belli for
  reporting.
* The initial move number in PGNs was missing, if black was to move in the
  starting position. Thanks to Jürgen Précour for reporting.
* Detect more impossible en passant squares in `Board.status()`. There already
  was a requirement for a pawn on the fifth rank. Now the sixth and seventh
  rank must be empty, additionally. We do not do further retrograde analysis,
  because these are the only cases affecting move generation.

New in v0.8.3
-------------

Bugfixes:

* The initial move number in PGNs was missing, if black was to move in the
  starting position. Thanks to Jürgen Précour for reporting.
* Detect more impossible en passant squares in `Board.status()`. There already
  was a requirement for a pawn on the fifth rank. Now the sixth and seventh
  rank must be empty, additionally. We do not do further retrograde analysis,
  because these are the only cases affecting move generation.

New in v0.9.0
-------------

**This is a big update with quite a few breaking changes. Carefully review
the changes before upgrading. It's no problem if you can not update right now.
The 0.8.x branch still gets bugfixes.**

Incompatible changes:

* Removed castling right constants. Castling rights are now represented as a
  bitmask of the rook square. For example:

  .. code:: python

      >>> board = chess.Board()

      >>> # Standard castling rights.
      >>> board.castling_rights == chess.BB_A1 | chess.BB_H1 | chess.BB_A8 | chess.BB_H8
      True

      >>> # Check for the presence of a specific castling right.
      >>> can_white_castle_queenside = chess.BB_A1 & board.castling_rights

  Castling moves were previously encoded as the corresponding king movement in
  UCI, e.g. `e1f1` for white kingside castling. **Now castling moves are
  encoded as a move to the corresponding rook square** (`UCI_Chess960`-style),
  e.g. `e1a1`.

  You may use the new methods `Board.uci(move, chess960=True)`,
  `Board.parse_uci(uci)` and `Board.push_uci(uci)` to handle this
  transparently.

  The `uci` module takes care of converting moves when communicating with an
  engine that is not in `UCI_Chess960` mode.

* The `get_entries_for_position(board)` method of polyglot opening book readers
  has been changed to `find_all(board, minimum_weight=1)`. By default entries
  with weight 0 are excluded.

* The `Board.pieces` lookup list has been removed.

* In 0.8.1 the spelling of repetition (was repitition) was fixed.
  `can_claim_threefold_repetition()` and `is_fivefold_repetition()` are the
  affected method names. Aliases are now removed.

* `Board.set_epd()` will now interpret `bm`, `am` as a list of moves for the
  current position and `pv` as a variation (represented by a list of moves).
  Thanks to Jordan Bray for reporting this.

* Removed `uci.InfoHandler.pre_bestmove()` and
  `uci.InfoHandler.post_bestmove()`.

* `uci.InfoHandler().info["score"]` is now relative to multipv. Use

  .. code:: python

      >>> with info_handler as info:
      ...     if 1 in info["score"]:
      ...         cp = info["score"][1].cp

  where you were previously using

  .. code:: python

      >>> with info_handler as info:
      ...     if "score" in info:
      ...         cp = info["score"].cp

* Clear `uci.InfoHandler()` dictionary at the start of new searches
  (new `on_go()`), not at the end of searches.

* Renamed `PseudoLegalMoveGenerator.bitboard` and `LegalMoveGenerator.bitboard`
  to `PseudoLegalMoveGenerator.board` and `LegalMoveGenerator.board`,
  respectively.

* Scripts removed.

* Python 3.2 compability dropped. Use Python 3.3 or higher. Python 2.7 support
  is not affected.

New features:

* **Introduced Chess960 support.** `Board(fen)` and `Board.set_fen(fen)` now
  support X-FENs. Added `Board.shredder_fen()`.
  `Board.status(allow_chess960=True)` has an optional argument allowing to
  insist on standard chess castling rules.
  Added `Board.is_valid(allow_chess960=True)`.

* **Improved move generation using** `Shatranj-style direct lookup
  <http://arxiv.org/pdf/0704.3773.pdf>`_. **Removed rotated bitboards. Perft
  speed has been more than doubled.**

* Added `choice(board)` and `weighted_choice(board)` for polyglot opening book
  readers.

* Added `Board.attacks(square)` to determine attacks *from* a given square.
  There already was `Board.attackers(color, square)` returning attacks *to*
  a square.

* Added `Board.is_en_passant(move)`, `Board.is_capture(move)` and
  `Board.is_castling(move)`.

* Added `Board.pin(color, square)` and `Board.is_pinned(color, square)`.

* There is a new method `Board.pieces(piece_type, color)` to get a set of
  squares with the specified pieces.

* Do expensive Syzygy table initialization on demand.

* Allow promotions like `e8Q` (usually `e8=Q`) in `Board.parse_san()` and
  PGN files.

* Patch by Richard C. Gerkin: Added `Board.__unicode__()` just like
  `Board.__str__()` but with unicode pieces.
* Patch by Richard C. Gerkin: Added `Board.__html__()`.

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
  handling en passant correctly. Thanks to Norbert Naskov for reporting.

New in v0.4.1
-------------

* Fix `is_fivefold_repitition()`: The new fivefold repetition rule requires
  the repetitions to occur on *alternating consecutive* moves.

* Minor testing related improvements: Close PGN files, allow running via
  setuptools.

* Add recently introduced features to README.

New in v0.4.0
-------------

* Introduce `can_claim_draw()`, `can_claim_fifty_moves()` and
  `can_claim_threefold_repitition()`.

* Since the first of July 2014 a game is also over (even without claim by one
  of the players) if there were 75 moves without a pawn move or capture or
  a fivefold repetition. Let `is_game_over()` respect that. Introduce
  `is_seventyfive_moves()` and `is_fivefold_repitition()`. Other means of
  ending a game take precedence.

* Threefold repetition checking requires efficient hashing of positions
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
