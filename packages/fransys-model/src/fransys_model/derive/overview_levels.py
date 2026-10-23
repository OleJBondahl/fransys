"""The overview's levels: what a level holds, its lines lifted with counts, a strip opened.

The system level is the block diagram's rows (O2), a unit level folds each nested unit and each
terminal strip into one box and lifts every connection to the boxes it joins (O3, O5). Reached as
`derive.overview_level` and `derive.strip_view` (model-0197).
"""

from functools import cache
from typing import Any, cast
lazy from collections.abc import Callable

from fransys_model.derive.facts.item_predicates import terminal_items
from fransys_model.derive.facts.units import boundary, item_chain, unit_items
from fransys_model.layout import OverviewRef, OverviewRefKind
from fransys_model.vocab.enums import Aspect, FunctionKind
from fransys_model.vocab.tables import conductors, functions, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Unit

from .block_diagram import BoxKey, box_dashed, box_lines, box_of, box_order, diagram_lines
from .designation import connector_designation, function_designation, printed_designation
from .designation_label import terminal_of
from .drawing_text import stub_far_end
from .facts.strips import strip_of
from .kinds import item_kind
from .lookups import effective_placement, item_of_port, strip_set
from .memo import Memo
from .order import natural_key
from .overview import links_of, unit_links
from .overview_names import display_unit
from .rows import (
    ItemKind,
    LineRef,
    OverviewBox,
    OverviewLevel,
    OverviewLine,
    OverviewLink,
    OverviewLinkKind,
    OverviewStub,
    StripTerminal,
    StripView,
)

__all__ = ["level_box", "open_strips", "overview_level", "strip_view"]

type _Order = Callable[[BoxKey], tuple[tuple[Any, ...], str]]

# The block diagram's box text and order, read once per box for the whole engine run (O25).
level_box_lines = Memo(box_lines)
level_box_order = Memo(box_order)


def level_box(model: Model, item: Id[Item], unit: Id[Unit] | None) -> BoxKey | None:
    """The box of `unit`'s level holding `item`: a nested unit, a strip, or its root item.

    `None` when the item lies outside `unit` or under a cable or harness.
    """
    found = box_of(model, item, unit)
    if found is None or found.kind == "unit":
        return found
    return next((one for one in item_chain(model, item) if one in strip_set(model)), found)


def _box(
    model: Model, box: BoxKey, unit: Id[Unit] | None, tabs: set[str], strips: dict[Id[Item], int]
) -> OverviewBox:
    """One box with its text, tabs and, for an item, its kind and effective nodes."""
    if box.kind == "unit":
        return OverviewBox(
            box=box,
            kind=None,
            lines=level_box_lines(model, box, unit),
            tabs=tuple(sorted(tabs, key=natural_key)),
            dashed=False,
            group=None,
            location=None,
            terminals=0,
        )
    item = cast("Id[Item]", box)
    return OverviewBox(
        box=box,
        kind=item_kind(model, item),
        lines=level_box_lines(model, box, unit),
        tabs=tuple(sorted(tabs, key=natural_key)),
        dashed=box_dashed(model, box, unit),
        group=effective_placement(model, item, Aspect.FUNCTION),
        location=effective_placement(model, item, Aspect.LOCATION),
        terminals=strips.get(item, 0),
    )


def _terminal_counts(model: Model) -> dict[Id[Item], int]:
    """Each strip's terminal count."""
    found: dict[Id[Item], int] = {}
    for terminal in terminal_items(model):
        strip = strip_of(model, terminal)
        if strip is not None:
            found[strip] = found.get(strip, 0) + 1
    return found


def _boxes(
    model: Model, unit: Id[Unit] | None, tabs: dict[Id[Any], set[str]], order: _Order
) -> tuple[OverviewBox, ...]:
    """The boxes of `tabs`' keys, in box text order."""
    strips = _terminal_counts(model)
    ordered = sorted(tabs, key=order)
    return tuple(_box(model, box, unit, tabs[box], strips) for box in ordered)


def _tab_text(model: Model, function: Id[Function], unit: Id[Unit]) -> str:
    """A boundary function as a tab reads: a connector by its designation, else with its name."""
    if functions(model)[function].kind is FunctionKind.CONNECTOR:
        return connector_designation(model, function, unit=unit)
    return function_designation(model, function, unit=unit)


