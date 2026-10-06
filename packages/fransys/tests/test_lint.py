"""G5 (decision 0029): `fr.lint(*libraries)` lints installed part libraries by import name."""

from importlib.resources import as_file, files

import fransys as fr
import fransys_parts


def _root_lint(package: str):
    with as_file(files(package)) as root:
        return fransys_parts.lint(root)


def test_lint_of_demo_parts_is_the_parts_lint_of_its_root() -> None:
    assert fr.lint("demo_parts") == _root_lint("demo_parts")


def test_lint_of_no_library_is_empty() -> None:
    assert fr.lint() == ()


def test_lint_reports_a_library_with_a_defect(tmp_path, monkeypatch) -> None:
    """A package with no `library.toml` gives `LIBRARY_FILE_MISSING`, the same as the root lint."""
    package = tmp_path / "broken_parts"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    findings = fr.lint("broken_parts")

    assert [f.code for f in findings] == ["LIBRARY_FILE_MISSING"]
    assert findings == fransys_parts.lint(package)


def test_lint_of_two_libraries_lists_the_first_then_the_second(tmp_path, monkeypatch) -> None:
    package = tmp_path / "broken_parts"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    findings = fr.lint("demo_parts", "broken_parts")

    assert findings == (*_root_lint("demo_parts"), *fransys_parts.lint(package))
    assert "LIBRARY_FILE_MISSING" in [f.code for f in findings]
