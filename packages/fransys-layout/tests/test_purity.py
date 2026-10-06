"""FC8 purity check (layout-redesign spec D8, layout-0096), a pure AST scan of `src`.

Fails on (a) a parameter whose annotation is a mutable type at its top level, (b) `nonlocal`,
(c) a module-level binding of a mutable value. The core takes a tree so the can-fail tests
feed it tmp_path source; the real check runs on the package.
"""

import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PACKAGE_ROOT / "src" / "fransys_layout"

MUTABLE_TYPES = frozenset(
    {
        "list",
        "dict",
        "set",
        "bytearray",
        "defaultdict",
        "Counter",
        "deque",
        "OrderedDict",
        "List",
        "Dict",
        "Set",
        "DefaultDict",
        "Deque",
        "MutableSequence",
        "MutableMapping",
        "MutableSet",
    }
)
MUTABLE_CALLS = frozenset({"list", "dict", "set", "defaultdict"})
MUTABLE_LITERALS = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)


def _type_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _top_level_mutable(annotation: ast.expr) -> bool:
    """True when the annotation, or a member of its `|` union, is a mutable type."""
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _top_level_mutable(annotation.left) or _top_level_mutable(annotation.right)
    base = annotation.value if isinstance(annotation, ast.Subscript) else annotation
    return _type_name(base) in MUTABLE_TYPES


def _all_args(args: ast.arguments) -> list[ast.arg]:
    named = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    return [*named, *(a for a in (args.vararg, args.kwarg) if a)]


def mutable_parameters(tree: ast.Module) -> list[tuple[int, str]]:
    """(line, parameter name) of each parameter with a mutable top-level annotation."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found += [
                (arg.lineno, arg.arg)
                for arg in _all_args(node.args)
                if arg.annotation is not None and _top_level_mutable(arg.annotation)
            ]
    return found


def nonlocals(tree: ast.Module) -> list[tuple[int, str]]:
    """(line, names) of each `nonlocal` statement."""
    return [(n.lineno, ",".join(n.names)) for n in ast.walk(tree) if isinstance(n, ast.Nonlocal)]


def _is_mutable_value(value: ast.expr | None) -> bool:
    if isinstance(value, MUTABLE_LITERALS):
        return True
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in MUTABLE_CALLS
    )


def mutable_module_bindings(tree: ast.Module) -> list[tuple[int, str]]:
    """(line, name) of each module-level binding of a list, dict or set value."""
    found = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and _is_mutable_value(node.value):
            found += [(node.lineno, ast.unparse(t)) for t in node.targets]
        elif isinstance(node, ast.AnnAssign) and _is_mutable_value(node.value):
            found.append((node.lineno, ast.unparse(node.target)))
    return found


# The one recorded module-level mutable: the fact registry, written only by `@fact` at import
# (decision layout-0111). A stale entry fails `test_the_registry_allowance_is_live`.
ALLOWED_STATE = frozenset({"conventions/facts.py:FACTS"})


def scan(src_root: Path, allowed: frozenset[str] = frozenset()) -> list[str]:
    """One `path:line: what` per violation of checks (a) to (c) under `src_root`, less `allowed`."""
    out = []
    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(src_root).as_posix()
        checks = (
            ("mutable parameter", mutable_parameters),
            ("nonlocal", nonlocals),
            ("mutable module binding", mutable_module_bindings),
        )
        out += [
            f"{rel}:{line}: {label} {name}"
            for label, check in checks
            for line, name in check(tree)
            if f"{rel}:{name}" not in allowed
        ]
    return out


def _write(tmp_path: Path, source: str) -> list[str]:
    (tmp_path / "mod.py").write_text(source, encoding="utf-8")
    return scan(tmp_path)


def test_mutable_parameter_flagged(tmp_path):
    source = "def f(a: list[int], b: dict | None, *c: set[int], d: bytearray = b''): ...\n"
    hits = _write(tmp_path, source)
    assert sorted(h.rsplit(" ", 1)[1] for h in hits) == ["a", "b", "c", "d"]


def test_typing_alias_parameter_flagged(tmp_path):
    hits = _write(tmp_path, "import typing\ndef f(a: typing.List[int], b: MutableMapping): ...\n")
    assert len(hits) == 2


def test_read_only_parameters_pass(tmp_path):
    source = "def f(a: Sequence[list[int]], b: tuple[list, ...], c: Mapping[str, set]): ...\n"
    assert _write(tmp_path, source) == []


def test_nonlocal_flagged(tmp_path):
    source = "def f():\n    n = 0\n    def g():\n        nonlocal n\n        n += 1\n"
    hits = _write(tmp_path, source)
    assert hits == ["mod.py:4: nonlocal n"]


def test_mutable_module_bindings_flagged(tmp_path):
    source = (
        "A = [1]\nB = {}\nC = {1}\nD = [x for x in A]\nE: dict[str, int] = {'a': 1}\n"
        "F = defaultdict(list)\nG = set()\nH = {k: 1 for k in A}\n"
    )
    names = [h.rsplit(" ", 1)[1] for h in _write(tmp_path, source)]
    assert names == list("ABCDEFGH")


def test_immutable_and_local_bindings_pass(tmp_path):
    source = (
        "A = (1,)\nB = frozenset({1})\nC = frozendict({1: 2})\nD = 'x'\n"
        "def f():\n    local = [1]\n    return local\n"
    )
    assert _write(tmp_path, source) == []


def test_package_is_pure():
    assert scan(SRC_ROOT, ALLOWED_STATE) == []


def test_the_registry_allowance_is_live():
    """Without the allowance the fact registry is flagged, so the entry is not stale."""
    flagged = {h.split(":")[0] + ":" + h.rsplit(" ", 1)[1] for h in scan(SRC_ROOT)}
    assert flagged >= ALLOWED_STATE
