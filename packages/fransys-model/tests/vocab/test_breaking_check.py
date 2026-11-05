"""`check_breaking`: a protective device's breaking point against the prospective fault.

A battery bus declared by pins with no fault current; strings of modules join its plus bus
through string fuses `SF{i}`, a main fuse `FM` leaves it. Every fuse states breaking points.
"""

import dataclasses
from typing import TYPE_CHECKING

from current_plant import device, fuse, hub, run
from fault_plant import module
from plant import Plant
from rating_plant import figures, point, rail, states_block, supply

from fransys_model.checks.ratings_breaking import (
    RATING_BREAKING_BELOW_FAULT,
    check_breaking,
)
from fransys_model.checks.ratings_current import (
    LOAD_ABOVE_LIMIT,
    LOADS_ABOVE_LIMIT,
    check_load_draw,
)
from fransys_model.elecdef import Current, Fuse, Range, Unit
from fransys_model.kernel import Finding, Model, Severity, make_id
from fransys_model.vocab import (
    Operating,
    OperatingFacet,
)
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.templates import FunctionTemplate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function


def _fn(key: str) -> Id[Function]:
    return Plant.function_id(key, "f")


_WORKED = (point("1000", "15000", "15"),)


def _states(plant: Plant, key: str, points: Sequence[Range]) -> None:
    """Make fuse `key`'s template state `points`, as a part library would."""
    states_block(plant, make_id(FunctionTemplate, (key, "f")), Fuse(breaking_capacity=tuple(points)), key=key)


def _limit(plant: Plant, key: str) -> None:
    """Give module `key` a 186 A current limit, so loops through it bound a load's draw."""
    facet_id = make_id(OperatingFacet, (key,))
    for at, record in enumerate(plant.records):
        if record.id == facet_id:
            operating = dataclasses.replace(record.operating, max_current=figures(Unit.A, None, "186"))
            plant.records[at] = dataclasses.replace(record, operating=operating)


def _battery(  # noqa: PLR0913 -- one keyword per thing a test varies
    points: Sequence[Range] = _WORKED,
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
    supply(plant, "bat", {"B+": rail(volts), "B-": rail("0")}, current=Current.DC, pins=(plus, minus))
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
            operating = Operating(nominal_current=Unit.A(draw))
            facet_id = make_id(OperatingFacet, (f"L{at}{number}", "n"))
            plant.add(OperatingFacet(id=facet_id, key=(f"L{at}{number}", "n"), subject=template, operating=operating))
            run(plant, node, [lamp], minus)
    return plant


def _main(model: Model) -> list[Finding]:
    """The findings on the main fuse: with one string the string fuse sees no source (0 A)."""
    return [f for f in check_breaking(model) if f.subjects == (_fn("FM"),)]


def test_worked_example_gives_the_three_findings() -> None:
    """The main fuse at 18000 A is over 15000 A, the string fuses at 12000 A not."""
    model = _battery(draws=(("2.5",), ("0.8", "0.8", "0.8"))).model()
    breaking = check_breaking(model)
    (below,) = breaking
    assert (below.code, below.severity, below.subjects) == (
        RATING_BREAKING_BELOW_FAULT,
        Severity.ERROR,
        (_fn("FM"),),
    )
    assert f"function {ref(_fn('FM'))} breaks 15000 A DC at 1000 V at 15 ms" in below.message
    assert "below the prospective 18000 A DC" in below.message
    assert ref(_fn("m00")) in below.message
    draw = check_load_draw(model)
    assert [(f.code, f.severity) for f in draw] == [
        (LOADS_ABOVE_LIMIT, Severity.WARNING),
        (LOAD_ABOVE_LIMIT, Severity.ERROR),
    ]
    assert draw[0].subjects == tuple(sorted(_fn(f"L1{n}") for n in range(3)))
    assert draw[1].subjects == (_fn("L00"),)


def test_the_blocks_points_decide_the_outcome() -> None:
    """The same main fuse is over its point at 15000 A and clear of it at 20000 A."""
    assert _main(_battery(points=(point("1000", "20000", "15"),)).model()) == []
    assert len(_main(_battery().model())) == 1


def test_an_unknown_time_constant_leaves_only_points_without_one() -> None:
    model = _battery(strings=1, per=1, fault="1000", tc=None).model()
    (finding,) = _main(model)
    assert "time constant of the sources, unknown" in finding.message
