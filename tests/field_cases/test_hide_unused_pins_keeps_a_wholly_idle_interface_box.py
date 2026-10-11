"""Field case: an interface device whose every port is a spare, with `hide_unused_pins` on.

The engineering shape: a unit hands back a lamp of its interface that nothing is wired to,
inside the unit or across it, and sets `hide_unused_pins` on its own profile. The lamp is drawn
as a labelled box, so the switch drops each of its unused ports.

The bug: the box was left with no port, and placing the unit's page raised ValueError "min()
iterable argument is empty" in `_port_y` (stages/place.py).
The rule: a unit's boundary function stays drawn (the parent's replica column needs its spec,
layout-0139 (amended 2026-10-11)), and its box keeps its ports when all of them are spare.
"""

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
    """The unit's own page and the cabinet page place; the idle lamp keeps PORT_UNCONNECTED."""
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    d.add(_box, "U1")
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    (tmp_path / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-idle-box", cover=tmp_path / "own.md")
    result = fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "c.md"))
    assert any(f.code == "PORT_UNCONNECTED" for f in result.findings)
