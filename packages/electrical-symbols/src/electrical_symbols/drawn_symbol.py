"""The symbol a drawn record names, built from the strings known after placement (es-0076)."""

import math
from typing import TYPE_CHECKING

from symdef import (
    Library,
    Orientation,
    Symbol,
    SymdefError,
    fitted_table,
    from_divisions,
    measure,
    translate,
)
from symdef import text_width as symdef_text_width

from electrical_symbols.box_ports import G_PER_MODULE, GENERIC_BOX_KEY, box_port_marking
from electrical_symbols.generic_box import generic_box

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = ["drawn_slots", "drawn_symbol"]

_HEADS = ("contact-head", "contact-head-headed")
_HEADED = "contact-head-headed"
_ROW = "contact-row"
_TITLES = ("no", "nc")  # the head's two title slots, and each row's two cell slots


def _marking_width(library: Library, name: str) -> int:
    """The width in G of a port's marking set 1 M high in the library font, rounded up."""
    width = symdef_text_width(library.font, box_port_marking(name), 1.0)
    return math.ceil(round(width, 9) * G_PER_MODULE)


def _box(
    texts: Sequence[Sequence[str]],
    library: Library,
    offsets: Mapping[str, int],
    sides: Mapping[str, str],
) -> Symbol:
    """A generic box: one port per row, named by its first cell, at its offset (G) when given."""
    names = tuple(row[0] for row in texts)
    return generic_box(
        names,
        tuple(sides[n] for n in names) if sides else (),
        offsets=tuple(offsets[n] / G_PER_MODULE for n in names) if offsets else (),
        marking_widths=tuple(_marking_width(library, n) for n in names),
    )


def _head_texts(key: str, head: Sequence[str]) -> dict[str, str]:
    """The head's slot strings: the two column titles, and the heading of the headed head."""
    found = dict(zip(_TITLES, head, strict=False))
    return {**found, "heading": head[2]} if key == _HEADED else found


def _table(key: str, texts: Sequence[Sequence[str]], library: Library) -> Symbol:
    """The fitted contact table with its keep-out's top-left at the origin.

    `texts[0]` is the head row: the NO and NC titles, then the heading for the headed head. Each
    further row is a NO cell and an NC cell, an empty cell leaving its column unset.
    """
    font = library.font
    assert font is not None  # noqa: S101 -- a drawn library carries its font
    head, *rows = texts
    made = fitted_table(
        library.get(_ROW),
        "y",
        [{c: cell for c, cell in zip(_TITLES, row, strict=False) if cell} for row in rows],
        library,
        font.heights["body"] / library.grid.module_mm,
        head=library.get(key),
        head_texts=_head_texts(key, head),
    )
    corner = measure(made, Orientation.R0, library).keepout.min
    return translate(
        made, from_divisions(library.grid, -corner.x), from_divisions(library.grid, -corner.y)
    )


def drawn_symbol(
    key: str,
    texts: Sequence[Sequence[str]],
    *,
    library: Library,
    offsets: Mapping[str, int] | None = None,
    sides: Mapping[str, str] | None = None,
) -> Symbol:
    """The symbol of library `key` over `texts`, the rows of cell strings a drawn record holds.

    No texts: `library.get(key)`. The generic box key: a box with a port per row, named by the
    row's first cell. A contact head key: the fitted table, head row first, its keep-out's
    top-left at the origin. Any other key with texts is refused. `offsets` (port name to G) put a
    box's ports at those x; the body then ends one pitch past the last (model-0129). `sides` (port
    name to `n` or `s`) puts each box port on its side; none: the alternating sides.
    """
    if not texts:
        return library.get(key)
    if key == GENERIC_BOX_KEY:
        return _box(texts, library, offsets or {}, sides or {})
    if key in _HEADS:
        return _table(key, texts, library)
    msg = f"symbol {key!r} takes no texts; its drawn record carries {len(texts)} rows"
    raise SymdefError(msg)


def drawn_slots(key: str, texts: Sequence[Sequence[str]]) -> dict[str, str]:
    """The string of each slot of `drawn_symbol(key, texts)` that holds text, by slot id.

    A box marks each port (`marking.<port>`); a table sets its titles, its heading and, for row
    k from 1, `k.no` and `k.nc`. Empty texts, or a key that takes none, give no strings.
    """
    if not texts:
        return {}
    if key == GENERIC_BOX_KEY:
        return {f"marking.{row[0]}": box_port_marking(row[0]) for row in texts}
    head, *rows = texts
    found = _head_texts(key, head)
    for k, row in enumerate(rows, 1):
        found.update({f"{k}.{c}": cell for c, cell in zip(_TITLES, row, strict=False) if cell})
    return found
