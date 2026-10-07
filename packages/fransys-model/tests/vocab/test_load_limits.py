"""`load_limits`: the limit that bounds each load's draw (RATINGS-3 R4, R14, R15, R17).

Every device is an item `key` with one function `f` (builders in `current_plant`); a supply puts
its rails on the source's two ports and wires carry them to the load. Expected values are written
by hand from the spec.
"""

from decimal import Decimal

from current_plant import device, external, fuse, hub, wire, with_role
from plant import Plant
from rating_plant import AC_400, rail, supply

from fransys_model.kernel import Model, make_id
from fransys_model.vocab import Operating, OperatingFacet
from fransys_model.vocab.current_bounds import LimitRole
from fransys_model.vocab.current_chains import chains_unordered
from fransys_model.vocab.enums import Current, FunctionKind, PortRole
from fransys_model.vocab.load_limits import load_limits
from fransys_model.vocab.templates import FunctionTemplate

_LOAD = Plant.function_id("D", "f")


def _dc_plant() -> Plant:
    plant = Plant()
    supply(plant, "dc", {"DC+": rail("24"), "DC-": rail("0")}, current=Current.DC)
    return plant


def _source(plant: Plant, key: str = "S", limit: str = "186") -> tuple:
    return device(plant, key, limit=limit, kind=FunctionKind.SUPPLY, rails=[["DC+"], ["DC-"]])


def _load(
    plant: Plant,
    names: tuple[str, ...] = ("1", "2"),
    *,
    nominal: str | None = "2.5",
    key: str = "D",
) -> tuple:
    """Item `key`: a load function `f` with the ports `names`, drawing `nominal` A."""
    part = plant.part(key)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "f")),
        key=(key, "f"),
        part=part,
        name="f",
        kind=FunctionKind.LOAD,
    )
    plant.add(template)
    if nominal is not None:
        operating = Operating(nominal_current_a=Decimal(nominal))
        facet = OperatingFacet(
            id=make_id(OperatingFacet, (key,)), key=(key,), subject=template.id, operating=operating
        )
        plant.add(facet)
    function = plant.function(
        plant.item(key, part=part), "f", template=template.id, kind=FunctionKind.LOAD
    )
    return tuple(plant.port(function, name) for name in names)


def _behind_fuse(
    fuse_a: str = "2", *, limit: str = "186", names: tuple[str, ...] = ("1", "2")
) -> Model:
    """`S - F - D - S`: a source, a full-range fuse and a load in one loop."""
    plant = _dc_plant()
    source, protection, ports = (
        _source(plant, limit=limit),
        fuse(plant, "F", fuse_a),
        _load(plant, names),
    )
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], ports[0])
    wire(plant, ports[1], source[1])
    return plant.model()


def test_a_two_port_load_behind_a_fuse_is_bounded_by_the_fuse() -> None:
    (limit,) = load_limits(_behind_fuse())
    assert (limit.function, limit.port, limit.kind, limit.draw_a) == (
        _LOAD,
        None,
        Current.DC,
        Decimal("2.5"),
    )
    assert limit.bound is not None
    assert (limit.bound.value, limit.bound.by, limit.bound.role) == (
        Decimal(2),
        Plant.function_id("F", "f"),
        LimitRole.PROTECTION,
    )


def test_a_source_limit_below_the_fuse_bounds_the_load() -> None:
    (limit,) = load_limits(_behind_fuse(limit="1"))
    assert limit.bound is not None
    assert (limit.bound.value, limit.bound.by, limit.bound.role) == (
        Decimal(1),
        Plant.function_id("S", "f"),
        LimitRole.SOURCE,
    )


def test_a_three_port_load_has_one_limit_per_phase_with_its_own_fuse() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    neutral = hub(plant, "N")
    ports = _load(plant, ("1", "2", "3"))
    for number, phase in enumerate(("L1", "L2", "L3")):
        source = device(
            plant, f"S{number}", limit_ac="100", kind=FunctionKind.SUPPLY, rails=[[phase], ["N"]]
        )
        protection = fuse(plant, f"F{number}", None, amps_ac=str(4 + 2 * number))
        wire(plant, source[0], protection[0])
        wire(plant, protection[1], ports[number])
        wire(plant, source[1], neutral)
    limits = load_limits(plant.model())
    assert [limit.port for limit in limits] == sorted(ports)
    assert {limit.port: limit.bound.by for limit in limits if limit.bound} == {
        ports[number]: Plant.function_id(f"F{number}", "f") for number in range(3)
    }
    assert {limit.port: limit.bound.value for limit in limits if limit.bound} == {
        ports[number]: Decimal(4 + 2 * number) for number in range(3)
    }
    assert {limit.kind for limit in limits} == {Current.AC}


