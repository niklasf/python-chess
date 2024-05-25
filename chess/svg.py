from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import chess

from typing import Dict, Iterable, Optional, Tuple, Union
from chess import Color, IntoSquareSet, Square


SQUARE_SIZE = 45
MARGIN = 20
NAG_SIZE = 15

PIECES = {
    "b": """<g id="black-bishop" class="black bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zm6-4c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z" fill="#000" stroke-linecap="butt"/><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke="#fff" stroke-linejoin="miter"/></g>""",  # noqa: E501
    "k": """<g id="black-king" class="black king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6" stroke-linejoin="miter"/><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#000" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#000"/><path d="M20 8h5" stroke-linejoin="miter"/><path d="M32 29.5s8.5-4 6.03-9.65C34.15 14 25 18 22.5 24.5l.01 2.1-.01-2.1C20 18 9.906 14 6.997 19.85c-2.497 5.65 4.853 9 4.853 9M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0" stroke="#fff"/></g>""",  # noqa: E501
    "n": """<g id="black-knight" class="black knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#000000; stroke:#000000;"/><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#000000; stroke:#000000;"/><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#ececec; stroke:#ececec;"/><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#ececec; stroke:#ececec;"/><path d="M 24.55,10.4 L 24.1,11.85 L 24.6,12 C 27.75,13 30.25,14.49 32.5,18.75 C 34.75,23.01 35.75,29.06 35.25,39 L 35.2,39.5 L 37.45,39.5 L 37.5,39 C 38,28.94 36.62,22.15 34.25,17.66 C 31.88,13.17 28.46,11.02 25.06,10.5 L 24.55,10.4 z " style="fill:#ececec; stroke:none;"/></g>""",  # noqa: E501
    "p": """<g id="black-pawn" class="black pawn"><path d="M22.5 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38C17.33 16.5 16 18.59 16 21c0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#000" stroke="#000" stroke-width="1.5" stroke-linecap="round"/></g>""",  # noqa: E501
    "q": """<g id="black-queen" class="black queen" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#000" stroke="none"><circle cx="6" cy="12" r="2.75"/><circle cx="14" cy="9" r="2.75"/><circle cx="22.5" cy="8" r="2.75"/><circle cx="31" cy="9" r="2.75"/><circle cx="39" cy="12" r="2.75"/></g><path d="M9 26c8.5-1.5 21-1.5 27 0l2.5-12.5L31 25l-.3-14.1-5.2 13.6-3-14.5-3 14.5-5.2-13.6L14 25 6.5 13.5 9 26zM9 26c0 2 1.5 2 2.5 4 1 1.5 1 1 .5 3.5-1.5 1-1.5 2.5-1.5 2.5-1.5 1.5.5 2.5.5 2.5 6.5 1 16.5 1 23 0 0 0 1.5-1 0-2.5 0 0 .5-1.5-1-2.5-.5-2.5-.5-2 .5-3.5 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-27 0z" stroke-linecap="butt"/><path d="M11 38.5a35 35 1 0 0 23 0" fill="none" stroke-linecap="butt"/><path d="M11 29a35 35 1 0 1 23 0M12.5 31.5h20M11.5 34.5a35 35 1 0 0 22 0M10.5 37.5a35 35 1 0 0 24 0" fill="none" stroke="#fff"/></g>""",  # noqa: E501
    "r": """<g id="black-rook" class="black rook" fill="#000" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 39h27v-3H9v3zM12.5 32l1.5-2.5h17l1.5 2.5h-20zM12 36v-4h21v4H12z" stroke-linecap="butt"/><path d="M14 29.5v-13h17v13H14z" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M14 16.5L11 14h23l-3 2.5H14zM11 14V9h4v2h5V9h5v2h5V9h4v5H11z" stroke-linecap="butt"/><path d="M12 35.5h21M13 31.5h19M14 29.5h17M14 16.5h17M11 14h23" fill="none" stroke="#fff" stroke-width="1" stroke-linejoin="miter"/></g>""",  # noqa: E501
    "B": """<g id="white-bishop" class="white bishop" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><g fill="#fff" stroke-linecap="butt"><path d="M9 36c3.39-.97 10.11.43 13.5-2 3.39 2.43 10.11 1.03 13.5 2 0 0 1.65.54 3 2-.68.97-1.65.99-3 .5-3.39-.97-10.11.46-13.5-1-3.39 1.46-10.11.03-13.5 1-1.354.49-2.323.47-3-.5 1.354-1.94 3-2 3-2zM15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2zM25 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 1 1 5 0z"/></g><path d="M17.5 26h10M15 30h15m-7.5-14.5v5M20 18h5" stroke-linejoin="miter"/></g>""",  # noqa: E501
    "K": """<g id="white-king" class="white king" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22.5 11.63V6M20 8h5" stroke-linejoin="miter"/><path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#fff" stroke-linecap="butt" stroke-linejoin="miter"/><path d="M11.5 37c5.5 3.5 15.5 3.5 21 0v-7s9-4.5 6-10.5c-4-6.5-13.5-3.5-16 4V27v-3.5c-3.5-7.5-13-10.5-16-4-3 6 5 10 5 10V37z" fill="#fff"/><path d="M11.5 30c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0m-21 3.5c5.5-3 15.5-3 21 0"/></g>""",  # noqa: E501
    "N": """<g id="white-knight" class="white knight" fill="none" fill-rule="evenodd" stroke="#000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M 22,10 C 32.5,11 38.5,18 38,39 L 15,39 C 15,30 25,32.5 23,18" style="fill:#ffffff; stroke:#000000;"/><path d="M 24,18 C 24.38,20.91 18.45,25.37 16,27 C 13,29 13.18,31.34 11,31 C 9.958,30.06 12.41,27.96 11,28 C 10,28 11.19,29.23 10,30 C 9,30 5.997,31 6,26 C 6,24 12,14 12,14 C 12,14 13.89,12.1 14,10.5 C 13.27,9.506 13.5,8.5 13.5,7.5 C 14.5,6.5 16.5,10 16.5,10 L 18.5,10 C 18.5,10 19.28,8.008 21,7 C 22,7 22,10 22,10" style="fill:#ffffff; stroke:#000000;"/><path d="M 9.5 25.5 A 0.5 0.5 0 1 1 8.5,25.5 A 0.5 0.5 0 1 1 9.5 25.5 z" style="fill:#000000; stroke:#000000;"/><path d="M 15 15.5 A 0.5 1.5 0 1 1 14,15.5 A 0.5 1.5 0 1 1 15 15.5 z" transform="matrix(0.866,0.5,-0.5,0.866,9.693,-5.173)" style="fill:#000000; stroke:#000000;"/></g>""",  # noqa: E501
    "P": """<g id="white-pawn" class="white pawn"><path d="M22.5 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38C17.33 16.5 16 18.59 16 21c0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#fff" stroke="#000" stroke-width="1.5" stroke-linecap="round"/></g>""",  # noqa: E501
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

NAGS = {
    # "!"
    "1": """<g id="great_find">
                <path class="icon-background" fill="#5c8bb0" d="M 7.506 0 C 1.737 0 -1.869 6.25 1.015 11.25 C 3.9 16.25 11.111 16.25 13.996 11.25 C 14.654 10.11 15 8.817 15 7.5 C 15 3.358 11.644 0 7.506 0 Z"/>
                <path class="icon-component" fill="#fff" d="M 8.605 11.75 C 8.613 11.786 8.613 11.822 8.605 11.858 C 8.587 11.892 8.565 11.923 8.538 11.95 L 8.447 12.017 L 8.339 12.017 L 6.673 12.017 L 6.565 12.017 L 6.473 11.95 C 6.43 11.892 6.407 11.822 6.407 11.75 L 6.407 10.167 C 6.398 10.131 6.398 10.094 6.407 10.058 C 6.421 10.027 6.441 9.999 6.465 9.975 C 6.488 9.948 6.517 9.926 6.548 9.908 L 6.656 9.908 L 8.322 9.908 C 8.398 9.906 8.47 9.936 8.522 9.992 C 8.548 10.016 8.571 10.044 8.588 10.075 C 8.592 10.111 8.592 10.147 8.588 10.183 L 8.605 11.75 Z M 8.505 8.475 C 8.517 8.507 8.517 8.542 8.505 8.575 C 8.49 8.608 8.471 8.639 8.447 8.667 C 8.391 8.708 8.324 8.732 8.255 8.733 L 6.756 8.733 C 6.604 8.748 6.472 8.628 6.473 8.475 L 6.348 2.833 C 6.348 2.76 6.374 2.688 6.423 2.633 C 6.446 2.602 6.478 2.579 6.515 2.567 C 6.55 2.558 6.587 2.558 6.623 2.567 L 8.38 2.567 C 8.458 2.562 8.534 2.593 8.588 2.65 C 8.637 2.705 8.663 2.777 8.663 2.85 L 8.505 8.475 Z"/>
            </g>""",
    # "?"
    "2": """<g id="mistake">
                <path class="icon-background" fill="#e58f2a" d="M 7.505 0 C 1.736 0 -1.869 6.25 1.015 11.25 C 3.899 16.25 11.111 16.25 13.996 11.25 C 14.653 10.11 15 8.817 15 7.5 C 15 3.357 11.645 0 7.505 0 Z" style=""></path>
                <path class="icon-component" fill="#fff" d="M 8.272 12.1 C 8.279 12.134 8.279 12.168 8.272 12.2 C 8.258 12.233 8.237 12.264 8.213 12.291 C 8.161 12.342 8.093 12.368 8.022 12.367 L 6.423 12.367 C 6.39 12.375 6.356 12.375 6.323 12.367 C 6.291 12.351 6.261 12.328 6.24 12.299 C 6.191 12.252 6.165 12.185 6.165 12.117 L 6.165 10.575 C 6.163 10.504 6.189 10.435 6.24 10.383 L 6.323 10.325 L 6.423 10.325 L 7.997 10.325 C 8.068 10.323 8.137 10.35 8.188 10.4 C 8.211 10.426 8.23 10.453 8.246 10.483 C 8.254 10.519 8.254 10.555 8.246 10.592 L 8.272 12.1 Z M 10.104 6.125 C 10.03 6.339 9.93 6.545 9.803 6.733 C 9.679 6.909 9.543 7.077 9.396 7.233 C 9.26 7.378 9.115 7.514 8.962 7.642 C 8.772 7.807 8.592 7.982 8.421 8.166 C 8.274 8.325 8.193 8.535 8.197 8.75 L 8.197 8.934 C 8.205 8.966 8.205 9.001 8.197 9.033 C 8.19 9.065 8.172 9.095 8.147 9.116 C 8.124 9.141 8.095 9.162 8.064 9.175 L 7.963 9.175 L 6.498 9.175 L 6.397 9.175 C 6.366 9.162 6.337 9.141 6.314 9.116 C 6.289 9.094 6.268 9.065 6.256 9.033 C 6.25 9 6.25 8.967 6.256 8.934 L 6.256 8.641 C 6.25 8.404 6.287 8.166 6.365 7.941 C 6.429 7.745 6.522 7.561 6.639 7.392 C 6.748 7.226 6.874 7.073 7.014 6.934 C 7.147 6.808 7.289 6.692 7.422 6.583 C 7.61 6.416 7.787 6.238 7.955 6.05 C 8.094 5.898 8.17 5.699 8.171 5.491 C 8.174 5.394 8.154 5.297 8.113 5.208 C 8.062 5.123 7.989 5.052 7.905 5 C 7.734 4.868 7.521 4.798 7.305 4.8 C 7.167 4.799 7.03 4.818 6.897 4.859 C 6.78 4.897 6.665 4.944 6.556 5 C 6.469 5.04 6.388 5.091 6.314 5.15 L 6.223 5.225 C 6.162 5.258 6.093 5.275 6.023 5.275 C 5.948 5.265 5.88 5.223 5.84 5.158 L 5.007 4.166 C 4.918 4.073 4.918 3.927 5.007 3.833 C 5.06 3.772 5.118 3.716 5.182 3.666 C 5.335 3.537 5.503 3.424 5.681 3.334 C 5.919 3.208 6.167 3.105 6.423 3.025 C 6.746 2.924 7.083 2.876 7.422 2.884 C 7.761 2.886 8.098 2.94 8.421 3.041 C 8.746 3.15 9.053 3.308 9.329 3.509 C 9.6 3.712 9.821 3.975 9.979 4.275 C 10.139 4.608 10.218 4.973 10.211 5.342 C 10.217 5.606 10.181 5.872 10.104 6.125 Z" style=""></path>
            </g>""",
    # "!!"
    "3": """<g id="brilliant">
                <path class="icon-background" fill="#1bada6" d="M 7.506 0 C 1.737 0 -1.869 6.25 1.015 11.25 C 3.9 16.25 11.111 16.25 13.996 11.25 C 14.654 10.11 15 8.817 15 7.5 C 15 3.358 11.644 0 7.506 0 Z"></path>
                <path class="icon-component" fill="#fff" d="M 10.479 11.75 C 10.483 11.786 10.483 11.822 10.479 11.858 C 10.461 11.892 10.439 11.923 10.412 11.95 L 10.32 12.017 L 10.212 12.017 L 8.547 12.017 L 8.438 12.017 L 8.339 11.95 C 8.319 11.885 8.319 11.815 8.339 11.75 L 8.339 10.167 C 8.32 10.112 8.32 10.054 8.339 10 C 8.362 9.973 8.39 9.951 8.422 9.933 L 8.53 9.933 L 10.195 9.933 C 10.271 9.931 10.344 9.961 10.395 10.017 C 10.422 10.041 10.444 10.069 10.462 10.1 C 10.466 10.136 10.466 10.172 10.462 10.208 L 10.479 11.75 Z M 10.379 8.475 C 10.39 8.507 10.39 8.542 10.379 8.575 C 10.364 8.608 10.344 8.639 10.32 8.667 C 10.265 8.708 10.198 8.732 10.129 8.733 L 8.63 8.733 C 8.478 8.748 8.346 8.628 8.347 8.475 L 8.222 2.833 C 8.232 2.754 8.274 2.682 8.339 2.633 C 8.361 2.602 8.393 2.579 8.43 2.567 C 8.465 2.558 8.503 2.558 8.538 2.567 L 10.254 2.567 C 10.332 2.562 10.408 2.593 10.462 2.65 C 10.51 2.705 10.537 2.777 10.537 2.85 L 10.379 8.475 Z"></path>
                <path class="icon-component" fill="#fff" d="M 6.731 11.75 C 6.736 11.786 6.736 11.822 6.731 11.858 C 6.714 11.892 6.691 11.923 6.665 11.95 L 6.573 12.017 L 6.465 12.017 L 4.8 12.017 L 4.691 12.017 L 4.6 11.95 C 4.556 11.892 4.533 11.822 4.533 11.75 L 4.533 10.167 C 4.524 10.131 4.524 10.094 4.533 10.058 C 4.547 10.027 4.567 9.999 4.591 9.975 C 4.615 9.948 4.643 9.926 4.675 9.908 L 4.783 9.908 L 6.448 9.908 C 6.533 9.9 6.618 9.934 6.673 10 C 6.7 10.024 6.722 10.052 6.74 10.083 C 6.744 10.119 6.744 10.156 6.74 10.192 L 6.731 11.75 Z M 6.673 8.475 C 6.685 8.507 6.685 8.542 6.673 8.575 C 6.658 8.608 6.639 8.639 6.615 8.667 C 6.559 8.708 6.492 8.732 6.423 8.733 L 4.883 8.733 C 4.73 8.748 4.599 8.628 4.6 8.475 L 4.475 2.833 C 4.474 2.76 4.501 2.688 4.55 2.633 C 4.572 2.602 4.605 2.579 4.641 2.567 C 4.676 2.558 4.714 2.558 4.75 2.567 L 6.507 2.567 C 6.584 2.566 6.659 2.596 6.715 2.65 C 6.763 2.705 6.79 2.777 6.79 2.85 L 6.673 8.475 Z"></path>
            </g>""",
    # "??"
    "4": """<g id="blunder">
                <path class="icon-background" fill="#ca3431" d="M 7.505 0 C 1.736 0 -1.869 6.25 1.015 11.25 C 3.9 16.25 11.111 16.25 13.996 11.25 C 14.653 10.11 15 8.817 15 7.5 C 15 3.357 11.645 0 7.505 0 Z"></path>
                <path class="icon-component" fill="#fff" d="M 12.285 4.167 C 12.151 3.842 11.94 3.557 11.669 3.333 C 11.394 3.129 11.088 2.972 10.761 2.867 C 10.438 2.764 10.101 2.711 9.762 2.708 C 9.429 2.705 9.098 2.753 8.779 2.85 C 8.521 2.932 8.271 3.035 8.03 3.158 C 7.938 3.208 7.849 3.264 7.763 3.325 C 7.899 3.487 8.017 3.662 8.113 3.85 C 8.307 4.229 8.41 4.649 8.413 5.075 C 8.47 5.076 8.525 5.058 8.571 5.025 L 8.646 5 C 8.724 4.942 8.804 4.89 8.888 4.842 C 8.999 4.788 9.112 4.741 9.229 4.7 C 9.359 4.66 9.494 4.64 9.629 4.642 C 9.846 4.635 10.058 4.706 10.228 4.842 C 10.309 4.897 10.375 4.972 10.42 5.058 C 10.46 5.147 10.48 5.244 10.478 5.342 C 10.48 5.547 10.406 5.746 10.27 5.9 C 10.1 6.086 9.919 6.261 9.729 6.425 C 9.59 6.537 9.456 6.657 9.329 6.783 C 9.187 6.917 9.061 7.069 8.954 7.233 C 8.837 7.402 8.744 7.587 8.679 7.783 C 8.606 8.007 8.57 8.24 8.571 8.475 L 8.571 8.767 C 8.563 8.799 8.563 8.834 8.571 8.867 C 8.6 8.929 8.65 8.979 8.713 9.008 L 8.813 9.008 L 10.237 9.008 L 10.337 9.008 C 10.369 8.997 10.398 8.977 10.42 8.95 C 10.444 8.927 10.461 8.898 10.47 8.867 C 10.477 8.834 10.477 8.8 10.47 8.767 L 10.47 8.583 C 10.464 8.368 10.541 8.159 10.686 8 C 10.836 7.844 11.019 7.669 11.236 7.475 C 11.386 7.35 11.527 7.217 11.661 7.075 C 11.808 6.92 11.942 6.752 12.06 6.575 C 12.191 6.392 12.293 6.19 12.36 5.975 C 12.449 5.707 12.488 5.424 12.477 5.142 C 12.488 4.807 12.422 4.473 12.285 4.167 Z"></path>
                <path class="icon-component" fill="#fff" d="M 10.32 10.125 L 8.754 10.125 L 8.654 10.125 C 8.565 10.172 8.508 10.265 8.505 10.367 L 8.505 11.883 C 8.504 11.953 8.528 12.021 8.571 12.075 C 8.594 12.102 8.622 12.122 8.654 12.133 L 8.754 12.133 L 10.32 12.133 C 10.353 12.142 10.387 12.142 10.42 12.133 C 10.455 12.122 10.486 12.102 10.511 12.075 C 10.536 12.051 10.556 12.022 10.57 11.992 C 10.578 11.956 10.578 11.919 10.57 11.883 L 10.57 10.383 C 10.577 10.351 10.577 10.317 10.57 10.283 C 10.553 10.253 10.534 10.226 10.511 10.2 C 10.461 10.15 10.392 10.123 10.32 10.125 Z"></path>
                <path class="icon-component" fill="#fff" d="M 5.665 10.125 L 4.099 10.125 L 4 10.125 C 3.91 10.172 3.853 10.265 3.85 10.367 L 3.85 11.883 C 3.849 11.953 3.873 12.021 3.916 12.075 C 3.939 12.102 3.967 12.122 4 12.133 L 4.099 12.133 L 5.665 12.133 C 5.698 12.142 5.732 12.142 5.765 12.133 C 5.792 12.125 5.818 12.111 5.84 12.092 C 5.864 12.067 5.884 12.039 5.898 12.008 C 5.906 11.972 5.906 11.936 5.898 11.9 L 5.898 10.383 C 5.906 10.351 5.906 10.317 5.898 10.283 C 5.882 10.253 5.862 10.226 5.84 10.2 C 5.793 10.154 5.731 10.127 5.665 10.125 Z"></path>
                <path class="icon-component" fill="#fff" d="M 6.997 3.333 C 6.72 3.141 6.414 2.995 6.09 2.9 C 5.767 2.797 5.429 2.744 5.09 2.742 C 4.757 2.738 4.427 2.787 4.108 2.883 C 3.85 2.965 3.599 3.068 3.358 3.192 C 3.196 3.282 3.042 3.387 2.9 3.508 L 2.725 3.667 C 2.643 3.766 2.643 3.909 2.725 4.008 L 3.558 5.008 C 3.595 5.066 3.656 5.103 3.725 5.108 C 3.795 5.109 3.864 5.092 3.925 5.058 L 3.991 5 C 4.069 4.942 4.149 4.89 4.233 4.842 L 4.566 4.7 C 4.708 4.654 4.857 4.632 5.007 4.633 C 5.224 4.627 5.437 4.697 5.607 4.833 C 5.687 4.889 5.753 4.963 5.798 5.05 C 5.833 5.14 5.847 5.237 5.84 5.333 C 5.84 5.54 5.762 5.739 5.623 5.892 C 5.456 6.077 5.279 6.252 5.09 6.417 C 4.949 6.529 4.812 6.648 4.682 6.775 C 4.54 6.909 4.414 7.061 4.308 7.225 C 4.192 7.395 4.099 7.58 4.033 7.775 C 3.96 7.998 3.924 8.232 3.925 8.467 L 3.925 8.758 C 3.92 8.792 3.92 8.825 3.925 8.858 C 3.942 8.89 3.965 8.917 3.991 8.942 C 4.011 8.97 4.041 8.991 4.074 9 C 4.107 9.01 4.142 9.01 4.174 9 L 5.607 9 L 5.707 9 C 5.739 8.988 5.768 8.968 5.79 8.942 C 5.814 8.917 5.834 8.889 5.848 8.858 C 5.852 8.825 5.852 8.792 5.848 8.758 L 5.848 8.583 C 5.845 8.367 5.926 8.157 6.073 8 C 6.263 7.822 6.464 7.655 6.673 7.5 C 6.822 7.375 6.964 7.242 7.106 7.1 C 7.249 6.932 7.382 6.757 7.505 6.575 C 7.63 6.388 7.731 6.187 7.805 5.975 C 7.887 5.705 7.923 5.423 7.913 5.142 C 7.896 4.799 7.799 4.465 7.63 4.167 C 7.491 3.841 7.274 3.555 6.997 3.333 Z"></path>
            </g>""",
    # "?!"
    "6": """<g id="inaccuracy">
                <path class="icon-background" fill="#e87d00" d="M 7.506 0 C 1.737 0 -1.869 6.25 1.015 11.25 C 3.9 16.25 11.111 16.25 13.996 11.25 C 14.654 10.11 15 8.817 15 7.5 C 15 3.358 11.644 0 7.506 0 Z"></path>
                <path class="icon-component" fill="#fff" d="M 11.386 11.917 C 11.394 11.952 11.394 11.989 11.386 12.025 C 11.374 12.062 11.35 12.093 11.32 12.117 C 11.295 12.146 11.263 12.169 11.228 12.183 L 11.128 12.183 L 9.463 12.183 L 9.354 12.183 C 9.321 12.168 9.293 12.145 9.271 12.117 C 9.213 12.066 9.177 11.994 9.171 11.917 L 9.171 10.333 C 9.167 10.297 9.167 10.261 9.171 10.225 C 9.185 10.194 9.205 10.166 9.229 10.142 L 9.313 10.075 L 9.421 10.075 L 11.086 10.075 C 11.159 10.077 11.227 10.107 11.278 10.158 C 11.305 10.182 11.327 10.211 11.344 10.242 C 11.353 10.277 11.353 10.314 11.344 10.35 L 11.386 11.917 Z M 11.286 8.642 C 11.294 8.677 11.294 8.714 11.286 8.75 C 11.272 8.782 11.253 8.81 11.228 8.833 C 11.176 8.882 11.106 8.906 11.036 8.9 L 9.529 8.9 C 9.377 8.915 9.245 8.795 9.246 8.642 L 9.121 3 C 9.12 2.93 9.138 2.862 9.171 2.8 L 9.263 2.733 L 9.371 2.733 L 11.128 2.733 C 11.208 2.73 11.287 2.76 11.344 2.817 C 11.387 2.875 11.41 2.945 11.411 3.017 L 11.286 8.642 Z"></path>
                <path class="icon-component" fill="#fff" d="M 6.382 11.933 C 6.389 11.967 6.389 12.001 6.382 12.033 C 6.37 12.068 6.35 12.1 6.323 12.125 L 6.24 12.183 L 6.132 12.183 L 4.533 12.183 C 4.5 12.192 4.466 12.192 4.433 12.183 C 4.4 12.168 4.372 12.145 4.35 12.117 C 4.302 12.068 4.274 12.002 4.275 11.933 L 4.275 10.408 C 4.277 10.337 4.303 10.27 4.35 10.217 L 4.433 10.158 L 4.533 10.158 L 6.107 10.158 C 6.178 10.157 6.247 10.184 6.298 10.233 C 6.323 10.257 6.343 10.285 6.357 10.317 C 6.365 10.352 6.365 10.389 6.357 10.425 L 6.382 11.933 Z M 8.214 5.958 C 8.14 6.173 8.04 6.378 7.914 6.567 C 7.789 6.742 7.653 6.91 7.506 7.067 C 7.373 7.222 7.228 7.367 7.073 7.5 C 6.882 7.665 6.701 7.84 6.532 8.025 C 6.383 8.183 6.303 8.392 6.307 8.608 L 6.307 8.792 C 6.316 8.824 6.316 8.859 6.307 8.892 C 6.3 8.925 6.283 8.954 6.257 8.975 C 6.234 9.002 6.206 9.022 6.174 9.033 L 6.074 9.033 L 4.616 9.033 C 4.584 9.043 4.549 9.043 4.516 9.033 C 4.482 9.024 4.453 9.003 4.433 8.975 C 4.402 8.955 4.379 8.926 4.367 8.892 C 4.361 8.858 4.361 8.825 4.367 8.792 L 4.367 8.5 C 4.365 8.262 4.402 8.026 4.475 7.8 C 4.542 7.606 4.635 7.421 4.75 7.25 C 4.858 7.085 4.984 6.931 5.124 6.792 C 5.258 6.667 5.399 6.55 5.532 6.442 C 5.723 6.275 5.904 6.097 6.074 5.908 C 6.209 5.754 6.283 5.556 6.282 5.35 C 6.284 5.252 6.264 5.156 6.223 5.067 C 6.181 4.976 6.114 4.898 6.032 4.842 C 5.86 4.71 5.649 4.639 5.432 4.642 C 5.29 4.63 5.147 4.642 5.008 4.675 C 4.89 4.717 4.776 4.767 4.666 4.825 C 4.58 4.875 4.499 4.933 4.425 5 L 4.333 5.075 C 4.282 5.093 4.228 5.102 4.175 5.1 C 4.091 5.104 4.01 5.067 3.959 5 L 3.126 3.992 C 3.041 3.897 3.041 3.753 3.126 3.658 C 3.19 3.592 3.263 3.532 3.342 3.483 C 3.486 3.361 3.642 3.255 3.809 3.167 C 4.049 3.042 4.299 2.939 4.558 2.858 C 4.878 2.757 5.213 2.709 5.549 2.717 C 6.23 2.719 6.895 2.934 7.448 3.333 C 7.713 3.541 7.931 3.802 8.089 4.1 C 8.256 4.433 8.342 4.802 8.339 5.175 C 8.339 5.441 8.296 5.706 8.214 5.958 Z"></path>
            </g>"""
}

XX = """<g id="xx"><path d="M35.865 9.135a1.89 1.89 0 0 1 0 2.673L25.173 22.5l10.692 10.692a1.89 1.89 0 0 1 0 2.673 1.89 1.89 0 0 1-2.673 0L22.5 25.173 11.808 35.865a1.89 1.89 0 0 1-2.673 0 1.89 1.89 0 0 1 0-2.673L19.827 22.5 9.135 11.808a1.89 1.89 0 0 1 0-2.673 1.89 1.89 0 0 1 2.673 0L22.5 19.827 33.192 9.135a1.89 1.89 0 0 1 2.673 0z" fill="#000" stroke="#fff" stroke-width="1.688"/></g>"""  # noqa: E501

CHECK_GRADIENT = """<radialGradient id="check_gradient" r="0.5"><stop offset="0%" stop-color="#ff0000" stop-opacity="1.0" /><stop offset="50%" stop-color="#e70000" stop-opacity="1.0" /><stop offset="100%" stop-color="#9e0000" stop-opacity="0.0" /></radialGradient>"""  # noqa: E501

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
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "viewBox": f"0 0 {viewbox:d} {viewbox:d}",
    })

    if size is not None:
        svg.set("width", str(size))
        svg.set("height", str(size))

    return svg


