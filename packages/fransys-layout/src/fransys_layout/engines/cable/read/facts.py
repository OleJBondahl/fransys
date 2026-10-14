"""The widths and flags of one drawable block, read from the model's drawing facts."""

from dataclasses import dataclass
from itertools import count
from typing import Any
lazy from collections.abc import Iterator, Mapping

from fransys_layout.engines.cable.values import (
    BlockFacts,
    CableFacts,
    CoreFacts,
    EndFacts,
    PinFacts,
)
from fransys_layout.engines.schematic.read.reading import profile_and_sheet
from fransys_layout.geometry import WIRING_GRID, text_width
from fransys_model.derive import HarnessCable, HarnessCore, printed_designation
from fransys_model.derive.cable_drawing import (
    DrawnOpen,
    block_brackets,
    block_cables,
    block_wires,
    cable_heading,
    core_texts,
    drawn_open_cores,
    drawn_pins,
    end_by_others,
    end_label,
    end_rows,
    pair_room,
    row_links,
)
from fransys_model.derive.designation import end_outside_nested_unit
lazy from fransys_model.kernel import Id, Model


@dataclass
class _Ctx:
    """What `_cores_of` shares across one block's cables: the key counter, links, open cores."""

    keys: Iterator[int]
    links: set[Id[Any]]
    opens: tuple[DrawnOpen, ...]


def _end(
    model: Model, subject: Id[Any], item: Id[Any], unit: Id[Any] | None, height: int
) -> EndFacts:
    """One end's flags, label width and drawn pins."""
    blank = end_outside_nested_unit(model, item, unit)
    return EndFacts(
        item=item,
        dashed=end_by_others(model, item, unit),
        blank=blank,
        label_width=text_width(end_label(model, item, unit, subject), height=height),
        pins=tuple(
            PinFacts(
                port=pin.port,
                landed=pin.landed,
                marking_width=text_width(pin.marking, height=height),
                cores=pin.cores,
            )
            for pin in drawn_pins(model, subject, item, unit)
        ),
    )


def _cores_of(
    cable: HarnessCable, texts: Mapping[Id[Any], str], height: int, ctx: _Ctx
) -> tuple[CoreFacts, ...]:
    """One cable's cores and open cores by core number; keys run on over the whole block."""
    opens = {one.index: one for one in ctx.opens if one.cable == cable.cable}
    byindex: dict[int, HarnessCore | DrawnOpen] = {core.index: core for core in cable.cores}
    byindex |= opens
    found = []
    for index in sorted(byindex):
        core = byindex[index]
        if isinstance(core, DrawnOpen):
            found.append(
                CoreFacts(
                    key=next(ctx.keys),
                    conductor=core.core,
                    end_a=core.anchor,
                    end_b=core.anchor,
                    text_width=text_width(texts[core.core], height=height),
                    open=True,
                    landed=core.landed,
                )
            )
        else:
            found.append(
                CoreFacts(
                    key=next(ctx.keys),
                    conductor=core.conductor,
                    end_a=core.end_a,
                    end_b=core.end_b,
                    text_width=text_width(texts[core.conductor], height=height),
                    link=core.conductor in ctx.links,
                )
            )
    return tuple(found)


def _cables(
    model: Model, subject: Id[Any], unit: Id[Any] | None, height: int, keys: Iterator[int]
) -> tuple[CableFacts, ...]:
    """The block's cables in print order; core keys run on over the whole block."""
    cables = block_cables(model, subject, unit)
    ctx = _Ctx(
        keys=keys,
        links=set(row_links(model, subject, unit)),
        opens=drawn_open_cores(model, cables),
    )
    texts = core_texts(model, subject, unit)
    return tuple(
        CableFacts(
            cable=cable.cable,
            external=end_by_others(model, cable.cable, unit),
            heading_width=text_width(cable_heading(model, cable, unit), height=height),
            cores=_cores_of(cable, texts, height, ctx),
        )
        for cable in cables
    )


def _wires(
    model: Model, subject: Id[Any], unit: Id[Any] | None, height: int, keys: Iterator[int]
) -> tuple[CoreFacts, ...]:
    """The block's single wires in key order, their keys running on after the cables' cores."""
    links = set(row_links(model, subject, unit))
    return tuple(
        CoreFacts(
            key=next(keys),
            conductor=wire.conductor,
            end_a=wire.end_a,
            end_b=wire.end_b,
            text_width=text_width(wire.text, height=height),
            link=wire.conductor in links,
        )
        for wire in block_wires(model, subject, unit)
    )


def _harness_width(model: Model, subject: Id[Any], unit: Id[Any] | None, height: int) -> int | None:
    """The harness label's width, or None when the block's subject is a cable (no dashed box)."""
    first = block_cables(model, subject, unit)
    if first and first[0].cable == subject:
        return None
    return text_width(printed_designation(model, subject, unit=unit), height=height)


def _bracket_room(
    model: Model, subject: Id[Any], unit: Id[Any] | None, height: int, pad: int
) -> int:
    """The room a bracket and its label take over the cable box's rows, 0 with no bracket."""
    return pair_room(height, pad, WIRING_GRID).room if block_brackets(model, subject, unit) else 0


def block_facts(model: Model, subject: Id[Any], unit: Id[Any] | None) -> BlockFacts:
    """The facts of one drawable block."""
    profile, _, sheet_format = profile_and_sheet(model)
    height = profile.text_height
    top, bottom = end_rows(model, subject, unit)
    keys = count(1)
    return BlockFacts(
        subject=subject,
        unit=unit,
        sheet_format=sheet_format,
        text_height=height,
        turn_penalty=profile.route_turn_penalty,
        crossing_penalty=profile.route_crossing_penalty,
        pad=profile.marker_padding,
        cables=_cables(model, subject, unit, height, keys),
        top=tuple(_end(model, subject, item, unit, height) for item in top),
        bottom=tuple(_end(model, subject, item, unit, height) for item in bottom),
        harness_width=_harness_width(model, subject, unit, height),
        wires=_wires(model, subject, unit, height, keys),
        bracket_room=_bracket_room(model, subject, unit, height, profile.marker_padding),
    )
