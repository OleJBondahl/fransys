"""`HARNESS_END_AMBIGUOUS` also reads a unit-owned cable as its unit's document does (model-0090).

`unit_cables` prints unit-relative: a board unit's drawing drops the board's tag, so two ends whose
absolute texts differ (`+C1-A1-X1`, `+C1-X1`) can both print `-X1` there, and WireViz would merge
them into one node. An end outside a nested unit reads `""`, which is never a collision (two
untitled nodes on purpose, wireviz-0009). Invented data throughout; the pass is run directly.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from plant import Plant
from query_builders import make_core, make_node, make_placement, make_terminal

from fransys_model.derive.harness import all_cables, all_unit_cables
from fransys_model.derive.passes.numbering import HARNESS_END_AMBIGUOUS, number
from fransys_model.kernel import Severity, make_id
from fransys_model.vocab.facets.cable import CableFacet

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id
    from fransys_model.vocab.core import Item, Port, Unit


@dataclass(frozen=True)
class _Design:
    plant: Plant
    w3: Id[Item]
    w4: Id[Item]
    plug: Id[Item]
    cabinet_x1: Id[Item]


def _cable(
    plant: Plant, key: str, tag: str, *, unit: Id[Unit] | None, parent: Id[Item] | None = None
) -> Id[Item]:
    """A cable `tag` in `unit`, in `parent` when given."""
    item = plant.item(key, designation=tag, parent=parent, unit=unit)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=item,
            length_mm=None,
        )
    )
    return item


def _pin(plant: Plant, item: Id[Item]) -> Id[Port]:
    """The one port `1` of `item`'s one function."""
    return plant.port(plant.function(item, "f"), "1")


def _findings(plant: Plant) -> list[Finding]:
    """The pass's `HARNESS_END_AMBIGUOUS` findings only."""
    _, findings = number(plant.model())
    return [finding for finding in findings if finding.code == HARNESS_END_AMBIGUOUS]


def _design(*, cabinet_at: str | None = None) -> _Design:
    """The reviewer's model: a top-level board unit `bu`, root `A1` at `+C1`.

    `W3` (child of `A1`, in `bu`) runs the board's plug `X1` to a cabinet connector `X1` in no
    unit and, by default, no location: absolute ends `+C1-A1-X1` and `-X1`, unit-relative both
    `-X1`. `W4` (in `bu` too) runs the board's `K1` to a cabinet `X2`: `-K1` and `-X2`, distinct
    either way. With `cabinet_at="c1"` the cabinet is at `+C1`, and its end prints `+C1-X1`.
    """
    plant = Plant()
    c1 = make_node("c1", None)
    plant.add(c1)
    bu = plant.unit("bu", name="bu")
    board = plant.item("a1", designation="A1", part=plant.board_part(), unit=bu)
    plug = plant.item("x1", designation="X1", parent=board, unit=bu)
    k1 = plant.item("k1", designation="K1", parent=board, unit=bu)
    cabinet_x1 = plant.item("cab-x1", designation="X1")
    cabinet_x2 = plant.item("cab-x2", designation="X2")
    placed = (board, plug, k1) if cabinet_at is None else (board, plug, k1, cabinet_x1, cabinet_x2)
    for number_, item in enumerate(placed):
        plant.add(make_placement(f"placed-{number_}", item, c1.id))
    w3 = _cable(plant, "w3", "W3", unit=bu, parent=board)
    w4 = _cable(plant, "w4", "W4", unit=bu, parent=board)
    make_core(plant, "c3", w3, (_pin(plant, plug), _pin(plant, cabinet_x1)), index=1)
    make_core(plant, "c4", w4, (_pin(plant, k1), _pin(plant, cabinet_x2)), index=1)
    return _Design(plant, w3, w4, plug, cabinet_x1)


def test_ends_equal_only_in_the_units_reading_are_ambiguous() -> None:
    """Absolute `+C1-A1-X1` / `-X1` differ, the board unit's `-X1` twice do not: one finding."""
    design = _design()
    absolute = {cable.cable: cable for cable in all_cables(design.plant.model())}[design.w3]
    assert [end.designation for end in absolute.ends] == ["+C1-A1-X1", "-X1"]
    in_unit = {cable.cable: cable for cable in all_unit_cables(design.plant.model())}[design.w3]
    assert [end.designation for end in in_unit.ends] == ["-X1", "-X1"]
    (finding,) = _findings(design.plant)
    assert finding.severity == Severity.ERROR
    assert set(finding.subjects) == {design.w3, design.plug, design.cabinet_x1}
    assert finding.message == (
        "two ends of -W3 print '-X1' in its unit's document; "
        "place the unit instances at locations or tag the strips apart"
    )


def test_a_located_end_outside_the_unit_prints_its_path_so_it_is_not_ambiguous() -> None:
    """FAR-END-ONE-HOME A2: the cabinet's `+C1-X1` differs from the board's `-X1`: no finding."""
    design = _design(cabinet_at="c1")
    in_unit = {cable.cable: cable for cable in all_unit_cables(design.plant.model())}[design.w3]
    assert [end.designation for end in in_unit.ends] == ["-X1", "+C1-X1"]
    assert _findings(design.plant) == []


def test_a_cable_with_distinct_ends_in_its_unit_reading_is_not_reported() -> None:
    """`W4` reads `-K1` and `-X2` in `bu`'s document: only `W3` is in the findings."""
    design = _design()
    assert all(design.w4 not in finding.subjects for finding in _findings(design.plant))


def test_two_blank_ends_outside_a_nested_unit_are_not_a_collision() -> None:
    """A cable of the nested unit `bu` running between two items in no unit: both read `""`."""
    plant = Plant()
    cabinet = plant.unit("cabinet")
    bu = plant.unit("bu", parent=cabinet)
    left = plant.item("left", designation="P1")
    right = plant.item("right", designation="Q1")
    cable = _cable(plant, "w1", "W1", unit=bu)
    make_core(plant, "c1", cable, (_pin(plant, left), _pin(plant, right)), index=1)
    (read,) = all_unit_cables(plant.model())
    assert [end.designation for end in read.ends] == ["", ""]
    assert _findings(plant) == []


def test_a_cable_that_collides_in_both_readings_gives_one_finding() -> None:
    """Two units' unplaced `X1` strips print `-X1` absolute and in the top-level unit `u`."""
    plant = Plant()
    unit_a = plant.unit("cab-a")
    unit_b = plant.unit("cab-b")
    unit_u = plant.unit("cab-u")
    x1_a = plant.item("x1-a", designation="X1", unit=unit_a)
    x1_b = plant.item("x1-b", designation="X1", unit=unit_b)
    l1_a = make_terminal(plant, "x1-a", "t1", group="L", index=1)
    l1_b = make_terminal(plant, "x1-b", "t1", group="L", index=1)
    cable = _cable(plant, "w1", "W1", unit=unit_u)
    make_core(plant, "core", cable, (l1_a.external, l1_b.external), index=1)
    (in_unit,) = all_unit_cables(plant.model())
    assert [end.designation for end in in_unit.ends] == ["-X1", "-X1"]
    (finding,) = _findings(plant)
    assert set(finding.subjects) == {cable, x1_a, x1_b}
    assert finding.message == (
        "two ends of -W1 print '-X1'; place the unit instances at locations or tag the strips apart"
    )
