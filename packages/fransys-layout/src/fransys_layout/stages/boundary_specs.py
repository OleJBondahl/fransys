"""The specs and the black-box column of a unit's boundary functions (`replicate_boundaries`)."""

from typing import TYPE_CHECKING
lazy from collections.abc import Mapping, Sequence

from fransys_layout.stages.columns import boundary_key
from fransys_layout.stages.types import Cell, Column, Home

if TYPE_CHECKING:
    from fransys_layout.stages.types import FunctionSpec, Handle
    from fransys_model.kernel import AuthoringKey


def boundary_replica(
    spec: FunctionSpec,
    parent: Handle | None,
    parent_key: AuthoringKey | None,
    home_column: Column,
) -> Column:
    """The black-box column of `spec` in the unit's parent, in the home column's group."""
    return Column(
        key=boundary_key(spec.key, parent_key),
        cells=(Cell(function=spec.function, index=0, home=Home.ELSEWHERE),),
        group=home_column.group,
        role=home_column.role,
        location=home_column.location,
        unit=parent,
    )


def unit_specs(
    functions: Sequence[Handle],
    specs: Mapping[Handle, FunctionSpec],
    pins: Mapping[Handle, list[FunctionSpec]],
) -> list[FunctionSpec]:
    """The specs a unit's boundary draws, each once (model-0188).

    A function with pin views (a connector's, or a landed port of any function) is drawn as
    those pin cells; an idle port has no cell. One with a spec and no pin view is its own cell.
    """
    found: dict[Handle, FunctionSpec] = {}
    for function in functions:
        spec = specs.get(function)
        if function in pins:
            found.update((pin.function, pin) for pin in pins[function])
        elif spec is not None:
            found[spec.function] = spec
    return list(found.values())
