"""LC4's three markdown gates: token ceiling, opening-paragraph shape, long-sentence count.

Covers the fixed "current truth" file set only (LC4: DESIGN.md, `docs/design/*.md`, every md under
`packages/*/docs/`, every CLAUDE.md and README, ROADMAP, GLOSSARY, `docs/contracts/` and the
consumer guide) -- never
`docs/decisions/`, `docs/specs/`, `docs/reviews/` or `docs/archive/` (history, read by id).

Not a package module (loaded by file path, never imported): lives under root `scripts/`, loaded by
its own tests via `importlib.util.spec_from_file_location`, and feeds `lean_ceilings.check`/`lower`/
`first_run` the same way the other LEAN-GATES parts do.
"""

from __future__ import annotations

import dataclasses
import re
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

_PATTERNS: tuple[str, ...] = (
    "docs/DESIGN.md",
    "docs/design/*.md",
    "docs/ROADMAP.md",
    "docs/GLOSSARY.md",
    "docs/contracts/*.md",
    "CLAUDE.md",
    "packages/*/CLAUDE.md",
    "README.md",
    "packages/*/README.md",
    "packages/*/docs/*.md",
    "packages/fransys/src/fransys/guide/*.md",
)

# git's ls-files glob crosses "/" (unlike a shell glob), so "packages/*/README.md" also matches
# the generated packages/electrical-symbols/build/README.md. That file is build output, not
# source truth (LC4 covers current truth only), so it is dropped here by name -- a scoping
# decision the designer should confirm, not a code exemption.
_EXCLUDED_PATHS: frozenset[str] = frozenset({"packages/electrical-symbols/build/README.md"})


def covered_files(root: Path) -> tuple[Path, ...]:
    """LC4's current-truth file set: the union of `_PATTERNS` minus `_EXCLUDED_PATHS`.

    Resolved with `git -C root ls-files`, never a bare recursive glob (this worktree's own
    `.venv/` and `.pytest_cache/` both hold stray README-like files a naive glob would catch). A
    pattern whose directory does not exist yet (`docs/design/*.md` today) simply matches
    nothing; git exits 0 either way.
    """
    matched: set[str] = set()
    for pattern in _PATTERNS:
        result = subprocess.run(  # noqa: S603  git from PATH, fixed args only
            ["git", "-C", str(root), "ls-files", "--", pattern],  # noqa: S607  git from PATH
            check=True,
            capture_output=True,
            text=True,
        )
        matched.update(line for line in result.stdout.splitlines() if line)
    matched -= _EXCLUDED_PATHS
    return tuple(sorted(root / path for path in matched))


def _rel(path: Path, root: Path) -> str:
    """Root-relative posix path, bare (LC1's site-key shape for a per-file site)."""
    return path.resolve().relative_to(root.resolve()).as_posix()


# --- check 1: token ceiling ------------------------------------------------------------------


