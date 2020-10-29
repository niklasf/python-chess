# This file is part of the python-chess library.
# Copyright (C) 2016-2020 Niklas Fiekas <niklas.fiekas@backscattering.de>
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

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import chess

from typing import Dict, Iterable, Optional, Tuple, Union
from chess import Color, IntoSquareSet, Square


SQUARE_SIZE = 45
MARGIN = 20

PIECES = {
    "b": """<g id="black-bishop" class="black bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zm6-4c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z" fill="#000" stroke-linecap="butt"/><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke="#fff" stroke-linejoin="miter"/></g>""",  # noqa: E501
    "k": """<g id="black-king" class="black king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6" stroke-linejoin="miter"/><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#000" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#000"/><path d="M20 8h5" stroke-linejoin="miter"/><path d="M32 29.5s8.5-4 6.03-9.65C34.15 14 25 18 22.5 24.5l.01 2.1-.01-2.1C20 18 9.906 14 6.997 19.85c-2.497 5.65 4.853 9 4.853 9M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0" stroke="#fff"/></g>""",  # noqa: E501
    "n": """<g id="black-knight" class="black knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#000000; stroke:#000000;"/><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#000000; stroke:#000000;"/><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#ececec; stroke:#ececec;"/><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#ececec; stroke:#ececec;"/><path d="M 24.55,10.4 L 24.1,11.85 L 24.6,12 C 27.75,13 30.25,14.49 32.5,18.75 C 34.75,23.01 35.75,29.06 35.25,39 L 35.2,39.5 L 37.45,39.5 L 37.5,39 C 38,28.94 36.62,22.15 34.25,17.66 C 31.88,13.17 28.46,11.02 25.06,10.5 L 24.55,10.4 z " style="fill:#ececec; stroke:none;"/></g>""",  # noqa: E501
    "p": """<g id="black-pawn" class="black pawn"><path d="M22 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38-1.95 1.12-3.28 3.21-3.28 5.62 0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" stroke="#000" stroke-width="1.5" stroke-linecap="round"/></g>""",  # noqa: E501
    "q": """<g id="black-queen" class="black queen" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#000" stroke="none"><circle cx="6" cy="12" r="2.75"/><circle cx="14" cy="9" r="2.75"/><circle cx="22.5" cy="8" r="2.75"/><circle cx="31" cy="9" r="2.75"/><circle cx="39" cy="12" r="2.75"/></g><path d="M9 26c8.5-1.5 21-1.5 27 0l2.5-12.5L31 25l-.3-14.1-5.2 13.6-3-14.5-3 14.5-5.2-13.6L14 25 6.5 13.5 9 26zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt"/><path d="M11 38.5a35 35 1 0 0 23 0" fill="none" stroke-linecap="butt"/><path d="M11 29a35 35 1 0 1 23 0M12.5 31.5h20M11.5 34.5a35 35 1 0 0 22 0M10.5 37.5a35 35 1 0 0 24 0" fill="none" stroke="#fff"/></g>""",  # noqa: E501
    "r": """<g id="black-rook" class="black rook" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12.5 32l1.5-2.5h17l1.5 2.5h-20zM12 36v-4h21v4H12z" stroke-linecap="butt"/><path d="M14 29.5v-13h17v13H14z" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M14 16.5L11 14h23l-3 2.5H14zM11 14V9h4v2h5V9h5v2h5V9h4v5H11z" stroke-linecap="butt"/><path d="M12 35.5h21M13 31.5h19M14 29.5h17M14 16.5h17M11 14h23" fill="none" stroke="#fff" stroke-width="1" stroke-linejoin="miter"/></g>""",  # noqa: E501
    "B": """<g id="white-bishop" class="white bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#fff" stroke-linecap="butt"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zM15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z"/></g><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke-linejoin="miter"/></g>""",  # noqa: E501
    "K": """<g id="white-king" class="white king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6M20 8h5" stroke-linejoin="miter"/><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#fff" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#fff"/><path d="M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0"/></g>""",  # noqa: E501
    "N": """<g id="white-knight" class="white knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#ffffff; stroke:#000000;"/><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#ffffff; stroke:#000000;"/><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#000000; stroke:#000000;"/><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#000000; stroke:#000000;"/></g>""",  # noqa: E501
    "P": """<g id="white-pawn" class="white pawn"><path d="M22 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38-1.95 1.12-3.28 3.21-3.28 5.62 0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#fff" stroke="#000" stroke-width="1.5" stroke-linecap="round"/></g>""",  # noqa: E501
    "Q": """<g id="white-queen" class="white queen" fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 12a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM24.5 7.5a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM41 12a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM16 8.5a2 2 0 1 1-4 0 2 2 0 1 1 4 0zM33 9a2 2 0 1 1-4 0 2 2 0 1 1 4 0z"/><path d="M9 26c8.5-1.5 21-1.5 27 0l2-12-7 11V11l-5.5 13.5-3-15-3 15-5.5-14V25L7 14l2 12zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt"/><path d="M11.5 30c3.5-1 18.5-1 22 0M12 33.5c6-1 15-1 21 0" fill="none"/></g>""",  # noqa: E501
    "R": """<g id="white-rook" class="white rook" fill="#fff" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12 36v-4h21v4H12zM11 14V9h4v2h5V9h5v2h5V9h4v5" stroke-linecap="butt"/><path d="M34 14l-3 3H14l-3-3"/><path d="M31 17v12.5H14V17" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M31 29.5l1.5 2.5h-20l1.5-2.5"/><path d="M11 14h23" fill="none" stroke-linejoin="miter"/></g>""",  # noqa: E501
}

