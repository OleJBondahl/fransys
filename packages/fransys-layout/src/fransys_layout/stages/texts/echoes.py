"""A tag echo's `CROSS_REFERENCE` label requests, one per function of the item.

`references` decides which cuts are tag echoes (`References.echoes`); each request's text names
its partners' placed frame cells, so `texts` writes it once every page is placed. A naming
collision only with the reference marker: this is the tag echo's own label, still built
and measured here because `labels.py` sizes that label's box from real text, unlike a
reference's fixed box (`references.marker_boxes.reference_box_width`).
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_layout.stages.lookups import set_rank
from fransys_layout.stages.types import LabelKind, LabelRequest, RequestPartner
from fransys_model.derive.drawing_text import (
    frame_column,
    frame_row,
    partner_position_text,
)

from .markers import link_end, placed_world

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.stages.references.types import Cut, LocationPath
    from fransys_layout.stages.types import (
        DrawnFunction,
        Handle,
        PlacedFunction,
        SheetFormat,
    )

    from .markers import LinkEnd, PlacedWorld


@dataclass(frozen=True, slots=True)
class SetNames:
    """What a reference says of a drawing set: its location path and its rank among its unit's."""

    paths: Mapping[int, LocationPath]
    ranks: Mapping[int, int]


def echo_requests(
    echoes: tuple[Cut, ...],
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    *,
    sheet: SheetFormat,
    sets: SetNames,
) -> tuple[LabelRequest, ...]:
    """One `CROSS_REFERENCE` request per function of a tag echo, naming its partners ."""
    world = placed_world(placed, drawn)
    texts: dict[Handle, set[tuple[int, int, int, str]]] = defaultdict(set)
    partners: dict[Handle, set[tuple[int, int, int, Handle, int]]] = defaultdict(set)
    for cut in echoes:
        ends = tuple(link_end(end.ref, end.page, world) for end in cut.ends)
        for end, partner in (ends, ends[::-1]):
            column = frame_column(sheet.content_width, sheet.frame_columns, partner.at.x)
            texts[end.ref.function].add(
                (
                    partner.page[0],
                    partner.page[1],
                    column,
                    _tag_echo_text(end, partner, sheet, sets, world),
                )
            )
            partners[end.ref.function].add(
                (partner.page[0], partner.page[1], column, partner.ref.port, partner.at.x)
            )
    return tuple(
        LabelRequest(
            kind=LabelKind.CROSS_REFERENCE,
            subject=function,
            slot="tag",
            text=" ".join(text for *_, text in sorted(texts[function])),
            partners=tuple(
                RequestPartner(port=port, drawing_set=drawing_set, page=page, x=x)
                for drawing_set, page, _column, port, x in sorted(partners[function])
            ),
        )
        for function in sorted(texts)
    )


def _tag_echo_text(
    end: LinkEnd,
    partner: LinkEnd,
    sheet: SheetFormat,
    sets: SetNames,
    world: PlacedWorld,
) -> str:
    """What `end`'s tag-echo `CROSS_REFERENCE` says about `partner` (layout-0089)."""
    column = frame_column(sheet.content_width, sheet.frame_columns, partner.at.x)
    placement_y = world.where[partner.ref.function][partner.page].at.y
    row = frame_row(sheet.content_height, sheet.frame_rows, placement_y)
    seats = tuple(
        (set_rank(sets.ranks, one.page[0]), one.page[1], sets.paths.get(one.page[0], ()))
        for one in (end, partner)
    )
    same = end.page[0] == partner.page[0]
    return partner_position_text(*seats, column, row, same_set=same)  # The text render prints
