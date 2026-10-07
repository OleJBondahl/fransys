"""A three-pole breaker built as one function: its poles are three positions told apart by `ports`.

The poles share one `functions` tuple; the two end ports are the identity (RATINGS-3 R17).
"""

from current_plant import device, rate, run
from plant import Plant

from fransys_model.derive import current_chains
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Port
from fransys_model.vocab.current_bounds import LimitRole
from fransys_model.vocab.enums import FunctionKind, LinkKind, PortRole
from fransys_model.vocab.templates import FunctionTemplate, PortTemplate
lazy from fransys_model.vocab.current_chains import CurrentPosition

Pole = tuple[Id[Port], Id[Port]]


def _breaker(plant: Plant, key: str, amps: str) -> list[Pole]:
    """One protection function `f` with three pole links, each between its own two ports."""
    part = rate(plant, key, amps)
    kind = FunctionKind.PROTECTION
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "f")), key=(key, "f"), part=part, name="f", kind=kind
    )
    names = [(f"{n}a", f"{n}b") for n in (1, 2, 3)]
    pins = {
        name: PortTemplate(
            id=make_id(PortTemplate, (key, "f", name)),
            key=(key, "f", name),
            function=template.id,
            name=name,
            role=PortRole.GENERIC,
        )
        for pair in names
        for name in pair
    }
    plant.add(template, *pins.values())
    for first, second in names:
        plant.link(pins[first], pins[second], LinkKind.CONDUCTIVE, key=f"link-{key}-{first}")
    function = plant.function(plant.item(key, part=part), "f", template=template.id, kind=kind)
    ports = {name: plant.port(function, name, template=pin.id) for name, pin in pins.items()}
    return [(ports[first], ports[second]) for first, second in names]


def _series_plant() -> tuple[Plant, list[Pole]]:
    """A 186 A source in series with the three poles of a 100 A breaker, a loop of one block."""
    plant = Plant()
    source = device(plant, "S", limit="186")
    poles = _breaker(plant, "Q", "100")
    run(plant, source[1], [poles[0], poles[1], poles[2]], source[0])
    return plant, poles


def _positions(plant: Plant) -> list[CurrentPosition]:
    return [p for chain in current_chains(plant.model()) for p in chain.positions]


def test_three_poles_of_one_function_are_three_positions_told_apart_by_ports() -> None:
    plant, poles = _series_plant()
    breaker = [p for p in _positions(plant) if p.functions == (Plant.function_id("Q", "f"),)]
    assert len(breaker) == 3
    assert len({p.functions for p in breaker}) == 1
    assert sorted(tuple(sorted(p.ports)) for p in breaker) == sorted(
        tuple(sorted(pole)) for pole in poles
    )


def test_a_bound_set_by_a_pole_carries_that_poles_ports() -> None:
    plant, poles = _series_plant()
    pole_ports = {tuple(sorted(pole)) for pole in poles}
    bounds = [b for p in _positions(plant) for b in p.bounds if b.role is LimitRole.PROTECTION]
    assert bounds
    assert {tuple(sorted(b.ports)) for b in bounds} <= pole_ports
    # equal in value, setter and role, the lowest ports win, whatever the input order
    assert {b.ports for b in bounds} == {min(bounds, key=lambda b: b.ports).ports}
