"""F1 part 3d (D13): an off stub stores its far port, carrier and facing and no text; the text
derived from them (`off_stub_text`) equals the text layout MEASURED the stub's box from (the stage
marker's `.text`) for every stub of every fixture. The text a stub's box was sized from is the
text render prints.

The fixtures are the ones the D10 and W3 stub tests build (a cabinet unit whose boundary plug
mates a harness, the two-cabinet system, two boundary connectors with and without a foreign
column between, a top-level cable between two locations), the same two plugs wired by plain
wires, and the layout cabinet with a second location. `off_ends` is checked by hand-built pairs
of one text. A line's one stub (HL1, HL18) stores no text: its box is checked against its derived
text's measure (`stub_size`), the plain wires keep a shared-box run without a carrier.

Can-fail, checked by hand: with `write/markers.py` writing no `carrier` the equality test fails on
the cable segment; with `facing` always `Side.S` it fails on the arrow of an N-facing stub.
"""

import dataclasses
import importlib.util
from functools import cache

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document
from layout_cabinet import build_cabinet
from workspace_root import WORKSPACE_ROOT

from fransys_layout.engines import lay_out_schematic
from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import LayoutError
from fransys_layout.stages.offstubs import off_ends
from fransys_layout.stages.references.marker_boxes import stub_size
from fransys_model.derive.drawing_text import off_stub_text
from fransys_model.kernel import freeze
from fransys_model.layout import DrawingSet, LinkMarker, Page, Side, StarKind, layout_of
from fransys_model.vocab.tables import functions, items, ports

_ROOT_TESTS = WORKSPACE_ROOT / "tests"


def _load(name: str):
    """A root test module, loaded by path (root tests are not a package)."""
    spec = importlib.util.spec_from_file_location(name[:-3], _ROOT_TESTS / name)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_UNITS = _load("test_dd_units_stubs.py")


@cache
def _unit_stub():
    return _UNITS._off_stub_model()


@cache
def _system():
    return _UNITS._system_model()


@cache
def _connectors(*, relay_between: bool):
    return _UNITS._build_two_connectors(relay_between=relay_between)


@cache
def _cable():
    return _UNITS._two_location_cable_model()


@cache
def _wires():
    """The top-level cable's two plugs, wired by two plain wires: no line, no carrier."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_UNITS._OFF_STUB._PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    a, b = d.location("A", "Cabinet"), d.location("B", "Field")
    group = d.group("G", "Pump")
    p1 = d.item("DEMO-CONN-2P", tag="P1", at=a, group=group)
    p2 = d.item("DEMO-CONN-2P", tag="P2", at=b, group=group)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(p1["1"], p2["1"])
    wire(p1["2"], p2["2"])
    return fr.build(parts, d.draft(), layout_trigger_document()).model


@cache
def _cabinet_two_location():
    return lay_out_schematic(freeze(build_cabinet(second_location=True)))[0]


_FIXTURES = {
    "unit-stub": _unit_stub,
    "system": _system,
    "two-connectors": lambda: _connectors(relay_between=False),
    "two-connectors-relay": lambda: _connectors(relay_between=True),
    "top-level-cable": _cable,
    "top-level-wires": _wires,
    "cabinet-two-location": _cabinet_two_location,
}


def _line_stub(marker: LinkMarker) -> bool:
    """HL18: a leaving line's one stub, keyed `line_stub` (write/harness.py)."""
    return marker.key[3] == "line_stub"


def _stubs(model) -> list[LinkMarker]:
    return [m for m in layout_of(model, LinkMarker).values() if m.star is StarKind.OFF]


def _in_unit_set(model, marker) -> bool:
    page = layout_of(model, Page)[marker.page]
    return layout_of(model, DrawingSet)[page.drawing_set].unit is not None


def _run_size(model, marker) -> int:
    """The stubs one shared box serves: the same page, `box_x` and `y`; 1 for a box of its own."""
    if marker.box_x is None:
        return 1
    return sum(
        1
        for other in _stubs(model)
        if (other.page, other.box_x, other.y) == (marker.page, marker.box_x, marker.y)
    )


