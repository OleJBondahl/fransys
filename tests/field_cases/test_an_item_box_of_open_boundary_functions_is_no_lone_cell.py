"""Field case: a unit's interface device drawn as one box, every function an open boundary (L5).
The bug: `LONE_CELL` rule (b) keyed its open-boundary exemption by function, so the item box missed it and fired.
Fixed by layout-0202 (amending layout-0077): an item box whose functions are all boundary functions is an open end too."""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest


class _Io(NamedTuple):
    psu: Any


@fr.unit("demo-open-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: Any) -> _Io:
    psu = u.device("G1", "DEMO-PSU-24-5OUT", interface=True, unused=True)
    lamp = u.device("H1", "DEMO-LAMP-24")
    other = u.device("P1", "DEMO-LAMP-24")
    u.series(lamp["1"], other["1"], wire=("RD", 0.75))
    u.series(lamp["2"], other["2"], wire=("RD", 0.75))
    return _Io(psu)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    d.add(_box, "U1")
    (root / "own.md").write_text("# Box\n", encoding="utf-8")
    (root / "c.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-open-box", cover=root / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=root / "c.md"))


def test_an_open_boundary_item_box_gives_no_lone_cell(built: fr.BuildResult) -> None:
    assert [f for f in built.findings if f.code == "LONE_CELL"] == []
