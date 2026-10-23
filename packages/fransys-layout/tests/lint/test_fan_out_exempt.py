"""HA-D2 probe 6: a harness fan-out leg is exempt from the geometric lint by kind.

The lint reads `Layout.routes` only. A `HarnessFanOut` is a model record, not a `Route`.
"""

from pathlib import Path


def test_lint_code_does_not_read_fan_outs() -> None:
    """No lint module names `HarnessFanOut`, `FanLeg` or `harness_fan_out`."""
    lint_dir = Path(__file__).parents[2] / "src" / "fransys_layout" / "lint"
    text = "".join(path.read_text() for path in lint_dir.glob("*.py"))
    assert not any(name in text for name in ("HarnessFanOut", "FanLeg", "harness_fan_out"))
