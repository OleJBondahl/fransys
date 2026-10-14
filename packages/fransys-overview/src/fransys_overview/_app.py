"""The overview page's script: hand-written ES2020, no framework, no build step.

Its parts are the `_js_*` modules, joined into one function. Its rules (`textContent` only, no
randomness, clock or network, no layout call) are in the README.
"""

from typing import Final

from ._js_alt import JS_ALT
from ._js_changes import JS_CHANGES
from ._js_core import JS_CORE
from ._js_draw import JS_DRAW
from ._js_features import JS_FEATURES
from ._js_focus import JS_FOCUS
from ._js_lens import JS_LENS
from ._js_main import JS_MAIN
from ._js_matrix import JS_MATRIX
from ._js_panels import JS_PANELS
from ._js_places import JS_PLACES
from ._js_zoom import JS_ZOOM

APP_JS: Final[str] = (
    "'use strict';\n(function () {"
    + JS_CORE
    + JS_CHANGES
    + JS_DRAW
    + JS_PANELS
    + JS_PLACES
    + JS_ZOOM
    + JS_FEATURES
    + JS_FOCUS
    + JS_MATRIX
    + JS_LENS
    + JS_ALT
    + JS_MAIN
    + "})();\n"
)
