"""Field case: a unit sets its own layout profile in its body, and only its own pages read it.

The engineering shape: an Ethernet switch (eight one-pin port connectors and a 24 V supply
function) sits in a released unit. Two of its ports are wired to a lamp; the supply and the
other ports are idle. The unit's author wants the idle supply left off the unit's drawing
(`hide_unused_pins`) and a narrower column gap. The parent design sets a different profile.

The bug: `d.layout.profile(...)` inside a unit body raised AttributeError, so a unit could not
state its own profile. The consumer set it on the top design, which governed every page, the
unit's own pages included.

The rule (decision author-0034, model-0192): a unit's profile belongs to the unit. It governs
the unit's own documents wherever they are built, so the unit's PDF is the same bytes on its own
and inside a parent. A parent's profile governs the parent's own pages only; a unit with no
profile of its own draws with the house default, never its parent's.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest

from fransys_model.layout import DrawingSet, Page, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items

if TYPE_CHECKING:
    from pathlib import Path

_OWN = {"hide_unused_pins": True, "column_gap": 64}
_PARENT = {"hide_unused_pins": False, "column_gap": 40}
_UNIT_PDF = "demo-switch-box-v1.1.pdf"
_BOXES = ("demo-first-box", "demo-second-box")
_A3_NUMBERS = {
    "width_mm": 420,
    "height_mm": 297,
    "content_x_mm": 10,
    "content_y_mm": 10,
    "content_width_mm": 400,
    "content_height_mm": 277,
    "frame_columns": 8,
    "frame_rows": 6,
    "module_mm": Decimal("2.5"),
}


class _Io(NamedTuple):
    switch: fr.Device


def _release(profile: dict[str, Any] | None, *, own_sheet: bool = False) -> Any:
    @fr.unit(
        "demo-switch-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB"
    )
    def box(u: fr.Design) -> _Io:
        if profile is not None:
            sheet = _A3_NUMBERS if own_sheet else None
            u.layout.profile(
                **profile, **({} if sheet is None else {"sheet": u.layout.sheet("UA3", **sheet)})
            )
        switch = u.device("U9", "DEMO-SW-8P")
        lamp = u.device("P1", "DEMO-LAMP-24")
        u.wire(switch.p1["1"], lamp["1"], wire=("WH", 0.75))
        u.wire(switch.p2["1"], lamp.lamp["2"], wire=("WH", 0.75))
        return _Io(switch)

    return box


def _build(
    tmp_path: Path,
    *,
    unit_profile: dict[str, Any] | None,
    parent: dict[str, Any] | None,
    beside: bool,
    own_sheet: bool = False,
) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    if parent is not None:
        d.layout.profile(**parent)
    d.add(_release(unit_profile, own_sheet=own_sheet), "U1")
    if beside:
        first = d.device("P8", "DEMO-LAMP-24", place="C1")
        second = d.device("P9", "DEMO-LAMP-24", place="C1")
        d.wire(first["1"], second["1"], wire=("WH", 0.75))
        d.wire(first["2"], second["2"], wire=("WH", 0.75))
    (tmp_path / "own.md").write_text("# Switch box\n", encoding="utf-8")
    (tmp_path / "cab.md").write_text("# Cabinet\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-switch-box", cover=tmp_path / "own.md")
    documents = [own]
    if beside:
        documents.append(fr.document(preset, cabinet, cover=tmp_path / "cab.md"))
    return fr.build(d, *documents)


def _unit_drawn(result: fr.BuildResult) -> list[str]:
    """The name of every function of the unit's items that the layout draws."""
    model = result.model
    return sorted(
        functions(model)[p.function].key[-1]
        for p in layout_of(model, SymbolPlacement).values()
        if items(model)[functions(model)[p.function].item].unit is not None
        and functions(model)[p.function].key[-1] != "lamp"
    )


