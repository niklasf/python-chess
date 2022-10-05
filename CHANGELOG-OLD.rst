Old Changelog for python-chess up to 1.0.0
==========================================

New in v1.0.0 (24th Sep 2020)
-----------------------------

Changes:

* Now requires Python 3.7+.
* `chess.engine` will now cut off illegal principal variations at the first
  illegal move instead of discarding them entirely.
* `chess.engine.EngineProtocol` renamed to `chess.engine.Protocol`.
* `chess.engine.Option` is no longer a named tuple.
* Renamed `chess.gaviota` internals.
* Relaxed type annotations of `chess.pgn.GameNode.variation()` and related
  methods.
* Changed default colors of `chess.svg.Arrow` and
  `chess.pgn.GameNode.arrows()`. These can be overriden with the new
  `chess.svg.board(..., colors)` feature.
* Documentation improvements. Will now show type aliases like `chess.Square`
  instead of `int`.

Bugfixes:

* Fix insufficient material with same-color bishops on both sides.
* Clarify that `chess.Board.can_claim_draw()` and related methods refer to
  claims by the player to move. Three-fold repetition could already be claimed
  before making the final repeating move. `chess.Board.can_claim_fifty_moves()`
  now also allows a claim before the final repeating move. The previous
  behavior is `chess.Board.is_fifty_moves()`.
* Fix parsing of green arrows/circles in `chess.pgn.GameNode.arrows()`.
* Fix overloaded type signature of `chess.engine.Protocol.engine()`.

New features:

* Added `chess.parse_square()`, to be used instead of
  `chess.SQUARE_NAMES.index()`.
* Added `chess.Board.apply_mirror()`.
* Added `chess.svg.board(..., colors)`, to allow overriding the default theme.

New in v0.31.4 (9th Aug 2020)
-----------------------------

Bugfixes:

* Fix inconsistency where `board.is_legal()` was not accepting castling moves
  in Chess960 notation (when board is in standard mode), while all other
  methods did.
* Fix `chess.pgn.GameNode.set_clock()` with negative or floating point values.
* Avoid leading and trailing spaces in PGN comments when setting annotations.

New features:

* Finish typing and declare support for mypy.

New in v0.31.3 (18th Jul 2020)
------------------------------

Bugfixes:

* Custom castling rights assigned to `board.castling_rights` or castling rights
  left over after `Board.set_board_fen()` were not correctly cleaned after
  the first move.

Changes:

* Ignore up to one consecutive empty line between PGN headers.
* Added PGN Variant `From Position` as an alias for standard chess.
* `chess.pgn.FileExporter.result()` now returns the number of written
  characters.
* `chess.engine` now avoids sending 0 for search limits, which some engines
  misunderstand as no limit.
* `chess.engine` better handles null moves sent to the engine.
* `chess.engine` now gracefully handles `NULL` ponder moves and uppercase
  moves received from UCI engines, which is technically invalid.

New features:

* Added `chess.pgn.GameNode.{clock, set_clock}()` to read and write
  `[%clk ...]` **PGN annotations**.
* Added `chess.pgn.GameNode.{arrows, set_arrows}()` to read and write
  `[%csl ...]` and `[%cal ...]` PGN annotations.
* Added `chess.pgn.GameNode.{eval, set_eval}()` to read and write
  `[%eval ...]` PGN annotations.
* Added `SquareSet.ray(a, b)` and `SquareSet.between(a, b)`.

New in v0.31.2 (2nd Jun 2020)
-----------------------------

Bugfixes:

* Fix rejected/accepted in `chess.engine.XBoardProtocol`.
* Misc typing fixes.

Changes:

* Deprecated `chess.syzygy.is_table_name()`. Replaced with
  `chess.syzygy.is_tablename()` which has additional parameters and defaults to
  `one_king`.
* Take advantage of `int.bit_count()` coming in Python 3.10.

New in v0.31.1 (5th May 2020)
-----------------------------

Bugfixes:

* `RacingKingsBoard.is_variant_win()` no longer incorrectly returns `True`
  for drawn positions.
* Multiple moves for EPD opcodes *am* and *bm* are now sorted as required by
  the specification.
* Coordinates of SVG boards are now properly aligned, even when rendered as
  SVG Tiny.

Changes:

* SVG boards now have a background color for the coordinate margin, making
  coordinates readable on dark backgrounds.
* Added *[Variant "Illegal"]* as an alias for standard chess
  (used by Chessbase).

Features:

* Added `Board.find_move()`, useful for finding moves that match human input.