COORDS = {
    "1": """<path d="M6.754 26.996h2.578v-8.898l-2.805.562v-1.437l2.79-.563h1.578v10.336h2.578v1.328h-6.72z"/>""",  # noqa: E501
    "2": """<path d="M8.195 26.996h5.508v1.328H6.297v-1.328q.898-.93 2.445-2.492 1.555-1.57 1.953-2.024.758-.851 1.055-1.437.305-.594.305-1.164 0-.93-.657-1.516-.648-.586-1.695-.586-.742 0-1.57.258-.82.258-1.758.781v-1.593q.953-.383 1.781-.578.828-.196 1.516-.196 1.812 0 2.89.906 1.079.907 1.079 2.422 0 .72-.274 1.368-.265.64-.976 1.515-.196.227-1.243 1.313-1.046 1.078-2.953 3.023z"/>""",  # noqa: E501
    "3": """<path d="M11.434 22.035q1.132.242 1.765 1.008.64.766.64 1.89 0 1.727-1.187 2.672-1.187.946-3.375.946-.734 0-1.515-.149-.774-.14-1.602-.43V26.45q.656.383 1.438.578.78.196 1.632.196 1.485 0 2.258-.586.782-.586.782-1.703 0-1.032-.727-1.61-.719-.586-2.008-.586h-1.36v-1.297h1.423q1.164 0 1.78-.46.618-.47.618-1.344 0-.899-.64-1.375-.633-.485-1.82-.485-.65 0-1.391.141-.743.14-1.633.437V16.95q.898-.25 1.68-.375.788-.125 1.484-.125 1.797 0 2.844.82 1.046.813 1.046 2.204 0 .968-.554 1.64-.555.664-1.578.922z"/>""",  # noqa: E501
    "4": """<path d="M11.016 18.035L7.03 24.262h3.985zm-.414-1.375h1.984v7.602h1.664v1.312h-1.664v2.75h-1.57v-2.75H5.75v-1.523z"/>""",  # noqa: E501
    "5": """<path d="M6.719 16.66h6.195v1.328h-4.75v2.86q.344-.118.688-.172.343-.063.687-.063 1.953 0 3.094 1.07 1.14 1.07 1.14 2.899 0 1.883-1.171 2.93-1.172 1.039-3.305 1.039-.735 0-1.5-.125-.758-.125-1.57-.375v-1.586q.703.383 1.453.57.75.188 1.586.188 1.351 0 2.14-.711.79-.711.79-1.93 0-1.219-.79-1.93-.789-.71-2.14-.71-.633 0-1.266.14-.625.14-1.281.438z"/>""",  # noqa: E501
    "6": """<path d="M10.137 21.863q-1.063 0-1.688.727-.617.726-.617 1.992 0 1.258.617 1.992.625.727 1.688.727 1.062 0 1.68-.727.624-.734.624-1.992 0-1.266-.625-1.992-.617-.727-1.68-.727zm3.133-4.945v1.437q-.594-.28-1.204-.43-.601-.148-1.195-.148-1.562 0-2.39 1.055-.82 1.055-.938 3.188.46-.68 1.156-1.04.696-.367 1.531-.367 1.758 0 2.774 1.07 1.023 1.063 1.023 2.899 0 1.797-1.062 2.883-1.063 1.086-2.828 1.086-2.024 0-3.094-1.547-1.07-1.555-1.07-4.5 0-2.766 1.312-4.406 1.313-1.649 3.524-1.649.593 0 1.195.117.61.118 1.266.352z"/>""",  # noqa: E501
    "7": """<path d="M6.25 16.66h7.5v.672L9.516 28.324H7.867l3.985-10.336H6.25z"/>""",  # noqa: E501
    "8": """<path d="M10 22.785q-1.125 0-1.773.602-.641.601-.641 1.656t.64 1.656q.649.602 1.774.602t1.773-.602q.649-.61.649-1.656 0-1.055-.649-1.656-.64-.602-1.773-.602zm-1.578-.672q-1.016-.25-1.586-.945-.563-.695-.563-1.695 0-1.399.993-2.211 1-.813 2.734-.813 1.742 0 2.734.813.993.812.993 2.21 0 1-.57 1.696-.563.695-1.571.945 1.14.266 1.773 1.04.641.773.641 1.89 0 1.695-1.04 2.602-1.03.906-2.96.906t-2.969-.906Q6 26.738 6 25.043q0-1.117.64-1.89.641-.774 1.782-1.04zm-.578-2.492q0 .906.562 1.414.57.508 1.594.508 1.016 0 1.586-.508.578-.508.578-1.414 0-.906-.578-1.414-.57-.508-1.586-.508-1.023 0-1.594.508-.562.508-.562 1.414z"/>""",  # noqa: E501
    "a": """<path d="M23.328 10.016q-1.742 0-2.414.398-.672.398-.672 1.36 0 .765.5 1.218.508.445 1.375.445 1.196 0 1.914-.843.727-.852.727-2.258v-.32zm2.867-.594v4.992h-1.437v-1.328q-.492.797-1.227 1.18-.734.375-1.797.375-1.343 0-2.14-.75-.79-.758-.79-2.024 0-1.476.985-2.226.992-.75 2.953-.75h2.016V8.75q0-.992-.656-1.531-.649-.547-1.829-.547-.75 0-1.46.18-.711.18-1.368.539V6.062q.79-.304 1.532-.453.742-.156 1.445-.156 1.898 0 2.836.984.937.985.937 2.985z"/>""",  # noqa: E501
    "b": """<path d="M24.922 10.047q0-1.586-.656-2.485-.649-.906-1.79-.906-1.14 0-1.796.906-.649.899-.649 2.485 0 1.586.649 2.492.656.898 1.797.898 1.14 0 1.789-.898.656-.906.656-2.492zm-4.89-3.055q.452-.781 1.14-1.156.695-.383 1.656-.383 1.594 0 2.586 1.266 1 1.265 1 3.328 0 2.062-1 3.328-.992 1.266-2.586 1.266-.96 0-1.656-.375-.688-.383-1.14-1.164v1.312h-1.446V2.258h1.445z"/>""",  # noqa: E501
    "c": """<path d="M25.96 6v1.344q-.608-.336-1.226-.5-.609-.172-1.234-.172-1.398 0-2.172.89-.773.883-.773 2.485 0 1.601.773 2.492.774.883 2.172.883.625 0 1.234-.164.618-.172 1.227-.508v1.328q-.602.281-1.25.422-.64.14-1.367.14-1.977 0-3.14-1.242-1.165-1.242-1.165-3.351 0-2.14 1.172-3.367 1.18-1.227 3.227-1.227.664 0 1.296.14.633.134 1.227.407z"/>""",  # noqa: E501
    "d": """<path d="M24.973 6.992V2.258h1.437v12.156h-1.437v-1.312q-.453.78-1.149 1.164-.687.375-1.656.375-1.586 0-2.586-1.266-.992-1.266-.992-3.328 0-2.063.992-3.328 1-1.266 2.586-1.266.969 0 1.656.383.696.375 1.149 1.156zm-4.899 3.055q0 1.586.649 2.492.656.898 1.797.898 1.14 0 1.796-.898.657-.906.657-2.492 0-1.586-.657-2.485-.656-.906-1.796-.906-1.141 0-1.797.906-.649.899-.649 2.485z"/>""",  # noqa: E501
    "e": """<path d="M26.555 9.68v.703h-6.61q.094 1.484.89 2.265.806.774 2.235.774.828 0 1.602-.203.781-.203 1.547-.61v1.36q-.774.328-1.586.5-.813.172-1.649.172-2.093 0-3.32-1.22-1.219-1.218-1.219-3.296 0-2.148 1.157-3.406 1.164-1.266 3.132-1.266 1.766 0 2.79 1.14 1.03 1.134 1.03 3.087zm-1.438-.422q-.015-1.18-.664-1.883-.64-.703-1.703-.703-1.203 0-1.93.68-.718.68-.828 1.914z"/>""",  # noqa: E501
    "f": """<path d="M25.285 2.258v1.195H23.91q-.773 0-1.078.313-.297.312-.297 1.125v.773h2.367v1.117h-2.367v7.633H21.09V6.781h-1.375V5.664h1.375v-.61q0-1.46.68-2.124.68-.672 2.156-.672z"/>""",  # noqa: E501
    "g": """<path d="M24.973 9.937q0-1.562-.649-2.421-.64-.86-1.804-.86-1.157 0-1.805.86-.64.859-.64 2.421 0 1.555.64 2.415.648.859 1.805.859 1.164 0 1.804-.86.649-.859.649-2.414zm1.437 3.391q0 2.234-.992 3.32-.992 1.094-3.04 1.094-.757 0-1.429-.117-.672-.11-1.304-.344v-1.398q.632.344 1.25.508.617.164 1.257.164 1.414 0 2.118-.743.703-.734.703-2.226v-.711q-.446.773-1.141 1.156-.695.383-1.664.383-1.61 0-2.594-1.227-.984-1.226-.984-3.25 0-2.03.984-3.257.985-1.227 2.594-1.227.969 0 1.664.383t1.14 1.156V5.664h1.438z"/>""",  # noqa: E501
    "h": """<path d="M26.164 9.133v5.281h-1.437V9.18q0-1.243-.485-1.86-.484-.617-1.453-.617-1.164 0-1.836.742-.672.742-.672 2.024v4.945h-1.445V2.258h1.445v4.765q.516-.789 1.211-1.18.703-.39 1.617-.39 1.508 0 2.282.938.773.93.773 2.742z"/>""",  # noqa: E501
}

