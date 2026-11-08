"""`whitelist.py` and `pyproject.toml`'s `[tool.vulture].ignore_names`: every entry still
defined, every entry carries its reader-class reason, and the entry count never exceeds a
shrink-only ceiling (decision 0050).
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
# 90 + ConductorKind.MOUNT and Scope.link (links order, ruling), each with its reader
# + cross_section_mm2 + LabelKind.WIRE (model twin, tests)
# + PoleSide.LINE, six ConductorMark members, pole_side and conductor_mark
# + two first-half names (default_symbol, pole_order), wired by the second half
# + five ProtectionType members (model-0127), read by value in the loader and by tests
# + four surface calls: series, parallel, ac_supply, dc_supply
# - `design`, + Fn.limits (author-0017 O4), + _.port_pairs: net 138
# + Profile.hide_unused_pins (model-0136 removed the model's own read; layout reads it): net 139
# decision 0115: the count leaves out an OTHER entry that cites a reader in another package
# (148 entries, of which 36 are cross-package OTHER)
# - nominal_current_a (`draw` reads it): one fewer counted entry
# + _.dashed (render defines its own dashed params, so 0115's cross-package exemption
# does not apply)
# 112: _.dashed read by fransys-render/_diagram_boxes.py; render defines its own `dashed`
# (owner 2026-10-07: ceilings may rise; cleanup round 2026-10-08 lowers)
# +1: Design.rack read only by author tests ; owner 2026-10-07: ceilings may rise;
# cleanup round 2026-10-08 lowers
# +3: overview row fields read only by tests until the OVERVIEW Part 3 page reads them; owner
# 2026-10-07: ceilings may rise; cleanup round lowers
# +4: OperatedBy members (parts-0020), built by value in the loader, named by tests;
# +1: d.detail (author-0042) read only by author tests and the guide;
# owner 2026-10-07: ceilings may rise; cleanup round lowers
# 77: CLEANUP-CEILINGS-2 dropped 58 entries a per-package run without the whitelist never flags
# +61: CORE-WAVE0 contract fields, read by later stages; cleanup round lowers
# +3: KeepWhole item_boxes, pole_groups, line_units (EL-GATES-FACTS), 2026-10-15
# +3: Natural.keepout, cut_x, cut_y (SYMDEF-SLOTS-WS Part 4), read by the first engine switch's
# builder; cleanup round lowers
# +3: DrawnSymbol orient, tint, muted (O3-SCENE), read when render draws the scene
# +23: EL-2a role-table fields (model-0288), 2026-10-16
# +4: SignalKind members built by value from SIGNAL_TYPES (EL-3), 2026-10-16; cleanup lowers
# +7: core names cut from __all__ (decision 0226), read by layout tests until P6.1; cleanup lowers
# +1: PlacedView.lane_heads (OVERVIEW-ROWS), read only by fransys_overview, 2026-10-16
# -15: CLEANUP-MODEL-3 dropped entries vulture no longer needs; +2: Settings.pdf and
# Settings.look, read when SETTINGS-LOOK lands (SETTINGS-A1); cleanup lowers
# +9 (measured): Style, Sheet and DrawnWire fields read only by layout tests (DRAWING-VALUE);
# cleanup lowers
# +5 (measured): DrawnText.turned and the Corner members, read by the Label/WireLabel mapping and
# render (ELECTRICAL-MARKERS part F, model-0319); +3 (EL-7): SupplyRails L1-L3; +5 (KIT-FACTS): the
# rows_device_chains and rows_pin_views fields read by fransys_layout's read package;
# +2 (TABLE-T2): Footprints no_cells, nc_cells; cleanup lowers;
# +2 (SHEETS, Ruling 128): SheetKind.BLOCK, LayoutSheet.sheet_kind
# +2 (BUILD-ROWS, R1940): DrawnRow.height, width, read by the consumer
WHITELIST_CEILING = (
    # +1 PageRoutes.dots (P3c, R535); -1 `_.pitch`; +2 PlacedWire.run_a/run_b (layout-0408);
    # -1 shape_key (LINT-ESCAPES-2 P5, its one reader was its test, deleted with it);
    # -6 DS-2 zero-use; -1 R608 band_ranks; +1 SlotSide.C (LAYOUT-LEFTOVERS, KI-034: a deleted TypeVar C had hidden it)
    113  # FIELDS-1: 107 entries gone (84 no run flags, 23 fields deleted); cleanup lowers
)
IGNORE_NAMES_CEILING = 14  # FIELDS-1: the 52 names no per-package vulture run flags are gone


def _whitelist_lines(text: str) -> list[str]:
    """Every stripped line of `text` that opens a whitelist entry (`_.name...`)."""
    return [line.strip() for line in text.splitlines() if line.strip().startswith("_.")]


def _reasoned_entries(text: str) -> list[tuple[str, str, str, int]]:
    """`(name, reader_class, path, line)` for every entry line that matches the reasoned shape."""
    entries: list[tuple[str, str, str, int]] = []
    for line in _whitelist_lines(text):
        match = _REASONED_ENTRY_RE.match(line)
        if match:
            entries.append((match.group(1), match.group(2), match.group(3), int(match.group(4))))
    return entries


def _ignore_names() -> tuple[str, ...]:
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    names: tuple[str, ...] = tuple(str(n) for n in data.get("tool", {}).get("vulture", {}).get("ignore_names", ()))
    return names


def _collect_target_names(target: ast.expr, names: set[str]) -> None:
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, ast.Attribute):
        names.add(target.attr)
    elif isinstance(target, ast.Tuple | ast.List):
        for elt in target.elts:
            _collect_target_names(elt, names)


def _is_enum_base(base: ast.expr) -> bool:
    return (isinstance(base, ast.Name) and base.id == "Enum") or (isinstance(base, ast.Attribute) and base.attr == "Enum")


@pytest.fixture(scope="module")
def workspace_trees() -> list[ast.Module]:
    """Every `packages/*/src/**/*.py` file, parsed once (module-scoped: this walk is the
    expensive part, shared by every fixture below it).
    """
    return [ast.parse(path.read_text(encoding="utf-8")) for path in (ROOT / "packages").glob("*/src/**/*.py")]


def _defined_in(tree: ast.Module) -> set[str]:
    """Every name `tree` defines: a def/class, an assigned name, an attribute-store target."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                _collect_target_names(target, names)
        elif isinstance(node, ast.AnnAssign):
            _collect_target_names(node.target, names)
    return names


