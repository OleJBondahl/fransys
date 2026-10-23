"""The render check's finding codes (BUILD-MESSAGES M1)."""

from fransys_model.kernel import CodeInfo, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="DRAW_PROBLEM",
        severities=(Severity.ERROR,),
        stage="render",
        who="Fransys",
        cause=(
            "A drawing set holds a record the renderer cannot draw, such as an unknown symbol "
            "key or an outline that is not a rectangle; the set draws no page."
        ),
        fix=(
            "No call clears this: send the smallest model that shows it. The message names the "
            "record and what the renderer expected."
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
            "Wire the functions you want drawn into current paths inside function blocks. "
            "Write: d.series(a, b, c)"
        ),
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
            "location so the reference names it. "
            "Write: fr.document(<preset>, <subject>, cover=<cover>)"
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
        fix=(
            "Shorten the notice of <subject> to fit its cell. Write: fr.document(<preset>, "
            "<subject>, cover=<cover>, notice=<shorter notice>)"
        ),
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
        fix=(
            "Use a sheet format with a taller title-block band or a wider title block. "
            'Write: [paper] default = "A2" in the settings file, '
            "passed as fr.build(settings=fr.settings(path))"
        ),
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
            "Use a sheet format whose title-block band is at least the named height, or the "
            'house text height. Write: [paper] default = "A2" in the settings file, '
            "passed as fr.build(settings=fr.settings(path))"
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
        fix=(
            "Shorten the field the message names. Write: d.project(title=<shorter text>, "
            "number=<number>, customer=<shorter text>, revision=<n>, author=<shorter text>) "
            "for the title, number, customer, revision or author, or "
            "d.layout.page_title(<thing>, <shorter text>) for a page title."
        ),
        page="findings-render",
    ),
)

_BY_CODE: dict[str, CodeInfo] = {info.code: info for info in FINDING_CODES}


def fix_text(code: str, **values: str) -> str:
    """The `fix` of one finding of `code`: the code's template filled with `values`."""
    return _BY_CODE[code].filled(**values)
