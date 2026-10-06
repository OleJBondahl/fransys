"""WP17 tests beyond the goldens: the two designs are healthy and say what they set out to.

The golden files pin every byte; these tests pin the reasons: no validator complains, the
PLC bindings are the ones the pass would choose, the numbering pass handles the unnumbered
cable, and the closure runs from a remote sensor into the board.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from cabinet import build_cabinet
from harness_board import build_harness_board

from fransys_model.derive import (
    allocate_plc,
    bom_lines,
    designation_list,
    net_of,
    number,
    terminal_rows,
)
from fransys_model.derive.designation import own_designation_or_none
from fransys_model.kernel import Id, Model, Severity, dumps, evolve, freeze, merge
from fransys_model.vocab import ALL_VALIDATORS
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.facets.cable import CoreFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.tables import conductors, facets_of, items, ports
from fransys_model.vocab.validators import check_cables

if TYPE_CHECKING:
    from fransys_model.vocab.core import Item, Port


_GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"


def _design(name: str) -> Model:
    """The frozen design called `name`: `cabinet`, `harness_board` or their `merged` union."""
    match name:
        case "cabinet":
            return freeze(build_cabinet())
        case "harness_board":
            return freeze(build_harness_board())
        case _:
            return freeze(merge(build_cabinet(), build_harness_board()))


def _item(model: Model, designation: str) -> Item:
    (found,) = (
        i for i in items(model).values() if own_designation_or_none(model, i) == designation
    )
    return found


def _port(model: Model, *key: str) -> Id[Port]:
    (found,) = (p.id for p in ports(model).values() if p.key == key)
    return found


def test_a_one_record_change_shows_in_the_canonical_json_and_the_digest() -> None:
    """The golden comparison can fail: drop the `scaling` facet of `B1` and both differ."""
    model = _design("cabinet")
    (scaling,) = facets_of(model, ScalingFacet).values()
    changed = evolve(model, remove=[scaling.id])
    golden = (_GOLDEN_DIR / "cabinet.json").read_text(encoding="utf-8")
    golden_digest = (_GOLDEN_DIR / "cabinet.digest").read_text(encoding="utf-8").strip()
    assert dumps(model) == golden
    assert dumps(changed) != golden
    assert model.digest == golden_digest
    assert changed.digest != golden_digest


@pytest.mark.parametrize("name", ["cabinet", "harness_board", "merged"])
def test_no_validator_reports_a_warning_or_an_error(name: str) -> None:
    """Only `INFO` findings remain: spare pins, part-less containers, unused channels."""
    model = _design(name)
    findings = [f for check in ALL_VALIDATORS for f in check(model)]
    assert [f for f in findings if f.severity is not Severity.INFO] == []
    assert findings, "the designs keep some INFO findings, so an empty list means a broken check"


def test_the_part_less_harness_is_one_info_finding_and_nothing_else() -> None:
    """Decision 0026: harness `WH1` has no part, which is `ITEM_WITHOUT_PART` at `INFO` alone."""
    model = _design("harness_board")
    harness = _item(model, "WH1")
    on_harness = [f for check in ALL_VALIDATORS for f in check(model) if harness.id in f.subjects]
    assert [(f.code, f.severity) for f in on_harness] == [("ITEM_WITHOUT_PART", Severity.INFO)]
    children = {
        own_designation_or_none(model, child)
        for child in items(model).values()
        if child.parent == harness.id
    }
    assert children == {"H1", None}


def test_the_cable_validator_can_fail_on_the_cabinet() -> None:
    """Removing one core of `W1` gives `CABLE_CORE_COUNT`, so a clean run means something."""
    model = _design("cabinet")
    w1 = _item(model, "W1").id
    core = next(c for c in conductors(model).values() if c.carrier == w1)
    facet = next(f for f in facets_of(model, CoreFacet).values() if f.subject == core.id)
    broken = evolve(model, remove=[facet.id, core.id])
    assert [f.code for f in check_cables(broken)] == ["CABLE_CORE_COUNT"]
    assert check_cables(model) == ()


def test_allocation_finds_nothing_to_bind_on_the_cabinet() -> None:
    """Every request already has its binding, so the pass returns the same model, silently."""
    model = _design("cabinet")
    allocated, findings = allocate_plc(model)
    assert allocated is model
    assert findings == ()


def test_allocation_reproduces_the_authored_bindings() -> None:
    """Remove the three bindings: the pass binds the same channels again, digest for digest."""
    model = _design("cabinet")
    bindings = list(facets_of(model, PlcBindingFacet).values())
    assert len(bindings) == 3
    stripped = evolve(model, remove=[b.id for b in bindings])
    assert stripped.digest != model.digest
    allocated, findings = allocate_plc(stripped)
    assert findings == ()
    assert allocated.digest == model.digest


def test_the_cabinet_fixtures_module_pins_are_distinct_and_number_reports_none() -> None:
    """Each channel's pins are numbered distinctly, so numbering finds no duplicate (0077)."""
    # MUTATION: a module's channel pins repeat again (e.g. drop the per-channel numbering,
    # giving two channels the same pin text): this test fails with PORT_DESIGNATION_DUPLICATE
    _, findings = number(_design("cabinet"))
    assert findings == ()


