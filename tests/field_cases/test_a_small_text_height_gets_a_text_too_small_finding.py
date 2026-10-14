"""Field case: a drawing profile sets the text so small that it prints under its floor.

The engineering shape: a lamp wired to a terminal on a cabinet page. The drawing profile sets
`text_height_mm` to 1 mm, well under the house 1.8 mm capital height, to fit more on a page. That
prints text unreadably small on paper.

The bug: nothing reported it. The build was green and the pages were drawn, so the author learned
of the unreadable text only from the printed drawing.

The rule (decisions layout-0179, layout-0185 and model-0203): a profile carries
`min_text_height_mm`, a capital height in mm that defaults to 1.8. A profile whose
`text_height_mm` is under it gets one `TEXT_TOO_SMALL` warning. The default profile never gets
one, and nothing is shrunk or grown.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path

_CODE = "TEXT_TOO_SMALL"


class _Io(NamedTuple):
    lamp: fr.Device


def _build(tmp_path: Path, **profile: Any) -> list[Any]:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    if profile:
        d.layout.profile(**profile)
    lamp = d.device("P1", "DEMO-LAMP-24")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    d.wire(x1.run("SIG", 1)[1], lamp.lamp["1"], wire=("WH", 0.75))
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    document = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet, cover=tmp_path / "c.md")
    return [f for f in fr.build(d, document).findings if f.code == _CODE]


def test_a_text_height_of_one_mm_gets_one_text_too_small_finding(tmp_path: Path) -> None:
    (found,) = _build(tmp_path, text_height_mm=Decimal(1))
    assert "text height of 1 mm" in found.message
    assert "minimum of 1.8 mm" in found.message


def test_the_default_profile_gets_none(tmp_path: Path) -> None:
    assert _build(tmp_path) == []


def test_a_lower_floor_silences_it(tmp_path: Path) -> None:
    assert _build(tmp_path, text_height_mm=Decimal(1), min_text_height_mm=Decimal("0.5")) == []


def test_a_unit_profile_and_the_top_profile_each_get_one(tmp_path: Path) -> None:
    @fr.unit("demo-lamp-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def box(u: fr.Design) -> _Io:
        u.layout.profile(text_height_mm=Decimal(1))
        lamp = u.device("P1", "DEMO-LAMP-24")
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5")
        u.wire(x1.run("SIG", 1)[1], lamp.lamp["1"], wire=("WH", 0.75))
        return _Io(lamp)

    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    d.layout.profile(text_height_mm=Decimal("1.5"))
    d.add(box, "U1")
    lamp = d.device("P2", "DEMO-LAMP-24", place="C1")
    x1 = d.terminal_strip("X2", "DEMO-TB-2.5", place="C1")
    d.wire(x1.run("SIG", 1)[1], lamp.lamp["1"], wire=("WH", 0.75))
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    own = fr.document(preset, "demo-lamp-box", cover=tmp_path / "own.md")
    top = fr.document(preset, cabinet, cover=tmp_path / "c.md")
    found = [f for f in fr.build(d, own, top).findings if f.code == _CODE]
    assert sorted("text height of 1 mm" in f.message for f in found) == [False, True]
