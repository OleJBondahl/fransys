"""Terminal numbers and cable cores are each the lowest free integer (M4)."""

from decimal import Decimal

from author_catalogue import _ORIGIN, _library, _part
from fransys_author.surface import design
from series_parts import core_ends, series_library

from fransys_model.kernel import make_id
from fransys_model.vocab import CableProductFacet, PartCategory

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


def test_a_series_takes_the_lowest_free_terminals_around_the_taken_ones() -> None:
    d = design(series_library(), place="C1")
    q1, m1 = d.device("Q1", "TEST-MCB-3P"), d.device("M1", "TEST-MOTOR-3P")
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="TEST-TERM-PE")
    for n in (1, 2, 4):
        x1[n]
    d.series(q1.main, x1, d.cable("W1", "TEST-CBL-4"), m1, wire=WIRE)
    cores = core_ends(d)
    assert [x1[n].outer.id in cores[i] for i, n in ((1, 3), (2, 5), (3, 6))] == [True] * 3


def test_a_gnye_core_in_the_middle_is_skipped_by_the_series() -> None:
    d = design(_lib_with_gnye_second(), place="C1")
    q1, m1 = d.device("Q1", "TEST-MCB-3P"), d.device("M1", "TEST-MOTOR-3P")
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="TEST-TERM-PE")
    d.series(q1.main, x1, d.cable("W1", "TEST-CBL-5"), m1, wire=WIRE)
    cores = core_ends(d)
    pe = m1.load["PE"].id
    assert sorted(cores) == [1, 2, 3, 4]
    assert [i for i, ends in cores.items() if pe in ends] == [2]
    assert [x1[n].outer.id in cores[i] for i, n in ((1, 1), (3, 2), (4, 3))] == [True] * 3
