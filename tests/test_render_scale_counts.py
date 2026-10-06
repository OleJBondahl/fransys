"""The render count test: no render code object grows by more than 2.5x when the scale doubles.

RW3 (render-0006). `count_render` (tests/scale_counter.py, the harness the layout count test
shares) counts calls, generator resumes and loop iterations per `fransys_render` code object
in `pages(model)` on `build_scale(8)` and `build_scale(16)`; a code object whose count grows by
more than 2.5x with count(16) >= 100 is flagged. Ratios only, never exact counts; no wall time.
The `flagged` unit tests live in test_scale_call_counts.py.
"""

import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from scale_counter import BuildCounts, count_render, flagged  # noqa: E402

_METRICS = ("jumps", "calls", "resumes")


@pytest.fixture(scope="module")
def builds() -> tuple[BuildCounts, BuildCounts]:
    return count_render(8), count_render(16)


def test_no_render_code_object_grows_faster_than_2_5x_per_doubling(builds):
    # UNDO 1: tests/scale_counter.py, `_RENDER_MARK = "/fransys_render/"`
    #     -> `"/fransys_nowhere/"` (no render code is ever seen: the sanity assert fails)
    # UNDO 2: below, `"_symbols.py:symbols_group:"` -> `"_symbols.py:nowhere:"`
    #     (the sanity assert fails)
    small, big = builds
    for size, run in (("N", small), ("2N", big)):
        assert any(key.startswith("_symbols.py:symbols_group:") for key in run.calls), (
            f"no call of _symbols.py:symbols_group counted at {size}: no render code seen"
        )
    grown = [
        f"{key} {metric} {ratio:.2f}"
        for metric in _METRICS
        for key, ratio in flagged(getattr(small, metric), getattr(big, metric)).items()
    ]
    assert not grown, "grows more than 2.5x per doubling (file:qualname:line metric ratio):\n" + (
        "\n".join(sorted(grown))
    )