XX = """<g id="xx"><path d="M35.865 9.135a1.89 1.89 0 0 1 0 2.673L25.173 22.5l10.692 10.692a1.89 1.89 0 0 1 0 2.673 1.89 1.89 0 0 1-2.673 0L22.5 25.173 11.808 35.865a1.89 1.89 0 0 1-2.673 0 1.89 1.89 0 0 1 0-2.673L19.827 22.5 9.135 11.808a1.89 1.89 0 0 1 0-2.673 1.89 1.89 0 0 1 2.673 0L22.5 19.827 33.192 9.135a1.89 1.89 0 0 1 2.673 0z" fill="#000" stroke="#fff" stroke-width="1.688"/></g>"""  # noqa: E501

CHECK_GRADIENT = """<radialGradient id="check_gradient"><stop offset="0%" stop-color="#ff0000" stop-opacity="1.0" /><stop offset="50%" stop-color="#e70000" stop-opacity="1.0" /><stop offset="100%" stop-color="#9e0000" stop-opacity="0.0" /></radialGradient>"""  # noqa: E501

DEFAULT_COLORS = {
    "square light": "#ffce9e",
    "square dark": "#d18b47",
    "square dark lastmove": "#aaa23b",
    "square light lastmove": "#cdd16a",
    "margin": "#212121",
    "coord": "#e5e5e5",
    "arrow green": "#15781B80",
    "arrow red": "#88202080",
    "arrow yellow": "#e68f00b3",
    "arrow blue": "#00308880",
}


