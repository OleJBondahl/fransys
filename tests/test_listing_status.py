"""`listing_status`: a stored listing compared under the rules of the release that cut it (LS3).

One PE-strip fixture: three motors, two PE wires. The twin lands a wire on another motor.
"""

import dataclasses
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import GNYE

from fransys_model.derive import baseline
from fransys_model.vocab.tables import units


class _Open(NamedTuple):
    pass


def _wire(u: Any, wired: tuple[str, ...]) -> None:
    pe = u.terminal_strip("X1", "DEMO-TB-PE-2.5")
    motors = {n: u.device(n, "DEMO-MOTOR-4KW") for n in ("M1", "M2", "M3")}
    for i, name in enumerate(wired, 1):
        u.series(motors[name].motor["PE"], pe[i].inner, wire=(GNYE, 2.5))


@fr.unit("ls-bar", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _bar_unit(u: Any) -> _Open:
    _wire(u, ("M1", "M2"))
    return _Open()


@fr.unit("ls-bar", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _twin_unit(u: Any) -> _Open:
    _wire(u, ("M1", "M3"))
    return _Open()


def _model(unit: Any) -> tuple[Any, Any]:
    d = fr.design("demo_parts")
    d.project(title="Status", number="LS-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    d.location("CAB", "Cabinet")
    d.add(unit, "B1", place="CAB")
    model = fr.build(d).model
    return model, next(uid for uid, u in units(model).items() if u.key[0] == "B1")


_MODEL, _UNIT = _model(_bar_unit)
_TWIN, _TWIN_UNIT = _model(_twin_unit)


def _stored(rules: baseline.ListingRules) -> str:
    return baseline.dumps(baseline.listing(_MODEL, _UNIT, rules))


def _status(stored: str, version: str, model: Any = _MODEL, unit: Any = _UNIT) -> Any:
    return baseline.listing_status(stored, model, unit, version)


@pytest.mark.parametrize("version", ["0.18.4", "0.19.8"])
def test_a_listing_cut_under_todays_rules_is_the_same(version: str) -> None:
    assert _status(_stored(baseline.ListingRules()), version).state == "same"


def test_a_changed_unit_differs_under_todays_rules_too() -> None:
    status = _status(_stored(baseline.ListingRules()), "0.19.8", _TWIN, _TWIN_UNIT)
    assert (status.state, status.sections) == ("differs", ("conductors",))


def test_a_listing_older_than_the_table_is_too_old_never_compared_under_today() -> None:
    assert _status(_stored(baseline.ListingRules()), "0.9.0").state == "too_old"
    assert _status(_stored(baseline.ListingRules()), "").state == "too_old"


def test_a_version_the_table_does_not_know_is_refused_even_when_the_text_is_equal() -> None:
    """The refusal comes before the equality check: no `fransys` entry is never "same"."""
    assert _status(_stored(baseline.ListingRules()), "").state == "too_old"
    assert _status(_stored(baseline.ListingRules()), "0.9.0").state == "too_old"


def _blocks() -> tuple[Any, Any]:
    from listing_golden_cases import _all_moves

    model = _all_moves()
    return model, next(uid for uid, u in units(model).items() if u.key == ("C1", "unit"))


def test_rows_the_old_holder_rule_cannot_print_are_left_out_and_counted() -> None:
    """A block numbered before 0.18.2 has no number in today's model: one state, not `differs`."""
    model, unit = _blocks()
    stored = baseline.dumps(baseline.listing(model, unit, baseline.ListingRules(holder_designation=False)))
    status = baseline.listing_status(stored, model, unit, "0.18.1")
    assert (status.state, status.sections, status.unchecked) == ("rows_unchecked", (), 3)
    assert status.moved_in == "0.18.2"


def test_a_real_change_beside_the_left_out_rows_still_differs() -> None:
    model, unit = _blocks()
    listing = baseline.listing(model, unit, baseline.ListingRules(holder_designation=False))
    rows = tuple(dataclasses.replace(c, colour="BU") if c.a == "-M1:PE" else c for c in listing.conductors)
    stored = baseline.dumps(dataclasses.replace(listing, conductors=rows))
    status = baseline.listing_status(stored, model, unit, "0.18.1")
    assert (status.state, status.sections) == ("differs", ("conductors",))
