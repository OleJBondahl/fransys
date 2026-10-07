"""`check_load_draw`: a load's draw against its limit, alone and together (RATINGS-3 R16).

A 24 V DC source `S` feeds a fuse, a hub `H` fans out to the loads; each load is an item with one
function `f` drawing the stated amps. Invented data only.
"""

from decimal import Decimal

from current_plant import contactor, device, fuse, hub, rate, wire
from plant import Plant
from rating_plant import AC_400, rail, supply

from fransys_model.kernel import Id, Model, Severity, make_id
from fransys_model.vocab import Operating, OperatingFacet
from fransys_model.vocab.enums import Current, FunctionKind, LinkKind, PortRole
from fransys_model.vocab.load_limits import load_limits
from fransys_model.vocab.templates import FunctionTemplate, PortTemplate
from fransys_model.vocab.validators import ALL_VALIDATORS
from fransys_model.vocab.validators.ratings_current import (
    LOAD_ABOVE_LIMIT,
    LOADS_ABOVE_LIMIT,
    RATING_CURRENT_BELOW_BRANCH,
    check_load_draw,
    check_ratings_current,
)
lazy from fransys_model.vocab.core import Function


def _fn(item: str) -> Id[Function]:
    return Plant.function_id(item, "f")


def _lamp(plant: Plant, key: str, nominal: str | None) -> tuple:
    """Item `key`: a two-port load drawing `nominal` A."""
    ports = device(plant, key, kind=FunctionKind.LOAD)
    if nominal is not None:
        operating = Operating(nominal_current_a=Decimal(nominal))
        facet_id = make_id(OperatingFacet, (key, "n"))
        subject = make_id(FunctionTemplate, (key, "f"))
        plant.add(OperatingFacet(id=facet_id, key=(key, "n"), subject=subject, operating=operating))
    return ports


def _plant() -> tuple[Plant, tuple]:
    plant = Plant()
    supply(plant, "dc", {"DC+": rail("24"), "DC-": rail("0")}, current=Current.DC)
    source = device(plant, "S", limit="186", kind=FunctionKind.SUPPLY, rails=[["DC+"], ["DC-"]])
    return plant, source


def _on_fuse(draws: list[str], fuse_a: str = "2") -> Model:
    """`S - F - H`, then each load from `H` back to `S`."""
    plant, source = _plant()
    protection, node = fuse(plant, "F", fuse_a), hub(plant, "H")
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], node)
    for number, draw in enumerate(draws):
        load = _lamp(plant, f"D{number}", draw)
        wire(plant, node, load[0])
        wire(plant, load[1], source[1])
    return plant.model()


def test_a_load_above_its_fuse_is_one_error_naming_both() -> None:
    (finding,) = check_load_draw(_on_fuse(["2.5"]))
    assert (finding.code, finding.severity, finding.subjects) == (
        LOAD_ABOVE_LIMIT,
        Severity.ERROR,
        (_fn("D0"),),
    )
    assert "function 'f' of item D0 draws 2.5 A DC, above its limit of 2 A DC" in finding.message
    assert "the protective device of function 'f' of item F" in finding.message


def test_loads_that_are_above_the_fuse_only_together_are_one_warning() -> None:
    (finding,) = check_load_draw(_on_fuse(["0.8", "0.8", "0.8"]))
    assert (finding.code, finding.severity) == (LOADS_ABOVE_LIMIT, Severity.WARNING)
    assert finding.subjects == tuple(sorted(_fn(f"D{n}") for n in range(3)))
    assert "draw 2.4 A DC together, above the limit of 2 A DC" in finding.message


def test_loads_within_the_fuse_together_give_nothing() -> None:
    assert check_load_draw(_on_fuse(["0.8", "0.8"])) == ()


def test_one_load_above_among_others_is_the_error_only() -> None:
    (finding,) = check_load_draw(_on_fuse(["2.5", "0.8", "0.8"]))
    assert finding.code == LOAD_ABOVE_LIMIT
    assert finding.subjects == (_fn("D0"),)


