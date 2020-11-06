Changelog for python-chess
==========================

New in v1.3.0
-------------

Changes:

* Introduced ``chess.pgn.ChildNode``, a subclass of ``chess.pgn.GameNode``
  for all nodes other than the root node, and converted ``chess.pgn.GameNode``
  to an abstract base class. This improves ergonomics in typed code.

  The change is backwards compatible if using only documented features.
  However, a notable undocumented feature is the ability to create dangling
  nodes. This is no longer possible. If you have been using this for
  subclassing, override ``GameNode.add_variation()`` instead of
  ``GameNode.dangling_node()``. It is now the only method that creates child
  nodes.

Bugfixes:

* Removed broken ``weakref`` based caching in ``chess.pgn.GameNode.board()``.

New features:

* Added ``chess.pgn.GameNode.next()``.

New in v1.2.2
-------------

Bugfixes:

* Fixed regression where releases were uploaded without the ``py.typed``
  marker.

New in v1.2.1
-------------

Changes:

* The primary location for the published package is now
  https://pypi.org/project/chess/. Thanks to
  `Kristian Glass <https://github.com/doismellburning>`_ for transferring the
  namespace.

  The old https://pypi.org/project/python-chess/ will remain an alias that
  installs the package from the new location as a dependency (as recommended by
  `PEP423 <https://www.python.org/dev/peps/pep-0423/#how-to-rename-a-project>`_).

New in v1.2.0
-------------

New features:

* Added ``chess.Board.ply()``.
* Added ``chess.pgn.GameNode.ply()`` and ``chess.pgn.GameNode.turn()``.
* Added ``chess.engine.PovWdl``, ``chess.engine.Wdl``, and conversions from
  scores: ``chess.engine.PovScore.wdl()``, ``chess.engine.Score.wdl()``.
* Added ``chess.engine.Score.score(*, mate_score: int) -> int`` overload.

Changes:

* The ``PovScore`` returned by ``chess.pgn.GameNode.eval()`` is now always
  relative to the side to move. The ambiguity around ``[%eval #0]`` has been
  resolved to ``Mate(-0)``. This makes sense, given that the authors of the
  specification probably had standard chess in mind (where a game-ending move
  is always a loss for the opponent). Previously, this would be parsed as
  ``None``.
* Typed ``chess.engine.InfoDict["wdl"]`` as the new ``chess.engine.PovWdl``,
  rather than ``Tuple[int, int, int]``. The new type is backwards compatible,
  but it is recommended to use its documented fields and methods instead.
* Removed ``chess.engine.PovScore.__str__()``. String representation falls back
  to ``__repr__``.
* The ``en_passant`` parameter of ``chess.Board.fen()`` and
  ``chess.Board.epd()`` is now typed as ``Literal["legal", "fen", "xfen"]``
  rather than ``str``.

New in v1.1.0
-------------

New features:

* Added ``chess.svg.board(..., orientation)``. This is a more idiomatic way to
  set the board orientation than ``flipped``.
* Added ``chess.svg.Arrow.pgn()`` and ``chess.svg.Arrow.from_pgn()``.

Changes:

* Further relaxed ``chess.Board.parse_san()``. Now accepts fully specified moves
  like ``e2e4``, even if that is not a pawn move, castling notation with zeros,
  null moves in UCI notation, and null moves in XBoard notation.

New in v1.0.1
-------------

Bugfixes:

* ``chess.svg``: Restored SVG Tiny compatibility by splitting colors like
  ``#rrggbbaa`` into a solid color and opacity.

New in v1.0.0
-------------

See ``CHANGELOG-OLD.rst`` for changes up to v1.0.0.
