"""Names gate (FRANSYS FR1, FR2, FR4): the old project name appears only in the allowed places.

Any tracked file outside the skip list that holds the word, in any case, fails. The allowances are
the moving page that names the old spellings, the two seed strings that keep model ids and KiCad
tstamps stable (FR2), the consumer-guide quote (an owner's words), and the two gitleaks history
fingerprints, which name a file by its path in that commit.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = "schematika"
SKIP_PREFIXES = (
    "docs/decisions/",
    "docs/archive/",
    "docs/reviews/",
    "docs/plans/",
    "examples/pump-station/",
    "docs/specs/2026-10-05-fransys-rename.md",
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
    ("packages/fransys-model/src/fransys_model/kernel/ids.py", '"schematika-model:id"'),
    ("packages/fransys-kicad/src/fransys_kicad/netlist.py", '"schematika_kicad"'),
    ("docs/specs/2026-09-26-consumer-guide.md", "external consumers of schematika, so when"),
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
