# -*- coding: utf-8 -*-
#
# This file is part of the python-chess library.
# Copyright (C) 2016-2018 Niklas Fiekas <niklas.fiekas@backscattering.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# Piece vector graphics are copyright (C) Colin M.L. Burnett
# <https://en.wikipedia.org/wiki/User:Cburnett> and also licensed under the
# GNU General Public License.

from __future__ import division

import chess
import collections
import math

import xml.etree.ElementTree as ET


SQUARE_SIZE = 45

PIECES = {
    "b": """<g id="black-bishop" class="black bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zm6-4c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z" fill="#000" stroke-linecap="butt"/><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke="#fff" stroke-linejoin="miter"/></g>""",
    "k": """<g id="black-king" class="black king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6" stroke-linejoin="miter"/><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#000" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#000"/><path d="M20 8h5" stroke-linejoin="miter"/><path d="M32 29.5s8.5-4 6.03-9.65C34.15 14 25 18 22.5 24.5l.01 2.1-.01-2.1C20 18 9.906 14 6.997 19.85c-2.497 5.65 4.853 9 4.853 9M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0" stroke="#fff"/></g>""",
    "n": """<g id="black-knight" class="black knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#000000; stroke:#000000;"/><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#000000; stroke:#000000;"/><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#ececec; stroke:#ececec;"/><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#ececec; stroke:#ececec;"/><path d="M 24.55,10.4 L 24.1,11.85 L 24.6,12 C 27.75,13 30.25,14.49 32.5,18.75 C 34.75,23.01 35.75,29.06 35.25,39 L 35.2,39.5 L 37.45,39.5 L 37.5,39 C 38,28.94 36.62,22.15 34.25,17.66 C 31.88,13.17 28.46,11.02 25.06,10.5 L 24.55,10.4 z " style="fill:#ececec; stroke:none;"/></g>""",
    "p": """<g id="black-pawn" class="black pawn"><path d="M22 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38-1.95 1.12-3.28 3.21-3.28 5.62 0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" stroke="#000" stroke-width="1.5" stroke-linecap="round"/></g>""",
    "q": """<g id="black-queen" class="black queen" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#000" stroke="none"><circle cx="6" cy="12" r="2.75"/><circle cx="14" cy="9" r="2.75"/><circle cx="22.5" cy="8" r="2.75"/><circle cx="31" cy="9" r="2.75"/><circle cx="39" cy="12" r="2.75"/></g><path d="M9 26c8.5-1.5 21-1.5 27 0l2.5-12.5L31 25l-.3-14.1-5.2 13.6-3-14.5-3 14.5-5.2-13.6L14 25 6.5 13.5 9 26zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt"/><path d="M11 38.5a35 35 1 0 0 23 0" fill="none" stroke-linecap="butt"/><path d="M11 29a35 35 1 0 1 23 0M12.5 31.5h20M11.5 34.5a35 35 1 0 0 22 0M10.5 37.5a35 35 1 0 0 24 0" fill="none" stroke="#fff"/></g>""",
    "r": """<g id="black-rook" class="black rook" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12.5 32l1.5-2.5h17l1.5 2.5h-20zM12 36v-4h21v4H12z" stroke-linecap="butt"/><path d="M14 29.5v-13h17v13H14z" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M14 16.5L11 14h23l-3 2.5H14zM11 14V9h4v2h5V9h5v2h5V9h4v5H11z" stroke-linecap="butt"/><path d="M12 35.5h21M13 31.5h19M14 29.5h17M14 16.5h17M11 14h23" fill="none" stroke="#fff" stroke-width="1" stroke-linejoin="miter"/></g>""",
    "B": """<g id="white-bishop" class="white bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#fff" stroke-linecap="butt"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zM15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z"/></g><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke-linejoin="miter"/></g>""",
    "K": """<g id="white-king" class="white king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6M20 8h5" stroke-linejoin="miter"/><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#fff" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#fff"/><path d="M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0"/></g>""",
    "N": """<g id="white-knight" class="white knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#ffffff; stroke:#000000;"/><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#ffffff; stroke:#000000;"/><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#000000; stroke:#000000;"/><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#000000; stroke:#000000;"/></g>""",
    "P": """<g id="white-pawn" class="white pawn"><path d="M22 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38-1.95 1.12-3.28 3.21-3.28 5.62 0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#fff" stroke="#000" stroke-width="1.5" stroke-linecap="round"/></g>""",
    "Q": """<g id="white-queen" class="white queen" fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 12a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM24.5 7.5a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM41 12a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM16 8.5a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM33 9a2 2 0 1 1-4 0 2 2 0 1 1 4 0z"/><path d="M9 26c8.5-1.5 21-1.5 27 0l2-12-7 11V11l-5.5 13.5-3-15-3 15-5.5-14V25L7 14l2 12zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt"/><path d="M11.5 30c3.5-1 18.5-1 22 0M12 33.5c6-1 15-1 21 0" fill="none"/></g>""",
    "R": """<g id="white-rook" class="white rook" fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12 36v-4h21v4H12zM11 14V9h4v2h5V9h5v2h5V9h4v5" stroke-linecap="butt"/><path d="M34 14l-3 3H14l-3-3"/><path d="M31 17v12.5H14V17" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M31 29.5l1.5 2.5h-20l1.5-2.5"/><path d="M11 14h23" fill="none" stroke-linejoin="miter"/></g>"""
}

