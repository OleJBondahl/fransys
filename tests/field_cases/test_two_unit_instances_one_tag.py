"""Field case: two instances of one board are tagged alike in two function blocks of one design.

The engineering shape: a cabinet design places the same I/O board twice, once in each of two
function blocks (circuits), both as `U1`. A circuit is a function block, never a place, so
both instances sit under one parent and the tag must be unique there, as it is for two items.

The bug (v0.8.0): the instance check compared items' `unit`, and each instance's items carry a
different `unit`, so the duplicate tag passed with no finding.

The decision that fixes it: model-0145.
"""

from typing import NamedTuple

import fransys as fr
import pytest


class _Io(NamedTuple):
    X1: fr.Device


@fr.unit("demo-io-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _board(d: fr.Design) -> _Io:
    return _Io(d.device("X1", "DEMO-CONN-2P", interface=True))


class _Open(NamedTuple):
    """A cabinet unit with nothing to hand back."""


@fr.unit("demo-cabinet", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cabinet(d: fr.Design) -> _Open:
    """A cabinet unit that places the board twice, in two function blocks, both as `U1`."""
    for block in ("RUN", "LAMPS"):
        with d.function(block, block):
            d.add(_board, "U1", unused=("X1",))
    return _Open()


@pytest.fixture(scope="module")
def codes() -> dict[tuple[str, str], list[str]]:
    out = {}
    for pair in (("U1", "U1"), ("U1", "U2")):
        d = fr.design("demo_parts", place="C1")
        for block, tag in zip(("RUN", "LAMPS"), pair, strict=True):
            with d.function(block, block):
                d.add(_board, tag, unused=("X1",))
        out[pair] = [f.code for f in fr.build(d).findings]
    return out


def test_one_tag_in_two_function_blocks_is_a_duplicate(codes: dict) -> None:
    assert "DESIGNATION_DUPLICATE" in codes[("U1", "U1")]


def test_distinct_tags_are_no_duplicate(codes: dict) -> None:
    assert "DESIGNATION_DUPLICATE" not in codes[("U1", "U2")]


def test_one_tag_in_two_function_blocks_inside_a_cabinet_unit_is_a_duplicate() -> None:
    d = fr.design("demo_parts", place="C1")
    d.add(_cabinet, "CAB")
    assert "DESIGNATION_DUPLICATE" in [f.code for f in fr.build(d).findings]
