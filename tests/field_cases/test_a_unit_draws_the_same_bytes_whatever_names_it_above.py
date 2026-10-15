"""Field case: a unit's own PDF is the same bytes whatever instance tag or parent it has.

The engineering shape: a unit of three lamps, the first one's two pins each wired to the other
two lamps (a star net per pin), with its own schematic document. It is added to a design as
"U1", as "U2", and inside another unit.

The bug: a model stores a conductor's ends in id order, and an id follows the instance path. The
router drew each conductor from its first end, so renaming "U1" to "U2" or nesting the unit drew
some conductors from the opposite end: the same ink, other bytes.

The rule (decision layout-0177): a unit's drawing reads nothing from above it. A conductor is
drawn from its upper end (then the left one), the bracket's own end points.
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr

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
        u.detail.wire(first[pin], second[pin], wire=("WH", 0.75))
        u.detail.wire(first[pin], third[pin], wire=("WH", 0.75))
    return _Io(first)


@fr.unit("demo-outer-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _outer(u: Any) -> _Io:
    u.add(_inner, "U2")
    return _Io(u.device("P9", "DEMO-LAMP-24"))


def _inner_pdf(tmp_path: Path, unit: Any, tag: str) -> bytes:
    """The inner unit's own PDF, with `unit` added to the design as `tag`."""
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(unit, tag)
    (tmp_path / "own.md").write_text("# Box\n", encoding="utf-8")
    own = fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, "demo-inner-box", cover=tmp_path / "own.md"
    )
    fr.write(fr.build(d, own), tmp_path / "out")
    return (tmp_path / "out" / _PDF).read_bytes()


def test_renaming_the_instance_tag_leaves_the_units_pdf_unchanged(tmp_path: Path) -> None:
    """U1 against U2, no nesting."""
    for sub in ("one", "two"):
        (tmp_path / sub).mkdir()
    assert _inner_pdf(tmp_path / "one", _inner, "U1") == _inner_pdf(tmp_path / "two", _inner, "U2")


def test_nesting_the_unit_leaves_its_pdf_unchanged(tmp_path: Path) -> None:
    """The unit alone against the same unit inside an outer unit."""
    for sub in ("alone", "nested"):
        (tmp_path / sub).mkdir()
    alone = _inner_pdf(tmp_path / "alone", _inner, "U1")
    assert alone == _inner_pdf(tmp_path / "nested", _outer, "U1")
