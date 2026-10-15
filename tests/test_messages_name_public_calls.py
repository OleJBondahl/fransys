"""Every call a message names exists on the public surface (BUILD-MESSAGES M4, decision 0192).

The scan reads each string literal of `packages/*/src` that is not a docstring: raise sites,
message templates and the finding registries' cause and fix texts. A name `d.<call>`,
`d.detail.<call>`, `d.layout.<call>`, `fr.<name>` or a bare `call()` must be a public one. The
public surface is collected by introspection, so no list here can drift from it. A moved name
(`d.wire`) is public only as `d.detail.wire`; the text that announces the move is the one
exception.
"""

import ast
import inspect
import re
from pathlib import Path

import fransys as fr

ROOT = Path(__file__).resolve().parent.parent
_NAMED = re.compile(r"(?<![\w.])(fr|d|s)((?:\.[A-Za-z_]\w*){1,2})")
_BARE = re.compile(r"^([a-z_]\w*)\(\) ")
_MOVE = "moved to"


def _methods(cls: type) -> set[str]:
    return {name for name, _ in inspect.getmembers(cls) if not name.startswith("_")}


_DETAIL = _methods(fr.Detail) - _methods(object)
_LAYOUT = _methods(fr.Layout)
_HANDLES = set().union(*(_methods(getattr(fr, n)) for n in ("Device", "Fn", "Pin", "Run")))
_HANDLES |= _methods(fr.Terminal) | _methods(fr.TerminalStrip)
_DESIGN = _methods(fr.Design) - _DETAIL
_BARE_OK = set(fr.__all__) | _DESIGN | _DETAIL | _LAYOUT | _HANDLES


def _named_offence(owner: str, tail: str) -> bool:
    first, *rest = tail.removeprefix(".").split(".")
    second = rest[0] if rest else None
    if owner == "s":
        return True  # a scope handle is no public name
    if owner == "fr":
        found = getattr(fr, first, None)
        return found is None or (second is not None and not hasattr(found, second))
    if first == "detail":
        return second is not None and second not in _DETAIL
    if first == "layout":
        return second is not None and second not in _LAYOUT
    return first not in _DESIGN or (second is not None and second not in _HANDLES | _DETAIL)


def offences(text: str) -> list[str]:
    """The names in `text` that are no public call; empty when the text is clean."""
    if _MOVE in text:
        return []
    named = [m.group(0) for m in _NAMED.finditer(text) if _named_offence(m[1], m[2])]
    bare = [f"{m[1]}()" for m in _BARE.finditer(text) if m[1] not in _BARE_OK]
    return named + bare


def _docstring_nodes(tree: ast.AST) -> set[int]:
    nodes: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                nodes.add(id(body[0].value))
    return nodes


def _strings(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = _docstring_nodes(tree)
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip
    ]


def test_every_message_names_only_public_calls():
    found: list[str] = []
    for path in sorted(ROOT.glob("packages/*/src/**/*.py")):
        if path.name.startswith(("_vendor", "_js_")):
            continue
        for line, text in _strings(path):
            found += [f"{path.relative_to(ROOT)}:{line}: {name}" for name in offences(text)]
    assert not found, f"{len(found)} message strings name a call that is not public:\n" + "\n".join(
        found
    )


def test_the_scan_can_fail():
    assert offences("use d.order") == ["d.order"]
    assert offences("d.bridge needs two terminals") == ["d.bridge"]
    assert offences("call s.unit(...) first") == ["s.unit"]
    assert offences("boundary() needs a unit") == ["boundary()"]
    assert offences("a pin is one wire: use d.wire") == ["d.wire"]
    assert offences("use fr.nonesuch") == ["fr.nonesuch"]
    assert offences("d.layout.nonesuch") == ["d.layout.nonesuch"]


def test_the_scan_passes_public_names():
    assert offences("run d.series(a, b); a fixed terminal is d.detail.wire") == []
    assert offences("d.layout.order(g1, g2) and fr.unit and fr.build") == []
    assert offences("d.wire moved to d.detail.wire in 0.19.0") == []
