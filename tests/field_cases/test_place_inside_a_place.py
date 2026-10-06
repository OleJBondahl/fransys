"""Field case: a container names a place `BATT` inside a place `HOLD`, and places a device in it.

The bug (v0.7.0): the model nests places and prints them `+HOLD+BATT`, but `d.location(tag, text)`
took no outer place, so a place nested only when a unit was placed in it. Fixing decision:
author-0020 (`d.location(..., within=)`).
"""

import fransys as fr
import pytest
from fransys_author import AuthorError


def _designation(d: fr.Design, tag: str) -> str:
    rows = fr.derive.designation_list(fr.build(d).model)
    (row,) = (r for r in rows if r.designation == f"-{tag}")
    return row.reference


def test_a_device_in_a_nested_place_prints_both_signs() -> None:
    d = fr.design("demo_parts")
    d.location("HOLD", "Hold")
    d.location("BATT", "Battery bay", within="HOLD")
    d.device("Q1", "DEMO-MCB-C6", place="BATT")
    assert _designation(d, "Q1") == "+HOLD+BATT-Q1"


def test_a_missing_outer_place_raises_and_lists_the_places() -> None:
    d = fr.design("demo_parts")
    d.location("HOLD", "Hold")
    with pytest.raises(AuthorError, match=r"no place 'DECK'.*places: HOLD"):
        d.location("BATT", "Battery bay", within="DECK")
