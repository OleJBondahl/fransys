"""Reads of the model's units for the stages (D6): each unit's boundary and the unused ones."""

from functools import partial
from typing import TYPE_CHECKING, Any

from fransys_layout.stages.exempt import UnitNesting
from fransys_layout.stages.references import BlackBoxReads
from fransys_layout.stages.replicate import UnitBoundary
from fransys_model.vocab.membership import boundary, units
from fransys_model.vocab.tables import units as units_table
from fransys_model.vocab.tables import unused_boundaries
from fransys_model.vocab.unit_index import unit_index

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.kernel import Id, Model


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


def boundary_parents(model: Model) -> dict[Id[Any], Id[Any] | None]:
    """Each boundary function's unit's parent, `None` for a top-level unit (`edge_mates`)."""
    parent_of: dict[Id[Any], Id[Any] | None] = {}
    for unit in units(model):
        for function in boundary(model, unit):
            parent_of[function] = units_table(model)[unit].parent
    return parent_of


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
