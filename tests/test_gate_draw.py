"""Draw gates E5 and E6 (spec SURFACE-COHERENCE R1): layout and pdf draw nothing.

E7 (no `Callable` in a public core name) lives in `test_core_public_types.py`.
"""

import ast

from gate_scan import package_of, src_modules
from test_one_home import SVG_TAGS, _strings

TYPST_SHAPES = ("#rect(", "#line(", "#circle(", "#polygon(", "#path(")
DRAW_NAMES = frozenset(["to_svg", "wire", "table", "stretch"])
DRAW_PREFIX = "to_fragment"


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
