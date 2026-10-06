"""The count test: no layout code object grows by more than 2.5x when the scale doubles.

D10's Check (docs/specs/2026-09-25-layout-redesign.md; decision layout-0086). No code object is
exempt by name. `count_build` (tests/scale_counter.py) counts calls, generator resumes and loop
iterations per code object on `build_scale(8)` and `build_scale(16)`; a code object whose count
grows by more than 2.5x with count(16) >= 100 is flagged. Ratios only, never exact counts; no wall
time.
"""

import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_counter import BuildCounts, check_passes, count_build, flagged  # noqa: E402

_METRICS = ("jumps", "calls", "resumes")


def test_linear_growth_is_not_flagged():
    assert flagged({"a": 100}, {"a": 200}) == {}


def test_quadratic_growth_is_flagged():
    assert flagged({"a": 100}, {"a": 400}) == {"a": 4.0}


def test_exactly_the_threshold_is_not_flagged():
    assert flagged({"a": 100}, {"a": 250}) == {}


def test_growth_below_the_floor_is_not_flagged():
    assert flagged({"a": 24}, {"a": 96}) == {}


def test_zero_at_n_and_over_the_floor_at_2n_is_flagged():
    assert flagged({}, {"a": 100}) == {"a": float("inf")}
    assert flagged({"a": 0}, {"a": 100}) == {"a": float("inf")}


def test_a_key_only_in_the_small_run_is_ignored():
    assert flagged({"a": 500}, {}) == {}


def test_unequal_pass_counts_fail():
    with pytest.raises(AssertionError, match="2 times at N but 3 times at 2N"):
        check_passes(BuildCounts(2, {}, {}, {}), BuildCounts(3, {}, {}, {}))


@pytest.fixture(scope="module")
def builds() -> tuple[BuildCounts, BuildCounts]:
    return count_build(8), count_build(16)


def test_no_layout_code_object_grows_faster_than_2_5x_per_doubling(builds):
    # UNDO 1: tests/scale_counter.py, `_PASS_CODE = pagerun._place_each.__code__`
    #     -> `_PASS_CODE = (lambda: 0).__code__` (no pass is ever seen: the passes assert fails)
    # UNDO 2: below, `"stages/place.py:place:"` -> `"stages/place.py:nowhere:"`
    #     (the layout assert fails)
    small, big = builds
    check_passes(small, big)
    assert small.passes > 0, "_place_each never ran, the counter saw nothing"
    for size, run in (("N", small), ("2N", big)):
        assert any(key.startswith("stages/place.py:place:") for key in run.calls), (
            f"no call of stages/place.py:place counted at {size}: the counter saw no layout code"
        )
    grown = [
        f"{key} {metric} {ratio:.2f}"
        for metric in _METRICS
        for key, ratio in flagged(getattr(small, metric), getattr(big, metric)).items()
    ]
    assert not grown, "grows more than 2.5x per doubling (file:qualname:line metric ratio):\n" + (
        "\n".join(sorted(grown))
    )
