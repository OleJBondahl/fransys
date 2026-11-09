"""BUNDLE (R544, R545, R550, layout-0405): the ends of one reference stand on pins of one net.

Under six id salts (the default and `uuid5(URL, "salt-" + X)` for X in a to e) the salt moves the
order of equal-rank columns, so a reference once took its two ends from two lanes of a bundle and
"""

from functools import cache
from typing import Any

import pytest
from _reference_lane_runner import run

SALTS = ("-", "a", "b", "c", "d", "e")
pytestmark = [pytest.mark.rule("BUNDLE"), pytest.mark.private_input]  # internal/ (R462)
_CASES = (
    "machine_panel",
    "panel_di16p",
    "remote_io",
    "distribution_board",
    "mcc",
    "demo-skid",
)


@cache
def _built(salt: str) -> dict[str, Any]:
    """Every case built in this process under `salt`; `run` holds the empty context the sweep sees each build in (R1219)."""
    return run(salt)


@pytest.mark.parametrize("salt", SALTS, ids=lambda s: "default" if s == "-" else s)
def test_each_salt_draws_one_net_per_reference(salt: str) -> None:
    """Every case builds under the salt; each has markers, no split, no short, no ERROR."""
    built = _built(salt)
    assert sorted(built) == sorted(_CASES)
    assert [n for n, b in built.items() if not b["markers"]] == []
    assert {n: b["split"] for n, b in built.items() if b["split"]} == {}
    assert sum(b["tag_ends"] for b in built.values()) > 0  # the guard below sees real TAG ends (mcc plans tags)
    assert {n: b["pinless"] for n, b in built.items() if b["pinless"]} == {}
    assert {n: b["shorts"] for n, b in built.items() if b["shorts"]} == {}
    assert {n: b["errors"] for n, b in built.items() if b["errors"]} == {}


@pytest.mark.parametrize("salt", SALTS[1:])
def test_a_fan_deals_the_same_lanes_at_every_salt(salt: str) -> None:
    """NUMBER-SORT, layout-0465: a fan deals in the model's order, so the six-coil shape fills the same lanes."""
    assert {n: b["lanes"] for n, b in _built(salt).items()} == {n: b["lanes"] for n, b in _built("-").items()}