def _unit_pdf(result: fr.BuildResult, out: Path) -> bytes:
    fr.write(result, out)
    return (out / _UNIT_PDF).read_bytes()


@pytest.fixture
def own_profile(tmp_path: Path) -> tuple[fr.BuildResult, fr.BuildResult]:
    """The unit with its own profile, alone and under a parent that sets a different one."""
    for sub in ("alone", "inside"):
        (tmp_path / sub).mkdir()
    alone = _build(tmp_path / "alone", unit_profile=_OWN, parent=None, beside=False)
    inside = _build(tmp_path / "inside", unit_profile=_OWN, parent=_PARENT, beside=True)
    return alone, inside


def test_the_unit_profile_hides_its_idle_supply_and_its_idle_ports(
    own_profile: tuple[fr.BuildResult, fr.BuildResult],
) -> None:
    """Only the two wired port connectors are drawn; the idle supply box is left off."""
    alone, inside = own_profile
    assert _unit_drawn(alone) == ["p1", "p2"]
    assert _unit_drawn(inside) == ["p1", "p2"]


def test_the_unit_pdf_is_the_same_bytes_under_a_parent_with_another_profile(
    tmp_path: Path,
) -> None:
    """The parent's profile is hide off and a wide gap, or none: the unit's own pages are one."""
    for sub in ("set", "none"):
        (tmp_path / sub).mkdir()
    with_profile = _build(tmp_path / "set", unit_profile=_OWN, parent=_PARENT, beside=True)
    without = _build(tmp_path / "none", unit_profile=_OWN, parent=None, beside=True)
    assert _unit_pdf(with_profile, tmp_path / "o-set") == _unit_pdf(without, tmp_path / "o-none")


def test_a_parent_profile_does_not_reach_a_unit_without_one(tmp_path: Path) -> None:
    """The parent hides unused pins; the unit sets nothing, so its idle supply stays drawn."""
    for sub in ("alone", "inside", "plain"):
        (tmp_path / sub).mkdir()
    alone = _build(tmp_path / "alone", unit_profile=None, parent=None, beside=False)
    inside = _build(
        tmp_path / "inside", unit_profile=None, parent={"hide_unused_pins": True}, beside=True
    )
    plain = _build(tmp_path / "plain", unit_profile=None, parent=None, beside=True)
    assert _unit_drawn(inside) == _unit_drawn(alone)
    assert "supply" in _unit_drawn(inside)
    assert _unit_pdf(inside, tmp_path / "o-inside") == _unit_pdf(plain, tmp_path / "o-plain")


def test_a_sheet_only_the_unit_profile_names_is_not_unused(tmp_path: Path) -> None:
    """The unit's pages are drawn on its sheet, and no finding calls that sheet unused."""
    result = _build(tmp_path, unit_profile=_OWN, parent=_PARENT, beside=True, own_sheet=True)
    assert [f for f in result.findings if f.code == "SHEET_FORMAT_UNUSED"] == []
    model = result.model
    unit_sets = {s.id for s in layout_of(model, DrawingSet).values() if s.unit is not None}
    pages = [p for p in layout_of(model, Page).values() if p.drawing_set in unit_sets]
    assert pages
    assert {p.sheet_format for p in pages} != {None}
    top_pages = [p for p in layout_of(model, Page).values() if p.drawing_set not in unit_sets]
    assert {p.sheet_format for p in top_pages} == {None}


class _EdgeIo(NamedTuple):
    edge: fr.Device


