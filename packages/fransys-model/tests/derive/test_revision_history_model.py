"""Tests for `derive.revision_history` (units spec U4)."""

from typing import Any

import pytest
from query_builders import reversed_tables

from fransys_model.derive import revision_history
from fransys_model.kernel import Draft, Id, Origin, SchemaError, freeze, make_id
from fransys_model.vocab.core import Unit, UnitRelease
from fransys_model.vocab.revision import Revision

_ORIGIN = Origin(file="test_revision_history_model.py", line=1, note="fixture")
_RELEASE_KEY = ("unit_release", "board", "1", "3")
_RELEASE = make_id(UnitRelease, _RELEASE_KEY)


def _unit() -> tuple[UnitRelease, Unit]:
    release = UnitRelease(
        id=_RELEASE,
        key=_RELEASE_KEY,
        name="board",
        version=1,
        revision=3,
        interface="1",
    )
    return release, Unit(
        id=make_id(Unit, ("board",)), key=("board",), release=release.id, parent=None
    )


def _revision(key: str, **fields: Any) -> Revision:
    base: dict[str, Any] = {
        "id": make_id(Revision, (key,)),
        "key": (key, "revision"),
        "release": None,
        "version": 1,
        "revision": 1,
        "date": "2026-01-01",
        "text": "",
        "created": "OJB",
    }
    return Revision(**{**base, **fields})


def test_three_out_of_order_entries_of_one_release_sort_by_date() -> None:
    """Three `Revision` entries authored out of date order come back in date order."""
    r_mid = _revision("mid", release=_RELEASE, revision=2, date="2026-02-01")
    r_first = _revision("first", release=_RELEASE, revision=1, date="2026-01-01")
    r_last = _revision("last", release=_RELEASE, revision=3, date="2026-03-01")
    draft = Draft()
    draft.extend(_unit(), origin=_ORIGIN)
    draft.extend((r_mid, r_first, r_last), origin=_ORIGIN)
    model = freeze(draft)
    history = revision_history(model, _RELEASE)
    assert len(history) == 3
    assert history == (r_first, r_mid, r_last)


def test_none_selects_only_the_projects_own_entries() -> None:
    """A release's `Revision` entries never show up in the project's own history (`None`)."""
    project_entry = _revision("proj", release=None, date="2026-01-01", text="Project text")
    unit_entry = _revision("unit", release=_RELEASE, date="2026-01-01", text="Unit text")
    draft = Draft()
    draft.extend(_unit(), origin=_ORIGIN)
    draft.extend((project_entry, unit_entry), origin=_ORIGIN)
    model = freeze(draft)
    history = revision_history(model, None)
    assert len(history) == 1
    assert history[0].text == "Project text"
    # examined: the unit's own entry is really absent, not merely uncounted
    assert "Unit text" not in {entry.text for entry in history}


def test_a_three_digit_revision_sorts_after_a_two_digit_one_same_date() -> None:
    """Revision 99 before 100: a sort on the revision's text puts `"100"` first, since `"1" < "9"`.

    Same date, so only the revision-order tie-break decides. Sorting the ints gets it right; a
    sort on `str(revision)` would not.
    """
    hundred = _revision("hundred", release=_RELEASE, revision=100, date="2026-01-01")
    ninety_nine = _revision("ninety-nine", release=_RELEASE, revision=99, date="2026-01-01")
    draft = Draft()
    draft.extend(_unit(), origin=_ORIGIN)
    draft.extend((hundred, ninety_nine), origin=_ORIGIN)
    model = freeze(draft)
    history = revision_history(model, _RELEASE)
    assert len(history) == 2
    assert history == (ninety_nine, hundred)
    naive = sorted((hundred, ninety_nine), key=lambda entry: str(entry.revision))
    assert tuple(naive) != history


def test_date_orders_first_and_id_breaks_a_full_tie_table_order_independent() -> None:
    """Date outranks revision order; two entries tied on both date and revision fall to id.

    `a` is revision 2 dated first; `b` is revision 1 dated second -- date and revision
    order disagree, so a sort keyed on revision alone would get this wrong. `c`/`d` share
    one date and one revision, so only `id` orders them. Checked under `reversed_tables`
    too, so canonical table order is never what makes this pass.
    """
    a = _revision("a", release=_RELEASE, revision=2, date="2026-01-01")
    b = _revision("b", release=_RELEASE, revision=1, date="2026-02-01")
    c = _revision("c", release=_RELEASE, revision=3, date="2026-03-01")
    d = _revision("d", release=_RELEASE, revision=3, date="2026-03-01")
    expected = tuple(sorted((c, d), key=lambda entry: entry.id))
    draft = Draft()
    draft.extend(_unit(), origin=_ORIGIN)
    draft.extend((d, b, c, a), origin=_ORIGIN)
    model = freeze(draft)
    history = revision_history(model, _RELEASE)
    assert len(history) == 4
    assert history == (a, b, *expected)
    assert revision_history(reversed_tables(model), _RELEASE) == history


def test_one_date_lists_the_pair_in_numeric_order_across_versions() -> None:
    """Same date: 1.1 .. 1.10 in numeric order, 1.9 before 1.10, and 1.10 before 2.1 (acceptance 8).

    A sort on the printed texts would put `"1.10"` before `"1.2"`; a sort on the revision alone
    would put `2.1` before `1.10`.
    """
    entries = [_revision(f"v1r{n}", release=_RELEASE, version=1, revision=n) for n in range(1, 11)]
    v2 = _revision("v2r1", release=_RELEASE, version=2, revision=1)
    draft = Draft()
    draft.extend(_unit(), origin=_ORIGIN)
    draft.extend((v2, *reversed(entries)), origin=_ORIGIN)
    history = revision_history(freeze(draft), _RELEASE)
    assert [(entry.version, entry.revision) for entry in history] == [
        *((1, n) for n in range(1, 11)),
        (2, 1),
    ]
    naive = sorted((*entries, v2), key=lambda entry: f"{entry.version}.{entry.revision}")
    assert tuple(naive) != history


def test_an_earlier_date_at_a_later_version_sorts_before_a_later_date() -> None:
    """Date wins: 2.1 dated first comes before 1.10 dated second, whatever the pair says."""
    early_v2 = _revision("early-v2", release=_RELEASE, version=2, revision=1, date="2026-01-01")
    late_v1 = _revision("late-v1", release=_RELEASE, version=1, revision=10, date="2026-02-01")
    draft = Draft()
    draft.extend(_unit(), origin=_ORIGIN)
    draft.extend((late_v1, early_v2), origin=_ORIGIN)
    assert revision_history(freeze(draft), _RELEASE) == (early_v2, late_v1)


def test_an_unknown_release_raises() -> None:
    """A release id the model does not hold is refused, the same `require`-based pattern."""
    model = freeze(Draft())
    with pytest.raises(SchemaError):
        revision_history(model, Id(kind="unit_release", value="9" * 32))