class Arrow:
    """Details of an arrow to be drawn."""

    tail: Square
    """Start square of the arrow."""

    head: Square
    """End square of the arrow."""

    color: str
    """Arrow color."""

    def __init__(self, tail: Square, head: Square, *, color: str = "green") -> None:
        self.tail = tail
        self.head = head
        self.color = color

    def pgn(self) -> str:
        """
        Returns the arrow in the format used by ``[%csl ...]`` and
        ``[%cal ...]`` PGN annotations, e.g., ``Ga1`` or ``Ya2h2``.

        Colors other than ``red``, ``yellow``, and ``blue`` default to green.
        """
        if self.color == "red":
            color = "R"
        elif self.color == "yellow":
            color = "Y"
        elif self.color == "blue":
            color = "B"
        else:
            color = "G"

        if self.tail == self.head:
            return f"{color}{chess.SQUARE_NAMES[self.tail]}"
        else:
            return f"{color}{chess.SQUARE_NAMES[self.tail]}{chess.SQUARE_NAMES[self.head]}"

    def __str__(self) -> str:
        return self.pgn()

    def __repr__(self) -> str:
        return f"Arrow({chess.SQUARE_NAMES[self.tail].upper()}, {chess.SQUARE_NAMES[self.head].upper()}, color={self.color!r})"

    @classmethod
    def from_pgn(cls, pgn: str) -> Arrow:
        """
        Parses an arrow from the format used by ``[%csl ...]`` and
        ``[%cal ...]`` PGN annotations, e.g., ``Ga1`` or ``Ya2h2``.

        Also allows skipping the color prefix, defaulting to green.

        :raises: :exc:`ValueError` if the format is invalid.
        """
        if pgn.startswith("G"):
            color = "green"
            pgn = pgn[1:]
        elif pgn.startswith("R"):
            color = "red"
            pgn = pgn[1:]
        elif pgn.startswith("Y"):
            color = "yellow"
            pgn = pgn[1:]
        elif pgn.startswith("B"):
            color = "blue"
            pgn = pgn[1:]
        else:
            color = "green"

        tail = chess.parse_square(pgn[:2])
        head = chess.parse_square(pgn[2:]) if len(pgn) > 2 else tail
        return cls(tail, head, color=color)


