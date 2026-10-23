"""Field case: on the core path a unit's own document is laid out as its own drawing set.

The shape: a design holds a unit U1 (a lamp and a boundary strip) beside a lamp of its own. Today's
engine lays out the top level and each unit as separate drawing sets, so `fr.write(unit=...)`
finds the unit's pages.

The bug: P6.1-F's private core path solved the top level once and built no per-unit set. Fixed by
UNIT-SETS (el-0022, designer Ruling 70): one drawing set per (unit, location).

The repro wires the unit's output to the top-level lamp. The first input left it open, so it met a
BOUNDARY_UNCONNECTED ERROR and never reached the bug.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    out: fr.Terminal


@fr.unit("demo-core-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    lamp = u.device("P1", "DEMO-LAMP-24")
    sig = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True).run("SIG", 1)
    u.detail.wire(sig[1], lamp.lamp["1"], wire=("WH", 0.75))
    return _Io(sig[1])


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    room = d.location("R", "Room")
    box = d.add(_box, "U1", place="R")
    lamp = d.device("H1", "DEMO-LAMP-24", place="R")
    d.detail.wire(box.out, lamp.lamp["1"], wire=("WH", 0.75))
    (tmp_path / "r.md").write_text("# Room\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, room, cover=tmp_path / "r.md"))


def _unit_pages_drawn(result: fr.BuildResult) -> bool:
    sets = layout_of(result.model, DrawingSet)
    pages = layout_of(result.model, Page)
    return any(sets[pages[p].drawing_set].unit is not None for p in drawn_pages(result.model))


def test_a_unit_document_is_drawn_on_the_core_path(tmp_path: Path) -> None:
    assert _unit_pages_drawn(_build(tmp_path))


def _set_warnings(result: fr.BuildResult) -> list[str]:
    codes = ("NET_CUT_BY_SET", "SET_WITHOUT_PAGE")
    return [f.code for f in result.findings if f.code in codes]


def test_a_net_cut_by_the_unit_sets_is_a_warning_not_a_silent_drop(tmp_path: Path) -> None:
    """The top set keeps its end of the unit's output net with a stub and so has a page (R468 U1).

    NET_CUT_BY_SET still names the net (its raiser is XF part 6); SET_WITHOUT_PAGE is gone.
    """
    result = _build(tmp_path)
    assert _set_warnings(result) == ["NET_CUT_BY_SET"]
    sets = layout_of(result.model, DrawingSet)
    pages = layout_of(result.model, Page)
    assert any(sets[pages[p].drawing_set].unit is None for p in drawn_pages(result.model))


def test_a_net_between_a_unit_and_its_container_draws_with_no_set_warning(tmp_path: Path) -> None:
    assert _set_warnings(_build(tmp_path)) == []