def test_numbering_counts_the_fan_out_cable_within_its_harness_not_beside_the_cabinet() -> None:
    """The sibling group is the scope: under harness `WH1` the cable is `W1` in either design."""
    for name in ("harness_board", "merged"):
        numbered, findings = number(_design(name))
        assert findings == ()
        fan_out = next(i for i in items(numbered).values() if i.key == ("w-fanout",))
        assert own_designation_or_none(numbered, fan_out) == "W1"
        assert fan_out.tag is None
    unnumbered = _design("harness_board")
    fan_out = next(i for i in items(unnumbered).values() if i.key == ("w-fanout",))
    assert own_designation_or_none(unnumbered, fan_out) is None


def test_the_two_f1_fuses_sit_under_different_parents_and_numbering_accepts_both() -> None:
    """Same designation, different items: `DESIGNATION_DUPLICATE` is about siblings only."""
    merged = _design("merged")
    fuses = [i for i in items(merged).values() if own_designation_or_none(merged, i) == "F1"]
    assert {i.parent is None for i in fuses} == {True, False}
    _, findings = number(merged)
    assert findings == ()


def test_the_spare_contactor_is_listed_but_not_in_the_bom() -> None:
    """`K3` stays in the designation list, and `SIM-CONTACTOR-9A-1NO` counts `K1` only."""
    cabinet = _design("cabinet")
    assert "-K3" in {row.designation for row in designation_list(cabinet)}
    (line,) = (line for line in bom_lines(cabinet) if line.mpn == "SIM-CONTACTOR-9A-1NO")
    assert (line.count, line.designations) == (1, ("-K1",))


def test_the_l1_terminals_share_a_jumper_group_and_the_others_have_none() -> None:
    """The jumper bridges the two `L1` terminals of `X1`, and only those."""
    cabinet = _design("cabinet")
    rows = terminal_rows(cabinet, _item(cabinet, "X1").id)
    assert [(r.group, r.index, r.jumper_group) for r in rows] == [
        ("L1", 1, 1),
        ("L1", 2, 1),
        ("L2", 1, None),
        ("L3", 1, None),
        ("PE", 1, None),
    ]
    jumpers = [c for c in conductors(cabinet).values() if c.kind is ConductorKind.JUMPER]
    assert len(jumpers) == 1


def test_a_sensor_is_on_the_board_net_through_the_harness_core_and_the_mate() -> None:
    """design/examples.md 11: from `B10`, through core 1 and the mate, to the
    board-edge pin `J1:1`."""
    model = _design("harness_board")
    net = net_of(model, _port(model, "b10", "signal", "signal"))
    assert net is not None
    assert _port(model, "jb1", "fn", "J1", "port", "1") in net.ports
    assert _port(model, "h1", "fn", "P1", "port", "1") in net.ports
