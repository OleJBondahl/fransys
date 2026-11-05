"""Field case: a connector table accounts for every pin, as a terminal table does (L18).
The bug: CONNECTOR_LIST knew only a board's connectors, so a unit's document printed no table and a pin off the drawing was listed nowhere.
Fixed by pdf-0030 (owner 2026-10-13), CONNECTOR_LIST prints one table per connector with a row per pin, whatever the drawing shows."""

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
    u.series(j1[1], lamp["1"], wire=(BK, 0.5))
    u.series(j1[2], lamp["2"], wire=(BK, 0.5))
    psu = u.device("T1", "DEMO-PSU-24")
    u.dc_supply("S", psu)
    u.series(j1[3], psu.output["+"], wire=(BK, 0.5))
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
    return next((root / "inter").glob("*.typ")).read_text(encoding="utf-8")


def test_the_connector_table_lists_every_pin_with_its_ends(tmp_path: Path) -> None:
    """The table is headed `-J1`; pin 4 (no wire) is a row; pin 3 shows its wire's far end."""
    source = _source(tmp_path)
    assert 'strong(text("Pin"))' in source
    assert '#heading(level: 2, text("-J1"))' in source
    table = source[source.index('strong(text("Pin"))') :].split("\n]", 1)[0]
    assert 'text("1"), box(text("-H1:1"))' in table
    assert 'text("3"), box(text("-T1:+"))' in table  # the wire's far end
    assert 'text("4"), text("")' in table  # no wire: an empty Ends cell


# -- L7, the connector half: a top-level unit's interface connector `J8`, wired only outside the unit, keeps its pin stub (layout-0080) --


class _J8(NamedTuple):
    J8: Any


@fr.unit("demo-conn-box", text="x", by="AB", **_REL)
def _box(u: Any) -> _J8:
    j8 = u.device("J8", "DEMO-CONN-2P", interface=True)
    lamp = u.device("P2", "DEMO-LAMP-24")
    u.series(j8["2"], lamp.lamp["1"], wire=(BK, 0.5))
    u.series(u.terminal_strip("X1", "DEMO-TB-2.5")[1].inner, lamp.lamp["2"], wire=(BK, 0.5))
    return _J8(j8)


@pytest.fixture(scope="module")
def texts() -> dict[str, list[str]]:
    """The drawn texts of each unit's own pages."""
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts")
    cabinet = d.location("C1", "Cabinet")
    box = d.add(_box, "U3", place="C1")
    outside = d.device("H9", "DEMO-LAMP-24", place="C1")
    d.series(outside.lamp["1"], box.J8["1"], wire=(BK, 0.5))
    d.series(d.terminal_strip("X9", "DEMO-TB-2.5", place="C1")[1].inner, outside.lamp["2"], wire=(BK, 0.5))
    names = ("demo-conn-box",)
    docs = []
    for name in names:
        (root / f"{name}.md").write_text("# x\n", encoding="utf-8")
        docs.append(fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, name, cover=root / f"{name}.md"))
    (root / "cabinet.md").write_text("# x\n", encoding="utf-8")
    cover = root / "cabinet.md"
    docs.append(fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=cover))
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


def test_a_top_level_units_pin_wired_from_outside_stays_with_its_stub(
    texts: dict[str, list[str]],
) -> None:
    assert any(t.startswith("-J8:1") for t in texts["demo-conn-box"])
    assert any("H9" in t for t in texts["demo-conn-box"])
