"""Layout's symdef layer (SB11, layout-0316): the one place `fransys_layout` reads symdef.

It measures a symbol once per allowed orientation, copies the fields into the core's plain
values and does no arithmetic of its own. The placement core stays on integers.
"""

from .markers import fitted_marker, fitted_marker_views, marker_views, with_marker
from .shape import LibrarySymbol, Shape, library_symbol, stretched_body, symbol_shape
from .table import TableAsk
from .views import Ask, Views, symbol_views

__all__ = (
    "Ask",
    "LibrarySymbol",
    "Shape",
    "TableAsk",
    "Views",
    "fitted_marker",
    "fitted_marker_views",
    "library_symbol",
    "marker_views",
    "stretched_body",
    "symbol_shape",
    "symbol_views",
    "with_marker",
)
