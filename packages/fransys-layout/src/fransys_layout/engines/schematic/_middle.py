"""The engine's glue for the middle outlines (HL11, HL12, HL20, layout-0153)."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_layout.stages import LabelKind
from fransys_layout.stages.middle import group_index, middle_groups, strip_columns
from fransys_layout.stages.middle_reach import line_reach
from fransys_layout.stages.types import PlacedLabel, PlacedOutline

from .read.middle import middle_units

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages import Column, ColumnWidth
    from fransys_layout.stages.connector_boxes import PlacedConnectorBox
    from fransys_layout.stages.middle import MiddleUnit
    from fransys_layout.stages.middle_fold import GroupShape
    from fransys_layout.stages.pagerun import FirstCall, PageInputs
    from fransys_layout.stages.types import PagePlan, PlacedFunction
    from fransys_model.kernel import AuthoringKey, Id, Model

    from .read import StageInputs


def strip_middle(
    model: Model, inputs: StageInputs, columns: tuple[Column, ...]
) -> tuple[
    StageInputs,
    tuple[Column, ...],
    tuple[MiddleUnit, ...],
    dict[Id[Any], tuple[AuthoringKey, ...]],
]:
    """HL11: the middle units, their reached line views out of the columns, and the reach."""
    reach, units = line_reach(columns, middle_units(model, inputs.functions))
    if not units:
        return inputs, columns, units, {}
    columns, reach = strip_columns(columns, units, reach)
    return inputs, columns, units, reach


def middle_inputs(
    inputs: PageInputs,
    units: Sequence[MiddleUnit],
    sized: tuple[
        Sequence[Column], Mapping[Id[Any], tuple[AuthoringKey, ...]], Sequence[ColumnWidth]
    ],
) -> PageInputs:
    """The page inputs with each middle unit's group, its edges decided on the sized columns."""
    columns, reach, widths = sized
    width_of = {one.column: one.width for one in widths}
    groups = middle_groups(units, columns, reach, width_of, inputs.profile.text_height)
    return replace(inputs, middle=group_index(groups))


def moved_shapes(
    pages: Sequence[tuple[Any, FirstCall]],
    before: Sequence[PlacedFunction],
    after: Sequence[PlacedFunction],
) -> tuple[GroupShape, ...]:
    """Each folded shape moved as `shift_pages` moved its page (C22b), by a placement's move."""
    was = {(one.drawing_set, one.page): one.at for one in before}
    now = {(one.drawing_set, one.page): one.at for one in after}
    found = []
    for shape in (shape for _, call in pages for shape in call.shapes):
        page = (shape.drawing_set, shape.page)
        dx, dy = now[page].x - was[page].x, now[page].y - was[page].y
        found.append(shape.moved(dx, dy) if dx or dy else shape)
    return tuple(found)


def with_middle(
    plans: Sequence[PagePlan],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    outlines: tuple[PlacedOutline, ...],
    boxes: tuple[PlacedConnectorBox, ...],
    shapes: Sequence[GroupShape],
) -> tuple[list[Any], tuple[PlacedOutline, ...], tuple[PlacedConnectorBox, ...]]:
    """The pages with each middle outline's title, the outlines and the boxes with theirs."""
    titles: dict[tuple[int, int], list[PlacedLabel]] = {}
    for shape in shapes:
        titles.setdefault((shape.drawing_set, shape.page), []).append(_title(shape))
    found = []
    for plan, (placed, labels) in zip(plans, pages, strict=True):
        found.append((placed, (*labels, *titles.get((plan.drawing_set, plan.number), ()))))
    framed = tuple(
        PlacedOutline(
            unit=s.unit, lead=s.lead, drawing_set=s.drawing_set, page=s.page, box=s.outline
        )
        for s in shapes
    )
    folded = [box for shape in shapes for box in shape.boxes]
    # a leaving interface's views stay as the group's anchor: the outline's box replaces theirs
    taken = {(box.function, box.drawing_set, box.page) for box in folded}
    kept = (box for box in boxes if (box.function, box.drawing_set, box.page) not in taken)
    drawn = sorted(
        (*kept, *folded),
        key=lambda box: (box.drawing_set, box.page, box.function),
    )
    return found, (*outlines, *framed), tuple(drawn)


def _title(shape: GroupShape) -> PlacedLabel:
    return PlacedLabel(
        kind=LabelKind.TAG,
        subject=shape.lead,
        slot="outline_title",
        drawing_set=shape.drawing_set,
        page=shape.page,
        box=shape.title,
    )
