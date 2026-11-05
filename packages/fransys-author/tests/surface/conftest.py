"""The supply tests' module fixture: the series library plus PSU variants."""

import pytest
from author_catalogue import _ORIGIN, _function, _library, _part
from ratings_fixtures import rng
from series_parts import MINUS, PLUS, _pin, series_library

from fransys_model.elecdef import Unit
from fransys_model.kernel import Draft, make_id
from fransys_model.vocab import ConductorMark, FunctionKind, Operating, OperatingFacet, PartCategory


def _psu(draft: Draft, mpn: str, marks: dict[str, ConductorMark | None], volts: str | None) -> None:
    """A PSU `out` function with one pin per `marks` item and `volts` as its nominal voltage."""
    lib = _library(draft, f"lib-{mpn}")
    part = _part(draft, lib, manufacturer="TestCo", mpn=mpn, category=PartCategory.GENERIC, letter="G")
    out = _function(draft, part, "out", FunctionKind.SUPPLY)
    for name, mark in marks.items():
        _pin(draft, out, name, None, mark)
    if volts is not None:
        key = (*out.key, "operating")
        facet = OperatingFacet(
            id=make_id(OperatingFacet, key),
            key=key,
            subject=out.id,
            operating=Operating(voltage=(rng(Unit.V, nom=volts),)),
        )
        draft.add(facet, origin=_ORIGIN)


@pytest.fixture(scope="module")
def lib() -> Draft:
    """The series library plus PSU variants: a mid pin, no voltage, no marks, a '24.0' voltage."""
    draft = series_library()
    _psu(draft, "PSU-MID", {"B": ConductorMark.M, "A": MINUS, "C": PLUS}, "12")
    _psu(draft, "PSU-NOV", {"+": PLUS, "-": MINUS}, None)
    _psu(draft, "PSU-NOMARK", {"+": None, "-": None}, "24")
    _psu(draft, "PSU-NOMINUS", {"+": PLUS, "-": None}, "24")
    _psu(draft, "PSU-TWO-OUT", {"+": PLUS, "-": MINUS}, "24.0")
    return draft
