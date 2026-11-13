"""A drawn symbol's body rectangle in G, and a compiled page's text ink in mm, read from the library (DEL-4 reader tests)."""

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, NamedTuple

from symdef import Orientation, orient_box, text_width
from symdef.boxes import body_box

from electrical_symbols import LIBRARY, drawn_symbol, is_generic_box
lazy from fransys_layout.drawing import DrawnSymbol

__all__ = ["Ink", "Rect", "body_g", "page_ink"]

if TYPE_CHECKING:
    from collections.abc import Iterator

Rect = tuple[int, int, int, int]


def body_g(symbol: DrawnSymbol) -> Rect:
    """`symbol`'s own body as (x0, y0, x1, y1) in G: the library body turned and moved to it."""
    made = (
        drawn_symbol(
            symbol.key,
            symbol.texts,
            library=LIBRARY,
            offsets=dict(symbol.offsets),
            sides=dict(symbol.sides),
            turn=symbol.turn,
        )
        if is_generic_box(symbol.key)
        else LIBRARY.get(symbol.key)
    )
    box = orient_box(body_box(made), Orientation(symbol.orient))
    per = LIBRARY.grid.divisions_per_module
    return (
        symbol.x + int(box.min.x * per),
        symbol.y + int(box.min.y * per),
        symbol.x + int(box.max.x * per),
        symbol.y + int(box.max.y * per),
    )


class Ink(NamedTuple):
    """A text of a compiled page: its string, the origin of the symbol group that holds it, its ink box in mm on the sheet."""

    text: str
    origin: tuple[float, float]
    box: tuple[float, float, float, float]


_TRANSLATE = re.compile(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)")
_TURNED = re.compile(r"rotate\(\s*-90[ ,]+([-\d.]+)[ ,]+([-\d.]+)\s*\)")


def _walk(node: ET.Element, at: tuple[float, float]) -> Iterator[tuple[ET.Element, tuple[float, float]]]:
    """Every `<text>` under `node` with the summed translate of its parents."""
    for child in node:
        found = _TRANSLATE.search(child.get("transform") or "")
        here = (at[0] + float(found.group(1)), at[1] + float(found.group(2))) if found else at
        if child.tag.endswith("text"):
            yield child, at
        else:
            yield from _walk(child, here)


def page_ink(svg: str) -> list[Ink]:
    """The ink box of every text on a compiled page `svg`, measured in the library's font (anchor, size, cap height); a turned text as turned."""
    font = LIBRARY.font
    found = []
    for node, at in _walk(ET.fromstring(svg), (0.0, 0.0)):  # noqa: S314 - the page SVG is this build's own output
        size, text = float(node.get("font-size", "0")), node.text or ""
        x, y = float(node.get("x", "0")), float(node.get("y", "0"))
        width = text_width(font, text, size)
        left = {"start": x, "middle": x - width / 2, "end": x - width}[node.get("text-anchor", "start")]
        cap = font.cap_height / font.units_per_em * size
        box = (left, y - cap, left + width, y)
        turned = _TURNED.search(node.get("transform") or "")
        if turned:  # rotate(-90 cx cy) maps (px, py) to (cx + py - cy, cy - px + cx)
            cx, cy = float(turned.group(1)), float(turned.group(2))
            box = (cx + box[1] - cy, cy - box[2] + cx, cx + box[3] - cy, cy - box[0] + cx)
        found.append(Ink(text, at, (at[0] + box[0], at[1] + box[1], at[0] + box[2], at[1] + box[3])))
    return found
