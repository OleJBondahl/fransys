"""EA7: `device(..., mounted_on=)` writes the engine script's mount links and fails by name."""

from typing import Any

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design
from fransys_author.surface._mount import mount

from fransys_model.vocab import (
    Conductor,
    ConductorKind,
    FunctionKind,
    Item,
    LinkKind,
    PartCategory,
)

from ..conftest import _function, _library, _part  # noqa: TID252 -- importlib mode puts tests/ on no path
from ..equivalence.series_parts import (  # noqa: TID252 -- same suite's stub parts
    _THREE,
    MINUS,
    _pin,
    _poles,
    series_library,
)

TWO = r"F1\.main has 3 poles; Q1 has main and main2 with 3 poles: say which"
NONE = r"F1\.main has 3 poles; Q1 has no function of 3 poles; it has: aux \(1\), main \(1\)"
_KIND = FunctionKind.PROTECTION
_SW = LinkKind.PROTECTIVE


@pytest.fixture(scope="module")
def lib():
    """The series library plus a part of two 3-pole functions and a part of two L- pins."""
    draft = series_library()
    extra = _library(draft, "test-mount")
    twin = _part(
        draft, extra, manufacturer="TestCo", mpn="TEST-2X3",
        category=PartCategory.PROTECTION, letter="Q",
    )  # fmt: skip
    _poles(draft, twin, "main", _KIND, _SW, _THREE)
    _poles(draft, twin, "main2", _KIND, _SW, _THREE)
    one = _part(
        draft, extra, manufacturer="TestCo", mpn="TEST-MCB-1X1",
        category=PartCategory.PROTECTION, letter="Q",
    )  # fmt: skip
    _poles(draft, one, "main", _KIND, _SW, [("1", "2")])
    _poles(draft, one, "aux", FunctionKind.CONTACT_NO, LinkKind.SWITCHED, [("13", "14")])
    minus = _part(
        draft, extra, manufacturer="TestCo", mpn="TEST-2MINUS",
        category=PartCategory.ELECTROMECHANICAL, letter="K",
    )  # fmt: skip
    _poles(draft, minus, "main", _KIND, _SW, _THREE)
    for name in ("coil", "spare"):
        _pin(draft, _function(draft, minus, name, FunctionKind.GENERIC), "A2", None, MINUS)
    return draft


def _links(d: Any) -> list[Conductor]:
    return [r for r in d.draft().records() if isinstance(r, Conductor)]


def test_mounted_on_writes_the_links_the_engine_script_writes(lib) -> None:
    d = design(lib, place="C1")
    k1 = d.device("K1", "TEST-KM-3P")
    d.device("F1", "TEST-OL-3P", mounted_on=k1)

    twin = design(lib, place="C1")
    k = twin._engine.item("TEST-KM-3P", tag="K1", name="K1")
    f = twin._engine.item("TEST-OL-3P", tag="F1", name="F1")
    for a, b in zip("246", "135", strict=True):
        twin._engine.link(k.fn("main")[a], f.fn("main")[b], kind="mount")
    twin._engine.link(k.fn("coil")["A2"], f.fn("pass")["A2"], kind="mount")
    assert _links(d) == _links(twin)
    assert len(_links(d)) == 4
    assert {c.kind for c in _links(d)} == {ConductorKind.MOUNT}


def test_mounted_on_pairs_load_side_to_line_side(lib) -> None:
    """Can-fail: pairing load to load puts K1's pin 1 where 2 belongs and this fails."""
    d = design(lib, place="C1")
    k1 = d.device("K1", "TEST-KM-3P")
    f1 = d.device("F1", "TEST-OL-3P", mounted_on=k1)
    joined = {frozenset((c.a, c.b)) for c in _links(d)}
    for load, line in zip("246", "135", strict=True):
        assert frozenset((k1.main[load].id, f1.main[line].id)) in joined
    assert frozenset((k1.coil.A2.id, f1.A2.id)) in joined


def test_a_carrier_function_may_be_named(lib) -> None:
    d = design(lib, place="C1")
    q1 = d.device("Q1", "TEST-2X3")
    f1 = d.device("F1", "TEST-MCB-3P", mounted_on=q1.main2)
    joined = {frozenset((c.a, c.b)) for c in _links(d)}
    assert joined == {
        frozenset((q1.main2[a].id, f1.main[b].id)) for a, b in zip("246", "135", strict=True)
    }


def test_two_carrier_functions_of_equal_poles_raise_naming_both(lib) -> None:
    d = design(lib, place="C1")
    q1 = d.device("Q1", "TEST-2X3")
    with pytest.raises(AuthorError, match=TWO):
        d.device("F1", "TEST-MCB-3P", mounted_on=q1)


def test_no_carrier_function_of_the_width_raises_with_counts(lib) -> None:
    d = design(lib, place="C1")
    q1 = d.device("Q1", "TEST-MCB-1X1")
    with pytest.raises(
        AuthorError,
        match=r"F1\.main has 3 poles; Q1 has no function of 3 poles; it has: aux \(1\), main \(1\)",
    ):
        d.device("F1", "TEST-MCB-3P", mounted_on=q1)


def test_a_pass_through_with_no_equal_conductor_raises(lib) -> None:
    d = design(lib, place="C1")
    q1 = d.device("Q1", "TEST-MCB-3P")
    with pytest.raises(
        AuthorError, match=r"F1\.pass\.A2 carries L-; Q1 has no pin of that conductor"
    ):
        d.device("F1", "TEST-OL-3P", mounted_on=q1)


def test_a_pass_through_with_two_equal_conductors_raises_naming_both(lib) -> None:
    d = design(lib, place="C1")
    k1 = d.device("K1", "TEST-2MINUS")
    with pytest.raises(AuthorError, match=r"carries L-; K1 has several: coil\.A2, spare\.A2"):
        d.device("F1", "TEST-OL-3P", mounted_on=k1)


def test_mounting_on_itself_raises(lib) -> None:
    d = design(lib, place="C1")
    f1 = d.device("F1", "TEST-OL-3P")
    with pytest.raises(AuthorError, match="F1 cannot be mounted on itself"):
        mount(d, f1, f1)


def test_the_item_keywords_reach_the_item_record(lib) -> None:
    d = design(lib, place="C1")
    d.device("X9", "TEST-KM-3P", description="spare", position=7, installed=False, external=True)
    d.device("X8", "TEST-KM-3P")
    items = {r.tag: r for r in d.draft().records() if isinstance(r, Item)}
    assert (items["X9"].description, items["X9"].position) == ("spare", 7)
    assert (items["X9"].installed, items["X9"].external) == (False, True)
    assert (items["X8"].description, items["X8"].position) == ("", None)
    assert (items["X8"].installed, items["X8"].external) == (True, False)


def test_device_refuses_a_part_two_makers_make(lib) -> None:
    d = design(lib)
    with pytest.raises(AuthorError, match="MPN 'TEST-SHARED' is ambiguous across manufacturers"):
        d.device("Q1", "TEST-SHARED")
