"""`s.boundary(fn, rating=, operating=)`: one `BoundaryValuesFacet` beside the `Boundary` (Q5)."""

import inspect
import os
from decimal import Decimal

import pytest
from fransys_author import AuthorError, Design, Scope

from fransys_model.vocab import Boundary, BoundaryValuesFacet, Operating, Rating

_RATING = Rating(voltage_ac_v=Decimal(250), current_ac_a=Decimal("0.5"))
_OPERATING = Operating(
    nominal_voltage_v=Decimal(24), min_voltage_v=Decimal(18), max_voltage_v=Decimal(30)
)


def _unit_scope(design: Design, name: str = "u1") -> Scope:
    return design.scope(name).unit("demo-unit", revision=1, interface="1")


def _facets(design: Design) -> list[BoundaryValuesFacet]:
    return [r for r in design.draft().records() if isinstance(r, BoundaryValuesFacet)]


def _boundaries(design: Design) -> list[Boundary]:
    return [r for r in design.draft().records() if isinstance(r, Boundary)]


def _here() -> int:
    frame = inspect.currentframe()
    assert frame is not None
    assert frame.f_back is not None
    return frame.f_back.f_lineno


def test_a_boundary_with_no_values_writes_no_facet(parts):
    d = Design(parts)
    u = _unit_scope(d)
    u.boundary(u.item("TEST-CONN-2P", tag="X1"))
    assert len(_boundaries(d)) == 1
    assert _facets(d) == []


@pytest.mark.parametrize(
    ("rating", "operating"),
    [(_RATING, None), (None, _OPERATING), (_RATING, _OPERATING)],
    ids=["rating", "operating", "both"],
)
def test_given_values_write_one_facet_on_the_boundary(parts, rating, operating):
    d = Design(parts)
    u = _unit_scope(d)
    x1 = u.item("TEST-CONN-2P", tag="X1")
    u.boundary(x1, rating=rating, operating=operating)
    (boundary,) = _boundaries(d)
    (facet,) = _facets(d)
    assert facet.subject == boundary.id
    assert facet.rating == rating
    assert facet.operating == operating


def test_the_facet_and_the_boundary_share_the_calling_line(parts):
    d = Design(parts)
    u = _unit_scope(d)
    x1 = u.item("TEST-CONN-2P", tag="X1")
    line = _here() + 1
    u.boundary(x1, rating=_RATING)
    (boundary,) = _boundaries(d)
    (facet,) = _facets(d)
    for record in (boundary, facet):
        origin = d.draft().origin_of(record.id)
        assert origin is not None
        assert os.path.normcase(origin.file) == os.path.normcase(__file__)
        assert origin.line == line


def test_the_facet_key_is_the_boundary_key_plus_boundary_values(parts):
    d = Design(parts)
    u = _unit_scope(d)
    u.boundary(u.item("TEST-CONN-2P", tag="X1"), operating=_OPERATING)
    (boundary,) = _boundaries(d)
    (facet,) = _facets(d)
    assert facet.key == (*boundary.key, "boundary_values")


def test_two_instances_of_one_unit_give_two_facets_that_do_not_collide(parts):
    d = Design(parts)
    for name in ("u1", "u2"):
        u = _unit_scope(d, name)
        u.boundary(u.item("TEST-CONN-2P", tag="X1"), rating=_RATING)
    facets = _facets(d)
    assert len(facets) == 2
    assert len({f.key for f in facets}) == 2
    assert len({f.id for f in facets}) == 2
    assert {f.subject for f in facets} == {b.id for b in _boundaries(d)}


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("rating", "250"),
        ("rating", 250.0),
        ("rating", {"voltage_ac_v": Decimal(250)}),
        ("rating", _OPERATING),
        ("operating", "24"),
        ("operating", _RATING),
        ("rating", Rating()),
        ("operating", Operating()),
    ],
    ids=[
        "rating-str",
        "rating-float",
        "rating-dict",
        "rating-is-an-operating",
        "operating-str",
        "operating-is-a-rating",
        "rating-empty",
        "operating-empty",
    ],
)
def test_a_wrong_or_empty_value_is_refused_and_writes_nothing(parts, keyword, value):
    d = Design(parts)
    u = _unit_scope(d)
    x1 = u.item("TEST-CONN-2P", tag="X1")
    before = list(d.draft().records())
    with pytest.raises(AuthorError, match=rf"{keyword}="):
        u.boundary(x1, **{keyword: value})
    assert list(d.draft().records()) == before
    assert _boundaries(d) == []
    assert _facets(d) == []


def test_a_refusal_leaves_the_good_value_unwritten_too(parts):
    d = Design(parts)
    u = _unit_scope(d)
    x1 = u.item("TEST-CONN-2P", tag="X1")
    with pytest.raises(AuthorError, match=r"operating="):
        u.boundary(x1, rating=_RATING, operating="24")  # ty: ignore[invalid-argument-type] -- a bare str where `Operating` is required, testing the refusal named in the match
    assert _boundaries(d) == []
    assert _facets(d) == []
    u.boundary(x1, rating=_RATING)
    assert len(_facets(d)) == 1


@pytest.mark.parametrize("values", [{}, {"rating": _RATING}, {"operating": _OPERATING}])
def test_a_scope_with_no_unit_still_refuses_with_or_without_values(parts, values):
    d = Design(parts)
    x1 = d.item("TEST-CONN-2P", tag="X1")
    with pytest.raises(AuthorError, match="needs a unit"):
        d.boundary(x1, **values)
    assert _boundaries(d) == []
    assert _facets(d) == []
