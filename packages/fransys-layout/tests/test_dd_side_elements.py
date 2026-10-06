"""D1 (layout deep dive): a function is a side element only when every wired pole is a side pole.

Each design is a few contactors and a strip of terminals, built by `fr.build`; a test reads the
placements and the findings of the build.
"""

from typing import Any

from dd_chain_fixtures import build, placed
from test_dd_chains import XA1, XA2, XA3, XA4, _strip_of_terminals

from fransys_model.vocab.tables import functions

K1, K2 = ("K1", "fn", "main"), ("K2", "fn", "main")
# the contactors' coils are wired to nothing here: the only lone cells (an unwired aux is no cell)
COILS = [(k, "fn", "coil") for k in ("K1", "K2")]


def _lone_cells(result: Any) -> list[tuple[str, ...]]:
    """The function keys `LONE_CELL` names, sorted."""
    return sorted(
        functions(result.model)[subject].key
        for finding in result.findings
        if finding.code == "LONE_CELL"
        for subject in finding.subjects
    )


def test_a_function_with_a_strapped_pole_and_a_live_pole_is_a_side_element_nowhere() -> None:
    """D1 (F6-A2): K2's pole 1 is strapped to K1's, its pole 2 is live in its own chain.

    K1's pole 1 is wired XA:1 to XA:2; K2's pole 2 is wired XA:3 to XA:4. K2 stands in the column
    of its own chain, not beside K1, and no cell is left alone.
    """
    # UNDO: stages/_chain_sides.py _side_nowhere, count only the picked poles (no wired-pole check)
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    k1, k2 = (d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2"))
    wire(k1["1"], k2["1"])
    wire(k1["2"], k2["2"])
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    wire(t3.outer, k2["3"])
    wire(k2["4"], t4.inner)
    result = build(parts, d)
    model = result.model
    assert _lone_cells(result) == COILS
    first = tuple(placed(model, *key) for key in (XA1, K1, XA2))
    assert len({p.x for p in first}) == 1
    assert first[0].y < first[1].y < first[2].y
    second = tuple(placed(model, *key) for key in (XA3, K2, XA4))
    assert len({p.x for p in second}) == 1
    assert second[0].y < second[1].y < second[2].y
    assert second[1].x != first[1].x


def test_a_function_that_is_a_side_element_of_two_carriers_is_unplaced_in_no_column() -> None:
    """D1: K2, strapped to F1 and to K1 both, keeps a cell of its own and no finding names it."""
    # UNDO: none. A guard for the unmerge: it passed before EF-D Part 3b and no mutation of
    # `_side_nowhere` makes the columns pass raise this finding.
    parts, d, c, g, (t1, t2, t3, t4), wire = _strip_of_terminals(4)
    f1 = d.item("DEMO-MCB-C6", tag="F1", at=c, group=g)
    k1, k2 = (d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2"))
    wire(f1["1"], k2["1"])
    wire(f1["2"], k2["2"])
    wire(k1["1"], k2["3"])
    wire(k1["2"], k2["4"])
    wire(t1.outer, f1["1"])
    wire(f1["2"], t2.inner)
    wire(t3.outer, k1["1"])
    wire(k1["2"], t4.inner)
    result = build(parts, d)
    k2_function = placed(result.model, *K2).function
    named = [f for f in result.findings if k2_function in f.subjects]
    assert [f for f in named if f.code == "FUNCTION_UNPLACED_IN_COLUMN"] == []


def test_an_unwired_second_pole_leaves_the_function_a_side_element() -> None:
    """D1: K2's pole 1 is strapped to K1's, its pole 2 shares its nets with nothing.

    K1 is wired XA:1 to XA:2; K2 stands in K1's row, one lane over, and opens no column.
    """
    # UNDO: stages/_chain_sides.py _wired, `> 0` becomes `>= 0` (an unwired pole counts as wired)
    parts, d, c, g, (t1, t2), wire = _strip_of_terminals(2)
    k1, k2 = (d.item("DEMO-CTR-3P-24", tag=tag, at=c, group=g).fn("main") for tag in ("K1", "K2"))
    wire(k1["1"], k2["1"])
    wire(k1["2"], k2["2"])
    wire(t1.outer, k1["1"])
    wire(k1["2"], t2.inner)
    result = build(parts, d)
    model = result.model
    assert _lone_cells(result) == COILS
    k1_at, side = placed(model, *K1), placed(model, *K2)
    assert side.y == k1_at.y
    assert side.x != k1_at.x
    assert placed(model, *XA1).x == k1_at.x
