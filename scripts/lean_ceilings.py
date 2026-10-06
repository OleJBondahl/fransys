"""LEAN-GATES' shared `ceilings.toml` model: parsing, rendering, checking, lowering.

The one shared home for every other LEAN-GATES part's ceilings-file logic. `ceilings.toml` (a
root-level tracked file, not written by this module) holds scalar `[limits]`, one ceilings table
per check section (site -> its recorded ceiling), and a designer-ruled `[exempt]` table (site ->
reason). `check` and `lower` share one contract: `measured` holds only sites already over the
plain numeric limit -- a checker never puts a within-limit site in `measured`.

Not a package module (loaded by file path, never imported): lives under root `scripts/`, loaded by
its own tests via `importlib.util.spec_from_file_location`, and imported by the other LEAN-GATES
parts the same way.

A site key's shape says how it is matched: a bare file path is a per-file site, a
`path::qualname` is a per-function site -- both matched only by exact `site in exempt` in
`check`/`lower`/`first_run` -- while a bare directory path (no trailing slash) is a subtree
scope, matched only by `is_exempt_under`, used only by the noqa/ty:ignore reason checker.
"""

from __future__ import annotations

import dataclasses
import tomllib
import types
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

SECTION_ORDER: tuple[str, ...] = (
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

_RESERVED_TABLES = ("limits", "exempt")

#: The inline comment printed after a `[limits]` key; a limit with no entry prints bare.
LIMIT_NOTES: dict[str, str] = {
    "docstring_lines": "summary, blank, two why lines, closing quotes (LC3)",
}


@dataclasses.dataclass(frozen=True)
class CeilingsFile:
    """A parsed `ceilings.toml`.

    Scalar limits, one ceilings table per check section, and the designer-ruled exempt table.
    `sections` holds only the sections actually present in the file (empty sections are simply
    absent, never an empty table).
    """

    limits: dict[str, int]
    sections: dict[str, dict[str, int]]
    exempt: dict[str, str]


@dataclasses.dataclass(frozen=True)
class Violation:
    """One ceilings-check failure.

    `site`, the `measured` value, the `limit` (the effective ceiling it exceeded -- either the
    section's recorded ceiling, or the plain numeric limit when the site was unlisted), and
    whether it was `listed` in ceilings.toml already.
    """

    site: str
    measured: int
    limit: int
    listed: bool


def load_ceilings(path: Path) -> CeilingsFile:
    """Parse `ceilings.toml` via `tomllib` (stdlib, read-only).

    `[limits]` and `[exempt]` are reserved top-level tables; every other top-level table is a
    ceilings section, keyed by its own site->ceiling mapping.
    """
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    limits = dict(data.get("limits", {}))
    exempt = dict(data.get("exempt", {}))
    sections = {name: dict(table) for name, table in data.items() if name not in _RESERVED_TABLES}
    return CeilingsFile(limits=limits, sections=sections, exempt=exempt)


def _quote(text: str) -> str:
    r"""Wrap `text` in double quotes, escaping only `\\` and `"`."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_int_table(name: str, entries: Mapping[str, int]) -> str:
    """`[name]` followed by one sorted `"key" = value` line per entry."""
    lines = [f"[{name}]"]
    lines.extend(f"{_quote(key)} = {entries[key]}" for key in sorted(entries))
    return "\n".join(lines)


def _limit_line(key: str, value: int) -> str:
    note = LIMIT_NOTES.get(key)
    return f"{key} = {value}" + (f"  # {note}" if note else "")


def render_ceilings(file: CeilingsFile) -> str:
    """Render deterministic ceilings text.

    `[limits]` first (keys sorted), then each name in `SECTION_ORDER` that is present in
    `file.sections` and non-empty (sites sorted), then any section present in `file.sections`
    but not in `SECTION_ORDER` (sorted by name, forward-compatible), then `[exempt]` last (keys
    sorted). Skip a table header entirely when its dict is empty (except `[limits]`, always
    emitted). One blank line between tables. Trailing newline.
    """
    tables = ["\n".join(_limit_line(key, file.limits[key]) for key in sorted(file.limits))]
    tables[0] = "[limits]\n" + tables[0] if file.limits else "[limits]"

    ordered_known = [name for name in SECTION_ORDER if file.sections.get(name)]
    ordered_extra = sorted(
        name for name in file.sections if name not in SECTION_ORDER and file.sections[name]
    )
    tables.extend(
        _render_int_table(name, file.sections[name]) for name in [*ordered_known, *ordered_extra]
    )

    if file.exempt:
        lines = ["[exempt]"]
        lines.extend(f"{_quote(key)} = {_quote(file.exempt[key])}" for key in sorted(file.exempt))
        tables.append("\n".join(lines))

    return "\n\n".join(tables) + "\n"


def check(
    measured: Mapping[str, int],
    ceilings: Mapping[str, int],
    limit: int,
    exempt: Mapping[str, str] = types.MappingProxyType({}),
) -> tuple[Violation, ...]:
    """Return violations for `measured` sites over `limit`.

    `measured` holds ONLY sites already over `limit` (every checker's own contract -- a checker
    never puts a within-limit site in `measured`). For each site in `measured`, skip it if `site
    in exempt`; else fail (unlisted, `listed=False`) if `site not in ceilings`; else fail
    (`listed=True`) if `measured[site] > ceilings[site]`; else pass. Sites in `ceilings` but
    absent from `measured` (now within limit) are never a `check` failure -- that is `lower`'s
    job. Return violations sorted by `site`.
    """
    violations: list[Violation] = []
    for site in measured:
        if site in exempt:
            continue
        if site not in ceilings:
            violations.append(
                Violation(site=site, measured=measured[site], limit=limit, listed=False)
            )
        elif measured[site] > ceilings[site]:
            violations.append(
                Violation(site=site, measured=measured[site], limit=ceilings[site], listed=True)
            )
    return tuple(sorted(violations, key=lambda violation: violation.site))


def lower(
    measured: Mapping[str, int],
    ceilings: Mapping[str, int],
    exempt: Mapping[str, str] = types.MappingProxyType({}),
) -> dict[str, int]:
    """Shrink ceilings toward measured values; never raises one.

    For each `site` in `ceilings` (skip any `site in exempt` -- it never appears in the output
    regardless): if `site not in measured` (now within limit), it is deleted (omitted from the
    result); else the new value is `min(ceilings[site], measured[site])` -- shrinks when
    `measured[site]` is smaller, stays unchanged (never raised) when `measured[site]` is larger
    or equal. Never adds a site that is in `measured` but not already in `ceilings` -- a
    brand-new violation stays a `check` failure; only `first_run` (below) ever adds an entry.
    """
    result: dict[str, int] = {}
    for site, ceiling in ceilings.items():
        if site in exempt:
            continue
        if site not in measured:
            continue
        result[site] = min(ceiling, measured[site])
    return result


def first_run(
    measured: Mapping[str, int], exempt: Mapping[str, str] = types.MappingProxyType({})
) -> dict[str, int]:
    """Write a ceilings baseline entry for every measured site.

    LC6 step 3's baseline-writer mode, never called by the lowering run (the caller, not
    this function, enforces that -- just implement the pure logic): every site in `measured`
    (already over-limit, by the same contract as `check`/`lower`) gets a ceilings entry at its
    own measured value, except sites in `exempt`.
    """
    return {site: value for site, value in measured.items() if site not in exempt}


def is_exempt_under(path: str, exempt: Mapping[str, str]) -> bool:
    """Directory-scope exempt match.

    `path` is exempt when it equals a key in `exempt`, or sits under one as a path prefix
    (`path == key or path.startswith(f"{key}/")`). Only a checker that exempts a whole subtree
    (the noqa/ty:ignore reason rule's own dated layout entry) calls this; every per-site numeric
    check (statements, complexity, branches, nested_defs, module_code_lines, docstring_lines,
    md_tokens, md_long_sentences) must keep using plain `site in exempt` (exact match) so a
    directory-shaped key never accidentally exempts an unrelated per-function or per-file site
    under the same path.
    """
    return any(path == key or path.startswith(f"{key}/") for key in exempt)
