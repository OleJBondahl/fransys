"""PRINTED_TEXT_WRONG: each text a finished `Drawing` prints, read back against the derive function the writer calls (READ-IDENTITY).

Six readers, each `(model, net) -> Iterator[(subjects, message)]`: pin markings, tags, contact tables, where-texts, frame titles, power potentials.
The expected side is derive's; the drawn side is the `Drawing`, so a text changed after the write is a finding (CORRECTNESS-PROOF, ruling 9).
"""

from typing import TYPE_CHECKING

from electrical_symbols import drawn_slots, is_generic_box, marking_slot
from fransys_layout.symbols import library_symbol
from fransys_model.derive import (
    coil_table_texts,
    contact_places,
    function_placements,
    hidden_pins,
    port_marking,
    port_power_text,
    printed_tag,
)

from .drawn_finding import drawn_finding
from .drawn_power import POWER_KEYS, page_unit
from .drawn_where import stand_places, where_text
from .kit_keys import function_of
from .write_tables import HEAD

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from typing import Any

    from electrical_symbols import Library
    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.layout import Page
    from fransys_model.vocab import Port

    from .drawn_netlist import Netlist

__all__ = ["declared_marks", "printed_findings"]

type _Row = tuple[tuple[Id[Any], ...], str]


def declared_marks(drawings: Mapping[Id[Page], Drawing], by: Mapping[str, Mapping[str, Id[Port]]], library: Library) -> dict[str, str]:
    """Each port to the marking slot id its symbol declares at that pin; a generic box declares none (`drawn_slots` owns its markings)."""
    found = {}
    for drawing in drawings.values():
        for symbol in drawing.symbols:
            if symbol.id not in by or is_generic_box(symbol.key):
                continue
            declared = {slot.id for slot in library_symbol(library, symbol.key, symbol.poles).slots}
            found.update({port.value: slot for pin, port in by[symbol.id].items() if (slot := marking_slot(pin)) in declared})
    return found


def _markings(model: Model, net: Netlist) -> Iterator[_Row]:
    """A declared marking slot whose drawn text is not `port_marking` of its port (hidden pins skipped)."""
    hidden = hidden_pins(model)
    drawn = {(symbol.id, slot): text for part in net.pages.values() for symbol in part.drawing.symbols for slot, text in symbol.slots}
    for port, slot in net.marks.items():
        if net.ids[port] in hidden:
            continue
        want, got = port_marking(model, net.ids[port]) or "", drawn.get((net.owners[port], slot), "")
        if want != got:
            yield (net.ids[port],), f"symbol {net.owners[port]} prints {got!r} in slot {slot} where the port is marked {want!r}"


def _tags(model: Model, net: Netlist) -> Iterator[_Row]:
    """A TAG text of a drawn symbol that is not `printed_tag` (a strip tag has no owner yet, N3)."""
    for page, part in net.pages.items():
        unit = page_unit(model, page)
        for text in part.drawing.texts:
            key = net.keys.get(text.owner or "")
            if getattr(text, "kind", "") != "TAG" or key is None:  # DrawnText.kind, read as in drawing_invariants
                continue
            want = printed_tag(model, key, unit=unit, alone=(page, text.owner) in net.alone)
            if text.text != want:
                yield (key,), f"symbol {text.owner} prints the tag {text.text!r} where the model gives {want!r}"


def _tables(model: Model, net: Netlist) -> Iterator[_Row]:
    """A contact-table head whose cells or slots are not `coil_table_texts` over the places `contact_places` gives."""
    for page, part in net.pages.items():
        for symbol in (s for s in part.drawing.symbols if s.id in net.heads):
            coil = net.heads[symbol.id]
            texts = coil_table_texts(model, coil, contact_places(model, coil, page))
            if (symbol.texts, symbol.slots) != (texts, tuple(drawn_slots(HEAD, texts).items())):
                yield (coil,), f"the contact table {symbol.id} prints {symbol.texts!r} where the model gives {texts!r}"


def _where(model: Model, net: Netlist) -> Iterator[_Row]:
    """A WHERE line of a placed terminal that is not `where_text` of one of its other placements or the stand places it names (R2993)."""
    rows = function_placements(model)
    for page, part in net.pages.items():
        for text in (t for t in part.drawing.texts if getattr(t, "kind", "") == "WHERE" and net.keys.get(t.owner or "") is not None):
            function = function_of(model, net.keys[text.owner or ""])
            here = next((r for r in rows.get(function, ()) if r[0] == page), None)
            others = (r for r in rows.get(function, ()) if r[0] != page)
            wanted = {where_text(model, here, there) for there in (*others, *(at for _, at in stand_places(model, function)))} if here else set()
            if text.text not in wanted:
                yield (
                    (function,),
                    f"symbol {text.owner} prints the where-text {text.text!r} where the model gives {len(wanted)} other placements, none printing it",
                )


def _outlines(_model: Model, net: Netlist) -> Iterator[_Row]:
    """A frame label that is not the title of its unit (`frame_titles`)."""
    for page, part in net.pages.items():
        for outline in (o for o in part.drawing.outlines if o.id in net.titles):
            got = outline.label.text if outline.label else ""
            if got != net.titles[outline.id]:
                yield (page,), f"frame {outline.id} prints {got!r} where its unit's title is {net.titles[outline.id]!r}"


def _powers(model: Model, net: Netlist) -> Iterator[_Row]:
    """A power symbol whose printed potential is not `port_power_text` of its port (A5)."""
    for part in net.pages.values():
        for symbol in (s for s in part.drawing.symbols if s.key in POWER_KEYS and s.ports):
            port = net.ids[symbol.ports[0]]
            want = port_power_text(model, port)
            for slot, text in symbol.slots if want is not None else ():
                if text != want:
                    yield (port,), f"symbol {symbol.id} prints {text!r} in slot {slot} where the net's potential is {want!r}"


def printed_findings(model: Model, net: Netlist) -> tuple[Finding, ...]:
    """PRINTED_TEXT_WRONG per drawn text that is not its derive text."""
    readers = (_markings, _tags, _tables, _where, _outlines, _powers)
    return tuple(drawn_finding("PRINTED_TEXT_WRONG", subjects, message) for read in readers for subjects, message in read(model, net))
