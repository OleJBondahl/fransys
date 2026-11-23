"""BUNDLE (R544, R545, R550, layout-0405): the ends of one reference stand on pins of one net.

Under six id salts (the default and `uuid5(URL, "salt-" + X)` for X in a to e) the salt moves the
order of equal-rank columns, so a reference once took its two ends from two lanes of a bundle and
"""

from functools import cache
from typing import Any

import pytest
from _reference_lane_runner import _cases, run

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
def _built(salt: str, case: str) -> dict[str, Any]:
    """`case` built in this process under `salt`; `run` holds the empty context the sweep sees each build in (R1219)."""
    return run(salt, case)


def _salt_id(salt: str) -> str:
    return "default" if salt == "-" else salt


def test_every_case_the_runner_knows_is_parametrised() -> None:
    """The runner's case list is the parametrised one: a case added to one and not the other is seen, with no build."""
    assert sorted(_cases()) == sorted(_CASES)


@pytest.fixture
def built(salt: str, case: str) -> dict[str, Any]:
    """The (salt, case) build, made in setup: the 180 s cap charges the test function only (decision 0222)."""
    return _built(salt, case)


@pytest.fixture
def default(case: str) -> dict[str, Any]:
    return _built("-", case)


@pytest.mark.parametrize("case", _CASES)
@pytest.mark.parametrize("salt", SALTS, ids=_salt_id)
def test_each_salt_draws_one_net_per_reference(built: dict[str, Any]) -> None:
    """The case builds under the salt; it has markers, no split, no short, no ERROR."""
    b = built
    assert b["markers"]
    assert not b["split"]
    assert not b["pinless"]
    assert not b["shorts"]
    assert not b["errors"]


@pytest.mark.parametrize("salt", SALTS, ids=_salt_id)
def test_the_guard_sees_tag_ends(salt: str) -> None:
    """The pinless guard above sees real TAG ends: mcc plans tags under every salt."""
    assert _built(salt, "mcc")["tag_ends"] > 0


@pytest.mark.timeout(600)  # corpus builds, 71-139 s each in a quiet run, over 180 s under load (MEASURE-LANDING-1112)
@pytest.mark.parametrize("case", _CASES)
@pytest.mark.parametrize("salt", SALTS[1:])
def test_a_fan_deals_the_same_lanes_at_every_salt(built: dict[str, Any], default: dict[str, Any]) -> None:
    """NUMBER-SORT, layout-0465: a fan deals in the model's order, so the six-coil shape fills the same lanes."""
    assert built["lanes"] == default["lanes"]
