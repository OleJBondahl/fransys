"""Read of the terminal pairs a contact image lists, by the rule render prints them by."""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages.image_refs import holds_list, listed
from fransys_layout.stages.images import ImageInputs
from fransys_model.derive import NO_PLACE, contact_list_key, owned_contacts
from fransys_model.derive.drawing_text import coil_heading, contact_marks

from .units import containing_units

if TYPE_CHECKING:
    from fransys_layout.stages import FunctionSpec
    from fransys_model.kernel import Id, Model

    from . import StageInputs


def image_marks_of(
    model: Model, functions: tuple[FunctionSpec, ...]
) -> dict[Id[Any], tuple[list[str], list[str]]]:
    """Each contact function of `functions` -> the marks it lists under NO and under NC."""
    found: dict[Id[Any], tuple[list[str], list[str]]] = {}
    for spec in functions:
        if listed(spec):  # layout-0227: a group lists each member's marks
            marks = [contact_marks(model, member) for member in spec.members]
            found[spec.function] = (
                [m for no, _ in marks for m in no],
                [m for _, nc in marks for m in nc],
            )
    return found


def image_inputs(model: Model, inputs: StageInputs) -> ImageInputs:
    """The run's `ImageInputs`: the marks, and each contact function's owner item."""
    every = (*inputs.functions, *inputs.spares)  # A spare contact is listed, not drawn
    owners = {
        contact: item
        for item in {spec.item for spec in every}
        for contact in owned_contacts(model, item)
    }
    owners.update({s.function: s.switch_group for s in every if s.switch_group is not None})
    marks = image_marks_of(model, every)
    row_order = {function: contact_list_key(model, function) for function in marks}
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
            (s.function, one): coil_heading(model, s.item, unit=one)
            for s in inputs.functions
            if holds_list(s)
            for one in (None, *containing_units(model, s.unit))
        },
    )
