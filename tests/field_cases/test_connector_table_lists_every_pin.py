"""Field case: a connector table accounts for every pin, as a terminal table does (L18).

The engineering shape: a cabinet unit holds a device connector `J1` of four pins, mated to a
harness plug `P5`. Pins 1 and 2 are wired to a lamp inside the unit. Pin 3 has no wire of its
own, but its mated pin is wired to the supply. Pin 4 has no wire at all.

The bug: the CONNECTOR_LIST knew only a board's connectors, so the unit's document printed no
connector table and a pin left off the drawing was listed nowhere. The rule (decision pdf-0030,
owner 2026-10-13): CONNECTOR_LIST prints one table per connector, headed by its designation, with
a row per pin (Pin, Net, Mate, Ends), whatever the drawing shows.
"""

import re
import tempfile
from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model import derive
from fransys_model.layout import DrawingSet, Page, layout_of

_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01"}


class _Open(NamedTuple):
    pass


@fr.unit("demo-conn-cab", text="first", by="AB", **_REL)
def _cab(u: Any) -> _Open:
    j1 = u.device("J1", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    lamp = u.device("H1", "DEMO-LAMP-24")
    u.wire(j1[1], lamp["1"], wire=(BK, 0.5))
    u.wire(j1[2], lamp["2"], wire=(BK, 0.5))
    psu = u.device("T1", "DEMO-PSU-24")
    u.dc_supply("S", psu)
    harness = u.harness("W5")
    plug = u.device("P5", "DEMO-HSG-4M", parent=harness, contacts="DEMO-CRIMP-M")
    u.mate(plug, j1)
    u.wire(plug[3], psu.output["+"], wire=(BK, 0.5))
    return _Open()


def _source(root: Path) -> str:
    """The typst source of the unit's document with the connector list added."""
    d = fr.design("demo_parts")
    d.add(_cab, "C1", place=None)
    (root / "cab.md").write_text("# cab\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC,
        "demo-conn-cab",
        cover=root / "cab.md",
    )
    fr.write(fr.build(d, document), root / "out", intermediates=root / "inter")
    return (root / "inter" / "cab.typ").read_text(encoding="utf-8")


def test_the_connector_table_lists_every_pin_with_its_ends(tmp_path: Path) -> None:
    """The table is headed `-J1`; pin 4 (no wire) is a row; pin 3 shows its mate's far end."""
    source = _source(tmp_path)
    assert 'strong(text("Pin"))' in source
    assert '#heading(level: 2, text("-J1"))' in source
    table = source[source.index('strong(text("Pin"))') :].split("\n]", 1)[0]
    assert 'text("1"), text("-W5-P5:1"), box(text("-H1:1"))' in table
    assert 'text("3"), text("-W5-P5:3"), box(text("-T1:+"))' in table  # the mate's wire
    assert 'text("4"), text("-W5-P5:4"), text("")' in table  # no wire: an empty Ends cell


# -- L7, the connector half: a pin no wire inside the drawing reaches is not drawn (layout-0197) --
#
# The shape: a nested unit hands its connector `J7` up as its interface; only the parent wires pin
# 1, and a lamp inside the unit is wired to pin 2. A top-level unit's interface connector `J8` is
# wired only to a device outside the unit. The nested unit's own pages draw pin 2 and not pin 1;
# the parent's black box draws pin 1; the top-level unit's pin keeps its stub (layout-0080).


class _J7(NamedTuple):
    J7: Any


class _J8(NamedTuple):
    J8: Any


@fr.unit("demo-conn-inner", text="x", by="AB", **_REL)
def _inner(u: Any) -> _J7:
    j7 = u.device("J7", "DEMO-CONN-2P", interface=True)
    lamp = u.device("P1", "DEMO-LAMP-24")
    u.wire(j7["2"], lamp.lamp["1"], wire=(BK, 0.5))
    return _J7(j7)


@fr.unit("demo-conn-outer", text="x", by="AB", **_REL)
def _outer(u: Any) -> _Open:
    inner = u.add(_inner, "U2")
    h1 = u.device("H1", "DEMO-LAMP-24")
    u.wire(h1.lamp["1"], inner.J7["1"], wire=(BK, 0.5))
    return _Open()


@fr.unit("demo-conn-box", text="x", by="AB", **_REL)
def _box(u: Any) -> _J8:
    j8 = u.device("J8", "DEMO-CONN-2P", interface=True)
    lamp = u.device("P2", "DEMO-LAMP-24")
    u.wire(j8["2"], lamp.lamp["1"], wire=(BK, 0.5))
    return _J8(j8)


@pytest.fixture(scope="module")
def texts() -> dict[str, list[str]]:
    """The drawn texts of each unit's own pages."""
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    d.add(_outer, "U1")
    box = d.add(_box, "U3", place="C1")
    outside = d.device("H9", "DEMO-LAMP-24", place="C1")
    d.wire(outside.lamp["1"], box.J8["1"], wire=(BK, 0.5))
    names = ("demo-conn-outer", "demo-conn-inner", "demo-conn-box")
    docs = []
    for name in names:
        (root / f"{name}.md").write_text("# x\n", encoding="utf-8")
        docs.append(
            fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, name, cover=root / f"{name}.md")
        )
    result = fr.build(d, *docs)
    assert [f for f in result.findings if f.severity.name == "ERROR"] == []
    fr.write(result, root / "out", intermediates=root / "inter")
    model = result.model
    by_name = {derive.unit_release(model, u).name: u for u in derive.units(model)}
    sets = layout_of(model, DrawingSet)
    found: dict[str, list[str]] = {name: [] for name in names}
    for page in layout_of(model, Page).values():
        svg = (root / "inter" / f"layout.page-{page.id.value}.svg").read_text("utf-8")
        for name in names:
            if sets[page.drawing_set].unit == by_name[name]:
                found[name] += re.findall(r">([^<>]+)</text>", svg)
    return found


def test_a_nested_units_pin_only_the_parent_wires_is_not_drawn_on_its_own_pages(
    texts: dict[str, list[str]],
) -> None:
    assert [t for t in texts["demo-conn-inner"] if t.startswith("-J7:1")] == []
    assert any(t.startswith("-J7:2") for t in texts["demo-conn-inner"])
    assert any(t.startswith("-U2-J7:1") for t in texts["demo-conn-outer"])


def test_a_top_level_units_pin_wired_from_outside_stays_with_its_stub(
    texts: dict[str, list[str]],
) -> None:
    assert any(t.startswith("-J8:1") for t in texts["demo-conn-box"])
    assert any("H9" in t for t in texts["demo-conn-box"])
