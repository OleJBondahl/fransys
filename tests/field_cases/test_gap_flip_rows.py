"""Every strict xfail of the field cases names a `GAP-FLIP-<n>` row (FLIP-NOW Acceptance 3)."""

import re
import tomllib
from pathlib import Path
from typing import Any, cast

from _gap_flip import EXCEPTIONS, GAP_PREFIX, field_raises, gaps, mark_gaps, other_gaps
lazy import pytest

ROW = re.compile(r"GAP-(?:FLIP-(?:\d+|DRAWING-SUBJECT)|OTHER-(?:CYCLE|SALT-GROUP|SALT-FAN))")
HERE = Path(__file__).parent


def test_every_gap_entry_names_a_row_of_the_gap_shape() -> None:
    bad = {t: g for t, g in gaps().items() if not ROW.fullmatch(g)}
    assert bad == {}


def undefined_tests(table: dict[str, str], root: Path) -> list[str]:
    """The keys whose file lacks a `def` of the named test: such a row marks nothing (KI-035)."""
    out = []
    for key in table:
        path, _, name = key.partition("::")
        file = root / path
        if not file.is_file() or f"def {name.partition('[')[0]}(" not in file.read_text("utf-8"):
            out.append(key)
    return out


def test_every_gap_entry_names_a_test_that_exists() -> None:
    assert undefined_tests(gaps(), HERE) == []


def test_a_gap_key_naming_no_defined_test_is_found(tmp_path: Path) -> None:
    (tmp_path / "test_a.py").write_text("def test_x(): ...\n", encoding="utf-8")
    table = {"test_a.py::test_x[1]": "GAP-FLIP-1", "test_a.py::test_y": "GAP-FLIP-1"}
    assert undefined_tests(table, tmp_path) == ["test_a.py::test_y"]


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
    mark_gaps(cast("Any", [hit, other]))  # stand-in items
    (mark,) = hit.marks
    assert mark.kwargs["strict"] is True
    assert ROW.search(mark.kwargs["reason"])
    assert other.marks == []


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


def test_every_field_case_xfail_names_the_exception_it_raises() -> None:
    """R1342: a bare xfail counts an escaping TypeError as xfailed, so each listed case names `raises=`."""
    items = [_Item(GAP_PREFIX + test_id) for test_id in gaps()]
    mark_gaps(cast("Any", items))
    assert [i.nodeid for i in items if i.marks[0].kwargs.get("raises") is None] == []
    assert field_raises(next(iter(gaps()))) is AssertionError


def test_every_raises_entry_names_a_listed_case_and_a_known_exception() -> None:
    table = tomllib.loads((HERE / "gap_flip.toml").read_text(encoding="utf-8")).get("raises", {})
    assert {t: e for t, e in table.items() if t not in gaps() or e not in EXCEPTIONS} == {}
