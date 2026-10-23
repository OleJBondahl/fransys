"""The drawn values: what render draws from, in G, with every string final (SW5, layout-0315).

A `Drawing` is one page's things; a `Sheet` its frame; a `Style` the pens and sizes. Each is a
frozen dataclass of numbers, strings and tuples, so `fransys_layout.core.to_plain` and `from_plain`
give its JSON form. Imports the standard library and the core's plain values only.
"""

from dataclasses import dataclass
from typing import Literal

lazy from .core.values import XY, Box, Orientation, Side, Size
lazy from .drawing_reads import (
    page_texts,
    struck_texts,
    text_overlaps,
    wire_bends,
    wire_crossings,
    wire_length,
)
lazy from .geometry.symbols import port_points

__all__ = (
    "Corner",
    "Drawing",
    "DrawnMarker",
    "DrawnOutline",
    "DrawnSymbol",
    "DrawnText",
    "DrawnWire",
    "Sheet",
    "Style",
    "TextStyle",
    "WireStyle",
    "page_texts",
    "port_points",
    "struck_texts",
    "text_overlaps",
    "wire_bends",
    "wire_crossings",
    "wire_length",
)

Corner = Literal["NW", "NE", "SW", "SE"]


@dataclass(frozen=True, slots=True)
class DrawnText:
    """One text: its final string, its box in G and the corner of the box it is anchored by."""

    text: str
    box: Box
    kind: str
    anchor: Corner


@dataclass(frozen=True, slots=True)
class DrawnSymbol:
    """A library symbol at (x, y) in G, turned to `orient`.

    `stretch` is (axis, length G) pairs, `offsets` (port id, G along the stretch axis) pairs,
    `sides` (box port id, `n` or `s`) pairs, `leads` the ports whose bound leads draw (none:
    no bound lead), `n` the rows of a table
    symbol, `poles` the pole count (the symbol repeated that many times), `slots` (slot id,
    string) pairs, `texts` the rows of cell strings that size a box or a table (empty for a
    plain library symbol). A marker and a contact table are DrawnSymbols too.
    `outline` is the body box in G on the page, absolute: the box the core placed, or the
    symbol's own body at its origin; `None` when the producer knew no body. `ports` and `net`
    are identity strings with no meaning to the core or to render: the ports the symbol draws,
    and the net a marker stands for.
    """

    id: str
    key: str
    x: int
    y: int
    orient: Orientation
    slots: tuple[tuple[str, str], ...] = ()
    stretch: tuple[tuple[str, int], ...] = ()
    offsets: tuple[tuple[str, int], ...] = ()
    sides: tuple[tuple[str, str], ...] = ()
    leads: tuple[str, ...] = ()
    n: int = 1
    poles: int = 1
    muted: bool = False
    tint: str | None = None
    texts: tuple[tuple[str, ...], ...] = ()
    outline: Box | None = None
    ports: tuple[str, ...] = ()
    net: str = ""


@dataclass(frozen=True, slots=True)
class DrawnWire:
    """One polyline in the library wire style `style`; `lanes` above one is a bundle.

    `net` is the identity string of the net it draws; render ignores it.
    """

    id: str
    points: tuple[XY, ...]
    style: str
    lanes: int = 1
    label: DrawnText | None = None
    net: str = ""


@dataclass(frozen=True, slots=True)
class DrawnMarker:
    """A reference marker at (x, y) facing `side`, with its texts by slot id."""

    id: str
    key: str
    x: int
    y: int
    side: Side
    texts: tuple[tuple[str, str], ...]
    tint: str | None


@dataclass(frozen=True, slots=True)
class DrawnOutline:
    """A closed outline of library style `key` through `points`, with an optional label."""

    id: str
    key: str
    points: tuple[XY, ...]
    label: DrawnText | None


@dataclass(frozen=True, slots=True)
class Drawing:
    """One page: its area in G, the things drawn on it and the library version they name."""

    area: Size
    symbols: tuple[DrawnSymbol, ...]
    wires: tuple[DrawnWire, ...]
    markers: tuple[DrawnMarker, ...]
    texts: tuple[DrawnText, ...]
    outlines: tuple[DrawnOutline, ...]
    library_version: str


@dataclass(frozen=True, slots=True)
class Sheet:
    """A sheet in mm: its frame symbol key, and its title-block texts."""

    width_mm: float
    height_mm: float
    frame_key: str
    slots: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class WireStyle:
    """A wire's stroke width and dash lengths in mm (no dash: an empty tuple)."""

    width_mm: float
    dash_mm: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class TextStyle:
    """A text's capital height in mm and its font family."""

    height_mm: float
    family: str


@dataclass(frozen=True, slots=True)
class Style:
    """Pens, sizes and the grid: everything `svg` needs that a `Drawing` does not carry.

    `tints` are the net-reference fills in slot order; `muted_colour` draws a not-installed thing.
    `wires`, `texts` and `dashes` are (id, value) pairs in the model's order
    (no sort); a dash is its lengths in mm.
    `module_mm` is one module (M).
    """

    tints: tuple[str, ...]
    wires: tuple[tuple[str, WireStyle], ...]
    texts: tuple[tuple[str, TextStyle], ...]
    dashes: tuple[tuple[str, tuple[float, ...]], ...]
    line_thin_mm: float
    line_thick_mm: float
    line_rule_mm: float
    junction_dot_mm: float
    muted_colour: str
    module_mm: float
    wiring_grid: int
    g_per_module: int
