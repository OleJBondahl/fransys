"""`whitelist.py` and `pyproject.toml`'s `[tool.vulture].ignore_names`: every entry still
defined, every entry carries its reader-class reason, and the entry count never exceeds a
shrink-only ceiling (VULTURE-60, decision 0050).

"Still defined" is class-aware (FIX1): OTHER and TESTS entries cite one real reader `file:line`
-- the specific site whose literal `obj.attr`/call syntax is the whole proof the name is used --
so staleness is checked there and only there: the name must still be spelled (as vulture itself
matches, by bare identifier, not only where first defined) inside that one cited file. A
workspace-wide check would pass even after that exact reader site was rewritten, as long as some
unrelated definition elsewhere in `packages/*/src` happens to share the same spelling (e.g.
`design.py`'s own `def scope(...)` keeps a bare "still defined" check green even if the cited
test no longer calls it). FIELDS and DICT entries cite a shared, generic mechanism site instead
(`kernel/schema.py:37`'s `dataclasses.fields()`, `derive/rows.py:765`'s `getattr(record, name)`)
that never spells any one field's name literally -- their citation is structural, "the class
alone is sufficient evidence" (whitelist.py's own docstring), so they keep the original
workspace-wide "still defined somewhere under packages/*/src" check.

`ignore_names` predates this order by one absorption move (decision 0015): its 15 entries were
`graphical-symbols`' own enum members, back when that package's `src` was still scanned by
`packages/*/src`; since it became an external, pinned, unscanned dependency none of the 15
resolves in `packages/*/src` any more, and none is this order's to fix (root `pyproject.toml`).
`_LEGACY_IGNORE_NAMES` names them so the "still a real enum member" check below applies only to
whatever is added beyond them -- today, nothing (the ROOT-LINES hand-back adds 51 more; until
that lands, every check on `ignore_names` here is vacuously true, proven able to fail by the
probes instead, on a patched copy).

`IGNORE_NAMES_CEILING` is set to 66 (15 legacy + the 51 ROOT-LINES adds), not today's real count
of 15: the shrink-only rule (Part 3c) only ever lowers a ceiling, so its initial value has to be
the one it settles at the moment ROOT-LINES lands, not a number a later, non-root-owned commit
would need to raise.
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WHITELIST_PATH = ROOT / "whitelist.py"
PYPROJECT_PATH = ROOT / "pyproject.toml"

_REASONED_ENTRY_RE = re.compile(r"^_\.(\w+)  # (FIELDS|DICT|OTHER|TESTS) (\S+):(\d+)$")

# Today's count (this branch), shrink-only: lowered as entries are removed, never raised except
# by adding real, reasoned entries.
# 90 + ConductorKind.MOUNT and Scope.link (links order, designer ruling), each with its reader
# + cross_section_mm2 (WIRE-LIST) + LabelKind.WIRE (WIRE-LIST-2: model twin, tests)
# + four F8 data-only fields (nominal_power_w, nominal_current_a, power_loss_w, resistance_ohm)
# + F9: PoleSide.LINE, six ConductorMark members, pole_side and conductor_mark (POLE-SIDES)
# + two EF-B first-half names (default_symbol, pole_order), wired by EF-B part 2
# + five ProtectionType members (model-0127), read by value in the loader and by tests
# + four EA-SERIES surface calls: series, parallel, ac_supply, dc_supply
# - `design` (EA-SWAP), + Fn.limits (author-0017 O4), + _.port_pairs (BOX-OVER-GROUP): net 138
# + Profile.hide_unused_pins (model-0136 removed the model's own read; layout reads it): net 139
WHITELIST_CEILING = 139
IGNORE_NAMES_CEILING = 70  # 15 legacy + 51 ROOT-LINES names + 4 layout-0111 enum members

_LEGACY_IGNORE_NAMES = frozenset(
    {
        "THICK",
        "VERIFIED",
        "UNVERIFIED",
        "ELEMENT",
        "QUALIFIER",
        "SWITCH_OPEN",
        "SWITCH_CLOSED",
        "IMPEDANCE",
        "SOURCE",
        "DIODE",
        "CONDUCTOR",
        "EARTH",
        "PROTECTIVE_EARTH",
        "FUNCTIONAL_EARTH",
        "FRAME",
    }
)


def _whitelist_lines(text: str) -> list[str]:
    """Every stripped line of `text` that opens a whitelist entry (`_.name...`)."""
    return [line.strip() for line in text.splitlines() if line.strip().startswith("_.")]


def _reasoned_entries(text: str) -> list[tuple[str, str, str, int]]:
    """`(name, reader_class, path, line)` for every entry line that matches the reasoned shape."""
    entries = []
    for line in _whitelist_lines(text):
        match = _REASONED_ENTRY_RE.match(line)
        if match:
            entries.append((match.group(1), match.group(2), match.group(3), int(match.group(4))))
    return entries


def _ignore_names() -> tuple[str, ...]:
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    return tuple(data.get("tool", {}).get("vulture", {}).get("ignore_names", ()))


def _collect_target_names(target: ast.expr, names: set[str]) -> None:
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, ast.Attribute):
        names.add(target.attr)
    elif isinstance(target, ast.Tuple | ast.List):
        for elt in target.elts:
            _collect_target_names(elt, names)


def _is_enum_base(base: ast.expr) -> bool:
    return (isinstance(base, ast.Name) and base.id == "Enum") or (
        isinstance(base, ast.Attribute) and base.attr == "Enum"
    )


@pytest.fixture(scope="module")
def workspace_trees() -> list[ast.Module]:
    """Every `packages/*/src/**/*.py` file, parsed once (module-scoped: this walk is the
    expensive part, shared by every fixture below it).
    """
    return [
        ast.parse(path.read_text(encoding="utf-8"))
        for path in (ROOT / "packages").glob("*/src/**/*.py")
    ]


@pytest.fixture(scope="module")
def defined_names(workspace_trees: list[ast.Module]) -> frozenset[str]:
    """Every name defined anywhere under `packages/*/src`: a function/class def, an assigned
    name at any scope, or an attribute-store target (`obj.name = ...`).
    """
    names: set[str] = set()
    for tree in workspace_trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    _collect_target_names(target, names)
            elif isinstance(node, ast.AnnAssign):
                _collect_target_names(node.target, names)
    return frozenset(names)


def _spelled_names(tree: ast.Module) -> set[str]:
    """Every identifier `tree` spells: a def, an assignment target, a plain name reference, an
    attribute access, a parameter or a keyword-argument name -- vulture's own matching
    granularity (whitelist.py's own docstring: a name counts as used everywhere it is spelled
    the same, not only where it is first defined).
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.keyword) and node.arg is not None:
            names.add(node.arg)  # keyword.arg: str | None; None is **kwargs, never a name
    return names


