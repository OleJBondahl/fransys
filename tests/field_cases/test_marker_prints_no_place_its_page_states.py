"""Field case: a container page scoped to place C1, a unit's boundary strip wired to lamps.
The bug: the stub's far end was printed from the whole path, so the page's own place showed (+C1-U1-X1 for -U1-X1).
Fixed by layout-0121, a link marker on a page prints no place the page already states."""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import DrawingSet, LinkMarker, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    out: fr.Terminal


@fr.unit("demo-strip-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    u.location("C1", "Cabinet")
    lamp = u.device("P1", "DEMO-LAMP-24")
    sig = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True).run("SIG", 1)
    u.series(sig[1].inner, lamp.lamp["1"], wire=("WH", 0.75))
    ret = u.terminal_strip("X2", "DEMO-TB-2.5", 1)
    u.series(ret[1].inner, lamp.lamp["2"], wire=("WH", 0.75))
    return _Io(sig[1])


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    io = d.add(_box, "U1")
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.series(io.out.outer, lamp.lamp["1"], wire=("WH", 0.75))
    x9 = d.terminal_strip("X9", "DEMO-TB-2.5", 2)
    d.series(x9[1].inner, lamp.lamp["2"], wire=("WH", 0.75))
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-strip-box", cover=tmp_path / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "c.md"))


def test_a_marker_prints_no_place_its_page_states(tmp_path: Path) -> None:
    """The container page is C1's; the replica's stub it prints names the unit's lamp `-U1-P1:1`, never `+C1-U1-P1:1` (R895)."""
    model = _build(tmp_path).model
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    texts = [marker_text(model, m) for m in layout_of(model, LinkMarker).values() if sets[pages[m.page].drawing_set].unit is None]
    assert [t.lstrip("\u2190\u2192 ") for t in texts] == ["-U1-P1:1"], texts  # the arrow follows the pin side


def test_a_unit_page_still_prints_the_whole_path_of_an_end_outside_the_unit(tmp_path: Path) -> None:
    """The unit's page states no place (model-0143): its stub keeps `+C1-H1:1`."""
    model = _build(tmp_path).model
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    texts = [marker_text(model, m) for m in layout_of(model, LinkMarker).values() if sets[pages[m.page].drawing_set].unit is not None]
    assert [t.lstrip("\u2190\u2192 ") for t in texts] == ["+C1-H1:1"], texts  # the arrow follows the pin side
