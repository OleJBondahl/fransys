"""Label requests rewritten per row and per unit set: who shows which tag (layout-0085).

The engine steps between column sizing and page placement that decide a tag's slot and text from
the rows of its columns: a run of terminals, a device's own terminal, a connector's pins, an
item's lanes, and a unit's own-set text. The texts themselves are the model's (`derive`): the
stage asks for them through `TagTexts`, one callable each, built by `read/tag_texts.py`, so it
reads a text only when a rule needs it.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast
lazy from collections.abc import Mapping
lazy from collections.abc import Set as AbstractSet

from fransys_layout.stages.slices import by_key
from fransys_layout.stages.types import Column, LabelKind, LabelRequest

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_layout.stages.types import (
        DrawnFunction,
        FunctionSpec,
        PagePlan,
        PlacedFunction,
    )
    from fransys_model.kernel import Id

_MIN_ROW_LANES = 2  # a "row" of lanes needs at least two lanes to share tags


@dataclass(frozen=True, slots=True)
class TagTexts:
    """The model's tag texts, one callable each, that the tag rules ask for a function at a time."""

    connector_designation: Callable[[Id[Any]], str]
    item_tag_text: Callable[[Id[Any]], str]
    is_device_terminal: Callable[[Id[Any]], bool]
    strip_tag_text: Callable[[Id[Any]], str]
    point_text: Callable[[Id[Any]], str]
    unit_tag_text: Callable[[Id[Any], str, Id[Any]], str | None]


def _device_terminal_tags(
    texts: TagTexts, specs: tuple[FunctionSpec, ...], requests: tuple[LabelRequest, ...]
) -> tuple[LabelRequest, ...]:
    """L2, F2: a device's own terminal is labelled like a port, item tag W, marking E, level."""
    devices = {
        spec.function
        for spec in specs
        if spec.roles.terminal
        and spec.pin_function is None
        and spec.function.kind == "function"
        and texts.is_device_terminal(spec.function)
    }
    kept = [r for r in requests if not (r.kind is LabelKind.TAG and r.subject in devices)]
    added = [
        LabelRequest(kind=LabelKind.TAG, subject=f, slot=slot, text=text(f), level=True)
        for f in sorted(devices)
        for slot, text in (("tag.strip", texts.strip_tag_text), ("tag.point", texts.point_text))
    ]
    return (*kept, *added)


def _terminal_row_tags(
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
    requests: tuple[LabelRequest, ...],
) -> tuple[LabelRequest, ...]:
    """R6 D1: a row of two or more terminals of one strip shows one strip tag, a point text each."""
    spec_of = {spec.function: spec for spec in specs}
    swapped: dict[Id[Any], list[LabelRequest]] = {}
    for column in columns:
        rows = by_key((c for c in column.cells if not c.side), lambda c: c.index)
        for cells in rows.values():
            lanes = [spec_of[cell.function] for cell in sorted(cells, key=lambda c: c.lane)]
            # the strip text is the item designation only (D12): two strips of one designation
            # print one text, so a run is the terminals of one strip item
            strips = {(spec.strip_text, spec.item_parent or spec.item) for spec in lanes}
            if (
                len(lanes) < _MIN_ROW_LANES
                or any(not s.roles.terminal for s in lanes)
                or lanes[0].strip_text == ""
            ):
                continue
            if len(strips) != 1:
                continue
            first = lanes[0]
            swapped[first.function] = [
                LabelRequest(
                    kind=LabelKind.TAG,
                    subject=first.function,
                    slot="tag.strip",
                    text=first.strip_text,
                ),
            ]
            for spec in lanes:
                swapped.setdefault(spec.function, []).append(
                    LabelRequest(
                        kind=LabelKind.TAG,
                        subject=spec.function,
                        slot="tag.point",
                        text=spec.point_text,
                    )
                )
    kept = [r for r in requests if not (r.kind is LabelKind.TAG and r.subject in swapped)]
    added = [request for found in swapped.values() for request in found]
    return (*kept, *added)


