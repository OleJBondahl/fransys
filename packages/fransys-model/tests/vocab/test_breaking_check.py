"""`check_breaking`: a protective device's breaking point against the prospective fault (R11, R12).

A battery bus declared by pins with no fault current; strings of modules join its plus bus
through string fuses `SF{i}`, a main fuse `FM` leaves it. Every fuse states breaking points.
Expected values are written by hand from the spec's worked example and acceptance 1, 4, 5, 13.
"""

import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

from current_plant import device, fuse, hub, rate, run, wire
from fault_plant import breaker, module
from plant import Plant
from rating_plant import AC_400, rail, supply

from fransys_model.kernel import Finding, Model, Severity, make_id
from fransys_model.vocab import (
    BreakingPoint,
    Operating,
    OperatingFacet,
    PartRatingFacet,
    Rating,
    RatingFacet,
)
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Current, FunctionKind
from fransys_model.vocab.prospective_fault import prospective_fault
from fransys_model.vocab.templates import FunctionTemplate
from fransys_model.vocab.validators import ALL_VALIDATORS
from fransys_model.vocab.validators.ratings_breaking import (
    RATING_BREAKING_BELOW_FAULT,
    RATING_BREAKING_NO_DATA,
    check_breaking,
)
from fransys_model.vocab.validators.ratings_current import (
    LOAD_ABOVE_LIMIT,
    LOADS_ABOVE_LIMIT,
    check_load_draw,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function


def _fn(key: str) -> Id[Function]:
    return Plant.function_id(key, "f")


def _point(volts: str, amps: str, tau: str | None = None) -> BreakingPoint:
    return BreakingPoint(
        voltage_v=Decimal(volts),
        current_a=Decimal(amps),
        time_constant_ms=None if tau is None else Decimal(tau),
    )


_WORKED = (_point("1000", "15000", "15"),)


def _states(plant: Plant, key: str, points: Sequence[BreakingPoint]) -> None:
    """Make fuse `key`'s template state `points` DC, as a part library would."""
    template = make_id(FunctionTemplate, (key, "f"))
    rating = Rating(current_dc_a=Decimal(125), breaking_dc=tuple(points))
    plant.add(
        RatingFacet(id=make_id(RatingFacet, (key,)), key=(key,), subject=template, rating=rating)
    )


def _limit(plant: Plant, key: str) -> None:
    """Give module `key` a 186 A current limit, so loops through it bound a load's draw."""
    facet_id = make_id(OperatingFacet, (key,))
    for at, record in enumerate(plant.records):
        if record.id == facet_id:
            operating = dataclasses.replace(record.operating, max_current_dc_a=Decimal(186))
            plant.records[at] = dataclasses.replace(record, operating=operating)


def _battery(  # noqa: PLR0913 -- one keyword per thing a test varies
    points: Sequence[BreakingPoint] = _WORKED,
    *,
    strings: int = 3,
    per: int = 4,
    volts: str = "51.2",
    fault: str | None = "6000",
    tc: str | None = "2",
    draws: Sequence[Sequence[str]] = (),
) -> Plant:
    """Strings of `per` modules, each through `SF{i}`; the main fuse `FM` feeds `draws` fuses.

    Each entry of `draws` is a 2 A fuse `D{n}` after `FM` with one load per draw behind it.
    Every `SF`/`FM` states `points`; the `D` fuses state none.
    """
    plant = Plant()
    plus, minus = hub(plant, "P"), hub(plant, "M")
    plant.net("bus+", (plus,), potential="B+")
    plant.net("bus-", (minus,), potential="B-")
    supply(
        plant, "bat", {"B+": rail(volts), "B-": rail("0")}, current=Current.DC, pins=(plus, minus)
    )
    for at in range(strings):
        modules = [module(plant, f"m{at}{n}", fault, tc) for n in range(per)]
        run(plant, minus, [*modules, fuse(plant, f"SF{at}", "125")], plus)
        _states(plant, f"SF{at}", points)
    if draws:  # a limited source adding no fault current closes the loops that bound the loads
        run(plant, minus, [module(plant, "S", "0")], plus)
        _limit(plant, "S")
    _states(plant, "FM", points)
    run(plant, plus, [fuse(plant, "FM", "125"), device(plant, "Z", kind=FunctionKind.LOAD)], minus)
    for at, loads in enumerate(draws):
        node = hub(plant, f"N{at}")
        run(plant, plus, [fuse(plant, f"D{at}", "2")], node)
        for number, draw in enumerate(loads):
            lamp = device(plant, f"L{at}{number}", kind=FunctionKind.LOAD)
            template = make_id(FunctionTemplate, (f"L{at}{number}", "f"))
            operating = Operating(nominal_current_a=Decimal(draw))
            facet_id = make_id(OperatingFacet, (f"L{at}{number}", "n"))
            plant.add(
                OperatingFacet(
                    id=facet_id, key=(f"L{at}{number}", "n"), subject=template, operating=operating
                )
            )
            run(plant, node, [lamp], minus)
    return plant


def _main(model: Model) -> list[Finding]:
    """The findings on the main fuse: with one string the string fuse sees no source (0 A)."""
    return [f for f in check_breaking(model) if f.subjects == (_fn("FM"),)]


def test_worked_example_gives_the_three_findings() -> None:
    """Acceptance 1: the main fuse at 18000 A is over 15000 A, the string fuses at 12000 A not."""
    model = _battery(draws=(("2.5",), ("0.8", "0.8", "0.8"))).model()
    breaking = check_breaking(model)
    (below,) = breaking
    assert (below.code, below.severity, below.subjects) == (
        RATING_BREAKING_BELOW_FAULT,
        Severity.ERROR,
        (_fn("FM"),),
    )
    assert "function 'f' of item FM breaks 15000 A DC at 1000 V at 15 ms" in below.message
    assert "below the prospective 18000 A DC" in below.message
    assert "function 'f' of item m00" in below.message
    draw = check_load_draw(model)
    assert [(f.code, f.severity) for f in draw] == [
        (LOADS_ABOVE_LIMIT, Severity.WARNING),
        (LOAD_ABOVE_LIMIT, Severity.ERROR),
    ]
    assert draw[0].subjects == tuple(sorted(_fn(f"L1{n}") for n in range(3)))
    assert draw[1].subjects == (_fn("L00"),)


def test_a_fuse_no_counted_source_reaches_reads_0_a_and_is_silent() -> None:
    """Acceptance 18: FM, with no source on the bus, reads 0 A; its timed DC point is silent."""
    model = _battery(strings=0).model()
    (fault,) = prospective_fault(model)
    assert (fault.position.functions, fault.current_a) == ((_fn("FM"),), 0)
    assert check_breaking(model) == ()


def test_a_fault_within_the_point_gives_nothing() -> None:
    model = _battery(strings=2).model()
    assert check_breaking(model) == ()


def test_the_point_is_chosen_by_the_voltage_across_the_device() -> None:
    """Acceptance 4: 3000 A at 400 V and 900 A at 800 V; at 600 V the 900 A point is used."""
    points = (_point("400", "3000"), _point("800", "900"))
    model = _battery(points, strings=1, per=1, volts="600", fault="1000").model()
    (finding,) = _main(model)
    assert finding.code == RATING_BREAKING_BELOW_FAULT
    assert "breaks 900 A DC at 800 V" in finding.message
    passing = _battery(points, strings=1, per=1, volts="600", fault="800").model()
    assert _main(passing) == []


def test_a_voltage_above_every_point_is_no_data() -> None:
    """Acceptance 4: at 900 V no point applies."""
    points = (_point("400", "3000"), _point("800", "900"))
    model = _battery(points, strings=1, per=1, volts="900", fault="1000").model()
    (finding,) = _main(model)
    assert (finding.code, finding.severity) == (RATING_BREAKING_NO_DATA, Severity.WARNING)
    assert "no point is rated for the circuit voltage of 900 V" in finding.message


def test_a_point_with_a_time_constant_above_the_devices_is_no_data() -> None:
    """Acceptance 5: a 15 ms point against a 20 ms source."""
    points = (_point("1000", "15000", "15"),)
    model = _battery(points, strings=1, per=1, fault="1000", tc="20").model()
    (finding,) = _main(model)
    assert (finding.code, finding.severity) == (RATING_BREAKING_NO_DATA, Severity.WARNING)
    assert "time constant of the sources, 20 ms" in finding.message


def test_an_unknown_time_constant_leaves_only_points_without_one() -> None:
    model = _battery(strings=1, per=1, fault="1000", tc=None).model()
    (finding,) = _main(model)
    assert "time constant of the sources, unknown" in finding.message


def test_a_holders_fitted_links_points_are_the_ones_checked() -> None:
    """Acceptance 13: the holder's point would pass, the link's fails; the link's is named."""
    plant = _battery((_point("1000", "20000"),), strings=2, per=1)
    part = rate(plant, "LK", None)
    link = Rating(breaking_dc=(_point("1000", "5000"),))
    facet = PartRatingFacet(
        id=make_id(PartRatingFacet, ("LK",)), key=("LK",), subject=part, rating=link
    )
    plant.add(facet)
    plant.item("LK", part=part, parent=make_id(Item, ("SF0",)))
    (finding,) = check_breaking(plant.model())
    assert finding.subjects == (_fn("SF0"),)
    assert "breaks 5000 A DC at 1000 V" in finding.message
    assert "below the prospective 6000 A DC" in finding.message


def test_an_unknown_fault_current_is_silent() -> None:
    model = _battery(strings=2, per=1, fault=None).model()
    assert check_breaking(model) == ()


def test_a_device_with_no_points_is_silent() -> None:
    model = _battery((), strings=2, per=1, fault="60000").model()
    assert check_breaking(model) == ()


def test_check_breaking_is_registered() -> None:
    assert check_breaking in ALL_VALIDATORS


def test_no_data_prints_the_circuit_voltage_to_one_decimal() -> None:
    """R12: breaker `Q` on L1 and L2 of a 10000 A grid stands at 398.37... V, above its 230 V."""
    plant = Plant()
    pins = [hub(plant, name) for name in AC_400]
    for name, pin in zip(AC_400, pins, strict=True):
        plant.net(f"grid-{name}", (pin,), potential=name)
    supply(plant, "grid", AC_400, pins=pins, fault_current_a=Decimal(10000))
    poles = breaker(plant, "Q")
    rating = Rating(current_ac_a=Decimal(16), breaking_ac=(_point("230", "20000"),))
    template = make_id(FunctionTemplate, ("Q", "f"))
    plant.add(
        RatingFacet(id=make_id(RatingFacet, ("Q",)), key=("Q",), subject=template, rating=rating)
    )
    for pin, (line, _) in zip(pins[:2], poles, strict=False):
        wire(plant, pin, line)
    (finding,) = check_breaking(plant.model())
    assert (finding.code, finding.severity, finding.subjects) == (
        RATING_BREAKING_NO_DATA,
        Severity.WARNING,
        (_fn("Q"),),
    )
    assert "no point is rated for the circuit voltage of 398.4 V" in finding.message
