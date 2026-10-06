"""`scripts/lean_markdown.py`: LC4's token, opening-paragraph and sentence-length gates.

Loaded like `test_lean_ceilings.py` loads `scripts/lean_ceilings.py` (`importlib.util.spec_from_
file_location`), since the script is not a package module. Every case builds its own tmp_path
tree; no real repo file is read here.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    if spec is None or spec.loader is None:
        msg = f"could not load {relpath}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lean_markdown = _load("fransys_lean_markdown", "scripts/lean_markdown.py")
lean_ceilings = _load("fransys_lean_ceilings", "scripts/lean_ceilings.py")


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
    (tmp_path / "docs" / "decisions" / "0001-x.md").write_text(
        "# 0001\n\nBody.\n", encoding="utf-8"
    )
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
    """A covered file over 5k tokens fails `lean_ceilings.check` at the LC4 limit."""
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


def test_opening_paragraph_no_paragraph_before_subheading_fails(tmp_path: Path):
    """A title followed by its blank gap then straight into a subheading, no paragraph, fails."""
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text("# Design\n\n## Subheading\n", encoding="utf-8")

    violations = lean_markdown.opening_paragraph_violations([covered], tmp_path)

    assert violations != ()
    assert violations[0].path == "docs/DESIGN.md"


def test_opening_paragraph_over_three_lines_fails(tmp_path: Path):
    """A 4-line opening paragraph fails the shape check."""
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text("# Design\n\nOne.\nTwo.\nThree.\nFour.\n\n## Next\n", encoding="utf-8")

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


def test_short_sentences_produce_no_long_sentence_entry(tmp_path: Path):
    """A control case: no sentence over 30 words, so the file is absent from `measured`."""
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text("# Design\nA short sentence. Another short one.\n", encoding="utf-8")

    measured = lean_markdown.measure_long_sentences([covered], tmp_path, sentence_words=30)

    assert measured == {}


def test_long_sentence_inside_fenced_code_block_not_counted(tmp_path: Path):
    text = f"# Design\nIntro.\n\n```\n{_thirty_one_words()}\n```\n\nOutro.\n"
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text(text, encoding="utf-8")

    measured = lean_markdown.measure_long_sentences([covered], tmp_path, sentence_words=30)

    assert measured == {}


def test_long_sentence_inside_table_cell_not_counted(tmp_path: Path):
    text = f"# Design\n| Col |\n|---|\n| {_thirty_one_words()} |\n"
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text(text, encoding="utf-8")

    measured = lean_markdown.measure_long_sentences([covered], tmp_path, sentence_words=30)

    assert measured == {}


def test_long_sentence_inside_inline_code_not_counted(tmp_path: Path):
    words = " ".join(["word"] * 31)
    text = f"# Design\nSee `{words}.` here.\n"
    covered = tmp_path / "docs" / "DESIGN.md"
    covered.parent.mkdir(parents=True)
    covered.write_text(text, encoding="utf-8")

    measured = lean_markdown.measure_long_sentences([covered], tmp_path, sentence_words=30)

    assert measured == {}


def test_heading_line_never_measured_as_sentence(tmp_path: Path):
    heading_words = " ".join(["word"] * 35)
    text = f"# {heading_words}.\nA short body sentence.\n"
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
