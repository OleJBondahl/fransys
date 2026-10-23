"""The PDF check's finding codes (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="COVER_OVERFLOW",
        severities=(Severity.ERROR,),
        stage="write, release",
        who="consumer",
        cause=(
            "A document's cover text plus revision table, measured by Typst at write, are taller "
            "than the content box; the write raises and writes nothing."
        ),
        fix=(
            "Shorten the cover file or the revision table of <subject>. Write: "
            "fr.document(<preset>, <subject>, cover=<shorter cover file>)"
        ),
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
        fix=(
            "Give <subject> one sheet format for all its pages. "
            'Write: [paper] default = "A2" in the settings file, '
            "passed as fr.build(settings=fr.settings(path))"
        ),
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
        fix=(
            "Add the missing content, shorten the texts, or remove the page kind from <subject>. "
            "Write: fr.document(<preset>, <subject>, cover=<cover>, remove=(<page kind>,))"
        ),
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
        fix=(
            "No call clears this: rewrite the cover or notes text of <subject> using only the "
            "supported Markdown subset."
        ),
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
        fix=(
            "Give the unit release a title and a number. "
            "Write: fr.unit(<name>, title=<title>, number=<number>, ...)"
        ),
        page="findings-pdf",
    ),
)

_BY_CODE: dict[str, CodeInfo] = {info.code: info for info in FINDING_CODES}


def fix_text(code: str, **values: str) -> str:
    """The `fix` of one finding of `code`: the code's template filled with `values`."""
    return _BY_CODE[code].filled(**values)