class SvgWrapper(str):
    def _repr_svg_(self) -> SvgWrapper:
        return self


def _svg(viewbox: int, size: Optional[int]) -> ET.Element:
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "viewBox": f"0 0 {viewbox:d} {viewbox:d}",
    })

    if size is not None:
        svg.set("width", str(size))
        svg.set("height", str(size))

    return svg


def _attrs(attrs: Dict[str, Union[str, int, float, None]]) -> Dict[str, str]:
    return {k: str(v) for k, v in attrs.items() if v is not None}


def _color(colors: Dict[str, str], color: str) -> Tuple[str, float]:
    color = colors.get(color, DEFAULT_COLORS[color])
    if color.startswith("#"):
        try:
            if len(color) == 5:
                return color[:4], int(color[4], 16) / 0xf
            elif len(color) == 9:
                return color[:7], int(color[7:], 16) / 0xff
        except ValueError:
            pass  # Ignore invalid hex value
    return color, 1.0


def _coord(text: str, x: int, y: int, width: int, height: int, horizontal: bool, margin: int, *, color: str, opacity: float) -> ET.Element:
    scale = margin / MARGIN

    if horizontal:
        x += int(width - scale * width) // 2
    else:
        y += int(height - scale * height) // 2

    t = ET.Element("g", _attrs({
        "transform": f"translate({x}, {y}) scale({scale}, {scale})",
        "fill": color,
        "stroke": color,
        "opacity": opacity if opacity < 1.0 else None,
    }))
    t.append(ET.fromstring(COORDS[text]))
    return t


def piece(piece: chess.Piece, size: Optional[int] = None) -> str:
    """
    Renders the given :class:`chess.Piece` as an SVG image.

    >>> import chess
    >>> import chess.svg
    >>>
    >>> chess.svg.piece(chess.Piece.from_symbol("R"))  # doctest: +SKIP

    .. image:: ../docs/wR.svg
        :alt: R
    """
    svg = _svg(SQUARE_SIZE, size)
    svg.append(ET.fromstring(PIECES[piece.symbol()]))
    return SvgWrapper(ET.tostring(svg).decode("utf-8"))


