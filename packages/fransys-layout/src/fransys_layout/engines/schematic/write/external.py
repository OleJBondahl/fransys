"""Private to `write/`: the `ExternalOutline` builder (OUTLINES BO7)."""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.write.keys import PREFIX, real_function
from fransys_model.kernel import make_id
from fransys_model.layout import ExternalOutline

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.engines.schematic.write.keys import PageId, WriteKeys
    from fransys_layout.stages import Layout
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.layout import Page


def external_outlines(
    keys: WriteKeys,
    layout: Layout,
    page_of: Mapping[PageId, Page],
    discriminator: Mapping[tuple[Id[Any], int, int], AuthoringKey],
    stamp: str,
) -> list[ExternalOutline]:
    """One `ExternalOutline` per run of an external item on a page, keyed by item and lead."""
    records = []
    for one in layout.external_outlines:
        real, pin = real_function(keys, one.lead)
        pin_part = (pin,) if pin is not None else ()
        extra = discriminator[one.lead, one.drawing_set, one.page]
        key = (
            *PREFIX,
            "external_outline",
            *keys.item[one.item],
            *keys.function[real],
            *pin_part,
            *extra,
        )
        records.append(
            ExternalOutline(
                id=make_id(ExternalOutline, key),
                key=key,
                item=one.item,
                page=page_of[one.drawing_set, one.page].id,
                x=one.box.x,
                y=one.box.y,
                width=one.box.width,
                height=one.box.height,
                produced_by=stamp,
            )
        )
    return records
