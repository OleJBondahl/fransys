"""Field case: a unit of three lamps with a star net per pin, added to a design as "U1", as "U2" and nested in another unit.
The bug: the router drew each conductor from its first end, which follows the instance path, so renaming changed the bytes.
Fixed by layout-0177, a unit's drawing reads nothing from above it, and a conductor is drawn from its upper end, then its left one."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest

if TYPE_CHECKING:
    from pathlib import Path

_PDF = "demo-inner-box-v1.1.pdf"


class _Io(NamedTuple):
    first: fr.Device


@fr.unit("demo-inner-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _inner(u: Any) -> _Io:
    first = u.device("P1", "DEMO-LAMP-24")
    second = u.device("P2", "DEMO-LAMP-24")
    third = u.device("P3", "DEMO-LAMP-24")
    for pin in ("1", "2"):
        u.series(first[pin], second[pin], wire=("WH", 0.75))
        u.series(first[pin], third[pin], wire=("WH", 0.75))
    return _Io(first)


@fr.unit("demo-outer-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _outer(u: Any) -> _Io:
    u.add(_inner, "U2")
    lamp = u.device("P9", "DEMO-LAMP-24")
    peer = u.device("P8", "DEMO-LAMP-24")
    for pin in ("1", "2"):
        u.series(lamp[pin], peer[pin], wire=("WH", 0.75))
    return _Io(lamp)


def _inner_pdf(tmp_path: Path, unit: Any, tag: str) -> bytes:
    """The inner unit's own PDF, with `unit` added to the design as `tag`."""
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(unit, tag)
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    own = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-inner-box", cover=tmp_path / "own.md")
    docs = [own]
    if unit is _outer:
        (tmp_path / "outer.md").write_text("# Outer\n", encoding="utf-8")
        docs.append(
            fr.document(
                fr.DocumentPreset.CABINET_SCHEMATIC,
                "demo-outer-box",
                cover=tmp_path / "outer.md",
            )
        )
    fr.write(fr.build(d, *docs), tmp_path / "out")
    return (tmp_path / "out" / _PDF).read_bytes()


@pytest.mark.rule("NUMBER-SORT")
def test_renaming_the_instance_tag_leaves_the_units_pdf_unchanged(tmp_path: Path) -> None:
    """U1 against U2, no nesting."""
    for sub in ("one", "two"):
        (tmp_path / sub).mkdir()
    assert _inner_pdf(tmp_path / "one", _inner, "U1") == _inner_pdf(tmp_path / "two", _inner, "U2")


@pytest.mark.rule("NUMBER-SORT")
def test_nesting_the_unit_leaves_its_pdf_unchanged(tmp_path: Path) -> None:
    """The unit alone against the same unit inside an outer unit."""
    for sub in ("alone", "nested"):
        (tmp_path / sub).mkdir()
    alone = _inner_pdf(tmp_path / "alone", _inner, "U1")
    assert alone == _inner_pdf(tmp_path / "nested", _outer, "U1")
