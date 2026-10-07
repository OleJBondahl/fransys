"""D10 (layout deep dive): a connector mated across a location gets the harness's off stub.

The unit's boundary connector X1 (4 pins) is mated by a bare Mate to the plug P1 of the top-level
harness -W3. The harness's core runs plug to plug, both plugs in the location +EXT, and P2 is mated
to K1's port, also in +EXT. No conductor crosses a location; the MATE from X1 to P1 does. D10's
worked example is "-W3 <- +EXT-K1:1 2 3 4" on X1's pins, one box for the run, its text produced by
`fransys_model.derive.drawing_text` (`stub_far_end`, `off_stub_line`, `off_stub_text`) and never
built in `read/`.

The connector is a 4-pin part written into a throwaway copy of `examples/demo-parts` in `tmp_path`
(the demo library has only a 2-pin connector, and the demo cable has 4 cores, so 4 pins is the
smallest shape with N >= 3 whose every pin can carry a core). The control is the existing
`test_unit_boundary_off_stub` fixture, where the plug is at the cabinet's location and a conductor
does cross: its stubs stay, once each.

Base state: the first three tests fail (no OFF marker on X1's pins); the control passes.
"""

import importlib.util
import shutil
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document

from fransys_model.derive import item_designation
from fransys_model.derive.drawing_text import off_stub_line, off_stub_text, stub_far_end
from fransys_model.layout import DrawingSet, LinkMarker, Page, Side, StarKind, layout_of
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Mate stub",
    "number": "P-1010",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
_PINS = 4
_CONNECTOR_4P = (
    """schema = 1

[part]
mpn = "DEMO-CONN-4P"
manufacturer = "Demo"
description = "Connector housing, 4-pin header"
category = "connector"
class_code = "J"

[[function]]
name = "x1"
kind = "connector"
ports = [
"""
    + "".join(f'    {{ name = "{n}", role = "generic" }},\n' for n in range(1, _PINS + 1))
    + """]

[function.connector]
style = "header-2p"
pincount = 4
gender = "male"
"""
)


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    """Unit boundary X1 mated to P1, core P1 to P2, P2 mated to K1; P1, P2, K1 all in +EXT."""
    root = tmp_path_factory.mktemp("lib") / "demo_parts"
    with as_file(files("demo_parts")) as demo_parts:
        shutil.copytree(demo_parts, root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (root / "parts" / "connector-header-4p.toml").write_text(_CONNECTOR_4P, encoding="utf-8")
    parts = fransys_parts.load_path(root)
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    x1 = u.item("DEMO-CONN-4P", tag="X1", at=c1, group=u.group("NET", "Network"))
    u.boundary(x1)
    ext, group = d.location("EXT", "External"), d.group("NET", "Network")
    w3 = d.harness(name="w3", tag="W3", at=ext, group=group)
    p1 = d.item("DEMO-CONN-4P", tag="P1", parent=w3, at=ext, group=group)
    p2 = d.item("DEMO-CONN-4P", tag="P2", parent=w3, at=ext, group=group)
    cable = d.cable("DEMO-CBL-4G1.5", name="w3c", parent=w3, at=ext)
    for core in range(1, _PINS + 1):
        cable.core(core, p1[str(core)], p2[str(core)])
    k1 = d.item("DEMO-CONN-4P", tag="K1", at=ext, group=group)
    d.mate(p1, x1)
    d.mate(p2, k1)
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _in_unit_set(model, marker) -> bool:
    page = layout_of(model, Page)[marker.page]
    return layout_of(model, DrawingSet)[page.drawing_set].unit is not None


def _item_tag(model, port) -> str | None:
    """The authored tag of the item that owns `port`."""
    return item_designation(model, functions(model)[ports(model)[port].function].item)


def _x1_stubs(model):
    """The OFF markers on the cabinet page whose port is a pin of X1."""
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.star is StarKind.OFF and _in_unit_set(model, m) and _item_tag(model, m.port) == "X1"
    ]


def test_the_connectors_pins_each_carry_an_off_stub_ending_on_one_box(model) -> None:
    """Every pin of the mated connector has an OFF stub, and all end on one box (one D10 run)."""
    # UNDO: stages/offstubs.py: `mate_stub` returns None (the mate
    #   that crosses the location gives no stub: the base, no OFF marker on X1's pins)
    stubs = _x1_stubs(model)
    assert {ports(model)[m.port].name for m in stubs} == {str(n) for n in range(1, _PINS + 1)}
    assert len(stubs) == _PINS
    assert all(m.box_x is not None for m in stubs)
    assert len({(m.page, m.box_x, m.y) for m in stubs}) == 1


def test_the_stub_text_is_the_worked_example_from_the_derive_function(model) -> None:
    """D10: "-W3 <- +EXT-K1:1 2 3 4", from `off_stub_line`/`stub_far_end`, facing north (`<-`)."""
    # UNDO: stages/offstubs.py: as the first test (no OFF marker)
    stubs = _x1_stubs(model)
    assert len(stubs) == _PINS
    assert {m.facing for m in stubs} == {Side.N}
    head = stub_far_end(model, stubs[0].far)[0]
    tails = [
        stub_far_end(model, far)[1] for far in sorted({m.far for m in stubs}, key=_far_pin(model))
    ]
    expected = off_stub_line("-W3", north=True, far=head, ports=tails)
    assert head == "+EXT-K1"  # the worked example's far device, not only self-consistent
    assert expected == "-W3 \N{LEFTWARDS ARROW} +EXT-K1:" + " ".join(map(str, range(1, _PINS + 1)))
    assert {off_stub_text(model, m) for m in stubs} == {expected} == {"-W3 ← +EXT-K1:1 2 3 4"}


def _far_pin(model):
    """Sort key: the pin number of a far port."""
    return lambda far: int(ports(model)[far].name)


def test_the_stub_names_the_harness_as_carrier_and_the_far_device_port(model) -> None:
    """F1 fields: `carrier` is the harness -W3, `far` the K1 port of the same pin number."""
    # UNDO: stages/offstubs.py: as the first test (no OFF marker)
    stubs = _x1_stubs(model)
    assert len(stubs) == _PINS
    for m in stubs:
        assert m.carrier is not None
        assert item_designation(model, m.carrier) == "W3"
        assert m.far is not None
        assert _item_tag(model, m.far) == "K1"
        assert ports(model)[m.far].name == ports(model)[m.port].name


def _load(name: str):
    """A sibling root test module, loaded by path (root tests are not a package)."""
    spec = importlib.util.spec_from_file_location(name[:-3], Path(__file__).with_name(name))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_conductor_that_crosses_the_location_still_gives_its_stub_once() -> None:
    """Control: the plug at the cabinet's location, the conductor crossing: one stub per X1 pin."""
    # UNDO: engines/schematic/read/offstubs.py: `boundary_offs` skips every pair (a
    #   `continue` at the top of its loop): the pins carry no stub. A fix that also stubs the mate
    #   would give each pin two stubs and fail the `len({m.port ...})` line
    built = _load("test_unit_boundary_off_stub.py")._build().model
    stubs = _x1_stubs(built)
    assert sorted(ports(built)[m.port].name for m in stubs) == ["1", "2"]
    assert len({m.port for m in stubs}) == len(stubs)
    head = stub_far_end(built, stubs[0].far)[0]
    tails = [stub_far_end(built, m.far)[1] for m in sorted(stubs, key=lambda m: m.x)]
    assert {off_stub_text(built, m) for m in stubs} == {
        off_stub_line("-W3", north=True, far=head, ports=tails)
    }