New in v0.31.0 (21st Apr 2020)
------------------------------

Changes:

* Replaced lookup table `chess.BB_BETWEEN[a][b]` with a function
  `chess.between(a, b)`. Improves initialization and runtime performance.
* `chess.pgn.BaseVisitor.result()` is now an abstract method, forcing
  subclasses to implement it.
* Removed helper attributes from `chess.engine.InfoDict`. Instead it is now
  a `TypedDict`.
* `chess.engine.PovScore` equality is now semantic instead of structural:
  Scores compare equal to the negative score from the opposite point of view.

Bugfixes:

* `chess.Board.is_irreversible()` now considers ceding legal en passant
  captures as irreversible. Also documented that false-negatives due to forced
  lines are by design.
* Fixed stack overflow in `chess.pgn` when exporting, visiting or getting the
  final board of a very long game.
* Clarified documentation regarding board validity.
* `chess.pgn.GameNode.__repr__()` no longer errors if the root node has invalid
  FEN or Variant headers.
* Carriage returns are no longer allowed in PGN header values, fixing
  reparsability.
* Fixed type error when XBoard name or egt features have a value that looks
  like an integer.
* `chess.engine` is now passing type checks with mypy.
* `chess.gaviota` is now passing type checks with mypy.

Features:

* Added `chess.Board.gives_check()`.
* `chess.engine.AnalysisResult.wait()` now returns `chess.engine.BestMove`.
* Added `empty_square` parameter for `chess.Board.unicode()` with better
  aligned default (⭘).

New in v0.30.1 (18th Jan 2020)
------------------------------

Changes:

* Positions with more than two checkers are considered invalid and
  `board.status()` returns `chess.STATUS_TOO_MANY_CHECKERS`.
* Pawns drops in Crazyhouse are considered zeroing and reset
  `board.halfmove_clock` when played.
* Now validating file sizes when opening Syzygy tables and Polyglot opening
  books.
* Explicitly warn about untrusted tablebase files and chess engines.

Bugfixes:

* Fix Racing Kings game end detection: Black cannot catch up if their own
  pieces block the goal. White would win on the next turn, so this did not
  impact the game theoretical outcome of the game.
* Fix bugs discovered by fuzzing the EPD parser: Fixed serialization of
  empty strings, reparsability of empty move lists, handling of non-finite
  floats, and handling of whitespace in opcodes.

Features:

* Added `board.checkers()`, returning a set of squares with the pieces giving
  check.

New in v0.30.0 (1st Jan 2020)
-----------------------------

Changes:

* **Dropped support for Python 3.5.**
* Remove explicit loop arguments in `chess.engine` module, following
  https://bugs.python.org/issue36373.

Bugfixes:

* `chess.engine.EngineProtocol.returncode` is no longer poisoned when
  `EngineProtocol.quit()` times out.
* `chess.engine.PlayResult.info` was not always of type
  `chess.engine.InfoDict`.

Features:

* The background thread spawned by `chess.engine.SimpleEngine` is now named
  for improved debuggability, revealing the PID of the engine process.
* `chess.engine.EventLoopPolicy` now supports `asyncio.PidfdChildWatcher`
  when running on Python 3.9+ and Linux 5.3+.
* Add `chess.Board.san_and_push()`.

New in v0.29.0 (2nd Dec 2019)
-----------------------------

Changes:

* `chess.variant.GiveawayBoard` **now starts with castling rights**.
  `chess.variant.AntichessBoard` is the same variant without castling rights.
* UCI info parser no longer reports errors when encountering unknown tokens.
* Performance improvements for repetition detection.
* Since Python 3.8: `chess.syzygy`/`chess.polyglot` use `madvise(MADV_RANDOM)`
  to prepare table/book files for random access.

Bugfixes:

* Fix syntax error in type annotation of `chess.engine.run_in_background()`.
* Fix castling rights when king is exploded in Atomic. Mitigated by the fact
  that the game is over and that it did not affect FEN.
* Fix insufficient material with underpromoted pieces in Crazyhouse. Mitigated
  by the fact that affected positions are unreachable in Crazyhouse.

Features:

* Support `wdl` in UCI info (usually activated with `UCI_ShowWDL`).

New in v0.28.3 (3rd Sep 2019)
-----------------------------

Bugfixes:

* Follow FICS rules in Atomic castling edge cases.
* Handle self-reported errors by XBoard engines "Error: ..." or
  "Illegal move: ...".

New in v0.28.2 (25th Jul 2019)
------------------------------

