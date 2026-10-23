"""Field case: a unit whose boundary is a supply's + and - outputs, with a parent lamp across them.

The engineering shape: a cabinet unit holds a supply `T1` and marks its output an interface; its
container wires a lamp across the output's `+` and `-`. The container's page draws the `+` pin
cell above and the `-` pin cell below the lamp.

The bug: the unit's outline is one box over its black-box members, so it spans both boundary
rows and encloses the parent's lamp, a function that is not the unit's. The black box must never
enclose a function that is not the unit's (2026-10-11).
Decision: layout-0169.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_layout.geometry import Box, overlaps, translate
from fransys_layout.geometry.symbols import generic_box_geometry

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}


class _Open(NamedTuple):
    pass


class _Supply(NamedTuple):
    T1: Any


@fr.unit("demo-supply-cab", **_UNIT)
def _cab(u: Any) -> _Supply:
    return _Supply(u.device("T1", "DEMO-PSU-24", interface=("output",)))


def _built() -> fr.BuildResult:
    @fr.unit("demo-container", **_UNIT)
    def container(c: Any) -> _Open:
        io = c.add(_cab, "U1")
        lamp = c.device("H1", "DEMO-LAMP-24")
        c.detail.wire(lamp["1"], io.T1.output["+"], wire=("WH", 0.5))
        c.detail.wire(lamp["2"], io.T1.output["-"], wire=("WH", 0.5))
        return _Open()

    d = fr.design("demo_parts")
    d.add(container, "C1", place=None)
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-container", cover=root / "c.md")
    return fr.build(d, cover)


def test_no_parent_function_is_drawn_inside_the_unit_outline() -> None:
    drawings = list(drawn_pages(_built().model).values())
    placed = [(drawing, one) for drawing in drawings for one in drawing.outlines]
    assert len(placed) == 2  # the foreign lamp splits the unit's pins: one outline per run
    assert len({id(drawing) for drawing, _ in placed}) == 1
    (drawing,) = {d for d, _ in placed}
    # both outlines are the same unit and each prints its title
    assert len([one for _, one in placed if one.label is not None]) == 2
    # the lamp is the page's one function drawn as a plain two-pin box: the parent's own
    lamps = [one for one in drawing.symbols if one.key == "generic-box" and not one.texts]
    assert len(lamps) == 1
    body = translate(generic_box_geometry(("1", "2")).body, dx=lamps[0].x, dy=lamps[0].y)
    for _, one in placed:
        xs, ys = [x for x, _ in one.points], [y for _, y in one.points]
        box = Box(x=min(xs), y=min(ys), width=max(xs) - min(xs), height=max(ys) - min(ys))
        assert not overlaps(box, body)
