"""S12's list (layout-0090): `side_by_side` is gone, and the one end it kept stays a wire.

The only end `side_by_side` wired on the goldens, the example and the field cases was
cabinet_narrow's `-S2:11` to `-X2:1`: consecutive rows of one column, D1's first wire case (an
adjacent cell), which `references.joins` decides from `columns` alone. `-X2:1` is its star net's
reference, with markers on the pages where the net's other ports stand apart; on the page the
wire is drawn it carries none.
"""

import ast
from collections import defaultdict
from pathlib import Path

from layout_cabinet import build_cabinet
from narrow_cabinet import narrow_results

from fransys_layout.stages import boxes
from fransys_model.derive.designation import port_designation
from fransys_model.kernel import freeze
from fransys_model.vocab.tables import ports

SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "fransys_layout"
_NARROW_WIDTH_MM = 158


def _ports_named(*names: str) -> list[set]:
    """The model ports each designation names (a terminal's two ports share one)."""
    model = freeze(build_cabinet())  # the narrow sheet changes no id
    found = defaultdict(set)
    for port in ports(model):
        found[port_designation(model, port)].add(port)
    return [found[name] for name in names]


def test_s2_11_to_x2_1_is_a_wire_decided_through_columns_alone() -> None:
    """The conductor is routed on one page, `-S2:11` carries no marker, `-X2:1` none there."""
    # CAN-FAIL (S12's probe): stages/references/joins.py `wired_beside`,
    #     `abs(x.cell - y.cell) == 1` -> `== 2`: the end becomes a reference and this fails
    results, _ = narrow_results(_NARROW_WIDTH_MM)
    s2, x2 = _ports_named("-S2:11", "-X2:1")
    (route,) = (r for r in results.layout.routes if {r.a, r.b} & s2 and {r.a, r.b} & x2)
    page = (route.drawing_set, route.page)
    markers = results.layout.markers
    assert not [m for m in markers if m.port in s2]
    assert not [m for m in markers if m.port in x2 and (m.drawing_set, m.page) == page]


def test_side_by_side_and_its_beside_builder_are_gone_from_boxes() -> None:
    """`boxes.py` has no `side_by_side`, and no module imports or calls it."""
    # CAN-FAIL: add `def side_by_side(): ...` to stages/boxes.py and the first assert fails
    assert not hasattr(boxes, "side_by_side")
    assert not hasattr(boxes, "Beside")
    found = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            named = [alias.name for alias in node.names] if isinstance(node, ast.ImportFrom) else []
            called = isinstance(node, ast.Call) and getattr(node.func, "id", "") == "side_by_side"
            if "side_by_side" in named or called:
                found.append(path.relative_to(SRC_ROOT).as_posix())
    assert found == []
