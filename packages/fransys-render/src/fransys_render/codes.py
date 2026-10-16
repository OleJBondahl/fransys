"""The render check's finding codes (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="DRAWING_SHORTS_NETS",
        severities=(Severity.INFO,),
        stage="render",
        who="Fransys",
        cause=(
            "A page draws two nets joined that the wiring keeps apart: a stub, a wire end or a "
            "power symbol lies on, or crosses, another net's wire or symbol."
        ),
        fix=(
            "A Fransys defect: send the smallest model that shows it. Check first that no "
            "authored hint crowds the nets."
        ),
        page="findings-render",
    ),
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
        code="REFERENCE_OFF_DOCUMENT",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A printed reference points to a page that no page of its own document holds, and its "
            "text prints no location, so a reader cannot tell which document to open. The message "
            "names the reference, its page and the target page."
        ),
        fix=(
            "Print both drawing sets in one document, or give the target's drawing set a "
            "location so the reference names it."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="TITLE_BLOCK_NOTICE_OVERFLOW",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "The `notice` text passed to `fr.document(notice=)` does not fit the notice cell "
            "and would be cut."
        ),
        fix="Shorten the `notice` text in `fr.document(notice=)`.",
        page="findings-render",
    ),
    CodeInfo(
        code="TITLE_BLOCK_NO_ROOM",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "The sheet format's title-block band is under the required 20mm, "
            "or its title block is under the required 97.5mm wide."
        ),
        fix="Use a sheet format with a taller title-block band or a wider sheet.",
        page="findings-render",
    ),
    CodeInfo(
        code="TITLE_BLOCK_STACK_OVERLAP",
        severities=(Severity.ERROR,),
        stage="render",
        who="consumer",
        cause=(
            "The profile's text height needs a taller title-block band than the sheet format "
            "has, so a title-block label overlaps its value."
        ),
        fix=(
            "Use a sheet format whose title-block band is at least the named height, "
            "or the house text height."
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="TITLE_BLOCK_TEXT_OVERFLOW",
        severities=(Severity.WARNING,),
        stage="render",
        who="consumer",
        cause=(
            "A one-line title-block field (title, number, customer, revision, date, author, "
            "page title, scope or sheet counter) does not fit its cell."
        ),
        fix="Shorten the text; for a page title, set a shorter one with `d.layout.page_title`.",
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