def test_a_main_fuse_sums_only_the_loads_it_bounds() -> None:
    plant, source = _plant()
    main, node = fuse(plant, "M", "2.5"), hub(plant, "H")
    wire(plant, source[0], main[0])
    wire(plant, main[1], node)
    for number in range(2):
        branch, load = fuse(plant, f"B{number}", "2"), _lamp(plant, f"D{number}", "1.5")
        wire(plant, node, branch[0])
        wire(plant, branch[1], load[0])
        wire(plant, load[1], source[1])
    model = plant.model()
    setters = {limit.function: limit.bound.by for limit in load_limits(model) if limit.bound}
    assert setters == {_fn(f"D{n}"): Plant.function_id(f"B{n}", "f") for n in range(2)}
    assert check_load_draw(model) == ()


def _breaker(plant: Plant) -> list[tuple]:
    """One protection function `f` with three pole links, rated 2 A AC."""
    part = rate(plant, "Q", None, amps_ac="2")
    kind = FunctionKind.PROTECTION
    key = ("Q", "f")
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, key), key=key, part=part, name="f", kind=kind
    )
    names = [(f"{n}a", f"{n}b") for n in (1, 2, 3)]
    pins = {
        name: PortTemplate(
            id=make_id(PortTemplate, (*key, name)),
            key=(*key, name),
            function=template.id,
            name=name,
            role=PortRole.GENERIC,
        )
        for pair in names
        for name in pair
    }
    plant.add(template, *pins.values())
    for first, second in names:
        plant.link(pins[first], pins[second], LinkKind.CONDUCTIVE, key=f"link-Q-{first}")
    function = plant.function(plant.item("Q", part=part), "f", template=template.id, kind=kind)
    ports = {name: plant.port(function, name, template=pin.id) for name, pin in pins.items()}
    return [(ports[first], ports[second]) for first, second in names]


def test_the_poles_of_one_breaker_are_told_apart_so_each_phase_is_its_own_sum() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    neutral, poles = hub(plant, "N"), _breaker(plant)
    for number, phase in enumerate(("L1", "L2", "L3")):
        source = device(
            plant, f"S{number}", limit_ac="100", kind=FunctionKind.SUPPLY, rails=[[phase], ["N"]]
        )
        load = _lamp(plant, f"D{number}", "0.8")
        wire(plant, source[0], poles[number][0])
        wire(plant, poles[number][1], load[0])
        wire(plant, load[1], neutral)
        wire(plant, source[1], neutral)
    model = plant.model()
    bounds = [limit.bound for limit in load_limits(model) if limit.bound]
    assert {(bound.by, bound.value) for bound in bounds} == {(_fn("Q"), Decimal(2))}
    assert len({bound.ports for bound in bounds}) == 3
    assert check_load_draw(model) == ()


def _lamp_across(*, draw: str | None) -> Model:
    """A 2 A fuse over a 1 A contactor, with a lamp across the fuse."""
    plant, source = _plant()
    protection, switch, lamp = (
        fuse(plant, "F", "2"),
        contactor(plant, "K", "1"),
        _lamp(plant, "D", draw),
    )
    wire(plant, source[0], protection[0])
    wire(plant, protection[1], switch[0])
    wire(plant, switch[1], source[1])
    wire(plant, lamp[0], protection[0])
    wire(plant, lamp[1], protection[1])
    return plant.model()


def test_a_lamp_across_a_fuse_leaves_the_branch_rating_finding_unchanged() -> None:
    with_lamp, without = _lamp_across(draw="0.1"), _lamp_across(draw=None)
    findings = check_ratings_current(with_lamp)
    assert [f.code for f in findings] == [RATING_CURRENT_BELOW_BRANCH]
    assert findings == check_ratings_current(without)
    assert check_load_draw(with_lamp) == ()


def test_check_load_draw_is_registered() -> None:
    assert check_load_draw in ALL_VALIDATORS
