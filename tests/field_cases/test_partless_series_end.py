"""Field case: a three-phase series ends on external equipment that has no part.

A feeder runs from a terminal strip through a three-pole breaker to a drive supplied by others.
The drive has no part, only the pins U, V and W its box draws.

The bug (0.19.6): `d.series(supply, breaker, drive)` raised `KeyError: None` from the pairing
code, because the part-less drive has no function template to count poles from.

Fixing decision: author-0054. A part-less device is accepted only as the last element of a
series, one pole per non-earth pin in declared order; anywhere else, or with another pin count,
it raises `AuthorError` naming the fix.
"""

from typing import Any

import fransys as fr
import pytest


def _design() -> tuple[fr.Design, Any, Any]:
    d = fr.design("demo_parts")
    xa = d.terminal_strip("XA", "DEMO-TB-2.5")
    supply = d.ac_supply("A", "230", xa[1], xa[2], xa[3], names=("A_L1", "A_L2", "A_L3"))
    return d, supply, d.device("QA", "DEMO-MCB-3P")


def _ends(d) -> set[frozenset]:
    return {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(fr.build(d).model)}


def test_a_part_less_last_element_meets_the_load_poles_in_declared_order() -> None:
    d, supply, qa = _design()
    ext = d.device("E1", None, external=True, pins=("U", "V", "W"))
    d.series(supply, qa.element, ext, wire=2.5)
    ends = _ends(d)
    for pin, load in (("U", "2"), ("V", "4"), ("W", "6")):
        assert frozenset((f"-E1:{pin}", f"-QA:{load}")) in ends, pin


def test_a_part_less_device_in_the_middle_is_refused_with_its_position_and_the_fix() -> None:
    d, supply, qa = _design()
    ext = d.device("E1", None, external=True, pins=("U", "V", "W"))
    with pytest.raises(fr.AuthorError, match=r"E1.*position 2 of 3.*make it the last element"):
        d.series(supply, ext, qa.element, wire=2.5)


def test_a_pin_count_that_differs_from_the_path_names_both_counts() -> None:
    d, supply, qa = _design()
    ext = d.device("E1", None, external=True, pins=("U", "V"))
    with pytest.raises(fr.AuthorError, match=r"2 non-earth pins.*3 poles.*d\.earth"):
        d.series(supply, qa.element, ext, wire=2.5)
