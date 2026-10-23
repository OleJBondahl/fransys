"""A consumer `module_mm` scales the drawn pages of the build; the house value changes none."""

from typing import Any, NamedTuple
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK

pytestmark = pytest.mark.wp("facade")

_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01"}


class _Open(NamedTuple):
    pass


@fr.unit("demo-grid-cab", text="first", by="AB", **_REL)
def _cab(u: Any) -> _Open:
    lamp = u.device("H1", "DEMO-LAMP-24")
    psu = u.device("T1", "DEMO-PSU-24")
    u.dc_supply("S", psu)
    u.detail.wire(psu.output["+"], lamp["1"], wire=(BK, 0.5))
    return _Open()


def _svgs(root: Path, settings: fr.Settings) -> dict[str, str]:
    d = fr.design("demo_parts")
    d.add(_cab, "C1", place=None)
    (root / "cab.md").write_text("# cab\n", encoding="utf-8")
    document = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, "demo-grid-cab", cover=root / "cab.md"
    )
    fr.write(fr.build(d, document, settings=settings), root / "out", intermediates=root / "inter")
    return {p.name: p.read_text(encoding="utf-8") for p in sorted((root / "inter").glob("*.svg"))}


def _grid(tmp_path: Path, module_mm: str) -> fr.Settings:
    path = tmp_path / f"grid-{module_mm}.toml"
    path.write_text(f"[grid]\nmodule_mm = {module_mm}\n", encoding="utf-8")
    return fr.settings(path)


def test_a_consumer_module_mm_changes_the_drawn_pages(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    house = _svgs(tmp_path / "a", fr.settings())
    theirs = _svgs(tmp_path / "b", _grid(tmp_path, "2.0"))
    assert house
    assert house.keys() == theirs.keys()
    assert house != theirs


def test_the_houses_own_module_mm_changes_no_byte(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    assert _svgs(tmp_path / "a", fr.settings()) == _svgs(tmp_path / "b", _grid(tmp_path, "2.5"))
