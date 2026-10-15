"""The model's finding codes raised by its passes and the block diagram (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

from . import codes_structure, codes_wiring

_OWN: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="DESIGNATION_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "Two items or unit instances under one parent print one designation: a tag equal "
            "to a sibling's text, or a retired or moved released one."
        ),
        fix=(
            "Give the item a distinct tag, or none. A tag a released revision reserved needs a "
            "new version."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="DIAGRAM_CABLE_FANOUT",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause=(
            "A cable reaches three or more boxes, so the block diagram draws a line from its "
            "first box to each other."
        ),
        fix="Nothing is wrong; split the cable only if a line per pair is not wanted.",
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_CABLE_ONE_BOX",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause="A cable's ends reach one box or none, so the block diagram draws no line for it.",
        fix="Usually nothing to fix: the cable runs inside one box, or an end is an unmated plug.",
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_COLUMN_TOO_TALL",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause=(
            "A block diagram gets no page because its tallest column holds more boxes than one "
            "sheet holds; the message gives the column, its boxes and how many fit."
        ),
        fix=(
            "A known limit of the system diagram: no setting changes it. "
            "`DOCUMENT_NO_DRAWINGS` is the error that stops the write."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="DIAGRAM_LOOSE_WIRE",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause="In the system reading, a wire with no cable joins two boxes and is not drawn.",
        fix=(
            "Usually nothing to fix: the unit pages show it as stubs. Put it in a cable to "
            "give it a line."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="HARNESS_END_AMBIGUOUS",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause="Two or more ends of one cable print the same text in its drawing.",
        fix="Place the colliding unit instances at distinct locations, or tag the strips apart.",
        page="findings-validators",
    ),
    CodeInfo(
        code="PART_LIBRARY_VERSION_CONFLICT",
        severities=(Severity.ERROR,),
        stage="library load",
        who="consumer",
        cause="Two `PartLibrary` records share a name but declare different versions.",
        fix="Load only one version of each named part library.",
        page="findings-validators",
    ),
    CodeInfo(
        code="PLC_CHANNEL_CONTESTED",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "Two or more PLC requests of the channel's signal are wired to the same channel. "
            "The finding names the channel's pins and every request; none of them binds, and "
            "none goes to the free queue."
        ),
        fix=(
            "One channel reads one signal: keep one request, or wire each request to its own "
            "channel."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="PLC_REQUEST_AMBIGUOUS",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "A PLC request is wired so that several free channels of its signal tie: its net "
            "reaches them all, or all by a direct conductor. It gets no binding."
        ),
        fix="Wire the request to one channel directly, or free the other channels.",
        page="findings-validators",
    ),
    CodeInfo(
        code="PLC_REQUEST_UNSERVABLE",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "No free PLC channel of the requested signal type on the request's unit chain (its "
            "unit declares none, or every one is taken)."
        ),
        fix=(
            "Add a channel of that signal type to the unit (or a parent unit), or move another "
            "request off one."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="PORT_DESIGNATION_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "Two or more ports of one item print the same designation text, so a drawing or "
            "list cannot tell them apart."
        ),
        fix="Give the part's pin markings distinct names so each port prints a unique text.",
        page="findings-validators",
    ),
    CodeInfo(
        code="PRODUCT_DESIGNATION_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "Two items print the same product designation (location plus own label): both at "
            "one location or, unplaced, both unnumbered alike in one unit instance."
        ),
        fix="Place one item at a distinct location, or tag it.",
        page="findings-validators",
    ),
    CodeInfo(
        code="REFERENCE_DESIGNATION_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="build",
        who="consumer",
        cause=(
            "Two items in the function or location aspect print the same full reference "
            "designation (e.g. two unit instances at one location)."
        ),
        fix="Place one of them at a distinct location so the designations differ.",
        page="findings-validators",
    ),
    CodeInfo(
        code="SIDE_HINT_NO_HARNESS_LINE",
        severities=(Severity.WARNING,),
        stage="build",
        who="consumer",
        cause=(
            "A `d.layout.side` hint names an interface that has no harness line, so the hint "
            "does nothing."
        ),
        fix="Remove the hint, or connect the interface through a harness line.",
        page="findings-validators",
    ),
)

FINDING_CODES: tuple[CodeInfo, ...] = (
    *_OWN,
    *codes_structure.FINDING_CODES,
    *codes_wiring.FINDING_CODES,
)
