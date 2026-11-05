"""The model validators' finding codes about structure, units and revisions (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="ASPECT_CROSS_PARENT",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause=("An aspect node's parent belongs to a different aspect (function, location or product)."),
        fix=('Give each location a parent of its own aspect, a location. Write: d.location("BATT", "Battery bay", within="HOLD")'),
        page="findings-validators",
    ),
    CodeInfo(
        code="ASPECT_CYCLE",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="An aspect node's parent chain loops back on itself.",
        fix=('Make the parents of locations form a tree, never a loop. Write: d.location("BATT", "Battery bay", within="HOLD")'),
        page="findings-validators",
    ),
    CodeInfo(
        code="BOUNDARY_NOT_IN_UNIT",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A unit's boundary function belongs to an item outside that unit's subtree.",
        fix=(
            'Declare as the unit\'s boundary only a function of an item built inside that unit. Write: d.device("X1", "DEMO-CONN-2P", interface=True)'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="BOUNDARY_UNCONNECTED",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A unit's boundary function is not connected across the unit nor declared unused.",
        fix=(
            "Wire each boundary function across the unit, or declare it unused on purpose: "
            'inside the unit for its own fact, d.device("X2", "DEMO-CONN-2P", interface=True, unused=True); '
            "in the design that adds it for a point it leaves to another carrier. Write: d.unused(pc.x3[3], pc.x4_1)"
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="CONNECTOR_WIRED_WITHOUT_MATE",
        severity=Severity.WARNING,
        stage="validators",
        who="consumer",
        cause=(
            "A conductor from outside a nested unit lands directly on its boundary connector, "
            "whose part gender is male or female (genderless or unstated passes)."
        ),
        fix=("End a cable's cores at the connector's pins. Write: d.cable(\"W1\", P.CBL).core(1, plug[1], connector[1])"),
        page="findings-validators",
    ),
    CodeInfo(
        code="CONTAINMENT_CYCLE",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="An item's physical-containment parent chain loops back on itself.",
        fix=('Make physical containment a tree: no item sits inside itself. Write: d.device("X1", "DEMO-CONN-2P", parent=k1)'),
        page="findings-validators",
    ),
    CodeInfo(
        code="DOCUMENT_UNIT_UNRESOLVED",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A document's `unit_name` matches no unit, or more than one.",
        fix=(
            "Document each placement with what `d.add` returned; the unit's own PDF comes from its "
            "release write. Write: "
            'fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, placed, cover=Path("cover.md"))'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="HARNESS_HOLDS_PLC_MODULE",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A PLC module sits under an item made with `d.harness`.",
        fix=('Put the PLC modules under a rack, not a harness, so they print flat. Write: d.rack("U1", name="plc")'),
        page="findings-validators",
    ),
    CodeInfo(
        code="HARNESS_WITHOUT_TAG",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause=("A harness (marked, or with a cable child) has no tag or assigned designation, so it has no label."),
        fix='Give the harness a tag so it has a label. Write: d.harness("W5")',
        page="findings-validators",
    ),
    CodeInfo(
        code="ITEM_PART_MISMATCH",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause=(
            "An item's functions or ports do not match its part's templates (missing, extra, "
            "duplicated, or differing in name, kind, role or marking)."
        ),
        fix=(
            "Make the item's functions and ports match its part's templates, by building it "
            'from the part as it stands. Write: d.device("Q1", "DEMO-MCB-3P")'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="ITEM_WITHOUT_PART",
        severity=Severity.INFO,
        stage="validators",
        who="note",
        cause=("A non-external item has no `part`, so its functions are authored directly, not checked against templates."),
        fix="Usually nothing to fix: assign a `part` to check against templates.",
        page="findings-validators",
    ),
    CodeInfo(
        code="MATE_NOT_CONNECTOR",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A mate end is not a connector or terminal (a relay coil, say).",
        fix="Mate only connector or terminal functions. Write: d.mate(plug, connector)",
        page="findings-validators",
    ),
    CodeInfo(
        code="MATE_PORT_MISMATCH",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause=("A mate's two functions have different port names, so some ports have no counterpart."),
        fix=("Mate two connectors whose port names match, so every port has a counterpart. Write: d.mate(j1, j2)"),
        page="findings-validators",
    ),
    CodeInfo(
        code="MATES_DISABLED",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A mate or harness line is refused in 0.22.",
        fix='Use a cable. Write: d.cable("W1", P.CBL)',
        page="findings-validators",
    ),
    CodeInfo(
        code="PLACEMENT_DUPLICATE",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause=("One item is placed more than once in the same aspect (function, location or product)."),
        fix=('Place each item once in each aspect. Write: d.device("X1", "DEMO-CONN-2P", place="A1")'),
        page="findings-validators",
    ),
    CodeInfo(
        code="REVISION_CURRENT_MISSING",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause=("A unit's (or the project's) current revision has no matching `Revision` history entry, so a title block prints no date."),
        fix=('Add a history entry for the current revision. Write: d.revision(1, date="2026-01-01", text="first", created="AB")'),
        page="findings-validators",
    ),
    CodeInfo(
        code="REVISION_DATE_FORMAT",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A revision entry's date is not in `YYYY-MM-DD` format.",
        fix=('Write each revision date as YYYY-MM-DD. Write: d.revision(1, date="2026-01-01", text="first", created="AB")'),
        page="findings-validators",
    ),
    CodeInfo(
        code="REVISION_INITIALS_MISSING",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A revision entry has no `created` (author initials).",
        fix=('Give each revision entry its author\'s initials in `created`. Write: d.revision(1, date="2026-01-01", text="first", created="AB")'),
        page="findings-validators",
    ),
    CodeInfo(
        code="STRIP_WITHOUT_TAG",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause=("A part-less top-level item, usually a floating strip, has no tag and no class code (no terminals, or disagreeing ones)."),
        fix=('Give the strip a tag, a part, or terminals of one class code. Write: d.terminal_strip("X1", "DEMO-TB-2.5", 4)'),
        page="findings-validators",
    ),
    CodeInfo(
        code="SCALING_RANGE_INVALID",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A channel's engineering or raw range has its low value at or above its high value.",
        fix='Write the low value first, below the high value. Write: fn.plc(fr.AI, "level").scale("%", raw=(4, 20), eng=("0", "100"))',
        page="findings-validators",
    ),
    CodeInfo(
        code="SCALING_NOT_ANALOGUE",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A function with an engineering range has no PLC request, or requests a DI, DO or RELAY channel.",
        fix=(
            "Scale only an analogue channel: request it with fr.AI, fr.AO or fr.SignalType.RTD. "
            'Write: fn.plc(fr.AI, "level").scale("%", raw=(4, 20), eng=("0", "100"))'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="SCALING_UNIT_EMPTY",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="The unit of a channel's engineering range is blank or has several lines.",
        fix='Name the unit, e.g. "%" or "bar". Write: fn.plc(fr.AI, "level").scale("%", raw=(4, 20), eng=("0", "100"))',
        page="findings-validators",
    ),
    CodeInfo(
        code="TERMINAL_MORE_THAN_TWO_PINS",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A terminal has over two ports.",
        fix='Use a two-pin part. Write: d.terminal_strip("X1", "DEMO-TB-2.5", 2)',
        page="findings-validators",
    ),
    CodeInfo(
        code="TERMINAL_POINT_OVERFILLED",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A terminal point has more wires and cable cores than its part takes (conductors_per_clamp, default 1).",
        fix='Use a part that takes more, or bridge a second terminal. Write: d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 2)',
        page="findings-validators",
    ),
    CodeInfo(
        code="UNIT_BOUNDARY_BYPASSED",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause=("A conductor or mate crosses out of a unit at a function that is not declared that unit's boundary."),
        fix=('Cross a unit\'s edge only at a function declared as its boundary. Write: d.device("X1", "DEMO-CONN-2P", interface=True)'),
        page="findings-validators",
    ),
    CodeInfo(
        code="UNIT_CYCLE",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A unit's parent chain loops back on itself.",
        fix='Nest units as a tree, adding each unit once. Write: d.add(cabinet, "U1")',
        page="findings-validators",
    ),
    CodeInfo(
        code="UNUSED_NOT_BOUNDARY",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A point named in d.unused is no boundary point of its nested unit.",
        fix="List in d.unused only the boundary points a nested unit offers; remove this one. Write: d.unused(pc.x3[3])",
        page="findings-validators",
    ),
    CodeInfo(
        code="UNUSED_POINT_WIRED",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A boundary point or a port named in d.unused is wired.",
        fix="Remove the point or port from d.unused, or the wire on it. Write: d.unused(pc.x3[4], h1.minus) with only unwired points",
        page="findings-validators",
    ),
    CodeInfo(
        code="UNUSED_CONTRADICTED",
        severity=Severity.WARNING,
        stage="validators",
        who="consumer",
        cause=("A function declared unused is wired, or is a unit boundary connected across the unit the declaration is on."),
        fix=(
            "Declare unused only a function that is wired nowhere, and for a boundary not across "
            "its unit. "
            'Write: d.device("X2", "DEMO-CONN-2P", interface=True, unused=True)'
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="CORE_INDEX_PAST_PRODUCT",
        severity=Severity.ERROR,
        stage="validators",
        who="consumer",
        cause="A cable core is numbered past the core count of the cable's product.",
        fix=("Number the cores from 1 to the product's core count. Write: W1.core(3, x1[1], x1[2])"),
        page="findings-validators",
    ),
)
