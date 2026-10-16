"""The symbol set's generic gates are one `symdef.check` call; the electrical-only gates follow."""

import json
import shutil
from pathlib import Path

import pytest
from symdef import Arc, Circle, Line, Polyline, load_library
from symdef.authoring import check

from electrical_symbols import LIBRARY

ROOT = Path(__file__).parent.parent
SOURCE = load_library(ROOT)  # a broken file is a loud collection error


def numbers(library):
    return sorted(s.reference.number for s in library)


def ids(symbols):
    return [s.reference.number for s in symbols]


def test_the_symbol_set_passes_symdef_check():
    """Files load, lint clean (also repeated), the build is not stale, the bundle matches."""
    assert check(ROOT) == ()


def test_symdef_check_fails_on_a_stale_build(tmp_path):
    """The check can fail: a source symbol edited without a rebuild is reported stale."""
    for name in ("library.toml", "symbols", "build", "src"):
        source = ROOT / name
        if source.is_dir():
            shutil.copytree(source, tmp_path / name)
        else:
            shutil.copy(source, tmp_path / name)
    assert check(tmp_path) == ()
    path = tmp_path / "symbols" / "make-contact.toml"
    text = path.read_text(encoding="utf-8")
    assert "Make contact, general symbol" in text
    path.write_text(
        text.replace("Make contact, general symbol", "Make contact", 1), encoding="utf-8"
    )
    assert "stale-build" in {finding.rule for finding in check(tmp_path)}


# The terminal's four stub
# leads are bound to the port each one draws.


def test_terminal_leads_are_bound_to_their_ports():
    terminal = SOURCE.get("terminal")
    bound = {
        e.port: (e.start, e.end)
        for e in terminal.elements
        if isinstance(e, Line) and e.port is not None
    }
    assert set(bound) == {"n", "e", "s", "w"}
    positions = {port.id: port.position for port in terminal.ports}
    for port_id, (start, end) in bound.items():
        assert positions[port_id] in (start, end)


def test_the_built_terminal_json_carries_the_bindings():
    data = json.loads((ROOT / "build" / "resolved" / "terminal.json").read_text(encoding="utf-8"))
    bound = {element["port"] for element in data["elements"] if "port" in element}
    assert bound == {"n", "e", "s", "w"}


@pytest.mark.parametrize("number", ["emergency-stop", "thermal-overload", "rcd"])
def test_protection_symbols_load_with_in_and_out_ports(number):
    """Layout enters a series device at `in` and leaves at `out`, the port ids break-contact has."""
    symbol = LIBRARY.get(number)
    assert {p.id for p in symbol.ports} == {"in", "out"}
    assert any(path.through for path in symbol.paths)


OPERATED_BY_SYMBOLS = [
    "push-button-break",
    "selector-make",
    "selector-break",
    "position-switch-make",
    "position-switch-break",
]


@pytest.mark.parametrize("number", OPERATED_BY_SYMBOLS)
def test_operated_by_symbols_have_ports_and_the_actuator_on_the_left(number):
    """Each operated-by composite has `in`/`out`, a through path and drawing left of its ports."""
    symbol = LIBRARY.get(number)
    assert {p.id for p in symbol.ports} == {"in", "out"}
    assert any(path.through for path in symbol.paths)
    xs = [pt.x for e in symbol.elements if isinstance(e, (Line, Polyline)) for pt in _points(e)]
    xs += [e.center.x - e.radius for e in symbol.elements if isinstance(e, Circle)]
    assert min(xs) <= -3


@pytest.mark.parametrize("number", ["actuator-turn", "actuator-position"])
def test_new_actuator_qualifiers_are_qualifiers_with_a_link(number):
    symbol = LIBRARY.get(number)
    assert symbol.kind.value == "qualifier"
    assert [a.id for a in symbol.anchors] == ["link"]


def test_actuator_position_is_a_circle_with_no_closed_polyline():
    """D49: the limit-switch actuator is a circle at the dashed linkage's end, no triangle."""
    elements = SOURCE.get("actuator-position").elements
    assert sum(isinstance(e, Circle) for e in elements) == 1
    assert not any(isinstance(e, Polyline) and e.closed for e in elements)


def _points(element):
    return element.points if isinstance(element, Polyline) else (element.start, element.end)


def test_emergency_stop_is_the_full_symbol():
    """Head left of the ports, ring right of the break contact, latching wedge on the link.

    The head is the one Arc, the positive-opening mark the one Circle, the latching wedge
    the one Polyline that leaves the link line (y = 0).
    """
    symbol = SOURCE.get(
        "emergency-stop"
    )  # the source, which the probe patches; the bundle gate ties them
    port_x = {p.position.x for p in symbol.ports}
    arcs = [e for e in symbol.elements if isinstance(e, Arc)]
    circles = [e for e in symbol.elements if isinstance(e, Circle)]
    vees = [
        e
        for e in symbol.elements
        if isinstance(e, Polyline) and any(pt.y != 0 for pt in e.points) and e.points[0].y == 0
    ]
    assert len(arcs) == 1
    assert len(circles) == 1
    assert len(vees) == 1
    assert arcs[0].center.x < min(port_x)
    # the ring sits right of the break contact (its stop ends at x = 1.25), at the link's height
    assert circles[0].center.y == 0
    assert circles[0].center.x - circles[0].radius > 1.25
    # the wedge is on the link, between the head and the link's midpoint
    link = [
        e
        for e in symbol.elements
        if isinstance(e, Line) and e.start.y == e.end.y == 0 and max(e.start.x, e.end.x) <= 0.5
    ]
    link_xs = [pt.x for e in link for pt in (e.start, e.end)]
    midpoint = (min(link_xs) + max(link_xs)) / 2
    wedge_xs = [pt.x for pt in vees[0].points]
    assert arcs[0].center.x < min(wedge_xs)
    assert max(wedge_xs) < midpoint


def test_the_positive_opening_break_contact_is_a_break_contact_with_the_mark():
    """D50: `in`/`out` and a through path, and the mark's one circle right of the through path."""
    symbol = LIBRARY.get("break-contact-positive-opening")
    assert {p.id for p in symbol.ports} == {"in", "out"}
    assert any(path.through for path in symbol.paths)
    circles = [e for e in symbol.elements if isinstance(e, Circle)]
    assert len(circles) == 1
    assert circles[0].center.x - circles[0].radius > 0
