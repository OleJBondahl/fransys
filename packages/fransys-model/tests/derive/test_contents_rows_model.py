"""Tests for `contents_rows` (units spec P8, pdf-0016)."""

from fransys_model.derive import contents_rows
from fransys_model.derive.rows import HarnessCable, HarnessEnd
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item

_CABLE_ID = make_id(Item, ("cable",))


def _end(designation: str) -> HarnessEnd:
    """A minimal `HarnessEnd`, only `designation` load-bearing for this pure reshaping test."""
    return HarnessEnd(
        item=make_id(Item, (f"end-{designation or 'blank'}",)),
        designation=designation,
        connector=None,
        style=None,
        pincount=None,
        gender=None,
        mpn=None,
        pins=(),
    )


def _cable(*end_designations: str, key: str = "cable") -> HarnessCable:
    """A `HarnessCable` with the given ends, in order; the other seven fields are fixed values."""
    return HarnessCable(
        cable=make_id(Item, (key,)),
        designation="-W1",
        mpn="MPN-1",
        description="Invented cable",
        core_count=4,
        gauge_mm2=None,
        shielded=None,
        length_mm=1500,
        cores=(),
        ends=tuple(_end(d) for d in end_designations),
    )


def test_two_non_blank_ends_join_by_en_dash_in_their_own_order() -> None:
    """Two non-blank ends print `"<a> \N{EN DASH} <b>"`, in the cable's own end order."""
    (row,) = contents_rows((_cable("-A1", "-B2"),))
    assert row.ends == "-A1 \N{EN DASH} -B2"


def test_one_blank_end_drops_both_the_end_and_its_dash() -> None:
    """A blank end (`designation == ""`) contributes neither text nor a dangling dash."""
    (row,) = contents_rows((_cable("", "-B2"),))
    assert row.ends == "-B2"
    (row,) = contents_rows((_cable("-A1", ""),))
    assert row.ends == "-A1"


def test_both_ends_blank_gives_an_empty_string() -> None:
    """Both ends blank: an empty cell, not a lone en dash."""
    (row,) = contents_rows((_cable("", ""),))
    assert row.ends == ""


def test_three_or_more_ends_all_print_none_dropped_except_blanks() -> None:
    """A splice (3+ ends): CONTENTS prints every non-blank end, unlike `CableListRow`'s two-cap."""
    (row,) = contents_rows((_cable("-A1", "-B2", "-C3"),))
    assert row.ends == "-A1 \N{EN DASH} -B2 \N{EN DASH} -C3"
    (row,) = contents_rows((_cable("-A1", "", "-C3"),))
    assert row.ends == "-A1 \N{EN DASH} -C3"


def test_the_other_seven_fields_are_a_straight_passthrough_of_the_harness_cable() -> None:
    """`cable`, `designation`, `mpn`, `description`, `core_count`, `gauge_mm2` and `length_mm`
    are copied verbatim from the `HarnessCable`, unaffected by the `ends` join."""
    cable = _cable("-A1", "-B2", key="w9")
    (row,) = contents_rows((cable,))
    assert row.cable == cable.cable
    assert row.designation == cable.designation
    assert row.mpn == cable.mpn
    assert row.description == cable.description
    assert row.core_count == cable.core_count
    assert row.gauge_mm2 == cable.gauge_mm2
    assert row.length_mm == cable.length_mm


def test_order_is_preserved_not_resorted() -> None:
    """`contents_rows` does not re-sort: the caller's own cable order comes back unchanged."""
    first = _cable("-A1", key="w1")
    second = _cable("-B1", key="w2")
    rows = contents_rows((second, first))
    assert [row.cable for row in rows] == [second.cable, first.cable]


def test_no_cables_returns_no_rows() -> None:
    """No cables in, no rows out."""
    assert contents_rows(()) == ()