def _unit_tabs(model: Model, unit: Id[Unit]) -> dict[Id[Any], set[str]]:
    """Every visible box of `unit`'s level, with the tabs standing on its border."""
    found: dict[Id[Any], set[str]] = {
        one.id: {_tab_text(model, f, unit) for f in boundary(model, one.id)}
        for one in units(model).values()
        if one.parent == unit
    }
    for item in sorted(unit_items(model, unit)):
        box = level_box(model, item, unit)
        if box is None:
            continue
        tab = found.setdefault(box, set())
        if box.kind != "unit" and box != item and item_kind(model, item) is ItemKind.CONNECTOR:
            tab.add(printed_designation(model, item, unit=unit))
    return found


def _line(link: OverviewLink, ends: tuple[BoxKey, BoxKey], order: _Order) -> OverviewLine:
    """The line for `link` between its two boxes, in box text order."""
    first, second = sorted(ends, key=order)
    return OverviewLine(
        ref=LineRef(a=first, b=second, kind=link.kind, via=link.via),
        label=link.via_designation or "",
        count=link.count,
        conductors=link.conductors,
    )


def _merge(lines: list[OverviewLine]) -> tuple[OverviewLine, ...]:
    """Lines with one `ref` joined: counts added, conductors united, in `ref` order."""
    joined: dict[LineRef, OverviewLine] = {}
    for line in lines:
        held = joined.get(line.ref)
        joined[line.ref] = (
            line
            if held is None
            else OverviewLine(
                ref=line.ref,
                label=line.label,
                count=held.count + line.count,
                conductors=tuple(sorted(held.conductors + line.conductors)),
            )
        )
    return tuple(
        sorted(
            joined.values(),
            key=lambda one: (one.ref.kind.value, one.ref.via is not None, one.ref.via, one.label),
        )
    )


def stub_far_root(model: Model, item: Id[Item]) -> OverviewRef:
    """The far end a stub names: the root of `item`'s parents, so a terminal stands as its strip."""
    return OverviewRef(kind=OverviewRefKind.ITEM, item=tuple(item_chain(model, item))[-1])


def stubs_of(
    model: Model, unit: Id[Unit], link: OverviewLink, inside: BoxKey, outside: Id[Item]
) -> list[OverviewStub]:
    """The stubs for the connections of `link` that leave the level at `inside`."""
    if not link.conductors:
        far = printed_designation(model, outside, unit=display_unit(model, outside, unit))
        return [
            OverviewStub(
                box=inside,
                kind=link.kind,
                via=link.via,
                far=far,
                ports="",
                end=stub_far_root(model, outside),
                count=link.count,
            )
        ]
    found = []
    for conductor in link.conductors:
        record = conductors(model)[conductor]
        near, far_port = (
            (record.a, record.b)
            if item_of_port(model, record.b) == outside
            else (record.b, record.a)
        )
        far, tails = stub_far_end(model, far_port, near, unit=display_unit(model, outside, unit))
        found.append(
            OverviewStub(
                box=inside,
                kind=link.kind,
                via=link.via,
                far=far,
                ports=tails,
                end=stub_far_root(model, outside),
                count=1,
            )
        )
    return found


def merge_stubs(
    model: Model, unit: Id[Unit], stubs: list[OverviewStub]
) -> tuple[OverviewStub, ...]:
    """`stubs` joined as `_merge_stubs` does, in the box order of `unit`'s level."""
    return _merge_stubs(stubs, cache(lambda box: level_box_order(model, box, unit)))


def _merge_stubs(stubs: list[OverviewStub], order: _Order) -> tuple[OverviewStub, ...]:
    """Equal stubs joined, counts added, in box text order."""
    joined: dict[tuple[Any, ...], OverviewStub] = {}
    for stub in stubs:
        key = (stub.box, stub.kind, stub.via, stub.far, stub.ports, stub.end)
        held = joined.get(key)
        joined[key] = (
            stub
            if held is None
            else OverviewStub(
                box=stub.box,
                kind=stub.kind,
                via=stub.via,
                far=stub.far,
                ports=stub.ports,
                end=stub.end,
                count=held.count + 1,
            )
        )
    return tuple(
        sorted(
            joined.values(),
            key=lambda one: (
                order(one.box),
                one.kind.value,
                one.via is not None,
                one.via,
                natural_key(one.far),
                one.ports,
            ),
        )
    )


