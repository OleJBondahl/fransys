"""REFERENCE_NOT_READABLE: a drawn reference marker read back against `reference_targets` (READ-REFERENCES, R2).

The model gives each stored frame cell the candidate markers there. A candidate is drawn when a symbol on its page
carries its port and prints `marker_text` whole, in the frame cell the stored one names. Markers drawn so are joined
by their reference group. A cell or text that differs, or one `#n` naming two groups in one drawing set, is an error.
"""

from collections import defaultdict
from typing import TYPE_CHECKING

from electrical_symbols import MARKER_SLOT
from fransys_layout.symbols import frame_cell
from fransys_model.derive import reference_targets
from fransys_model.layout import LinkMarker, Page, layout_of, sheet_format_of

from .drawn_finding import drawn_finding

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_model.kernel import Finding, Id, Model

    from .drawn_graph import Union
    from .drawn_netlist import Netlist, PagePart

__all__ = ["join_references", "reference_findings"]

XY = tuple[int, int]
type _Fault = tuple[Id[Page], Id[LinkMarker], str]


def _drawn(pages: Mapping[Id[Page], PagePart]) -> dict[tuple[Id[Page], str, str], list[XY]]:
    """The points of the symbols that print a marker text, by page, port value and the whole text."""
    found: dict[tuple[Id[Page], str, str], list[XY]] = defaultdict(list)
    for page, part in pages.items():
        for symbol in part.drawing.symbols:
            if symbol.ports and (text := dict(symbol.slots).get(MARKER_SLOT)) is not None:
                found[page, symbol.ports[0], text].append((symbol.x, symbol.y))
    return found


def _ambiguous(model: Model) -> list[_Fault]:
    """One fault per `#n` that names two groups in one drawing set: the number alone would not tell a reader which."""
    pages, named = layout_of(model, Page), defaultdict(dict)
    for (page, _), ends in reference_targets(model).items():
        for marker, number, group, _ in ends:
            named[pages[page].drawing_set, number].setdefault(group, (page, marker))
    return [
        (page, marker, f"reference number {number} names {len(groups)} groups in one drawing set")
        for (_, number), groups in named.items()
        if len(groups) > 1
        for page, marker in groups.values()
    ]


def _stands(model: Model, page: Id[Page], cell: tuple[int, str], at: list[XY], library: Library) -> bool:
    """True when one of the drawn points lies in the stored frame cell."""
    sheet = sheet_format_of(model, layout_of(model, Page)[page].sheet_format)
    return any(frame_cell(library, sheet, *one) == cell for one in at)


def join_references(model: Model, pages: Mapping[Id[Page], PagePart], library: Library, union: Union) -> tuple[_Fault, ...]:
    """Join the nodes of the markers of each reference group that are read back; the faults of those that are not."""
    drawn, markers = _drawn(pages), layout_of(model, LinkMarker)
    faults, nodes = _ambiguous(model), defaultdict(list)
    for (page, cell), ends in reference_targets(model).items():
        for marker, _, group, text in (end for end in ends if page in pages):
            at = drawn.get((page, markers[marker].port.value, text), [])
            if not _stands(model, page, cell, at, library):
                faults.append((page, marker, f"marker prints {text!r} in cell {cell}: " + ("drawn elsewhere" if at else "not drawn")))
            else:
                nodes[group].extend((page, one) for one in at if one in pages[page].nodes)
    for joined in nodes.values():
        for node in joined[1:]:
            union.join(joined[0], node)
    return tuple(faults)


def reference_findings(net: Netlist) -> tuple[Finding, ...]:
    """REFERENCE_NOT_READABLE per fault of the netlist's reference reading."""
    return tuple(drawn_finding("REFERENCE_NOT_READABLE", (page, marker), message) for page, marker, message in net.unreadable)
