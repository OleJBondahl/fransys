"""The render check's finding codes (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="LAYOUT_MISSING",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause=(
            "The model has connected functions to draw, but layout made no page for them. A "
            "function with nothing connected is drawn on no page and does not count."
        ),
        fix=(
            "Add a document so layout runs, and check the drawn location or unit holds the "
            "connected content."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="LIBRARY_VERSION_MISMATCH",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A placement was laid out against a symbol library version other than the "
            "installed one."
        ),
        fix="Re-run layout (build) with the installed `electrical_symbols` version.",
        page="findings-render",
    ),
    CodeInfo(
        code="UNKNOWN_SYMBOL_KEY",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause="A placement's symbol key is not in the installed symbol library.",
        fix=(
            "Fix the symbol key (rule, choice, or part data), or install a library version with it."
        ),
        page="findings-render",
    ),
)
