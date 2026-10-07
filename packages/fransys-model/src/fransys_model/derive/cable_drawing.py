"""The cable drawing's facts and texts: its block, rows, pins and printed words (CT5, CD3 to CD10).

Reached as `fransys_model.derive.cable_drawing.<name>`, never re-exported from `derive/__init__.py`
(model-0159): render, pdf and layout read it, a consumer never does. A block is one subject's
cables in one reading (`unit`, `None` for the absolute one). `all_cables` and `all_unit_cables`
stay off every `__all__`; layout reads them directly.
"""

from fransys_model.kernel import Id, Model, value
from fransys_model.kernel.ids import render_id
from fransys_model.vocab.membership import external, in_reading, is_harness
from fransys_model.vocab.tables import items
lazy from fransys_model.vocab import Conductor, Item, Port, Unit

from .cable_end_rank import cable_end_rank
from .drawing_text import external_note
from .harness import _end_designation, _facts_of, _pin_marking, all_cables, all_unit_cables
from .indexes import build_indexes
from .lone_cable import lone_cable_harness
from .lookups import cable_end_owner, item_of_port, pin_order
lazy from .rows import HarnessCable, HarnessCore

__all__ = [
    "DrawnPin",
    "block_cables",
    "cable_block_key",
    "cable_heading",
    "cable_subject",
    "core_text",
    "drawn_pins",
    "end_by_others",
    "end_label",
    "end_rows",
    "row_links",
]


@value
class DrawnPin:
    """One cell of an end box: a port, its marking, and whether a core of the block lands on it.

    A drawing value, not a row shape (model-0159).
    """

    port: Id[Port]
    marking: str
    landed: bool


def cable_subject(model: Model, cable: Id[Item]) -> Id[Item]:
    """What `cable` is drawn as: its harness with two or more cables or a part, else itself.

    A lone-cable harness is a cable (model-0148), so it never names the harness.
    """
    parent = items(model)[cable].parent
    if parent is None or not is_harness(model, parent) or lone_cable_harness(model, cable):
        return cable
    return parent


def cable_block_key(unit: Id[Unit] | None, subject: Id[Item]) -> str:
    """The key of the block of `subject` in `unit`'s reading: `render_id(subject)` when absolute.

    A unit's reading gives `unit:<hex>~item:<hex>`. `~` is in no rendered id and survives the
    facade's `_file_safe`, so two distinct blocks are two distinct intermediate files.
    """
    if unit is None:
        return render_id(subject)
    return f"{render_id(unit)}~{render_id(subject)}"


def block_cables(
    model: Model, subject: Id[Item], unit: Id[Unit] | None
) -> tuple[HarnessCable, ...]:
    """The subject's cables in the reading's own cable list, in its printed order (CT5-1B-FIX).

    The absolute reading is `all_cables`; a unit's is `all_unit_cables`, the cables whose own
    unit it is. The list is grouped by `cable_subject`; a cable with no designation is not in it.
    """
    all_items = items(model)
    reading = all_cables(model) if unit is None else all_unit_cables(model)
    return tuple(
        cable
        for cable in reading
        if cable_subject(model, cable.cable) == subject
        and (unit is None or all_items[cable.cable].unit == unit)
    )


def _port_keys(cables: tuple[HarnessCable, ...]) -> dict[Id[Port], tuple[int, int]]:
    """Each landed port's lowest core key: the cable's place in the block, then the core index."""
    keys: dict[Id[Port], tuple[int, int]] = {}
    for position, cable in enumerate(cables):
        for core in cable.cores:
            for port in (core.end_a, core.end_b):
                keys[port] = min(keys.get(port, (position, core.index)), (position, core.index))
    return keys


def _landed_by_end(
    model: Model, cables: tuple[HarnessCable, ...]
) -> dict[Id[Item], dict[Id[Port], tuple[int, int]]]:
    """The block's landed ports with their core keys, grouped by the end item they stand on."""
    ends: dict[Id[Item], dict[Id[Port], tuple[int, int]]] = {}
    for port, key in _port_keys(cables).items():
        owner = cable_end_owner(model, item_of_port(model, port))
        ends.setdefault(owner, {})[port] = key
    return ends


type _Groups = dict[Id[Item], dict[Id[Item], int]]


def _ordered_cores(cables: tuple[HarnessCable, ...]) -> list[HarnessCore]:
    """The block's cores in core-key order: the cable's place in the block, then the core index."""
    keyed = [((place, core.index), core) for place, c in enumerate(cables) for core in c.cores]
    return [core for _, core in sorted(keyed, key=lambda pair: pair[0])]


def _joined(groups: _Groups, one: Id[Item], two: Id[Item]) -> bool:
    """Join the groups of ends `one` and `two` on opposite sides; True if the core is a row link.

    A group maps each of its ends to a side. Both ends on one side of one group, or one item,
    leave the groups as they are and make the core a link.
    """
    mine, theirs = groups[one], groups[two]
    if mine is theirs:
        return mine[one] == mine[two]
    flip = int(mine[one] == theirs[two])
    for end, side in theirs.items():
        mine[end] = side ^ flip
        groups[end] = mine
    return False


