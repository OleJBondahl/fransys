"""Reads of the model's units for the stages (D6): each unit's boundary and the unused ones."""

from functools import partial
from typing import TYPE_CHECKING, Any

from fransys_layout.stages.exempt import UnitNesting
from fransys_layout.stages.references import BlackBoxReads
from fransys_layout.stages.replicate import UnitBoundary
from fransys_model.derive import black_box_unit
from fransys_model.vocab.membership import boundary, units
from fransys_model.vocab.tables import functions, items, unused_boundaries
from fransys_model.vocab.tables import units as units_table
from fransys_model.vocab.unit_index import unit_index

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model


def function_unit(model: Model, function: Id[Any]) -> Id[Any] | None:
    """The unit whose own document draws `function`: its item's (layout-0159)."""
    return items(model)[functions(model)[function].item].unit


def boundary_edges(model: Model) -> frozenset[Id[Any]]:
    """D10: the boundary functions of every unit of `model`."""
    return frozenset(f for unit in units_table(model) for f in boundary(model, unit))


def containing_units(model: Model, unit: Id[Any] | None) -> frozenset[Id[Any]]:
    """`unit` and every unit it is nested in: the one cycle-safe walk, never `Unit.parent`."""
    if unit is None:
        return frozenset()
    return unit_index(model).containing.get(unit, frozenset())


def top_level_unit(model: Model, unit: Id[Any] | None) -> Id[Any] | None:
    """The top-level unit (`None` parent) `unit` is in, `unit` itself if it is one."""
    table = units_table(model)
    return next((one for one in containing_units(model, unit) if table[one].parent is None), None)


def is_nested(model: Model, unit: Id[Any] | None) -> bool:
    """Whether `unit` is nested in another unit: the one test (`None` and a top-level one: no)."""
    return len(containing_units(model, unit)) > 1


def top_boundary_edges(model: Model) -> frozenset[Id[Any]]:
    """layout-0080: the boundary functions of the top-level units, pass-throughs included."""
    return frozenset(
        f
        for unit in units_table(model)
        if not is_nested(model, unit)
        for f in boundary(model, unit)
    )


def unit_boundaries(model: Model) -> tuple[UnitBoundary, ...]:
    """Every unit's boundary functions and parent, units in `Id` order (`replicate_boundaries`)."""
    unit_table = units_table(model)
    found = []
    for unit_id in units(model):
        unit = unit_table[unit_id]
        parent_key = unit_table[unit.parent].key if unit.parent is not None else None
        found.append(
            UnitBoundary(
                functions=boundary(model, unit_id), parent=unit.parent, parent_key=parent_key
            )
        )
    return tuple(found)


def boundary_parents(model: Model) -> dict[Id[Any], frozenset[Id[Any] | None]]:
    """Each boundary function's units' parents, `None` for a top-level unit (`edge_mates`).

    A function on the boundary of several units (author-0032) has one parent per unit.
    """
    parent_of: dict[Id[Any], set[Id[Any] | None]] = {}
    for unit in units(model):
        for function in boundary(model, unit):
            parent_of.setdefault(function, set()).add(units_table(model)[unit].parent)
    return {function: frozenset(parents) for function, parents in parent_of.items()}


def unit_nesting(model: Model, standing_in: Iterable[Id[Any] | None]) -> UnitNesting:
    """How the units of `model` nest (`boundary_exempt`)."""
    return UnitNesting(
        inside=unit_index(model).containing,
        nested=frozenset(unit for unit in standing_in if is_nested(model, unit)),
    )


def black_box_reads(model: Model, nested: frozenset[Id[Any] | None]) -> BlackBoxReads:
    """The `BlackBoxReads` of `model` (`black_box_sets`); `nested` is `unit_nesting(...).nested`."""
    return BlackBoxReads(
        nested=nested, edges=top_boundary_edges(model), top=partial(top_level_unit, model)
    )


def boundary_edge_set(model: Model) -> frozenset[Id[Any]]:
    """Every unit's boundary functions, in one set (`own_set_texts`)."""
    return frozenset(f for unit in units(model) for f in boundary(model, unit))


def unused_functions(model: Model) -> frozenset[Id[Any]]:
    """The functions declared unused boundaries (W3): they draw no pin."""
    return frozenset(one.function for one in unused_boundaries(model).values())


def shared_boundaries(model: Model) -> frozenset[Id[Any]]:
    """P6: the functions on the boundary of two or more units (read once)."""
    held: dict[Id[Any], int] = {}
    for unit in units(model):
        for function in boundary(model, unit):
            held[function] = held.get(function, 0) + 1
    return frozenset(function for function, count in held.items() if count > 1)


def hidden_sets(model: Model, unit: Id[Any], function: Id[Any]) -> frozenset[Id[Any] | None]:
    """P6: the sets (by unit, `None` the top) where `unit` does not draw a function it shares.

    A set draws it in the `derive.black_box_unit` of its item's unit, never in the set's own unit.
    """
    home = function_unit(model, function)
    if home is None:
        return frozenset()
    above = containing_units(model, home) - {home}
    return frozenset(
        one
        for one in (None, *units(model))
        if (one is not None and unit in containing_units(model, one))
        or ((one is None or one in above) and black_box_unit(model, home, one) != unit)
    )


def black_boxes(model: Model) -> dict[tuple[Id[Any], Id[Any] | None], Id[Any]]:
    """Each unit's black box in each set above it (`derive.black_box_unit`; `unit_outlines`)."""
    return {
        (unit, one): black_box_unit(model, unit, one)
        for unit in units(model)
        for one in (None, *containing_units(model, unit))
    }
