"""The codes of the finished-drawing sweep over the drawn netlist (DRAWN-NETLIST, el-0052).

Each starts as a WARNING with a falling stock per example (`tests/ratchets.toml`) and becomes an
ERROR in the commit that brings its stock to 0: DRAWING_SHORTS_NETS and ROUTE_WRONG_PORT are 0 on
all seven builds.
"""

from fransys_model.kernel import CodeInfo, Severity

_REPORT = "No call clears this: send the smallest model that shows it. The message names the page."

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="CONNECTION_NOT_DRAWN",
        severity=Severity.ERROR,
        stage="render",
        who="consumer",
        cause=(
            "The drawn ports of one physical net do not lie in one drawn piece: a port no wire, "
            "dot, link or reference reaches, or two pieces with no reference pair between them. "
            "A group the model joins with a port off the document needs each drawn piece to end in a stub "
            "that names a port of the group outside it."
        ),
        fix=(
            "Give both ends a location so layout can route or cut them; check `layout.route`, "
            "`layout.symbol_placement` and `layout.page`. Wire the open end's function into a function block, "
            "or move its device into a unit. Write: d.series(a, b, ...) to draw it in its block."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="DRAWING_SHORTS_NETS",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause=(
            "The wires, junction dots and references of the drawings join ports of two physical "
            "nets, or a wire ends on another net's wire with no junction dot."
        ),
        fix=_REPORT,
        page="findings-render",
    ),
    CodeInfo(
        code="ROUTE_WRONG_PORT",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause="A wire of one lane ends on a port of one net and on a port of another net.",
        fix=_REPORT,
        page="findings-render",
    ),
    CodeInfo(
        code="DANGLING_WIRE_END",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause=(
            "A Fransys drawing defect: a drawn wire ends where no symbol port, junction dot, "
            "reference marker, other wire or joined bundle lane end stands."
        ),
        fix=_REPORT,
        page="findings-render",
    ),
    CodeInfo(
        code="MARKER_UNPAIRED",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause="A reference marker is drawn and the marker it refers to is drawn on no page.",
        fix=_REPORT,
        page="findings-render",
    ),
    CodeInfo(
        code="CONNECTION_DRAWN_TWICE",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause="Two routes on one page join the same ports: the wires of a page close a loop.",
        fix=_REPORT,
        page="findings-render",
    ),
    CodeInfo(
        code="WIRE_NOT_ORTHOGONAL",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause="A drawn wire has a segment that is neither horizontal nor vertical.",
        fix=_REPORT,
        page="findings-render",
    ),
    CodeInfo(
        code="MISSING_JUNCTION_DOT",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause=("A wire ends on the middle of another wire of the same net with no junction dot, so the page does not show them joined."),
        fix=_REPORT,
        page="findings-render",
    ),
)
