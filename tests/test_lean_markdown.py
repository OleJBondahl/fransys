"""`scripts/lean_markdown.py`: the token, opening-paragraph and sentence-length gates.

Loaded like `test_lean_ceilings.py` loads `scripts/lean_ceilings.py` (`importlib.util.spec_from_
file_location`), since the script is not a package module. Every case builds its own tmp_path
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from gate_scan import load_script

ROOT = Path(__file__).resolve().parents[1]


lean_markdown = load_script("fransys_lean_markdown", "lean_markdown.py")
lean_ceilings = load_script("fransys_lean_ceilings", "lean_ceilings.py")


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # noqa: S603, S607  git from PATH
    subprocess.run(  # noqa: S603 -- git from PATH
        ["git", "-C", str(root), "add", "-A"],  # noqa: S607  git from PATH
        check=True,
    )


# --- file enumeration: never a bare recursive glob --------------------------------------------


def test_covered_files_enumeration_matches_anchors_and_excludes_history(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "DESIGN.md").write_text("# Design\n\nBody.\n", encoding="utf-8")
    (tmp_path / "docs" / "decisions").mkdir()
    (tmp_path / "docs" / "decisions" / "0001-x.md").write_text("# 0001\n\nBody.\n", encoding="utf-8")
    (tmp_path / "packages" / "fake").mkdir(parents=True)
    (tmp_path / "packages" / "fake" / "CLAUDE.md").write_text("# Fake\n\nBody.\n", encoding="utf-8")
    # A file a bare recursive "**/*.md" glob would catch, but none of our anchor patterns would.
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "random.md").write_text("# Random\n\nBody.\n", encoding="utf-8")

    _init_git_repo(tmp_path)

    covered = lean_markdown.covered_files(tmp_path)

    assert (tmp_path / "docs" / "DESIGN.md") in covered
    assert (tmp_path / "packages" / "fake" / "CLAUDE.md") in covered
    assert (tmp_path / "docs" / "decisions" / "0001-x.md") not in covered
    assert (tmp_path / "notes" / "random.md") not in covered


# --- check 1: token ceiling ---------------------------------------------------------------------


def test_md_tokens_over_limit_fails_the_gate(tmp_path: Path):
    """A covered file over 5k tokens fails `lean_ceilings.check` at the token limit."""
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text("# Design\n\n" + "word " * 6000, encoding="utf-8")

    limit = 5000
    raw = lean_markdown.measure_md_tokens([covered], tmp_path)
    measured = {site: count for site, count in raw.items() if count > limit}
    violations = lean_ceilings.check(measured, ceilings={}, limit=limit)

    assert violations != ()
    assert violations[0].site == "docs/DESIGN.md"


# --- check 2: opening-paragraph shape ------------------------------------------------------------


@pytest.mark.parametrize(
    "text", ["# Design\n\n## Subheading\n", "# Design\n\nOne.\nTwo.\nThree.\nFour.\n\n## Next\n"], ids=["no-paragraph", "over-three-lines"]
)
def test_opening_paragraph_shape_fails(tmp_path: Path, text: str):
    """No paragraph before a subheading, or a 4-line opening paragraph, fails the shape check."""
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text(text, encoding="utf-8")

    violations = lean_markdown.opening_paragraph_violations([covered], tmp_path)

    assert violations != ()
    assert violations[0].path == "docs/DESIGN.md"


def test_opening_paragraph_shape_passes_with_normal_blank_line_after_title(tmp_path: Path):
    """A normal file -- title, the usual blank line, then a 1-3 line paragraph -- passes.

    This is the regression case: the earlier (wrong) rule required no blank line after the
    title and wrongly failed every real file in the repo, which all use this normal shape.
    """
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text("# Design\n\nBody text right here.\n\n## Next\n", encoding="utf-8")

    violations = lean_markdown.opening_paragraph_violations([covered], tmp_path)

    assert violations == ()


# --- check 3: sentence-length --------------------------------------------------------------------


def _thirty_one_words() -> str:
    return " ".join(["word"] * 31) + "."


def test_long_sentence_over_30_words_fails_when_ceiling_is_zero(tmp_path: Path):
    """A 31-word sentence fails `check` when the file's own ceiling entry is 0."""
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text(f"# Design\n{_thirty_one_words()}\n", encoding="utf-8")

    measured = lean_markdown.measure_long_sentences([covered], tmp_path, sentence_words=30)
    violations = lean_ceilings.check(measured, ceilings={"docs/DESIGN.md": 0}, limit=0)

    assert violations != ()
    assert violations[0].site == "docs/DESIGN.md"


_WORDS31 = " ".join(["word"] * 31)


@pytest.mark.parametrize(
    "text",
    [
        "# Design\nA short sentence. Another short one.\n",
        f"# Design\nIntro.\n\n```\n{_thirty_one_words()}\n```\n\nOutro.\n",
        f"# Design\n| Col |\n|---|\n| {_thirty_one_words()} |\n",
        f"# Design\nSee `{_WORDS31}.` here.\n",
        f"# {' '.join(['word'] * 35)}.\nA short body sentence.\n",
    ],
    ids=["short-control", "fenced-code", "table-cell", "inline-code", "heading"],
)
def test_no_long_sentence_entry_for_short_or_excluded_text(tmp_path: Path, text: str):
    """No sentence over 30 words, or the long one sits in fenced code, a table cell, inline code or a heading: absent from `measured`."""
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text(text, encoding="utf-8")

    measured = lean_markdown.measure_long_sentences([covered], tmp_path, sentence_words=30)

    assert measured == {}


def test_covered_files_includes_package_docs_two_folders_deep(tmp_path: Path):
    """`packages/*/docs/*.md` crosses "/": a docs/rules/x.md path is in the set."""
    deep = tmp_path / "packages" / "fake" / "docs" / "rules" / "x.md"
    deep.parent.mkdir(parents=True)
    deep.write_text("# X\n\nBody.\n", encoding="utf-8")
    _init_git_repo(tmp_path)

    assert deep in lean_markdown.covered_files(tmp_path)
