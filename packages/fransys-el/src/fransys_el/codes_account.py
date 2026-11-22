"""The code of the core's account check (CORE-ACCOUNT, R2650)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="CONNECTION_NOT_ACCOUNTED",
        severity=Severity.WARNING,
        stage="render",
        who="Fransys",
        cause=("No wire or marker accounts for a conductor end, or a wire and a stub both do, or two stubs do (CORE-ACCOUNT); the message names it."),
        fix="No call clears this: send the smallest model that shows it.",
        page="findings-render",
    ),
)
