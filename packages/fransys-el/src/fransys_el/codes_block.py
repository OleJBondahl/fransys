"""The code of the cable-block check (PROOF-S5, el-0122)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="HARNESS_WIRE_MISMATCH",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause=(
            "A wire drawn in a cable or harness block page differs from the harness-wire row of the model: another core, "
            "other ends or another cable, or a row is not drawn once. The message names the cable, the core and the ends."
        ),
        fix="No call clears this: send the smallest model that shows it. The message names the cable and the core.",
        page="findings-render",
    ),
)
