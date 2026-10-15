"""`d.pair(a, cable, b)` joins two ends pin for pin, and fails by name on a wrong use."""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.kernel import make_id
from fransys_model.vocab import CableProductFacet, Conductor, ConductorKind, CoreFacet, PartCategory

from ..conftest import _ORIGIN, _library, _part  # noqa: TID252 -- importlib mode puts tests/ on no path
from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path
from .test_does_not_lines import has_does_not

if TYPE_CHECKING:
    from fransys_author.surface import Design

    from fransys_model.kernel import Draft

STRIP, CABLE, CABLE_PE, SENSOR = "DEMO-TB-2.5", "DEMO-CBL-3X0.34", "TEST-CBL-4", "DEMO-SENSOR-2W"


def _cores(d: Design) -> dict[int, frozenset[Any]]:
    records = d.draft().records()
    facets = {r.subject: r.index for r in records if isinstance(r, CoreFacet)}
    return {
        facets[r.id]: frozenset((r.a, r.b))
        for r in records
        if isinstance(r, Conductor) and r.kind is ConductorKind.CORE
    }


def _parts() -> tuple[Design, Any, Any, Any]:
    d = design(pair_library(), place="C1")
    return d, d.terminal_strip("X8", STRIP), d.cable("W3", CABLE), d.device("B1", SENSOR)


def test_core_i_joins_pin_i_to_pin_i() -> None:
    d, x8, w3, b1 = _parts()
    d.pair(x8[1:3], w3, b1.sig)
    pins = b1.sig.pins
    assert _cores(d) == {
        1: frozenset((x8[1].outer.id, pins[0].id)),
        2: frozenset((x8[2].outer.id, pins[1].id)),
    }


def test_a_tuple_of_terminals_is_an_end() -> None:
    d, x8, w3, b1 = _parts()
    d.pair((x8[1], x8[3]), w3, b1.sig)
    assert len(_cores(d)) == 2


def test_the_gnye_core_is_left_spare_with_no_pe_end() -> None:
    d = design(pair_library(), place="C1")
    x8, b1 = d.terminal_strip("X8", STRIP), d.device("B1", SENSOR)
    d.pair(x8[1:3], d.cable("W3", CABLE_PE), b1.sig)
    assert sorted(_cores(d)) == [1, 2]


def test_a_middle_that_is_not_a_cable_raises() -> None:
    d, x8, _w3, b1 = _parts()
    with pytest.raises(AuthorError, match=r"takes a cable in the middle.*d\.cable"):
        d.pair(x8[1:3], b1, b1.sig)


def test_unequal_pin_counts_raise_naming_both_ends() -> None:
    d, x8, w3, b1 = _parts()
    with pytest.raises(AuthorError, match=r"leaves with 3 .* takes 2"):
        d.pair(x8[1:4], w3, b1.sig)


@pytest.mark.parametrize("bad", ["strip", "device", "port"])
def test_a_strip_a_device_or_a_port_as_an_end_raises(bad: str) -> None:
    d, x8, w3, b1 = _parts()
    end = {"strip": x8, "device": b1, "port": b1.sig.pins[0]}[bad]
    with pytest.raises(AuthorError, match=r"takes terminals or a function.*x8\[1:3\]"):
        d.pair(end, w3, b1.sig)


def test_pair_has_a_does_not_line() -> None:
    d, *_ = _parts()
    assert has_does_not(type(d).pair.__doc__)


def _bare_cable_library() -> Draft:
    """The pair library plus a cable part whose core table is empty."""
    draft = pair_library()
    lib = _library(draft, "test-bare")
    cable = _part(
        draft, lib, manufacturer="TestCo", mpn="TEST-CBL-BARE",
        category=PartCategory.CABLE, letter="W",
    )  # fmt: skip
    key = (*cable.key, "cable_product")
    facet = CableProductFacet(
        id=make_id(CableProductFacet, key),
        key=key,
        subject=cable.id,
        core_colours=(),
        gauge_mm2=Decimal("1.5"),
        shielded=False,
    )
    draft.add(facet, origin=_ORIGIN)
    return draft


def test_a_cable_with_no_core_table_raises_naming_the_fix() -> None:
    """No core table means no cores to join: the refusal is the cable's, as for `d.series`."""
    d = design(_bare_cable_library(), place="C1")
    x8, b1 = d.terminal_strip("X8", STRIP), d.device("B1", SENSOR)
    with pytest.raises(AuthorError, match=r"W3 has 0 free cores for 2 poles: use a cable"):
        d.pair(x8[1:3], d.cable("W3", "TEST-CBL-BARE"), b1.sig)
