"""The font family, its ratios, its text heights and its TTFs are named once (GRID-HOME G7).

Outside `electrical-symbols` (and the symdef toolkit), no source types a font family name, a
`.ttf` file name, a font ratio (capital, ascent or descender over the em) or a text height as a
literal. The two sheet-profile defaults in `layout/formats.py` are named stock: their fate is
GRID-HOME-B. The model's generated advance table is the one allowed file (MODEL-TEXT).
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = "packages/electrical-symbols/"
FAMILY = re.compile(r"^DejaVu\b[\w ]*$")
RATIOS = (1493 / 2048, 1556 / 2048, 426 / 2048)
HEIGHT_NAMES = {"text_height_mm", "min_text_height_mm"}
ALLOWED_FILES = {"packages/fransys-model/src/fransys_model/derive/_text_widths.py"}
# Named stock: the sheet profile's own default heights, until GRID-HOME-B reads the record.
STOCK = {"packages/fransys-model/src/fransys_model/layout/formats.py": 2}


def _near_ratio(text: str) -> bool:
    try:
        value = float(text)
    except ValueError:
        return False
    return any(abs(value - ratio) < 1e-3 for ratio in RATIOS)


def _constant_kind(value: object) -> str | None:
    if isinstance(value, str):
        if FAMILY.match(value):
            return "a font family"
        if value.endswith(".ttf"):
            return "a TTF name"
        return "a font ratio" if _near_ratio(value) else None
    if isinstance(value, float) and _near_ratio(str(value)):
        return "a font ratio"
    return None


def _node_kind(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant):
        return _constant_kind(node.value)
    if isinstance(node, ast.Assign | ast.AnnAssign):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        named = {getattr(t, "id", "") for t in targets} & HEIGHT_NAMES
        return "a text height" if named and node.value is not None else None
    if isinstance(node, ast.JoinedStr):
        text = "".join(str(p.value) for p in node.values if isinstance(p, ast.Constant))
        return "a font family" if re.search(r'font: "[A-Za-z]', text) else None
    return None


def font_hits(source: str) -> list[tuple[int, str]]:
    """Each typed family, TTF name, ratio or text height in `source`: `(line, kind)`."""
    found = ((getattr(n, "lineno", 0), _node_kind(n)) for n in ast.walk(ast.parse(source)))
    return sorted({(line, kind) for line, kind in found if kind})


def scan(root: Path) -> list[str]:
    """Every violation under `root/packages/*/src`, as `file:line: what`."""
    found: list[str] = []
    for path in sorted((root / "packages").glob("*/src/**/*.py")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(HOME) or rel in ALLOWED_FILES:
            continue
        for line, kind in font_hits(path.read_text()):
            found.append(f"{rel}:{line}: {kind}; the one home is {HOME}")
    return [f for f in found if _not_stock(f)]


def _not_stock(found: str) -> bool:
    rel = found.split(":", maxsplit=1)[0]
    return not (rel in STOCK and "a text height" in found)


def test_the_font_facts_have_one_home() -> None:
    assert scan(ROOT) == []


def test_the_scan_flags_each_typed_font_fact(tmp_path: Path) -> None:
    src = tmp_path / "packages" / "p" / "src" / "p"
    src.mkdir(parents=True)
    (src / "a.py").write_text(
        'F = "DejaVu Sans"\n'
        'T = "x/Face.ttf"\n'
        "R = 0.7290\n"
        "S = f'#set text(font: \"Other\", size: {1})'\n"
        'text_height_mm = Decimal("1.8")\n'
    )
    found = scan(tmp_path)
    assert [f.split(": ")[1].split(";")[0] for f in found] == [
        "a font family",
        "a TTF name",
        "a font ratio",
        "a font family",
        "a text height",
    ]


def test_the_scan_passes_a_read_through_the_record(tmp_path: Path) -> None:
    src = tmp_path / "packages" / "p" / "src" / "p"
    src.mkdir(parents=True)
    (src / "a.py").write_text("def f(model):\n    return font_family(model)\n")
    assert scan(tmp_path) == []


def test_the_named_stock_is_still_there() -> None:
    for rel, count in STOCK.items():
        hits = [k for _, k in font_hits((ROOT / rel).read_text()) if k == "a text height"]
        assert len(hits) == count, f"{rel}: stock changed (GRID-HOME-B)"
