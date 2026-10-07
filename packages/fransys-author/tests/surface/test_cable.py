"""EA5, EA7: `d.cable` and `W1.core` build the engine script's records, and fail by name."""

from typing import TYPE_CHECKING, Any

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design
from fransys_author.surface._cable import Cable
from fransys_author.surface.colours import BK, BN, BU, GNYE

from fransys_model.vocab import CableFacet, Conductor, ConductorKind, CoreFacet
from fransys_model.vocab import Item as ModelItem

from ..equivalence.series_parts import series_library  # noqa: TID252 -- importlib mode puts tests/ on no path
from .test_does_not_lines import has_does_not

if TYPE_CHECKING:
    from fransys_author.surface import Design

    from fransys_model.kernel import Draft

WIRE = ("BK", 2.5)
FOUR, THREE = "TEST-CBL-4", "TEST-CBL-3"


@pytest.fixture(scope="module")
def lib() -> Draft:
    return series_library()


def _cores(d: Design) -> dict[int, frozenset[Any]]:
    """Core number -> the two port ids its conductor joins, in no order."""
    records = d.draft().records()
    facets = {r.subject: r.index for r in records if isinstance(r, CoreFacet)}
    return {
        facets[r.id]: frozenset((r.a, r.b))
        for r in records
        if isinstance(r, Conductor) and r.kind is ConductorKind.CORE
    }


def _field(d: Design) -> tuple[Any, Any, Any]:
    """Breaker, strip and motor of the field series; the cable between strip and motor."""
    q1, m1 = d.device("Q1", "TEST-MCB-3P"), d.device("M1", "TEST-MOTOR-3P")
    x1 = d.terminal_strip("X1", "TEST-TERM", pe="TEST-TERM-PE")
    return q1, x1, m1


