"""Field case: two instances of one board are tagged alike in two function blocks of one design.
The bug (v0.8.0): the instance check compared each item's unit, which differs per instance, so a duplicate tag passed.
Fixed by model-0145, a duplicate tag is checked under one parent, as it is for two items."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _expected_codes import expect_codes


class _Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(d: fr.Design) -> _Io:
    return _Io(d.device("X1", "DEMO-CONN-2P", interface=True, unused=True))


class _Open(NamedTuple):
    """A cabinet unit with nothing to hand back."""


@fr.unit("demo-cabinet", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cabinet(d: fr.Design) -> _Open:
    """A cabinet unit that places the board twice, in two function blocks, both as `U1`."""
    for block in ("RUN", "LAMPS"):
        with d.function(block, block):
            d.add(_board, "U1")
    return _Open()


@pytest.fixture(scope="module")
def built() -> dict[tuple[str, str], fr.BuildResult]:
    out = {}
    for pair in (("U1", "U1"), ("U1", "U2")):
        d = fr.design("demo_parts", place="C1")
        for block, tag in zip(("RUN", "LAMPS"), pair, strict=True):
            with d.function(block, block):
                d.add(_board, tag)
        out[pair] = fr.build(d)
    return out


def test_one_tag_in_two_function_blocks_is_a_duplicate(built: dict[Any, Any]) -> None:
    expect_codes(built[("U1", "U1")], "DESIGNATION_DUPLICATE", "PRODUCT_DESIGNATION_DUPLICATE")


def test_distinct_tags_are_no_duplicate(built: dict[Any, Any]) -> None:
    assert "DESIGNATION_DUPLICATE" not in [f.code for f in built[("U1", "U2")].findings]


def test_one_tag_in_two_function_blocks_inside_a_cabinet_unit_is_a_duplicate() -> None:
    d = fr.design("demo_parts", place="C1")
    d.add(_cabinet, "CAB")
    expect_codes(fr.build(d), "DESIGNATION_DUPLICATE", "PRODUCT_DESIGNATION_DUPLICATE")


def test_the_duplicate_message_prints_the_item_not_its_key() -> None:
    d = fr.design("demo_parts", place="C1")
    d.add(_cabinet, "CAB")
    result = fr.build(d)
    expect_codes(result, "DESIGNATION_DUPLICATE", "PRODUCT_DESIGNATION_DUPLICATE")
    (finding, *_) = [f for f in result.findings if f.code == "DESIGNATION_DUPLICATE"]
    assert "-" in finding.message
    assert "⟨" not in finding.message
    assert "/" not in finding.message.split("designation")[0]
