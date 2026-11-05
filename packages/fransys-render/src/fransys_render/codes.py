"""The render check's finding codes (BUILD-MESSAGES M1)."""

from typing import Any
lazy from collections.abc import Iterable

from fransys_model.kernel import CodeInfo, Finding, Id, Severity

FINDING_CODES: tuple[CodeInfo, ...] = (
    CodeInfo(
        code="DRAW_PROBLEM",
        severity=Severity.ERROR,
        stage="render",
        who="Fransys",
        cause=(
            "A drawing set holds a record the renderer cannot draw, such as an unknown symbol "
            "key or an outline that is not a rectangle; the set draws no page."
        ),
        fix=("No call clears this: send the smallest model that shows it. The message names the record and what the renderer expected."),
        page="findings-render",
    ),
    CodeInfo(
        code="REFERENCE_OFF_DOCUMENT",
        severity=Severity.WARNING,
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
        severity=Severity.WARNING,
        stage="render",
        who="consumer",
        cause=("The `notice` text passed to `fr.document(notice=)` does not fit the notice cell and would be cut."),
        fix=("Shorten the notice of <subject> to fit its cell. Write: fr.document(<preset>, <subject>, cover=<cover>, notice=<shorter notice>)"),
        page="findings-render",
    ),
    CodeInfo(
        code="TITLE_BLOCK_NO_ROOM",
        severity=Severity.WARNING,
        stage="render",
        who="consumer",
        cause=("The sheet format's title-block band is under the required 20mm, or its title block is under the required 97.5mm wide."),
        fix=(
            "Use a sheet format with a taller title-block band or a wider title block. "
            'Write: [paper] default = "A2" in the settings file, '
            "passed as fr.build(settings=fr.settings(path))"
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="TITLE_BLOCK_STACK_OVERLAP",
        severity=Severity.ERROR,
        stage="render",
        who="consumer",
        cause=("The profile's text height needs a taller title-block band than the sheet format has, so a title-block label overlaps its value."),
        fix=(
            "Use a sheet format whose title-block band is at least the named height, or the "
            'house text height. Write: [paper] default = "A2" in the settings file, '
            "passed as fr.build(settings=fr.settings(path))"
        ),
        page="findings-render",
    ),
    CodeInfo(
        code="TITLE_BLOCK_TEXT_OVERFLOW",
        severity=Severity.WARNING,
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
            "d.function(<name>, <shorter text>) for a page title: the text of a block the page draws."
        ),
        page="findings-render",
    ),
)

_BY_CODE: dict[str, CodeInfo] = {info.code: info for info in FINDING_CODES}


def finding(code: str, subjects: Iterable[Id[Any]], message: str, **fix_values: str) -> Finding:
    """The `Finding` of `code`: its one severity, its fix filled from `fix_values`."""
    return _BY_CODE[code].finding(subjects, message, **fix_values)