def measure_md_tokens(files: Iterable[Path], root: Path) -> dict[str, int]:
    """Per-file token count, `len(text) // 4` (LC4's own formula).

    Every file in `files` gets an entry, over the `[limits].md_tokens` ceiling or not -- this is
    a raw measurement, not a `measured`-for-`check` mapping. Filtering to the sites over the
    limit, before calling `lean_ceilings.check`/`lower`, is the caller's job.
    """
    return {_rel(file, root): len(file.read_text(encoding="utf-8")) // 4 for file in files}


# --- check 2: opening-paragraph shape (report-only shape check, no ceiling) -------------------


@dataclasses.dataclass(frozen=True)
class PathViolation:
    """One opening-paragraph shape failure: `path` and a human `reason`."""

    path: str
    reason: str


_OPENING_PARAGRAPH_MIN_LINES = 1
_OPENING_PARAGRAPH_MAX_LINES = 3
_LIST_ITEM_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s")


def _is_structural_line(line: str) -> bool:
    """A heading, list item, table row, image or code-fence line -- never paragraph text."""
    stripped = line.lstrip()
    return (
        stripped.startswith(("#", "```", "!["))
        or _is_table_row(line)
        or _LIST_ITEM_RE.match(line) is not None
    )


def _opening_paragraph_reason(lines: list[str]) -> str | None:
    """`None` when `lines` opens with a title, its blank-line gap, then a 1-3 line paragraph.

    The blank line(s) that ordinarily follow a heading are skipped, not gated -- LC4 gates the
    first content BLOCK after the title, not the gap before it.
    """
    title_index = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if title_index is None:
        return "no title line (`# `) found"
    index = title_index + 1
    while index < len(lines) and lines[index].strip() == "":
        index += 1
    if index >= len(lines) or _is_structural_line(lines[index]):
        return "no plain paragraph as the first block after the title"
    end_index = index
    while (
        end_index < len(lines)
        and lines[end_index].strip() != ""
        and not _is_structural_line(lines[end_index])
    ):
        end_index += 1
    paragraph_lines = end_index - index
    if not _OPENING_PARAGRAPH_MIN_LINES <= paragraph_lines <= _OPENING_PARAGRAPH_MAX_LINES:
        return f"opening paragraph has {paragraph_lines} lines, not 1-3"
    return None


def opening_paragraph_violations(files: Iterable[Path], root: Path) -> tuple[PathViolation, ...]:
    """Every covered file that fails LC4's opening-paragraph shape.

    A shape check only: no ceiling, no baseline ("the gate checks the shape; the reviewer checks
    the content", LC4). Always evaluated in full -- never routed through `lean_ceilings.check`,
    since whether a non-empty result here is wired as hard-fail or report-only is the LEAD's
    call (P5), not this function's.
    """
    violations = [
        PathViolation(path=_rel(file, root), reason=reason)
        for file in files
        for reason in (_opening_paragraph_reason(file.read_text(encoding="utf-8").splitlines()),)
        if reason is not None
    ]
    return tuple(sorted(violations, key=lambda violation: violation.path))


# --- check 3: sentence-length ------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*```")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_TABLE_SEPARATOR_RE = re.compile(r"^[\s|:-]+$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _is_table_separator(line: str) -> bool:
    """A `| --- | --- |`-shaped divider row: only `-`, `:`, `|` and whitespace, one dash."""
    stripped = line.strip()
    return stripped != "" and "-" in stripped and _TABLE_SEPARATOR_RE.match(stripped) is not None


def _is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|") or _is_table_separator(line)


def _measurable_text(text: str) -> str:
    """`text`'s lines with fenced code, headings and table rows dropped, inline code stripped.

    Surviving lines are joined by a single space, which turns LC4's "line's end" sentence
    terminator into an ordinary whitespace one for `_SENTENCE_SPLIT_RE`.
    """
    lines = text.splitlines()
    kept: list[str] = []
    in_fence = False
    for index, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or line.startswith("#"):
            continue
        if _is_table_row(line) or (index > 0 and _is_table_row(lines[index - 1])):
            continue
        kept.append(_INLINE_CODE_RE.sub(" ", line))
    return " ".join(kept)


def _long_sentence_count(text: str, sentence_words: int) -> int:
    measurable = _measurable_text(text)
    sentences = (s.strip() for s in _SENTENCE_SPLIT_RE.split(measurable))
    return sum(1 for sentence in sentences if sentence and len(sentence.split()) > sentence_words)


def measure_long_sentences(
    files: Iterable[Path], root: Path, sentence_words: int
) -> dict[str, int]:
    """Per-file count of sentences over `sentence_words` words (LC4's splitter, verbatim).

    A file with zero over-length sentences is absent from the result -- the same implicit-zero
    convention as `nested_defs`, so the `limit` passed to `lean_ceilings.check`/`lower` for this
    section is `0`.
    """
    counts = {
        _rel(file, root): _long_sentence_count(file.read_text(encoding="utf-8"), sentence_words)
        for file in files
    }
    return {path: count for path, count in counts.items() if count > 0}