# Reader classes whose citation is one specific reader site (checked against that one file);
# the other two (FIELDS, DICT) cite a shared, generic mechanism site instead (module docstring).
_SITE_SPECIFIC_CLASSES = frozenset({"OTHER", "TESTS"})


@pytest.fixture(scope="module")
def spelled_names_by_cited_path() -> dict[str, frozenset[str]]:
    """Every `OTHER`/`TESTS` whitelist entry's own cited file, parsed once, mapped to every
    name it spells.
    """
    entries = _reasoned_entries(WHITELIST_PATH.read_text(encoding="utf-8"))
    by_path: dict[str, frozenset[str]] = {}
    for _, reader_class, path, _ in entries:
        if reader_class in _SITE_SPECIFIC_CLASSES and path not in by_path:
            tree = ast.parse((ROOT / "packages" / path).read_text(encoding="utf-8"))
            by_path[path] = frozenset(_spelled_names(tree))
    return by_path


@pytest.fixture(scope="module")
def enum_member_names(workspace_trees: list[ast.Module]) -> frozenset[str]:
    """Every member name of an `Enum` subclass defined anywhere under `packages/*/src`."""
    names: set[str] = set()
    for tree in workspace_trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(_is_enum_base(base) for base in node.bases):
                assigns = (stmt for stmt in node.body if isinstance(stmt, ast.Assign))
                names.update(
                    target.id
                    for stmt in assigns
                    for target in stmt.targets
                    if isinstance(target, ast.Name)
                )
    return frozenset(names)


# --- whitelist.py: defined, reasoned, ceiling -----------------------------------------------


def test_every_whitelist_entry_is_still_defined(
    defined_names: frozenset[str], spelled_names_by_cited_path: dict[str, frozenset[str]]
) -> None:
    entries = _reasoned_entries(WHITELIST_PATH.read_text(encoding="utf-8"))
    stale = []
    for name, reader_class, path, _ in entries:
        if reader_class in _SITE_SPECIFIC_CLASSES:
            if name not in spelled_names_by_cited_path[path]:
                stale.append(name)
        elif name not in defined_names:
            stale.append(name)
    assert stale == []


def test_every_whitelist_entry_has_its_reason() -> None:
    text = WHITELIST_PATH.read_text(encoding="utf-8")
    unreasoned = [line for line in _whitelist_lines(text) if not _REASONED_ENTRY_RE.match(line)]
    assert unreasoned == []


def test_whitelist_entry_count_is_at_most_the_ceiling() -> None:
    entries = _reasoned_entries(WHITELIST_PATH.read_text(encoding="utf-8"))
    assert len(entries) <= WHITELIST_CEILING


# --- ignore_names: still a real enum member (beyond the legacy set), ceiling ----------------


def test_ignore_names_beyond_the_legacy_set_are_real_enum_members(
    enum_member_names: frozenset[str],
) -> None:
    new_entries = [name for name in _ignore_names() if name not in _LEGACY_IGNORE_NAMES]
    stale = [name for name in new_entries if name not in enum_member_names]
    assert stale == []


def test_ignore_names_count_is_at_most_the_ceiling() -> None:
    assert len(_ignore_names()) <= IGNORE_NAMES_CEILING
