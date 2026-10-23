"""`BuildErrors` prints each finding under one `CODE (severity):` head (BUILD-MESSAGES M6)."""

import fransys as fr
import pytest
from fransys._codes import BY_CODE
from fransys._finding_text import filled_fix
from fransys.pipeline import BuildErrors

from fransys_model.kernel import SchemaError

SITE = "https://olejbondahl.github.io/fransys/"
_DESIGN = fr.design("demo_parts")
_DESIGN.device("X1", "DEMO-CONN-2P")
_DESIGN.device("X2", "DEMO-CONN-2P")
_MODEL = fr.build(_DESIGN).model


def _row_url(info) -> str:
    """The independent spelling of the row URL: site, version, page, code anchor."""
    return f"{SITE}{fr.__version__}/guide/{info.page}/#{info.code.lower()}"


def _finding(message: str) -> fr.Finding:
    return fr.Finding(
        code="UNIT_REVISION_CLASH",
        severity=fr.Severity.ERROR,
        subjects=(),
        message=message,
        fix="Write: x",
    )


def test_a_described_message_keeps_its_one_head() -> None:
    head = "UNIT_REVISION_CLASH (error): two releases\n  subject: unit -U1"
    text = str(BuildErrors((_finding(head),), model=_MODEL))
    assert text.count("UNIT_REVISION_CLASH") == 1
    assert text.startswith("UNIT_REVISION_CLASH (error): two releases")


def test_a_plain_message_gets_the_same_head() -> None:
    text = str(BuildErrors((_finding("two releases"),), model=_MODEL))
    assert text.startswith("UNIT_REVISION_CLASH (error): two releases")


def test_an_error_ends_with_its_fix_and_findings_row_url() -> None:
    info_fix = BY_CODE["EXPORT_NAME_CLASH"].fix
    finding = fr.Finding(
        code="EXPORT_NAME_CLASH",
        severity=fr.Severity.ERROR,
        subjects=tuple(i for i in _MODEL.origins if i.kind == "item")[:2],
        message="two subjects",
        fix=info_fix,
    )
    info = BY_CODE["EXPORT_NAME_CLASH"]
    lines = str(BuildErrors((finding,), model=_MODEL)).splitlines()
    assert lines[-2:] == [f"  fix: {filled_fix(finding, _MODEL)}", f"  see: {_row_url(info)}"]


def _templated(fix: str, subjects: tuple = ()) -> fr.Finding:
    return fr.Finding(
        code="UNIT_REVISION_CLASH",
        severity=fr.Severity.ERROR,
        subjects=subjects,
        message="m",
        fix=fix,
    )


def test_a_subject_placeholder_prints_the_subjects_text_and_others_stay_literal() -> None:
    subject = next(i for i in _MODEL.origins if i.kind == "item")
    finding = _templated("Move <subject> to <preset>", (subject,))
    text = str(BuildErrors((finding,), model=_MODEL))
    assert "  fix: Move " in text
    assert "<subject>" not in text
    assert " to <preset>" in text
    assert finding.fix == "Move <subject> to <preset>"


def test_a_subject_placeholder_with_no_subject_raises() -> None:
    with pytest.raises(SchemaError, match=r"UNIT_REVISION_CLASH.*<subject>.*Move <subject>"):
        BuildErrors((_templated("Move <subject>"),), model=_MODEL)
