"""The code of a refused drawing set (R3155): the note beside the ERROR that stopped its drawing."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="DRAWING_SET_REFUSED",
        severity=Severity.INFO,
        stage="render",
        who="note",
        cause="A layout ERROR refused a drawing set: its drawing is not written and its drawn-page checks did not run. The message names the set.",
        fix="Nothing more to do here; clear the ERROR that refused the set, and the set is drawn and checked.",
        page="findings-render",
    ),
)
