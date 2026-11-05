"""The scanner of the LIBRARY-TWINS gate (decision root-0409, SPEC-LIB-ADOPT R5, R7).

A twin is Fransys code that copies what `symdef`, `elecdef` or `refdef` provide. Two kinds of
site: a file of `TWINS` (counted in code lines) and a top-level def, class or assignment outside
"""

import ast
import importlib

from gate_scan import ROOT, src_modules

LIBRARIES = ("symdef", "elecdef", "refdef")
DOORS = ("fransys_model.kernel", "fransys_model.elecdef", "fransys_model.refdef")
DOOR_FILES = ("fransys_kernel.naturals",)
# Qualified names the scan skips, each with its reason (designer R783 Q4).
NOT_TWINS = {
    "fransys_layout.core.flow_values::Block": "a placement block, not an electrical one",
    "fransys_layout.drawing::Corner": (
        "text-anchor Literal = symdef.freetext.Corner, not exported; "
        "next batched symdef release exports it, then drawing re-exports and the Literal goes (R1622)"
    ),
    "fransys_model.layout.enums::Corner": "the model may not import symdef (owner 2026-10-24)",
    "fransys_el.placement_annexes::Corner": "CLEANUP-AFTER-022 (R1622)",
}
M = "packages/fransys-model/src/fransys_model/"
A = "packages/fransys-author/src/fransys_author/surface/"
P = "packages/fransys-parts/src/fransys_parts/"
L = "packages/fransys-layout/src/fransys_layout/"
TWINS = [
    *(f"{M}vocab/{n}.py" for n in ["designation_scheme", "colours", "signal_types", "markings"]),
    *(f"{M}derive/facts/{n}.py" for n in ["function_ratings", "part_throws", "part_poles"]),
    f"{M}derive/contacts.py",
    f"{M}derive/texts/designation_render.py",
    f"{M}derive/texts/designation_segments.py",
    f"{M}vocab/facets/rating.py",
    f"{A}_tags.py",
    f"{A}_unit_tags.py",
    # _ratings.py is no twin (R915 P5): function_ratings and the part-level [block] mapping read Fransys records; narrowed by name, ADOPT-POLES-2
    f"{P}_protection.py",
    f"{L}core/keys.py",
    f"{L}geometry/symbols.py",  # symdef reader; falls with CC3
]


def code_lines(path: str) -> list[str]:
    """`path:N` for every line of the file that is neither blank nor a comment."""
    file = ROOT / path
    rows = file.read_text(encoding="utf-8").splitlines() if file.exists() else []
    return [f"{path}:{i}" for i, row in enumerate(rows, 1) if row.strip() and not row.lstrip().startswith("#")]


def _top_names(tree: ast.Module) -> list[str]:
    found: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            found.append(node.name)
        elif isinstance(node, ast.Assign):
            found += [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.append(node.target.id)
    return found


def library_names() -> frozenset[str]:
    """Every public name of the three libraries."""
    names: frozenset[str] = frozenset(str(n) for lib in LIBRARIES for n in importlib.import_module(lib).__all__)
    return names


def library_twins(names: frozenset[str] | None = None) -> dict[str, list[int | str]]:
    """Every twin site, keyed as the `[library_twins]` table keys it, with its `path:line` list."""
    names = library_names() if names is None else names
    sites: dict[str, list[int | str]] = {path: list(code_lines(path)) for path in TWINS}
    for module, path in src_modules():
        if module.startswith(DOORS) or module in DOOR_FILES:
            continue
        for name in dict.fromkeys(_top_names(ast.parse(path.read_text(encoding="utf-8")))):
            if name in names and f"{module}::{name}" not in NOT_TWINS:
                sites[f"name:{module}::{name}"] = [f"{module}::{name}"]
    return sites