Bugfixes:

* Fixed exception propagation, when a UCI engine sends an invalid `bestmove`.
  Thanks @fsmosca.

Changes:

* `chess.Move.from_uci()` no longer accepts moves from and to the same square,
  for example `a1a1`. `0000` is now the only valid null move notation.

New in v0.28.1 (25th May 2019)
------------------------------

Bugfixes:

* The minimum Python version is 3.5.3 (instead of 3.5.0).
* Fix `board.is_irreversible()` when capturing a rook that had castling rights.

Changes:

* `is_en_passant()`, `is_capture()`, `is_zeroing()`, `is_irreversible()`,
  `is_castling()`, `is_kingside_castling()` and `is_queenside_castling()`
  now consistently return `False` for null moves.
* Added `chess.engine.InfoDict` class with typed shorthands for common keys.
* Support `[Variant "3-check"]` (from chess.com PGNs).

New in v0.28.0 (20th May 2019)
------------------------------

Changes:

* Dropped support for Python 3.4 (end of life reached).
* `chess.polyglot.Entry.move` **is now a property instead of a method**.
  The raw move is now always decoded in the context of the position (relevant
  for castling moves).
* `Piece`, `Move`, `BaseBoard` and `Board` comparisons no longer support
  duck typing.
* FENs sent to engines now always include potential en passant squares, even if
  no legal en passant capture exists.
* Circular SVG arrows now have a `circle` CSS class.
* Superfluous dashes (-) in EPDs are no longer treated as opcodes.
* Removed `GameCreator`, `HeaderCreator` and `BoardCreator` aliases for
  `{Game,Headers,Board}Builder`.

Bugfixes:

* Notation like `Kh1` is no longer accepted for castling moves.
* Remove stale files from wheels published on PyPI.
* Parsing Three-Check EPDs with moves was always failing.
* Some methods in `chess.variant` were returning bool-ish integers, when they
  should have returned `bool`.
* `chess.engine`: Fix line decoding when Windows line-endings arrive seperately
  in stdout buffer.
* `chess.engine`: Survive timeout in analysis.
* `chess.engine`: Survive unexpected `bestmove` sent by misbehaving UCI engines.

New features:

* **Experimental type signatures for almost all public APIs** (`typing`).
  Some modules do not yet internally pass typechecking.
* Added `Board.color_at(square)`.
* Added `chess.engine.AnalysisResult.get()` and `empty()`.
* `chess.engine`: The `UCI_AnalyseMode` option is still automatically managed,
  but can now be overwritten.
* `chess.engine.EngineProtocol` and constructors now optionally take
  an explicit `loop` argument.

New in v0.27.3 (21st Mar 2019)
------------------------------

Changes:

* `XBoardProtocol` will no longer raise an exception when the engine resigned.
  Instead it sets a new flag `PlayResult.resigned`. `resigned` and
  `draw_offered` are keyword-only arguments.
* Renamed `chess.pgn.{Game,Header,Board}Creator` to
  `{Game,Headers,Board}Builder`. Aliases kept in place.

Bugfixes:

* Make `XBoardProtocol` robust against engines that send a move after claiming
  a draw or resigning. Thanks @pascalgeo.
* `XBoardProtocol` no longer ignores `Hint:` sent by the engine.
* Fix handling of illegal moves in `XBoardProtocol`.
* Fix exception when engine is shut down while pondering.
* Fix unhandled internal exception and file descriptor leak when engine
  initialization fails.
* Fix `HordeBoard.status()` when black pieces are on the first rank.
  Thanks @Wisling.

New features:

* Added `chess.pgn.Game.builder()`, `chess.pgn.Headers.builder()` and
  `chess.pgn.GameNode.dangling_node()` to simplify subclassing `GameNode`.
* `EngineProtocol.communicate()` is now also available in the synchronous API.

New in v0.27.2 (16th Mar 2019)
------------------------------

Bugfixes:

* `chess.engine.XBoardProtocol.play()` was searching 100 times longer than
  intended when using `chess.engine.Limit.time`, and searching 100 times more
  nodes than intended when using `chess.engine.Limit.nodes`. Thanks @pascalgeo.

New in v0.27.1 (15th Mar 2019)
------------------------------

Bugfixes:

* `chess.engine.XBoardProtocol.play()` was raising `KeyError` when using time
  controls with increment or remaining moves. Thanks @pascalgeo.

New in v0.27.0 (14th Mar 2019)
------------------------------

This is the second **release candidate for python-chess 1.0**. If you see the
need for breaking changes, please speak up now!

