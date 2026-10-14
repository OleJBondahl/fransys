"""A profile whose `text_height_mm` is under its `min_text_height_mm` gets one `TEXT_TOO_SMALL`.

`read_inputs` builds it from the profile (decisions layout-0179, layout-0185), so the
finding reaches `stage_results`' findings with the profile as its subject. All data invented.
"""

import dataclasses
from decimal import Decimal

from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.house import DEFAULT_PROFILE
from fransys_layout.lint.codes import ALL_CODES, TEXT_TOO_SMALL
from fransys_model.kernel import Draft, Origin, Severity, freeze, make_id
from fransys_model.layout import Profile

_ORIGIN = Origin(file="tests/engines/test_text_too_small.py", line=1, note="profile")


def _profile(**changes: object) -> Profile:
    base = Profile(
        id=make_id(Profile, ("test", "profile")),
        key=("test", "profile"),
        column_gap=DEFAULT_PROFILE.column_gap,
        row_gap=DEFAULT_PROFILE.row_gap,
        route_margin=DEFAULT_PROFILE.route_margin,
        marker_padding=DEFAULT_PROFILE.marker_padding,
        route_turn_penalty=DEFAULT_PROFILE.route_turn_penalty,
        route_crossing_penalty=DEFAULT_PROFILE.route_crossing_penalty,
        band_ranks=DEFAULT_PROFILE.band_ranks,
        group_ranks=DEFAULT_PROFILE.group_ranks,
    )
    return dataclasses.replace(base, **changes)


def _found(profile: Profile | None) -> list:
    draft: Draft = build_cabinet()
    if profile is not None:
        draft.extend((profile,), origin=_ORIGIN)
    model = freeze(draft)
    _, findings = stage_results(model, read_inputs(model))
    return [finding for finding in findings if finding.code == TEXT_TOO_SMALL]


def test_the_code_is_listed() -> None:
    assert TEXT_TOO_SMALL in ALL_CODES


def test_a_small_text_height_is_warned_about_with_both_sizes() -> None:
    profile = _profile(text_height_mm=Decimal(1))
    (finding,) = _found(profile)
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (profile.id,)
    assert finding.message == (
        "profile test.profile sets a text height of 1 mm, under its minimum of 1.8 mm"
    )


def test_the_house_text_height_and_the_house_profile_give_none() -> None:
    assert _found(_profile()) == []
    assert _found(None) == []


def test_a_lower_floor_gives_none() -> None:
    assert _found(_profile(text_height_mm=Decimal(1), min_text_height_mm=Decimal("0.5"))) == []


def test_the_floor_is_exact_at_the_boundary() -> None:
    """A height equal to the floor does not fire; a hundredth of a mm under it does."""
    assert _found(_profile(text_height_mm=Decimal("1.8"), min_text_height_mm=Decimal("1.8"))) == []
    assert _found(_profile(text_height_mm=Decimal("2.5"), min_text_height_mm=Decimal("2.5"))) == []
    assert (
        len(_found(_profile(text_height_mm=Decimal("1.79"), min_text_height_mm=Decimal("1.8"))))
        == 1
    )
