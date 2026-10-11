"""Read of the terminal pairs a contact image lists, by the rule render prints them by."""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages.images import ImageInputs
from fransys_model.derive import NO_PLACE, owned_contacts
from fransys_model.derive.contact_entries import contact_entries, image_order
from fransys_model.derive.drawing_text import coil_heading, contact_marks
from fransys_model.vocab.tables import functions as functions_table

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
    """The run's `ImageInputs`: the marks, and each contact function's owner item."""
    every = (*inputs.functions, *inputs.spares)  # A spare contact is listed, not drawn
    owners = {
        contact: item
        for item in {spec.item for spec in every}
        for contact in owned_contacts(model, item)
    }
    marks = image_marks_of(model, every)
    row_order = {function: _row_order(model, function) for function in marks}
    return ImageInputs(
        inputs.functions,
        inputs.sheet,
        inputs.profile,
        marks,
        owners,
        inputs.spares,
        row_order=row_order,
        no_place=NO_PLACE,
        heads={
            s.function: coil_heading(model, s.item)
            for s in inputs.functions
            if s.roles.contacts_apart
        },
    )


def _row_order(model: Model, function: Id[Any]) -> tuple[Any, ...]:
    """model-0138: a contact's first entry by `image_order`, the key of its table row."""
    no, nc = contact_entries(model, functions_table(model)[function])
    return min(map(image_order, (*no, *nc)), default=())
