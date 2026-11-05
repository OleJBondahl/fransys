"""The block-diagram spec's two worked examples through the diagram engine (BD-2 P3).

Both readings lay out with none of the four geometry findings, and write their records.
"""
# CONNECTION_NOT_DRAWN 2 per default-salt build set (MATES-DISABLED): mated, harness or board-unit input, refused for 0.22 (R1216).

import pytest
from test_block_diagram_worked_examples import _station
from test_units_worked_example import _build_cabinet_own

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_diagrams

_GEOMETRY = {
    "DIAGRAM_BOX_OVERLAP",
    "DIAGRAM_LABEL_STRUCK",
    "DIAGRAM_LINES_SHARE_TRACK",
    "DIAGRAM_LINE_OFF_BOX",
    "DIAGRAM_LINE_THROUGH_BOX",
    "DIAGRAM_TEXT_OVERLAP",
}


def _cabinet():
    return _build_cabinet_own(prefix="p", name="C1")[0].model


@pytest.mark.parametrize("build", [_station, _cabinet], ids=["station", "cabinet"])
def test_a_worked_example_lays_out_without_geometry_findings(build):
    layout, findings = lay_out_diagrams(build(), LIBRARY)
    assert not _GEOMETRY & {f.code for f in findings}
    assert layout.sheet_places()
    assert all(sheet.lines for d in layout.diagrams for sheet in d.sheets)
