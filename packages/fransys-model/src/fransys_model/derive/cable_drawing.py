"""The cable drawing's facts and texts: its block, rows, pins and printed words.

Reached as `fransys_model.derive.cable_drawing.<name>`, never re-exported from `derive/__init__.py`
(model-0159): render, pdf and layout read it, a consumer never does. A block is one subject's
cables in one reading (`unit`, `None` for the absolute one). `all_cables` and `all_unit_cables`
stay off every `__all__`; layout reads them directly.
"""

from typing import Any

from fransys_kernel import render_id
from fransys_model.derive.facts.units import external, in_reading, is_harness
from fransys_model.kernel import Id, Model, value
from fransys_model.vocab.tables import items
lazy from fransys_model.vocab import Conductor, Function, Item, Port, Unit
lazy from fransys_model.vocab.facets.cable import OpenCoreFacet

from .cable_end_rank import cable_end_owner, cable_end_rank
from .core_pairs import (
    DrawnPair,
    cable_pairs,
    core_mark,
    drawn_pairs,
    pair_form,
    screened_pairs,
)
from .drawing_text import external_note
from .drawn_marks import DrawnBracket, PairRoom, pair_room
from .drawn_wires import DrawnWire, block_wires, wire_cores, wire_ends, wire_harness_subjects
from .harness import _facts_of, _pin_marking, all_cables, all_unit_cables
from .house_settings import word
from .indexes import build_indexes
from .lone_cable import lone_cable_harness
from .lookups import item_of_port, pin_order
from .open_core_ends import open_core_text
from .open_drawn import DrawnOpen, drawn_open_cores
from .order import designation_key, port_designation_key
from .texts.context import PrintContext
from .texts.core_text import core_text as core_text_of
from .texts.end_text import DRAWN_END, end_text
lazy from .rows import HarnessCable, HarnessCore

__all__ = [
    "DrawnBracket",
    "DrawnOpen",
    "DrawnPair",
    "DrawnPin",
    "DrawnWire",
    "PairRoom",
    "block_brackets",
    "block_cables",
    "block_drawn",
    "block_wires",
    "cable_block_key",
    "cable_heading",
    "cable_subject",
    "core_mark",
    "core_text",
    "core_texts",
    "drawn_blocks",
    "drawn_open_cores",
    "drawn_pairs",
    "drawn_pins",
    "end_by_others",
    "end_label",
    "end_rows",
    "open_core_text",
    "pair_room",
    "row_links",
    "wire_harness_subjects",
]


@value
class DrawnPin:
    """One cell of an end box: a port, its marking, and the cores of the block that land on it.

    `cores` runs in core-key order and gives the cell one place each (model-0168); a
    free pin has none and one place. A drawing value, not a row shape (model-0159).
    """

    port: Id[Port]
    marking: str
    landed: bool
    cores: tuple[Id[Any], ...] = ()


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
    """The subject's cables in the reading's own cable list, in its printed order.

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
    name = () if cabled else designation_key(model, subject)
    return (unit is not None, render_id(unit) if unit else "", not cabled, name, render_id(subject))


type _Key = tuple[int, tuple[object, ...]]
type _Keyed = list[tuple[_Key, HarnessCore]]


def _keyed_cores(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> _Keyed:
    """The block's cores in core-key order: cable place then core index, the wires after the cables.

    A wire's place is the number of cables; its key then runs by the natural order of its printed
    from-end, then to-end (model-0185), its index breaking a tie.
    """
    cables = block_cables(model, subject, unit)
    keyed: _Keyed = [
        ((place, (core.index,)), core) for place, c in enumerate(cables) for core in c.cores
    ]
    for core in wire_cores(model, subject, unit):
        ends = [port_designation_key(model, p, unit=unit) for p in (core.end_a, core.end_b)]
        keyed.append(((len(cables), (*ends, core.index)), core))
    return sorted(keyed, key=lambda pair: pair[0])


type _Opened = list[tuple[_Key, DrawnOpen]]


def _keyed_open(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> _Opened:
    """The block's open cores with the key of a core of the same cable and index."""
    cables = block_cables(model, subject, unit)
    return [((o.place, (o.index,)), o) for o in drawn_open_cores(model, cables)]


