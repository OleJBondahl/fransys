"""LEAN-GATES' one entry point: `report`, `hard`, `enforce`, `lower`, `first-run`.

Wires every other LEAN-GATES checker to `ceilings.toml` (`lean_ceilings.py`). One measurement
pass resolves the API surface once (`lean_surface.resolve_surface_names`) and shares it across
every surface-scoped check; every other checker is called exactly once too.

- `report`: prints every ceilings-bound finding plus the two informational-only checks
  (opening-paragraph shape, record-field types), grouped by section. Always exits 0.
- `hard`: the two zero-baseline checks -- unreasoned `noqa`/`ty: ignore` sites and API-surface
  docstring presence (`missing` or an unplaceable `no def node found`). Non-zero exit on any
  finding.
- `enforce`: the flip's numeric half. One line per numeric violation (a site over its limit with
  no `ceilings.toml` key, or measured past its listed ceiling); non-zero exit on any. `hard`
  stays the zero-baseline check; `lower` still calls only `hard`.
- `lower`: runs `hard` first (never lowers a baseline `hard` itself would reject), then shrinks
  every numeric ceiling to its fresh measurement (`lean_ceilings.lower`), writing only on a
  real change. Never touches `[limits]`/`[exempt]`.
- `first-run`: LC6 step 3's baseline writer. A merge onto any existing `ceilings.toml` (never a
  rewrite): `[limits]`/`[exempt]` untouched, each numeric section replaced wholesale by
  `lean_ceilings.first_run`. Used now (this order's own provisional baseline) and once more at
  the flip; never called by `lower`.

A checker that raises aborts the run before any write: `first-run`/`lower` never partially write
a baseline built from a garbage measurement.

Not a package module (loaded by file path, never imported): lives under root `scripts/`, run via
`uv run python scripts/lean_check.py {report,hard,enforce,lower,first-run}`.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import importlib.util
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types

ROOT = Path(__file__).resolve().parents[1]
CEILINGS_PATH = ROOT / "ceilings.toml"
_SCRIPTS_DIR = Path(__file__).resolve().parent

_HEADER = (
    "# The lean gates' ceilings (decision 0087). `just ceil-lower` rewrites this file,\n"
    "# so every comment here comes from scripts/lean_ceilings.py and scripts/lean_check.py.\n\n"
)

#: LC1's own worked example, hand-authored (Part A): the starting `[limits]`, this order's only.
STARTING_LIMITS: dict[str, int] = {
    "statements": 15,
    "complexity": 8,
    "branches": 12,
    "module_code_lines": 300,
    "docstring_lines": 5,
    "surface_docstring_lines": 15,
    "md_tokens": 5000,
    "sentence_words": 30,
}

#: Hand-authored (Part A), designer-ruled reasons verbatim; do not improvise different text.
STARTING_EXEMPT: dict[str, str] = {
    "packages/fransys-overview/src/fransys_overview/_vendor_cytoscape.py": (
        "generated (overview-0001)"
    ),
    "packages/fransys-layout/src/fransys_layout/stages/types.py": ("D8 exemption, unchanged (LC2)"),
    "packages/fransys-layout/src/fransys_layout/geometry/text_metrics.py": (
        "D8 exemption, unchanged (LC2)"
    ),
}


def _load(name: str, filename: str) -> types.ModuleType:
    """Load `scripts/<filename>` under `name`, the way every other LEAN-GATES script does.

    `sys.modules`-cached by `name`: loading `lean_ceilings`/`lean_surface` here FIRST, under the
    exact names their own consumers use internally, means those consumers (loaded next) hit this
    same cached module instead of a second copy -- one `resolve_surface_names()` import cost,
    not several.
    """
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    if spec is None or spec.loader is None:
        msg = f"could not load scripts/{filename}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lean_ceilings = _load("fransys_lean_ceilings", "lean_ceilings.py")
lean_surface = _load("fransys_lean_surface", "lean_surface.py")
lean_code_gates = _load("fransys_lean_code_gates", "lean_code_gates.py")
lean_code_shape = _load("fransys_lean_code_shape", "lean_code_shape.py")
lean_docstrings = _load("fransys_lean_docstrings", "lean_docstrings.py")
lean_markdown = _load("fransys_lean_markdown", "lean_markdown.py")
lean_surface_types = _load("fransys_lean_surface_types", "lean_surface_types.py")

#: Every ceilings-bound section's own measurer, called with `(root, limits, entries)`.
_NUMERIC_SECTIONS = (
    "statements",
    "complexity",
    "branches",
    "nested_defs",
    "module_code_lines",
    "docstring_lines",
    "surface_docstring_lines",
    "surface_types",
    "md_tokens",
    "md_long_sentences",
)


@dataclasses.dataclass(frozen=True)
class Measurement:
    """One `report`/`lower` measurement pass: every ceilings-bound section, plus two counts.

    The zero-baseline `hard` checks (unreasoned sites, surface docstring presence, banned
    sections) are NOT here -- `cmd_hard` measures those itself, separately, since `report` and
    `lower` never need them (LC6.2's own report/hard split).

    `sections` holds `_NUMERIC_SECTIONS`' own `measured` dicts (over-limit sites only, the shared
    `lean_ceilings` contract). `opening_paragraph`/`record_field_count` are informational only,
    no ceiling. The three counters feed `report`'s own speed instrumentation: `files_walked` is
    every `packages/*/src` file plus every covered markdown file; `functions_measured` is every
    over-limit ruff/nested-def site plus every resolved surface name; `docstrings_measured` is
    every surface site checked for its docstring length plus every non-surface docstring found
    over the line cap.
    """

    sections: dict[str, dict[str, int]]
    opening_paragraph: tuple[Any, ...]
    record_field_count: int
    files_walked: int
    functions_measured: int
    docstrings_measured: int


def _assert_limits_match_checkers(limits: dict[str, int]) -> None:
    """LC1's "one home": fail loudly on drift between `ceilings.toml` and a checker's constant.

    `RUFF_SECTIONS`'s three thresholds and `DEFAULT_DOCSTRING_LINES_LIMIT` are still hardcoded
    inside their own checkers, with no `limit=` parameter to route `[limits]` through (open item,
    decision 0044) -- this assert is the stopgap until one of them changes.
    """
    checks = (
        ("statements", lean_code_gates.RUFF_SECTIONS["PLR0915"][1]),
        ("complexity", lean_code_gates.RUFF_SECTIONS["C901"][1]),
        ("branches", lean_code_gates.RUFF_SECTIONS["PLR0912"][1]),
        ("docstring_lines", lean_docstrings.DEFAULT_DOCSTRING_LINES_LIMIT),
    )
    for name, checker_default in checks:
        if limits[name] != checker_default:
            msg = (
                f"ceilings.toml [limits].{name}={limits[name]} disagrees with the checker's own "
                f"default {checker_default} -- update both together (LC1, decision 0044)"
            )
            raise ValueError(msg)


def measure_all(root: Path, limits: dict[str, int]) -> Measurement:
    """One real run of every checker, `resolve_surface_names` shared, `limits` from `ceilings.toml`.

    Cheap AST-only checks (`nested_defs`, `module_code_lines`) run first, so a raise anywhere
    downstream (the ruff subprocess, the surface resolve, the markdown git scan) never wastes
    the earlier work -- and, symmetrically, a raise here surfaces before any of the slower steps.
    """
    _assert_limits_match_checkers(limits)

    nested_defs = lean_code_shape.measure_nested_defs(root)
    module_code_lines = lean_code_shape.measure_module_code_lines(
        root, limit=limits["module_code_lines"]
    )

    ruff_sections = lean_code_gates.measure_ruff_sections(root)

    entries = lean_surface.resolve_surface_names()
    surface_keys = lean_docstrings.surface_site_keys(entries=entries, root=root)
    surface_lengths = lean_docstrings.measure_surface_docstring_lines(
        limit=limits["surface_docstring_lines"], entries=entries, root=root
    )
    docstring_lines = lean_docstrings.measure_docstring_lines(root, surface_keys)

    surface_types = lean_surface_types.measure_surface_types(entries=entries)
    record_fields = lean_surface_types.measure_record_field_types(entries=entries)

    md_files = lean_markdown.covered_files(root)
    md_tokens_all = lean_markdown.measure_md_tokens(md_files, root)
    md_tokens = {path: n for path, n in md_tokens_all.items() if n > limits["md_tokens"]}
    opening_paragraph = lean_markdown.opening_paragraph_violations(md_files, root)
    md_long_sentences = lean_markdown.measure_long_sentences(
        md_files, root, limits["sentence_words"]
    )

    sections = {
        "statements": ruff_sections["statements"],
        "complexity": ruff_sections["complexity"],
        "branches": ruff_sections["branches"],
        "nested_defs": nested_defs,
        "module_code_lines": module_code_lines,
        "docstring_lines": docstring_lines,
        "surface_docstring_lines": surface_lengths,
        "surface_types": surface_types,
        "md_tokens": md_tokens,
        "md_long_sentences": md_long_sentences,
    }

    docstrings_measured = len(surface_keys) + len(docstring_lines)
    files_walked = len(lean_code_shape.package_src_files(root)) + len(md_files)
    functions_measured = (
        sum(len(ruff_sections[name]) for name in ("statements", "complexity", "branches"))
        + len(nested_defs)
        + len(entries)
    )

    return Measurement(
        sections=sections,
        opening_paragraph=opening_paragraph,
        record_field_count=len(record_fields),
        files_walked=files_walked,
        functions_measured=functions_measured,
        docstrings_measured=docstrings_measured,
    )


def build_ceilings(
    existing: lean_ceilings.CeilingsFile | None, measured: dict[str, dict[str, int]]
) -> lean_ceilings.CeilingsFile:
    """Merge fresh `measured` sections onto `existing`, never a from-scratch rewrite.

    A fresh limits/exempt-only file when `existing` is `None`; either way, `limits` and `exempt`
    are NEVER touched here (hand-authored, kept as-is) -- each numeric section in `measured` is
    replaced wholesale by `lean_ceilings.first_run(measured[name], exempt=existing.exempt)`.
    """
    if existing is None:
        limits = dict(STARTING_LIMITS)
        exempt = dict(STARTING_EXEMPT)
    else:
        limits = dict(existing.limits)
        exempt = dict(existing.exempt)
    sections = {name: lean_ceilings.first_run(measured[name], exempt=exempt) for name in measured}
    return lean_ceilings.CeilingsFile(limits=limits, sections=sections, exempt=exempt)


def _write_ceilings(path: Path, file: lean_ceilings.CeilingsFile) -> None:
    """Write `file` to `path` with `_HEADER` prepended, LF line endings, one call, every writer."""
    path.write_text(_HEADER + lean_ceilings.render_ceilings(file), encoding="utf-8", newline="\n")


def numeric_violations(
    sections: dict[str, dict[str, int]], ceilings: lean_ceilings.CeilingsFile
) -> list[tuple[str, lean_ceilings.Violation]]:
    """Every ceilings-bound violation as `(section, violation)`, in `SECTION_ORDER`."""
    found: list[tuple[str, lean_ceilings.Violation]] = []
    for name in lean_ceilings.SECTION_ORDER:
        violations = lean_ceilings.check(
            sections.get(name, {}),
            ceilings.sections.get(name, {}),
            ceilings.limits.get(name, 0),
            exempt=ceilings.exempt,
        )
        found.extend((name, v) for v in violations)
    return found


def _report_lines(measurement: Measurement, ceilings: lean_ceilings.CeilingsFile) -> list[str]:
    """`report` mode's own printed lines.

    Every ceilings-bound finding, then the two informational-only counts, grouped and labeled.
    """
    lines: list[str] = []
    current = None
    for name, v in numeric_violations(measurement.sections, ceilings):
        if name != current:
            lines.append(f"[{name}]")
            current = name
        lines.append(
            f"  {v.site}: {v.measured} > {v.limit} ({'listed' if v.listed else 'unlisted'})"
        )
    lines.append(
        "[opening_paragraph] not ceiling-bound, informational: "
        f"{len(measurement.opening_paragraph)} file(s) fail the shape check"
    )
    lines.extend(f"  {v.path}: {v.reason}" for v in measurement.opening_paragraph)
    lines.append(
        "[record_field_types] not ceiling-bound, informational: "
        f"{measurement.record_field_count} offending @value/@record class(es)"
    )
    return lines


def cmd_report(root: Path, ceilings_path: Path) -> int:
    """`report`: print every finding, always exit 0."""
    wall_start = time.perf_counter()
    cpu_start = time.process_time()

    ceilings = lean_ceilings.load_ceilings(ceilings_path)
    measurement = measure_all(root, ceilings.limits)

    cpu_elapsed = time.process_time() - cpu_start
    wall_elapsed = time.perf_counter() - wall_start

    for line in _report_lines(measurement, ceilings):
        print(line)  # noqa: T201 -- this script's whole job is CLI output
    print(  # noqa: T201 -- this script's whole job is CLI output
        f"files walked: {measurement.files_walked}, functions/classes measured: "
        f"{measurement.functions_measured}, docstrings measured: {measurement.docstrings_measured}"
    )
    print(f"cpu time (process_time, this process only): {cpu_elapsed:.2f}s")  # noqa: T201 -- this script's whole job is CLI output
    print(  # noqa: T201 -- this script's whole job is CLI output
        "wall time (includes the ruff subprocess), not the acceptance evidence: "
        f"{wall_elapsed:.2f}s"
    )
    return 0


def cmd_hard(root: Path, ceilings_path: Path) -> int:
    """`hard`: the two zero-baseline checks. Non-zero exit on any finding."""
    ceilings = lean_ceilings.load_ceilings(ceilings_path)
    unreasoned = lean_code_gates.unreasoned_sites(
        [*root.glob("packages/*/src"), *root.glob("packages/*/tests")], root
    )
    unreasoned = lean_code_gates.report_unreasoned(unreasoned, ceilings.exempt)
    surface_violations = lean_docstrings.check_surface_docstrings(
        limit=ceilings.limits["surface_docstring_lines"], root=root
    )
    surface_hard = tuple(
        v for v in surface_violations if v.reason in ("missing", "no def node found")
    )
    surface_keys = lean_docstrings.surface_site_keys(root=root)
    banned = lean_docstrings.banned_section_sites(root, surface_keys)

    findings = False
    for site in unreasoned:
        print(f"unreasoned: {site.path}:{site.line}: {site.text}")  # noqa: T201 -- this script's whole job is CLI output
        findings = True
    for violation in surface_hard:
        print(f"surface docstring: {violation.site}: {violation.reason}")  # noqa: T201 -- this script's whole job is CLI output
        findings = True
    for site in banned:
        print(f"banned docstring section: {site}")  # noqa: T201 -- this script's whole job is CLI output
        findings = True
    return 1 if findings else 0


def cmd_enforce(root: Path, ceilings_path: Path) -> int:
    """`enforce`: one line per numeric violation (new, or grown past its ceiling); exit 1 on any."""
    ceilings = lean_ceilings.load_ceilings(ceilings_path)
    measurement = measure_all(root, ceilings.limits)
    violations = numeric_violations(measurement.sections, ceilings)
    for name, v in violations:
        kind = "ceiling" if v.listed else "limit"
        why = "listed, grown past its ceiling" if v.listed else "unlisted, no ceilings.toml key"
        print(f"enforce: [{name}] {v.site}: measured {v.measured} > {kind} {v.limit} ({why})")  # noqa: T201 -- this script's whole job is CLI output
    return 1 if violations else 0


def _child_defs(node: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef]:
    """Every def/class directly under `node`, looking through `if`/`try` blocks, not into defs."""
    found: list[ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.append(child)
        else:
            found.extend(_child_defs(child))
    return found


def site_exists(root: Path, site: str) -> bool:
    """Whether `site` still exists: a bare path is a file, `path::qualname` a def chain in it."""
    path, _, qualname = site.partition("::")
    file = root / path
    if not file.is_file():
        return False
    if not qualname:
        return True
    node: ast.AST = ast.parse(file.read_text(encoding="utf-8"))
    for part in qualname.split("."):
        matches = [d for d in _child_defs(node) if d.name == part]
        if not matches:
            return False
        node = matches[0]
    return True


def deleted_site_note(root: Path, site: str, measured_section: dict[str, int]) -> str:
    """The `lower` suffix for a deleted key: `(within limit)`, or `(gone)` plus a same-name move."""
    if site_exists(root, site):
        return "(within limit)"
    qualname = site.partition("::")[2]
    if not qualname:
        return "(gone)"
    paths = sorted(
        {other.partition("::")[0] for other in measured_section if other.endswith(f"::{qualname}")}
        - {site.partition("::")[0]}
    )
    if not paths:
        return "(gone)"
    return f"(gone) -- same name now over its limit at {', '.join(paths)}"


def cmd_lower(root: Path, ceilings_path: Path) -> int:
    """`lower`: run `hard` first (never lower a baseline `hard` would reject); then shrink."""
    hard_status = cmd_hard(root, ceilings_path)
    if hard_status != 0:
        return hard_status

    ceilings = lean_ceilings.load_ceilings(ceilings_path)
    measurement = measure_all(root, ceilings.limits)

    changed = False
    new_sections = dict(ceilings.sections)
    for name in _NUMERIC_SECTIONS:
        lowered = lean_ceilings.lower(
            measurement.sections.get(name, {}), ceilings.sections.get(name, {}), ceilings.exempt
        )
        if lowered != ceilings.sections.get(name, {}):
            changed = True
        new_sections[name] = lowered

    if not changed:
        print("no ceiling lowered")  # noqa: T201 -- this script's whole job is CLI output
        return 0

    new_file = dataclasses.replace(ceilings, sections=new_sections)
    _write_ceilings(ceilings_path, new_file)
    for name in _NUMERIC_SECTIONS:
        before, after = ceilings.sections.get(name, {}), new_sections[name]
        for site in sorted(set(before) - set(after)):
            note = deleted_site_note(root, site, measurement.sections.get(name, {}))
            print(f"lowered [{name}]: {site} deleted {note}")  # noqa: T201 -- this script's whole job is CLI output
        for site in sorted(after):
            if before.get(site) != after[site]:
                print(f"lowered [{name}]: {site} {before.get(site)} -> {after[site]}")  # noqa: T201 -- this script's whole job is CLI output
    return 0


def cmd_first_run(root: Path, ceilings_path: Path) -> int:
    """`first-run`: LC6 step 3's baseline writer, a merge onto any file, never a rewrite."""
    existing = lean_ceilings.load_ceilings(ceilings_path) if ceilings_path.exists() else None
    limits = dict(existing.limits) if existing is not None else dict(STARTING_LIMITS)
    measurement = measure_all(root, limits)
    new_file = build_ceilings(existing, measurement.sections)
    _write_ceilings(ceilings_path, new_file)
    return 0


_COMMANDS = {
    "report": cmd_report,
    "hard": cmd_hard,
    "enforce": cmd_enforce,
    "lower": cmd_lower,
    "first-run": cmd_first_run,
}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: one of `report`, `hard`, `enforce`, `lower`, `first-run`.

    A checker exception aborts before any write and prints to stderr with a non-zero exit --
    `first-run`/`lower` never partially write a baseline built from a garbage measurement.
    """
    parser = argparse.ArgumentParser(prog="lean_check.py")
    parser.add_argument("command", choices=sorted(_COMMANDS))
    args = parser.parse_args(argv)

    try:
        return _COMMANDS[args.command](ROOT, CEILINGS_PATH)
    except Exception as exc:  # noqa: BLE001 -- a checker's own exception is this CLI's own failure mode
        print(f"lean_check.py {args.command}: aborted, nothing written: {exc}", file=sys.stderr)  # noqa: T201 -- this script's whole job is CLI output
        return 1


if __name__ == "__main__":
    sys.exit(main())
