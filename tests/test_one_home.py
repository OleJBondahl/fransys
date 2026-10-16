"""One rule, one home (design 7.1 and section 9): a fact is read, and a literal held, in one place.

Gates over every `packages/*/src` file, each with a table in `one-home.toml` of today's
sites as `"module::name" = count`. A count above the table fails and names each `module:line`;
a count below fails with "lower the allowlist", so the table only shrinks. `uv run python
tests/test_one_home.py --write` rewrites the file from the tree. A later gate adds a scanner
to `SCANNERS` and a test; the walk, the compare and the writer are shared. Decision root-0212:
a printed literal and a selection each have one home, and the facade reads no fact field. The
render gates (derive imports, SVG literals) are tested in `tests/test_boundaries.py`.
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
# [literal_homes]: "module::literal" = a string constant holding a HOMES literal outside its home.
# [selection_branches]: "module::PageKind" = compares and dispatch keys on `DocumentPreset` or
# `PageKind` members outside `fransys_model.derive` (root-0212).
# [render_derive_imports]: "module::name" = a `fransys_model.derive` function imported by render
# (a row type or a constant is free; the title-block-text names are exempt). Ends at none.
# [render_svg_literals]: "module::<tag" = a string constant that opens an SVG element (render
# draws nothing itself; `symdef` and `electrical_symbols` do). Ends at none.
# [facade_field_reads]: "module::name" = `.unit`, `.parent`, `.kind` or `.installed` read by
# `fransys` outside the handle check `_subjects.py`.
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

# `bound.kind` of a `CurrentBound` is a `Current`, `bound.role` a `LimitRole`: values of a fact, not
# a function kind or port role, so no role table replaces them (root-0215). Such a receiver is
# skipped only in a module that names `Current` or `LimitRole`; it stays counted anywhere else.
NON_FACT_ENUMS = frozenset(["Current", "LimitRole"])
NON_FACT_RECEIVERS = frozenset(["bound", "limit", "load", "fault", "chosen"])

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
# The test for this list (root-0215): a read counts when EL-2 or EL-3 switches it to a role table.
# Port roles and net classes are such reads, as are the kind enums. `Current` and `LimitRole` are
# values of a fact, not a kind branch, so they are not here, and neither is a `.kind` or `.role`
# read on a record that holds them (`NON_FACT_RECEIVERS`). The next enum is judged by this test.
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

# A printed literal -> the one module that holds it (root-0212). A literal inside another module's
# string constant (a docstring excepted) is a site. Left out for want of a home: " mm²" (two
# derive sites, no home), "(severity)" (docstrings only), "ports added " (home is a G-order).
# "Field devices (" is in two derive modules; `overview_field` is the home, the other is a site.
HOMES = {
    "Block diagram": "fransys_model.derive.page_headings",
    "Own drawing: ": "fransys_model.derive.overview_tree",
    "Field devices (": "fransys_model.derive.overview_field",
}

# A selection function is defined in exactly one module; a compare or dispatch key on these enums
# outside `fransys_model.derive` (and the vocabulary defining them) is a site. `page_titles` is not
# a function on main, so it is left out.
SELECTIONS = frozenset(
    [
        "document_scope",
        "drawn_pages",
        "release_identity",
        "unit_racks",
        "cable_list_rows_of",
        "jumper_lanes",
        "cable_runs",
    ]
)
SELECTION_ENUMS = frozenset(["DocumentPreset", "PageKind"])
SELECTION_HOMES = ("fransys_model.derive", "fransys_model.vocab")

# Gate 2: render calls no derive function except these, and reads derive's row types and constants.
TITLE_BLOCK_TEXT = frozenset(["title_block_strings"])
RENDER_PACKAGE = "fransys_render"
RENDER_MODEL_OK = frozenset(["layout", "vocab", "kernel", "derive"])
SVG_TAGS = ("<text", "<rect", "<line", "<polyline", "<circle", "<path")

# Gate 4: the fact fields the facade does not read, and the one module that checks a handle.
FACADE = "fransys"
FACADE_FIELDS = frozenset(["unit", "parent", "kind", "installed"])
FACADE_HANDLE = "fransys._subjects"

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


def _non_fact_receivers(tree: ast.AST) -> frozenset[str]:
    """`NON_FACT_RECEIVERS` when the module names `Current` or `LimitRole`, else none."""
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    return NON_FACT_RECEIVERS if names & NON_FACT_ENUMS else frozenset()


def _is_non_fact_value(node: ast.Attribute, receivers: frozenset[str]) -> bool:
    """`bound.kind` or `bound.role` on a receiver that holds a `Current` or `LimitRole`."""
    return (
        node.attr in ("kind", "role")
        and isinstance(node.value, ast.Name)
        and node.value.id in receivers
    )


def field_reads(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """Loads of a fact-owned field name, outside the module that owns it.

    A keyword of a class pattern (`case Ref(kind=k)`) reads that field too (root-0215).
    """
    found = []
    skip = _non_fact_receivers(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            if not (_is_non_fact_value(node, skip)):
                found.append((node.attr, node.lineno))
        elif isinstance(node, ast.MatchClass):
            found.extend((kw, node.lineno) for kw in node.kwd_attrs)
    return [(name, line) for name, line in found if HOME_OF_ATTR.get(name, module) != module]


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


def _docstring_ids(tree: ast.AST) -> set[int]:
    """The ids of the string constants that are a module, class or function docstring."""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                ids.add(id(first.value))
    return ids


def _strings(tree: ast.AST) -> list[tuple[str, int]]:
    """Every string constant outside a docstring, as `(text, line)`; an f-string's parts too."""
    skip = _docstring_ids(tree)
    return [
        (n.value, n.lineno)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip
    ]