def _pin_rows(
    columns: tuple[Column, ...], specs: tuple[FunctionSpec, ...]
) -> tuple[frozenset[Id[Any]], frozenset[Id[Any]]]:
    """R7 A5: pins sharing a row with another pin of their connector; and each run's lane 0."""
    spec_of = {spec.function: spec for spec in specs}
    leads, rowed = set(), set()
    for column in columns:
        rows = by_key(
            (
                c
                for c in column.cells
                if spec_of[c.function].pin_function is not None and not c.side
            ),
            lambda c: (c.index, spec_of[c.function].pin_function),
        )
        for cells in rows.values():
            if len(cells) < _MIN_ROW_LANES:
                continue
            rowed.update(cell.function for cell in cells)
            leads.add(min(cells, key=lambda cell: cell.lane).function)
    return frozenset(leads), frozenset(rowed)


def pin_labels(
    texts: TagTexts,
    requests: tuple[LabelRequest, ...],
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
) -> tuple[LabelRequest, ...]:
    """R7 A / A5: a pin alone in its row shows its pin tag (-X5:2) and no marking."""
    pins = {spec.function: spec for spec in specs if spec.pin_function is not None}
    leads, rowed = _pin_rows(columns, specs)
    return tuple(
        pin_tag(texts, r, cast("Id[Any]", pins[r.subject].pin_function), leads)
        if r.kind is LabelKind.TAG and r.subject in pins
        else r
        for r in requests
        if not (r.kind is LabelKind.MARKING and r.subject in pins and r.subject not in rowed)
        and not (r.kind is LabelKind.TAG and r.subject in rowed - leads)
    )


def pin_tag(
    texts: TagTexts, request: LabelRequest, function: Id[Any], leads: frozenset[Id[Any]]
) -> LabelRequest:
    """A pin's TAG: the connector designation on a row lead (model-0073), else the full pin tag."""
    if request.subject not in leads:
        return replace(request, slot="tag.pin")
    return replace(request, slot="tag.conn", text=texts.connector_designation(function))


def one_item_tag(
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
    requests: tuple[LabelRequest, ...],
) -> tuple[LabelRequest, ...]:
    """R4: an item's own tag prints once per page, on its main view; contact, pin keep theirs."""
    spec_of = {spec.function: spec for spec in specs}
    views = {
        cell.function
        for column in columns
        for cell in column.cells
        if cell.function in spec_of and spec_of[cell.function].item == cell.function
    }
    return tuple(
        r
        for r in requests
        if not (
            r.kind is LabelKind.TAG
            and r.subject in spec_of
            and r.subject not in views
            and not spec_of[r.subject].roles.contact  # layout-0123: a contact prints its tag
            and spec_of[r.subject].pin_function is None  # layout-0131: a pin names below the item
            and spec_of[r.subject].item in views
        )
    )


def one_module_tag(
    requests: tuple[LabelRequest, ...],
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
) -> tuple[LabelRequest, ...]:
    """C6: PLC channels of one module at one y show the module tag once, on the leftmost."""
    item_of = {one.function: one.item for one in drawn if one.roles.plc_channel}
    lead: dict[tuple[Id[Any], int], Id[Any]] = {}
    for one in sorted(placed, key=lambda p: p.at.x):
        if one.function in item_of:
            lead.setdefault((item_of[one.function], one.at.y), one.function)
    followers = {
        one.function
        for one in placed
        if one.function in item_of and lead[item_of[one.function], one.at.y] != one.function
    }
    return tuple(r for r in requests if not (r.kind is LabelKind.TAG and r.subject in followers))


def _item_row_tags(
    texts: TagTexts,
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
    requests: tuple[LabelRequest, ...],
) -> tuple[Any, ...]:
    """C13(a): a row of one item's mixed-kind lanes shows the item's tag once, on lane 0."""
    spec_of = {spec.function: spec for spec in specs}
    lead, quiet, points = set(), set(), []
    for column in columns:
        rows = by_key((c for c in column.cells if not c.side and c.host is None), lambda c: c.index)
        for cells in rows.values():
            lanes = [spec_of[cell.function] for cell in sorted(cells, key=lambda c: c.lane)]
            if len(lanes) < _MIN_ROW_LANES or any(one.pin_function is not None for one in lanes):
                continue
            if len({one.item for one in lanes}) != 1 or len({one.kind for one in lanes}) == 1:
                continue
            lead.add(lanes[0].function)
            for one in lanes[1:]:
                quiet.add(one.function)
                if one.roles.terminal and one.point_text:
                    points.append(
                        LabelRequest(
                            kind=LabelKind.TAG,
                            subject=one.function,
                            slot="tag.point",
                            text=one.point_text,
                            level=True,  # F2: a device's own terminal
                        )
                    )
    return (*_item_lead_tags(texts, requests, spec_of, lead, quiet), *points)