Bugfixes:

* `EngineProtocol.analyse(*, multipv)` was not passing this argument to the
  engine and therefore only returned the first principal variation.
  Thanks @svangordon.
* `chess.svg.board(*, squares)`: The X symbol on selected squares is now more
  visible when it overlaps pieces.

Changes:

* **FEN/EPD parsing is now more relaxed**: Incomplete FENs and EPDs are
  completed with reasonable defaults (`w - - 0 1`). The EPD parser accepts
  fields with moves in UCI notation (for example the technically invalid
  `bm g1f3` instead of `bm Nf3`).
* The PGN parser now skips games with invalid FEN headers and variations after
  an illegal move (after handling the error as usual).

New features:

* Added `Board.is_repetition(count=3)`.
* Document that `chess.engine.EngineProtocol` is compatible with
  AsyncSSH 1.16.0.

New in v0.26.0 (19th Feb 2019)
------------------------------

This is the first **release candidate for python-chess 1.0**. If you see the
need for breaking changes, please speak up now!

Changes:

* `chess.engine` **is now stable and replaces**
  `chess.uci` **and** `chess.xboard`.
* Advanced: `EngineProtocol.initialize()` is now public for use with custom
  transports.
* Removed `__ne__` implementations (not required since Python 3).
* Assorted documentation and coding-style improvements.

New features:

* Check insufficient material for a specific side:
  `board.has_insufficient_material(color)`.
* Copy boards with limited stack depth: `board.copy(stack=depth)`.

Bugfixes:

* Properly handle delayed engine errors, for example unsupported options.

New in v0.25.1 (24th Jan 2019)
------------------------------

Bugfixes:

* `chess.engine` did not correctly handle Windows-style line endings.
  Thanks @Bstylestuff.

New in v0.25.0 (18th Jan 2019)
------------------------------

New features:

* This release introduces a new **experimental API for chess engine
  communication**, `chess.engine`, based on `asyncio`. It is intended to
  eventually replace `chess.uci` and `chess.xboard`.

Bugfixes:

* Fixed race condition in LRU-cache of open Syzygy tables. The LRU-cache is
  enabled by default (*max_fds*).
* Fix deprecation warning and unclosed file in setup.py.
  Thanks Mickaël Schoentgen.

Changes:

* `chess.pgn.read_game()` now ignores BOM at the start of the stream.
* Removed deprecated items.

New in v0.24.2 (5th Jan 2019)
-----------------------------

Bugfixes:

* `CrazyhouseBoard.root()` and `ThreeCheckBoard.root()` were not returning the
  correct pockets and number of remaining checks, respectively. Thanks @gbtami.
* `chess.pgn.skip_game()` now correctly skips PGN comments that contain
  line-breaks and PGN header tag notation.

Changes:

* Renamed `chess.pgn.GameModelCreator` to `GameCreator`. Alias kept in place
  and will be removed in a future release.
* Renamed `chess.engine` to `chess._engine`. Use re-exports from `chess.uci`
  or `chess.xboard`.
* Renamed `Board.stack` to `Board._stack`. Do not use this directly.
* Improved memory usage: `Board.legal_moves` and `Board.pseudo_legal_moves`
  no longer create reference cycles. PGN visitors can manage headers
  themselves.
* Removed previously deprecated items.

Features:

* Added `chess.pgn.BaseVisitor.visit_board()` and `chess.pgn.BoardCreator`.

New in v0.24.1, v0.23.11 (7th Dec 2018)
---------------------------------------

Bugfixes:

* Fix `chess.Board.set_epd()` and `chess.Board.from_epd()` with semicolon
  in string operand. Thanks @jdart1.
* `chess.pgn.GameNode.uci()` was always raising an exception.
  Also included in v0.24.0.

New in v0.24.0 (3rd Dec 2018)
-----------------------------

This release **drops support for Python 2**. The *0.23.x* branch will be
maintained for one more month.

Changes:

* **Require Python 3.4.** Thanks @hugovk.
* No longer using extra pip features:
  `pip install python-chess[engine,gaviota]` is now `pip install python-chess`.
* Various keyword arguments can now be used as **keyword arguments only**.
* `chess.pgn.GameNode.accept()` now
  **also visits the move leading to that node**.
* `chess.pgn.GameModelCreator` now requires that `begin_game()` be called.
* `chess.pgn.scan_headers()` and `chess.pgn.scan_offsets()` have been removed.
  Instead the new functions `chess.pgn.read_headers()` and
  `chess.pgn.skip_game()` can be used for a similar purpose.
