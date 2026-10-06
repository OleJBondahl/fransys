"""`scripts/lean_code_gates.py`: LC2's two ruff/tokenize-measured checks.

Check 1, `measure_ruff_sections`: one real `ruff check` subprocess over every `packages/*/src`
tree, at LC2's own (lower) thresholds for `PLR0915`/`C901`/`PLR0912`, mapped from ruff's own
`def`-line JSON findings to per-function qualnames via `ast`. Returns three `measured` dicts
(`"statements"`, `"complexity"`, `"branches"`) shaped for `lean_ceilings.check`/`lower`/
`first_run`, which `lean_check.py` (a later LEAN-GATES part, not this one) calls directly.

Check 2, `unreasoned_sites`/`report_unreasoned`: every `# noqa`/`# ty: ignore` comment across
`packages/*/src` and `packages/*/tests` with no reason text after its rule-code list, found via
`tokenize` (never `ast`, which drops comments, and never a line regex, which would false-fire on
a `# noqa`-shaped string literal). This check carries no ceiling and no baseline -- it does not
go through `lean_ceilings.check` at all -- but still honors a directory-scope `[exempt]` entry
through `lean_ceilings.is_exempt_under`.

Not a package module (loaded by file path, never imported): lives under root `scripts/`, loaded by
its own tests via `importlib.util.spec_from_file_location`, and imports `scripts/lean_ceilings.py`
the same way (there is no scripts package to import from).
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.util
import json
import re
import subprocess
import sys
import tokenize
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import types
    from collections.abc import Iterable, Mapping

_SCRIPTS_DIR = Path(__file__).resolve().parent
_LEAN_CEILINGS_NAME = "fransys_lean_ceilings"


def _load_lean_ceilings() -> types.ModuleType:
    """Load `scripts/lean_ceilings.py` the way its own tests do, reusing a prior load."""
    if _LEAN_CEILINGS_NAME in sys.modules:
        return sys.modules[_LEAN_CEILINGS_NAME]
    spec = importlib.util.spec_from_file_location(
        _LEAN_CEILINGS_NAME, _SCRIPTS_DIR / "lean_ceilings.py"
    )
    if spec is None or spec.loader is None:
        msg = "could not load scripts/lean_ceilings.py"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_LEAN_CEILINGS_NAME] = module
    spec.loader.exec_module(module)
    return module


lean_ceilings = _load_lean_ceilings()

# --- Check 1: ruff-measured statements/complexity/branches ---------------------------------

#: ruff rule code -> (this check's section name, LC2's own lower threshold for that rule).
RUFF_SECTIONS: dict[str, tuple[str, int]] = {
    "PLR0915": ("statements", 15),
    "C901": ("complexity", 8),
    "PLR0912": ("branches", 12),
}

_MEASURED_RE = re.compile(r"\((\d+)\s*[<>]")


def _qualname_map(path: Path) -> dict[int, str]:
    """Map each function/method/nested-function's own `def`-line `lineno` to its qualname.

    Walks the whole `ast` tree once; `enclosing_scope_names` is the dotted chain of enclosing
    `ClassDef`/`FunctionDef`/`AsyncFunctionDef` names, so a module-level function maps to just
    its own name, a method to `"ClassName.method"`, and a nested function to `"outer.inner"`.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mapping: dict[int, str] = {}

    def visit(node: ast.AST, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                qualname = ".".join([*scope, child.name])
                mapping[child.lineno] = qualname
                visit(child, (*scope, child.name))
            elif isinstance(child, ast.ClassDef):
                visit(child, (*scope, child.name))
            else:
                visit(child, scope)

    visit(tree, ())
    return mapping


def measure_ruff_sections(root: Path) -> dict[str, dict[str, int]]:
    """Run ruff once over every `packages/*/src`; split its findings into the three sections.

    One `uv run ruff check` subprocess (JSON output, `--ignore-noqa` so a real suppression still
    shows up), at `RUFF_SECTIONS`'s own thresholds layered onto the root `pyproject.toml` via
    `--config`, with the root's `per-file-ignores` emptied: they ignore these three rules under
    `packages/*/src/**` (the lean gate owns them), and `--ignore-noqa` does not lift them
    (never a replacement scratch config, which would lose the root's excludes and
    `target-version`). Each returned dict is keyed `"root/relative/path.py::qualname"` and holds
    only sites already over that section's threshold -- ruff itself never reports a within-limit
    site, so this satisfies `lean_ceilings`'s "measured holds only over-limit sites" contract for
    free. A finding whose `location.row` is not a function's own `lineno` (should not happen for
    these three rules, which always point at a `def`) is skipped rather than mis-mapped.
    """
    sections: dict[str, dict[str, int]] = {name: {} for name, _limit in RUFF_SECTIONS.values()}
    src_dirs = sorted(root.glob("packages/*/src"))
    if not src_dirs:
        return sections

    completed = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [  # noqa: S607 -- `uv` resolved from PATH, same as every `just` recipe in this repo
            "uv",
            "run",
            "--project",
            str(_SCRIPTS_DIR.parent),  # the repo's own env, so `root` need not be a uv project
            "ruff",
            "check",
            *(str(path) for path in src_dirs),
            "--select",
            ",".join(RUFF_SECTIONS),
            "--ignore-noqa",
            "--output-format",
            "json",
            "--config",
            f"lint.mccabe.max-complexity={RUFF_SECTIONS['C901'][1]}",
            "--config",
            f"lint.pylint.max-statements={RUFF_SECTIONS['PLR0915'][1]}",
            "--config",
            f"lint.pylint.max-branches={RUFF_SECTIONS['PLR0912'][1]}",
            "--config",
            "lint.per-file-ignores={}",  # the root's ignores of these rules must not hide a site
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in (0, 1):
        msg = (
            f"ruff check exited {completed.returncode} (0=clean, 1=findings expected); "
            f"stderr: {completed.stderr}"
        )
        raise RuntimeError(msg)
    findings = json.loads(completed.stdout or "[]")
    if completed.returncode == 1 and not findings:
        msg = f"ruff check exited 1 with no parsed finding; stderr: {completed.stderr}"
        raise RuntimeError(msg)

    qualname_cache: dict[Path, dict[int, str]] = {}
    for finding in findings:
        code = finding["code"]
        if code not in RUFF_SECTIONS:
            continue
        section, _limit = RUFF_SECTIONS[code]
        file_path = Path(finding["filename"]).resolve()
        if file_path not in qualname_cache:
            # `dict.setdefault(k, _qualname_map(k))` would re-parse the file on every finding --
            # its default argument is evaluated eagerly, cache hit or not.
            qualname_cache[file_path] = _qualname_map(file_path)
        qualnames = qualname_cache[file_path]
        row = finding["location"]["row"]
        qualname = qualnames.get(row)
        measured_match = _MEASURED_RE.search(finding["message"])
        if qualname is None or measured_match is None:
            continue
        rel = file_path.relative_to(root).as_posix()
        sections[section][f"{rel}::{qualname}"] = int(measured_match.group(1))

    return sections


# --- Check 2: the noqa/ty:ignore reason rule ------------------------------------------------

#: A `noqa` comment (bare or `: CODE, CODE`) then optional reason text; capture group is the reason.
_NOQA_RE = re.compile(r"^#\s*noqa(?::\s*[A-Za-z0-9]+(?:\s*,\s*[A-Za-z0-9]+)*)?\s*(.*)$")
#: a ty suppression (bare or bracketed) then optional reason text; capture group is the reason.
_TY_IGNORE_RE = re.compile(r"^#\s*ty:\s*ignore(?:\[[^\]]*\])?\s*(.*)$")


@dataclasses.dataclass(frozen=True)
class UnreasonedSite:
    """One `# noqa`/`# ty: ignore` comment with no reason text after its rule-code list."""

    path: str
    line: int
    text: str


def _reason(comment: str) -> str | None:
    """The trailing reason text of a `# noqa`/`# ty: ignore` comment, or `None` if neither."""
    match = _NOQA_RE.match(comment) or _TY_IGNORE_RE.match(comment)
    return None if match is None else match.group(1).strip()


def unreasoned_sites(paths: Iterable[Path], root: Path) -> tuple[UnreasonedSite, ...]:
    """Every unreasoned `# noqa`/`# ty: ignore` comment under each of `paths`'s `.py` files.

    Uses `tokenize`'s `COMMENT` tokens, never `ast` (drops comments) or a bare line regex (would
    false-fire on `# noqa` text inside a string literal). `paths` are directory roots (this
    check's own callers pass `packages/*/src` and `packages/*/tests`); each is walked recursively.
    """
    sites: list[UnreasonedSite] = []
    for base in paths:
        for candidate in sorted(base.rglob("*.py")):
            with candidate.open("rb") as handle:
                for token in tokenize.tokenize(handle.readline):
                    if token.type != tokenize.COMMENT:
                        continue
                    reason = _reason(token.string)
                    if reason is None or reason:
                        continue
                    rel = candidate.resolve().relative_to(root).as_posix()
                    sites.append(UnreasonedSite(path=rel, line=token.start[0], text=token.string))
    return tuple(sites)


def report_unreasoned(
    sites: tuple[UnreasonedSite, ...], exempt: Mapping[str, str]
) -> tuple[UnreasonedSite, ...]:
    """Drop every `sites` entry under a directory-scope `[exempt]` entry.

    Matches via `lean_ceilings.is_exempt_under` (subtree scope), never plain `site in exempt`
    (exact match) -- this check's exemptions are whole directories, not single sites.
    """
    return tuple(site for site in sites if not lean_ceilings.is_exempt_under(site.path, exempt))
