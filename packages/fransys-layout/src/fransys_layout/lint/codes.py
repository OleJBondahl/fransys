"""Every finding code this repo emits, in one list.

Codes are stable.
"""

from fransys_layout.lint import codes_defects, codes_design

# lint/diagram.py, all ERROR
DIAGRAM_BOX_OVERLAP = "DIAGRAM_BOX_OVERLAP"
DIAGRAM_LABEL_STRUCK = "DIAGRAM_LABEL_STRUCK"
DIAGRAM_LINES_SHARE_TRACK = "DIAGRAM_LINES_SHARE_TRACK"
DIAGRAM_LINE_OFF_BOX = "DIAGRAM_LINE_OFF_BOX"
DIAGRAM_LINE_THROUGH_BOX = "DIAGRAM_LINE_THROUGH_BOX"
DIAGRAM_TEXT_OVERLAP = "DIAGRAM_TEXT_OVERLAP"

# engines/overview/engine.py, ERROR: a view the diagram placer finds no room plan for
OVERVIEW_UNPLACED = "OVERVIEW_UNPLACED"


FINDING_CODES = (
    *codes_defects.FINDING_CODES,
    *codes_design.FINDING_CODES,
)
