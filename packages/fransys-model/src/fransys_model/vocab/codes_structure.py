"""The model validators' finding codes about structure, units and revisions (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="ASPECT_CROSS_PARENT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "An aspect node's parent belongs to a different aspect (function, location or product)."
        ),
        fix="Move the node under a parent of the same aspect, or fix its authored parent.",
        page="findings-validators",
    ),
    CodeInfo(
        code="ASPECT_CYCLE",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="An aspect node's parent chain loops back on itself.",
        fix="Correct the parent authored on one of the looping nodes.",
        page="findings-validators",
    ),
    CodeInfo(
        code="BOUNDARY_NOT_IN_UNIT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A unit's boundary function belongs to an item outside that unit's subtree.",
        fix=(
            "Declare the boundary on a function whose item is in the unit, or fix the item's "
            "unit/parent."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="BOUNDARY_UNCONNECTED",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A unit's boundary function is not connected across the unit nor declared unused.",
        fix=(
            "Wire the boundary, or leave it open: `unused=` on `d.add` for one instance, on "
            "`d.device` for all. A unit alone in its design never fires it, nor an interface "
            "passed up from a nested unit."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="CONNECTOR_WIRED_WITHOUT_MATE",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause=(
            "A conductor from outside a nested unit lands directly on its boundary connector, "
            "whose part gender is male or female (neutral or unstated passes)."
        ),
        fix=(
            "Mate a plug to the boundary connector (`u.mate(plug, connector)`) and wire the "
            "plug's pin instead."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="CONTAINMENT_CYCLE",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="An item's physical-containment parent chain loops back on itself.",
        fix="Correct the parent authored on one of the looping items.",
        page="findings-validators",
    ),
    CodeInfo(
        code="DOCUMENT_UNIT_UNRESOLVED",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A document's `unit_name` matches no unit, or more than one.",
        fix="Make the unit name unique so `unit_name` resolves to one instance.",
        page="findings-validators",
    ),
    CodeInfo(
        code="HARNESS_HOLDS_PLC_MODULE",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A PLC module sits under an item made with `d.harness`.",
        fix="Build the rack with `d.rack`, so its modules print flat.",
        page="findings-validators",
    ),
    CodeInfo(
        code="HARNESS_WITHOUT_TAG",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A harness (marked, or with a cable child) has no tag or assigned designation, so "
            "it has no label."
        ),
        fix="Give it a tag: `d.harness(tag=...)`, or `tag=` on the item.",
        page="findings-validators",
    ),
    CodeInfo(
        code="ITEM_PART_MISMATCH",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "An item's functions or ports do not match its part's templates (missing, extra, "
            "duplicated, or differing in name, kind, role or marking)."
        ),
        fix="Fix the item's authored functions and ports (or the part's templates) so they agree.",
        page="findings-validators",
    ),
    CodeInfo(
        code="ITEM_WITHOUT_PART",
        severities=(Severity.INFO,),
        stage="validators",
        who="note",
        cause=(
            "A non-external item has no `part`, so its functions are authored directly, not "
            "checked against templates."
        ),
        fix="Usually nothing to fix: assign a `part` to check against templates.",
        page="findings-validators",
    ),
    CodeInfo(
        code="MATE_NOT_CONNECTOR",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A mate end is not a connector or terminal (a relay coil, say).",
        fix="Mate a connector or terminal.",
        page="findings-validators",
    ),
    CodeInfo(
        code="MATE_PORT_MISMATCH",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause=(
            "A mate's two functions have different port names, so some ports have no counterpart."
        ),
        fix=(
            "Example: a lettered inlet (L1, L2, L3, N, PE) mated to a numbered plug. Rename "
            "the ports to match."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="PLACEMENT_DUPLICATE",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "One item is placed more than once in the same aspect (function, location or product)."
        ),
        fix="Remove the duplicate placement so the item is placed once per aspect.",
        page="findings-validators",
    ),
    CodeInfo(
        code="REVISION_CURRENT_MISSING",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A unit's (or the project's) current revision has no matching `Revision` history "
            "entry, so a title block prints no date."
        ),
        fix=(
            "Add the missing entry: `history=` on `@fr.unit`, or `Design.revision(rev, date=, "
            "text=, created=)`."
        ),
        page="findings-validators",
    ),
    CodeInfo(
        code="REVISION_DATE_FORMAT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A revision entry's date is not in `YYYY-MM-DD` format.",
        fix="Rewrite the date as `YYYY-MM-DD`.",
        page="findings-validators",
    ),
    CodeInfo(
        code="REVISION_INITIALS_MISSING",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A revision entry has no `created` (author initials).",
        fix="Add the author's initials to the revision entry's `created` field.",
        page="findings-validators",
    ),
    CodeInfo(
        code="STRIP_WITHOUT_TAG",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A part-less top-level item, usually a floating strip, has no tag and no class "
            "code (no terminals, or disagreeing ones)."
        ),
        fix="Give it a part, a tag, or terminals of one class code.",
        page="findings-validators",
    ),
    CodeInfo(
        code="UNIT_BOUNDARY_BYPASSED",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause=(
            "A conductor or mate crosses out of a unit at a function that is not declared that "
            "unit's boundary."
        ),
        fix="Declare it the unit's boundary, or route it through an existing boundary function.",
        page="findings-validators",
    ),
    CodeInfo(
        code="UNIT_CYCLE",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A unit's parent chain loops back on itself.",
        fix="Correct the parent authored on one of the looping units.",
        page="findings-validators",
    ),
    CodeInfo(
        code="UNUSED_CONTRADICTED",
        severities=(Severity.WARNING,),
        stage="validators",
        who="consumer",
        cause=(
            "A boundary declared unused names a function that is no unit's boundary, or is "
            "connected across the unit the declaration is on."
        ),
        fix="Remove `unused=` if the function is wired, or fix the unit/function it names.",
        page="findings-validators",
    ),
    CodeInfo(
        code="CORE_INDEX_PAST_PRODUCT",
        severities=(Severity.ERROR,),
        stage="validators",
        who="consumer",
        cause="A cable core is numbered past the core count of the cable's product.",
        fix="Use a core from 1 to the product's core count, or choose a part with more cores.",
        page="findings-validators",
    ),
)
