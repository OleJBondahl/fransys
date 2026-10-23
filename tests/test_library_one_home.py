"""The grid and the font are set once, in `electrical-symbols/library.toml` (ES-SYMDEF, SB0).

The scan fails on a second `[grid]` or `[font]` table, on the divisions factor typed as a literal
(a `G_PER_MODULE = 8` binding, a `round(x * 8)` converter, `* 8` in a `_g` or `to_grid`), on a
second font advance table. Each message names the file, the line and the home.
Reads of the name `G_PER_MODULE` are fine
(`fransys_layout/geometry/units.py`, `fransys_render/_slots.py` hold no
literal). The allowlist names the two sites that still hold the copy, each with the order that
ends it. The sheet formats' `module_mm` (`formats.py`, STOCK) is named, not
checked: its fate is GRID-HOME-B.
"""

import ast
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ROOT / "packages"
HOME = "packages/electrical-symbols/library.toml"
FACTOR_NAMES = {"G_PER_MODULE", "DIVISIONS_PER_MODULE"}
CONVERTERS = {"_g", "to_grid"}
FONT_PAIR = re.compile(r"\b20=585\b")

# (path relative to the root, what it holds): the order that deletes it.
ALLOWED = {
    ("packages/fransys-model/src/fransys_model/derive/_text_widths.py", "font"): "MODEL-TEXT",
}

# Named stock, not an exception: sheet formats declare their own module_mm (same 2.5 today).
# Fate GRID-HOME-B (designer 2026-10-16); library.toml [grid] module_mm = 2.5 is right.
STOCK = {
    "packages/fransys-model/src/fransys_model/layout/formats.py": ("        module_mm=Decimal", 2),
}


def _is_eight(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value == 8 and isinstance(node.value, int)


def _times_factor(node: ast.AST, *, named: bool = True) -> bool:
    """`x * 8`, and with `named` also `x * G_PER_MODULE`."""
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Mult)
        and (
            _is_eight(node.right)
            or _is_eight(node.left)
            or (
                named
                and any(
                    isinstance(s, ast.Name) and s.id in FACTOR_NAMES
                    for s in (node.left, node.right)
                )
            )
        )
    )


def python_hits(source: str) -> list[tuple[int, str]]:
    """The factor and font sites of one Python source: `(line, kind)`."""
    tree = ast.parse(source)
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if node.value is not None and _is_eight(node.value):
                hits += [
                    (node.lineno, "factor") for t in targets if getattr(t, "id", "") in FACTOR_NAMES
                ]
        elif (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", "") == "round"
            and any(_times_factor(a) for a in node.args)
        ):
            hits.append((node.lineno, "factor"))
        elif isinstance(node, ast.FunctionDef) and node.name in CONVERTERS:
            hits += [
                (n.lineno, "factor")
                for n in ast.walk(node)
                if isinstance(n, ast.BinOp) and _times_factor(n, named=False)
            ]
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and FONT_PAIR.search(node.value)
        ):
            hits.append((node.lineno, "font"))
    return sorted(set(hits))


def toml_hits(text: str) -> list[str]:
    """The `grid` and `font` top-level tables of one TOML text."""
    return [k for k in ("grid", "font") if k in tomllib.loads(text)]


def scan(root: Path) -> list[str]:
    """Every violation under `root/packages`, as `file:line: what, home`."""
    found: list[str] = []
    for path in sorted((root / "packages").rglob("*.toml")):
        rel = path.relative_to(root).as_posix()
        if rel != HOME and "/.venv/" not in rel and path.name == "library.toml":
            found += [
                f"{rel}: a [{k}] table; the one home is {HOME}" for k in toml_hits(path.read_text())
            ]
    for path in sorted((root / "packages").glob("*/src/**/*.py")):
        rel = path.relative_to(root).as_posix()
        text = path.read_text()
        for line, kind in python_hits(text):
            if (rel, kind) not in ALLOWED:
                what = "the divisions factor" if kind == "factor" else "a font advance table"
                found.append(f"{rel}:{line}: {what}; the one home is {HOME}")
    return found


def test_the_grid_and_the_font_have_one_home() -> None:
    assert scan(ROOT) == []


def test_the_home_declares_both() -> None:
    assert toml_hits((ROOT / HOME).read_text()) == ["grid", "font"]


def test_the_allowlist_still_holds_what_it_names() -> None:
    """An entry whose site is gone fails, so the list only shrinks."""
    for (rel, kind), order in ALLOWED.items():
        assert (ROOT / rel).exists(), f"{rel} is gone: delete its entry ({order})"
        assert any(k == kind for _, k in python_hits((ROOT / rel).read_text())), (
            f"{rel} holds no {kind}: delete its entry"
        )


def test_the_scan_flags_each_second_declaration(tmp_path: Path) -> None:
    src = tmp_path / "packages" / "p" / "src" / "p"
    src.mkdir(parents=True)
    (src / "a.py").write_text(
        "G_PER_MODULE = 8\n"
        "def _g(m):\n    return round(m * 8)\n"
        "def to_grid(m):\n    return m * 8\n"
        "T = '20=585 21=738'\n"
    )
    (tmp_path / "packages" / "p" / "library.toml").write_text("[grid]\nmodule_mm = 2.5\n")
    found = scan(tmp_path)
    assert [f.split(": ")[0] for f in found] == [
        "packages/p/library.toml",
        "packages/p/src/p/a.py:1",
        "packages/p/src/p/a.py:3",
        "packages/p/src/p/a.py:5",
        "packages/p/src/p/a.py:6",
    ]


def test_the_scan_passes_a_read_of_the_name(tmp_path: Path) -> None:
    src = tmp_path / "packages" / "p" / "src" / "p"
    src.mkdir(parents=True)
    (src / "a.py").write_text("from e import G_PER_MODULE\ndef to_grid(m):\n    return m * G\n")
    assert scan(tmp_path) == []


def test_the_named_stock_is_still_there() -> None:
    for rel, (needle, count) in STOCK.items():
        assert (ROOT / rel).read_text().count(needle) == count, (
            f"{rel}: stock changed (GRID-HOME-B)"
        )


def test_the_models_record_of_the_factor_equals_the_library_grid() -> None:
    """The facade writes the library's grid into the model; `derive` reads the factor there."""
    from fransys._drawing_library import with_drawing_library

    from electrical_symbols import LIBRARY
    from fransys_model.derive.library_grid import divisions
    from fransys_model.kernel import Draft, freeze

    assert divisions(with_drawing_library(freeze(Draft()))) == LIBRARY.grid.divisions_per_module
