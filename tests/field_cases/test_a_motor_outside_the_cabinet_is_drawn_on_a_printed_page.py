"""Field case: a top-level motor in the plant room, fed by cable from a cabinet unit's strip, belongs to the cabinet's document.
The bug (R311): the motor got a page, but document_drawing_sets gives a unit document only its own unit's sets, so no document printed it.
Fixed by R316 (decision model-0360), a unit document prints the sets of the top-level items its strips feed."""

from dataclasses import replace
from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
from _expected_codes import expect_codes
from fransys_el import lay_out_core
from fransys_el.drawn_netlist import drawn_netlist, is_marker
lazy import pytest

from fransys_model.derive import printed_drawing_sets
from fransys_model.layout import DrawingSet, Page, layout_of


class _Io(NamedTuple):
    out: fr.TerminalStrip


@fr.unit("demo-mini-mcc", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _cabinet(c: fr.Design) -> _Io:
    x = c.terminal_strip("X1", "DEMO-TB-2.5", 3, pe="DEMO-TB-PE-2.5", interface=True)
    c.earth(x.run("PE", 1)[1])
    return _Io(x)


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="PLANT")
    d.location("PLANT", "Plant room")
    strip = d.add(_cabinet, "U1", place=None)
    m = d.device("M1", "DEMO-MOTOR-4KW")
    cable = d.cable("W11", "DEMO-CBL-4G1.5", length_m=25)
    d.series(strip.out, cable, m.motor, wire=2.5)
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, "demo-mini-mcc", cover=tmp_path / "c.md"))


def test_a_motor_outside_the_cabinet_is_drawn_on_a_printed_page(tmp_path: Path) -> None:
    model = _build(tmp_path).model
    pages = layout_of(model, Page).values()
    drawn = {p.drawing_set for p in pages}
    printed = {s.id for s in printed_drawing_sets(model)}
    unprinted = [s.number for s in layout_of(model, DrawingSet).values() if s.id in drawn - printed]
    assert unprinted == [], f"drawing sets with a page that no document prints: {unprinted}"


def test_the_fed_motor_gives_no_unprinted_set_warning(tmp_path: Path) -> None:
    findings = _build(tmp_path).findings
    assert [f.code for f in findings if f.code == "UNPRINTED_SET"] == []


def test_a_motor_no_unit_feeds_gives_the_unprinted_set_error(tmp_path: Path) -> None:
    d = fr.design("demo_parts", place="PLANT")
    d.location("PLANT", "Plant room")
    d.location("FIELD", "Field")
    strip = d.add(_cabinet, "U1", place=None)
    m = d.device("M1", "DEMO-MOTOR-4KW")
    d.series(strip.out, d.cable("W11", "DEMO-CBL-4G1.5", length_m=25), m.motor, wire=2.5)
    a = d.device("M2", "DEMO-MOTOR-4KW", place="FIELD")
    b = d.device("M3", "DEMO-MOTOR-4KW", place="FIELD")
    d.series(a.motor, d.cable("W12", "DEMO-CBL-4G1.5", length_m=5), b.motor, wire=2.5)
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, fr.document(preset, "demo-mini-mcc", cover=tmp_path / "c.md"))
    expect_codes(result, "UNPRINTED_SET")
    (found,) = [f for f in result.findings if f.code == "UNPRINTED_SET"]
    assert found.severity is fr.Severity.ERROR
    assert "M2" in found.message
    assert "Add a document for" in found.message


def test_a_bundled_motor_cable_cut_at_the_cabinet_boundary_draws_its_leads_to_the_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KI-132 class D (R1700): each of the cable's three stubs stands on a terminal pin whose other pin a lead reaches, so no stub floats."""
    caught: list[Any] = []
    original = lay_out_core.drawn_netlist
    monkeypatch.setattr(lay_out_core, "drawn_netlist", lambda *a: caught.append(original(*a)) or caught[-1])

    @fr.unit("demo-feeder", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def feeder(c: fr.Design) -> _Io:
        with c.function("INC", "Incomer"):
            x0 = c.terminal_strip("X0", "DEMO-TB-2.5", 4, pe="DEMO-TB-PE-2.5")
            bus = c.ac_supply("400V", 230, x0[1], x0[2], x0[3], n=x0[4])
        with c.function("M1", "Feeder 1"):
            x = c.terminal_strip("X1", "DEMO-TB-2.5", 3, pe="DEMO-TB-PE-2.5", interface=True)
            f, q = c.device("F11", "DEMO-MCB-3P"), c.device("Q11", "DEMO-CTR-3P-NC")
            c.series(bus, f.element, q.main, c.device("B11", "DEMO-OVERLOAD-3P").main, x, wire=2.5)
            c.earth(x.run("PE", 1)[1])
        return _Io(x)

    d = fr.design("demo_parts", place="PLANT")
    d.location("PLANT", "Plant room")
    strip = d.add(feeder, "U1", place=None)
    with d.function("M1", "Motor 1"):
        d.series(strip.out, d.cable("W11", "DEMO-CBL-4G1.5", length_m=25), d.device("M1", "DEMO-MOTOR-4KW").motor, wire=2.5)
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-feeder", cover=tmp_path / "c.md"))
    floating, stubs = [], 0
    for part in caught[-1].pages.values():
        ends = {p for w in part.drawing.wires for p in (w.points[0], w.points[-1])}
        joined = {
            p
            for s in part.drawing.symbols
            if not is_marker(s) and any(part.ports.get(q) in ends for q in s.ports)
            for q in s.ports
            if (p := part.ports.get(q))
        }
        floating += [(s.x, s.y) for s in part.drawing.symbols if is_marker(s) and (s.x, s.y) not in ends | joined]
        stubs += sum(is_marker(s) for s in part.drawing.symbols)
    assert stubs == 3
    assert floating == []


def test_a_marker_with_no_wire_reaching_it_is_no_node_of_the_drawn_netlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R820, R1029: a marker's own port point is a node only where a drawn wire reaches it or it stands on a port of its symbol."""
    caught: list[Any] = []
    original = lay_out_core.drawn_netlist
    monkeypatch.setattr(lay_out_core, "drawn_netlist", lambda *a: caught.append(a) or original(*a))
    _build(tmp_path)
    model, kit, drawings, links, library = caught[-1]
    bare = {page: replace(drawing, wires=()) for page, drawing in drawings.items()}
    net = drawn_netlist(model, kit, bare, links, library)
    assert any(is_marker(s) for part in net.pages.values() for s in part.drawing.symbols)
    on_pin = {
        s.id.rpartition(":")[2]
        for part in net.pages.values()
        for s in part.drawing.symbols
        if is_marker(s) and (s.x, s.y) in set(part.ports.values())
    }
    assert {key for key, node in net.markers.items() if node is not None} <= on_pin
