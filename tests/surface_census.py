"""Census of package surfaces for the SURFACE-RATCHETS tests: kind, readers, transitive reads.

`census(modules)` maps `module.name` to a `NameRow`. A reader is a file that imports the name from
its module (AST, `gate_scan.imports_of`). An outside reader is a file in neither the module's own
package nor a tests folder. A name is read transitively when a name with an outside reader mentions
it in a parameter or return annotation (a row type returned by a read function).
"""

import annotationlib
import dataclasses
import enum
import functools
import importlib
import inspect
import re
import types
import typing
from collections import defaultdict
from typing import TYPE_CHECKING, NamedTuple

from gate_scan import ROOT, imports_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

DEFAULT_SCAN = (
    *sorted(ROOT.glob("packages/*/src")),
    *sorted(ROOT.glob("packages/*/tests")),
    ROOT / "tests",
    ROOT / "scripts",
    ROOT / "internal",
)
ALIAS_TYPES = ("TypeAliasType", "_GenericAlias", "UnionType", "GenericAlias", "_UnionGenericAlias")
DOORS = ("fransys_model.kernel", "fransys_model.vocab", "fransys_model.derive")


class NameRow(NamedTuple):
    """One public name: its kind, every reader file, the outside ones, and the transitive flag."""

    module: str
    name: str
    kind: str
    readers: tuple[str, ...]
    outside: tuple[str, ...]
    transitive: bool

    @property
    def unread(self) -> bool:
        """No outside reader and no transitive reader."""
        return not self.outside and not self.transitive


def kind(obj: object) -> str:
    """enum, error, dataclass, class, module, function, callable, alias or constant."""
    if isinstance(obj, type):
        if issubclass(obj, enum.Enum):
            return "enum"
        if issubclass(obj, BaseException):
            return "error"
        return "dataclass" if dataclasses.is_dataclass(obj) else "class"
    if isinstance(obj, types.ModuleType):
        return "module"
    if callable(obj):
        plain = inspect.isfunction(obj) or inspect.isbuiltin(obj) or hasattr(obj, "__wrapped__")
        return "function" if plain else "callable"
    return "alias" if type(obj).__name__ in ALIAS_TYPES else "constant"


def _package_of(rel: str) -> str:
    parts = rel.split("/")
    if parts[0] == "packages":
        return parts[1] + ("/tests" if parts[2] == "tests" else "")
    return parts[0]


def _is_test(rel: str) -> bool:
    return "/tests" in _package_of(rel) or rel.startswith("tests/")


def readers_of(modules: Iterable[str], scan: Sequence[Path], root: Path) -> dict[tuple, set[str]]:
    """`(module, name) -> {file}` for each `from module import name` or `alias.name` in `scan`."""
    wanted = set(modules)
    hits: dict[tuple, set[str]] = defaultdict(set)
    for base in scan:
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(root).as_posix()
            try:
                rows = imports_of(path.read_text(encoding="utf-8"), rel)
            except SyntaxError, UnicodeDecodeError:
                continue
            for row in rows:
                if row.source in wanted and row.name:
                    hits[(row.source, row.name)].add(rel)
    return hits


def _mentioned(annotation: object, home: dict[str, object]) -> Iterable[object]:
    """The objects an annotation names, through generics and unions; forward names via `home`."""
    if isinstance(annotation, str | annotationlib.ForwardRef):
        text = annotation if isinstance(annotation, str) else annotation.__forward_arg__
        words = set(re.findall(r"\w+", text))
        yield from (v for k, v in home.items() if k in words)
        return
    yield annotation
    for arg in typing.get_args(annotation):
        yield from _mentioned(arg, home)


def _signature_mentions(obj: object, home: dict[str, object]) -> list[object]:
    if not (inspect.isfunction(obj) or inspect.isclass(obj)):
        return []
    target = obj.__init__ if inspect.isclass(obj) else obj
    try:
        hints = annotationlib.get_annotations(target, format=annotationlib.Format.FORWARDREF)
    except TypeError, AttributeError:
        return []
    return [m for a in hints.values() for m in _mentioned(a, home)]


def _transitive(objs: Mapping[str, object], read: Iterable[str]) -> set[str]:
    """Keys of names whose object a read name's signature mentions."""
    home = {key.rpartition(".")[2]: obj for key, obj in objs.items()}
    by_id = {id(obj): key for key, obj in objs.items() if kind(obj) != "constant"}
    found = set()
    for key in read:
        for mention in _signature_mentions(objs[key], home):
            if id(mention) in by_id and by_id[id(mention)] != key:
                found.add(by_id[id(mention)])
    return found


def census(
    modules: Sequence[str], scan: Sequence[Path] = DEFAULT_SCAN, root: Path = ROOT
) -> dict[str, NameRow]:
    """One `NameRow` per name of each module's `__all__`, with transitive reads resolved."""
    hits = readers_of(modules, scan, root)
    objs: dict[str, object] = {}
    rows: dict[str, NameRow] = {}
    for module in modules:
        mod = importlib.import_module(module)
        home = module.split(".")[0].replace("_", "-")
        for name in mod.__all__:
            obj = objs[f"{module}.{name}"] = getattr(mod, name)
            files = sorted(hits.get((module, name), set()))
            far = tuple(f for f in files if _package_of(f) != home and not _is_test(f))
            rows[f"{module}.{name}"] = NameRow(
                module, name, kind(obj), tuple(files), far, transitive=False
            )
    via = _transitive(objs, [key for key, row in rows.items() if row.outside])
    return {key: row._replace(transitive=key in via) for key, row in rows.items()}


@functools.cache
def door_census() -> dict[str, NameRow]:
    """The census of the three doors, built once per process and shared by the ratchet tests."""
    return census(DOORS)
