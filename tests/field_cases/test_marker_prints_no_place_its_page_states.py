"""Field case: a container page scoped to place C1, a unit's boundary strip wired to lamps.

The rule (owner 2026-09-24: shortest designations; designer's ruling 2026-10-06): a link marker
on a page prints no place the page already states. The container page's off stubs name the
strip `-U1-X1:...`, never `+C1-U1-X1:...`.

The bug: the stub's far end was printed from the whole path, so the page's own place showed.
The decision that fixed it: layout-0121.
"""

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
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    sig = x1.run("SIG", 1)
    u.wire(sig[1], lamp.lamp["1"], wire=("WH", 0.75))
    return _Io(sig[1])


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    io = d.add(_box, "U1")
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.wire(io.out, lamp.lamp["1"], wire=("WH", 0.75))
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-strip-box", cover=tmp_path / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "c.md"))


def test_a_marker_prints_no_place_its_page_states(tmp_path: Path) -> None:
    """The container page is C1's; its stubs name `-U1-X1:SIG:1`, never `+C1-U1-X1:SIG:1`."""
    model = _build(tmp_path).model
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    texts = [
        marker_text(model, m)
        for m in layout_of(model, LinkMarker).values()
        if sets[pages[m.page].drawing_set].unit is None
    ]
    assert any("-U1-X1" in text for text in texts), texts
    assert not any("+C1" in text for text in texts), texts


def test_a_unit_page_still_prints_the_whole_path_of_an_end_outside_the_unit(tmp_path: Path) -> None:
    """The unit's page states no place (model-0143): its stub keeps `+C1-H1:1`."""
    model = _build(tmp_path).model
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    texts = [
        marker_text(model, m)
        for m in layout_of(model, LinkMarker).values()
        if sets[pages[m.page].drawing_set].unit is not None
    ]
    assert texts == ["\u2190 +C1-H1:1"], texts
