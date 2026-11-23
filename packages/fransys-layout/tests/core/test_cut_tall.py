"""CUT-TALL: a column more than two pages tall is cut into as many pieces as it needs."""

from __future__ import annotations

import pytest
from options_fixtures import core_options

from fransys_layout.core.cut_tall import Tall, _wires
from fransys_layout.core.errors import CoreError
from fransys_layout.core.flow_values import Cell, Column, End, Lane
from fransys_layout.core.values import PinRef, RefKind

from .cut_fixtures import chain, cut_of, elem, net

PAGE_H = 822


@pytest.mark.rule("PAGE-CUT")
def test_a_column_of_four_pages_is_cut_into_pieces_that_each_fit_one() -> None:
    """Thirty cells of 96 G stack to 3112 G: no two cuts make the pieces fit, so there are more."""
    ids = [f"k{i:02d}" for i in range(30)]
    result = cut_of([elem(i, 40, 96) for i in ids], chain(ids))
    columns = result.flow.columns
    assert [c.id for c in columns] == [f"c:k00#{chr(97 + k)}" for k in range(len(columns))]
    assert len(columns) >= 4
    assert all(c.height <= PAGE_H for c in columns)
    assert [cell.sym for c in columns for cell in c.lanes[0].cells] == ids
    tags = [r for r in result.spec.reference_plan if r.kind is RefKind.TAG]
    assert len(tags) == len(columns) - 1
    assert not [f for f in result.spec.findings if f.code == "PAGE_OVERFLOW"]


def test_every_piece_of_a_cut_column_has_one_head_and_one_foot_per_lane() -> None:
    """KI-836: one element in parallel with k10 is a member lane shorter than the chain; the cut left it no foot, and the last piece two."""
    ids = [f"k{i:02d}" for i in range(30)]
    nets = [n for n in chain(ids) if n.id not in ("x9", "x10")]
    nets += [net("x9", "k09.s", "k10.n", "m.n"), net("x10", "k10.s", "k11.n", "m.s")]
    result = cut_of([*(elem(i, 40, 96) for i in ids), elem("m", 40, 96)], nets)
    shapes = [(len(c.lanes), len(c.heads), len(c.feet)) for c in result.flow.columns]
    assert len(result.flow.columns) > 2
    assert any(lanes == 2 for lanes, _, _ in shapes)
    assert all(lanes == heads == feet for lanes, heads, feet in shapes)


def test_a_cut_between_cells_with_no_shared_net_is_refused_not_tagged_with_an_empty_net() -> None:
    """F1 row 7: `net_of.get(pin, "")` made a TAG with net "", a reference pair with no conductor; the cut now names the cells."""
    cells = (Cell("a", "R0", "n", "s"), Cell("b", "R0", "n", "s"))
    col = Column("c:a", (Lane(cells, 0),), (End("open"),), (End("open"),), 0, 0)
    joined = net("x", "a.s", "b.n")
    ok = Tall({}, core_options(), 0, 0, dict.fromkeys(joined.pins, "x"), {"x": joined.pins}, {}, {}, ())
    assert _wires(col, 0, 1, ok) == (("x", PinRef("a", "s"), PinRef("b", "n")),)
    for net_of in ({}, {PinRef("a", "s"): "x"}, {PinRef("a", "s"): "x", PinRef("b", "n"): "y"}):
        apart = Tall({}, core_options(), 0, 0, net_of, {}, {}, {}, ())
        with pytest.raises(CoreError, match="cells a and b of lane 0 in column c:a share no net"):
            _wires(col, 0, 1, apart)