def _item_lead_tags(
    texts: TagTexts,
    requests: tuple[LabelRequest, ...],
    spec_of: Mapping[Id[Any], FunctionSpec],
    lead: AbstractSet[Id[Any]],
    quiet: AbstractSet[Id[Any]],
) -> list[LabelRequest]:
    """`requests` without the `quiet` lanes' tags, each `lead` lane's tag as the item's."""
    kept = []
    for r in requests:
        if r.kind is LabelKind.TAG and r.subject in quiet:
            continue
        if r.kind is LabelKind.TAG and r.subject in lead:
            item = spec_of[r.subject]
            kept.append(replace(r, slot="tag.item", text=texts.item_tag_text(item.item)))
            continue
        kept.append(r)
    return kept


def _row_followers(
    columns: tuple[Column, ...], specs: tuple[FunctionSpec, ...]
) -> frozenset[Id[Any]]:
    """Lanes 1..n of a row whose (item, kind) is lane 0's: they draw no tag (R5 rule 2)."""
    spec_of = {spec.function: spec for spec in specs}
    found = set()
    for column in columns:
        rows = by_key((c for c in column.cells if not c.side), lambda c: c.index)
        for cells in rows.values():
            first = spec_of[cells[0].function]
            for cell in cells[1:]:
                spec = spec_of[cell.function]
                if spec.pin_function is None and (spec.item, spec.kind) == (
                    first.item,
                    first.kind,
                ):
                    found.add(cell.function)
    return frozenset(found)


def row_labels(
    texts: TagTexts,
    functions: tuple[FunctionSpec, ...],
    columns: tuple[Column, ...],
    requests: tuple[LabelRequest, ...],
) -> tuple[tuple[LabelRequest, ...], tuple[Any, ...]]:
    """`requests` rewritten per row of `columns`: sizing labels and pin base (R7 A, A5)."""
    followers = _row_followers(columns, functions)  # R5 rule 2: one item's row shows lane 0's tag
    per_row = tuple(r for r in requests if not (r.kind is LabelKind.TAG and r.subject in followers))
    per_row = _terminal_row_tags(columns, functions, per_row)
    per_row = _device_terminal_tags(texts, functions, per_row)
    per_row = _item_row_tags(texts, columns, functions, per_row)
    return pin_labels(texts, per_row, columns, functions), per_row


def unit_texts(
    texts: TagTexts,
    plan: PagePlan,
    requests: tuple[LabelRequest, ...],
    specs: tuple[FunctionSpec, ...],
) -> tuple[LabelRequest, ...]:
    """I4 R2: on a page of a unit's own set, a TAG of that unit's function carries its own text.

    That is the text printed there: only the unit's own aspects, below its sole root
    (`unit_tag_text`).
    """
    if plan.unit is None:
        return requests
    unit_of = {spec.function: spec.unit for spec in specs}
    found = []
    for r in requests:
        text = None
        if r.kind is LabelKind.TAG and unit_of.get(r.subject) is not None:
            text = texts.unit_tag_text(r.subject, r.slot, plan.unit)
        found.append(r if text is None else replace(r, text=text))
    return tuple(found)


def own_set_texts(
    texts: TagTexts,
    edges: frozenset[Id[Any]],
    requests: tuple[LabelRequest, ...],
    specs: tuple[FunctionSpec, ...],
) -> tuple[LabelRequest, ...]:
    """Short designations (owner): a unit's function is sized with the tag of its own set."""
    spec_of = {spec.function: spec for spec in specs}
    found = []
    for r in requests:
        spec = spec_of.get(r.subject)
        text = None
        if (
            r.kind is LabelKind.TAG
            and spec is not None
            and spec.unit is not None
            and (spec.pin_function or spec.function) not in edges
        ):
            text = texts.unit_tag_text(r.subject, r.slot, spec.unit)
        found.append(r if text is None else replace(r, text=text))
    return tuple(found)