XX = """<g id="xx" style="fill:none; stroke:#000000; stroke-width:2; stroke-opacity:1; stroke-linecap:round;stroke-linejoin:round; stroke-miterlimit:4; stroke-dasharray:none;"><path d="M 30,30 L 15,15" /><path d="M 30,15 L 15,30" /></g>"""

CHECK_GRADIENT = """<radialGradient id="check_gradient"><stop offset="0%" stop-color="#ff0000" stop-opacity="1.0" /><stop offset="50%" stop-color="#e70000" stop-opacity="1.0" /><stop offset="100%" stop-color="#9e0000" stop-opacity="0.0" /></radialGradient>"""

DEFAULT_COLORS = {
    "square light": "#ffce9e",
    "square dark": "#d18b47",
    "square dark lastmove": "#aaa23b",
    "square light lastmove": "#cdd16a",
}


class Arrow(collections.namedtuple("Arrow", "tail head")):
    """Details of an arrow to be drawn."""

    __slots__ = ()


def _svg(viewbox, size):
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "viewBox": "0 0 %d %d" % (viewbox, viewbox),
    })

    if size is not None:
        svg.set("width", str(size))
        svg.set("height", str(size))

    return svg


def _text(content, x, y, width, height):
    t = ET.Element("text", {
        "x": str(x + width // 2),
        "y": str(y + height // 2),
        "font-size": str(max(1, int(min(width, height) * 0.7))),
        "text-anchor": "middle",
        "alignment-baseline": "middle",
    })
    t.text = content
    return t


def piece(piece, size=None):
    """
    Renders the given :class:`chess.Piece` as an SVG image.

    >>> import chess
    >>> import chess.svg
    >>>
    >>> from IPython.display import SVG
    >>>
    >>> SVG(chess.svg.piece(chess.Piece.from_symbol("R")))  # doctest: +SKIP

    .. image:: ../docs/wR.svg
    """
    svg = _svg(SQUARE_SIZE, size)
    svg.append(ET.fromstring(PIECES[piece.symbol()]))
    return ET.tostring(svg).decode("utf-8")


def board(board=None, squares=None, flipped=False, coordinates=True, lastmove=None, check=None, arrows=(), size=None, style=None):
    """
    Renders a board with pieces and/or selected squares as an SVG image.

    :param board: A :class:`chess.BaseBoard` for a chessboard with pieces or
        ``None`` (the default) for a chessboard without pieces.
    :param squares: A :class:`chess.SquareSet` with selected squares.
    :param flipped: Pass ``True`` to flip the board.
    :param coordinates: Pass ``False`` to disable coordinates in the margin.
    :param lastmove: A :class:`chess.Move` to be highlighted.
    :param check: A square to be marked as check.
    :param arrows: A list of :class:`~chess.svg.Arrow` objects like
        ``[chess.svg.Arrow(chess.E2, chess.E4)]`` or a list of tuples like
        ``[(chess.E2, chess.E4)]``. An arrow from a square pointing to the same
        square is drawn as a circle, like ``[(chess.E2, chess.E2)]``.
    :param size: The size of the image in pixels (e.g., ``400`` for a 400 by
        400 board) or ``None`` (the default) for no size limit.
    :param style: A CSS stylesheet to include in the SVG image.

    >>> import chess
    >>> import chess.svg
    >>>
    >>> from IPython.display import SVG
    >>>
    >>> board = chess.Board("8/8/8/8/4N3/8/8/8 w - - 0 1")
    >>> squares = board.attacks(chess.E4)
    >>> SVG(chess.svg.board(board=board, squares=squares))  # doctest: +SKIP

    .. image:: ../docs/Ne4.svg
    """
    margin = 20 if coordinates else 0
    svg = _svg(8 * SQUARE_SIZE + 2 * margin, size)

    if style:
        ET.SubElement(svg, "style").text = style

    defs = ET.SubElement(svg, "defs")
    if board:
        for color in chess.COLORS:
            for piece_type in chess.PIECE_TYPES:
                if board.pieces_mask(piece_type, color):
                    defs.append(ET.fromstring(PIECES[chess.Piece(piece_type, color).symbol()]))
    if squares:
        defs.append(ET.fromstring(XX))
    if check is not None:
        defs.append(ET.fromstring(CHECK_GRADIENT))

    for square, bb in enumerate(chess.BB_SQUARES):
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)

        x = (file_index if not flipped else 7 - file_index) * SQUARE_SIZE + margin
        y = (7 - rank_index if not flipped else rank_index) * SQUARE_SIZE + margin

        cls = ["square", "light" if chess.BB_LIGHT_SQUARES & bb else "dark"]
        if lastmove and square in [lastmove.from_square, lastmove.to_square]:
            cls.append("lastmove")
        fill_color = DEFAULT_COLORS[" ".join(cls)]
        cls.append(chess.SQUARE_NAMES[square])

        ET.SubElement(svg, "rect", {
            "x": str(x),
            "y": str(y),
            "width": str(SQUARE_SIZE),
            "height": str(SQUARE_SIZE),
            "class": " ".join(cls),
            "stroke": "none",
            "fill": fill_color,
        })

        if square == check:
            ET.SubElement(svg, "rect", {
                "x": str(x),
                "y": str(y),
                "width": str(SQUARE_SIZE),
                "height": str(SQUARE_SIZE),
                "class": "check",
                "fill": "url(#check_gradient)",
            })

        # Render pieces.
        if board is not None:
            piece = board.piece_at(square)
            if piece:
                ET.SubElement(svg, "use", {
                    "xlink:href": "#%s-%s" % (chess.COLOR_NAMES[piece.color], chess.PIECE_NAMES[piece.piece_type]),
                    "transform": "translate(%d, %d)" % (x, y),
                })

        # Render selected squares.
        if squares is not None and squares & bb:
            ET.SubElement(svg, "use", {
                "xlink:href": "#xx",
                "x": str(x),
                "y": str(y),
            })

    if coordinates:
        for file_index, file_name in enumerate(chess.FILE_NAMES):
            x = (file_index if not flipped else 7 - file_index) * SQUARE_SIZE + margin
            svg.append(_text(file_name, x, 0, SQUARE_SIZE, margin))
            svg.append(_text(file_name, x, margin + 8 * SQUARE_SIZE, SQUARE_SIZE, margin))
        for rank_index, rank_name in enumerate(chess.RANK_NAMES):
            y = (7 - rank_index if not flipped else rank_index) * SQUARE_SIZE + margin
            svg.append(_text(rank_name, 0, y, margin, SQUARE_SIZE))
            svg.append(_text(rank_name, margin + 8 * SQUARE_SIZE, y, margin, SQUARE_SIZE))

    for tail, head in arrows:
        tail_file = chess.square_file(tail)
        tail_rank = chess.square_rank(tail)
        head_file = chess.square_file(head)
        head_rank = chess.square_rank(head)

        xtail = margin + (tail_file + 0.5 if not flipped else 7.5 - tail_file) * SQUARE_SIZE
        ytail = margin + (7.5 - tail_rank if not flipped else tail_rank + 0.5) * SQUARE_SIZE
        xhead = margin + (head_file + 0.5 if not flipped else 7.5 - head_file) * SQUARE_SIZE
        yhead = margin + (7.5 - head_rank if not flipped else head_rank + 0.5) * SQUARE_SIZE

        if (head_file, head_rank) == (tail_file, tail_rank):
            ET.SubElement(svg, "circle", {
                "cx": str(xhead),
                "cy": str(yhead),
                "r": str(SQUARE_SIZE * 0.9 / 2),
                "stroke-width": str(SQUARE_SIZE * 0.1),
                "stroke": "#888",
                "fill": "none",
                "opacity": "0.5",
            })
        else:
            marker_size = 0.75 * SQUARE_SIZE
            marker_margin = 0.1 * SQUARE_SIZE

            dx, dy = xhead - xtail, yhead - ytail
            hypot = math.hypot(dx, dy)

            shaft_x = xhead - dx * (marker_size + marker_margin) / hypot
            shaft_y = yhead - dy * (marker_size + marker_margin) / hypot

            xtip = xhead - dx * marker_margin / hypot
            ytip = yhead - dy * marker_margin / hypot

            ET.SubElement(svg, "line", {
                "x1": str(xtail),
                "y1": str(ytail),
                "x2": str(shaft_x),
                "y2": str(shaft_y),
                "stroke": "#888",
                "stroke-width": str(SQUARE_SIZE * 0.2),
                "opacity": "0.5",
                "stroke-linecap": "butt",
                "class": "arrow",
            })

            marker = []
            marker.append((xtip, ytip))
            marker.append((shaft_x + dy * 0.5 * marker_size / hypot,
                           shaft_y - dx * 0.5 * marker_size / hypot))
            marker.append((shaft_x - dy * 0.5 * marker_size / hypot,
                           shaft_y + dx * 0.5 * marker_size / hypot))

            ET.SubElement(svg, "polygon", {
                "points": " ".join(str(x) + "," + str(y) for x, y in marker),
                "fill": "#888",
                "opacity": "0.5",
                "class": "arrow",
            })

    return ET.tostring(svg).decode("utf-8")
