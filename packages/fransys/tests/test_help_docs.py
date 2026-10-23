"""The words that say what `write` removes and where `help KEY` is named (AGENT-HELP H3, H4).

The behaviour itself is `test_acceptance.py::test_stale_exports_are_removed_on_the_raise_path`:
an ERROR raises `BuildErrors` and the stale exports of `out_dir` are gone.
"""

import importlib.resources

import fransys as fr


def test_write_says_it_removes_the_exports_an_earlier_write_left():
    assert "earlier" in (fr.write.__doc__ or "")
    assert "writes no export" in (fr.write.__doc__ or "")


def test_the_build_page_says_the_same():
    page = importlib.resources.files("fransys").joinpath("guide", "build.md")
    text = page.read_text(encoding="utf-8")
    assert "removes the exports an earlier `write` left" in text


def test_unit_says_how_a_history_entry_with_no_version_is_numbered():
    assert "A `history=` entry with no `version` is numbered as" in (fr.unit.__doc__ or "")


def test_the_package_docstring_names_the_help_command():
    assert "python -m fransys help" in (fr.__doc__ or "")
