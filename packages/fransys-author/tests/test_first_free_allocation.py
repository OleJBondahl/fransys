"""Terminal numbers, cable cores and bar screws are each the lowest free integer (M4)."""

from decimal import Decimal

import fransys_parts
import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.kernel import make_id
from fransys_model.vocab import CableProductFacet, Conductor, ConductorKind, CoreFacet, PartCategory

from .conftest import _ORIGIN, _library, _part
from .equivalence.series_parts import series_library

WIRE = ("BK", 2.5)


def _lib_with_gnye_second():
    """The series library plus a five-core cable whose GNYE core is the second."""
    draft = series_library()
    cable = _part(
        draft,
        _library(draft, "planted"),
        manufacturer="TestCo",
        mpn="TEST-CBL-5",
        category=PartCategory.CABLE,
        letter="W",
    )
    key = (*cable.key, "cable_product")
    colours = ("BN", "GNYE", "BU", "BK", "GY")
    facet = CableProductFacet(
        id=make_id(CableProductFacet, key),
        key=key,
        subject=cable.id,
        core_colours=colours,
        gauge_mm2=Decimal("1.5"),
        shielded=False,
    )
    draft.add(facet, origin=_ORIGIN)
    return draft


def _core_ends(d):
    records = d.draft().records()
    index = {r.subject: r.index for r in records if isinstance(r, CoreFacet)}
    return {
        index[r.id]: frozenset((r.a, r.b))
        for r in records
        if isinstance(r, Conductor) and r.kind is ConductorKind.CORE
    }


def test_a_series_takes_the_lowest_free_terminals_around_the_taken_ones() -> None:
    d = design(series_library(), place="C1")
    q1, m1 = d.device("Q1", "TEST-MCB-3P"), d.device("M1", "TEST-MOTOR-3P")
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="TEST-TERM-PE")
    for n in (1, 2, 4):
        x1[n]
    d.series(q1.main, x1, d.cable("W1", "TEST-CBL-4"), m1, wire=WIRE)
    cores = _core_ends(d)
    assert [x1[n].outer.id in cores[i] for i, n in ((1, 3), (2, 5), (3, 6))] == [True] * 3


def test_a_gnye_core_in_the_middle_is_skipped_by_the_series() -> None:
    d = design(_lib_with_gnye_second(), place="C1")
    q1, m1 = d.device("Q1", "TEST-MCB-3P"), d.device("M1", "TEST-MOTOR-3P")
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="TEST-TERM-PE")
    d.series(q1.main, x1, d.cable("W1", "TEST-CBL-5"), m1, wire=WIRE)
    cores = _core_ends(d)
    pe = m1.load["PE"].id
    assert sorted(cores) == [1, 2, 3, 4]
    assert [i for i, ends in cores.items() if pe in ends] == [2]
    assert [x1[n].outer.id in cores[i] for i, n in ((1, 1), (3, 2), (4, 3))] == [True] * 3


def test_bar_screws_are_taken_in_order_and_the_last_is_the_twentieth() -> None:
    demo = fransys_parts.load("demo_parts")
    d = design(demo, place="C1")
    pe1 = d.device("PE1", "DEMO-PEBAR-20")
    for i in range(1, 21):
        m = d.device(f"M{i}", "DEMO-MOTOR-4KW")
        d.detail.wire(m.motor["PE"], pe1.pe, wire=("GNYE", 2.5))
    m21 = d.device("M21", "DEMO-MOTOR-4KW")
    with pytest.raises(AuthorError, match="has 20 screws and all are taken"):
        d.detail.wire(m21.motor["PE"], pe1.pe, wire=("GNYE", 2.5))
