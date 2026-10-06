"""Private to `write/`: the `Label` and `Outline` builders.

Refs: engine.md 7, model layout-namespace.md.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.write.keys import PREFIX, real_function
from fransys_model.kernel import make_id
from fransys_model.layout import CrossReferencePartner, Label, Outline
from fransys_model.layout import LabelKind as ModelLabelKind

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_layout.engines.schematic.write.keys import PageId, WriteKeys
    from fransys_layout.stages import Layout
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.layout import Page


def outlines(
    keys: WriteKeys,
    layout: Layout,
    page_of: Mapping[PageId, Page],
    discriminator: Mapping[tuple[Id[Any], int, int], AuthoringKey],
    stamp: str,
) -> list[Outline]:
    """I2a: one `Outline` per black box on a page, keyed by its unit and its lead member."""
    records = []
    for one in layout.outlines:
        real, pin = real_function(keys, one.lead)
        pin_part = (pin,) if pin is not None else ()
        extra = discriminator[one.lead, one.drawing_set, one.page]
        subject = (*keys.unit[one.unit], *keys.function[real], *pin_part)
        key = (*PREFIX, "outline", *subject, *extra)
        records.append(
            Outline(
                id=make_id(Outline, key),
                key=key,
                unit=one.unit,
                page=page_of[one.drawing_set, one.page].id,
                x=one.box.x,
                y=one.box.y,
                width=one.box.width,
                height=one.box.height,
                produced_by=stamp,
            )
        )
    return records


def labels(
    keys: WriteKeys,
    results: StageResults,
    page_of: Mapping[PageId, Page],
    discriminator: Mapping[tuple[Id[Any], int, int], AuthoringKey],
    stamp: str,
) -> list[Label]:
    """One `Label` per placed label: its subject, kind and slot and the box's top-left corner."""
    owner_of = {
        port.port: function.function for function in results.drawn for port in function.ports
    }
    records = []
    for label in results.layout.labels:
        kind = ModelLabelKind[label.kind.name]
        marking = kind is ModelLabelKind.MARKING
        real, pin = None, None  # bound on every path; only a function label sets them
        if marking:
            tail = keys.port[label.subject]
            extra = discriminator[owner_of[label.subject], label.drawing_set, label.page]
        else:
            real, pin = real_function(keys, label.subject)
            tail = keys.function[real]
            extra = discriminator[label.subject, label.drawing_set, label.page]
        written_slot = label.slot
        if not marking and pin is not None and label.slot == "tag.pin":
            written_slot = f"tag.pin.{pin}"  # R7 A: the pin view's pin, for render
        slot = (written_slot,) if written_slot else ()
        key = (*PREFIX, "label", *tail, kind.value, *slot, *extra)
        partners = tuple(
            CrossReferencePartner(
                port=partner.port, page=page_of[partner.drawing_set, partner.page].id, x=partner.x
            )
            for partner in label.partners
        )
        records.append(
            Label(
                id=make_id(Label, key),
                key=key,
                page=page_of[label.drawing_set, label.page].id,
                function=None if marking else real,
                port=label.subject if marking else None,
                conductor=None,
                kind=kind,
                slot=written_slot,
                x=label.box.x,
                y=label.box.y,
                # D13: the reserved box, measured once by the stage; render draws from it
                width=label.box.width,
                height=label.box.height,
                produced_by=stamp,
                partners=partners,
            )
        )
    return records