def _unit_level(model: Model, unit: Id[Unit]) -> OverviewLevel:
    """`unit`'s level: its boxes, the lines between them and the stubs that leave it."""
    tabs = _unit_tabs(model, unit)
    order = cache(lambda box: level_box_order(model, box, unit))
    lines: list[OverviewLine] = []
    stubs: list[OverviewStub] = []
    for link in unit_links(model, unit):
        end_a, end_b = (level_box(model, item, unit) for item in (link.a, link.b))
        if end_a is not None and end_b is not None:
            if end_a != end_b:
                lines.append(_line(link, (end_a, end_b), order))
        elif end_a is not None or end_b is not None:
            inside, outside = (end_a, link.b) if end_a is not None else (end_b, link.a)
            stubs.extend(stubs_of(model, unit, link, cast("BoxKey", inside), outside))
    return OverviewLevel(
        unit=unit,
        boxes=_boxes(model, unit, tabs, order),
        lines=_merge(lines),
        stubs=_merge_stubs(stubs, order),
    )


def _system_level(model: Model) -> OverviewLevel:
    """The system level: the block diagram's boxes and lines for `unit=None`, one line per cable."""
    tabs: dict[Id[Any], set[str]] = {}
    lines = []
    for diagram in diagram_lines(model, None):
        for box, tab in ((diagram.a, diagram.tab_a), (diagram.b, diagram.tab_b)):
            tabs.setdefault(box, set())
            if tab is not None:
                tabs[box].add(tab)
        cores = tuple(
            sorted(c.id for c in conductors(model).values() if c.carrier == diagram.cable)
        )
        lines.append(
            OverviewLine(
                ref=LineRef(
                    a=diagram.a, b=diagram.b, kind=OverviewLinkKind.CABLE, via=diagram.cable
                ),
                label=diagram.designation,
                count=len(cores),
                conductors=cores,
            )
        )
    order = cache(lambda box: level_box_order(model, box, None))
    return OverviewLevel(
        unit=None, boxes=_boxes(model, None, tabs, order), lines=tuple(lines), stubs=()
    )


@Memo
def overview_level(model: Model, unit: Id[Unit] | None) -> OverviewLevel:
    """One level of the overview: the system (`unit=None`) or `unit` opened.

    The system level is `diagram_lines` of the block diagram: unit boxes with tabs, by-others items
    dashed, one line per cable. An opened unit has one box per nested unit (with its boundary
    tabs), per terminal strip (folded, with its terminal count) and per other root item, with
    connectors on a box as its tabs. A line joins two boxes per kind and carrier; a connection
    between items inside one box is dropped, and `count` is the connections lifted into the line.
    A connection to an item outside `unit` is a stub at the inside box, named by `stub_far_end`.
    Designations are relative to `unit`. Boxes and lines are in box text order.
    """
    return _system_level(model) if unit is None else _unit_level(model, unit)


def open_strips(level: OverviewLevel) -> tuple[Id[Item], ...]:
    """The strips of `level` that open: those holding at least one terminal, in box order."""
    strips = (b.box for b in level.boxes if b.kind is ItemKind.STRIP and b.terminals > 0)
    return cast("tuple[Id[Item], ...]", tuple(strips))  # a STRIP box is an item


def _terminal_lines(
    model: Model, unit: Id[Unit], terminal: Id[Item], strip: BoxKey
) -> tuple[OverviewLine, ...]:
    """The lines of one terminal to the other boxes of the level."""
    found = []
    for link in links_of(model, terminal):
        other = level_box(model, link.b if link.a == terminal else link.a, unit)
        if other is not None and other != strip:
            found.append(
                OverviewLine(
                    ref=LineRef(a=terminal, b=other, kind=link.kind, via=link.via),
                    label=link.via_designation or "",
                    count=link.count,
                    conductors=link.conductors,
                )
            )
    return _merge(found)


def _strip_order(model: Model, terminal: Id[Item]) -> tuple[Any, ...]:
    """A terminal's place on its strip: group in natural order, then index."""
    facet = terminal_of(model, terminal)
    return (natural_key(facet.group), facet.index, terminal) if facet else ((), 0, terminal)


@Memo
def strip_view(model: Model, strip: Id[Item], unit: Id[Unit]) -> StripView:
    """`strip` opened on `unit`'s level: its terminals in strip order, each with its lines.

    Strip order is the terminal's group (natural order) then its index. A line runs from the
    terminal to the box on the other end, left out when that end is the strip itself or lies
    outside `unit`.
    """
    terminals = terminal_items(model)
    held = [t for t in unit_items(model, unit) if t in terminals and strip_of(model, t) == strip]
    return StripView(
        strip=strip,
        terminals=tuple(
            StripTerminal(
                item=terminal,
                label=printed_designation(model, terminal, unit=unit),
                lines=_terminal_lines(model, unit, terminal, strip),
            )
            for terminal in sorted(held, key=lambda one: _strip_order(model, one))
        ),
    )