def _landed_by_end(
    model: Model, keyed: _Keyed, opened: _Opened
) -> dict[Id[Item], dict[Id[Port], _Key]]:
    """The block's landed ports with their lowest core key, grouped by their end item.

    An open core lands its one port; an unlanded one adds none.
    """
    keys: dict[Id[Port], _Key] = {}
    for key, core in keyed:
        for port in (core.end_a, core.end_b):
            keys[port] = min(keys.get(port, key), key)
    for key, one in opened:
        if one.landed:
            keys[one.anchor] = min(keys.get(one.anchor, key), key)
    ends: dict[Id[Item], dict[Id[Port], _Key]] = {}
    for port, key in keys.items():
        ends.setdefault(cable_end_owner(model, item_of_port(model, port)), {})[port] = key
    return ends


def _cores_by_port(
    model: Model, keyed: _Keyed, opened: _Opened, top: set[Id[Item]]
) -> dict[Id[Port], tuple[Id[Any], ...]]:
    """Each port's cores in core-key order; a core with both ends on a port counts once.

    An open core stands in its anchor port's cell (`DrawnOpen.anchor`), and one landed below also
    in the top row's end of its neighbour core.
    """
    entries: list[tuple[_Key, Id[Any], tuple[Id[Port], ...]]] = [
        (key, core.conductor, (core.end_a, core.end_b)) for key, core in keyed
    ]
    entries += [(key, one.core, _open_ports(model, one, top)) for key, one in opened]
    found: dict[Id[Port], list[Id[Any]]] = {}
    for _, core_id, ports in sorted(entries, key=lambda entry: entry[0]):
        for port in dict.fromkeys(ports):
            found.setdefault(port, []).append(core_id)
    return {port: tuple(cores) for port, cores in found.items()}


def _open_ports(model: Model, one: DrawnOpen, top: set[Id[Item]]) -> tuple[Id[Port], ...]:
    """The ports whose cells hold the open core's places."""
    above = [p for p in one.mate if cable_end_owner(model, item_of_port(model, p)) in top]
    if not one.landed:
        return tuple(above[:1]) or (one.anchor,)
    if cable_end_owner(model, item_of_port(model, one.anchor)) in top:
        return (one.anchor,)
    return (one.anchor, *above[:1])


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
    """The ends on the side of their group's first seed: that end stands on top."""
    first: dict[int, int] = {}
    for seed in seeds:
        first.setdefault(id(groups[seed]), groups[seed][seed])
    return {end for end, group in groups.items() if group[end] == first[id(group)]}


def _colouring(
    model: Model, subject: Id[Item], unit: Id[Unit] | None
) -> tuple[list[Id[Item]], set[Id[Item]], tuple[Id[Conductor], ...]]:
    """The block's end items in row order, its top row and its row links (model-0166).

    The cores, in core-key order, join groups of ends each with a side. After the last core each
    group's first seed stands on top; flipping a group never changes a link.
    """
    keyed = _keyed_cores(model, subject, unit)
    opened = _keyed_open(model, subject, unit)
    keys = {i: min(p.values()) for i, p in _landed_by_end(model, keyed, opened).items()}
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
    """The block's end items, top row then bottom row, each left to right (model-0166).

    The ends are coloured in core-key order (`_colouring`). A row runs by lowest core key, rank
    breaking ties. One end box per item, however many cables land on it.
    """
    ends, top, _ = _colouring(model, subject, unit)
    return tuple(i for i in ends if i in top), tuple(i for i in ends if i not in top)


