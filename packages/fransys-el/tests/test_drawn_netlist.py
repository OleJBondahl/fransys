"""The drawn netlist is checked against the model (DRAWN-NETLIST, el-0052).

A clean build raises none of the sweep's codes. Each class is planted as a small patch to a
finished drawing: join two nets, move a wire end to a neighbour port, drop a junction dot, unpair a
marker, bend a wire, run a wire through a body, draw one connection twice.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

import pytest
from conventions_fixtures import house
from fransys_el import build, lay_out_core, lay_out_drawn
from fransys_el.drawn_netlist import drawn_netlist, is_marker
from fransys_el.drawn_sweep import drawing_sweep
from ring_cases import bank_model, box_kit

from electrical_symbols import LIBRARY
from fransys_layout.drawing import DrawnWire

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing

CODES = {
    "CONNECTION_NOT_DRAWN",
    "DRAWING_SHORTS_NETS",
    "ROUTE_WRONG_PORT",
    "MARKER_UNPAIRED",
    "CONNECTION_DRAWN_TWICE",
    "WIRE_NOT_ORTHOGONAL",
    "MISSING_JUNCTION_DOT",
}


@dataclass(frozen=True)
class Built:
    """What the sweep of one build was given: the model, kit, drawings and marker records."""

    model: Any
    kit: Any
    drawings: dict
    markers: Any

    def codes(self, drawings: dict | None = None) -> set[str]:
        """The sweep's codes (and OVERLAP) over `drawings`, or the build's own."""
        got = drawing_sweep(self.model, self._net(drawings or self.drawings), ())
        return {f.code for f in got}

    def count(self, code: str, drawings: dict | None = None) -> int:
        """How many findings of `code` the sweep gives over `drawings`, or the build's own."""
        return len(self.messages(code, drawings or self.drawings))

    def messages(self, code: str, drawings: dict) -> list[str]:
        return [
            f.message for f in drawing_sweep(self.model, self._net(drawings), ()) if f.code == code
        ]

    def _net(self, drawings: dict):
        return drawn_netlist(self.model, self.kit, drawings, self.markers, LIBRARY)

    def netlist(self):
        return self._net(self.drawings)

    def patched(self, page, **fields) -> dict:
        """The drawings with `page`'s drawing replaced by the same with `fields` changed."""
        return {**self.drawings, page: replace(self.drawings[page], **fields)}


def _built(bank: int, monkeypatch: pytest.MonkeyPatch) -> Built:
    model = bank_model(bank)
    conventions, kit = house(), box_kit(model)
    problem, _ = build(model, kit, conventions, LIBRARY)
    caught: list[tuple] = []
    original = lay_out_core.drawn_netlist

    def spy(*args):
        caught.append(args)
        return original(*args)

    monkeypatch.setattr(lay_out_core, "drawn_netlist", spy)
    lay_out_drawn(model, kit, problem, conventions, LIBRARY)
    laid, _, drawings, markers, _ = caught[0]
    return Built(laid, kit, dict(drawings), markers)


@pytest.fixture(scope="module")
def bank8():
    with pytest.MonkeyPatch.context() as patch:
        return _built(8, patch)


@pytest.fixture(scope="module")
def bank40():
    with pytest.MonkeyPatch.context() as patch:
        return _built(40, patch)


def _at(part, point) -> str | None:
    return next((p for p, at in part.ports.items() if at == point), None)


def _wire_between_ports(built: Built):
    """(page, index) of a one-lane wire with a port at each end, found in the build."""
    for page, part in built.netlist().pages.items():
        for i, wire in enumerate(part.drawing.wires):
            ends = (_at(part, wire.points[0]), _at(part, wire.points[-1]))
            if wire.lanes == 1 and all(ends) and ends[0] != ends[1]:
                return page, i
    pytest.fail("no wire between two ports")


