"""Model finding codes for things the placement problem left out of the drawing (model-0314)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="FUNCTION_NOT_DRAWN",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A function of a connected set has no symbol (reason function_without_symbol), so "
            "the layout leaves it out of the drawing. The message names the function and the "
            "reason."
        ),
        fix=(
            "Give the function a part whose kind has a symbol. Write: "
            'd.device("K1", "DEMO-RLY-2CO-24")'
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="FUNCTION_NOT_WIRED",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A function's symbol is on no net, so the page leaves it off (reason "
            "function_unwired). The message names the function."
        ),
        fix=(
            "Wire a pin of <subject> to another function, or remove it. Write: d.detail.wire(a, b)."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="NET_NOT_DRAWN",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A net of two or more ends has under two drawn pins, so it is "
            "left out. A lone pin gives none. The message names the port."
        ),
        fix="Give the net a second drawn pin. Write: d.series(a, <subject>)",
        page="findings-render",
    ),
    CodeInfo(
        code="NET_CUT_BY_SET",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A net has one end in a drawing set and its other end in another (a different "
            "unit or location), so the core path draws it in neither. The message names the "
            "net and the set."
        ),
        fix=(
            "Put the functions the net joins in one unit and one location. Write: "
            'd.device("K1", "DEMO-RLY-2CO-24", place="R") for each, with the same place.'
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="SET_WITHOUT_PAGE",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A drawing set holds symbols but every net of them has its other end in another "
            "set, so the core path gives it no page. The message names the set."
        ),
        fix=(
            "Put the set's functions in the unit and location of the functions they are wired "
            'to. Write: d.device("K1", "DEMO-RLY-2CO-24", place="R") with the same place.'
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="SPARE_FUNCTIONS",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause=(
            "A function on no net, on an item that has other wired functions, is a spare: it is "
            "left off the schematic. One finding per document names the count and the items."
        ),
        fix="Nothing is wrong; wire the function if it is not a spare.",
        page="findings-render",
    ),
    CodeInfo(
        code="SPARE_TERMINALS",
        severities=(Severity.INFO,),
        stage="render",
        who="note",
        cause=(
            "A terminal none of whose nets has a second end is a spare: it stands in the "
            "terminal list and is not drawn on the schematic. One finding per document names "
            "the count and the strips."
        ),
        fix="Nothing is wrong; wire the terminal if it is not a spare.",
        page="findings-render",
    ),
    CodeInfo(
        code="HINT_NOT_READ",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "An authored layout hint is kept in the model but the core path does not read it, "
            "so the drawing ignores it. The message names the hint and the function."
        ),
        fix=(
            "No call clears this: delete the d.layout.side line for <subject> from the design, "
            "or keep it for the old engine, which reads it."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="UNPRINTED_SET",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A drawing set has pages but no document prints it, so its items are not in any "
            "export. The message names the set and its items."
        ),
        fix=(
            "Add a document for the set's unit or location, or nest the unit in one that has "
            'one. Write: fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-mini-mcc")'
        ),
        page="findings-render",
    ),
)
