"""Layout's finding codes no consumer acts on: Fransys defects and notes (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

COULD_NOT_DRAW = "Fransys could not draw this cleanly; please report it with the smallest model"

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="DIAGRAM_BOX_OVERLAP",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause="Two boxes of a block diagram or of an overview view, or a tab and a box, overlap.",
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_LABEL_STRUCK",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause="A line of a block diagram or an overview view passes through a line label.",
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_LINE_OFF_BOX",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause=(
            "A line of a block diagram or an overview view does not end on its box's outline "
            "or tab."
        ),
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_LINE_THROUGH_BOX",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause="A line of a block diagram or an overview view crosses a box other than its own two.",
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_LINES_SHARE_TRACK",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause="Two cables of a block diagram or an overview view run along one track.",
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_TEXT_OVERLAP",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause="Two texts of a block diagram or an overview view overlap.",
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="OVERVIEW_UNPLACED",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause=(
            "The overview placer found no room plan for one view of the system overview, so "
            "the page would have no positions for it."
        ),
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="TEXT_OVERLAP",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause=(
            "Two texts on a page overlap, or a text overlaps a symbol body it does not belong to."
        ),
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
)
