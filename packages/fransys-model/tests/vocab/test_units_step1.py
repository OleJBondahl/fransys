"""Units spec STEP 1: `Unit`, `Item.unit`, `Boundary`, `UnusedBoundary`, `UNIT_CYCLE`.

`docs/archive/specs/2026-09-22-units.md` U1, U3; `docs/decisions/model-0038-units.md`.
"""

from plant import Plant

from fransys_model.derive import unit_release
from fransys_model.kernel import Severity, dumps, loads, make_id
from fransys_model.vocab.core import Unit
from fransys_model.vocab.tables import boundaries, items, units, unused_boundaries
from fransys_model.vocab.units import Boundary, UnusedBoundary
from fransys_model.vocab.validators.structure import UNIT_CYCLE, check_structure


def test_a_unit_round_trips_through_canonical_form() -> None:
    """`Unit` carries `release` and `parent`; comes back equal and reachable."""
    plant = Plant()
    parent_id = plant.unit("board", name="demo-io-board", revision=1, interface="2")
    plant.revision(parent_id)
    child_id = plant.unit("cabinet", name="demo-pump-cabinet", parent=parent_id)
    plant.revision(child_id)
    model = plant.model()
    reloaded = loads(dumps(model))
    assert reloaded == model
    assert reloaded.digest == model.digest
    assert units(reloaded)[child_id].parent == parent_id
    assert unit_release(reloaded, parent_id).name == "demo-io-board"


def test_a_boundary_round_trips_through_canonical_form() -> None:
    """`Boundary` names the unit and the function; reachable through `boundaries(model)`."""
    plant = Plant()
    unit_id = plant.unit("board")
    plant.pin("x1", "conn", "1")
    function_id = Plant.function_id("x1", "conn")
    boundary = Boundary(
        id=make_id(Boundary, ("board", "x1")),
        key=("board", "x1"),
        unit=unit_id,
        function=function_id,
    )
    plant.add(boundary)
    model = plant.model()
    reloaded = loads(dumps(model))
    assert reloaded == model
    assert boundaries(reloaded)[boundary.id] == boundary
    assert boundaries(reloaded)[boundary.id].function == function_id


def test_an_unused_boundary_round_trips_through_canonical_form() -> None:
    """`UnusedBoundary` names the function the integrator leaves unconnected on purpose."""
    plant = Plant()
    plant.pin("t1", "term", "1")
    function_id = Plant.function_id("t1", "term")
    unused = UnusedBoundary(id=make_id(UnusedBoundary, ("t1",)), key=("t1",), function=function_id)
    plant.add(unused)
    model = plant.model()
    reloaded = loads(dumps(model))
    assert reloaded == model
    assert unused_boundaries(reloaded)[unused.id] == unused


def test_an_item_without_unit_still_loads_with_the_default() -> None:
    """`Item(...)` built with no `unit=` freezes, dumps `"unit": null`, and round-trips."""
    plant = Plant()
    plant.item("lone")
    model = plant.model()
    (item,) = items(model).values()
    assert item.unit is None
    text = dumps(model)
    assert '"unit": null' in text
    assert loads(text) == model


def test_a_two_unit_parent_loop_yields_exactly_one_unit_cycle() -> None:
    """Unit A's parent is unit B and B's parent is A: one `UNIT_CYCLE`, subjects both units."""
    a_id, b_id = make_id(Unit, ("a",)), make_id(Unit, ("b",))
    plant = Plant()
    release = plant.release("u")
    plant.add(
        Unit(id=a_id, key=("a",), release=release, parent=b_id),
        Unit(id=b_id, key=("b",), release=release, parent=a_id),
    )
    model = plant.model()
    findings = [f for f in check_structure(model) if f.code == UNIT_CYCLE]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.severity == Severity.ERROR
    assert set(finding.subjects) == {a_id, b_id}


def test_a_unit_parent_chain_with_no_loop_yields_no_unit_cycle() -> None:
    """Can-fail twin: the same two units, but the child's parent is the root, not a loop."""
    plant = Plant()
    root_id = plant.unit("root")
    child_id = plant.unit("child", parent=root_id)
    model = plant.model()
    # examined: two units, and the parent chain is a chain (not a self-loop)
    assert len(units(model)) == 2
    assert units(model)[child_id].parent == root_id
    assert units(model)[root_id].parent is None
    findings = [f for f in check_structure(model) if f.code == UNIT_CYCLE]
    assert findings == []
