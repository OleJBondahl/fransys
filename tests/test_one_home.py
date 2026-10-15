"""One rule, one home (design 7.1): a fact's record field is read only in the fact's module.

Two gates over every `packages/*/src` file, each with a table in `one-home.toml` of today's
sites as `"module::name" = count`. A count above the table fails and names each `module:line`;
a count below fails with "lower the allowlist", so the table only shrinks. `uv run python
tests/test_one_home.py --write` rewrites the file from the tree. A later gate adds a scanner
to `SCANNERS` and a test; the walk, the compare and the writer are shared.
"""

import ast
import sys
import tomllib
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES_ROOT = ROOT / "packages"
ALLOWLIST = ROOT / "one-home.toml"

HEADER = """\
# One rule, one home (design 7.1): today's sites, written by
# `uv run python tests/test_one_home.py --write`. A seam that moves a read into its fact
# module lowers a count; a count never rises without a reason line in the commit message.
# [field_reads]: "module::field" = reads of a fact-owned record field outside its home.
# [table_walks]: "module::name" = raw record-table reads (`ports(model)`, `model.tables[...]`)
# outside `fransys_model` (a reader walking a table itself instead of reading a fact).
# [kind_reads]: "module::name" = kind-branch reads (`FunctionKind.X`, a `.kind == "unit"`
# compare) outside the role fact, in every package but the old layout engine (design 7.2).
# [kind_reads_legacy_layout]: the same reads in `fransys_layout`, which empties as families switch.
"""

# Record field -> the one module that may read it (design 7.1). The home modules do not exist
# yet, so every read is allowlisted. Name-level: a same-named field on another record is a
# false positive that the allowlist holds.
FACT_FIELDS = {
    "function.kind": "fransys_model.derive.facts.roles",
    "port.role": "fransys_model.derive.facts.roles",
    "net.net_class": "fransys_model.derive.facts.net_facts",
    "net.potential": "fransys_model.derive.facts.net_facts",
    "conductor.kind": "fransys_model.derive.facts.roles",
    "internal_link.kind": "fransys_model.derive.facts.roles",
    "internal_link.rest": "fransys_model.derive.facts.roles",
    "cable_product.core_colours": "fransys_model.derive.facts.cores",
    "item.parent": "fransys_model.derive.facts.children",
    "item.unit": "fransys_model.derive.facts.units",
}
HOME_OF_ATTR = {name.split(".")[1]: home for name, home in FACT_FIELDS.items()}

# The record-table accessors of `fransys_model.vocab.tables`.
TABLE_FUNCTIONS = frozenset(
    [
        "parts",
        "part_libraries",
        "function_templates",
        "port_templates",
        "internal_links",
        "items",
        "functions",
        "ports",
        "nets",
        "conductors",
        "mates",
        "units",
        "unit_releases",
        "boundaries",
        "supply_systems",
        "unused_boundaries",
        "aspect_nodes",
        "placements",
        "documents",
        "projects",
        "revisions",
        "table_of",
        "facets_of",
    ]
)
TABLE_WALK_SKIP = ("fransys_model",)

# Design 7.2: the enums whose members are the role fact's values, and the modules that may read
# them (the vocabulary, the role fact, the enum definitions and the parts lint's field specs).
KIND_ENUMS = frozenset(
    ["FunctionKind", "PortRole", "NetClass", "ConductorKind", "LinkKind", "ItemKind"]
)
KIND_HOMES = frozenset(
    [
        "fransys_model.vocab.roles",
        "fransys_model.derive.facts.roles",
        "fransys_model.vocab.enums",
        "fransys_model.vocab.core",
        "fransys_parts._fields",
    ]
)
LEGACY_LAYOUT = "fransys_layout"

Sites = dict[str, list[int]]
Scanner = Callable[[ast.AST, str], list[tuple[str, int]]]


def source_files() -> list[tuple[str, Path]]:
    """Every real `packages/*/src` .py file with its dotted module name, sorted."""
    found = []
    for path in sorted(PACKAGES_ROOT.glob("*/src/**/*.py")):
        if "__pycache__" in path.parts:
            continue
        parts = (
            path.relative_to(next(p for p in path.parents if p.name == "src")).with_suffix("").parts
        )
        found.append((".".join(parts[:-1] if parts[-1] == "__init__" else parts), path))
    return found


def scan(scanner: Scanner, source: str, module: str) -> Sites:
    """The `(name, line)` pairs `scanner` finds in `source`, grouped as `module::name`."""
    sites: Sites = defaultdict(list)
    for name, line in scanner(ast.parse(source), module):
        sites[f"{module}::{name}"].append(line)
    return dict(sites)


