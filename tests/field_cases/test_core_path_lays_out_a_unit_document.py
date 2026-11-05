"""Field case: on the core path a unit's own document is laid out as its own drawing set.
The bug: the core path solved the top level once and built no per-unit set, so fr.write(unit=...) found no unit pages.
Fixed by el-0022 (UNIT-SETS, designer Ruling 70), one drawing set per (unit, location)."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document, unit_document
from fransys.colours import BU

from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    out: fr.Terminal


@fr.unit("demo-core-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    lamp = u.device("P1", "DEMO-LAMP-24")
    sig = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True).run("SIG", 1)
    u.series(sig[1].inner, lamp.lamp["1"], wire=("WH", 0.75))
    ret = u.terminal_strip("X2", "DEMO-TB-2.5", 1)
    u.series(ret[1].inner, lamp.lamp["2"], wire=("WH", 0.75))
    return _Io(sig[1])


def build_room(tmp_path: Path, *, beyond: bool = False) -> fr.BuildResult:
    d = fr.design("demo_parts")
    room = d.location("R", "Room")
    box = d.add(_box, "U1", place="R")
    lamp = d.device("H1", "DEMO-LAMP-24", place="R")
    d.series(box.out.outer, lamp.lamp["1"], wire=("WH", 0.75))
    x9 = d.terminal_strip("X9", "DEMO-TB-2.5", 2, place="R")
    d.series(x9[1].inner, lamp.lamp["2"], wire=("WH", 0.75))
    extra = [unit_document("demo-core-box")]
    if beyond:  # a net with one end in another room: the set cuts it (the box's net is whole there, through the terminal replica)
        extra.append(cabinet_document(d.location("R2", "Room 2")))
        far = d.device("H2", "DEMO-LAMP-24", place="R2")
        d.series(lamp.lamp["2"], far.lamp["1"], wire=("WH", 0.75))
        d.series(x9[2].inner, far.lamp["2"], wire=("WH", 0.75))
    (tmp_path / "r.md").write_text("# Room\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, room, cover=tmp_path / "r.md"), *extra)


def _unit_pages_drawn(result: fr.BuildResult) -> bool:
    sets = layout_of(result.model, DrawingSet)
    pages = layout_of(result.model, Page)
    return any(sets[pages[p].drawing_set].unit is not None for p in drawn_pages(result.model))


def test_a_unit_document_is_drawn_on_the_core_path(tmp_path: Path) -> None:
    assert _unit_pages_drawn(build_room(tmp_path))


def _set_warnings(result: fr.BuildResult) -> list[str]:
    return [f.code for f in result.findings if f.code in ("CONNECTION_NOT_DRAWN", "SET_WITHOUT_PAGE")]


def test_a_net_cut_by_the_unit_sets_ends_in_a_stub_with_no_warning(tmp_path: Path) -> None:
    """The top set keeps its end of the unit's output net with a stub and so has a page (R468 U1).

    The cut net ends in a stub, so neither CONNECTION_NOT_DRAWN nor SET_WITHOUT_PAGE is raised (R520 B1).
    """
    result = build_room(tmp_path)
    assert _set_warnings(result) == []
    sets = layout_of(result.model, DrawingSet)
    pages = layout_of(result.model, Page)
    assert any(sets[pages[p].drawing_set].unit is None for p in drawn_pages(result.model))


def test_a_net_between_a_unit_and_its_container_draws_with_no_set_warning(tmp_path: Path) -> None:
    assert _set_warnings(build_room(tmp_path)) == []


_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01"}


class _WiredIo(NamedTuple):
    X1: Any


@fr.unit("demo-int-cab", text="first", by="AB", **_REL)
def _wired_cab(u: Any) -> _WiredIo:
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 2)
    x2 = u.terminal_strip("X2", "DEMO-TB-2.5", 2)
    u.series(x1[1].outer, x2[1].outer, wire=(BU, 0.5))
    return _WiredIo(x1)


def _build_wired(tmp_path: Path) -> fr.BuildResult:
    """R636 B: a cabinet set whose internal wires no page draws is one SET_WITHOUT_PAGE error."""
    d = fr.design("demo_parts")
    d.add(_wired_cab, "U1", place=None)
    (tmp_path / "cab.md").write_text("# cab\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-int-cab", cover=tmp_path / "cab.md")
    return fr.build(d, doc)


def test_the_wired_cabinet_builds_clean(tmp_path: Path) -> None:
    assert [f.code for f in _build_wired(tmp_path).findings if f.severity.name == "ERROR"] == []
