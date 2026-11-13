"""REFERENCE_NOT_READABLE: a drawn reference marker or off stub read back against `reference_targets` and `marker_text` (READ-REFERENCES, R2).

The model gives each stored frame cell the candidate markers there. A candidate is drawn when a symbol on its page
carries its port and prints `marker_text` whole, in the frame cell the stored one names. Markers drawn so are joined
by their reference group. An off stub with no reference is drawn when a symbol at its port prints its `marker_text` whole:
the text is the stub's far end, and one text names one set of far ports at one port (the lexicon, S2b). A cell
or text that differs, or one `#n` naming two groups in one drawing set, is an error.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from electrical_symbols import MARKER_SLOT
from fransys_layout.symbols import frame_cell
from fransys_model.derive import reference_targets
from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import LinkMarker, Page, StarKind, layout_of, sheet_format_of

from .drawn_finding import drawn_finding

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_model.kernel import Finding, Id, Model

    from .drawn_graph import Union
    from .drawn_netlist import Netlist, PagePart

__all__ = ["References", "join_references", "reference_findings"]

XY = tuple[int, int]
type _Fault = tuple[Id[Page], Id[LinkMarker], str]
type _Node = tuple[Id[Page], XY]


@dataclass(frozen=True)
class References:
    """What a reader reads of the markers: faults, each marker's node by record id (None: on no ink), each group's nodes, each stub's listed ports."""

    faults: tuple[_Fault, ...]
    markers: dict[str, _Node | None]
    groups: dict[object, list[_Node]]
    stubs: dict[_Node, set[str]] = field(default_factory=dict)


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


def _lexicon(model: Model, grouped: set[Id[LinkMarker]], pages: Mapping[Id[Page], PagePart]) -> dict[tuple[Id[Page], str, str], list[LinkMarker]]:
    """The stub lexicon: each off stub that is no reference, by the page, port and whole text it prints.

    A reader takes the stub's far ports from the text, so one key must name one set of them.
    """
    found: dict[tuple[Id[Page], str, str], list[LinkMarker]] = defaultdict(list)
    for record in layout_of(model, LinkMarker).values():
        if record.star is StarKind.OFF and record.pairs and record.page in pages and record.id not in grouped:
            found[record.page, record.port.value, marker_text(model, record)].append(record)
    return found


def _read_stubs(
    model: Model, drawn: Mapping[tuple[Id[Page], str, str], list[XY]], pages: Mapping[Id[Page], PagePart], grouped: set[Id[LinkMarker]]
) -> References:
    """The stubs read back: a stub is read where its whole text is drawn at its port.

    One text naming two far sets at one port, or a text drawn nowhere there, is a fault.
    """
    faults: list[_Fault] = []
    read: dict[str, _Node | None] = {}
    groups: dict[object, list[_Node]] = defaultdict(list)
    listed: dict[_Node, set[str]] = defaultdict(set)
    for (page, port, text), records in _lexicon(model, grouped, pages).items():
        first = records[0]
        if len({tuple(x.far for x in one.pairs) for one in records}) > 1:
            faults.append((page, first.id, f"stub text {text!r} names different far ports at one port"))
        elif not (at := drawn.get((page, port, text))):
            faults.append((page, first.id, f"stub prints {text!r}: not drawn at its port"))
        else:
            held = [(page, one) for one in at if one in pages[page].nodes]
            read.update(dict.fromkeys((one.id.value for one in records), held[0] if held else None))
            groups[frozenset((port, first.pairs[0].far.value))].extend(held[:1])
            for node in held[:1]:
                listed[node].update(x.port.value for one in records for x in one.pairs)
    return References(tuple(faults), read, groups, listed)


def join_references(model: Model, pages: Mapping[Id[Page], PagePart], library: Library, union: Union) -> References:
    """Join the nodes of the markers of each reference group that are read back, and read the stubs; the faults of those that are not."""
    drawn, markers = _drawn(pages), layout_of(model, LinkMarker)
    faults, nodes, read, listed = _ambiguous(model), defaultdict(list), {}, defaultdict(set)
    targets = reference_targets(model)
    for (page, cell), ends in targets.items():
        for marker, _, group, text in (end for end in ends if page in pages):
            at = drawn.get((page, markers[marker].port.value, text), [])
            held = [(page, one) for one in at if one in pages[page].nodes]
            if not _stands(model, page, cell, at, library):
                faults.append((page, marker, f"marker prints {text!r} in cell {cell}: " + ("drawn elsewhere" if at else "not drawn")))
            elif not held:
                faults.append((page, marker, f"marker prints {text!r} on no wire of its net"))
            else:
                nodes[group].extend(held)
                read[marker.value] = held[0]
                if markers[marker].star is StarKind.OFF:
                    listed[held[0]].update(x.port.value for x in markers[marker].pairs)
    stubs = _read_stubs(model, drawn, pages, {m for ends in targets.values() for m, *_ in ends})
    for joined in nodes.values():
        for node in joined[1:]:
            union.join(joined[0], node)
    return References((*faults, *stubs.faults), {**read, **stubs.markers}, {**nodes, **stubs.groups}, {**listed, **stubs.stubs})


def reference_findings(net: Netlist) -> tuple[Finding, ...]:
    """REFERENCE_NOT_READABLE per fault of the netlist's reference reading."""
    return tuple(drawn_finding("REFERENCE_NOT_READABLE", (page, marker), message) for page, marker, message in net.unreadable)
