"""The block-diagram spec's two worked examples through the diagram engine (BD-2 P3).

Both readings lay out with none of the four BD8 geometry findings, and write their records.
"""

import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from test_block_diagram_worked_examples import _station  # noqa: E402 -- after the sys.path insert
from test_units_worked_example import _build_cabinet_own  # noqa: E402 -- after the sys.path insert

from fransys_layout import lay_out_diagrams  # noqa: E402 -- after the sys.path insert
from fransys_model.layout import DiagramLine, DiagramSheet, layout_of  # noqa: E402 -- ditto

_GEOMETRY = {
    "DIAGRAM_BOX_OVERLAP",
    "DIAGRAM_LINE_OFF_BOX",
    "DIAGRAM_LINE_THROUGH_BOX",
    "DIAGRAM_TEXT_OVERLAP",
}


def _cabinet():
    return _build_cabinet_own(prefix="p", name="C1")[0].model


@pytest.mark.parametrize("build", [_station, _cabinet], ids=["station", "cabinet"])
def test_a_worked_example_lays_out_without_geometry_findings(build):
    model, findings = lay_out_diagrams(build())
    assert not _GEOMETRY & {f.code for f in findings}
    assert layout_of(model, DiagramSheet)
    assert layout_of(model, DiagramLine)
