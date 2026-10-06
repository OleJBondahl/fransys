"""Read of the terminal pairs a contact image lists (C19), by the rule render prints them by."""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages.images import ImageInputs
from fransys_model.derive import NO_PLACE, owned_contacts
from fransys_model.derive.drawing_text import contact_marks

if TYPE_CHECKING:
    from fransys_layout.stages import FunctionSpec
    from fransys_model.kernel import Id, Model

    from . import StageInputs


def image_marks_of(
    model: Model, functions: tuple[FunctionSpec, ...]
) -> dict[Id[Any], tuple[list[str], list[str]]]:
    """Each contact function of `functions` -> the marks it lists under NO and under NC."""
    return {
        spec.function: contact_marks(model, spec.function)
        for spec in functions
        if spec.roles.contact
    }


def image_inputs(model: Model, inputs: StageInputs) -> ImageInputs:
    """C19: the run's `ImageInputs`: the marks, and each contact function's owner item (V10)."""
    every = (*inputs.functions, *inputs.spares)  # V1: a spare contact is listed, not drawn
    owners = {
        contact: item
        for item in {spec.item for spec in every}
        for contact in owned_contacts(model, item)
    }
    marks = image_marks_of(model, every)
    return ImageInputs(
        inputs.functions,
        inputs.sheet,
        inputs.profile,
        marks,
        owners,
        inputs.spares,
        no_place=NO_PLACE,
    )
