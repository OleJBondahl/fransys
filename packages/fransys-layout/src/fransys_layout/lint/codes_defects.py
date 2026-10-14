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
        fix="A Fransys defect: send the smallest model that shows it.",
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
        fix="A Fransys defect: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_LINE_THROUGH_BOX",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause="A line of a block diagram or an overview view crosses a box other than its own two.",
        fix="A Fransys defect: send the smallest model that shows it.",
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
        fix="A Fransys defect: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="JOIN_UNALIGNED",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause=(
            "Same-net, same-facing ports at one end of neighbouring columns could not be "
            "aligned onto one row, so layout drew references."
        ),
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="LINE_ON_OUTLINE",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause="A harness line runs along a unit outline's edge, so the two read as one stroke.",
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="MARKER_UNPAIRED",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause=(
            "A severed connection's owner or user marker is missing, or a page marker matches "
            "no severed decision."
        ),
        fix=(
            "A Fransys defect: send the smallest model that shows it. Check first that the cut "
            "decision and its markers agree."
        ),
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
        fix="A Fransys defect: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="PAGE_UNDERFILLED",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause=(
            "A schematic page whose drawn content covers under half of the content box; its "
            "message gives the share and the page reference (`+C<set>p<page>` or "
            "`(p<set>.<page>)`, from the naming pass). Nothing is moved or scaled."
        ),
        fix=(
            "No action is needed. The page is mostly empty; a larger `module_mm` spreads the "
            "content ([Drawing well](drawing.md))."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="POWER_SYMBOL_UNPLACED",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause=(
            "No lead of up to 12 grids kept a power symbol clear of its neighbours, so it "
            "keeps one grid and may touch."
        ),
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="REDUNDANT_JOG",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause=(
            "A drawn route leaves a straight line and returns to it where a straight run was free."
        ),
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="ROUTE_SHORTS_NETS",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause=(
            "A drawn route touches a port of another physical net, or two routes of different "
            "physical nets touch on the page."
        ),
        fix=(
            "A Fransys defect: send the smallest model that shows it. Check first that no "
            "authored hint crowds the nets."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="ROUTE_WRONG_PORT",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause="A route does not run between the two ports it claims to join.",
        fix="A Fransys defect: send the smallest model that shows it.",
        page="findings-render",
    ),
    CodeInfo(
        code="STUBS_NOT_STACKED",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause=(
            "Leaving-line stubs of one page whose texts meet found no free staircase "
            "(layout-0256): the room, a shape or another line was in the way. They stay as drawn "
            "and their texts overlap. The message names the page."
        ),
        fix="Move a unit or cable so the lines leave apart, or send the smallest model showing it.",
        page="findings-render",
    ),
    CodeInfo(
        code="SYMBOL_DEFAULTED",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause=(
            "A function matched no symbol rule or choice, so it was drawn as a plain labelled box."
        ),
        fix=(
            "Add a symbol rule or choice for the function's kind or category if a real symbol "
            "is wanted."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="SYMBOL_OVERLAP",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause="The keep-out boxes of two symbols on one page overlap.",
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="TEXT_CROSSED_BY_ROUTE",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause="A link marker's stub runs through a text box (a label or another marker's box).",
        fix=COULD_NOT_DRAW,
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
    CodeInfo(
        code="WIRE_NOT_ORTHOGONAL",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause="A drawn route has a non-orthogonal segment (not purely horizontal or vertical).",
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="WIRE_OVER_LABEL",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause="A drawn route runs through a label's (or link marker's) box.",
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
    CodeInfo(
        code="WIRE_THROUGH_SYMBOL",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause="A drawn route runs through the keep-out box of a symbol it does not end at.",
        fix=COULD_NOT_DRAW,
        page="findings-render",
    ),
)
