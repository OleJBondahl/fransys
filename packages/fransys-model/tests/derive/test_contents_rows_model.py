"""Tests for `contents_rows` (pdf-0016)."""

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
