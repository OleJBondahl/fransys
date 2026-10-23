"""`fr.report`: one readable text of a build's findings (BUILD-MESSAGES M10)."""

import fransys as fr
import pytest
from fransys import _codes, _report
from fransys._finding_text import described_parts, filled_fix

from fransys_model.kernel import SchemaError

_SITE = "https://olejbondahl.github.io/fransys/"
_PATCHED = fr.build(fr.design("demo_parts"))  # an empty build; the raw findings are patched over it


def _built_with_a_document(tmp_path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    x1 = d.device("X1", "DEMO-CONN-2P")
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(
        d,
        fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC, x1, cover=cover, remove=(fr.PageKind.BOM,)
        ),
    )


def test_a_report_gives_the_summary_each_error_and_the_notes(tmp_path):
    lines = fr.report(_built_with_a_document(tmp_path)).splitlines()
    fix = next(line for line in lines if line.startswith("  fix: "))
    assert "<subject>" not in fix
    assert [line for line in lines if not line.startswith("  at: ")] == [
        "build: 1 error, 0 warnings, 3 notes",
        "DOCUMENT_NO_DRAWINGS (error): SCHEMATIC: no drawing set found",
        fix,
        f"  see: {_SITE}{fr.__version__}/guide/findings-pdf/#document_no_drawings",
        "notes: DOCUMENT_EMPTY_LIST 3",
    ]


def test_each_subject_prints_as_an_at_line(monkeypatch):
    """The subjects come from the kernel's structured description, not from the joined text."""
    d = fr.design("demo_parts")
    d.device("X1", "DEMO-CONN-2P")
    d.device("X2", "DEMO-CONN-2P")
    result = fr.build(d)
    subjects = tuple(result.model.origins)[:2]
    warning = fr.Finding(
        code="KEEP_TOGETHER_UNMET",
        severity=fr.Severity.WARNING,
        subjects=subjects,
        message="a keep_together set spans two drawing sets (p1.1: -K1)",
        fix=_codes.BY_CODE["KEEP_TOGETHER_UNMET"].fix,
    )
    note = fr.Finding(code="TEXT_OVERLAP", severity=fr.Severity.INFO, subjects=(), message="")
    monkeypatch.setattr(_report, "_raw_findings", lambda _result, _svgs: (warning, note))
    lines = fr.report(result).splitlines()
    assert lines[:2] == [
        "build: 0 errors, 1 warning, 1 note",
        "KEEP_TOGETHER_UNMET (warning): a keep_together set spans two drawing sets (p1.1: -K1)",
    ]
    assert lines[2:4] == [f"  at: {s}" for s in described_parts(warning, result.model).subjects]
    assert lines[4:] == [
        f"  fix: {filled_fix(warning, result.model)}",
        f"  see: {_SITE}{fr.__version__}/guide/findings-render/#keep_together_unmet",
        "notes: TEXT_OVERLAP 1",
    ]


def test_a_clean_build_reports_no_notes_line(monkeypatch):
    monkeypatch.setattr(_report, "_raw_findings", lambda _result, _svgs: ())
    assert fr.report(_PATCHED) == "build: 0 errors, 0 warnings, 0 notes\n"


def test_a_report_fills_the_subject_placeholder_and_keeps_others_literal(monkeypatch):
    d = fr.design("demo_parts")
    d.device("X1", "DEMO-CONN-2P")
    result = fr.build(d)
    subject = next(i for i in result.model.origins if i.kind == "item")
    finding = fr.Finding(
        code="LONE_CELL",
        severity=fr.Severity.WARNING,
        subjects=(subject,),
        message="m",
        fix="Fix <subject> with <preset>",
    )
    monkeypatch.setattr(_report, "_raw_findings", lambda _result, _svgs: (finding,))
    fix_line = next(x for x in fr.report(result).splitlines() if x.startswith("  fix: "))
    assert "<subject>" not in fix_line
    assert fix_line.endswith(" with <preset>")


def test_a_report_with_a_subject_placeholder_and_no_subject_raises(monkeypatch):
    finding = fr.Finding(
        code="LONE_CELL",
        severity=fr.Severity.WARNING,
        subjects=(),
        message="m",
        fix="Fix <subject>",
    )
    monkeypatch.setattr(_report, "_raw_findings", lambda _result, _svgs: (finding,))
    with pytest.raises(SchemaError, match=r"LONE_CELL.*<subject>"):
        fr.report(_PATCHED)
