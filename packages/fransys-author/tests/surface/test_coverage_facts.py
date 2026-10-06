"""EA-COVERAGE P2 facts: each call writes or reads exactly what the engine call does."""

from decimal import Decimal

import fransys_parts
import pytest
from fransys_author import AuthorError
from fransys_author.surface import Device, Fn, design

from fransys_model.vocab import Boundary, BoundaryValuesFacet, Operating, Rating
lazy from fransys_model.kernel import Draft

_RATING = Rating(voltage_ac_v=Decimal(250), current_ac_a=Decimal("0.5"))
_OPERATING = Operating(nominal_voltage_v=Decimal(24), max_voltage_v=Decimal(30))
_PART = (
    'schema = 1\n\n[part]\nmpn = "RT-1"\nmanufacturer = "Demo"\ndescription = "d"\n'
    'category = "generic"\nclass_code = "X"\n\n[rating]\nvoltage_ac_v = "500"\n\n'
    '[[function]]\nname = "coil"\nkind = "generic"\nports = [{ name = "A", role = "generic" }]\n'
    '\n[function.operating]\nnominal_voltage_v = "24"\n'
)


class Rt1(Device):
    mpn = "RT-1"


@pytest.fixture
def rated(tmp_path) -> Draft:
    (tmp_path / "parts").mkdir()
    (tmp_path / "library.toml").write_text(
        'schema = 1\nname = "l"\nversion = "0.1.0"\ndescription = "d"\n'
    )
    (tmp_path / "parts" / "rt1.toml").write_text(_PART)
    return fransys_parts.load_path(tmp_path)


def _records(d) -> list:
    return d.draft().records()


def test_project_and_revision_write_the_engine_records(parts: Draft) -> None:
    d, e = design(parts), design(parts)
    d.project(title="T", number="N", customer="C", revision=2, author="A", notice="n")
    d.revision(1, date="2026-01-01", text="first", created="A", checked="B")
    d.revision(2, date="2026-02-01", text="second", created="A", version=3)
    e._engine.project(title="T", number="N", customer="C", revision=2, author="A", notice="n")
    e._engine.revision(1, date="2026-01-01", text="first", created="A", checked="B")
    e._engine.revision(2, date="2026-02-01", text="second", created="A", version=3)
    assert _records(d) == _records(e)
    assert len(_records(d)) > len(_records(design(parts)))


@pytest.mark.parametrize("part", [Rt1, "RT-1"], ids=["class", "mpn"])
def test_reads_equal_the_engine_value(rated: Draft, part) -> None:
    d = design(rated)
    assert d.rating(part) == d._engine.rating("RT-1") == Rating(voltage_ac_v=Decimal(500))
    assert d.operating(part, "coil") == d._engine.operating("RT-1", "coil")
    assert d.operating(part, "coil") == Operating(nominal_voltage_v=Decimal(24))
    assert d.rating(part, "coil") == d._engine.rating("RT-1", "coil")


def test_a_tuple_part_raises(rated: Draft) -> None:
    d = design(rated)
    with pytest.raises(AuthorError, match="MPN string or a part class"):
        d.rating(("Demo", "RT-1"))  # ty: ignore[invalid-argument-type] -- the refusal under test
    with pytest.raises(AuthorError, match="MPN string or a part class"):
        d.operating(("Demo", "RT-1"), "coil")  # ty: ignore[invalid-argument-type] -- the refusal under test


def test_an_mpn_of_two_makers_raises(parts: Draft) -> None:
    d = design(parts)
    for call in (lambda: d.rating("TEST-SHARED"), lambda: d.operating("TEST-SHARED", "f")):
        with pytest.raises(AuthorError, match=r"\(Alpha, Beta\).*one part per MPN"):
            call()


def test_an_unknown_mpn_gets_the_engine_error(parts: Draft) -> None:
    with pytest.raises(AuthorError, match="NOPE-9"):
        design(parts).rating("NOPE-9")


def _boundary_fn(d) -> Fn:
    function = d._engine.item("TEST-CONN-2P", tag="X1", name="X1").as_function()
    return Fn("X1", function, d._engine)


def test_limits_without_a_value_raises_use_interface_true(parts: Draft) -> None:
    with pytest.raises(AuthorError, match=r"use interface=True on the device"):
        _boundary_fn(design(parts)).limits()


def _in_unit(parts: Draft):
    d = design(parts)
    root = d._engine
    d._engine = d._engine.unit("io", revision=1, interface="1")  # ty: ignore[invalid-assignment] -- test-only seam until EA-UNITS-RUNS
    return root, _boundary_fn(d)


def test_limits_writes_one_boundary_with_its_values(parts: Draft) -> None:
    root, fn = _in_unit(parts)
    assert fn.limits(rating=_RATING, operating=_OPERATING) is fn
    (boundary,) = [r for r in root.draft().records() if isinstance(r, Boundary)]
    (facet,) = [r for r in root.draft().records() if isinstance(r, BoundaryValuesFacet)]
    assert facet.subject == boundary.id
    assert (facet.rating, facet.operating) == (_RATING, _OPERATING)


def test_limits_outside_a_unit_raises_the_engine_error(parts: Draft) -> None:
    with pytest.raises(AuthorError, match="needs a unit"):
        _boundary_fn(design(parts)).limits(rating=_RATING)


def test_design_has_no_interface_call(parts: Draft) -> None:
    assert not hasattr(design(parts), "interface")
