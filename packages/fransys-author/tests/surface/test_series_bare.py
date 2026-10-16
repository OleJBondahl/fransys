"""A series between two functions with no line side pairs their pins in pin order (C6.2)."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.kernel import Draft, make_id
from fransys_model.vocab import Conductor, FunctionKind, PartCategory, PortRole, PortTemplate

from ..conftest import _ORIGIN, _function, _library, _part  # noqa: TID252 -- importlib mode puts tests/ on no path
from ..equivalence.series_parts import series_library  # noqa: TID252 -- importlib mode puts tests/ on no path

WIRE = ("BK", 0.75)
# (mpn, [(name, marking)] in the part file's order)
_CONNECTORS = {
    "TEST-CONN-4": [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")],
    "TEST-CONN-3": [("1", "1"), ("2", "2"), ("3", "3")],
    "TEST-CONN-NAMED": [("a", "1"), ("b", "2")],
    "TEST-CONN-NAMED-REVERSED": [("b", "1"), ("a", "2")],
    "TEST-CONN-OTHER": [("x", "1"), ("y", "2")],
}


@pytest.fixture(scope="module")
def lib() -> Draft:
    draft = series_library()
    library = _library(draft, "test-bare")
    for mpn, pins in _CONNECTORS.items():
        part = _part(
            draft, library, manufacturer="TestCo", mpn=mpn,
            category=PartCategory.CONNECTOR, letter="J",
        )  # fmt: skip
        fn = _function(draft, part, "x", FunctionKind.CONNECTOR)
        for name, marking in pins:
            key = (*fn.key, "port", name)
            draft.add(
                PortTemplate(
                    id=make_id(PortTemplate, key),
                    key=key,
                    function=fn.id,
                    name=name,
                    role=PortRole.GENERIC,
                    marking=marking,
                ),
                origin=_ORIGIN,
            )
    return draft


def _wires(d) -> set[frozenset]:
    return {frozenset((r.a, r.b)) for r in d.draft().records() if isinstance(r, Conductor)}


def _pairs(a, b, names: list[tuple[str, str]]) -> set[frozenset]:
    return {frozenset((a[x].id, b[y].id)) for x, y in names}


def test_two_four_pin_connectors_pair_one_to_one_in_pin_order(lib: Draft) -> None:
    d = design(lib, place="C1")
    j1, j2 = d.device("J1", "TEST-CONN-4"), d.device("J2", "TEST-CONN-4")
    d.series(j1.x, j2.x, wire=WIRE)
    assert _wires(d) == _pairs(j1.x, j2.x, [(n, n) for n in "1234"])


def test_pins_with_other_names_pair_in_pin_order_through_a_cable(lib: Draft) -> None:
    d = design(lib, place="C1")
    j1, j2 = d.device("J1", "TEST-CONN-NAMED"), d.device("J2", "TEST-CONN-OTHER")
    w1 = d.cable("W1", "TEST-CBL-3")
    d.series(j1.x, w1, j2.x, wire=WIRE)
    cores = {frozenset((r.a, r.b)) for r in d.draft().records() if isinstance(r, Conductor)}
    assert cores == _pairs(j1.x, j2.x, [("a", "x"), ("b", "y")])


def test_a_strip_between_carries_the_pairs(lib: Draft) -> None:
    d = design(lib, place="C1")
    j1, j2 = d.device("J1", "TEST-CONN-3"), d.device("J2", "TEST-CONN-3")
    x1 = d.terminal_strip("X1", "TEST-TERM", 3)
    d.series(j1.x, x1, j2.x, wire=WIRE)
    assert len(_wires(d)) == 6


def test_unequal_pin_counts_name_both(lib: Draft) -> None:
    d = design(lib, place="C1")
    j1, j2 = d.device("J1", "TEST-CONN-4"), d.device("J2", "TEST-CONN-3")
    with pytest.raises(AuthorError, match=r"J1\.x has 4 pins and J2\.x has 3"):
        d.series(j1.x, j2.x, wire=WIRE)


def test_equal_pin_names_in_different_orders_name_both_orders(lib: Draft) -> None:
    d = design(lib, place="C1")
    j1, j2 = d.device("J1", "TEST-CONN-NAMED"), d.device("J2", "TEST-CONN-NAMED-REVERSED")
    with pytest.raises(AuthorError, match=r"a, b against b, a"):
        d.series(j1.x, j2.x, wire=WIRE)


def test_a_sideless_function_in_the_middle_raises(lib: Draft) -> None:
    d = design(lib, place="C1")
    j1, j2, j3 = (d.device(f"J{i}", "TEST-CONN-3") for i in (1, 2, 3))
    with pytest.raises(AuthorError, match=r"J2\.x has no line/load pole pair.*j2\.x\.pins"):
        d.series(j1.x, j2.x, j3.x, wire=WIRE)


def test_a_sideless_end_against_a_supply_raises(lib: Draft) -> None:
    d = design(lib, place="C1")
    psu = d.device("G1", "TEST-PSU-24V")
    dc = d.dc_supply("24VDC", psu.out)
    j1 = d.device("J1", "TEST-CONN-NAMED")
    with pytest.raises(AuthorError, match=r"J1\.x has no line/load pole pair.*j1\.x\.pins"):
        d.series(dc.plus, j1.x, wire=WIRE)