def scan_tree(scanner: Scanner) -> Sites:
    """`scan` over every source file; fails first if the walk found no file."""
    files = source_files()
    assert files, "the source walk found no file"
    sites: Sites = {}
    for module, path in files:
        sites.update(scan(scanner, path.read_text(encoding="utf-8"), module))
    return sites


def field_reads(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """Loads of a fact-owned field name, outside the module that owns it."""
    return [
        (node.attr, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.ctx, ast.Load)
        and HOME_OF_ATTR.get(node.attr, module) != module
    ]


def _aliases(tree: ast.AST) -> dict[str, str]:
    """Local name -> accessor name for `from ... import ports as ports_table`."""
    return {
        alias.asname: alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.asname and alias.name in TABLE_FUNCTIONS
    }


def _table_call_name(node: ast.AST, aliases: dict[str, str]) -> str | None:
    """The accessor name of `ports(model)` or `tables.ports(model)`, else None."""
    if not isinstance(node, ast.Call) or not node.args:
        return None
    func = node.func
    if isinstance(func, ast.Name):
        name = aliases.get(func.id, func.id)
        return name if name in TABLE_FUNCTIONS else None
    if (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "tables"
    ):
        return func.attr if func.attr in TABLE_FUNCTIONS else None
    return None


def _is_tables_subscript(node: ast.AST) -> bool:
    """True for `<anything>.tables[...]`."""
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "tables"
    )