def literal_homes(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """String constants holding a HOMES literal in a module that is not its home."""
    return [
        (literal, line)
        for text, line in _strings(tree)
        for literal, home in HOMES.items()
        if literal in text and module != home
    ]


MAPPING_READS = frozenset(["get", "pop", "setdefault"])


def _selected_operands(node: ast.AST) -> list[ast.expr]:
    """What a member would select by in `node`: compare, key, subscript, match or `.get`."""
    out: list[ast.expr] = []
    if isinstance(node, ast.Compare):
        out = [node.left, *node.comparators]
    elif isinstance(node, ast.Dict):
        out = [k for k in node.keys if k is not None]
    elif isinstance(node, ast.Subscript):
        out = [node.slice]
    elif isinstance(node, ast.Match):
        out = [node.subject]
    elif isinstance(node, ast.MatchValue):
        out = [node.value]
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
        out = [node.args[0]] if node.func.attr in MAPPING_READS else []
    return out


def _enum_lookup(node: ast.AST) -> str | None:
    """The enum name of `PageKind[...]`, a member picked by a string."""
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        return node.value.id if node.value.id in SELECTION_ENUMS else None
    return None


def selection_branches(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """Members of `DocumentPreset` or `PageKind` that select a branch or a value outside derive."""
    if module.startswith(SELECTION_HOMES):
        return []
    found = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        found.extend(
            (op.value.id, line)
            for op in _flat(_selected_operands(node))
            if isinstance(op, ast.Attribute)
            and isinstance(op.value, ast.Name)
            and op.value.id in SELECTION_ENUMS
        )
        if (name := _enum_lookup(node)) is not None:
            found.append((name, line))
    return found


def _flat(operands: list[ast.expr]) -> list[ast.expr]:
    """The operands with every tuple, list and set unpacked to its members."""
    out: list[ast.expr] = []
    for op in operands:
        if isinstance(op, ast.Tuple | ast.List | ast.Set):
            out.extend(_flat(list(op.elts)))
        else:
            out.append(op)
    return out


def definitions(sources: dict[str, str]) -> dict[str, list[str]]:
    """Selection name -> the modules defining it (a `def` or a module-level assignment)."""
    found: dict[str, list[str]] = {name: [] for name in SELECTIONS}
    for module, source in sources.items():
        for node in ast.walk(ast.parse(source)):
            names = []
            if isinstance(node, ast.FunctionDef):
                names = [node.name]
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for name in names:
                if name in SELECTIONS and module not in found[name]:
                    found[name].append(module)
    return found


def _is_render(module: str) -> bool:
    return module.split(".", maxsplit=1)[0] == RENDER_PACKAGE


def _type_checking_ids(tree: ast.AST) -> set[int]:
    """The ids of every node under an `if TYPE_CHECKING:` block."""
    return {
        id(inner)
        for node in ast.walk(tree)
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test)
        for inner in ast.walk(node)
    }


DERIVE = "fransys_model.derive"
KINDS = ("function", "class", "constant")
MEMO_WRAPPERS = frozenset(["Memo"])
Defs = dict[str, dict[str, tuple[str, ...]]]


def _target_module(node: ast.ImportFrom, module: str, *, is_package: bool) -> str:
    """The dotted module an `ImportFrom` in `module` reads, relative levels resolved."""
    if not node.level:
        return node.module or ""
    base = module.split(".")
    if not is_package:
        base = base[:-1]
    base = base[: len(base) - (node.level - 1)]
    return ".".join([*base, *([node.module] if node.module else [])])


def _assigned_kind(value: ast.expr | None) -> str:
    """A `Memo(f)` wrapper is a named function; any other assignment is a constant."""
    wrapped = (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in MEMO_WRAPPERS
    )
    return "function" if wrapped else "constant"


def _module_defs(tree: ast.Module, module: str, *, is_package: bool) -> dict[str, tuple[str, ...]]:
    """Module-level name -> `(kind,)` for a def, class or assignment, `("from", module, name)`."""
    out: dict[str, tuple[str, ...]] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            out[node.name] = ("function",)
        elif isinstance(node, ast.ClassDef):
            out[node.name] = ("class",)
        elif isinstance(node, ast.Assign):
            kind = (_assigned_kind(node.value),)
            out.update({t.id: kind for t in node.targets if isinstance(t, ast.Name)})
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out[node.target.id] = (_assigned_kind(node.value),)
        elif isinstance(node, ast.ImportFrom):
            target = _target_module(node, module, is_package=is_package)
            out.update({(a.asname or a.name): ("from", target, a.name) for a in node.names})
    return out


def _resolve(defs: Defs, module: str, name: str, depth: int = 8) -> str | None:
    """The kind of `name` in `module`, following `from x import y [as z]` chains."""
    entry = defs.get(module, {}).get(name)
    if entry is None:
        return "module" if f"{module}.{name}" in defs else None
    if entry[0] != "from":
        return entry[0]
    return _resolve(defs, entry[1], entry[2], depth - 1) if depth else None


Resolved = dict[str, dict[str, str]]


def derive_modules(sources: dict[str, str] | None = None) -> Resolved:
    """Derive module -> name -> "function", "class" or "constant", imports followed.

    `sources` is module -> source text; None reads `fransys_model` from the tree.
    """
    if sources is None:
        sources = {
            module: path.read_text(encoding="utf-8")
            for module, path in source_files()
            if module.split(".")[0] == "fransys_model"
        }
    defs: Defs = {
        module: _module_defs(
            ast.parse(text),
            module,
            is_package=any(other.startswith(module + ".") for other in sources),
        )
        for module, text in sources.items()
    }
    resolved: Resolved = {}
    for module in defs:
        if module == DERIVE or module.startswith(DERIVE + "."):
            kinds = {name: _resolve(defs, module, name) for name in defs[module]}
            resolved[module] = {n: k for n, k in kinds.items() if k in KINDS}
    return resolved


def derive_kinds(resolved: Resolved | None = None) -> dict[str, str]:
    """Every name of `fransys_model.derive` and its modules -> its kind (a function wins a tie)."""
    kinds: dict[str, str] = {}
    for names in (derive_modules() if resolved is None else resolved).values():
        for name, kind in names.items():
            if kinds.get(name) != "function":
                kinds[name] = kind
    return kinds


_RESOLVED_CACHE: Resolved = {}


def _tree_resolved() -> Resolved:
    if not _RESOLVED_CACHE:
        _RESOLVED_CACHE.update(derive_modules())
    return _RESOLVED_CACHE


def _is_derive(module: str | None) -> bool:
    return module == DERIVE or (module or "").startswith(DERIVE + ".")


def _dotted(node: ast.AST) -> str | None:
    """`a.b.c` for a chain of names and attributes, else None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and (head := _dotted(node.value)):
        return f"{head}.{node.attr}"
    return None


def _module_aliases(tree: ast.AST, resolved: Resolved) -> dict[str, str]:
    """Local name -> dotted module, for `import x.y as a` and `from x import y` of a module."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update({a.asname: a.name for a in node.names if a.asname})
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for a in node.names:
                if (full := f"{node.module}.{a.name}") in resolved:
                    aliases[a.asname or a.name] = full
    return aliases


def _star_imports(node: ast.ImportFrom, resolved: Resolved) -> list[tuple[str, int]]:
    """One site per public derive function a `from derive import *` brings in."""
    if not any(a.name == "*" for a in node.names):
        return []
    names = resolved.get(node.module or "", {})
    return [(n, node.lineno) for n, k in names.items() if k == "function" and n[0] != "_"]


def _attribute_use(node: ast.Attribute, aliases: dict[str, str], resolved: Resolved) -> str | None:
    """The derive function `d.f` or `fransys_model.derive.f` names, else None."""
    head, _, rest = (_dotted(node.value) or "").partition(".")
    base = ".".join(part for part in (aliases.get(head, head), rest) if part)
    return node.attr if resolved.get(base, {}).get(node.attr) == "function" else None


def _derive_function_imports(tree: ast.AST, resolved: Resolved) -> list[tuple[str, int]]:
    """Every derive function the tree imports by name, by `*`, or reads off a module alias."""
    skip = _type_checking_ids(tree)
    kinds = derive_kinds(resolved)
    aliases = _module_aliases(tree, resolved)
    found = []
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.ImportFrom) and _is_derive(node.module):
            found.extend(_star_imports(node, resolved))
            found.extend(
                (a.name, node.lineno) for a in node.names if kinds.get(a.name) == "function"
            )
        elif isinstance(node, ast.Attribute) and (name := _attribute_use(node, aliases, resolved)):
            found.append((name, node.lineno))
    return [(name, line) for name, line in found if name not in TITLE_BLOCK_TEXT]


