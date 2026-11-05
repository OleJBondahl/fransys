"""A changeover is bound by its throw roles.

Three invented relays differ only in the names of the changeover's ports: `11/12/14`,
`COM/NC/NO` and `I/II/III`, each with roles `common`/`break`/`make` and no `symbol_port`. Each
"""

from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import fransys_parts
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import WH
from fransys_author.design import Design
from fransys_el import lay_out_core
from workspace_root import WORKSPACE_ROOT

from electrical_symbols import LIBRARY
from fransys_layout.symbols import library_symbol, symbol_shape

if TYPE_CHECKING:
    from pathlib import Path

_DEMO_TERMINAL = WORKSPACE_ROOT / "examples" / "demo-parts" / "demo_parts" / "parts" / "terminal-feedthrough-2_5.toml"
_LIBRARY = 'schema = 2\nname = "bind-parts"\nversion = "0.1.0"\ndescription = "Invented."\n'
_RELAY = """schema = 2

[part]
mpn = "BIND-RLY-1CO"
manufacturer = "Demo"
description = "Relay, one changeover, 24 V DC coil"
category = "electromechanical"
class_code = "K"

[[function]]
name = "coil"
kind = "coil"
symbol = "operating-device"
ports = [
    {{ name = "A1", role = "generic", symbol_port = "in" }},
    {{ name = "A2", role = "generic", symbol_port = "out" }},
]

[[function]]
name = "co_1"
kind = "contact_co"
symbol = "change-over-contact"
ports = [
    {{ name = "{com}", role = "common" }},
    {{ name = "{brk}", role = "break" }},
    {{ name = "{make}", role = "make" }},
]
links = [
    {{ a = "{com}", b = "{brk}", kind = "switched" }},
    {{ a = "{com}", b = "{make}", kind = "switched" }},
]
"""


