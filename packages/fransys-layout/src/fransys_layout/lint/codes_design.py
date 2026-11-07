"""Layout's finding codes a consumer acts on (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="BOARD_NETS_NOT_DRAWN",
        severity=Severity.ERROR,
        stage="render",
        who="consumer",
        cause=("A board shares its unit with another top-level device, so layout draws it as a black box and drops the nets between its parts."),
        fix=(
            "Make the board its own unit's only top-level device, with its parts as children. "
            'Write: @fr.unit(...) def board(d): b = d.device("A1", "DEMO-PCB-IO") and '
            'd.device("J1", "DEMO-CONN-2P", parent=b) in a unit of their own.'
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="CONNECTION_TO_UNDRAWN",
        severity=Severity.WARNING,
        stage="render",
        who="consumer",
        cause="A connection, net group or rail has an end whose function layout never draws.",
        fix=(
            "Put the missing end's item in a drawn unit or location, or remove the connection. "
            "Write: d.function(name, text) to place that item in a drawn group."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="ORDER_HINT_UNMET",
        severity=Severity.WARNING,
        stage="render",
        who="consumer",
        cause=("An authored order hint names two groups that are not on the same drawing set, so no page order can honour it."),
        fix=("Move both groups onto one drawing set, or drop the hint. Write: d.layout.order(a, b) for groups on one drawing set."),
        page="findings-render",
    ),
    CodeInfo(
        code="WIRE_AS_REFERENCE",
        severity=Severity.INFO,
        stage="render",
        who="consumer",
        cause=("No orthogonal path on the wiring grid could be found for a connection, so it is drawn as a reference at its pin."),
        fix=("None needed: the connection is shown by its reference. To draw it as a wire, give its ports more room."),
        page="findings-render",
    ),
)
