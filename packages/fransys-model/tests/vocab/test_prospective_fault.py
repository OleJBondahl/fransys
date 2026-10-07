"""`prospective_fault`: the fault current at each protective position (RATINGS-3 R7 to R10, R17).

Expected values are written by hand from the spec's worked example and acceptance 1-3, 7, 11
and 14-16. Every fuse stands on rails through a net of a supply declared by pins, so it reaches
a current kind; modules are two-port sources with no current limit (Q4).
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from current_plant import changeover, device, fuse, hub, run, wire
from fault_plant import breaker, into, module
from plant import Plant
from rating_plant import AC_400, rail, supply

from fransys_model.kernel import make_id
from fransys_model.vocab.core import Port, Unit
from fransys_model.vocab.current_graph import raw_of
from fransys_model.vocab.enums import Current, FunctionKind
from fransys_model.vocab.fault_graph import fault_graph
from fransys_model.vocab.membership import standalone
from fransys_model.vocab.prospective_fault import ProspectiveFault, prospective_fault
from fransys_model.vocab.supply_system import SupplySystem

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id, Model

_DC = {"B+": rail("51.2"), "B-": rail("0")}
_S = {"S+": rail("24"), "S-": rail("0")}


def _fn(key: str) -> Id:
    return Plant.function_id(key, "f")


def _at(model: Model, key: str) -> ProspectiveFault:
    """The one entry of the position whose function is item `key`'s `f`."""
    (found,) = (f for f in prospective_fault(model) if f.position.functions == (_fn(key),))
    return found


def _bus(plant: Plant) -> tuple[Id[Port], Id[Port]]:
    """The plus and minus bus hubs, on the rails of a battery bus declared with no fault current."""
    plus, minus = hub(plant, "P"), hub(plant, "M")
    plant.net("bus+", (plus,), potential="B+")
    plant.net("bus-", (minus,), potential="B-")
    supply(plant, "bat", _DC, current=Current.DC, pins=(plus, minus))
    return plus, minus


def _battery(strings: Sequence[Sequence[str | None]], tc: str | None = "2") -> Model:
    """String `i` of modules (fault currents) through fuse `SF{i}` to the plus bus; main `FM`.

    The last module of the first string states the time constant `tc`, every other one 2 ms.
    """
    plant = Plant()
    plus, minus = _bus(plant)
    for at, faults in enumerate(strings):
        last = len(faults) - 1
        modules = [
            module(plant, f"m{at}{n}", fault, tc if (at, n) == (0, last) else "2")
            for n, fault in enumerate(faults)
        ]
        run(plant, minus, [*modules, fuse(plant, f"SF{at}", "125")], plus)
    main = fuse(plant, "FM", "125")
    load = device(plant, "Z", kind=FunctionKind.LOAD)
    run(plant, plus, [main, load], minus)
    return plant.model()


def test_worked_example_string_fuses_read_12000_and_the_main_fuse_18000() -> None:
    """Acceptance 1: a string fuse counts the other two strings, never its own one through it."""
    model = _battery([["6000"] * 4] * 3)
    for own in range(3):
        string = _at(model, f"SF{own}")
        assert (string.kind, string.current_a, string.time_constant_ms) == (
            Current.DC,
            Decimal(12000),
            Decimal(2),
        )
        others = (s for s in range(3) if s != own)
        assert string.functions == tuple(sorted(_fn(f"m{s}{n}") for s in others for n in range(4)))
        assert string.supplies == ()
    main = _at(model, "FM")
    assert (main.current_a, main.time_constant_ms) == (Decimal(18000), Decimal(2))
    assert len(main.functions) == 3 * 4


def test_a_run_counts_at_its_largest_member() -> None:
    """Acceptance 2: strings 6000 + 9000 and 6000 in parallel give 9000 + 6000, not 21000."""
    model = _battery([["6000", "9000"], ["6000"]])
    assert _at(model, "FM").current_a == Decimal(15000)
    assert _at(model, "SF1").current_a == Decimal(9000)


def test_a_counted_source_with_no_fault_current_makes_the_value_unknown() -> None:
    """Acceptance 3: one module states no fault current, so every fuse it reaches reads `None`."""
    model = _battery([["6000", None], ["6000"]])
    main = _at(model, "FM")
    assert (main.current_a, main.time_constant_ms) == (None, Decimal(2))
    assert _at(model, "SF0").current_a is None
    assert _at(model, "SF1").current_a is None


def test_a_counted_dc_source_with_no_time_constant_makes_it_unknown() -> None:
    """R10: one module states no time constant, so the main fuse keeps 18000 A at `None` ms."""
    main = _at(_battery([["6000"] * 4] * 3, tc=None), "FM")
    assert (main.current_a, main.time_constant_ms) == (Decimal(18000), None)


def test_a_three_phase_supply_counts_once_at_each_pole() -> None:
    """Acceptance 7: a 10000 A grid on L1 L2 L3 N gives each breaker pole 10000 A, not 30000."""
    plant = Plant()
    pins = [hub(plant, name) for name in AC_400]
    for name, pin in zip(AC_400, pins, strict=True):
        plant.net(f"grid-{name}", (pin,), potential=name)
    grid = supply(plant, "grid", AC_400, pins=pins, fault_current_a=Decimal(10000))
    poles = breaker(plant, "Q")
    for pin, (line, _) in zip(pins, poles, strict=False):
        wire(plant, pin, line)
    found = prospective_fault(plant.model())
    assert len(found) == len(poles)
    assert {frozenset(f.position.ports) for f in found} == set(map(frozenset, poles))
    assert {(f.kind, f.current_a, f.time_constant_ms, f.supplies) for f in found} == {
        (Current.AC, Decimal(10000), None, (grid,))
    }