def _attrs(attrs: Dict[str, Union[str, int, float, None]]) -> Dict[str, str]:
    return {k: str(v) for k, v in attrs.items() if v is not None}


def _select_color(colors: Dict[str, str], color: str) -> Tuple[str, float]:
    return _color(colors.get(color, DEFAULT_COLORS[color]))


def _color(color: str) -> Tuple[str, float]:
    if color.startswith("#"):
        try:
            if len(color) == 5:
                return color[:4], int(color[4], 16) / 0xf
            elif len(color) == 9:
                return color[:7], int(color[7:], 16) / 0xff
        except ValueError:
            pass  # Ignore invalid hex value
    return color, 1.0


def _coord(text: str, x: float, y: float, scale: float, *, color: str, opacity: float) -> ET.Element:
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
          fill: Dict[Square, str] = {},
          squares: Optional[IntoSquareSet] = None,
          size: Optional[int] = None,
          coordinates: bool = True,
          colors: Dict[str, str] = {},
          flipped: bool = False,
          style: Optional[str] = None,
          nag:Optional[int] = None) -> str:
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
    :param fill: A dictionary mapping squares to a colors that they should be
        filled with.
    :param squares: A :class:`chess.SquareSet` with selected squares to mark
        with an X.
    :param size: The size of the image in pixels (e.g., ``400`` for a 400 by
        400 board), or ``None`` (the default) for no size limit.
    :param coordinates: Pass ``False`` to disable the coordinate margin.
    :param colors: A dictionary to override default colors. Possible keys are
        ``square light``, ``square dark``, ``square light lastmove``,
        ``square dark lastmove``, ``margin``, ``coord``, ``inner border``,
        ``outer border``, ``arrow green``, ``arrow blue``, ``arrow red``,
        and ``arrow yellow``. Values should look like ``#ffce9e`` (opaque),
        or ``#15781B80`` (transparent).
    :param flipped: Pass ``True`` to flip the board.
    :param style: A CSS stylesheet to include in the SVG image.
    :param nag: Pass ``NAG Constant`` to show Numerical Notation Glyphs (NAGs).
        Supports !(great), !!(brilliant), ?(mistake), ?!(inaccuracy) and ??(blunder)
        (requires ``lastmove`` to be passed along as argument)

    >>> import chess
    >>> import chess.svg
    >>>
    >>> board = chess.Board("8/8/8/8/4N3/8/8/8 w - - 0 1")
    >>>
    >>> chess.svg.board(
    ...     board,
    ...     fill=dict.fromkeys(board.attacks(chess.E4), "#cc0000cc"),
    ...     arrows=[chess.svg.Arrow(chess.E4, chess.F6, color="#0000cccc")],
    ...     squares=chess.SquareSet(chess.BB_DARK_SQUARES & chess.BB_FILE_B),
    ...     size=350,
    ... )  # doctest: +SKIP

    .. image:: ../docs/Ne4.svg
        :alt: 8/8/8/8/4N3/8/8/8

    .. deprecated:: 1.1
        Use *orientation* with a color instead of the *flipped* toggle.
    """
    # Bringing GLOBAL Constants in the local scope for a little performance boost 
    global SQUARE_SIZE, MARGIN, NAG_SIZE, PIECES, COORDS, NAGS, XX, CHECK_GRADIENT, DEFAULT_COLORS
    orientation ^= flipped
    full_size = 8 * SQUARE_SIZE
    svg = _svg(full_size, size)
    desc = ET.SubElement(svg, "desc")
    defs = ET.SubElement(svg, "defs")

    if style:
        ET.SubElement(svg, "style").text = style

    # Render board.
    for square, bb in enumerate(chess.BB_SQUARES):
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)

        x = (file_index if orientation else 7 - file_index) * SQUARE_SIZE
        y = (7 - rank_index if orientation else rank_index) * SQUARE_SIZE

        cls = ["square", "light" if chess.BB_LIGHT_SQUARES & bb else "dark"]
        square_color, square_opacity = _select_color(colors, " ".join(cls))

        cls.append(chess.SQUARE_NAMES[square])

        ET.SubElement(svg, "rect", _attrs({
            "x": x,
            "y": y,
            "width": SQUARE_SIZE,
            "height": SQUARE_SIZE,
            "class": " ".join(cls),
            "stroke": "none",
            "fill": square_color,
            "opacity": square_opacity if square_opacity < 1.0 else None,
        }))

        try:
            fill_color, fill_opacity = _color(fill[square])
        except KeyError:
            pass
        else:
            ET.SubElement(svg, "rect", _attrs({
                "x": x,
                "y": y,
                "width": SQUARE_SIZE,
                "height": SQUARE_SIZE,
                "stroke": "none",
                "fill": fill_color,
                "opacity": fill_opacity if fill_opacity < 1.0 else None,
            }))
    
    # Rendering lastmove
    if lastmove:
        for square in [lastmove.from_square, lastmove.to_square]:
            bb = 1 << square
            file_index = chess.square_file(square)
            rank_index = chess.square_rank(square)

            x = (file_index if orientation else 7 - file_index) * SQUARE_SIZE
            y = (7 - rank_index if orientation else rank_index) * SQUARE_SIZE

            cls = ["square", "light" if chess.BB_LIGHT_SQUARES & bb else "dark", "lastmove"]
            square_color, square_opacity = _select_color(colors, " ".join(cls))

            cls.append(chess.SQUARE_NAMES[square])

            ET.SubElement(svg, "rect", _attrs({
                "x": x,
                "y": y,
                "width": SQUARE_SIZE,
                "height": SQUARE_SIZE,
                "class": " ".join(cls),
                "stroke": "none",
                "fill": square_color,
                "opacity": square_opacity if square_opacity < 1.0 else None,
            }))

    # Render check mark.
    if check is not None:
        defs.append(ET.fromstring(CHECK_GRADIENT))
        file_index = chess.square_file(check)
        rank_index = chess.square_rank(check)

        x = (file_index if orientation else 7 - file_index) * SQUARE_SIZE
        y = (7 - rank_index if orientation else rank_index) * SQUARE_SIZE

        ET.SubElement(svg, "rect", _attrs({
            "x": x,
            "y": y,
            "width": SQUARE_SIZE,
            "height": SQUARE_SIZE,
            "class": "check",
            "fill": "url(#check_gradient)",
        }))

    # Render pieces and selected squares.
    if board is not None:
        asciiboard = ET.SubElement(desc, "pre")
        asciiboard.text = str(board)
        # Defining pieces
        for piece_color in chess.COLORS:
            for piece_type in chess.PIECE_TYPES:
                if board.pieces_mask(piece_type, piece_color):
                    defs.append(ET.fromstring(PIECES[chess.Piece(piece_type, piece_color).symbol()]))
        # Rendering pieces
        for square, bb in enumerate(chess.BB_SQUARES):
            file_index = chess.square_file(square)
            rank_index = chess.square_rank(square)

            x = (file_index if orientation else 7 - file_index) * SQUARE_SIZE
            y = (7 - rank_index if orientation else rank_index) * SQUARE_SIZE

            piece = board.piece_at(square)
            if piece:
                href = f"#{chess.COLOR_NAMES[piece.color]}-{chess.PIECE_NAMES[piece.piece_type]}"
                ET.SubElement(svg, "use", {
                    "href": href,
                    "xlink:href": href,
                    "transform": f"translate({x:d}, {y:d})",
                })

    # Render coordinates.
    if coordinates:
        light_color, light_opacity = _select_color(colors, "square light")
        dark_color, dark_opacity = _select_color(colors, "square dark")
        text_scale = 0.5
        coord_size = 18
        width = coord_size * text_scale
        height = coord_size * text_scale
        for file_index, file_name in enumerate(chess.FILE_NAMES):
            x = ((file_index if orientation else 7 - file_index) * SQUARE_SIZE) - width # type: ignore
            y = full_size - height # type: ignore
            coord_color, coord_opacity = (light_color, light_opacity) if (file_index+orientation)%2 == 1 else (dark_color, dark_opacity)
            svg.append(_coord(file_name, x+1.5, y-1, text_scale, color=coord_color, opacity=coord_opacity))
        x += (7 - file_index if orientation else file_index) * SQUARE_SIZE
        x += SQUARE_SIZE
        for rank_index, rank_name in enumerate(chess.RANK_NAMES):
            y = ((7 - rank_index if orientation else rank_index) * SQUARE_SIZE) - height # type: ignore
            coord_color, coord_opacity = (dark_color, dark_opacity) if (rank_index+orientation)%2 == 1 else (light_color, light_opacity)
            svg.append(_coord(rank_name, x-1, y+3, text_scale, color=coord_color, opacity=coord_opacity))

    # Render X Squares
    if squares is not None:
        defs.append(ET.fromstring(XX))
        squares = chess.SquareSet(squares) if squares else chess.SquareSet()
        for square in squares:
            file_index = chess.square_file(square)
            rank_index = chess.square_rank(square)
            x = (file_index if orientation else 7 - file_index) * SQUARE_SIZE
            y = (7 - rank_index if orientation else rank_index) * SQUARE_SIZE
            # Render selected squares
            ET.SubElement(svg, "use", _attrs({
                "href": "#xx",
                "xlink:href": "#xx",
                "x": x,
                "y": y,
            }))

    # Render arrows.
    for arrow in arrows:
        try:
            tail, head, color = arrow.tail, arrow.head, arrow.color  # type: ignore
        except AttributeError:
            tail, head = arrow  # type: ignore
            color = "green"

        try:
            color, opacity = _select_color(colors, " ".join(["arrow", color]))
        except KeyError:
            opacity = 1.0

        tail_file = chess.square_file(tail)
        tail_rank = chess.square_rank(tail)
        head_file = chess.square_file(head)
        head_rank = chess.square_rank(head)

        xtail = (tail_file + 0.5 if orientation else 7.5 - tail_file) * SQUARE_SIZE
        ytail = (7.5 - tail_rank if orientation else tail_rank + 0.5) * SQUARE_SIZE
        xhead = (head_file + 0.5 if orientation else 7.5 - head_file) * SQUARE_SIZE
        yhead = (7.5 - head_rank if orientation else head_rank + 0.5) * SQUARE_SIZE

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

    if nag is not None and \
       lastmove is not None and \
       NAGS.get(str(nag), None) is not None:
        ele = ET.fromstring(NAGS[str(nag)])
        defs.append(ele)
        id = ele.attrib.get("id")
        file_index = chess.square_file(lastmove.to_square)
        rank_index = chess.square_rank(lastmove.to_square)
        x = (file_index if orientation else 7 - file_index) * SQUARE_SIZE
        y = (7 - rank_index if orientation else rank_index) * SQUARE_SIZE
        # Making sure the NAGs doesn't overlap the Last Move Arrow by switching 
        # between top left and top right corner depending upon where the Arrow
        # is coming from.
        from_file_index = chess.square_file(lastmove.from_square)
        file_index = (file_index if orientation else 7 - file_index)
        from_file_index = (from_file_index if orientation else 7 - from_file_index)
        x = x + (SQUARE_SIZE - NAG_SIZE if file_index >= from_file_index else 0)
        ET.SubElement(svg, "use", _attrs({
            "href": f"#{id}",
            "xlink:href": f"#{id}",
            "x": x,
            "y": y,
        }))
    
    return SvgWrapper(ET.tostring(svg).decode("utf-8"))