* `chess.syzygy`: Invalid magic headers now raise `IOError`. Previously they
  were only checked in an assertion.
  `type(board).{tbw_magic,tbz_magic,pawnless_tbw_magic,pawnless_tbz_magic}`
  are now byte literals.
* `board.status()` constants (`STATUS_`) are now typed using `enum.IntFlag`.
  Values remain unchanged.
* `chess.svg.Arrow` is no longer a `namedtuple`.
* `chess.PIECE_SYMBOLS[0]` and `chess.PIECE_NAMES[0]` are now `None` instead
  of empty strings.
* Performance optimizations:

  * `chess.pgn.Game.from_board()`,
  * `chess.square_name()`
  * Replace `collections.deque` with lists almost everywhere.

* Renamed symbols (aliases will be removed in the next release):

  * `chess.BB_VOID` -> `BB_EMPTY`
  * `chess.bswap()` -> `flip_vertical()`
  * `chess.pgn.GameNode.main_line()` -> `mainline_moves()`
  * `chess.pgn.GameNode.is_main_line()` -> `is_mainline()`
  * `chess.variant.BB_HILL` -> `chess.BB_CENTER`
  * `chess.syzygy.open_tablebases()` -> `open_tablebase()`
  * `chess.syzygy.Tablebases` -> `Tablebase`
  * `chess.syzygy.Tablebase.open_directory()` -> `add_directory()`
  * `chess.gaviota.open_tablebases()` -> `open_tablebase()`
  * `chess.gaviota.open_tablebases_native()` -> `open_tablebase_native()`
  * `chess.gaviota.NativeTablebases` -> `NativeTablebase`
  * `chess.gaviota.PythonTablebases` -> `PythonTablebase`
  * `chess.gaviota.NativeTablebase.open_directory()` -> `add_directory()`
  * `chess.gaviota.PythonTablebase.open_directory()` -> `add_directory()`

Bugfixes:

* The PGN parser now gives the visitor a chance to handle unknown chess
  variants and continue parsing.
* `chess.pgn.GameNode.uci()` was always raising an exception.

New features:

* `chess.SquareSet` now extends `collections.abc.MutableSet` and can be
  initialized from iterables.
* `board.apply_transform(f)` and `board.transform(f)` can apply bitboard
  transformations to a position. Examples:
  `chess.flip_{vertical,horizontal,diagonal,anti_diagonal}`.
* `chess.pgn.GameNode.mainline()` iterates over nodes of the mainline.
  Can also be used with `reversed()`. Reversal is now also supported for
  `chess.pgn.GameNode.mainline_moves()`.
* `chess.svg.Arrow(tail, head, color="#888")` gained an optional *color*
  argument.
* `chess.pgn.BaseVisitor.parse_san(board, san)` is used by parsers and can
  be overwritten to deal with non-standard input formats.
* `chess.pgn`: Visitors can advise the parser to skip games or variations by
  returning the special value `chess.pgn.SKIP` from `begin_game()`,
  `end_headers()` or `begin_variation()`. This is only a hint.
  The corresponding `end_game()` or `end_variation()` will still be called.
* Added `chess.svg.MARGIN`.

New in v0.23.10 (31st Oct 2018)
-------------------------------

Bugfixes:

* `chess.SquareSet` now correctly handles negative masks. Thanks @hasnul.
* `chess.pgn` now accepts `[Variant "chess 960"]` (with the space).

New in v0.23.9 (4th Jul 2018)
-----------------------------

Changes:

* Updated `Board.is_fivefold_repetition()`. FIDE rules have changed and the
  repetition no longer needs to occur on consecutive alternating moves.
  Thanks @LegionMammal978.

New in v0.23.8 (1st Jul 2018)
-----------------------------

Bugfixes:

* `chess.syzygy`: Correctly initialize wide DTZ map for experimental 7 piece
  table KRBBPvKQ.

New in v0.23.7 (26th Jun 2018)
------------------------------

Bugfixes:

* Fixed `ThreeCheckBoard.mirror()` and `CrazyhouseBoard.mirror()`, which
  were previously resetting remaining checks and pockets respectively.
  Thanks @QueensGambit.

Changes:

* `Board.move_stack` is now guaranteed to be UCI compatible with respect to
  the representation of castling moves and `board.chess960`.
* Drop support for Python 3.3, which is long past end of life.
* `chess.uci`: The `position` command now manages `UCI_Chess960` and
  `UCI_Variant` automatically.
