"""model-0192: a profile belongs to one unit, and `profile_of` reads exactly that one."""

import dataclasses
from decimal import Decimal

from layout_examples import sheet_format

from fransys_model.derive import text_room, text_room_g
from fransys_model.kernel import Draft, Id, Model, Origin, Record, freeze, make_id
from fransys_model.layout import Profile, default_profile, profile_of
from fransys_model.vocab.core import Unit, UnitRelease


def _profile(value: str) -> Profile:
    return Profile(
        id=Id(kind="layout.profile", value=value * 32),
        key=("examples", "layout", "profile", value),
        sheet_format=sheet_format().id,
        column_gap=48,
        row_gap=32,
        route_margin=16,
        text_height_mm=Decimal("1.8"),
        marker_padding=2,
        route_turn_penalty=5,
        route_crossing_penalty=20,
    )


def _board_unit() -> tuple[UnitRelease, Unit]:
    release_key = ("unit_release", "board", "1", "1")
    release = UnitRelease(
        id=make_id(UnitRelease, release_key),
        key=release_key,
        name="board",
        version=1,
        revision=1,
        interface="1",
    )
    unit = Unit(
        id=Id(kind="unit", value="d" * 32),
        key=("examples", "board"),
        release=release.id,
        parent=None,
    )
    return release, unit


def _freeze(*records: Record) -> Model:
    draft = Draft()
    draft.extend(records, origin=Origin(file="test_profile_of.py", line=1, note="fixture"))
    return freeze(draft)


def test_a_profile_per_unit_and_one_for_the_top_freeze_and_profile_of_reads_each() -> None:
    """`profile_of(model, unit)` matches the unit exactly; none is the house profile."""
    release, unit = _board_unit()
    top = _profile("a")
    own = dataclasses.replace(_profile("b"), unit=unit.id, column_gap=7)
    model = _freeze(sheet_format(), release, unit, top, own)
    assert profile_of(model) == top
    assert profile_of(model, unit.id) == own


def test_a_unit_without_a_profile_gets_the_house_profile_not_the_tops() -> None:
    """The top's profile never reaches a unit: a unit of its own draws with the house numbers."""
    release, unit = _board_unit()
    top = dataclasses.replace(_profile("a"), column_gap=3)
    model = _freeze(sheet_format(), release, unit, top)
    assert profile_of(model, unit.id) == default_profile()
    assert profile_of(model).column_gap == 3


def test_min_text_height_mm_defaults_to_the_house_size_and_an_authored_one_survives() -> None:
    """model-0203: `min_text_height_mm` is 1.8 mm by default; an authored one is read back."""
    assert default_profile().min_text_height_mm == Decimal("1.8")
    release, unit = _board_unit()
    authored = dataclasses.replace(_profile("a"), min_text_height_mm=Decimal("2.5"))
    model = _freeze(sheet_format(), release, unit, authored)
    assert profile_of(model).min_text_height_mm == Decimal("2.5")


def test_text_room_reads_the_unit_profile_and_its_sheet_not_the_tops() -> None:
    """RO-12: `text_room(model, unit)` uses that unit's own height, never the top's."""
    release, unit = _board_unit()
    own = dataclasses.replace(_profile("b"), unit=unit.id, text_height_mm=Decimal("3.5"))
    sheet = sheet_format()
    model = _freeze(sheet, release, unit, _profile("a"), own)
    assert text_room(model) == text_room_g(Decimal("1.8"), sheet.module_mm)
    assert text_room(model, unit.id) == text_room_g(Decimal("3.5"), sheet.module_mm)
    assert text_room(model) != text_room(model, unit.id)
