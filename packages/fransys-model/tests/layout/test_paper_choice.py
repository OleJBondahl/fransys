"""model-0312: `sheet_for` reads the build's `PaperChoice`; a page's authored sheet still wins."""

import dataclasses

import pytest
from derive_helpers import frozen_with_library

from fransys_model.kernel import Draft, Model, Origin, Record, SchemaError, freeze, make_id
from fransys_model.layout import (
    PaperChoice,
    Profile,
    SheetFormat,
    a2_sheet_format,
    default_profile,
    default_sheet_format,
    sheet_for,
    sheet_format_of,
)
from fransys_model.vocab import PageKind

_ORIGIN = Origin(file="test_paper_choice.py", line=1, note="fixture")
A3, A2 = default_sheet_format(), a2_sheet_format()


def _model(default: SheetFormat, by_kind: dict[PageKind, SheetFormat], *extra: Record) -> Model:
    key = ("test", "choice")
    choice = PaperChoice(
        id=make_id(PaperChoice, key),
        key=key,
        default=default.id,
        by_kind=frozendict({kind.value: sheet.id for kind, sheet in by_kind.items()}),
    )
    draft = Draft()
    draft.extend([A3, A2, choice, *extra], origin=_ORIGIN)
    return freeze(draft)


def test_the_kind_s_paper_wins_over_the_default() -> None:
    model = _model(A2, {PageKind.BLOCK_DIAGRAM: A3})
    assert sheet_for(model, PageKind.BLOCK_DIAGRAM).id == A3.id
    assert sheet_for(model, PageKind.SCHEMATIC).id == A2.id


def test_a_default_of_a2_is_the_sheet_of_a_page_with_no_sheet() -> None:
    model = _model(A2, {})
    assert sheet_format_of(model, None).id == A2.id
    assert sheet_for(model, PageKind.BLOCK_DIAGRAM).id == A2.id


def test_a_profile_s_authored_sheet_wins_until_settings_c() -> None:
    own = dataclasses.replace(default_profile(), id=make_id(Profile, ("t", "p")), key=("t", "p"))
    own = dataclasses.replace(own, sheet_format=A2.id)
    model = _model(A3, {PageKind.BLOCK_DIAGRAM: A3}, own)
    assert sheet_for(model, PageKind.SCHEMATIC).id == A2.id


def test_a_model_with_no_paper_record_raises_naming_the_fix() -> None:
    draft = Draft()
    draft.extend([A3], origin=_ORIGIN)
    with pytest.raises(SchemaError, match=r"layout\.paper.*fransys\.build"):
        sheet_format_of(freeze(draft), None)


def test_a_second_paper_choice_does_not_freeze() -> None:
    with pytest.raises(SchemaError):
        frozen_with_library(_second())


def _second() -> Draft:
    other = PaperChoice(id=make_id(PaperChoice, ("other",)), key=("other",), default=A3.id)
    draft = Draft()
    draft.extend([A3, other], origin=_ORIGIN)
    return draft
