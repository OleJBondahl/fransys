"""Field case: a part-less harness holding one cable lists one row, the cable's, under its tag.

The engineering shape: a unit holds a lamp and a loom, a harness `W3` with two plugs and one
cable. The loom's cable prints as the harness, `-W3` (model-0148).

The bug: the unit's baseline listing wrote two rows under `-W3`: the harness item with an empty
part number and the cable. Plugs (`-W3-J1`, `-W3-J2`) are unaffected.

Fixed by decision model-0150, which amends model-0148.
"""

from typing import Any, NamedTuple, TypedDict

import fransys as fr
import pytest

from fransys_model.derive import baseline
from fransys_model.vocab.tables import units

_CABLE = "DEMO-CBL-4G1.5"
_PLUG = "DEMO-CONN-2P"


class _Release(TypedDict):
    revision: int
    interface_version: int
    date: str
    text: str
    by: str


_REL: _Release = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-10-06",
    "text": "First release",
    "by": "XX",
}


class _Unit(NamedTuple):
    """The unit hands back nothing."""


@fr.unit("demo-loom-unit", **_REL)
def _loom_unit(d: fr.Design) -> _Unit:
    """A lamp beside a part-less harness `W3` with two plugs and one cable."""
    loom = d.harness("W3")
    near = d.device("J1", _PLUG, parent=loom)
    far = d.device("J2", _PLUG, parent=loom)
    d.cable("W1", _CABLE, parent=loom, name="cable").core(1, near[1], far[1])
    d.device("H1", "DEMO-LAMP-24")
    return _Unit()


@pytest.fixture(scope="module")
def rows() -> tuple[Any, ...]:
    """The item rows of the one unit's baseline listing."""
    d = fr.design("demo_parts")
    d.add(_loom_unit, "U1")
    model = fr.build(d).model
    (unit,) = units(model)
    return baseline.listing(model, unit).items


def test_one_row_under_the_harness_tag(rows: tuple[Any, ...]) -> None:
    """Exactly one `-W3` row, and it carries the cable's part number."""
    under = [row for row in rows if row.designation == "-W3"]
    assert [row.mpn for row in under] == [_CABLE]


def test_no_row_has_an_empty_part_number(rows: tuple[Any, ...]) -> None:
    """The harness item writes no part-less row."""
    assert [row.designation for row in rows if not row.mpn] == []


def test_the_plugs_keep_their_rows(rows: tuple[Any, ...]) -> None:
    """`-W3-J1` and `-W3-J2` are listed."""
    assert {row.designation for row in rows} >= {"-W3-J1", "-W3-J2"}
