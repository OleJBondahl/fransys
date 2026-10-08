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
from .designation import item_designation, port_designation
from .drawing_text import external_note
from .drawn_wires import DrawnWire, block_wires, wire_cores, wire_ends, wire_harness_subjects
from .harness import _end_designation, _facts_of, _pin_marking, all_cables, all_unit_cables
from .indexes import build_indexes
from .lone_cable import lone_cable_harness
from .lookups import cable_end_owner, item_of_port, pin_order
from .natural_order import natural_key
lazy from .rows import HarnessCable, HarnessCore

__all__ = [
    "DrawnPin",
    "DrawnWire",
    "block_cables",
    "block_drawn",
    "block_wires",
    "cable_block_key",
    "cable_heading",
    "cable_subject",
    "core_text",
    "drawn_blocks",
    "drawn_pins",
    "end_by_others",
    "end_label",
    "end_rows",
    "row_links",
    "wire_harness_subjects",
]


@value
class DrawnPin:
    """One cell of an end box: a port, its marking, and the cores of the block that land on it.

    `cores` runs in core-key order and gives the cell one place each (CD6, P1, model-0168); a
    free pin has none and one place. A drawing value, not a row shape (model-0159).
    """

    port: Id[Port]
    marking: str
    landed: bool
    cores: tuple[Id[Conductor], ...] = ()


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


def block_drawn(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> bool:
    """Whether the block of `subject` in `unit`'s reading is drawn: it has a cable or a single wire.

    The one predicate of "this block is drawn" (model-0182): layout's engine and every PDF check
    ask it, so a harness of plain wires is drawn wherever a harness of cables is.
    """
    return bool(block_cables(model, subject, unit)) or bool(block_wires(model, subject, unit))


def drawn_blocks(model: Model) -> tuple[tuple[Id[Unit] | None, Id[Item]], ...]:
    """Every drawn (unit, subject) of the model once: absolute ones, then units', in print order.

    The one list of the blocks a harness drawing draws (model-0182): layout lays out exactly
    these and the PDF lists its wire-only harnesses from them. Each pair holds `block_drawn`.
    """
    all_items = items(model)
    pairs = [(None, cable_subject(model, c.cable)) for c in all_cables(model)]
    pairs += [
        (all_items[c.cable].unit, cable_subject(model, c.cable)) for c in all_unit_cables(model)
    ]
    cabled = set(pairs)
    for harness in wire_harness_subjects(model):
        pairs.append((None, harness))
        if all_items[harness].unit is not None:
            pairs.append((all_items[harness].unit, harness))
    drawn = [pair for pair in dict.fromkeys(pairs) if block_drawn(model, pair[1], pair[0])]
    return tuple(sorted(drawn, key=lambda pair: _block_key(model, pair, cabled=pair in cabled)))


def _block_key(
    model: Model, pair: tuple[Id[Unit] | None, Id[Item]], *, cabled: bool
) -> tuple[object, ...]:
    """Print order: absolute then units'; cable blocks by id, then wire-only ones by designation."""
    unit, subject = pair
    name = () if cabled else natural_key(item_designation(model, subject))
    return (unit is not None, render_id(unit) if unit else "", not cabled, name, render_id(subject))


type _Key = tuple[int, tuple[object, ...]]
type _Keyed = list[tuple[_Key, HarnessCore]]


def _keyed_cores(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> _Keyed:
    """The block's cores in core-key order: cable place then core index, the wires after the cables.

    A wire's place is the number of cables; its key then runs by the natural order of its printed
    from-end, then to-end (model-0185, SORT-ORDER O5), its index breaking a tie.
    """
    cables = block_cables(model, subject, unit)
    keyed: _Keyed = [
        ((place, (core.index,)), core) for place, c in enumerate(cables) for core in c.cores
    ]
    for core in wire_cores(model, subject, unit):
        ends = [
            natural_key(port_designation(model, p, unit=unit)) for p in (core.end_a, core.end_b)
        ]
        keyed.append(((len(cables), (*ends, core.index)), core))
    return sorted(keyed, key=lambda pair: pair[0])


def _landed_by_end(model: Model, keyed: _Keyed) -> dict[Id[Item], dict[Id[Port], _Key]]:
    """The block's landed ports with their lowest core key, grouped by their end item."""
    keys: dict[Id[Port], _Key] = {}
    for key, core in keyed:
        for port in (core.end_a, core.end_b):
            keys[port] = min(keys.get(port, key), key)
    ends: dict[Id[Item], dict[Id[Port], _Key]] = {}
    for port, key in keys.items():
        ends.setdefault(cable_end_owner(model, item_of_port(model, port)), {})[port] = key
    return ends


def _cores_by_port(keyed: _Keyed) -> dict[Id[Port], tuple[Id[Conductor], ...]]:
    """Each landed port's cores in core-key order; a core with both ends on a port counts once."""
    found: dict[Id[Port], list[Id[Conductor]]] = {}
    for _, core in keyed:
        for port in dict.fromkeys((core.end_a, core.end_b)):
            found.setdefault(port, []).append(core.conductor)
    return {port: tuple(cores) for port, cores in found.items()}


type _Groups = dict[Id[Item], dict[Id[Item], int]]


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
    keyed = _keyed_cores(model, subject, unit)
    keys = {i: min(p.values()) for i, p in _landed_by_end(model, keyed).items()}
    ends = sorted(keys, key=lambda item: (keys[item], cable_end_rank(model, item)))
    seeds = sorted(ends, key=lambda i: (not in_reading(model, i, unit), cable_end_rank(model, i)))
    groups: _Groups = {end: {end: 0} for end in ends}
    links = []
    for _, core in keyed:
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

    A port any core of the block lands on is landed, at the place of its lowest core key, and
    holds one place per core landing on it (P1). A connector end then shows its other pins in
    `pin_order`; any other end shows landed pins only.
    """
    keyed = _keyed_cores(model, subject, unit)
    landed = _landed_by_end(model, keyed).get(item, {})
    marked = {port: _pin_marking(model, port) for port in landed}
    cores = _cores_by_port(keyed)
    pins = [
        DrawnPin(port=port, marking=marked[port], landed=True, cores=cores[port])
        for port in sorted(landed, key=lambda p: (landed[p], pin_order(marked[p], p)))
    ]
    free = sorted(
        (port for port in _connector_ports(model, subject, unit, item) if port not in landed),
        key=lambda port: pin_order(_pin_marking(model, port), port),
    )
    pins.extend(
        DrawnPin(port=port, marking=_pin_marking(model, port), landed=False) for port in free
    )
    return tuple(pins)


def _connector_ports(
    model: Model, subject: Id[Item], unit: Id[Unit] | None, item: Id[Item]
) -> tuple[Id[Port], ...]:
    """Every port of the connector function `item` is drawn as, or `()` for any other end.

    The function is read off the ends of the block's cables and of its wires alike.
    """
    ends = [e for cable in block_cables(model, subject, unit) for e in cable.ends]
    found = [
        end.connector
        for end in (*ends, *wire_ends(model, subject, unit))
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
