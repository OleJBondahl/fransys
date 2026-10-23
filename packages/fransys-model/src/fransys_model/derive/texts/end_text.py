"""The text of one cable or conductor end, in its three styles (design 7.7).

A port's far end, a cable-list end and a drawn end share one function and one `PrintContext`.
"""

from dataclasses import dataclass
from typing import cast

from fransys_model.derive.designation import (
    connector_segment,
    end_outside_nested_unit,
    product_designation,
)
from fransys_model.derive.drawing_text import external_note
from fransys_model.derive.facts.units import external
from fransys_model.derive.location_text import port_designation_in, product_designation_in
from fransys_model.derive.lookups import item_of_port
lazy from fransys_model.derive.texts.context import PrintContext
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Port


@dataclass(frozen=True, slots=True)
class EndTextStyle:
    """Which words an end prints: a `port` id, the connector `segment`, the `by_others` note."""

    port: bool = False
    segment: bool = False
    by_others: bool = False


FAR_END = EndTextStyle(port=True)
LIST_END = EndTextStyle(segment=True)
DRAWN_END = EndTextStyle(segment=True, by_others=True)


def end_designation(model: Model, item: Id[Item], ctx: PrintContext) -> str:
    """The end at `item`: absolute, `""` outside `ctx.reading`'s nested unit, else local."""
    if ctx.reading is None:
        return product_designation(model, item)
    if end_outside_nested_unit(model, item, ctx.reading):
        return ""
    return product_designation_in(model, item, ctx.location, unit=ctx.reading)


def end_text(
    model: Model,
    end: Id[Port] | Id[Item],
    style: EndTextStyle,
    ctx: PrintContext,
    connector: Id[Function] | None = None,
) -> str:
    """One end as printed; `end` is a port id for a `port` style, else an item id."""
    if style.port:
        port = cast("Id[Port]", end)
        if end_outside_nested_unit(model, item_of_port(model, port), ctx.reading):
            return ""
        return port_designation_in(model, port, ctx.location, unit=ctx.reading)
    item = cast("Id[Item]", end)
    label = end_designation(model, item, ctx)
    if style.segment and connector is not None and label:
        label += connector_segment(model, connector)
    if style.by_others and external(model, item):
        return f"{label} ({external_note()})"
    return label