def render_derive_imports(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """Derive functions render uses: imported, star-imported or read off a module alias."""
    return _derive_function_imports(tree, _tree_resolved()) if _is_render(module) else []


def render_model_imports(source: str) -> set[str]:
    """The `fransys_model` modules a render source imports beyond layout, vocab, kernel, derive."""
    bad = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            targets = [node.module]
        elif isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        else:
            continue
        for target in targets:
            top, _, rest = target.partition(".")
            if top == "fransys_model" and rest.split(".")[0] not in RENDER_MODEL_OK:
                bad.add(target)
    return bad


def render_svg_literals(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """String constants in render that open an SVG element."""
    if not _is_render(module):
        return []
    return [
        (tag, line)
        for text, line in _strings(tree)
        for tag in SVG_TAGS
        if text.lstrip().startswith(tag)
    ]


def facade_field_reads(tree: ast.AST, module: str) -> list[tuple[str, int]]:
    """Loads of `.unit`, `.parent`, `.kind` or `.installed` in the facade, bar its handle check."""
    if module.split(".", maxsplit=1)[0] != FACADE or module == FACADE_HANDLE:
        return []
    return [
        (node.attr, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.ctx, ast.Load)
        and node.attr in FACADE_FIELDS
    ]


SCANNERS: dict[str, Scanner] = {
    "field_reads": field_reads,
    "table_walks": table_walks,
    "kind_reads": kind_reads,
    "kind_reads_legacy_layout": kind_reads_legacy_layout,
    "literal_homes": literal_homes,
    "selection_branches": selection_branches,
    "render_derive_imports": render_derive_imports,
    "render_svg_literals": render_svg_literals,
    "facade_field_reads": facade_field_reads,
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


def test_the_field_gate_counts_class_pattern_keywords():
    module = "fransys_model.derive.bom"
    source = (
        "match x:\n    case Ref(kind=k, role=r):\n        pass\n"
        "    case Other(plain):\n        pass\n"
    )
    sites = scan(field_reads, source, module)
    assert {k: len(v) for k, v in sites.items()} == {f"{module}::kind": 1, f"{module}::role": 1}
    assert compare(sites, {}) != []
    home_sites = scan(field_reads, source, FACT_FIELDS["function.kind"])
    assert not any(key.endswith("::kind") for key in home_sites)


def test_the_kind_gate_skips_current_and_limit_role_values():
    module = "fransys_model.vocab.x"
    source = "a = Current.AC\nb = LimitRole.MAX\nc = bound.kind is Current.AC\n"
    assert scan(kind_reads, source, module) == {}
    assert scan(field_reads, source + "d = bound.role\n", module) == {}
    planted = source + "e = bound.role is PortRole.LINE\nf = port.role\n"
    assert {k.split("::")[1]: v for k, v in scan(kind_reads, planted, module).items()} == {
        "PortRole": [4]
    }
    assert {k.split("::")[1]: v for k, v in scan(field_reads, planted, module).items()} == {
        "role": [5]
    }


def test_a_bound_receiver_counts_where_no_current_is_named():
    source = "if bound.kind is ItemKind.STRIP:\n    pass\n"
    sites = scan(field_reads, source, "fransys_model.derive.x")
    assert {k.split("::")[1]: v for k, v in sites.items()} == {"kind": [1]}
    assert scan(kind_reads, source, "fransys_model.derive.x")


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


def test_no_homed_literal_outside_its_home():
    sites = scan_tree(literal_homes)
    assert compare(sites, load_allowlist()["literal_homes"]) == []
    files = dict(source_files())
    for literal, home in HOMES.items():
        assert home in files, f"HOMES home {home} does not exist: drop the row"
        assert literal in files[home].read_text(encoding="utf-8"), f"{literal!r} not in {home}"


def test_a_selection_is_defined_in_one_module():
    sources = {m: p.read_text(encoding="utf-8") for m, p in source_files()}
    found = definitions(sources)
    assert {n: m for n, m in found.items() if len(m) != 1} == {}, "define it in one module"


def test_no_preset_or_page_kind_branch_outside_derive():
    assert gate("selection_branches") == []


def test_the_facade_reads_no_fact_field_outside_its_handle_check():
    assert gate("facade_field_reads") == []


def test_the_literal_gate_can_fail():
    module = "fransys_pdf.x"
    source = 'x = "Block diagram 3"\ny = f"Own drawing: {x}"\nz = "other"\n'
    sites = scan(literal_homes, source, module)
    assert {k.split("::")[1]: v for k, v in sites.items()} == {
        "Block diagram": [1],
        "Own drawing: ": [2],
    }
    assert "fransys_pdf.x:1" in compare(sites, {})[0]
    assert compare(sites, {f"{module}::Block diagram": 2, f"{module}::Own drawing: ": 1}) == [
        f"{module}::Block diagram read 1 times, allowed 2: lower the allowlist"
    ]
    home = HOMES["Block diagram"]
    assert scan(literal_homes, source, home).keys() == {f"{home}::Own drawing: "}
    docstring = '"""Block diagram."""\ndef f():\n    """Own drawing: x"""\n'
    assert scan(literal_homes, docstring, module) == {}


def test_the_selection_gate_can_fail():
    module = "fransys_pdf.x"
    source = (
        "if kind is PageKind.BOM:\n    pass\n"
        "ok = kind in (PageKind.COVER, PageKind.NOTES)\n"
        "table = {PageKind.BOM: f, DocumentPreset.FULL: g}\n"
        "bad = other is Energy.DC\n"
    )
    sites = scan(selection_branches, source, module)
    assert {k.split("::")[1]: v for k, v in sites.items()} == {
        "PageKind": [1, 3, 3, 4],
        "DocumentPreset": [4],
    }
    assert scan(selection_branches, source, "fransys_model.derive.x") == {}
    two = {"a": "def drawn_pages(): pass", "b": "drawn_pages = Memo(f)", "c": "x = 1"}
    assert definitions(two)["drawn_pages"] == ["a", "b"]
    assert definitions({"c": "x = 1"})["drawn_pages"] == []


def _enum_sites(source: str) -> dict[str, list[int]]:
    sites = scan(selection_branches, source, "fransys_pdf.x")
    return {k.split("::")[1]: sorted(v) for k, v in sites.items()}


def test_the_selection_gate_flags_a_match_on_a_member():
    source = (
        "match kind:\n    case PageKind.BOM | PageKind.COVER:\n        pass\n"
        "    case DocumentPreset.FULL:\n        pass\n"
        "match PageKind.NOTES:\n    case _:\n        pass\n"
    )
    assert _enum_sites(source) == {"PageKind": [2, 2, 6], "DocumentPreset": [4]}
    assert "fransys_pdf.x:2" in " ".join(
        compare(scan(selection_branches, source, "fransys_pdf.x"), {})
    )
    plain = 'match kind:\n    case "bom":\n        pass\n    case Energy.DC:\n        pass\n'
    assert _enum_sites(plain) == {}


def test_the_selection_gate_flags_a_name_or_member_subscript():
    source = 'a = PageKind["BOM"]\nb = table[PageKind.BOM]\nc = table[DocumentPreset.FULL, 1]\n'
    assert _enum_sites(source) == {"PageKind": [1, 2], "DocumentPreset": [3]}
    near = "a = table[kind]\nb = Other['BOM']\nc = table[Energy.DC]\nd: dict[PageKind, str] = {}\n"
    assert _enum_sites(near) == {}


def test_the_selection_gate_flags_a_mapping_read_keyed_by_a_member():
    source = (
        "a = t.get(PageKind.BOM)\nb = t.get(DocumentPreset.FULL, d)\nc = t.pop(PageKind.NOTES)\n"
        "d = t.setdefault(PageKind.COVER, [])\n"
    )
    assert _enum_sites(source) == {"PageKind": [1, 3, 4], "DocumentPreset": [2]}
    near = "a = t.get(kind)\nb = t.get('x', PageKind.BOM)\nc = t.update(PageKind.BOM)\n"
    assert _enum_sites(near) == {}


def test_the_facade_gate_can_fail():
    source = "a = x.unit\nb = y.parent\nc = z.kind\nd = w.installed\ne = w.name\nf.unit = 1\n"
    sites = scan(facade_field_reads, source, "fransys.pipeline")
    assert {k.split("::")[1]: v for k, v in sites.items()} == {
        "unit": [1],
        "parent": [2],
        "kind": [3],
        "installed": [4],
    }
    assert "fransys.pipeline:2" in " ".join(compare(sites, {}))
    assert compare({"fransys.pipeline::unit": [1]}, {"fransys.pipeline::unit": 2}) == [
        "fransys.pipeline::unit read 1 times, allowed 2: lower the allowlist"
    ]
    assert scan(facade_field_reads, source, FACADE_HANDLE) == {}
    assert scan(facade_field_reads, source, "fransys_layout.x") == {}


PLANTED = {
    "fransys_model.vocab": "def real_fn(): pass\nclass lower_class: pass\n",
    "fransys_model.derive": (
        "from fransys_model.vocab import real_fn, lower_class\n"
        "from .a import CamelFn, lower_const, Wrapped, _hidden, limit as top\n"
    ),
    "fransys_model.derive.a": (
        "def CamelFn(): pass\nlower_const: Final = 3\nWrapped = Memo(f)\nlimit = 3\n"
        "def _hidden(): pass\n"
    ),
    "fransys_model.derive.b": "class OnlyClass: pass\nLIMIT_B = 1\n",
}


def test_the_derive_kind_lookup_can_fail():
    resolved = derive_modules(PLANTED)
    kinds = derive_kinds(resolved)
    assert kinds == {
        "real_fn": "function",
        "lower_class": "class",
        "CamelFn": "function",
        "lower_const": "constant",
        "Wrapped": "function",
        "top": "constant",
        "limit": "constant",
        "_hidden": "function",
        "OnlyClass": "class",
        "LIMIT_B": "constant",
    }
    source = (
        "from fransys_model.derive import real_fn, CamelFn, Wrapped, lower_class, "
        "lower_const, top\n"
    )
    flagged = _derive_function_imports(ast.parse(source), resolved)
    assert [name for name, _ in flagged] == ["real_fn", "CamelFn", "Wrapped"]
    sites = {"fransys_render.x::CamelFn": [1]}
    assert "fransys_render.x:1" in " ".join(compare(sites, {}))
    assert _derive_function_imports(ast.parse(source), {}) == []


def _flagged(source: str) -> list[tuple[str, int]]:
    return _derive_function_imports(ast.parse(source), derive_modules(PLANTED))


def _named(source: str) -> str:
    """The `compare(sites, {})` text for a planted render source: it names each `module:line`."""
    sites: Sites = {}
    for name, line in _flagged(source):
        sites.setdefault(f"fransys_render.x::{name}", []).append(line)
    return " ".join(compare(sites, {}))


def test_a_private_derive_function_is_flagged():
    assert _flagged("from fransys_model.derive.a import _hidden\n") == [("_hidden", 1)]
    assert "fransys_render.x:1" in _named("from fransys_model.derive.a import _hidden\n")
    assert _flagged("from fransys_model.derive.b import OnlyClass, LIMIT_B\n") == []


def test_a_star_import_of_derive_is_one_site_per_public_function():
    names = [name for name, _ in _flagged("from fransys_model.derive import *\n")]
    assert names == ["real_fn", "CamelFn", "Wrapped"]
    assert "fransys_render.x:1" in _named("from fransys_model.derive.a import *\n")
    assert _flagged("from fransys_model.derive.b import *\n") == []


def test_a_derive_module_alias_use_is_flagged():
    aliased = "import fransys_model.derive as d\nx = d.real_fn(d.lower_class, d.LIMIT_B)\n"
    assert _flagged(aliased) == [("real_fn", 2)]
    assert _flagged("import fransys_model.derive\nfransys_model.derive.CamelFn()\n") == [
        ("CamelFn", 2)
    ]
    assert _flagged("from fransys_model import derive\nderive.Wrapped(1)\n") == [("Wrapped", 2)]
    assert _flagged("from fransys_model.derive import a\na.CamelFn()\n") == [("CamelFn", 2)]
    assert "fransys_render.x:2" in _named(aliased)
    near = "import other as d\nd.real_fn()\nimport fransys_model.derive as e\ne.lower_const\n"
    assert _flagged(near) == []
    guarded = "if TYPE_CHECKING:\n    import fransys_model.derive as d\n    d.real_fn\n"
    assert _flagged(guarded) == []


def test_a_camel_case_derive_function_is_flagged():
    assert _flagged("from fransys_model.derive import CamelFn, lower_class\n") == [("CamelFn", 1)]
    assert _flagged("from fransys_model.derive import lower_class, lower_const\n") == []


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        write()
    else:
        sys.exit("usage: uv run python tests/test_one_home.py --write")
