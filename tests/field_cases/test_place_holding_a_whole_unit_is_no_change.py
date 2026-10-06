"""Kept by design: a place that holds every item of a unit is no change to its release.

The engineering shape: a unit whose devices all sit in one place `C1` inside it, so each reference
designation prints `+C1-<tag>`. A new issue drops the place and the references print `-<tag>`.

The rule (baseline spec L2, decision model-0146): a change list is relative to the unit. The listing
drops the location that holds every item of the unit, so both issues list the same designations, the
change list reads "No changes." and `fr.verify` of the stored first issue stays clean.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_NAME = "placed"


def _build(*, place: bool) -> fr.BuildResult:
    """A unit of two lamps, in place `C1` when `place`, else in none."""

    @fr.unit(_NAME, revision=1, interface_version=1, date="2026-10-06", text="Issue", by="XX")
    def placed(u: fr.Design) -> _Open:
        if place:
            u.location("C1", "Place")
        u.device("lamp1", "DEMO-LAMP-24", place="C1" if place else None)
        u.device("lamp2", "DEMO-LAMP-24", place="C1" if place else None)
        return _Open()

    d = fr.design("demo_parts")
    d.add(placed, "U1")
    return fr.build(d)


def test_place_holding_a_whole_unit_is_no_change(tmp_path: Path) -> None:
    """Dropping the place gives "No changes." and the stored release still verifies."""
    baselines = tmp_path / "baselines"
    fr.release(_build(place=True), baselines, unit=_NAME)
    rebuilt = _build(place=False)
    assert "No changes." in fr.diff(rebuilt, baselines, unit=_NAME)
    assert not fr.verify(rebuilt, baselines)
