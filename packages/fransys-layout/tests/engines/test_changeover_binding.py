"""CONTACT-STATES CS3, Acceptance 4 (binding half): a changeover is bound by its throw roles.

Three invented relays differ only in the names of the changeover's ports: `11/12/14`,
`COM/NC/NO` and `I/II/III`, each with roles `common`/`break`/`make` and no `symbol_port`. Each
is built through the whole pipeline with the same wiring, so the drawn symbol and the routes
to its ports must match role for role. The parts are written to a temporary library.
"""

from typing import TYPE_CHECKING

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document
from workspace_root import WORKSPACE_ROOT

from fransys_model.layout import Route, SymbolPlacement, layout_of
from fransys_model.vocab.tables import ports

if TYPE_CHECKING:
    from pathlib import Path

_DEMO_TERMINAL = (
    WORKSPACE_ROOT
    / "examples"
    / "demo-parts"
    / "demo_parts"
    / "parts"
    / "terminal-feedthrough-2_5.toml"
)
_LIBRARY = 'schema = 1\nname = "bind-parts"\nversion = "0.1.0"\ndescription = "Invented."\n'
_RELAY = """schema = 1

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
    (tmp_path / "parts" / "terminal.toml").write_text(
        _DEMO_TERMINAL.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "parts" / "relay.toml").write_text(
        _RELAY.format(com=com, brk=brk, make=make), encoding="utf-8"
    )
    parts = fransys_parts.load_path(tmp_path)
    d = fransys_author.Design(parts)
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
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def _drawn(model, names: tuple[str, str, str]):
    """The changeover's symbol and turn, and where each of its ports is reached.

    A port's anchor is the end of its route at that port, relative to the symbol's origin (a
    longer port name can shift the column). The middle of a route is the router's, not the
    binding's, so it is left out.
    """
    by_name = dict(zip(names, ("common", "break", "make"), strict=True))
    role_of = {
        port.id: by_name[port.name] for port in ports(model).values() if port.name in by_name
    }
    (placement,) = (
        p for p in layout_of(model, SymbolPlacement).values() if p.symbol == "change-over-contact"
    )
    anchors: dict[str, set[tuple[int, int]]] = {role: set() for role in by_name.values()}
    for route in layout_of(model, Route).values():
        for end, point in ((route.a, route.points[0]), (route.b, route.points[-1])):
            if end in role_of:
                anchors[role_of[end]].add((point.x - placement.x, point.y - placement.y))
    return placement.symbol, placement.orientation, anchors


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


_TWO_CO = """schema = 1

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
    (tmp_path / "parts" / "terminal.toml").write_text(
        _DEMO_TERMINAL.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "parts" / "switch.toml").write_text(_TWO_CO, encoding="utf-8")
    parts = fransys_parts.load_path(tmp_path)
    d = fransys_author.Design(parts)
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
    model = fr.build(parts, d.draft(), layout_trigger_document()).model
    symbols = [p.symbol for p in layout_of(model, SymbolPlacement).values()]
    assert symbols.count("change-over-contact") == 2