def _built(tmp_path: Path, names: tuple[str, str, str]):
    """K1 with a changeover whose (common, break, make) ports are `names`, wired one way."""
    com, brk, make = names
    (tmp_path / "library.toml").write_text(_LIBRARY, encoding="utf-8")
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "terminal.toml").write_text(_DEMO_TERMINAL.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "parts" / "relay.toml").write_text(_RELAY.format(com=com, brk=brk, make=make), encoding="utf-8")
    parts = fransys_parts.load_path(tmp_path)
    d = Design(parts)
    d.project(title="Bind", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-09-26", text="First issue", created="XX")
    c1, group = d.location("C1", "Cabinet"), d.group("CTL", "Control")
    strip = d.strip("X1", at=c1)
    feed, supply, zero, out1, out2 = (strip.terminal("DEMO-TB-2.5", group=group) for _ in range(5))
    k1 = d.item("BIND-RLY-1CO", tag="K1", at=c1, group=group)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(feed.inner, k1.fn("coil")["A1"])
    wire(k1.fn("coil")["A2"], zero.inner)
    wire(supply.inner, k1.fn("co_1")[com])
    wire(k1.fn("co_1")[make], out1.inner)
    wire(k1.fn("co_1")[brk], out2.inner)
    return fr.build(parts, d.draft(), cabinet_document(c1)).model


def _changeovers(model):
    """Every drawn changeover symbol with the Drawing it stands on."""
    return [(drawing, symbol) for drawing in drawn_pages(model).values() for symbol in drawing.symbols if symbol.key == "change-over-contact"]


def _drawn(model, names: tuple[str, str, str]):
    """The changeover's symbol and turn, and where each of its ports is reached.

    A role's marking is the symbol slot that names it. A port's anchor is its pin, relative to
    the symbol's origin, when a wire ends on it (a longer port name can shift the column). The
    """
    ((drawing, symbol),) = _changeovers(model)
    shape = symbol_shape(library_symbol(LIBRARY, symbol.key, symbol.poles), LIBRARY)
    slots = dict(symbol.slots)
    pins = {"common": "com", "break": "nc", "make": "no"}
    assert [slots[f"marking.{pin}"] for pin in pins.values()] == list(names)
    anchors: dict[str, set[tuple[int, int]]] = {role: set() for role in pins}
    for role, pin in pins.items():
        point = (symbol.x + shape.pins[pin].dx, symbol.y + shape.pins[pin].dy)
        if any(point in (w.points[0], w.points[-1]) for w in drawing.wires):
            anchors[role].add((point[0] - symbol.x, point[1] - symbol.y))
    return symbol.key, symbol.orient, anchors


@pytest.mark.parametrize("names", [("COM", "NC", "NO"), ("I", "II", "III")], ids=["com", "roman"])
def test_a_changeover_named_otherwise_is_drawn_as_the_digit_one(tmp_path, names) -> None:
    """Common, break and make land on the same symbol ports, so the same routes reach them."""
    digits = ("11", "12", "14")
    (tmp_path / "digits").mkdir()
    (tmp_path / "other").mkdir()
    *reference_drawn, reference = _drawn(_built(tmp_path / "digits", digits), digits)
    *drawn, points = _drawn(_built(tmp_path / "other", names), names)
    assert drawn == reference_drawn
    assert all(reference.values())
    assert points == reference


_TWO_CO = """schema = 2

[part]
mpn = "BIND-2CO"
manufacturer = "Demo"
description = "Two changeover contacts, no coil"
category = "electromechanical"
class_code = "S"

[[function]]
name = "co_1"
kind = "contact_co"
symbol = "change-over-contact"
ports = [
    { name = "11", role = "common" },
    { name = "12", role = "break" },
    { name = "14", role = "make" },
]
links = [{ a = "11", b = "12", kind = "switched" }, { a = "11", b = "14", kind = "switched" }]

[[function]]
name = "co_2"
kind = "contact_co"
symbol = "change-over-contact"
ports = [
    { name = "21", role = "common" },
    { name = "22", role = "break" },
    { name = "24", role = "make" },
]
links = [{ a = "21", b = "22", kind = "switched" }, { a = "21", b = "24", kind = "switched" }]
"""


def test_two_changeovers_of_one_item_stay_two_symbols(tmp_path) -> None:
    """Their ports all bind to `com`/`nc`/`no`, so they cannot be one item box's ports."""
    # UNDO: read/views.py:item_views, `throw_port(spec, port) or ` before `resolved[...]`
    (tmp_path / "library.toml").write_text(_LIBRARY, encoding="utf-8")
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "terminal.toml").write_text(_DEMO_TERMINAL.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "parts" / "switch.toml").write_text(_TWO_CO, encoding="utf-8")
    parts = fransys_parts.load_path(tmp_path)
    d = Design(parts)
    d.project(title="Bind", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-09-26", text="First issue", created="XX")
    c1, group = d.location("C1", "Cabinet"), d.group("CTL", "Control")
    strip = d.strip("X1", at=c1)
    terminals = [strip.terminal("DEMO-TB-2.5", group=group) for _ in range(6)]
    s1 = d.item("BIND-2CO", tag="S1", at=c1, group=group)
    wire = d.wiring(colour="BU", gauge="0.5")
    for terminal, (function, port) in zip(
        terminals,
        (
            ("co_1", "11"),
            ("co_1", "12"),
            ("co_1", "14"),
            ("co_2", "21"),
            ("co_2", "22"),
            ("co_2", "24"),
        ),
        strict=True,
    ):
        wire(terminal.inner, s1.fn(function)[port])
    model = fr.build(parts, d.draft(), cabinet_document(c1)).model
    assert len(_changeovers(model)) == 2


def test_two_contacts_with_a_wider_column_gap_are_placed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R1512: the hard order, not the trunk's side, says which side of a trunk a foreign box is pushed to; main closed a y ring here.

    The options value `column_gap_min=40` reaches the build through `lay_out_core.options`: no core entry builds this plant.
    """
    colours = (WH, 0.5)

    class Io(NamedTuple):
        pass

    @fr.unit("fc-co", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def build(d: fr.Design) -> Io:
        strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 8, external=True)
        with d.function("CTRL", "Control"):
            loads = {i: d.device(f"Y{i}", "DEMO-RLY-2CO-24") for i in (1, 2)}
            buttons = {i: d.device(f"S{i}", "DEMO-PB-NO") for i in (1, 2)}
            holds = {i: d.device(f"Q{i}", "DEMO-RLY-2CO-24") for i in (1, 2)}
            relay = d.device("K1", "DEMO-RLY-2CO-24")
            d.series(strip[1].outer, relay.coil, strip[2].outer, wire=colours)
            for i in (1, 2):
                contact = getattr(relay, f"co_{i}")
                d.series(holds[i].coil, contact.nc, buttons[i].sw, wire=colours)
                d.series(strip[5].outer, holds[i].coil, wire=colours)
                d.series(buttons[i].sw, strip[3].outer, wire=colours)
                d.series(contact.no, loads[i].coil, wire=colours)
                d.series(loads[i].coil, strip[4].outer, wire=colours)
        return Io()

    options = lay_out_core.options
    monkeypatch.setattr(lay_out_core, "options", lambda conventions, library: replace(options(conventions, library), column_gap_min=40))
    d = fr.design("demo_parts")
    d.add(build, "U1")
    (tmp_path / "cover.md").write_text("# cover\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "fc-co", cover=tmp_path / "cover.md")
    assert "PLACEMENT_PROBLEM" not in {f.code for f in fr.build(d, document).findings}
