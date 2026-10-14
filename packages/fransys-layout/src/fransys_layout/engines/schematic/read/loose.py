"""layout-0218: a function with nothing connected leaves the run before placement."""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.stages.exempt import open_ends
from fransys_model.derive import build_indexes, function_is_loose

from .units import open_end_inputs

if TYPE_CHECKING:
    from fransys_layout.stages import FunctionSpec
    from fransys_model.kernel import Model

    from . import StageInputs


def without_loose(model: Model, inputs: StageInputs) -> StageInputs:
    """`inputs` with its loose functions moved from `functions` to `loose`.

    A unit's open boundary function (`open_ends`) is never loose: its outside is the parent's.
    """
    edges = open_ends(inputs.functions, *open_end_inputs(model))
    loose = {
        spec.function
        for spec in inputs.functions
        if spec.function not in edges and _is_loose(model, spec)
    }
    return replace(
        inputs,
        functions=tuple(s for s in inputs.functions if s.function not in loose),
        loose=tuple(s for s in inputs.functions if s.function in loose),
    )


def _is_loose(model: Model, spec: FunctionSpec) -> bool:
    """A pin view reads its connector; an item box is loose when every function of it is."""
    if spec.pin_function is not None:
        return function_is_loose(model, spec.pin_function)
    if spec.roles.item_view:
        of_item = build_indexes(model).functions_by_item.get(spec.item, ())
        return all(function_is_loose(model, f) for f in of_item)
    return function_is_loose(model, spec.function)