def _edge_box(name: str, profile: dict[str, Any]) -> Any:
    """A unit of two lamps and a boundary connector, with its own profile."""

    @fr.unit(name, revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def box(u: fr.Design) -> _EdgeIo:
        u.layout.profile(**profile)
        edge = u.device("X1", "DEMO-CONN-2P", interface=True)
        lamp = u.device("P2", "DEMO-LAMP-24")
        other = u.device("P3", "DEMO-LAMP-24")
        u.wire(lamp["1"], other["1"], wire=("WH", 0.75))
        u.wire(edge["1"], lamp["2"], wire=("WH", 0.75))
        return _EdgeIo(edge)

    return box


def _two_units(
    tmp_path: Path, first_profile: dict[str, Any], second_profile: dict[str, Any]
) -> fr.BuildResult:
    """Two units wired to each other at their boundary connectors, each with its own profile."""
    d = fr.design("demo_parts", place="C1")
    first = d.add(_edge_box("demo-first-box", first_profile), "U1")
    second = d.add(_edge_box("demo-second-box", second_profile), "U2")
    d.wire(first.edge["2"], second.edge["2"], wire=("WH", 0.75))
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    docs = []
    for name in _BOXES:
        (tmp_path / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
        docs.append(fr.document(preset, name, cover=tmp_path / f"{name}.md"))
    return fr.build(d, *docs)


def _two_pdfs(result: fr.BuildResult, out: Path) -> tuple[bytes, ...]:
    fr.write(result, out)
    return tuple((out / f"{name}-v1.1.pdf").read_bytes() for name in _BOXES)


def test_a_unit_wired_to_another_unit_reads_no_profile_from_it(tmp_path: Path) -> None:
    """A wire between two units draws as stubs, so each unit's pages ignore the other's profile."""
    for sub in ("mixed", "same-a", "same-b"):
        (tmp_path / sub).mkdir()
    mixed = _two_units(tmp_path / "mixed", _OWN, _PARENT)
    same_a = _two_units(tmp_path / "same-a", _OWN, _OWN)
    same_b = _two_units(tmp_path / "same-b", _PARENT, _PARENT)
    first_pdf, second_pdf = _two_pdfs(mixed, tmp_path / "o-mixed")
    assert first_pdf == _two_pdfs(same_a, tmp_path / "o-a")[0]
    assert second_pdf == _two_pdfs(same_b, tmp_path / "o-b")[1]
    assert first_pdf != _two_pdfs(same_b, tmp_path / "o-b")[0]


class _StarIo(NamedTuple):
    lamp: fr.Device


def _star_box() -> Any:
    """A unit whose first lamp pin heads a net of three: its pages print reference boxes."""

    @fr.unit("demo-star-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
    def box(u: fr.Design) -> _StarIo:
        lamp, second, third = (u.device(f"P{n}", "DEMO-LAMP-24") for n in (2, 3, 4))
        u.wire(lamp["1"], second["1"], wire=("WH", 0.75))
        u.wire(lamp["1"], third["1"], wire=("WH", 0.75))
        u.wire(lamp["2"], second["2"], wire=("WH", 0.75))
        return _StarIo(lamp)

    return box


def _star_pdf(tmp_path: Path, *, parent_sets: bool) -> bytes:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    d.add(_star_box(), "U1")
    if parent_sets:
        d.location("LONGPLACE-LONGER", "Panel")
        for n in range(3):
            far = d.device(f"P{10 + n}", "DEMO-LAMP-24", place="LONGPLACE-LONGER")
            near = d.device(f"P{20 + n}", "DEMO-LAMP-24", place="C1")
            d.wire(far["1"], near["1"], wire=("WH", 0.75))
    (tmp_path / "star.md").write_text("# Star box\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, fr.document(preset, "demo-star-box", cover=tmp_path / "star.md"))
    fr.write(result, tmp_path / "out")
    return (tmp_path / "out" / "demo-star-box-v1.1.pdf").read_bytes()


def test_a_unit_reference_box_is_sized_from_the_units_own_sets(tmp_path: Path) -> None:
    """A parent with more drawing sets and a long location path widens no box in the unit."""
    for sub in ("alone", "inside"):
        (tmp_path / sub).mkdir()
    assert _star_pdf(tmp_path / "alone", parent_sets=False) == _star_pdf(
        tmp_path / "inside", parent_sets=True
    )
