"""Layout's finding codes a consumer acts on (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="CONNECTION_TO_UNDRAWN",
        severity=Severity.ERROR,
        stage="render",
        who="consumer",
        cause="A connection, net group or rail has an end whose function layout never draws.",
        fix=(
            "Put the missing end's item in a drawn unit or location, or remove the connection. "
            "Write: d.function(name, text) to place that item in a drawn group."
        ),
        page="findings-wires",
    ),
    CodeInfo(
        code="WIRE_AS_REFERENCE",
        severity=Severity.INFO,
        stage="render",
        who="consumer",
        cause=("No orthogonal path on the wiring grid could be found for a connection, so it is drawn as a reference at its pin."),
        fix=("None needed: the connection is shown by its reference. To draw it as a wire, give its ports more room."),
        page="findings-wires",
    ),
)