@pytest.fixture(scope="module")
def defined_names(workspace_trees: list[ast.Module]) -> frozenset[str]:
    """Every name defined anywhere under `packages/*/src`: a function/class def, an assigned
    name at any scope, or an attribute-store target (`obj.name = ...`).
    """
    names: set[str] = set()
    for tree in workspace_trees:
        names |= _defined_in(tree)
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
                names.update(target.id for stmt in assigns for target in stmt.targets if isinstance(target, ast.Name))
    return frozenset(names)


# --- whitelist.py: defined, reasoned, ceiling -----------------------------------------------


def test_every_whitelist_entry_is_still_defined(defined_names: frozenset[str], spelled_names_by_cited_path: dict[str, frozenset[str]]) -> None:
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


def _package_of(path: str) -> str:
    """The workspace package a `packages/`-relative `path` lies in."""
    return path.split("/", 1)[0]


@pytest.fixture(scope="module")
def defining_packages() -> dict[str, frozenset[str]]:
    """Each name mapped to the packages whose `src` defines it (same walk as `defined_names`)."""
    found: dict[str, set[str]] = {}
    for path in (ROOT / "packages").glob("*/src/**/*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        package = path.relative_to(ROOT / "packages").parts[0]
        for name in _defined_in(tree):
            found.setdefault(name, set()).add(package)
    return {name: frozenset(packages) for name, packages in found.items()}


def _counted_entries(entries: list[tuple[str, str, str, int]], defining: dict[str, frozenset[str]]) -> list[tuple[str, str, str, int]]:
    """The entries the ceiling counts: all but an OTHER one citing a reader in a package that
    defines no such name (proven used there, decision 0115).
    """
    return [
        entry for entry in entries if not (entry[1] == "OTHER" and "/src/" in entry[2] and _package_of(entry[2]) not in defining.get(entry[0], ()))
    ]


def test_whitelist_entry_count_is_at_most_the_ceiling(
    defining_packages: dict[str, frozenset[str]],
) -> None:
    entries = _reasoned_entries(WHITELIST_PATH.read_text(encoding="utf-8"))
    assert len(_counted_entries(entries, defining_packages)) <= WHITELIST_CEILING


def test_an_other_entry_citing_its_own_package_is_counted(
    defining_packages: dict[str, frozenset[str]],
) -> None:
    same = ("port_pairs", "OTHER", "fransys-model/src/fransys_model/x.py", 1)
    cross = ("port_pairs", "OTHER", "fransys-render/src/fransys_render/cables.py", 1)
    assert _counted_entries([same, cross], defining_packages) == [same]


def test_an_other_entry_citing_another_packages_tests_is_counted(
    defining_packages: dict[str, frozenset[str]],
) -> None:
    tests_reader = ("pitch", "OTHER", "fransys-render/tests/test_cables.py", 1)
    assert _counted_entries([tests_reader], defining_packages) == [tests_reader]


# --- ignore_names: still a real enum member, ceiling ----------------


def test_ignore_names_beyond_the_legacy_set_are_real_enum_members(
    enum_member_names: frozenset[str],
) -> None:
    stale = [name for name in _ignore_names() if name not in enum_member_names]
    assert stale == []


def test_ignore_names_count_is_at_most_the_ceiling() -> None:
    assert len(_ignore_names()) <= IGNORE_NAMES_CEILING
