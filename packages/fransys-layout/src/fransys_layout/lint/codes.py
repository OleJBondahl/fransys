"""Every finding code this repo emits, in one list.

Codes are stable.
"""

from fransys_layout.lint import codes_defects, codes_design, codes_design_more

# Emitted by the drawing engine (fransys_el and the layout core), all WARNING
KEEP_TOGETHER_UNMET = "KEEP_TOGETHER_UNMET"
ORDER_HINT_UNMET = "ORDER_HINT_UNMET"
ROUTE_FAILED = "ROUTE_FAILED"
TEXT_OVERLAP = "TEXT_OVERLAP"

# lint/diagram.py, all ERROR
DIAGRAM_BOX_OVERLAP = "DIAGRAM_BOX_OVERLAP"
DIAGRAM_LABEL_STRUCK = "DIAGRAM_LABEL_STRUCK"
DIAGRAM_LINES_SHARE_TRACK = "DIAGRAM_LINES_SHARE_TRACK"
DIAGRAM_LINE_OFF_BOX = "DIAGRAM_LINE_OFF_BOX"
DIAGRAM_LINE_THROUGH_BOX = "DIAGRAM_LINE_THROUGH_BOX"
DIAGRAM_TEXT_OVERLAP = "DIAGRAM_TEXT_OVERLAP"

# engines/overview/engine.py, ERROR: a view the diagram placer finds no room plan for
OVERVIEW_UNPLACED = "OVERVIEW_UNPLACED"

# fransys_el.read_findings (R258): SHEET_FORMAT_UNUSED and TEXT_TOO_SMALL, both
# WARNING. The code rows stay here, the source of FINDING_CODES (R219).
SHEET_FORMAT_UNUSED = "SHEET_FORMAT_UNUSED"
TEXT_TOO_SMALL = "TEXT_TOO_SMALL"
CONNECTION_TO_UNDRAWN = "CONNECTION_TO_UNDRAWN"  # fransys_el.read_findings (R267)
# fransys_el, WARNING (layout-0322)
BOARD_NETS_NOT_DRAWN = "BOARD_NETS_NOT_DRAWN"

ALL_CODES: tuple[str, ...] = (
    BOARD_NETS_NOT_DRAWN,
    CONNECTION_TO_UNDRAWN,
    DIAGRAM_BOX_OVERLAP,
    DIAGRAM_LABEL_STRUCK,
    DIAGRAM_LINE_OFF_BOX,
    DIAGRAM_LINE_THROUGH_BOX,
    DIAGRAM_LINES_SHARE_TRACK,
    DIAGRAM_TEXT_OVERLAP,
    KEEP_TOGETHER_UNMET,
    ORDER_HINT_UNMET,
    ROUTE_FAILED,
    SHEET_FORMAT_UNUSED,
    TEXT_OVERLAP,
    TEXT_TOO_SMALL,
)

# Drawing defects no consumer action clears: INFO with `codes_defects.COULD_NOT_DRAW` (layout-0252)
UNCLEARABLE: frozenset[str] = frozenset(
    {
        DIAGRAM_LABEL_STRUCK,
        DIAGRAM_LINES_SHARE_TRACK,
        TEXT_OVERLAP,
    }
)


FINDING_CODES = (
    *codes_defects.FINDING_CODES,
    *codes_design.FINDING_CODES,
    *codes_design_more.FINDING_CODES,
)
