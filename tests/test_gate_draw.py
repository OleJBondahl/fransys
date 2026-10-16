"""Draw gates E5, E6 and E7 (spec SURFACE-COHERENCE R1): layout and pdf draw nothing.

E7 is the `Callable` half of the core-scope rule; the two sort keys of `topology_cycles` are exempt.
"""

import ast

from gate_scan import PACKAGES_ROOT, package_of, src_modules
from test_one_home import SVG_TAGS, _strings

TYPST_SHAPES = ("#rect(", "#line(", "#circle(", "#polygon(", "#path(")
DRAW_NAMES = frozenset(["to_svg", "wire", "table", "stretch"])
DRAW_PREFIX = "to_fragment"
CORE_DIR = PACKAGES_ROOT / "fransys-layout" / "src" / "fransys_layout" / "core"
KEY_EXEMPT = frozenset([("topology_cycles", "y_cycle_cuts", "key")])


def svg_literals(source: str) -> list[tuple[str, int]]:
    """String constants outside docstrings that open an SVG element."""
    return [
        (tag, line)
        for text, line in _strings(ast.parse(source))
        for tag in SVG_TAGS
        if text.lstrip().startswith(tag)
    ]


def typst_shapes(source: str) -> list[tuple[str, int]]:
    """String constants outside docstrings that hold a Typst drawing call."""
    return [
        (shape, line)
        for text, line in _strings(ast.parse(source))
        for shape in TYPST_SHAPES
        if shape in text
    ]


def _is_draw(name: str) -> bool:
    return name in DRAW_NAMES or name.startswith(DRAW_PREFIX)


def _in_symdef(module: str) -> bool:
    return module == "symdef" or module.startswith("symdef.")


def draw_calls(source: str) -> list[tuple[str, int]]:
    """Calls of a symdef draw function, by an imported name or an attribute of a symdef alias."""
    tree = ast.parse(source)
    names: dict[str, str] = {}
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and _in_symdef(node.module or ""):
            names.update({a.asname or a.name: a.name for a in node.names})
        elif isinstance(node, ast.Import):
            modules.update(
                a.asname or a.name.split(".")[0] for a in node.names if _in_symdef(a.name)
            )
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and _is_draw(names.get(func.id, "")):
            hits.append((names[func.id], node.lineno))
        elif isinstance(func, ast.Attribute) and _is_draw(func.attr):
            root = func.value
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and (root.id in modules or root.id in names):
                hits.append((func.attr, node.lineno))
    return hits


def _mentions_callable(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name) and node.id == "Callable":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "Callable":
            return True
        if isinstance(node, ast.Constant) and "Callable" in str(node.value):
            return True
    return False


def callable_params(source: str, module: str) -> list[tuple[str, str, int]]:
    """`(function, parameter, line)` of each public top-level function with a `Callable` parameter.

    Public means not underscore-named; the private `_pick` (`rank`) is not scanned.
    """
    hits = []
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) or node.name.startswith(
            "_"
        ):
            continue
        args = node.args
        every = [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]
        typed = [a for a in every if a and a.annotation]
        hits += [(node.name, a.arg, a.lineno) for a in typed if _mentions_callable(a.annotation)]
    return [h for h in hits if (module, *h[:2]) not in KEY_EXEMPT]


def _public_core_callables() -> list[str]:
    hits = []
    for path in sorted(CORE_DIR.glob("*.py")):
        found = callable_params(path.read_text(encoding="utf-8"), path.stem)
        hits += [f"{path.stem}:{line} {fn}({arg})" for fn, arg, line in found]
    return hits


def _scan(package: str, scanner) -> list[str]:
    hits = []
    for module, path in src_modules():
        if package_of(module) == package:
            found = scanner(path.read_text(encoding="utf-8"))
            hits += [f"{module}:{line} {what}" for what, line in found]
    return hits


def test_layout_and_pdf_write_no_svg_element():
    assert any(m.startswith("fransys_pdf") for m, _ in src_modules())
    assert _scan("fransys_layout", svg_literals) == []
    assert _scan("fransys_pdf", svg_literals) == []


def test_pdf_draws_no_typst_shape_but_places_and_tables():
    placed = sum(
        path.read_text(encoding="utf-8").count("#place(")
        for module, path in src_modules()
        if package_of(module) == "fransys_pdf"
    )
    assert placed > 0, "the scan reads no Typst string"
    assert _scan("fransys_pdf", typst_shapes) == []


def test_layout_calls_no_symdef_draw_function():
    assert any(
        "body_box" in path.read_text(encoding="utf-8")
        and module == "fransys_layout.geometry.symbols"
        for module, path in src_modules()
    )
    assert _scan("fransys_layout", draw_calls) == []


def test_layout_reads_body_box_from_symdef():
    path = dict(src_modules())["fransys_layout.geometry.symbols"]
    tree = ast.parse(path.read_text(encoding="utf-8"))
    taken = {
        a.name
        for n in ast.walk(tree)
        if isinstance(n, ast.ImportFrom) and _in_symdef(n.module or "")
        for a in n.names
    }
    assert "body_box" in taken


def test_no_public_core_function_takes_a_callable():
    source = (CORE_DIR / "topology_cycles.py").read_text(encoding="utf-8")
    assert "def y_cycle_cuts(" in source, "the exempt key function moved"
    assert callable_params(source, "none"), "the scan found no Callable even without the exemption"
    assert _public_core_callables() == []


def test_the_svg_gate_can_fail():
    assert svg_literals('x = "<rect x=1/>"')
    assert svg_literals("x = f'<text {a}>'")
    assert svg_literals('"""<rect doc"""\nx = 1') == []
    assert svg_literals('x = "#place(dx: 1pt)"') == []


def test_the_typst_gate_can_fail():
    for shape in TYPST_SHAPES:
        assert typst_shapes(f'x = "{shape}width: 1pt)"')
    assert typst_shapes('x = "#place(dx: 1pt)"') == []
    assert typst_shapes('x = "#table(columns: 2)"') == []


def test_the_draw_gate_can_fail():
    forms = [
        "from symdef import wire\nwire(1)",
        "from symdef import to_fragment_a\nto_fragment_a(1)",
        "from symdef import wire as w\nw(1)",
        "from symdef.model import table\ntable(1)",
        "import symdef\nsymdef.wire(1)",
        "import symdef as s\ns.stretch(1)",
        "from symdef import model\nmodel.to_svg(1)",
    ]
    for source in forms:
        assert draw_calls(source), source
    assert draw_calls("from symdef import body_box\nbody_box(1)") == []
    assert draw_calls("from other import wire\nwire(1)") == []
    assert draw_calls("def wire(x): ...\nwire(1)") == []


def test_the_callable_gate_can_fail():
    forms = [
        "def f(a: Callable[[str], int]): ...",
        "def f(a: Callable[[str], int] | None = None): ...",
        "def f(*, a: collections.abc.Callable): ...",
        "def f(*a: Callable): ...",
        "def f(a: 'Callable[[], int]'): ...",
    ]
    for source in forms:
        assert callable_params(source, "x"), source
    assert callable_params("def _f(a: Callable): ...", "x") == []
    assert callable_params("def f(a: int): ...", "x") == []
    exempt = "def y_cycle_cuts(key: Callable): ..."
    assert callable_params(exempt, "topology_cycles") == []
    assert callable_params(exempt, "other")