def board(board: Optional[chess.BaseBoard] = None, *,
          orientation: Color = chess.WHITE,
          lastmove: Optional[chess.Move] = None,
          check: Optional[Square] = None,
          arrows: Iterable[Union[Arrow, Tuple[Square, Square]]] = [],
          squares: Optional[IntoSquareSet] = None,
          size: Optional[int] = None,
          coordinates: bool = True,
          colors: Dict[str, str] = {},
          flipped: bool = False,
          style: Optional[str] = None) -> str:
    """
    Renders a board with pieces and/or selected squares as an SVG image.

    :param board: A :class:`chess.BaseBoard` for a chessboard with pieces, or
        ``None`` (the default) for a chessboard without pieces.
    :param orientation: The point of view, defaulting to ``chess.WHITE``.
    :param lastmove: A :class:`chess.Move` to be highlighted.
    :param check: A square to be marked indicating a check.
    :param arrows: A list of :class:`~chess.svg.Arrow` objects, like
        ``[chess.svg.Arrow(chess.E2, chess.E4)]``, or a list of tuples, like
        ``[(chess.E2, chess.E4)]``. An arrow from a square pointing to the same
        square is drawn as a circle, like ``[(chess.E2, chess.E2)]``.
    :param squares: A :class:`chess.SquareSet` with selected squares.
    :param size: The size of the image in pixels (e.g., ``400`` for a 400 by
        400 board), or ``None`` (the default) for no size limit.
    :param coordinates: Pass ``False`` to disable the coordinate margin.
    :param colors: A dictionary to override default colors. Possible keys are
        ``square light``, ``square dark``, ``square light lastmove``,
        ``square dark lastmove``, ``margin``, ``coord``, ``arrow green``,
        ``arrow blue``, ``arrow red``, and ``arrow yellow``. Values should look
        like ``#ffce9e`` (opaque), or ``#15781B80`` (transparent).
    :param flipped: Pass ``True`` to flip the board.
    :param style: A CSS stylesheet to include in the SVG image.

    >>> import chess
    >>> import chess.svg
    >>>
    >>> board = chess.Board("8/8/8/8/4N3/8/8/8 w - - 0 1")
    >>> squares = board.attacks(chess.E4)
    >>> chess.svg.board(board, squares=squares, size=350)  # doctest: +SKIP

    .. image:: ../docs/Ne4.svg
        :alt: 8/8/8/8/4N3/8/8/8

    .. deprecated:: 1.1
        Use *orientation* with a color instead of the *flipped* toggle.
    """
    orientation ^= flipped
    margin = 15 if coordinates else 0
    svg = _svg(8 * SQUARE_SIZE + 2 * margin, size)

    if style:
        ET.SubElement(svg, "style").text = style

    defs = ET.SubElement(svg, "defs")
    if board:
        for piece_color in chess.COLORS:
            for piece_type in chess.PIECE_TYPES:
                if board.pieces_mask(piece_type, piece_color):
                    defs.append(ET.fromstring(PIECES[chess.Piece(piece_type, piece_color).symbol()]))

    squares = chess.SquareSet(squares) if squares else chess.SquareSet()
    if squares:
        defs.append(ET.fromstring(XX))

    if check is not None:
        defs.append(ET.fromstring(CHECK_GRADIENT))

    if coordinates:
        margin_color, margin_opacity = _color(colors, "margin")
        ET.SubElement(svg, "rect", _attrs({
            "x": 0,
            "y": 0,
            "width": 2 * margin + 8 * SQUARE_SIZE,
            "height": 2 * margin + 8 * SQUARE_SIZE,
            "fill": margin_color,
            "opacity": margin_opacity if margin_opacity < 1.0 else None,
        }))

    for square, bb in enumerate(chess.BB_SQUARES):
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)

        x = (file_index if orientation else 7 - file_index) * SQUARE_SIZE + margin
        y = (7 - rank_index if orientation else rank_index) * SQUARE_SIZE + margin

        cls = ["square", "light" if chess.BB_LIGHT_SQUARES & bb else "dark"]
        if lastmove and square in [lastmove.from_square, lastmove.to_square]:
            cls.append("lastmove")
        fill_color, fill_opacity = _color(colors, " ".join(cls))

        cls.append(chess.SQUARE_NAMES[square])

        ET.SubElement(svg, "rect", _attrs({
            "x": x,
            "y": y,
            "width": SQUARE_SIZE,
            "height": SQUARE_SIZE,
            "class": " ".join(cls),
            "stroke": "none",
            "fill": fill_color,
            "opacity": fill_opacity if fill_opacity < 1.0 else None,
        }))

        if square == check:
            ET.SubElement(svg, "rect", _attrs({
                "x": x,
                "y": y,
                "width": SQUARE_SIZE,
                "height": SQUARE_SIZE,
                "class": "check",
                "fill": "url(#check_gradient)",
            }))

        # Render pieces.
        if board is not None:
            piece = board.piece_at(square)
            if piece:
                ET.SubElement(svg, "use", {
                    "xlink:href": f"#{chess.COLOR_NAMES[piece.color]}-{chess.PIECE_NAMES[piece.piece_type]}",
                    "transform": f"translate({x:d}, {y:d})",
                })

        # Render selected squares.
        if squares is not None and square in squares:
            ET.SubElement(svg, "use", _attrs({
                "xlink:href": "#xx",
                "x": x,
                "y": y,
            }))

    if coordinates:
        coord_color, coord_opacity = _color(colors, "coord")
        for file_index, file_name in enumerate(chess.FILE_NAMES):
            x = (file_index if orientation else 7 - file_index) * SQUARE_SIZE + margin
            svg.append(_coord(file_name, x, 0, SQUARE_SIZE, margin, True, margin, color=coord_color, opacity=coord_opacity))
            svg.append(_coord(file_name, x, margin + 8 * SQUARE_SIZE, SQUARE_SIZE, margin, True, margin, color=coord_color, opacity=coord_opacity))
        for rank_index, rank_name in enumerate(chess.RANK_NAMES):
            y = (7 - rank_index if orientation else rank_index) * SQUARE_SIZE + margin
            svg.append(_coord(rank_name, 0, y, margin, SQUARE_SIZE, False, margin, color=coord_color, opacity=coord_opacity))
            svg.append(_coord(rank_name, margin + 8 * SQUARE_SIZE, y, margin, SQUARE_SIZE, False, margin, color=coord_color, opacity=coord_opacity))

    for arrow in arrows:
        try:
            tail, head, color = arrow.tail, arrow.head, arrow.color  # type: ignore
        except AttributeError:
            tail, head = arrow  # type: ignore
            color = "green"

        try:
            color, opacity = _color(colors, " ".join(["arrow", color]))
        except KeyError:
            opacity = 1.0

        tail_file = chess.square_file(tail)
        tail_rank = chess.square_rank(tail)
        head_file = chess.square_file(head)
        head_rank = chess.square_rank(head)

        xtail = margin + (tail_file + 0.5 if orientation else 7.5 - tail_file) * SQUARE_SIZE
        ytail = margin + (7.5 - tail_rank if orientation else tail_rank + 0.5) * SQUARE_SIZE
        xhead = margin + (head_file + 0.5 if orientation else 7.5 - head_file) * SQUARE_SIZE
        yhead = margin + (7.5 - head_rank if orientation else head_rank + 0.5) * SQUARE_SIZE

        if (head_file, head_rank) == (tail_file, tail_rank):
            ET.SubElement(svg, "circle", _attrs({
                "cx": xhead,
                "cy": yhead,
                "r": SQUARE_SIZE * 0.9 / 2,
                "stroke-width": SQUARE_SIZE * 0.1,
                "stroke": color,
                "opacity": opacity if opacity < 1.0 else None,
                "fill": "none",
                "class": "circle",
            }))
        else:
            marker_size = 0.75 * SQUARE_SIZE
            marker_margin = 0.1 * SQUARE_SIZE

            dx, dy = xhead - xtail, yhead - ytail
            hypot = math.hypot(dx, dy)

            shaft_x = xhead - dx * (marker_size + marker_margin) / hypot
            shaft_y = yhead - dy * (marker_size + marker_margin) / hypot

            xtip = xhead - dx * marker_margin / hypot
            ytip = yhead - dy * marker_margin / hypot

            ET.SubElement(svg, "line", _attrs({
                "x1": xtail,
                "y1": ytail,
                "x2": shaft_x,
                "y2": shaft_y,
                "stroke": color,
                "opacity": opacity if opacity < 1.0 else None,
                "stroke-width": SQUARE_SIZE * 0.2,
                "stroke-linecap": "butt",
                "class": "arrow",
            }))

            marker = [(xtip, ytip),
                      (shaft_x + dy * 0.5 * marker_size / hypot,
                       shaft_y - dx * 0.5 * marker_size / hypot),
                      (shaft_x - dy * 0.5 * marker_size / hypot,
                       shaft_y + dx * 0.5 * marker_size / hypot)]

            ET.SubElement(svg, "polygon", _attrs({
                "points": " ".join(f"{x},{y}" for x, y in marker),
                "fill": color,
                "opacity": opacity if opacity < 1.0 else None,
                "class": "arrow",
            }))

    return SvgWrapper(ET.tostring(svg).decode("utf-8"))
