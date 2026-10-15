"""`BuildErrors` prints each finding under one `CODE (severity):` head (BUILD-MESSAGES M6)."""

import fransys as fr
from fransys._codes import BY_CODE
from fransys.pipeline import BuildErrors

SITE = "https://olejbondahl.github.io/fransys/"


def _row_url(info) -> str:
    """The independent spelling of the row URL: site, version, page, code anchor."""
    return f"{SITE}{fr.__version__}/guide/{info.page}/#{info.code.lower()}"


def _finding(message: str) -> fr.Finding:
    return fr.Finding(
        code="UNIT_REVISION_CLASH", severity=fr.Severity.ERROR, subjects=(), message=message
    )


def test_a_described_message_keeps_its_one_head() -> None:
    head = "UNIT_REVISION_CLASH (error): two releases\n  subject: unit -U1"
    text = str(BuildErrors((_finding(head),)))
    assert text.count("UNIT_REVISION_CLASH") == 1
    assert text.startswith("UNIT_REVISION_CLASH (error): two releases")


def test_a_plain_message_gets_the_same_head() -> None:
    text = str(BuildErrors((_finding("two releases"),)))
    assert text.startswith("UNIT_REVISION_CLASH (error): two releases")


def test_an_error_ends_with_its_fix_and_findings_row_url() -> None:
    finding = fr.Finding(
        code="EXPORT_NAME_CLASH", severity=fr.Severity.ERROR, subjects=(), message="two subjects"
    )
    info = BY_CODE["EXPORT_NAME_CLASH"]
    lines = str(BuildErrors((finding,))).splitlines()
    assert lines[-2:] == [f"  fix: {info.fix}", f"  see: {_row_url(info)}"]