def test_cores_map_in_order_and_the_gnye_core_goes_to_the_pe_port(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, x1, m1 = _field(d)
    w1 = d.cable("W1", FOUR, length_m=5)
    d.series(q1.main, x1, w1, m1, wire=WIRE)
    cores = _cores(d)
    load = m1.load
    outer = [x1[n].outer.id for n in (1, 2, 3)]
    assert [cores[i] for i in (1, 2, 3)] == [
        frozenset((o, load[p].id)) for o, p in zip(outer, "UVW", strict=True)
    ]
    assert cores[4] == {x1[4].outer.id, load["PE"].id}


def test_gnye_core_goes_to_the_pe_port(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, x1, m1 = _field(d)
    d.series(q1.main, x1, d.cable("W1", FOUR), m1, wire=WIRE)
    cores = _cores(d)
    pe = m1.load["PE"].id
    assert [i for i, ids in cores.items() if pe in ids] == [4]
    assert all(pe not in ids for i, ids in cores.items() if i != 4)


def test_a_core_of_another_colour_on_a_pe_port_raises(lib: Draft) -> None:
    d = design(lib)
    m1 = d.device("M1", "TEST-MOTOR-3P")
    w1 = d.cable("W1", FOUR)
    with pytest.raises(AuthorError, match="core 1 is BN: the PE core is GNYE"):
        w1.core(BN, m1.load["U"], m1.load["PE"])
    with pytest.raises(AuthorError, match="core 3 is BK: the PE core is GNYE"):
        w1.core(3, m1.load["PE"], m1.load["U"])
    w1.core(GNYE, m1.load["U"], m1.load["PE"])


def test_a_core_by_colour_and_by_number_is_one_record(lib: Draft) -> None:
    pair = []
    for which in (BN, 1):
        d = design(lib)
        m1 = d.device("M1", "TEST-MOTOR-3P")
        d.cable("W1", FOUR).core(which, m1.load["U"], m1.load["V"])
        pair.append([r for r in d.draft().records() if isinstance(r, Conductor | CoreFacet)])
    assert pair[0] == pair[1]
    assert len(pair[0]) == 2


def test_a_terminal_means_its_outer_port(lib: Draft) -> None:
    d = design(lib)
    m1, x1 = d.device("M1", "TEST-MOTOR-3P"), d.terminal_strip("X1", "TEST-TERM")
    d.cable("W1", THREE).core(BU, x1[1], m1.load["V"])
    assert _cores(d)[2] == {x1[1].outer.id, m1.load["V"].id}


def test_a_colour_twice_lists_the_numbers_and_a_missing_one_lists_the_colours(lib: Draft) -> None:
    d = design(lib)
    m1 = d.device("M1", "TEST-MOTOR-3P")
    two_bk = d._engine.cable(THREE, name="W9", tag="W9")
    two_bk._core_colours = (BK, BN, BK)  # the stub parts hold no doubled colour
    w9 = Cable("W9", two_bk)
    with pytest.raises(AuthorError, match=r"W9 has 2 BK cores, numbers \[1, 3\]: say the number"):
        w9.core(BK, m1.load["U"], m1.load["V"])
    w9.core(3, m1.load["U"], m1.load["V"])
    with pytest.raises(AuthorError, match=r"W2 has no 'GNYE' core; its colours: BN, BU, BK"):
        d.cable("W2", THREE).core(GNYE, m1.load["U"], m1.load["V"])
    with pytest.raises(AuthorError, match="core 9 is out of range"):
        d.cable("W3", THREE).core(9, m1.load["U"], m1.load["V"])


def test_length_m_is_whole_millimetres(lib: Draft) -> None:
    mm = {}
    for length in (5, 4.35, "2.5"):
        d = design(lib)
        d.cable("W1", THREE, length_m=length)
        (facet,) = [r for r in d.draft().records() if isinstance(r, CableFacet)]
        mm[length] = facet.length_mm
    assert mm == {5: 5000, 4.35: 4350, "2.5": 2500}  # 4.35 * 1000 is 4350.000000000001 as a float
    with pytest.raises(AuthorError, match=r"4\.3501"):
        design(lib).cable("W1", THREE, length_m=4.3501)
    with pytest.raises(AuthorError, match="not a number"):
        design(lib).cable("W1", THREE, length_m="long")
    with pytest.raises(TypeError):
        design(lib).cable("W1", THREE, length_mm=5000)  # ty: ignore[unknown-argument] -- not a spelling


def test_a_prefixed_tag_and_a_part_without_a_cable_product_raise(lib: Draft) -> None:
    with pytest.raises(AuthorError, match="write W1; cable"):
        design(lib).cable("-W1", THREE)
    with pytest.raises(AuthorError):
        design(lib).cable("W1", "TEST-MOTOR-3P")


def test_no_pe_part_on_the_strip_raises_the_strips_message(lib: Draft) -> None:
    d = design(lib)
    q1, m1 = d.device("Q1", "TEST-MCB-3P"), d.device("M1", "TEST-MOTOR-3P")
    x1 = d.terminal_strip("X1", "TEST-TERM")
    with pytest.raises(
        AuthorError, match=r"X1 has no PE terminal part: terminal_strip\(\.\.\., pe="
    ):
        d.series(q1.main, x1, d.cable("W1", FOUR), m1, wire=WIRE)


def test_a_gnye_core_with_a_neighbour_that_has_no_pe_raises(lib: Draft) -> None:
    d = design(lib)
    m1, k1 = d.device("M1", "TEST-MOTOR-3P"), d.device("K1", "TEST-KM-3P")
    with pytest.raises(AuthorError, match="W1 has a GNYE core, but K1 has no PE port"):
        d.series(k1.main, d.cable("W1", FOUR), m1, wire=WIRE)


def test_no_pe_port_leaves_the_gnye_core_spare(lib: Draft) -> None:
    d = design(lib)
    q1, k1 = d.device("Q1", "TEST-MCB-3P"), d.device("K1", "TEST-KM-3P")
    d.series(q1.main, d.cable("W1", FOUR), k1.main, wire=WIRE)
    assert sorted(_cores(d)) == [1, 2, 3]


def test_fewer_cores_than_poles_raises(lib: Draft) -> None:
    d = design(lib)
    q1, m1 = d.device("Q1", "TEST-MCB-3P"), d.device("M1", "TEST-MOTOR-3P")
    two = d._engine.cable(THREE, name="W2", tag="W2")
    two._core_colours = (BN, BU)
    with pytest.raises(AuthorError, match="W2 has 2 cores for 3 poles"):
        d.series(q1.main, Cable("W2", two), m1, wire=WIRE)


def test_cable_and_core_say_what_they_do_not_do() -> None:
    from fransys_author.surface._cable import Cables

    assert has_does_not(Cables.cable.__doc__)
    assert has_does_not(Cable.core.__doc__)
    assert has_does_not(Cable.__doc__)


def test_the_series_equals_the_engine_script(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1, x1, m1 = _field(d)
    d.series(q1.main, x1, d.cable("W1", FOUR, length_m=5), m1, wire=WIRE)

    twin = design(lib, place="C1")
    engine = twin._engine
    at = twin._place_node("C1")
    q = engine.item("TEST-MCB-3P", tag="Q1", name="Q1", at=at)
    m = engine.item("TEST-MOTOR-3P", tag="M1", name="M1", at=at)
    strip = engine.strip("X1", at=at)
    terminals = [strip.terminal("TEST-TERM", index=n) for n in (1, 2, 3)]
    pe = strip.terminal("TEST-TERM-PE", index=4)
    wiring = engine.wiring(colour="BK", gauge="2.5")
    for a, t in zip("246", terminals, strict=True):
        wiring(q.fn("main")[a], t.inner)
    cable = engine.cable(FOUR, name="W1", tag="W1", length_mm=5000, at=at)
    for index, (t, pin) in enumerate(zip(terminals, "UVW", strict=True), 1):
        cable.core(index, t.outer, m.fn("load")[pin])
    cable.core(4, pe.outer, m.fn("load")["PE"])

    def kept(x: Design) -> list[Any]:
        return [r for r in x.draft().records() if isinstance(r, Conductor | CoreFacet | CableFacet)]

    assert kept(d) == kept(twin)
    assert len(kept(d)) == 12


def test_a_strip_after_a_cable_is_entered_from_its_field_side(lib: Draft) -> None:
    d = design(lib, place="C1")
    q1 = d.device("Q1", "TEST-MCB-3P")
    x1, x2 = d.terminal_strip("X1", "TEST-TERM"), d.terminal_strip("X2", "TEST-TERM")
    d.series(q1.main, x1, d.cable("W1", FOUR), x2, wire=WIRE)
    cores = _cores(d)
    assert cores[1] == {x1[1].outer.id, x2[1].outer.id}
    wires = [
        r for r in d.draft().records() if isinstance(r, Conductor) and r.kind is ConductorKind.WIRE
    ]
    assert {frozenset((r.a, r.b)) for r in wires} >= {frozenset((q1.main[2].id, x1[1].inner.id))}


def test_a_cable_parent_is_the_items_parent(lib: Draft) -> None:
    d = design(lib)
    h1 = d.harness("W5")
    d.cable("W1", FOUR, parent=h1)
    d.cable("W2", FOUR)
    parents = {i.tag: i.parent for i in d.draft().records() if isinstance(i, ModelItem)}
    assert parents["W1"] == h1._item.id
    assert parents["W2"] is None


@pytest.mark.parametrize("kind", ["strip", "run", "terminal"])
def test_a_cable_parent_that_is_not_a_device_is_refused(lib: Draft, kind: str) -> None:
    d = design(lib)
    x1 = d.terminal_strip("X1", "TEST-TERM")
    parents = {"strip": x1, "run": x1.run("M", 2), "terminal": x1[1]}
    with pytest.raises(AuthorError, match=f"parent= takes a device, not a {kind}"):
        d.cable("W1", FOUR, parent=parents[kind])  # ty: ignore[invalid-argument-type] -- the refusal is the case
