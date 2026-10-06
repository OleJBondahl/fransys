"""Page skeleton: sheet resolution, number formatting, no `float` in the package (PART 1)."""

import ast
from decimal import Decimal
from pathlib import Path

import pytest
from fransys_render import pages
from fransys_render._numbers import format_decimal

from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.layout import DrawingSet, Page, PageRole, SheetFormat

_ORIGIN = Origin(
    file="packages/fransys-render/tests/test_pages_skeleton.py", line=1, note="invented page"
)


def _model(*records):
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _drawing_set(key_part, *, number=1):
    key = ("drawing_set", key_part)
    return DrawingSet(
        id=make_id(DrawingSet, key), key=key, location=None, number=number, produced_by="test"
    )


def _page(key_part, *, drawing_set, number=1, sheet_format=None):
    key = ("page", key_part)
    return Page(
        id=make_id(Page, key),
        key=key,
        drawing_set=drawing_set.id,
        number=number,
        role=PageRole.CONTROL,
        sheet_format=sheet_format,
        groups=(),
        produced_by="test",
    )


def _sheet_format(key_part, *, width_mm, height_mm):
    key = ("sheet_format", key_part)
    return SheetFormat(
        id=make_id(SheetFormat, key),
        key=key,
        name=key_part,
        width_mm=width_mm,
        height_mm=height_mm,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=width_mm - 20,
        content_height_mm=height_mm - 40,
        frame_columns=6,
        frame_rows=4,
        module_mm=Decimal("2.5"),
    )


# --- format_decimal (D5): no exponent, no trailing zeros, no signed zero -------------------

FORMAT_DECIMAL_CASES = [
    (Decimal("1E+1"), "10"),
    (Decimal("2.50"), "2.5"),
    (Decimal("-3.00"), "-3"),
    (Decimal(0), "0"),
    (Decimal("0.30"), "0.3"),
    (Decimal("12.1000"), "12.1"),
    # A signed zero collapses to plain "0" (never "-0"): `normalized == 0` compares equal for
    # every zero shape regardless of sign, but only when that branch actually runs -- the one
    # id (mutmut_11: `normalized == 0` -> `normalized == 1`) this case kills.
    (Decimal("-0"), "0"),
    (Decimal("-0.0"), "0"),
]


@pytest.mark.parametrize(("value", "expected"), FORMAT_DECIMAL_CASES)
def test_format_decimal(value, expected):
    assert format_decimal(value) == expected


# --- sheet resolution (D5, D9): the house sheet vs. an authored one, exactly and distinctly -

_HOUSE_VIEWBOX = 'viewBox="0 0 420 297"'


def test_default_sheet_format_gives_house_viewbox():
    drawing_set = _drawing_set("a")
    page = _page("a", drawing_set=drawing_set, sheet_format=None)
    model = _model(drawing_set, page)

    svgs = pages(model)

    assert len(svgs) == 1
    svg = next(iter(svgs.values()))
    assert _HOUSE_VIEWBOX in svg


def test_authored_sheet_format_gives_its_own_distinct_viewbox():
    drawing_set = _drawing_set("b")
    sheet = _sheet_format("b", width_mm=300, height_mm=200)
    page = _page("b", drawing_set=drawing_set, sheet_format=sheet.id)
    model = _model(drawing_set, sheet, page)

    svgs = pages(model)

    assert len(svgs) == 1
    svg = next(iter(svgs.values()))
    authored_viewbox = 'viewBox="0 0 300 200"'
    assert authored_viewbox in svg
    assert authored_viewbox != _HOUSE_VIEWBOX


# --- no `float` anywhere in the package (D5), proven with an AST scan ----------------------

_PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src" / "fransys_render"


def _float_findings(path: Path) -> list[str]:
    """Every `float` literal or `float(...)` call in `path`, as `"path:line"` strings."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            findings.append(f"{path}:{node.lineno}")
        is_float_call = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "float"
        )
        if is_float_call:
            findings.append(f"{path}:{node.lineno}")
    return findings


def _walk_for_floats(root: Path) -> tuple[int, list[str]]:
    """Its own directory walk (`Path.walk`, not `Path.glob`): files visited, and findings."""
    visited = 0
    findings: list[str] = []
    for dirpath, _dirnames, filenames in root.walk():
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            visited += 1
            findings.extend(_float_findings(dirpath / filename))
    return visited, findings


def test_no_float_in_package():
    # Independent of `_walk_for_floats`'s traversal: a recursive glob, not a manual walk, so
    # a scope bug in one cannot hide behind the same bug in the other.
    expected_files = sorted(_PACKAGE_SRC.glob("**/*.py"))
    assert len(expected_files) > 0

    visited, findings = _walk_for_floats(_PACKAGE_SRC)

    assert visited == len(expected_files)
    assert findings == []


def test_float_scanner_can_fail_on_a_synthetic_fixture(tmp_path):
    fixture = tmp_path / "has_float.py"
    fixture.write_text("x = 1.0\n", encoding="utf-8")

    findings = _float_findings(fixture)

    assert findings == [f"{fixture}:1"]
