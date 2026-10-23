"""A fact over `Draft.tables()` equals the same fact over `freeze(draft)` (EL-MODEL design 7.4).

The facts that take a tables view are `unit_boundary_pins`, `boundary`, `unit_items`,
`crosses_unit`, `wired_ports` and `physical_nets`. Excluded, because they need what a freeze
resolves: any fact reading an alias, and any fact reading a catalogue kind (`PortTemplate`,
`InternalLink`, `Part`) the author's own draft does not hold. That list is `Draft.tables()`'s
contract.
"""

from types import SimpleNamespace

from plant import Plant

from fransys_model.derive.facts.boundary_pins import unit_boundary_pins
from fransys_model.derive.facts.children import unit_parent
from fransys_model.derive.facts.closure import physical_nets
from fransys_model.derive.facts.unit_reach import (
    nested_boundary_functions,
    unused_functions,
    wired_inside_outside,
)
from fransys_model.derive.facts.units import boundary, crosses_unit, unit_items
from fransys_model.derive.facts.wired_ports import wired_ports
from fransys_model.kernel import Draft, Origin, freeze
from fransys_model.vocab.tables import items, units

_ORIGIN = Origin(file="view.py", line=1, note="test")


def _draft() -> Draft:
    return _plant()[0]


def _plant() -> tuple[Draft, tuple[object, ...]]:
    """A cabinet holding a board: X1 passes up, one wire stays inside, one leaves, one mate."""
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    board = plant.unit("board", name="board", parent=cabinet)
    x1, x2, x3 = (plant.item(k, unit=u) for k, u in (("x1", board), ("x2", board), ("x3", cabinet)))
    f1, f2, f3 = (plant.function(i, n) for i, n in ((x1, "X1"), (x2, "X2"), (x3, "X3")))
    p1, p2, p3 = plant.port(f1, "1"), plant.port(f2, "1"), plant.port(f3, "1")
    plant.port(f1, "10")
    plant.port(f3, "10")  # joined to X1.10 by the mate alone
    plant.wire(p1, p2, key="inside")
    plant.wire(p2, p3, key="leaves")
    plant.boundary(board, f1, key="board-x1")
    plant.boundary(cabinet, f1, key="cabinet-x1")
    plant.mate(f1, f3)
    draft = Draft()
    draft.extend(plant.records, origin=_ORIGIN)
    return draft, (p1, p2, p3)


def test_every_view_fact_equals_the_frozen_fact() -> None:
    """Each fact over the draft's view gives what it gives over the frozen model."""
    draft = _draft()
    view, model = SimpleNamespace(tables=draft.tables()), freeze(draft)
    assert len(units(model)) == 2
    for unit in units(model):
        assert unit_boundary_pins(view, unit) == unit_boundary_pins(model, unit) != ()
        assert boundary(view, unit) == boundary(model, unit)
        assert unit_items(view, unit) == unit_items(model, unit)
    pairs = [(a, b) for a in items(model) for b in items(model)]
    assert {crosses_unit(view, a, b) for a, b in pairs} == {True, False}
    assert all(crosses_unit(view, a, b) == crosses_unit(model, a, b) for a, b in pairs)
    assert wired_ports(view) == wired_ports(model) != frozenset()
    assert physical_nets(view) == physical_nets(model)
    assert len(physical_nets(view)) < len(wired_ports(view)) + 1


def test_a_view_is_not_cached_and_sees_a_later_snapshot() -> None:
    """Two snapshots of a growing draft give two answers: a view has no digest to cache on."""
    draft = _draft()
    before = SimpleNamespace(tables=draft.tables())
    plant = Plant()
    plant.records = list(draft.records())
    extra = plant.item("late", unit=None)
    plant.port(plant.function(extra, "LATE"), "1")
    draft.extend(plant.records, origin=_ORIGIN)
    after = SimpleNamespace(tables=draft.tables())
    assert len(items(before)) + 1 == len(items(after))
    assert physical_nets(before) != physical_nets(after)


def test_a_view_missing_the_wires_differs_from_the_frozen_model() -> None:
    """The equality can fail: a view without the wires (the mate stays) has other nets."""
    draft = _draft()
    tables = {kind: table for kind, table in draft.tables().items() if kind != "conductor"}
    assert physical_nets(SimpleNamespace(tables=tables)) != physical_nets(freeze(draft))


def test_the_unit_reach_facts_agree_on_view_and_model_and_name_the_crossing() -> None:
    """`wired_inside_outside` splits the wires by unit, `nested_boundary_functions` lists X1."""
    draft = _draft()
    view, model = SimpleNamespace(tables=draft.tables()), freeze(draft)
    inside, outside = wired_inside_outside(view)
    assert (inside, outside) == wired_inside_outside(model)
    _, (p1, p2, p3) = _plant()
    assert (inside, outside) == (frozenset({p1, p2}), frozenset({p2, p3}))
    assert unused_functions(view) == unused_functions(model) == frozenset()
    cabinet = next(u for u in units(model) if unit_parent(model, u) is None)
    assert nested_boundary_functions(view, cabinet) == nested_boundary_functions(model, cabinet)
    assert len(nested_boundary_functions(view, cabinet)) == 1


def test_a_view_missing_the_mate_differs_from_the_frozen_model() -> None:
    """The mate alone joins X1.10 to X3.10: a view without mates has more physical nets."""
    draft = _draft()
    tables = {kind: table for kind, table in draft.tables().items() if kind != "mate"}
    assert physical_nets(SimpleNamespace(tables=tables)) != physical_nets(freeze(draft))
