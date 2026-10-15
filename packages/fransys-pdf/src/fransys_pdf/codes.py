"""The PDF check's finding codes (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="COVER_OVERFLOW",
        severities=(Severity.WARNING,),
        stage="pdf",
        who="consumer",
        cause=(
            "A document's cover text plus revision table are estimated taller than the content box."
        ),
        fix="Shorten the cover or revision text.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="DOCUMENT_EMPTY_LIST",
        severities=(Severity.INFO,),
        stage="pdf",
        who="note",
        cause=(
            "A document's list page (PLC, terminal, connector, wire-label, designation, cable "
            "or BOM) has no rows and is left out."
        ),
        fix="Usually nothing to fix (pdf-0019); add records to show it.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="DOCUMENT_MIXED_SHEET_FORMATS",
        severities=(Severity.ERROR,),
        stage="pdf",
        who="consumer",
        cause="A document's pages use more than one sheet format.",
        fix="Give the document (or its unit/layout profile) one sheet format for all pages.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="DOCUMENT_NO_DRAWINGS",
        severities=(Severity.ERROR,),
        stage="pdf",
        who="consumer",
        cause=(
            "A SCHEMATIC page has no drawing set and the document has no other content page, "
            "or a HARNESS_DRAWING or BLOCK_DIAGRAM page has no cable or diagram, or a drawing "
            "is missing, too large or not drawable yet: interleaved harness cables, or a block "
            "diagram whose tallest column is taller than one sheet (a known limit of the system "
            "diagram; `DIAGRAM_COLUMN_TOO_TALL` names the column)."
        ),
        fix="Add the missing content, remove the page kind or shorten the texts.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="DOCUMENT_NO_TOP_LEVEL_CABLES",
        severities=(Severity.INFO,),
        stage="pdf",
        who="note",
        cause=(
            "A SYSTEM document's HARNESS_DRAWING section has nothing to draw: the model has no "
            "top-level cable."
        ),
        fix="Usually nothing to fix: add a top-level cable if one was expected.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="DRAWING_SET_REPLICA_ONLY",
        severities=(Severity.INFO,),
        stage="pdf",
        who="note",
        cause="A document's drawing set holds only black-box replicas of another unit's boundary.",
        fix="Usually nothing to fix; add content if a page is intended.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="MARKDOWN_UNSUPPORTED",
        severities=(Severity.ERROR,),
        stage="pdf",
        who="consumer",
        cause=(
            "A document's cover or notes text uses a Markdown construct the PDF renderer does "
            "not support."
        ),
        fix="Rewrite it using only the supported Markdown subset.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="TITLE_BLOCK_NOTICE_OVERFLOW",
        severities=(Severity.WARNING,),
        stage="pdf",
        who="consumer",
        cause=(
            "The `notice` text passed to `fr.document(notice=)` does not fit the notice cell "
            "and would be cut."
        ),
        fix="Shorten the `notice` text in `fr.document(notice=)`.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="TITLE_BLOCK_NO_ROOM",
        severities=(Severity.WARNING,),
        stage="pdf",
        who="consumer",
        cause="The sheet format's title-block band is under the required 20mm.",
        fix="Use a sheet format with a taller title-block band.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="TITLE_BLOCK_TEXT_OVERFLOW",
        severities=(Severity.WARNING,),
        stage="pdf",
        who="consumer",
        cause=(
            "A one-line title-block field (title, number, customer, revision, date, author, "
            "page title, scope or sheet counter) does not fit its cell."
        ),
        fix="Shorten the text; for a page title, set a shorter one with `d.layout.page_title`.",
        page="findings-pdf",
    ),
    CodeInfo(
        code="TITLE_BLOCK_UNIT_IDENTITY_MISSING",
        severities=(Severity.WARNING,),
        stage="pdf",
        who="consumer",
        cause=(
            "A unit document's unit has an empty `title` or `number`, so that title-block cell "
            "will print empty."
        ),
        fix="Give the unit release a `title` and/or `number`.",
        page="findings-pdf",
    ),
)
