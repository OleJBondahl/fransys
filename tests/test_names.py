"""Names gates: the old name stays out of the tree; the library's project-word count only falls.

Any tracked file outside the skip list that holds the word, in any case, fails. The public
electrical-symbols library's count of the project word is a ratchet (`[public_lib_names]`). The
allowances are the moving page that names the old spellings, the two seed strings that keep model
ids and KiCad tstamps stable, the consumer-guide quote (an owner's words), and the two gitleaks
history fingerprints, which name a file by its path in that commit.
"""

from pathlib import Path

import pytest
from gate_scan import ROOT, check_stock, stock

OLD = "schematika"
PUBLIC_LIB = "packages/electrical-symbols"
PROJECT_WORD = "fransys"
SKIP_PREFIXES = (
    "docs/decisions/",
    "docs/archive/",
    "docs/reviews/",
    "docs/plans/",
    "examples/pump-station/",
    "docs/archive/specs/2026-10-05-fransys-rename.md",
    "packages/fransys/src/fransys/guide/moving-to-fransys.md",
    "tests/test_names.py",
)
IGNORED_DIRS = {
    ".git",
    ".claude",
    ".venv",
    ".fransys",
    ".superpowers",
    "claude-tools",
    "htmlcov",
    "dist",
    "secret_external",
    "__pycache__",
    ".hypothesis",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
}
ALLOWED_LINES = {
    ("packages/fransys-kernel/src/fransys_kernel/ids.py", '"schematika-model:id"'),
    ("packages/fransys-kicad/src/fransys_kicad/netlist.py", '"schematika_kicad"'),
    (
        "docs/archive/specs/2026-09-26-consumer-guide.md",
        "external consumers of schematika, so when",
    ),
    (
        "security-allowlist.toml",
        ":packages/schematika-model/tests/kernel/test_record.py:generic-api-key:",
    ),
}


def hits(files: dict[str, str]) -> list[str]:
    found = []
    for rel, text in files.items():
        if rel.startswith(SKIP_PREFIXES) or Path(rel).name == "CLAUDE.md":
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if OLD in line.lower() and not any(
                rel == r and frag in line for r, frag in ALLOWED_LINES
            ):
                found.append(f"{rel}:{n}: {line.strip()[:80]}")
    return found


def tracked_texts() -> dict[str, str]:
    """Walk the tree, not `git ls-files`: a `just probe` copy sits untracked inside a worktree."""
    texts = {}
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT).as_posix()
        if not path.is_file() or set(rel.split("/")) & IGNORED_DIRS:
            continue
        try:
            texts[rel] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if OLD in rel.lower():
            texts[rel] += f"\n{OLD} in the path"
    return texts


def test_no_old_name_outside_the_allowed_places():
    texts = tracked_texts()
    assert "packages/fransys/pyproject.toml" in texts
    assert hits(texts) == []


def test_the_gate_fails_on_a_planted_import():
    planted = {"packages/fransys/src/fransys/x.py": "import schematika as sk\n"}
    assert hits(planted) == ["packages/fransys/src/fransys/x.py:1: import schematika as sk"]


def count_in(text: str) -> int:
    """Case-insensitive occurrences of the project word; a line with two counts two."""
    return text.lower().count(PROJECT_WORD)


def public_lib_files(root: Path = ROOT) -> list[Path]:
    """The library's docs, README, library.toml and source files; generated files skipped."""
    base = root / PUBLIC_LIB
    found = [
        base / "README.md",
        base / "library.toml",
        *base.glob("build/README.md"),
        *base.glob("docs/**/*.md"),
        *base.glob("src/**/*.py"),
    ]
    return sorted(path for path in found if path.is_file() and path.name != "_version.py")


def public_lib_name_count(files: list[Path]) -> int:
    """The project word's count over the given files."""
    return sum(count_in(path.read_text(encoding="utf-8")) for path in files)


@pytest.mark.private_input  # a private-gate count (R462)
def test_public_lib_names_stock():
    found = public_lib_name_count(public_lib_files())
    check_stock("public_lib_names", found, stock("public_lib_names"))


def test_synthetic_count_in_counts_each_case_and_each_occurrence():
    assert count_in("Fransys and fransys\nFRANSYS") == 3
    assert count_in("nothing here") == 0


def test_synthetic_walk_counts_a_planted_readme(tmp_path):
    readme = tmp_path / PUBLIC_LIB / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("Fransys\n", encoding="utf-8")
    assert public_lib_name_count(public_lib_files(tmp_path)) == 1
