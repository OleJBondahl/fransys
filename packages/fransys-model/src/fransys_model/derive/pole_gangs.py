"""The pole groups drawn as one multi-pole symbol, with their lead and each port's pole."""

from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.rows_pole_gangs import PoleGang, PolePort
from fransys_model.layout import PoleGroup, layout_of
lazy from fransys_model.kernel import Id, Model, canonical
lazy from fransys_model.vocab.core import Function

__all__ = ["pole_gangs"]


def pole_gangs(model: Model, drawn: frozenset[Id[Function]]) -> tuple[PoleGang, ...]:
    """One `PoleGang` per `PoleGroup` whose members are all in `drawn`, sorted by group id.

    The first member leads and member k's ports are pole k. A group with a member not in
    `drawn` has no row: each drawn member then draws alone. `selector` is the author's flag.
    """
    ports = build_indexes(model).ports_by_function
    rows = []
    groups = layout_of(model, PoleGroup)
    for group in (groups[i] for i in canonical(groups)):
        if not all(function in drawn for function in group.functions):
            continue
        pole_of = tuple(
            PolePort(port=port, pole=pole)
            for pole, function in enumerate(group.functions)
            for port in ports.get(function, ())
        )
        rows.append(
            PoleGang(
                group=group.id,
                lead=group.functions[0],
                members=group.functions,
                selector=group.selector,
                poles=len(group.functions),
                pole_of=pole_of,
            )
        )
    return tuple(rows)
