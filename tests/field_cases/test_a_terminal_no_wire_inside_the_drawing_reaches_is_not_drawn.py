"""Field case: a nested unit's strip X1, a top-level interface X4 and a bridged strip X5; the bug drew X1 with nothing to wire it (layout-0202).
Amended by layout-0463 (R937): a wire from another set reaches a terminal through its cut, so the unit's set draws it with the cut's reference.
"""

import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest

from fransys_model import derive
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.tables import functions

_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01"}


class _Strip(NamedTuple):
    X1: Any


class _Lamp(NamedTuple):
    H1: Any


class _Box(NamedTuple):
    X4: Any


@fr.unit("demo-idle-inner", text="x", by="AB", **_REL)
def _inner(u: Any) -> _Strip:
    run = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True).run("SIG", 1)
    x2 = u.terminal_strip("X2", "DEMO-TB-2.5")
    lamp = u.device("P1", "DEMO-LAMP-24")
    u.series(lamp.lamp["1"], x2.run("A", 1)[1].inner, wire=("WH", 0.75))
    u.series(lamp.lamp["2"], x2.run("0V", 1)[1].inner, wire=("WH", 0.75))
    return _Strip(run)


@fr.unit("demo-idle-outer", text="x", by="AB", **_REL)
def _outer(u: Any) -> _Lamp:
    inner = u.add(_inner, "U2")
    h1 = u.device("H1", "DEMO-LAMP-24")
    x3 = u.terminal_strip("X3", "DEMO-TB-2.5")
    u.series(h1.lamp["1"], inner.X1[1].outer, wire=("WH", 0.75))
    u.series(h1.lamp["2"], x3.run("0V", 1)[1].inner, wire=("WH", 0.75))
    return _Lamp(h1)


@fr.unit("demo-idle-box", text="x", by="AB", **_REL)
def _box(u: Any) -> _Box:
    run = u.terminal_strip("X4", "DEMO-TB-2.5", interface=True).run("SIG", 1)
    bridged = u.terminal_strip("X5", "DEMO-TB-2.5").run("B", 3, bridged=True)
    lamp = u.device("P2", "DEMO-LAMP-24")
    x6 = u.terminal_strip("X6", "DEMO-TB-2.5")
    u.series(lamp.lamp["1"], bridged[1].inner, wire=("WH", 0.75))
    u.series(lamp.lamp["2"], x6.run("0V", 1)[1].inner, wire=("WH", 0.75))
    return _Box(run)


class _Written(NamedTuple):
    model: Any
    texts: dict[str, list[str]]


@pytest.fixture(scope="module")
def written() -> _Written:
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts")
    d.location("C1", "Cabinet")
    d.add(_outer, "U1")
    box = d.add(_box, "U3", place="C1")
    outside = d.device("H9", "DEMO-LAMP-24", place="C1")
    ret = d.terminal_strip("X9", "DEMO-TB-2.5", place="C1")
    d.series(outside.lamp["1"], box.X4[1].outer, wire=("WH", 0.75))
    d.series(outside.lamp["2"], ret.run("0V", 1)[1].inner, wire=("WH", 0.75))
    names = ("demo-idle-outer", "demo-idle-inner", "demo-idle-box")
    docs = []
    for name in names:
        (root / f"{name}.md").write_text("# x\n", encoding="utf-8")
        docs.append(fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, name, cover=root / f"{name}.md"))
    result = fr.build(d, *docs)
    assert [f for f in result.findings if f.severity.name == "ERROR"] == []
    fr.write(result, root / "out", intermediates=root / "inter")
    model = result.model
    by_name = {derive.unit_release(model, u).name: u for u in derive.units(model)}
    sets = layout_of(model, DrawingSet)
    texts: dict[str, list[str]] = {name: [] for name in names}
    for page in layout_of(model, Page).values():
        svg = (root / "inter" / f"layout.page-{page.id.value}.svg").read_text("utf-8")
        for name in names:
            if sets[page.drawing_set].unit == by_name[name]:
                texts[name] += re.findall(r">([^<>]+)</text>", svg)
    return _Written(model, texts)


def _rows(model: Any, designation: str) -> int:
    (strip,) = [s for s in derive.terminal_strips(model) if derive.item_designation(model, s).endswith(designation)]
    return len(derive.terminal_rows(model, strip))


def test_a_nested_units_strip_only_the_parent_wires_is_not_drawn_on_its_own_pages(
    written: _Written,
) -> None:
    inner = written.texts["demo-idle-inner"]
    assert "-X1:SIG:1" in inner  # drawn with its cut's reference (R937): a terminal alone prints its full tag (STRIP-TAG-ONCE)
    assert "-X2:A:1" in inner
    assert "-U2-X1:SIG:1" in written.texts["demo-idle-outer"]


def test_a_top_level_units_terminal_wired_from_outside_stays_with_its_stub(
    written: _Written,
) -> None:
    texts = written.texts["demo-idle-box"]
    assert "-X4:SIG:1" in texts
    assert any("H9" in t for t in texts)


def test_a_bridged_terminal_is_no_wire(written: _Written) -> None:
    texts = written.texts["demo-idle-box"]
    assert "-X5:B:1" in texts
    assert not {"-X5:B:2", "-X5:B:3"} & set(texts)


def test_each_terminal_table_lists_every_terminal_of_its_strip(written: _Written) -> None:
    model = written.model
    assert (_rows(model, "X1"), _rows(model, "X4"), _rows(model, "X5")) == (1, 1, 3)


def _reached(model: Any, designation: str) -> list[bool]:
    """`function_is_reached` for each terminal of the strip, in row order."""
    (strip,) = [s for s in derive.terminal_strips(model) if derive.item_designation(model, s).endswith(designation)]
    by_item = {f.item: f.id for f in functions(model).values()}
    return [derive.function_is_reached(model, by_item[row.terminal]) for row in derive.terminal_rows(model, strip)]


def test_the_one_fact_reads_the_three_shapes(written: _Written) -> None:
    """Nested: the parent's wire counts, through its cut (R937). Top-level: the leaving wire does. A bridge: no."""
    model = written.model
    assert _reached(model, "X1") == [True]
    assert _reached(model, "X4") == [True]
    assert _reached(model, "X5") == [True, False, False]
