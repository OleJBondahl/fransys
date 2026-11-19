"""Field case: a place that holds every item of a unit is no change to its release.
The bug: none, kept by design; the place holding a whole unit printed in each designation and would look changed.
Fixed by model-0146: the change list is relative to the unit, so it drops the location that holds all its items."""

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


class _Boundary(NamedTuple):
    """A unit that hands back its interface device."""

    J1: fr.Device


@fr.unit("leaf", revision=1, interface_version=1, date="2026-11-19", text="Issue", by="XX")
def _leaf(u: fr.Design) -> _Boundary:
    return _Boundary(u.device("J1", "DEMO-CONN-2P", interface=True))


@fr.unit("holder", revision=1, interface_version=1, date="2026-11-19", text="Issue", by="XX", title="Holder", number="H-1")
def _holder(u: fr.Design) -> _Open:
    """The leaf placed once under a function scope of the holder."""
    with u.function("S1", "Scope one"):
        u.add(_leaf, "U1")
    return _Open()


def test_a_released_leaf_nested_under_a_function_scope_still_verifies(tmp_path: Path) -> None:
    """The scope the placement sits in is outside the leaf: its baseline rows never print it."""
    alone = fr.design("demo_parts")
    alone.add(_leaf, "U1")
    fr.release(fr.build(alone), tmp_path, unit="leaf")
    nested = fr.design("demo_parts")
    nested.add(_holder, "C1")
    result = fr.build(nested)
    assert not fr.verify(result, tmp_path)
    fr.release(result, tmp_path, unit="holder")
