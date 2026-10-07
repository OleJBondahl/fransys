"""The widths and flags of one drawable block, read from the model's drawing facts."""

from itertools import count
from typing import Any

from fransys_layout.engines.cable.values import (
    BlockFacts,
    CableFacts,
    CoreFacts,
    EndFacts,
    PinFacts,
)
from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_layout.geometry import text_width
from fransys_model.derive import printed_designation
from fransys_model.derive.cable_drawing import (
    block_cables,
    cable_heading,
    core_text,
    drawn_pins,
    end_by_others,
    end_label,
    end_rows,
    row_links,
)
from fransys_model.derive.designation import end_outside_nested_unit
lazy from fransys_model.kernel import Id, Model


def _end(
    model: Model, subject: Id[Any], item: Id[Any], unit: Id[Any] | None, height: int
) -> EndFacts:
    """One end's flags, label width and drawn pins."""
    blank = end_outside_nested_unit(model, item, unit)
    return EndFacts(
        item=item,
        dashed=end_by_others(model, item, unit),
        blank=blank,
        label_width=text_width(end_label(model, item, unit), height=height),
        pins=tuple(
            PinFacts(
                port=pin.port,
                landed=pin.landed,
                marking_width=text_width(pin.marking, height=height),
            )
            for pin in drawn_pins(model, subject, item, unit)
        ),
    )


def _cables(
    model: Model, subject: Id[Any], unit: Id[Any] | None, height: int
) -> tuple[CableFacts, ...]:
    """The block's cables in print order; core keys run on over the whole block (CD5)."""
    keys = count(1)
    links = set(row_links(model, subject, unit))
    return tuple(
        CableFacts(
            cable=cable.cable,
            external=end_by_others(model, cable.cable, unit),
            heading_width=text_width(cable_heading(model, cable, unit), height=height),
            cores=tuple(
                CoreFacts(
                    key=next(keys),
                    conductor=core.conductor,
                    end_a=core.end_a,
                    end_b=core.end_b,
                    text_width=text_width(core_text(core), height=height),
                    link=core.conductor in links,
                )
                for core in cable.cores
            ),
        )
        for cable in block_cables(model, subject, unit)
    )


def _harness_width(model: Model, subject: Id[Any], unit: Id[Any] | None, height: int) -> int | None:
    """The harness label's width, or None when the block's subject is a cable (no dashed box)."""
    first = block_cables(model, subject, unit)
    if first and first[0].cable == subject:
        return None
    return text_width(printed_designation(model, subject, unit=unit), height=height)


def block_facts(model: Model, subject: Id[Any], unit: Id[Any] | None) -> BlockFacts:
    """The facts of one drawable block."""
    profile, _, sheet_format = profile_and_sheet(model)
    height = profile.text_height
    top, bottom = end_rows(model, subject, unit)
    return BlockFacts(
        subject=subject,
        unit=unit,
        sheet_format=sheet_format,
        text_height=height,
        turn_penalty=profile.route_turn_penalty,
        crossing_penalty=profile.route_crossing_penalty,
        pad=profile.marker_padding,
        cables=_cables(model, subject, unit, height),
        top=tuple(_end(model, subject, item, unit, height) for item in top),
        bottom=tuple(_end(model, subject, item, unit, height) for item in bottom),
        harness_width=_harness_width(model, subject, unit, height),
    )
