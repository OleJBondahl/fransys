"""D4b: a harnessed cabinet writes with no ERROR, and its harness lines are drawn in the SVG.

The study board of `ha_study_board` (one unit with five interfaces on harnesses, beside PLC
devices and a terminal strip), built and written once through `fr` from `demo_parts` (module
fixture).
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple

import fransys as fr
import pytest

from fransys_model import derive
from fransys_model.layout import HarnessLine, layout_of

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from ha_study_board import build  # noqa: E402 -- needs the tests folder on sys.path first

_HARNESSES = {"-W11", "-W12", "-W13", "-W15", "-W17"}


class _Written(NamedTuple):
    result: fr.BuildResult
    exports: tuple[Path, ...]
    svg: str


@pytest.fixture(scope="module")
def written(tmp_path_factory: pytest.TempPathFactory) -> _Written:
    root = tmp_path_factory.mktemp("d4b")
    result = build()
    exports = fr.write(result, root / "out", intermediates=root / "inter")
    svg = "".join(p.read_text(encoding="utf-8") for p in sorted((root / "inter").rglob("*.svg")))
    return _Written(result, exports, svg)


def test_the_write_runs_with_no_error_finding(written: _Written) -> None:
    assert [f for f in written.result.findings if f.severity.name == "ERROR"] == []
    assert written.exports


def test_every_harness_line_is_drawn_as_a_polyline_with_its_label(written: _Written) -> None:
    model = written.result.model
    lines = list(layout_of(model, HarnessLine).values())
    assert lines
    polylines = re.findall(r'<polyline class="harness-line" points="[^"]+"/>', written.svg)
    assert len(polylines) == len(lines)
    labels = {derive.line_designation(model, line.harness, line.branch) for line in lines}
    assert {label.split(".")[0] for label in labels} == _HARNESSES  # branches read -W12.1
    for label in labels:
        assert f">{label}</text>" in written.svg