def test_a_changeover_counts_its_larger_throw_never_both() -> None:
    """Acceptance 11: a load switched between sources of 6000 A and 9000 A reads 9000 A."""
    plant = Plant()
    common, make, brk = changeover(plant, "CO", None)
    back = hub(plant, "R")
    small, large = module(plant, "S1", "6000"), module(plant, "S2", "9000")
    protection = fuse(plant, "F", "125")
    plant.net("plus", (protection[0],), potential="B+")
    plant.net("minus", (back,), potential="B-")
    supply(plant, "bat", _DC, current=Current.DC, pins=(protection[0], back))
    run(plant, back, [small], brk)
    run(plant, back, [large], make)
    run(plant, common, [protection, device(plant, "Z", kind=FunctionKind.LOAD)], back)
    found = _at(plant.model(), "F")
    assert (found.current_a, found.functions) == (Decimal(9000), (_fn("S2"),))


def test_a_position_no_source_reaches_reads_zero() -> None:
    model = _battery([])
    assert (_at(model, "FM").current_a, _at(model, "FM").functions) == (Decimal(0), ())


_UNIT = make_id(Unit, ("u",))
_TOP, _INNER = make_id(SupplySystem, ("S-top",)), make_id(SupplySystem, ("S-unit",))


def _declare(plant: Plant, key: str, pins: tuple[Id[Port], Id[Port]], fault: str) -> None:
    """Declare `S` on the hubs `pins` under the supply key `key`, at `fault` A."""
    plant.net(f"{key}+", (pins[0],), potential="S+")
    plant.net(f"{key}-", (pins[1],), potential="S-")
    unit = _UNIT if key == "S-unit" else None
    supply(
        plant,
        key,
        _S,
        name="S",
        current=Current.DC,
        unit=unit,
        pins=pins,
        fault_current_a=Decimal(fault),
    )


def _unit(plant: Plant, fault: str) -> tuple[Id[Port], Id[Port]]:
    """Unit `u`: feed hubs `UP`, `UM` declaring `S` at `fault` A, and fuse `F2` to a load."""
    plant.unit("u")
    pins = hub(plant, "UP"), hub(plant, "UM")
    _declare(plant, "S-unit", pins, fault)
    run(
        plant,
        pins[0],
        [fuse(plant, "F2", "125"), device(plant, "Z", kind=FunctionKind.LOAD)],
        pins[1],
    )
    into(plant, _UNIT, {"UP", "UM", "F2", "Z"})
    return pins


def _nested(top: str | None, inner: str) -> Model:
    """Hubs `XP`, `XM` with no unit (declaring `S` at `top` A unless `None`) feed unit `u`.

    `XP` feeds `UP` through the container's fuse `F1`; `XM` is wired to `UM`.
    """
    plant = Plant()
    outer = hub(plant, "XP"), hub(plant, "XM")
    if top is not None:
        _declare(plant, "S-top", outer, top)
    inner_pins = _unit(plant, inner)
    run(plant, outer[0], [fuse(plant, "F1", "125")], inner_pins[0])
    wire(plant, outer[1], inner_pins[1])
    return plant.model()


def test_a_nested_units_declaration_is_no_source_under_its_containers() -> None:
    """Acceptance 14: only the container's pins join S; F1 and F2 read its 10000 A, not 20000."""
    model = _nested("10000", "20000")
    graph = fault_graph(model, raw_of(model))
    joined = {edge.second for edge in graph.edges if edge.first.kind == "supply"}
    assert joined == {make_id(Port, ("XP", "f", "p")), make_id(Port, ("XM", "f", "p"))}
    for key in ("F1", "F2"):
        assert (_at(model, key).current_a, _at(model, key).supplies) == (Decimal(10000), (_TOP,))


def test_a_unit_built_alone_counts_its_own_declaration() -> None:
    """Acceptance 15: the unit alone reads its own S at its fuse."""
    plant = Plant()
    _unit(plant, "20000")
    model = plant.model()
    assert standalone(model, _UNIT)
    assert (_at(model, "F2").current_a, _at(model, "F2").supplies) == (Decimal(20000), (_INNER,))


def test_a_container_that_declares_nothing_counts_the_units_declaration() -> None:
    """Acceptance 16: with no container declaration of S, the nested unit's 6000 A counts."""
    model = _nested(None, "6000")
    assert not standalone(model, _UNIT)
    assert (_at(model, "F2").current_a, _at(model, "F2").supplies) == (Decimal(6000), (_INNER,))
    assert _at(model, "F1").current_a == Decimal(6000)


def test_a_fault_of_one_kind_joins_only_the_rails_of_that_kind() -> None:
    """R8: fuse `Q` joins the bus minus to hub `N` on a grid's N; module `m` runs from `N` to B+.

    `Q` reaches both supplies, so it reads one entry per kind. Its AC fault joins the grid's rails
    only: no AC path, 0 A. Joining B+ too would put `m`, which states no AC fault current, on one.
    """
    plant = Plant()
    plus, minus = _bus(plant)
    neutral = hub(plant, "N")
    plant.net("grid-N", (neutral,), potential="N")
    supply(plant, "grid", AC_400)
    run(plant, minus, [fuse(plant, "Q", "125")], neutral)
    run(plant, neutral, [module(plant, "m", "6000")], plus)
    found = {
        (f.kind, f.current_a, f.time_constant_ms, f.functions, f.supplies)
        for f in prospective_fault(plant.model())
    }
    assert found == {
        (Current.AC, Decimal(0), None, (), ()),
        (Current.DC, Decimal(6000), Decimal(2), (_fn("m"),), ()),
    }
