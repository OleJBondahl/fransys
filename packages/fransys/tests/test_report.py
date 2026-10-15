"""`fr.report`: one readable text of a build's findings (BUILD-MESSAGES M10)."""

import fransys as fr
from fransys import _codes, _report

_SITE = "https://olejbondahl.github.io/fransys/"
_PATCHED = fr.build(fr.design("demo_parts"))  # an empty build; check is patched over it


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
    info = _codes.BY_CODE["DOCUMENT_NO_DRAWINGS"]
    lines = fr.report(_built_with_a_document(tmp_path)).splitlines()
    assert [line for line in lines if not line.startswith("  at: ")] == [
        "build: 1 error, 0 warnings, 3 notes",
        "DOCUMENT_NO_DRAWINGS (error): SCHEMATIC: no drawing set found",
        f"  fix: {info.fix}",
        f"  see: {_SITE}{fr.__version__}/guide/findings-pdf/#document_no_drawings",
        "notes: DOCUMENT_EMPTY_LIST 3",
    ]


def test_each_subject_prints_as_an_at_line(monkeypatch):
    warning = fr.Finding(
        code="LONE_CELL",
        severity=fr.Severity.WARNING,
        subjects=(),
        message="LONE_CELL (warning): a symbol has no drawn conductor at all (p1.1: -K1)\n"
        "  subject: build.py:12 (K1)\n  subject: build.py:14 (K2)",
    )
    note = fr.Finding(code="PAGE_UNDERFILLED", severity=fr.Severity.INFO, subjects=(), message="")
    monkeypatch.setattr(_report, "check", lambda _result: (warning, note))
    assert fr.report(_PATCHED).splitlines() == [
        "build: 0 errors, 1 warning, 1 note",
        "LONE_CELL (warning): a symbol has no drawn conductor at all (p1.1: -K1)",
        "  at: build.py:12 (K1)",
        "  at: build.py:14 (K2)",
        f"  fix: {_codes.BY_CODE['LONE_CELL'].fix}",
        f"  see: {_SITE}{fr.__version__}/guide/findings-render/#lone_cell",
        "notes: PAGE_UNDERFILLED 1",
    ]


def test_a_clean_build_reports_no_notes_line(monkeypatch):
    monkeypatch.setattr(_report, "check", lambda _result: ())
    assert fr.report(_PATCHED) == "build: 0 errors, 0 warnings, 0 notes\n"
