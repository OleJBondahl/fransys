"""Every test that reads `internal/` or `rules/` carries `@pytest.mark.private_input` (R462).

The export has no `internal/` root and no `rules/`, so conftest skips a marked test there. An
unmarked reader fails the export's own gate. A test reads when it, a module-level name it uses, a
fixture it asks for or a name it imports from a sibling test module builds a path under those
folders (`ROOT / "internal"`) or loads a `placement_corpus` module. It is marked when its own
decorators, a fixture it asks for, or the module's `pytestmark` carry the marker, directly or
through a shared name whose value carries it (such as `CASE_PARAMS`).
"""

import ast
from pathlib import Path

from _export_signature import ROOT

READ_DIRS = frozenset({"internal", "rules"})
MARKER = "private_input"
CORPUS = "placement" + "_corpus"  # split, so this file does not flag itself
# Names that build an `internal/` path and read it only if it exists (a missing folder gives an
# empty glob or a False `is_file`), or that only name the signature or a tmp tree. Not readers.
TOLERANT = frozenset(
    {
        "is_export",
        "INTERNAL_FILE",
        "DEFAULT_SCAN",
        "_strict_xfail_sites",
        "test_covered_files_includes_package_docs_two_folders_deep",
    }
)


def _is_dir(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value in READ_DIRS


def _reads(node: ast.AST) -> bool:
    """True when the subtree divides a path by `internal`/`rules` or names a corpus module."""
    for n in ast.walk(node):
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div) and _is_dir(n.right):
            return True
        if isinstance(n, ast.Constant) and str(n.value).startswith(CORPUS):
            return True
    return False


def _refs(node: ast.AST) -> set[str]:
    """Every name the subtree loads, and every argument name of a function in it."""
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    return names | {a.arg for a in ast.walk(node) if isinstance(a, ast.arg)}


def _carries(nodes: list[ast.expr] | list[ast.AST], marked: set[str]) -> bool:
    """True when some node holds the marker or a name whose value holds it."""
    for node in nodes:
        for n in ast.walk(node):
            if isinstance(n, ast.Attribute) and n.attr == MARKER:
                return True
            if isinstance(n, ast.Name) and n.id in marked:
                return True
    return False


def _top_levels(tree: ast.Module) -> dict[str, ast.AST]:
    """The module's functions and plain assignments, by name."""
    found: dict[str, ast.AST] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef | ast.ClassDef):
            found[stmt.name] = stmt
        elif isinstance(stmt, ast.Assign):
            found.update({t.id: stmt for t in stmt.targets if isinstance(t, ast.Name)})
    return found


def _imports(tree: ast.Module) -> list[tuple[str, str]]:
    """(sibling module, name) of every `from module import name`."""
    return [
        (stmt.module, alias.asname or alias.name)
        for stmt in tree.body
        if isinstance(stmt, ast.ImportFrom) and stmt.module
        for alias in stmt.names
    ]


def _grow(defs: dict[str, ast.AST], tainted: set[str]) -> set[str]:
    """Add each top-level name that refers to a tainted name, until nothing is added."""
    grown = True
    while grown:
        grown = False
        for name, node in defs.items():
            if name not in tainted and _refs(node) & tainted:
                tainted.add(name)
                grown = True
    return tainted


def _analyse(
    trees: dict[str, ast.Module],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Per module: its reader names and its marked names, imports followed to a fixed point."""
    tops = {m: _top_levels(t) for m, t in trees.items()}
    tainted = {
        m: {n for n, node in d.items() if n not in TOLERANT and _reads(node)}
        for m, d in tops.items()
    }
    marked = {m: {n for n, node in d.items() if _carries([node], set())} for m, d in tops.items()}
    for _ in range(3):  # one sibling import chain deep is enough; a third pass settles it
        for module, tree in trees.items():
            for source, name in _imports(tree):
                if name in tainted.get(source, ()):
                    tainted[module].add(name)
                if name in marked.get(source, ()):
                    marked[module].add(name)
            tainted[module] = _grow(tops[module], tainted[module])
    return tainted, marked


def _fixture_covers(node: ast.AST | None, marked: set[str]) -> bool:
    return isinstance(node, ast.FunctionDef) and _carries(node.decorator_list, marked)


def unmarked_readers(sources: dict[str, str]) -> list[str]:
    """`module:test` of each test that reads a private input and is not marked."""
    trees = {m: ast.parse(s) for m, s in sources.items()}
    tainted, marked = _analyse(trees)
    found = []
    for module, tree in trees.items():
        tops = _top_levels(tree)
        module_mark = [
            s.value for s in tree.body if isinstance(s, ast.Assign) and _is_pytestmark(s)
        ]
        for name, node in tops.items():
            if not (name.startswith("test_") and name in tainted[module]):
                continue
            assert isinstance(node, ast.FunctionDef)
            asked = {a.arg for a in node.args.args}
            covered = (
                _carries(node.decorator_list, marked[module])
                or _carries(module_mark, marked[module])
                or any(_fixture_covers(tops.get(a), marked[module]) for a in asked)
            )
            if not covered:
                found.append(f"{module}:{name}")
    return found


def _is_pytestmark(stmt: ast.Assign) -> bool:
    return any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets)


def _test_sources() -> dict[str, str]:
    """Source of every `tests/**/*.py` and `packages/*/tests/**/*.py`, keyed by module stem."""
    paths = [*ROOT.glob("tests/**/*.py"), *ROOT.glob("packages/*/tests/**/*.py")]
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(paths)}


def test_every_test_that_reads_a_private_input_is_marked() -> None:
    assert unmarked_readers(_test_sources()) == []


READER = 'from pathlib import Path\n_RUN = Path(".") / "internal" / "run.py"\n'


def test_an_unmarked_reader_is_found() -> None:
    source = READER + "def test_a():\n    assert _RUN\n"
    assert unmarked_readers({"m": source}) == ["m:test_a"]


def test_a_reader_through_a_fixture_or_an_import_is_found() -> None:
    fixture = READER + "import pytest\n@pytest.fixture\ndef run():\n    return _RUN\n"
    fixture += "def test_a(run):\n    pass\n"
    assert unmarked_readers({"m": fixture}) == ["m:test_a"]
    shared = {"base": READER, "m": "from base import _RUN\ndef test_a():\n    _RUN\n"}
    assert unmarked_readers(shared) == ["m:test_a"]


def test_a_marker_on_the_test_the_module_or_a_shared_name_clears_it() -> None:
    own = READER + "@pytest.mark.private_input\ndef test_a():\n    _RUN\n"
    module = READER + "pytestmark = pytest.mark.private_input\ndef test_a():\n    _RUN\n"
    shared_value = "CASES = [pytest.param(1, marks=pytest.mark.private_input)]\n"
    fixture = (
        READER
        + "@pytest.fixture(params=CASES)\ndef run(request):\n    return _RUN\n"
        + "def test_a(run):\n    pass\n"
    )
    assert unmarked_readers({"m": own}) == []
    assert unmarked_readers({"m": module}) == []
    assert unmarked_readers({"base": shared_value, "m": "from base import CASES\n" + fixture}) == []
    assert unmarked_readers({"m": shared_value + fixture}) == []


def test_a_test_that_reads_nothing_private_needs_no_marker() -> None:
    assert unmarked_readers({"m": READER + "def test_a():\n    assert 1\n"}) == []
    assert Path(__file__).exists()