def _top_row(groups: _Groups, seeds: list[Id[Item]]) -> set[Id[Item]]:
    """The ends on the side of their group's first seed: that end stands on top (CD5)."""
    first: dict[int, int] = {}
    for seed in seeds:
        first.setdefault(id(groups[seed]), groups[seed][seed])
    return {end for end, group in groups.items() if group[end] == first[id(group)]}


def _colouring(
    model: Model, subject: Id[Item], unit: Id[Unit] | None
) -> tuple[list[Id[Item]], set[Id[Item]], tuple[Id[Conductor], ...]]:
    """The block's end items in row order, its top row and its row links (CD5 at L1, model-0166).

    The cores, in core-key order, join groups of ends each with a side. After the last core each
    group's first seed (CD5's rule) stands on top; flipping a group never changes a link.
    """
    cables = block_cables(model, subject, unit)
    keys = {i: min(p.values()) for i, p in _landed_by_end(model, cables).items()}
    ends = sorted(keys, key=lambda item: (keys[item], cable_end_rank(model, item)))
    seeds = sorted(ends, key=lambda i: (not in_reading(model, i, unit), cable_end_rank(model, i)))
    groups: _Groups = {end: {end: 0} for end in ends}
    links = []
    for core in _ordered_cores(cables):
        one, two = (
            cable_end_owner(model, item_of_port(model, p)) for p in (core.end_a, core.end_b)
        )
        if _joined(groups, one, two):
            links.append(core.conductor)
    return ends, _top_row(groups, seeds), tuple(links)


def end_rows(
    model: Model, subject: Id[Item], unit: Id[Unit] | None
) -> tuple[tuple[Id[Item], ...], tuple[Id[Item], ...]]:
    """The block's end items, top row then bottom row, each left to right (CD5, model-0166).

    The ends are coloured in core-key order (`_colouring`). A row runs by lowest core key, rank
    breaking ties. One end box per item, however many cables land on it.
    """
    ends, top, _ = _colouring(model, subject, unit)
    return tuple(i for i in ends if i in top), tuple(i for i in ends if i not in top)


def row_links(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> tuple[Id[Conductor], ...]:
    """The block's row links in core-key order: cores whose two ends stand in one row (CD5, L1).

    A two-colourable block has none. In an odd ring the highest-keyed core is the one link.
    """
    return _colouring(model, subject, unit)[2]


def drawn_pins(
    model: Model, subject: Id[Item], item: Id[Item], unit: Id[Unit] | None
) -> tuple[DrawnPin, ...]:
    """The pins of the end box of `item` in the block of `unit`'s reading, drawing order (CD6, Q9).

    A port any core of the block lands on is landed, at the place of its lowest core key. A
    connector end then shows its other pins in `pin_order`; any other end shows landed pins only.
    """
    cables = block_cables(model, subject, unit)
    landed = _landed_by_end(model, cables).get(item, {})
    marked = {port: _pin_marking(model, port) for port in landed}
    pins = [
        DrawnPin(port=port, marking=marked[port], landed=True)
        for port in sorted(landed, key=lambda p: (landed[p], pin_order(marked[p], p)))
    ]
    free = sorted(
        (port for port in _connector_ports(model, cables, item) if port not in landed),
        key=lambda port: pin_order(_pin_marking(model, port), port),
    )
    pins.extend(
        DrawnPin(port=port, marking=_pin_marking(model, port), landed=False) for port in free
    )
    return tuple(pins)


def _connector_ports(
    model: Model, cables: tuple[HarnessCable, ...], item: Id[Item]
) -> tuple[Id[Port], ...]:
    """Every port of the connector function `item` is drawn as, or `()` for any other end."""
    found = [
        end.connector
        for cable in cables
        for end in cable.ends
        if end.item == item and end.connector is not None
    ]
    return build_indexes(model).ports_by_function.get(min(found), ()) if found else ()


def core_text(core: HarnessCore) -> str:
    """A core's text: its index, then its colour when it has one, then its label when set (CD7)."""
    return " ".join(part for part in (str(core.index), core.colour, core.label) if part)


def end_by_others(model: Model, item: Id[Item], unit: Id[Unit] | None) -> bool:
    """Whether an end of `item` is marked "by others": external, in the absolute reading (CD10)."""
    return unit is None and external(model, item)


def end_label(model: Model, item: Id[Item], unit: Id[Unit] | None) -> str:
    """The end's designation in `unit`'s reading, plus " (by others)" (CD10); a blank end is ""."""
    label = _end_designation(model, item, _facts_of(model, unit))
    if end_by_others(model, item, unit):
        return f"{label} ({external_note()})"
    return label


def cable_heading(model: Model, cable: HarnessCable, unit: Id[Unit] | None) -> str:
    """The cable's heading: designation, "shielded", length, then "by others" (CD7, CD10, CD-H1).

    Example: `-W3, shielded, 3000 mm`. A cable inside an external harness is external too.
    """
    parts = [cable.designation]
    if cable.shielded:
        parts.append("shielded")
    if cable.length_mm is not None:
        parts.append(f"{cable.length_mm} mm")
    if end_by_others(model, cable.cable, unit):
        parts.append(external_note())
    return ", ".join(parts)
