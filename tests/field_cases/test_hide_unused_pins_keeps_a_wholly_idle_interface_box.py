"""Field case: an interface device whose every port is a spare keeps its box and ports under hide_unused_pins.
The bug: the box was left with no port, and placing the unit's page raised ValueError "min() iterable argument is empty".
Fixed by layout-0139 (amended 2026-10-11): the boundary function stays drawn, and the box keeps its ports when all are spare."""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    lamp: fr.Device


@fr.unit("demo-idle-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    u.layout.profile(hide_unused_pins=True)
    u.device("P1", "DEMO-LAMP-24")
    return _Io(u.device("X1", "DEMO-LAMP-24", interface=True))


def test_a_wholly_idle_interface_box_builds(tmp_path: Path) -> None:
    """The unit's own page and the cabinet page place."""
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    d.add(_box, "U1")
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-idle-box", cover=tmp_path / "own.md")
    codes = [f.code for f in fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "c.md")).findings]
    assert "FUNCTION_NOT_WIRED" in codes
    assert "SET_WITHOUT_PAGE" not in codes