def test_a_clean_build_raises_none_of_the_sweeps_codes(bank8, bank40):
    """The bank of 8 raises no code of the sweep since ROUTING's guard (R439)."""
    assert bank8.codes() & CODES == set()
    assert (
        bank40.codes() & {"ROUTE_WRONG_PORT", "MARKER_UNPAIRED", "CONNECTION_DRAWN_TWICE"} == set()
    )


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_that_joins_two_nets_is_a_short(bank8):
    net = bank8.netlist()
    page, part = next(iter(net.pages.items()))
    first = next(iter(part.ports))
    other = next(p for p in part.ports if net.net(bank8.model, p) != net.net(bank8.model, first))
    (ax, ay), (bx, by) = part.ports[first], part.ports[other]
    bridge = DrawnWire("bridge", ((ax, ay), (ax, by), (bx, by)), part.drawing.wires[0].style)
    planted = bank8.patched(page, wires=(*part.drawing.wires, bridge))
    assert bank8.count("DRAWING_SHORTS_NETS", planted) > bank8.count("DRAWING_SHORTS_NETS")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_end_moved_to_a_neighbour_port_is_a_wrong_port(bank8):
    page, i = _wire_between_ports(bank8)
    part = bank8.netlist().pages[page]
    wire = part.drawing.wires[i]
    mine = bank8.netlist().net(bank8.model, _at(part, wire.points[-1]))
    other = next(at for p, at in part.ports.items() if bank8.netlist().net(bank8.model, p) != mine)
    moved = replace(wire, points=(*wire.points[:-1], other))
    wires = tuple(moved if k == i else w for k, w in enumerate(part.drawing.wires))
    assert bank8.count("ROUTE_WRONG_PORT", bank8.patched(page, wires=wires)) > bank8.count(
        "ROUTE_WRONG_PORT"
    )


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_dropped_leaves_its_connection_missing(bank8):
    page, i = _wire_between_ports(bank8)
    wires = tuple(w for k, w in enumerate(bank8.drawings[page].wires) if k != i)
    assert bank8.count("CONNECTION_NOT_DRAWN", bank8.patched(page, wires=wires)) > bank8.count(
        "CONNECTION_NOT_DRAWN"
    )


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_second_path_between_two_ports_is_a_connection_drawn_twice(bank8):
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (ax, ay), (bx, by) = wire.points[0], wire.points[-1]
    detour = DrawnWire("again", ((ax, ay), (ax + 8, ay), (ax + 8, by), (bx, by)), wire.style)
    planted = bank8.patched(page, wires=(*bank8.drawings[page].wires, detour))
    assert bank8.count("CONNECTION_DRAWN_TWICE", planted) > bank8.count("CONNECTION_DRAWN_TWICE")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_marker_whose_partner_is_not_drawn_is_unpaired(bank40):
    for page, part in bank40.netlist().pages.items():
        marks = [s for s in part.drawing.symbols if is_marker(s)]
        if marks:
            kept = tuple(s for s in part.drawing.symbols if s is not marks[0])
            assert bank40.count(
                "MARKER_UNPAIRED", bank40.patched(page, symbols=kept)
            ) > bank40.count("MARKER_UNPAIRED")
            return
    pytest.fail("no reference marker in the bank of 40")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_junction_dot_dropped_leaves_a_dotless_t(bank40):
    for page, part in bank40.netlist().pages.items():
        dots = [s for s in part.drawing.symbols if s.key == "junction-dot"]
        if dots:
            kept = tuple(s for s in part.drawing.symbols if s is not dots[0])
            assert bank40.count(
                "MISSING_JUNCTION_DOT", bank40.patched(page, symbols=kept)
            ) > bank40.count("MISSING_JUNCTION_DOT")
            return
    pytest.fail("no junction dot in the bank of 40")


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_diagonal_segment_is_not_orthogonal(bank8):
    page, i = _wire_between_ports(bank8)
    wire = bank8.drawings[page].wires[i]
    (ax, ay) = wire.points[0]
    bent = replace(wire, points=((ax, ay), (ax + 8, ay + 8), wire.points[-1]))
    wires = tuple(bent if k == i else w for k, w in enumerate(bank8.drawings[page].wires))
    assert bank8.count("WIRE_NOT_ORTHOGONAL", bank8.patched(page, wires=wires)) > bank8.count(
        "WIRE_NOT_ORTHOGONAL"
    )


@pytest.mark.rule("DRAWN-NETLIST")
def test_a_wire_through_a_body_is_an_overlap(bank8):
    page = next(iter(bank8.drawings))
    drawing: Drawing = bank8.drawings[page]
    body = next(s.outline for s in drawing.symbols if s.outline and s.outline.w > 8)
    y = body.y + body.h // 2
    across = DrawnWire(
        "across", ((body.x - 8, y), (body.x + body.w + 8, y)), drawing.wires[0].style
    )
    planted = bank8.patched(page, wires=(*drawing.wires, across))
    before = sum(int(m.split()[0]) for m in bank8.messages("OVERLAP", bank8.drawings))
    assert sum(int(m.split()[0]) for m in bank8.messages("OVERLAP", planted)) == before + 1
