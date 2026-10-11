"""Stage 3's sizing: column widths from the measured labels, and the contact-image reserves."""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages.box_reach import sized_columns
from fransys_layout.stages.images import image_reserves, with_flipped_below
from fransys_layout.stages.references import Wiring, side_reference_rooms

from .read.contact_marks import image_inputs

if TYPE_CHECKING:
    from fransys_layout.stages import Column, ColumnWidth, DrawnFunction
    from fransys_layout.stages.images import ImageInputs
    from fransys_layout.stages.types import LabelRequest
    from fransys_model.kernel import Model

    from .read import StageInputs


def sized(
    model: Model,
    inputs: StageInputs,
    drawn: tuple[DrawnFunction, ...],
    columns: tuple[Column, ...],
    own_set: tuple[LabelRequest, ...],
) -> tuple[tuple[DrawnFunction, ...], tuple[ColumnWidth, ...], ImageInputs, dict[Any, Any]]:
    """The sized `drawn` functions and column widths, and each contact image's reserve."""
    # C8(b), S11: columns are sized with the keep-outs grown by the measured labels (`own_set`)
    # and by Room's first call for a reference beside an E or W port
    sides = side_reference_rooms(
        columns,
        drawn,
        Wiring(inputs.connections, inputs.net_groups),
        sheet=inputs.sheet,
        profile=inputs.profile,
    )
    # V5: a box's pins stand a contact's width apart, from the keep-outs grown by the labels
    drawn, widths = sized_columns(columns, drawn, own_set, sides, inputs.profile)
    # I4 Q1: room for each contact image under its coil's lane, kept while placing
    img = image_inputs(model, inputs)
    every = (*inputs.functions, *inputs.spares)
    heights = {one.function: one.geometry.keepout.height for one in drawn}
    reserves = image_reserves(columns, every, inputs.profile, img.marks, img.owners)
    return drawn, widths, img, with_flipped_below(reserves, columns, heights)
