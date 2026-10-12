"""Stage 3's sizing: column widths from the measured labels, and the contact-image reserves."""

from typing import TYPE_CHECKING, Any

from fransys_layout.stages._image_foot import marker_feet, with_marker_push
from fransys_layout.stages.box_reach import sized_columns
from fransys_layout.stages.images import image_reserves, with_flipped_below
from fransys_layout.stages.references import Wiring, side_reference_rooms
from fransys_layout.stages.tags import row_labels
from fransys_layout.stages.wide_columns import with_parts

from .read.contact_marks import image_inputs

if TYPE_CHECKING:
    from fransys_layout.stages import Column, ColumnWidth, DrawnFunction
    from fransys_layout.stages.images import ImageInputs
    from fransys_layout.stages.tags import TagTexts
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
    # Columns are sized with the keep-outs grown by the measured labels (`own_set`)
    # and by Room's first call for a reference beside an E or W port
    sides = side_reference_rooms(
        columns,
        drawn,
        Wiring(inputs.connections, inputs.net_groups),
        sheet=inputs.sheet,
        profile=inputs.profile,
    )
    # A box's pins stand a contact's width apart, from the keep-outs grown by the labels
    drawn, widths = sized_columns(columns, drawn, own_set, sides, inputs.profile)
    # Room for each contact image under its coil's lane, kept while placing
    img = image_inputs(model, inputs)
    return drawn, widths, img, reserves_for(inputs, drawn, img, columns)


def reserves_for(
    inputs: StageInputs,
    drawn: tuple[DrawnFunction, ...],
    img: ImageInputs,
    columns: tuple[Column, ...],
) -> dict[Any, Any]:
    """Each contact image's reserve in `columns`; again for the parts of a cut column (0182)."""
    every = (*inputs.functions, *inputs.spares)
    heights = {one.function: one.geometry.keepout.height for one in drawn}
    feet = marker_feet(drawn, inputs.power, inputs.profile)  # layout-0171
    reserves = image_reserves(columns, every, inputs.profile, img.marks, img.owners)
    reserves = with_marker_push(reserves, feet, inputs.profile)
    return with_flipped_below(reserves, columns, heights)


def recut_inputs(
    sizing: tuple[StageInputs, tuple[DrawnFunction, ...], ImageInputs],
    labels: tuple[TagTexts, tuple[Column, ...], tuple[LabelRequest, ...]],
    columns: tuple[Column, ...],
) -> tuple[dict[Any, Any], tuple[LabelRequest, ...]]:
    """The reserves and the row labels again once a column is cut in parts (layout-0182)."""
    inputs, drawn, img = sizing
    texts, every, requests = labels
    _, per_row = row_labels(texts, inputs.functions, with_parts(every, columns), requests)
    return reserves_for(inputs, drawn, img, columns), per_row
