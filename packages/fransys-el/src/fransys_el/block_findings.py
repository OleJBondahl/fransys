"""HARNESS_WIRE_MISMATCH: every drawn cable-block wire equals one derive harness-wire row, and every row is drawn (el-0122).

The rows are `fransys_model.derive.cable_drawing`'s (`block_cables`, `block_wires`); the drawn wires are the placed
values of `CableLayout`. Both are read as values: no SVG and no text is parsed.
"""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_model.derive.cable_drawing import block_cables, block_wires, drawn_pins, row_links
from fransys_model.kernel import render_id

from .drawn_finding import drawn_finding

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fransys_layout import CableLayout, PlacedBlock, PlacedWire
    from fransys_model.kernel import Finding, Id, Model

__all__ = ["block_wire_findings"]


@dataclass(frozen=True, slots=True)
class _Wire:
    """One core or single wire as a row says it or as the block draws it.

    `cable` is None for a single wire; `ends` holds its ports in drawn ends. A row link reaches no cable box,
    so its cable is not compared.
    """

    cable: Id[Any] | None
    ends: tuple[Id[Any], ...]
    link: bool = False


def _rows(model: Model, block: PlacedBlock) -> dict[Id[Any], _Wire]:
    """The derive rows of the block by conductor: each core of each cable, then each single wire.

    A blank end draws no pin, so its port is left out of both sides. A port the model gives a drawn end stays in the
    row, so a pin cell the block lost leaves the row end undrawn.
    """
    subject, unit = block.subject, block.unit
    seen = {pin.port for end in block.ends if not end.blank for pin in drawn_pins(model, subject, end.item, unit)}
    links = set(row_links(model, subject, unit))
    found = {
        core.conductor: _Wire(cable.cable, tuple(port for port in (core.end_a, core.end_b) if port in seen), core.conductor in links)
        for cable in block_cables(model, subject, unit)
        for core in cable.cores
    }
    found |= {
        wire.conductor: _Wire(None, tuple(port for port in (wire.end_a, wire.end_b) if port in seen), wire.conductor in links)
        for wire in block_wires(model, subject, unit)
    }
    return found


def _landings(block: PlacedBlock) -> dict[tuple[Id[Any], int, int], Id[Any]]:
    """`(conductor, x, y)` to the port a core lands on, at the edge of its drawn end box that faces the cable."""
    return {
        (place.core, place.x, end.y + end.height if end.top else end.y): cell.port
        for end in block.ends
        if not end.blank
        for cell in end.cells
        for place in cell.landings
    }


def _cables_touched(block: PlacedBlock, wire: PlacedWire) -> set[Id[Any]]:
    """The cables whose box edge a run of the wire reaches."""
    points = (*wire.run_a, *wire.run_b)
    return {
        placed.cable
        for placed in block.boxes
        for p in points
        if placed.box.x <= p.x <= placed.box.x + placed.box.width and p.y in (placed.box.y, placed.box.y + placed.box.height)
    }


def _drawn(block: PlacedBlock) -> Iterator[tuple[Id[Any], _Wire | None]]:
    """Each drawn core or wire by conductor with what it reaches; None when its runs reach two cable boxes."""
    landing = _landings(block)
    for wire in (w for w in block.wires if not w.open):
        ends = tuple(dict.fromkeys(landing[key] for p in (*wire.run_a, *wire.run_b) if (key := (wire.conductor, p.x, p.y)) in landing))
        touched = _cables_touched(block, wire)
        if len(touched) > 1:
            yield wire.conductor, None
        else:
            yield wire.conductor, _Wire(next(iter(touched), None), ends)


def _ports(ends: tuple[Id[Any], ...]) -> str:
    return ", ".join(render_id(port) for port in ends) or "none"


def _says(wire: _Wire) -> str:
    cable = "cable " + render_id(wire.cable) if wire.cable else "no cable"
    return f"{cable}, ends {_ports(wire.ends)}"


def _differs(drawn: _Wire | None, row: _Wire) -> bool:
    return drawn is None or set(drawn.ends) != set(row.ends) or (not row.link and drawn.cable != row.cable)


def _finding(block: PlacedBlock, conductor: Id[Any], row: _Wire | None, text: str) -> Finding:
    cable = row.cable if row and row.cable else block.subject
    name = f"core {render_id(conductor)} of {render_id(cable)}, block {render_id(block.subject)}"
    return drawn_finding("HARNESS_WIRE_MISMATCH", (cable, conductor), f"{name}: {text}")


def _block_findings(model: Model, block: PlacedBlock) -> Iterator[Finding]:
    rows = _rows(model, block)
    drawn = list(_drawn(block))
    for conductor, wire in drawn:
        row = rows.get(conductor)
        if row is None:
            yield _finding(block, conductor, None, "the block draws a wire that no harness-wire row has")
        elif _differs(wire, row):
            seen = "reaches two cables" if wire is None else _says(wire)
            yield _finding(block, conductor, row, f"drawn as {seen}, but the row says {_says(row)}")
    count = Counter(conductor for conductor, _ in drawn)
    for conductor, row in rows.items():
        if count[conductor] != 1:
            yield _finding(block, conductor, row, f"the harness-wire row is drawn {count[conductor]} times, not once")


def block_wire_findings(model: Model, layout: CableLayout) -> tuple[Finding, ...]:
    """One ERROR per drawn wire that differs from its row, per extra drawn wire and per row not drawn once."""
    return tuple(f for block in layout.blocks.values() for f in _block_findings(model, block))
