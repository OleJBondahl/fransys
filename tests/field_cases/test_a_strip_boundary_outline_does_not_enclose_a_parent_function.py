"""Field case: a unit's boundary is a two-terminal strip or a supply's + and - outputs, with a parent lamp wired across them.
The bug: the unit's outline enclosed the parent's lamp, a function that is not the unit's, across both boundary rows.
Fixed by layout-0169, a black box never encloses a function that is not the unit's."""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_facts import box_boxes
from _drawn_pages import drawn_pages

from fransys_layout.geometry import Box, overlaps, translate

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}


class _Open(NamedTuple):
    pass


class _Strip(NamedTuple):
    X1: Any


class _Supply(NamedTuple):
    T1: Any


@fr.unit("demo-strip-cab", **_UNIT)
def _strip_cab(u: Any) -> _Strip:
    return _Strip(u.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True))


@fr.unit("demo-supply-cab", **_UNIT)
def _supply_cab(u: Any) -> _Supply:
    return _Supply(u.device("T1", "DEMO-PSU-24", interface=("output",)))


def _strip_pins(io: Any) -> tuple[Any, Any]:
    return io.X1[1].outer, io.X1[2].outer


def _supply_pins(io: Any) -> tuple[Any, Any]:
    return io.T1.output["+"], io.T1.output["-"]


def _built(cab: Any, pins: Any) -> fr.BuildResult:
    @fr.unit("demo-container", **_UNIT)
    def container(c: Any) -> _Open:
        io = c.add(cab, "U1")
        lamp = c.device("H1", "DEMO-LAMP-24")
        first, second = pins(io)
        c.series(lamp["1"], first, wire=("WH", 0.5))
        c.series(lamp["2"], second, wire=("WH", 0.5))
        return _Open()

    d = fr.design("demo_parts")
    d.add(container, "C1", place=None)
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-container", cover=root / "c.md")
    return fr.build(d, cover)


def test_a_supply_boundary_draws_no_frame() -> None:
    """R1261: a nested unit's supply output has no kit symbol or replica (KI-480), so no frame stands on any page."""
    drawings = list(drawn_pages(_built(_supply_cab, _supply_pins).model).values())
    assert [one for drawing in drawings for one in drawing.outlines] == []
    assert len([s for drawing in drawings for s in drawing.symbols if s.key == "lamp"]) == 1


def test_no_parent_function_is_drawn_inside_the_unit_outline() -> None:
    drawings = list(drawn_pages(_built(_strip_cab, _strip_pins).model).values())
    placed = [(drawing, one) for drawing in drawings for one in drawing.outlines]
    assert len(placed) == 2  # the foreign lamp splits the unit's pins: one outline per run
    assert len({id(drawing) for drawing, _ in placed}) == 1
    (drawing,) = {d for d, _ in placed}
    # both outlines are the same unit and each prints its title
    assert len([one for _, one in placed if one.label is not None]) == 2
    # the lamp is the page's one function drawn as a plain two-pin box: the parent's own
    lamps = [one for one in drawing.symbols if one.key == "lamp"]
    assert len(lamps) == 1
    body = translate(box_boxes(("1", "2"))[0], dx=lamps[0].x, dy=lamps[0].y)
    for _, one in placed:
        xs, ys = [x for x, _ in one.points], [y for _, y in one.points]
        box = Box(x=min(xs), y=min(ys), width=max(xs) - min(xs), height=max(ys) - min(ys))
        assert not overlaps(box, body)
