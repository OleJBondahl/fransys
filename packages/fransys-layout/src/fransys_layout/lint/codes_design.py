"""Layout's finding codes a consumer acts on (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="CHAIN_BROKEN",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            'A connection between two "pole" cells was severed into a marker pair though its '
            "net has only those ports."
        ),
        fix=(
            "Keep the whole circuit in one function block, so no page break falls inside it "
            "([Drawing well](drawing.md))."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="CONNECTION_DRAWN_TWICE",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause=(
            "A connection (or net-group edge) is drawn by more than one route, or also "
            "contradicted by a cut decision."
        ),
        fix="Remove the duplicate so the connection is drawn or cut once.",
        page="findings-render",
    ),
    CodeInfo(
        code="CONNECTION_NOT_DRAWN",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause=(
            "A conductor or net-group edge is neither routed on a shared page nor cut with a "
            "marker."
        ),
        fix=(
            "Give both ends a location so layout can route or cut them; check `layout.route`, "
            "`layout.symbol_placement` and `layout.page`."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="CONNECTION_TO_UNDRAWN",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A connection, net group or rail has an end whose function layout never draws.",
        fix="Put the missing end's item in a drawn unit or location, or remove the connection.",
        page="findings-render",
    ),
    CodeInfo(
        code="FUNCTION_UNPLACED_IN_COLUMN",
        severities=(Severity.INFO,),
        stage="render",
        who="consumer",
        cause=(
            "A function is on no current path, authored or found from the wiring, so layout "
            "placed it alone in its own column."
        ),
        fix=(
            "Wire the function into a current path (`d.series`, or `d.wire` with two poles per "
            "net), or name the path with `d.layout.chain`; see drawing.md."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="GROUP_SPLIT",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A group of columns is wider than one page, so layout split it between columns.",
        fix=(
            "Split the block into function blocks that each fit one page ([Drawing "
            "well](drawing.md))."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="KEEP_TOGETHER_UNMET",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "An authored `keep_together` set could not be kept on one page (it does not fit, "
            "its groups sit on different drawing sets, or `break_before` is invalid)."
        ),
        fix="Shrink the set, move its groups onto one drawing set, or drop the hint.",
        page="findings-render",
    ),
    CodeInfo(
        code="LABEL_UNPLACED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A tag, marking or cross-reference found no free spot and sits at its default.",
        fix=(
            "Use the house `text_height_mm` 1.8; give the design structure ([Drawing "
            "well](drawing.md)). If it still fires, a Fransys defect: send the smallest model "
            "that shows it."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="LINK_FANOUT",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="More than one severed link crosses between the same two pages on one net.",
        fix=(
            "Join the net once with a terminal instead of severing it repeatedly between the "
            "same two pages."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="LINK_PARTNER_UNLOCATED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A signal crosses into a drawing set with no authored location, so its marker has "
            "no located prefix."
        ),
        fix="Name the drawing set's unit or location.",
        page="findings-render",
    ),
    CodeInfo(
        code="LONE_CELL",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A symbol has nothing connected, so it is drawn on no page; the message names the "
            "pins to wire and no page. Or a symbol stands alone on a page though its column has "
            "cells elsewhere."
        ),
        fix=(
            "Wire the named pins, or remove the device if it is not used; or move the column's "
            "cells onto one page. A unit's own open boundary functions and the item box "
            "standing under them, spare contacts and spare terminals never give it (decisions "
            "layout-0077, layout-0202 and layout-0218)."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="ORDER_HINT_UNDONE",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "An authored `keep_together` set pulled a group across an authored `order` hint, so "
            "the page order is not the one the `order` hint asked for."
        ),
        fix=(
            "Drop the `keep_together` hint or the `order` hint, or order both hints to agree; "
            "`keep_together` wins when you keep both."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="ORDER_HINT_UNMET",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "An authored order hint names two groups that are not on the same drawing set, so "
            "no page order can honour it."
        ),
        fix="Move both groups onto one drawing set, or drop the hint.",
        page="findings-render",
    ),
    CodeInfo(
        code="OUT_OF_CONTENT_BOX",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A symbol's keep-out box, label, marker box or route vertex sits outside the "
            'page\'s content box; the message ends " at p<page>:<cell>", with the drawing set '
            "before the page (`p<set>.<page>`) only when the layout has more than one."
        ),
        fix=(
            "Declare the supplies, wire each circuit as a current path, or split it into "
            "function blocks ([Drawing well](drawing.md)). If it still fires, a Fransys "
            "defect: send the smallest model that shows it."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="PAGE_OVERFULL",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause="A page's rows are taller than the content box; nothing is scaled.",
        fix=(
            "Declare the supply, or split the circuit into function blocks ([Drawing "
            "well](drawing.md)). If it still fires, a Fransys defect: send the smallest model "
            "that shows it."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="PIN_MAP_INCOMPLETE",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause="A symbol node has no model port bound to any of its symbol ports at all.",
        fix="Add the missing model port or a `port_map`/symbol choice.",
        page="findings-render",
    ),
    CodeInfo(
        code="REFERENCE_BOX_EXCEEDS_ROOM",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A drawing set has 100 or more cross-reference numbers (#n) or pages; a reference "
            "box then exceeds layout's room."
        ),
        fix=(
            "Keep each drawing set under 100 pages and 100 `#n` numbers: split the design into "
            "units."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="ROUTE_FAILED",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause=(
            "No orthogonal path on the wiring grid could be found between the two ports of a "
            "connection."
        ),
        fix=(
            "Usual causes: a redundant conductor between two points already on one net (rewire "
            "to a point already routed), or crowded geometry around the ports."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="SHEET_FORMAT_UNUSED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "An authored sheet format is named by no layout profile, so pages use the house "
            "sheet (or the profile's format)."
        ),
        fix="Name it in the layout profile, or remove it.",
        page="findings-render",
    ),
    CodeInfo(
        code="TEXT_TOO_SMALL",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A layout profile's `text_height_mm` is under its `min_text_height_mm`. Once per "
            "profile; nothing is shrunk or grown."
        ),
        fix=(
            "Raise `text_height_mm`, or lower `min_text_height_mm` if the small text is "
            "intended ([Drawing well](drawing.md))."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="UNIT_GROUP_SPLIT",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A unit group is wider than one page, so layout split it; each page keeps an "
            "outline for its own interfaces."
        ),
        fix=(
            "Even the edges with side hints (`d.layout.side`), or give the unit fewer harness "
            "interfaces."
        ),
        page="findings-render",
    ),
)