* `chess.uci`: The `position` command will now always send the entire history
  of moves from the root position.
* Various coding style fixes and improvements. Thanks @hugovk.

New features:

* Added `Board.root()`.

New in v0.23.6 (25th May 2018)
------------------------------

Bugfixes:

* Gaviota: Fix Python based Gaviota tablebase probing when there are multiple
  en passant captures. Thanks @bjoernholzhauer.
* Syzygy: Fix DTZ for some mate in 1 positions. Similarly to the fix from
  v0.23.1 this is mostly cosmetic.
* Syzygy: Fix DTZ off-by-one in some 6 piece antichess positions with moves
  that threaten to force a capture. This is mostly cosmetic.

Changes:

* Let `uci.Engine.position()` send history of at least 8 moves if available.
  Previously it sent only moves that were relevant for repetition detection.
  This is mostly useful for Lc0. Once performance issues are solved, a future
  version will always send the entire history. Thanks @SashaMN and @Mk-Chan.
* Various documentation fixes and improvements.

New features:

* Added `polyglot.MemoryMappedReader.get(board, default=None)`.

New in v0.23.5 (11th May 2018)
------------------------------

Bugfixes:

* Atomic chess: KNvKN is not insufficient material.
* Crazyhouse: Detect insufficient material. This can not happen unless the
  game was started with insufficient material.

Changes:

* Better error messages when parsing info from UCI engine fails.
* Better error message for `b.set_board_fen(b.fen())`.

New in v0.23.4 (29th Apr 2018)
------------------------------

New features:

* XBoard: Support pondering. Thanks Manik Charan.
* UCI: Support unofficial `info ebf`.

Bugfixes:

* Implement 16 bit DTZ mapping, which is required for some of the longest
  7 piece endgames.

New in v0.23.3 (21st Apr 2018)
------------------------------

New features:

* XBoard: Support `variant`. Thanks gbtami.

New in v0.23.2 (20th Apr 2018)
------------------------------

Bugfixes:

* XBoard: Handle multiple features and features with spaces. Thanks gbtami.
* XBoard: Ignore debug output prefixed with `#`. Thanks Dan Ravensloft and
  Manik Charan.

New in v0.23.1 (13th Apr 2018)
------------------------------

Bugfixes:

* Fix DTZ in case of mate in 1. This is a cosmetic fix, as the previous
  behavior was only off by one (which is allowed by design).

New in v0.23.0 (8th Apr 2018)
-----------------------------

New features:

* Experimental support for 7 piece Syzygy tablebases.

Changes:

* `chess.syzygy.filenames()` was renamed to `tablenames()` and
  gained an optional `piece_count=6` argument.
* `chess.syzygy.normalize_filename()` was renamed to `normalize_tablename()`.
* The undocumented constructors of `chess.syzygy.WdlTable` and
  `chess.syzygy.DtzTable` have been changed.

New in v0.22.2 (15th Mar 2018)
------------------------------

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

New in v0.22.1 (1st Jan 2018)
-----------------------------

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

New in v0.22.0 (20th Nov 2017)
------------------------------

Changes:

* `len(board.legal_moves)` **replaced by** `board.legal_moves.count()`.
  Previously `list(board.legal_moves)` was generating moves twice, resulting in
  a considerable slowdown. Thanks to Martin C. Doege for reporting.
* **Dropped Python 2.6 support.**
* XBoard: `offer_draw` renamed to `draw`.

New features:

* XBoard: Added `DrawHandler`.

New in v0.21.2 (17th Nov 2017)
------------------------------

Changes:

* `chess.svg` is now fully SVG Tiny 1.2 compatible. Removed
  `chess.svg.DEFAULT_STYLE` which would from now on be always empty.

New in v0.21.1 (14th Nov 2017)
------------------------------

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

New in v0.21.0 (13th Nov 2017)
------------------------------

Release yanked.

New in v0.20.1 (16th Oct 2017)
------------------------------

Bugfixes:

* Fix arrow positioning on SVG boards.
* Documentation fixes and improvements, making most doctests runnable.

New in v0.20.0 (13th Oct 2017)
------------------------------

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

New in v0.19.0 (27th Jul 2017)
------------------------------

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

New in v0.18.4 (27th Jul 2017)
------------------------------

Changes:

* Support `[Variant "fischerandom"]` in PGNs for Cutechess compatibility.
  Thanks to Steve Maughan for reporting.

New in v0.18.3 (28th Jun 2017)
------------------------------

Bugfixes:

* `chess.gaviota.NativeTablebases.get_dtm()` and `get_wdl()` were missing.

New in v0.18.2 (1st Jun 2017)
-----------------------------

Bugfixes:

* Fixed castling in atomic chess when there is a rank attack.
* The halfmove clock in Crazyhouse is no longer incremented unconditionally.
  `CrazyhouseBoard.is_zeroing(move)` now considers pawn moves and captures as
  zeroing. Added `Board.is_irreversible(move)` that can be used instead.
* Fixed an inconsistency where the `chess.pgn` tokenizer accepts long algebraic
  notation but `Board.parse_san()` did not.

Changes:

* Added more NAG constants in `chess.pgn`.

New in v0.18.1 (1st May 2017)
-----------------------------

Bugfixes:

* Crazyhouse drops were accepted as pseudo-legal (and legal) even if the
  respective piece was not in the pocket.
* `CrazyhouseBoard.pop()` was failing to undo en passant moves.
* `CrazyhouseBoard.pop()` was always returning `None`.
* `Move.__copy__()` was failing to copy Crazyhouse drops.
* Fix ~ order (marker for promoted pieces) in FENs.
* Promoted pieces in Crazyhouse were not communicated with UCI engines.

Changes:

* `ThreeCheckBoard.uci_variant` changed from `threecheck` to `3check`.

New in v0.18.0 (20th Apr 2017)
------------------------------

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

New in v0.17.0 (6th Mar 2017)
-----------------------------

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

New in v0.16.2 (15th Jan 2017)
------------------------------

Changes:

* `board.move_stack` now contains the exact move objects added with
  `Board.push()` (instead of normalized copies for castling moves).
  This ensures they can be used with `Board.variation_san()` amongst others.
* `board.ep_square` is now `None` instead of `0` for no en passant square.
* `chess.svg`: Better vector graphics for knights. Thanks to ProgramFox.
* Documentation improvements.

New in v0.16.1 (12th Dec 2016)
------------------------------

Bugfixes:

* Explosions in atomic chess were not destroying castling rights. Thanks to
  ProgramFOX for finding this issue.

New in v0.16.0 (11th Dec 2016)
------------------------------

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

New in v0.15.3 (21st Sep 2016)
------------------------------

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

New in v0.15.1 (12th Sep 2016)
------------------------------

Bugfixes:

* Fix a bug where `shift_up_right()` and `shift_up_left()` were producing
  integers larger than 64bit when shifting squares off the board.

New features:

* Replaced `__html__` with experimental SVG rendering for IPython.

New in v0.15.0 (11th Aug 2016)
------------------------------

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

New in v0.14.1 (7th Jun 2016)
-----------------------------

Bugfixes:

* Backport Bugfix for Syzygy DTZ related to en passant.
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

New in v0.14.0 (7th Apr 2016)
-----------------------------

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


New in v0.13.3 (7th Apr 2016)
-----------------------------

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

New in v0.13.2 (19th Jan 2016)
------------------------------

Changes:

* `chess.syzygy.open_tablebases()` now raises if the given directory
  does not exist.

* Allow visitors to handle invalid `FEN` tags in PGNs.

* Gaviota tablebase probing fails faster for piece counts > 5.

Minor new features:

* Added `chess.pgn.Game.from_board()`.

New in v0.13.1 (20th Dec 2015)
------------------------------

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

New in v0.13.0 (10th Nov 2015)
------------------------------

* `chess.pgn.Game.export()` and `chess.pgn.GameNode.export()` have been
  removed and replaced with a new visitor concept.

* `chess.pgn.read_game()` no longer takes an `error_handler` argument. Errors
  are now logged. Use the new visitor concept to change this behaviour.

New in v0.12.5 (18th Oct 2015)
------------------------------

Bugfixes:

* Context manager support for pure Python Gaviota probing code. Various
  documentation fixes for Gaviota probing. Thanks to Jürgen Précour for
  reporting.

* PGN variation start comments for variations on the very first move were
  assigned to the game. Thanks to Norbert Räcke for reporting.

New in v0.12.4 (13th Oct 2015)
------------------------------

Bugfixes:

* Another en passant related Bugfix for pure Python Gaviota tablebase probing.

New features:

* Added `pgn.GameNode.is_end()`.

Changes:

* Big speedup for `pgn` module. Boards are cached less agressively. Board
  move stacks are copied faster.

* Added tox.ini to specify test suite and flake8 options.

New in v0.12.3 (9th Oct 2015)
-----------------------------