def table_walks(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """Raw record-table reads outside `fransys_model`."""
    if module.split(".", maxsplit=1)[0] in TABLE_WALK_SKIP:
        return []
    found = []
    aliases = _aliases(tree)
    for node in ast.walk(tree):
        name = "tables[]" if _is_tables_subscript(node) else _table_call_name(node, aliases)
        if name:
            found.append((name, getattr(node, "lineno", 0)))
    return found


def _enum_name(node: ast.AST) -> str | None:
    """`FunctionKind` of `FunctionKind.X` or `enums.FunctionKind.X`, else None."""
    if not isinstance(node, ast.Attribute):
        return None
    base = node.value
    name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
    return name if name in KIND_ENUMS else None


def _is_str_operand(node: ast.AST) -> bool:
    """A string constant, or a tuple, list or set made only of string constants."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    return isinstance(node, ast.Tuple | ast.List | ast.Set) and all(
        _is_str_operand(e) for e in node.elts
    )


def _is_kind_compare(node: ast.AST) -> bool:
    """`x.kind == "unit"`, `!=`, `in`, `not in`, either order."""
    if not isinstance(node, ast.Compare):
        return False
    operands = [node.left, *node.comparators]
    ops = (ast.Eq, ast.NotEq, ast.In, ast.NotIn)
    if not all(isinstance(op, ops) for op in node.ops):
        return False
    has_kind = any(isinstance(o, ast.Attribute) and o.attr == "kind" for o in operands)
    return has_kind and any(_is_str_operand(o) for o in operands)


def _kind_reads(tree: ast.AST, module: str, *, legacy: bool) -> list[tuple[str, int]]:
    """Enum-member reads and `.kind` string compares outside the role fact's homes."""
    in_layout = module.split(".", maxsplit=1)[0] == LEGACY_LAYOUT
    if module in KIND_HOMES or in_layout != legacy:
        return []
    found = []
    for node in ast.walk(tree):
        name = _enum_name(node)
        if name and isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            found.append((name, getattr(node, "lineno", 0)))
        elif _is_kind_compare(node):
            found.append(("kind==str", getattr(node, "lineno", 0)))
    return found


def kind_reads(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """Kind-branch reads outside the old layout engine."""
    return _kind_reads(tree, module, legacy=False)


def kind_reads_legacy_layout(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """Kind-branch reads inside `fransys_layout` only."""
    return _kind_reads(tree, module, legacy=True)


SCANNERS: dict[str, Scanner] = {
    "field_reads": field_reads,
    "table_walks": table_walks,
    "kind_reads": kind_reads,
    "kind_reads_legacy_layout": kind_reads_legacy_layout,
}


def load_allowlist() -> dict[str, dict[str, int]]:
    """The tables of `one-home.toml`."""
    return tomllib.loads(ALLOWLIST.read_text(encoding="utf-8"))


def compare(sites: Sites, allowed: dict[str, int]) -> list[str]:
    """One problem line per site over its count (naming `module:line`) or under it."""
    problems = []
    for key in sorted(sites.keys() | allowed.keys()):
        lines, limit = sites.get(key, []), allowed.get(key, 0)
        module = key.split("::")[0]
        if len(lines) > limit:
            where = ", ".join(f"{module}:{line}" for line in lines)
            problems.append(f"{key} read {len(lines)} times, allowed {limit}: {where}")
        elif len(lines) < limit:
            problems.append(f"{key} read {len(lines)} times, allowed {limit}: lower the allowlist")
    return problems


def render(tables: dict[str, Sites]) -> str:
    """The `one-home.toml` text for the scanned sites."""
    out = [HEADER]
    for section, sites in tables.items():
        out.append(f"\n[{section}]\n")
        out.extend(f'"{key}" = {len(lines)}\n' for key, lines in sorted(sites.items()))
    return "".join(out)


def write() -> None:
    """Rewrite `one-home.toml` from the tree, as `lean_check.py` writes `ceilings.toml`."""
    text = render({section: scan_tree(scanner) for section, scanner in SCANNERS.items()})
    ALLOWLIST.write_text(text, encoding="utf-8", newline="\n")


def gate(section: str) -> list[str]:
    """The problems of one gate; fails first if the tree or the allowlist has no site."""
    sites = scan_tree(SCANNERS[section])
    allowed = load_allowlist()[section]
    assert sites, f"the {section} walk found no site"
    assert allowed, f"[{section}] of one-home.toml is empty"
    return compare(sites, allowed)


def test_no_field_read_outside_its_fact_module():
    assert gate("field_reads") == []


def test_no_raw_table_walk_outside_the_model():
    assert gate("table_walks") == []


def test_no_kind_branch_outside_the_role_fact():
    assert gate("kind_reads") + gate("kind_reads_legacy_layout") == []


def test_the_field_gate_can_fail():
    module = "fransys_model.derive.bom"
    sites = scan(field_reads, "x = fn.kind\ny = port.role\nport.role = 1\n", module)
    assert {k: len(v) for k, v in sites.items()} == {f"{module}::kind": 1, f"{module}::role": 1}
    assert compare(sites, {}) != []
    assert "fransys_model.derive.bom:1" in compare(sites, {})[0]
    assert compare(sites, {f"{module}::kind": 2, f"{module}::role": 1}) == [
        f"{module}::kind read 1 times, allowed 2: lower the allowlist"
    ]
    home = FACT_FIELDS["function.kind"]
    assert scan(field_reads, "x = fn.kind", home) == {}


def test_the_raw_table_gate_can_fail():
    module = "fransys_layout.stages.x"
    source = "a = ports(model)\nb = tables.items(model)\nc = model.tables['x']\nd = items.get(1)\n"
    sites = scan(table_walks, source, module)
    assert {k.split("::")[1]: v for k, v in sites.items()} == {
        "ports": [1],
        "items": [2],
        "tables[]": [3],
    }
    assert compare(sites, {}) != []
    assert scan(table_walks, source, "fransys_model.derive.bom") == {}
    aliased = scan(table_walks, "from m import units as u\nx = u(model)\n", module)
    assert aliased == {f"{module}::units": [2]}


def test_the_kind_gate_can_fail():
    module = "fransys_model.derive.bom"
    source = (
        "if fn.kind is FunctionKind.COIL:\n    pass\n"
        "ok = box.kind == 'unit'\n"
        "ok = 'unit' != box.kind\n"
        "ok = box.kind in ('a', 'b')\n"
        "x = Energy.DC\ny = box.kind == other\nz = box.name == 'unit'\n"
        "w = enums.PortRole.LINE\n"
    )
    sites = scan(kind_reads, source, module)
    assert {k.split("::")[1]: v for k, v in sites.items()} == {
        "FunctionKind": [1],
        "kind==str": [3, 4, 5],
        "PortRole": [9],
    }
    assert "fransys_model.derive.bom:1" in compare(sites, {})[0]
    assert scan(kind_reads, source, "fransys_model.derive.facts.roles") == {}
    assert scan(kind_reads, source, "fransys_parts._fields") == {}
    assert scan(kind_reads, source, "fransys_layout.x") == {}
    assert scan(kind_reads_legacy_layout, source, module) == {}
    assert scan(kind_reads_legacy_layout, source, "fransys_layout.x") != {}


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        write()
    else:
        sys.exit("usage: uv run python tests/test_one_home.py --write")
