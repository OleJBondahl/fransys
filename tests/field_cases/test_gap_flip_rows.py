"""Every strict xfail of the field cases names a `GAP-FLIP-<n>` row (FLIP-NOW Acceptance 3)."""

import re
from pathlib import Path

from _gap_flip import GAP_PREFIX, gaps, mark_gaps, other_gaps
lazy import pytest

ROW = re.compile(r"GAP-(?:FLIP-(?:\d+|DRAWING-SUBJECT)|OTHER-CYCLE)")
HERE = Path(__file__).parent


def test_every_gap_entry_names_a_row_of_the_gap_shape() -> None:
    bad = {t: g for t, g in gaps().items() if not ROW.fullmatch(g)}
    assert bad == {}


def test_every_gap_entry_names_a_test_that_exists() -> None:
    missing = [t for t in gaps() if not (HERE / t.partition("::")[0]).is_file()]
    assert missing == []


def test_the_shape_check_can_fail() -> None:
    assert not ROW.fullmatch("closed-later")
    assert not ROW.fullmatch("GAP-FLIP-")
    assert ROW.fullmatch("GAP-OTHER-CYCLE")


class _Item:
    def __init__(self, nodeid: str) -> None:
        self.nodeid = nodeid
        self.marks: list[pytest.MarkDecorator] = []
        self.appended = True

    def add_marker(self, mark: pytest.MarkDecorator, *, append: bool = True) -> None:
        self.marks.append(mark)
        self.appended = append


def test_the_hook_adds_a_strict_xfail_naming_the_row_and_only_to_listed_cases() -> None:
    listed = GAP_PREFIX + next(iter(gaps()))
    hit, other = _Item(listed), _Item(GAP_PREFIX + "test_not_listed.py::test_x")
    mark_gaps([hit, other])  # ty: ignore[invalid-argument-type] - stand-in items
    (mark,) = hit.marks
    assert mark.kwargs["strict"] is True
    assert ROW.search(mark.kwargs["reason"])
    assert other.marks == []


def test_every_other_gap_entry_names_a_row_and_an_existing_file() -> None:
    root = HERE.parents[1]
    table = other_gaps()
    assert {t: g for t, g in table.items() if not ROW.fullmatch(g)} == {}
    assert [t for t in table if not (root / t.partition("::")[0]).is_file()] == []


def test_no_public_gap_row_names_an_internal_file() -> None:
    named = [t for t in (*gaps(), *other_gaps()) if Path(t).parts[0] == "internal"]
    assert named == []


_STRICT_XFAIL = re.compile(r"xfail\((?:[^()]|\([^()]*\))*?strict\s*=\s*True")
_ALLOWED = {
    "tests/_gap_flip.py",
    "tests/field_cases/test_gap_flip_rows.py",
    Path("internal", "tests", "test_branch_guard.py").as_posix(),
}


def _strict_xfail_sites(root: Path) -> list[str]:
    folders = [root / "tests", root / "internal" / "tests", *root.glob("packages/*/tests")]
    found = []
    for folder in folders:
        for path in folder.rglob("*.py"):
            name = path.relative_to(root).as_posix()
            if name not in _ALLOWED and _STRICT_XFAIL.search(path.read_text(encoding="utf-8")):
                found.append(name)
    return found


def test_no_test_file_carries_a_strict_xfail_of_its_own() -> None:
    """R272: an xfail has one home, the gap tables the hook reads."""
    assert _strict_xfail_sites(HERE.parents[1]) == []


def test_the_xfail_scan_can_fail(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text(
        '@pytest.mark.xfail(\n    reason=f"{a}", strict=True\n)\ndef test_x(): ...\n',
        encoding="utf-8",
    )
    assert _strict_xfail_sites(tmp_path) == ["tests/test_x.py"]