Bugfixes:

* Some invalid castling rights were silently ignored by `Board.set_fen()`. Now
  it is ensured information is stored for retrieval using `Board.status()`.

New in v0.12.2 (7th Oct 2015)
-----------------------------

Bugfixes:

* Some Gaviota probe results were incorrect for positions where black could
  capture en passant.

New in v0.12.1 (7th Oct 2015)
-----------------------------

Changes:

* Robust handling of invalid castling rights. You can also use the new
  method `Board.clean_castling_rights()` to get the subset of strictly valid
  castling rights.

New in v0.12.0 (3rd Oct 2015)
-----------------------------

New features:

* Python 2.6 support. Patch by vdbergh.

* Pure Python Gaviota tablebase probing. Thanks to Jean-Noël Avila.

New in v0.11.1 (7th Sep 2015)
-----------------------------

Bugfixes:

* `syzygy.Tablebases.probe_dtz()` has was giving wrong results for some
  positions with possible en passant capturing. This was found and fixed
  upstream: https://github.com/official-stockfish/Stockfish/issues/394.

* Ignore extra spaces in UCI `info` lines, as for example sent by the
  Hakkapeliitta engine. Thanks to Jürgen Précour for reporting.

New in v0.11.0 (6th Sep 2015)
-----------------------------

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

New in v0.10.1 (30th Aug 2015)
------------------------------

Bugfixes:

* Fix use-after-free in Gaviota tablebase initialization.

New in v0.10.0 (28th Aug 2015)
------------------------------

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

New in v0.9.1 (15th Jul 2015)
-----------------------------

Bugfixes:

* UCI module could not handle castling ponder moves. Thanks to Marco Belli for
  reporting.
* The initial move number in PGNs was missing, if black was to move in the
  starting position. Thanks to Jürgen Précour for reporting.
* Detect more impossible en passant squares in `Board.status()`. There already
  was a requirement for a pawn on the fifth rank. Now the sixth and seventh
  rank must be empty, additionally. We do not do further retrograde analysis,
  because these are the only cases affecting move generation.

New in v0.8.3 (15th Jul 2015)
-----------------------------

Bugfixes:

* The initial move number in PGNs was missing, if black was to move in the
  starting position. Thanks to Jürgen Précour for reporting.
* Detect more impossible en passant squares in `Board.status()`. There already
  was a requirement for a pawn on the fifth rank. Now the sixth and seventh
  rank must be empty, additionally. We do not do further retrograde analysis,
  because these are the only cases affecting move generation.

New in v0.9.0 (24th Jun 2015)
-----------------------------

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

* Python 3.2 compatibility dropped. Use Python 3.3 or higher. Python 2.7
  support is not affected.

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

New in v0.8.2 (21st Jun 2015)
-----------------------------

Bugfixes:

* `pgn.Game.setup()` with the standard starting position was failing when the
  standard starting position was already set. Thanks to Jordan Bray for
  reporting this.

Optimizations:

* Remove `bswap()` from Syzygy decompression hot path. Directly read integers
  with the correct endianness.

New in v0.8.1 (29th May 2015)
-----------------------------

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

New in v0.8.0 (25th Mar 2015)
-----------------------------

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

New in v0.7.0 (21st Feb 2015)
-----------------------------

* **Implement UCI engine communication.**

* Patch by Matthew Lai: `Add caching for gameNode.board()`.

New in v0.6.0 (8th Nov 2014)
----------------------------

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

New in v0.5.0 (28th Oct 2014)
-----------------------------

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

New in v0.4.2 (11th Oct 2014)
-----------------------------

* Fix bug where `pawn_moves_from()` and consequently `is_legal()` weren't
  handling en passant correctly. Thanks to Norbert Naskov for reporting.

New in v0.4.1 (26th Aug 2014)
-----------------------------

* Fix `is_fivefold_repitition()`: The new fivefold repetition rule requires
  the repetitions to occur on *alternating consecutive* moves.

* Minor testing related improvements: Close PGN files, allow running via
  setuptools.

* Add recently introduced features to README.

New in v0.4.0 (19th Aug 2014)
-----------------------------

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

New in v0.3.1 (15th Aug 2014)
-----------------------------

* `Bitboard.status()` now correctly detects `STATUS_INVALID_EP_SQUARE`,
  instead of errors or false reports.

* Polyglot opening book reader now correctly handles knight underpromotions.

* Minor coding style fixes, including removal of unused imports.

New in v0.3.0 (13th Aug 2014)
-----------------------------

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
