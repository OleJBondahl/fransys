"""The side of each pin of an item box, by its function's rank."""

from typing import TYPE_CHECKING, Any
lazy from collections.abc import Set as AbstractSet

from fransys_layout.conventions import FACTS, rank_key
from fransys_layout.conventions.sides import V1
from fransys_layout.engines.schematic.read.side_facts import Subject
from fransys_model.vocab import marking_key

if TYPE_CHECKING:
    from fransys_layout.stages import FunctionSpec
    from fransys_model.kernel import Id, Model


def side_rank(model: Model, spec: FunctionSpec) -> tuple[int, ...]:
    """The side order, lowest first: power above signal, energy in above out, AC above DC."""
    # energy in is the part's fact (`takes_energy`, model-0131); the rule puts it before AC or DC
    return rank_key(
        V1, Subject(model, spec.function, tuple(port.current for port in spec.ports)), FACTS
    )


def function_groups(model: Model, group: tuple[FunctionSpec, ...]) -> dict[Id[Any], int]:
    """Each function's index in the item box's side order; equal ranks share an index."""
    rank = {spec.function: side_rank(model, spec) for spec in group}
    order = sorted(set(rank.values()))
    return {function: order.index(one) for function, one in rank.items()}


def item_sides(model: Model, group: tuple[FunctionSpec, ...]) -> dict[Id[Any], str]:
    """Each port of an item box N when its function ranks first, else S; `{}` on a tie."""
    rank = {spec.function: side_rank(model, spec) for spec in group}
    if len(set(rank.values())) < 2:  # noqa: PLR2004 -- two ranks are the least a side order needs
        return {}
    first = min(rank.values())
    return {
        port.port: "n" if rank[spec.function] == first else "s"
        for spec in group
        for port in spec.ports
    }


def pin_sides(
    model: Model, specs: tuple[FunctionSpec, ...], views: AbstractSet[Id[Any]]
) -> tuple[tuple[Id[Any], ...], tuple[Id[Any], ...]]:
    """The ports of the item boxes `views` on top, then those below, from their `specs`."""
    by_item: dict[Id[Any], list[FunctionSpec]] = {}
    for spec in specs:
        if spec.item in views:
            by_item.setdefault(spec.item, []).append(spec)
    sides = {
        port: side
        for group in by_item.values()
        for port, side in item_sides(model, tuple(group)).items()
    }
    north = tuple(sorted(port for port, side in sides.items() if side == "n"))
    return north, tuple(sorted(port for port, side in sides.items() if side == "s"))


def view_port_order(group: tuple[FunctionSpec, ...]) -> dict[Id[Any], int]:
    """Each port's rank in an item box: a function's ports together, functions by first marking."""
    first = {
        spec.function: min((marking_key(p.name) for p in spec.ports), default=()) for spec in group
    }
    ranked = sorted(group, key=lambda spec: (first[spec.function], spec.function))
    return {
        port.port: index
        for index, port in enumerate(
            port for spec in ranked for port in sorted(spec.ports, key=lambda p: p.order)
        )
    }