def test_a_lamp_with_l_n_and_pe_ports_is_one_two_port_edge() -> None:
    plant = _dc_plant()
    source, protection, ports = (
        _source(plant),
        fuse(plant, "F", "2"),
        _load(plant, ("L", "N", "PE")),
    )
    with_role(plant, ports[2], PortRole.PE)
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], ports[0])
    wire(plant, ports[1], source[1])
    (limit,) = load_limits(plant.model())
    assert limit.port is None
    assert limit.bound is not None
    assert limit.bound.by == Plant.function_id("F", "f")


def test_a_load_that_states_a_rating_is_a_position_with_its_chain_bound() -> None:
    plant = _dc_plant()
    source, protection = _source(plant), fuse(plant, "F", "2")
    load = device(plant, "D", amps="3", kind=FunctionKind.LOAD, rails=[[], []])
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], load[0])
    wire(plant, load[1], source[1])
    plant.add(
        OperatingFacet(
            id=make_id(OperatingFacet, ("Dn",)),
            key=("Dn",),
            subject=make_id(FunctionTemplate, ("D", "f")),
            operating=Operating(nominal_current_a=Decimal("2.5")),
        )
    )
    model = plant.model()
    (limit,) = load_limits(model)
    (position,) = (
        p for chain in chains_unordered(model) for p in chain.positions if p.functions == (_LOAD,)
    )
    assert limit.port is None
    assert limit.draw_a == Decimal("2.5")
    assert limit.bound is not None
    assert limit.bound.value == Decimal(2)
    assert limit.bound == position.bounds[0]


def test_a_load_with_no_stated_draw_has_no_entry() -> None:
    plant = _dc_plant()
    source, protection, ports = _source(plant), fuse(plant, "F", "2"), _load(plant, nominal=None)
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], ports[0])
    wire(plant, ports[1], source[1])
    assert load_limits(plant.model()) == ()


def _lamp_across_fuse(*, nominal: str | None) -> Model:
    plant = _dc_plant()
    source, protection, ports = _source(plant), fuse(plant, "F", "2"), _load(plant, nominal=nominal)
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], source[1])
    wire(plant, ports[0], protection[0])
    wire(plant, ports[1], protection[1])
    return plant.model()


def test_a_lamp_across_a_fuse_does_not_change_the_chains_but_has_its_own_limit() -> None:
    with_draw, without = _lamp_across_fuse(nominal="0.1"), _lamp_across_fuse(nominal=None)
    assert chains_unordered(with_draw) == chains_unordered(without)
    (limit,) = load_limits(with_draw)
    assert limit.bound is not None
    assert limit.bound.by == Plant.function_id("S", "f")
    assert load_limits(without) == ()


def test_loads_are_added_one_at_a_time() -> None:
    """A lamp across the fuse and a load behind it: together the lamp would bypass the fuse."""
    plant = _dc_plant()
    source, protection, ret = _source(plant), fuse(plant, "F", "2"), device(plant, "W", amps="10")
    lamp, behind = _load(plant, key="H", nominal="0.1"), _load(plant)
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], ret[0])
    wire(plant, ret[1], source[1])
    wire(plant, lamp[0], protection[0])
    wire(plant, lamp[1], protection[1])
    wire(plant, behind[0], protection[1])
    wire(plant, behind[1], source[1])
    by_function = {limit.function: limit.bound for limit in load_limits(plant.model())}
    fuse_id, source_id = Plant.function_id("F", "f"), Plant.function_id("S", "f")
    load_bound = by_function[_LOAD]
    assert load_bound is not None
    assert (load_bound.value, load_bound.by) == (Decimal(2), fuse_id)
    lamp_bound = by_function[Plant.function_id("H", "f")]
    assert lamp_bound is not None
    assert lamp_bound.by == source_id


def test_a_load_bridging_two_components_keeps_both() -> None:
    """The load's second port lies on a component the rest of the graph never joins to the first."""
    plant = _dc_plant()
    source, protection, ports = _source(plant), fuse(plant, "F", "2"), _load(plant)
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], ports[0])
    wire(plant, ports[1], external(plant, "T"))
    wire(plant, source[1], external(plant, "U"))
    (limit,) = load_limits(plant.model())
    assert limit.bound is not None
    assert (limit.bound.value, limit.bound.by) == (Decimal(2), Plant.function_id("F", "f"))