def row_links(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> tuple[Id[Conductor], ...]:
    """The block's row links in core-key order: cores whose two ends stand in one row.

    A two-colourable block has none. In an odd ring the highest-keyed core is the one link.
    """
    return _colouring(model, subject, unit)[2]


def drawn_pins(
    model: Model, subject: Id[Item], item: Id[Item], unit: Id[Unit] | None
) -> tuple[DrawnPin, ...]:
    """The pins of the end box of `item` in the block of `unit`'s reading, drawing order.

    A port any core of the block lands on is landed, at the place of its lowest core key, and
    holds one place per core landing on it. A connector end then shows its other pins in
    `pin_order`; any other end shows landed pins only.
    """
    keyed = _keyed_cores(model, subject, unit)
    opened = _keyed_open(model, subject, unit)
    landed = _landed_by_end(model, keyed, opened).get(item, {})
    marked = {port: _pin_marking(model, port) for port in landed}
    cores = _cores_by_port(model, keyed, opened, _colouring(model, subject, unit)[1])
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


def _end_connector(
    model: Model, subject: Id[Item], unit: Id[Unit] | None, item: Id[Item]
) -> Id[Function] | None:
    """The connector function `item` is drawn as in the block, or `None` for any other end.

    The function is read off the ends of the block's cables and of its wires alike.
    """
    ends = [e for cable in block_cables(model, subject, unit) for e in cable.ends]
    found = [
        end.connector
        for end in (*ends, *wire_ends(model, subject, unit))
        if end.item == item and end.connector is not None
    ]
    return min(found, default=None)


def _connector_ports(
    model: Model, subject: Id[Item], unit: Id[Unit] | None, item: Id[Item]
) -> tuple[Id[Port], ...]:
    """Every port of the connector function `item` is drawn as, or `()` for any other end."""
    function = _end_connector(model, subject, unit, item)
    return () if function is None else build_indexes(model).ports_by_function.get(function, ())


def core_text(core: HarnessCore, mark: str = "") -> str:
    """A core's text: its index, its colour when it has one, its label when set, then `mark`.

    `mark` is `core_mark`'s pair word for the core, `""` for none.
    """
    return core_text_of(core.index, core.colour, core.label, mark)


def end_by_others(model: Model, item: Id[Item]) -> bool:
    """Whether an end of `item` is marked "by others": it is external, in every reading (BO4)."""
    return external(model, item)


def end_label(
    model: Model, item: Id[Item], unit: Id[Unit] | None, subject: Id[Item] | None = None
) -> str:
    """The end's designation in `unit`'s reading, plus " (by others)"; a blank end is "".

    With the block's `subject`, a device that prints its connectors as sub-parts names the
    connector the block's cores land on behind its designation: `+C1-A1-X1`.
    """
    facts = _facts_of(model, unit)
    ctx = PrintContext(reading=unit, location=facts.context)
    function = None if subject is None else _end_connector(model, subject, unit, item)
    return end_text(model, item, DRAWN_END, ctx, function)


def cable_heading(model: Model, cable: HarnessCable, unit: Id[Unit] | None) -> str:  # noqa: ARG001 - the reading no longer decides; callers keep one signature
    """The cable's heading: designation, pair form, "shielded", length, then "by others".

    Example: `-W3, shielded, 3000 mm`, or `-W5, 2x2x0.75, screened pairs, 25000 mm` (CC10:
    "screened pairs" only when every pair has a screen). A cable inside an external harness is
    external too.
    """
    parts = [cable.designation]
    pairs = cable_pairs(model, cable.cable)
    if pairs:
        parts.append(pair_form(pairs, cable.gauge_mm2))
    if screened_pairs(pairs):
        parts.append("screened pairs")
    if cable.shielded:
        parts.append("shielded")
    if cable.length_mm is not None:
        parts.append(f"{cable.length_mm} mm")
    if end_by_others(model, cable.cable):
        parts.append(external_note())
    return ", ".join(parts)


def core_texts(
    model: Model, subject: Id[Item], unit: Id[Unit] | None
) -> frozendict[Id[Conductor] | Id[OpenCoreFacet], str]:
    """The text of every core and single wire of the block, by core id (conductor or open core).

    A paired cable's cores add their pair word (`core_mark`); an open core adds `spare`.
    """
    cables = block_cables(model, subject, unit)
    found: dict[Id[Any], str] = {}
    for cable in cables:
        pairs = drawn_pairs(model, cable.cable)
        for core in cable.cores:
            found[core.conductor] = core_text(core, core_mark(pairs, core.index))
    spare = word(model, "spare")
    for one in drawn_open_cores(model, cables):
        pairs = drawn_pairs(model, one.cable)
        found[one.core] = open_core_text(spare, one.row, core_mark(pairs, one.index))
    for wire in block_wires(model, subject, unit):
        found[wire.conductor] = wire.text
    return frozendict(found)


def block_brackets(
    model: Model, subject: Id[Item], unit: Id[Unit] | None
) -> tuple[DrawnBracket, ...]:
    """The block's brackets in cable and pair order: a pair whose cores are neighbours."""
    cables = block_cables(model, subject, unit)
    opens = drawn_open_cores(model, cables)
    found: list[DrawnBracket] = []
    for cable in cables:
        ids: dict[int, Id[Any]] = {core.index: core.conductor for core in cable.cores}
        ids |= {one.index: one.core for one in opens if one.cable == cable.cable}
        found.extend(
            DrawnBracket(
                cable=cable.cable,
                label=pair.label,
                core_a=ids[pair.cores[0]],
                core_b=ids[pair.cores[1]],
            )
            for pair in drawn_pairs(model, cable.cable)
            if pair.bracket and all(index in ids for index in pair.cores)
        )
    return tuple(found)