@pytest.mark.parametrize("name", list(_FIXTURES))
def test_the_derived_stub_text_equals_the_measured_text(name: str) -> None:
    model = _FIXTURES[name]()
    stubs = _stubs(model)
    assert stubs, "the fixture draws no off stub"
    inputs = read_inputs(model)
    results, _ = stage_results(model, inputs)
    measured = {
        (one.port, one.at.x, one.at.y): one.text
        for one in results.layout.markers
        if one.text  # an off stub, or (D9, F7) the reference that carries one
    }
    boxes = {
        (one.port, one.at.x, one.at.y): (one.box.width, one.box.height)
        for one in results.lines.stubs
    }
    assert len(measured) + len(boxes) == len(stubs)
    for marker in stubs:
        text = off_stub_text(model, marker)
        if _line_stub(marker):
            assert stub_size(text, inputs.profile) == boxes[marker.port, marker.x, marker.y]
            assert marker.far != marker.port
        else:
            assert text == measured[marker.port, marker.x, marker.y]
        assert not marker.ext


def test_the_fixtures_cover_every_shape_of_stub() -> None:
    """A shared-box run, a lone stub, a stand-in, no carrier and each facing all occur."""
    shapes: set[str] = set()
    for build in _FIXTURES.values():
        model = build()
        for marker in _stubs(model):
            shapes.add("run" if _run_size(model, marker) > 1 else "single")
            shapes.add("stand-in" if _in_unit_set(model, marker) else "top-level")
            shapes.add("no-carrier" if marker.carrier is None else "carrier")
            assert marker.facing is not None
            shapes.add(f"facing-{marker.facing.value}")
    wanted = {
        "run",
        "single",
        "stand-in",
        "top-level",
        "carrier",
        "no-carrier",
        "facing-n",
        "facing-s",
    }
    assert wanted <= shapes
    print("shapes covered:", sorted(shapes))  # noqa: T201 -- prints the covered shapes for a `-s` run


@pytest.mark.parametrize("name", list(_FIXTURES))
def test_far_and_carrier_are_records_of_the_model(name: str) -> None:
    model = _FIXTURES[name]()
    for marker in _stubs(model):
        assert marker.far in ports(model)
        assert marker.carrier is None or marker.carrier in items(model)
        assert isinstance(marker.facing, Side)


def test_a_stand_in_stub_carries_its_mates_far_end_and_carrier() -> None:
    """The unit's boundary X1 reads the parent's stub at X1: the same far port and carrier.

    HL18: W3 is a line, so each side's one stub stands at the connector it mates, X1.
    """
    model = _unit_stub()
    top = {ports(model)[m.port].function: m for m in _stubs(model) if not _in_unit_set(model, m)}
    stand_ins = [m for m in _stubs(model) if _in_unit_set(model, m)]
    assert stand_ins
    for marker in stand_ins:
        mate = top[ports(model)[marker.port].function]
        assert (marker.far, marker.carrier) == (mate.far, mate.carrier)
        assert marker.far != marker.port
    assert {functions(model)[ports(model)[m.port].function].key[:2] for m in stand_ins} == {
        ("cab", "X1")
    }


def _inputs_with(*, far_differs: bool):
    """The two-location cabinet's inputs plus a second `OffEnd` of its first end's text."""
    inputs = read_inputs(freeze(build_cabinet(second_location=True)))
    first = inputs.off_ends[0]
    other = next(end.far for end in inputs.off_ends if end.far != first.far)
    twin = dataclasses.replace(first, far=other if far_differs else first.far)
    return dataclasses.replace(inputs, off_ends=(*inputs.off_ends, twin))


def _ends(inputs):
    """The stage's `off_ends` over `inputs`' ends and texts (what `stage_results` passes)."""
    return off_ends(inputs.off_ends, inputs.off_texts)


def test_one_stub_text_naming_two_far_ends_is_refused() -> None:
    with pytest.raises(LayoutError, match="two different"):
        _ends(_inputs_with(far_differs=True))


def test_one_stub_text_naming_one_far_end_twice_is_kept() -> None:
    inputs = _inputs_with(far_differs=False)
    assert {end.port for end in _ends(inputs)} == {t.port for t in inputs.off_texts}
