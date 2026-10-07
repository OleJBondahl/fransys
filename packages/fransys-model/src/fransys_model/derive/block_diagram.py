"""The block diagram's facts: the box a cable end reaches, its lines and its findings (BD1 to BD3).

Reached as `fransys_model.derive.block_diagram.<name>`, never re-exported from `derive/__init__.py`
(model-0167, as `cable_drawing` in model-0159): layout, render and pdf read it, a consumer never
does. A diagram belongs to a reading: `unit=None` is the system, a unit its own.
"""

from typing import Any, cast

from fransys_model.kernel import Id, Model, value
from fransys_model.kernel.ids import render_id
from fransys_model.layout import DiagramMarker, DiagramSheet, layout_of, sheet_for
from fransys_model.vocab.cables import is_cable
from fransys_model.vocab.enums import FunctionKind, PageKind
from fransys_model.vocab.membership import is_harness, item_chain, unit_own_roots
from fransys_model.vocab.tables import conductors, functions, items, ports
lazy from fransys_model.vocab.core import Item, Port, Unit

from .cable_drawing import end_by_others, end_label
from .designation import printed_designation, unit_list_context
from .drawing_text import (
    content_extent,
    frame_column,
    frame_row,
    outline_title,
    partner_position_text,
    product_location,
)
from .harness import top_level_cables, unit_cables
from .indexes import build_indexes
from .instance_tag import instance_name, instance_tags
from .lookups import cable_end_owner, item_of_port, unit_chain
from .mate_rows import mate_partners
from .natural_order import NaturalKey, natural_key
lazy from .rows import HarnessCable

__all__ = [
    "DIAGRAM_CABLE_FANOUT",
    "DIAGRAM_CABLE_ONE_BOX",
    "DIAGRAM_LOOSE_WIRE",
    "BoxEnd",
    "BoxKey",
    "DiagramFact",
    "DiagramLine",
    "box_dashed",
    "box_lines",
    "box_order",
    "diagram_facts",
    "diagram_lines",
    "diagram_marker_text",
    "end_box",
]

DIAGRAM_CABLE_ONE_BOX = "DIAGRAM_CABLE_ONE_BOX"
DIAGRAM_CABLE_FANOUT = "DIAGRAM_CABLE_FANOUT"
DIAGRAM_LOOSE_WIRE = "DIAGRAM_LOOSE_WIRE"

type BoxKey = Id[Unit] | Id[Item]

_PAIR = 2


@value
class BoxEnd:
    """The box one cable end reaches, and the item the end lands on inside it.

    `box` is a unit instance (`Id.kind` says so) or a root item. `landed` is the end's strip, or
    the item it lands on, after a plug has crossed its mate. `anchored` is true when that item is a
    terminal strip or a connector item, the only landings a tab names (BD4).
    """

    box: Id[Any]
    landed: Id[Item]
    anchored: bool


@value
class DiagramLine:
    """One line of a diagram: a cable between two boxes, `a` before `b` in box order.

    `designation` is the cable's, as the cable list prints it in that reading. A tab is the text at
    the line's end on that box, or `None` for none (BD4).
    """

    cable: Id[Item]
    a: Id[Any]
    b: Id[Any]
    designation: str
    tab_a: str | None
    tab_b: str | None


@value
class DiagramFact:
    """A finding of the diagram in data form: a code and its subject.

    The layout engine turns it into a `Finding`, with the severity its code carries.
    """

    code: str
    subject: Id[Any]


def _is_plug(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is a plug of a cable or harness: its parent is one, and it is no cable."""
    parent = items(model)[item].parent
    if parent is None or is_cable(model, item):
        return False
    return is_cable(model, parent) or is_harness(model, parent)


def _mated_item(model: Model, item: Id[Item]) -> Id[Item] | None:
    """The item mated to any function of `item`, the smallest id when several; `None` unmated."""
    partners = mate_partners(model)
    all_functions = functions(model)
    found = (
        all_functions[partner].item
        for function in build_indexes(model).functions_by_item.get(item, ())
        for partner in partners.get(function, ())
    )
    return min(found, default=None)


def _on_connector(model: Model, port: Id[Port]) -> bool:
    """Whether `port` belongs to a connector-kind function."""
    return functions(model)[ports(model)[port].function].kind is FunctionKind.CONNECTOR


def _box_of(model: Model, landed: Id[Item], unit: Id[Unit] | None) -> BoxKey | None:
    """The reading's box holding `landed`: a child unit instance, or the root item itself.

    A unit-held item climbs `unit_chain`, a unit-less one its `parent` chain. `None` when `landed`
    lies outside the reading or under a cable or harness.
    """
    root = tuple(item_chain(model, landed))[-1]
    if is_cable(model, root) or is_harness(model, root):
        return None
    owner = items(model)[landed].unit
    chain = [] if owner is None else unit_chain(model, owner)
    if unit is None:
        return chain[-1] if chain else root
    if unit not in chain:
        return None
    at = chain.index(unit)
    return root if at == 0 else chain[at - 1]


def end_box(model: Model, port: Id[Port], unit: Id[Unit] | None) -> BoxEnd | None:
    """The box the end at `port` reaches in `unit`'s reading, or `None` when it reaches none.

    A plug of a cable or harness crosses its mate (`mate_partners`) to the mated connector's item;
    an unmated plug reaches no box. The item then climbs to a root item, or in a unit-held case to
    the reading's child unit instance. An end outside the reading reaches none. One walk serves a
    cable core and a loose wire.
    """
    item = item_of_port(model, port)
    landed = cable_end_owner(model, item)
    anchored = landed != item or _on_connector(model, port)
    if _is_plug(model, item):
        mated = _mated_item(model, item)
        if mated is None:
            return None
        landed, anchored = mated, True
    box = _box_of(model, landed, unit)
    return None if box is None else BoxEnd(box=box, landed=landed, anchored=anchored)


def box_order(
    model: Model, box: BoxKey, unit: Id[Unit] | None
) -> tuple[tuple[NaturalKey, ...], str]:
    """Boxes in text order: by the lines a box prints, then by id."""
    return (tuple(natural_key(line) for line in box_lines(model, box, unit)), render_id(box))


def _cable_ends(
    model: Model, cable: HarnessCable, unit: Id[Unit] | None
) -> dict[Id[Any], list[BoxEnd]]:
    """The ends the cores of `cable` reach, by box, the boxes in text order."""
    found: dict[Id[Any], list[BoxEnd]] = {}
    for core in cable.cores:
        for port in (core.end_a, core.end_b):
            end = end_box(model, port, unit)
            if end is not None:
                found.setdefault(end.box, []).append(end)
    return dict(sorted(found.items(), key=lambda pair: box_order(model, pair[0], unit)))


def _reading_cables(model: Model, unit: Id[Unit] | None) -> tuple[HarnessCable, ...]:
    """BD1's lines: the reading's own cables, `Item.unit == unit`, harness cables included."""
    return top_level_cables(model) if unit is None else unit_cables(model, unit)


def _tab(model: Model, box: Id[Any], ends: list[BoxEnd], unit: Id[Unit] | None) -> str | None:
    """The tab at a line's end on `box`: its one strip or connector item, or `None`.

    Read in the box's own unit when line 1 holds its tag, else in the reading. `None` when the
    ends land on several items, on anything but a strip or connector, or on the box's own item.
    """
    landed = {end.landed for end in ends}
    if len(landed) != 1 or not all(end.anchored for end in ends) or box in landed:
        return None
    reading = box if box.kind == "unit" and instance_tags(model, box, unit) else unit
    return printed_designation(model, landed.pop(), unit=reading)


def diagram_lines(model: Model, unit: Id[Unit] | None) -> tuple[DiagramLine, ...]:
    """The lines of `unit`'s diagram, sorted; none means the reading gets no page (BD3).

    A cable reaching two boxes is one line. One box, or none: no line. Three or more: one line
    from the first box in text order to each other box.
    """
    lines = []
    for cable in _reading_cables(model, unit):
        ends = _cable_ends(model, cable, unit)
        boxes = tuple(ends)
        lines.extend(
            DiagramLine(
                cable=cable.cable,
                a=boxes[0],
                b=other,
                designation=cable.designation,
                tab_a=_tab(model, boxes[0], ends[boxes[0]], unit),
                tab_b=_tab(model, other, ends[other], unit),
            )
            for other in boxes[1:]
        )
    return tuple(
        sorted(
            lines,
            key=lambda line: (
                natural_key(line.designation),
                line.cable,
                render_id(line.a),
                render_id(line.b),
            ),
        )
    )


def box_lines(model: Model, box: BoxKey, unit: Id[Unit] | None) -> tuple[str, ...]:
    """The text of a box in `unit`'s reading (BD4).

    A unit instance: line 1, the location its items print then its tag (`-U1`), left out when both
    are empty; line 2, `outline_title`. An item: its `end_label`, one line.
    """
    if box.kind != "unit":
        return (end_label(model, cast("Id[Item]", box), unit),)
    instance = cast("Id[Unit]", box)
    tags = instance_tags(model, instance, unit)
    roots = unit_own_roots(model, instance)
    context = unit_list_context(model, unit, None)
    place = product_location(model, min(roots), context, unit=unit) if roots else ""
    head = place + (instance_name(tags) if tags else "")
    return (*((head,) if head else ()), outline_title(model, instance))


def box_dashed(model: Model, box: BoxKey, unit: Id[Unit] | None) -> bool:
    """Whether the box is drawn dashed: an item whose end is by others (CT5 G2)."""
    return box.kind != "unit" and end_by_others(model, cast("Id[Item]", box), unit)


def _cable_facts(model: Model, unit: Id[Unit] | None) -> tuple[DiagramFact, ...]:
    """`DIAGRAM_CABLE_ONE_BOX` and `DIAGRAM_CABLE_FANOUT`, one per cable that earns one."""
    facts = []
    for cable in _reading_cables(model, unit):
        count = len(_cable_ends(model, cable, unit))
        if count < _PAIR:
            facts.append(DiagramFact(code=DIAGRAM_CABLE_ONE_BOX, subject=cable.cable))
        elif count > _PAIR:
            facts.append(DiagramFact(code=DIAGRAM_CABLE_FANOUT, subject=cable.cable))
    return tuple(facts)


def _loose_wires(model: Model) -> tuple[DiagramFact, ...]:
    """`DIAGRAM_LOOSE_WIRE` for a conductor with no cable whose ends reach two different boxes."""
    facts = []
    for conductor in conductors(model).values():
        if conductor.carrier is not None:
            continue
        a, b = (end_box(model, port, None) for port in (conductor.a, conductor.b))
        if a is not None and b is not None and a.box != b.box:
            facts.append(DiagramFact(code=DIAGRAM_LOOSE_WIRE, subject=conductor.id))
    return tuple(facts)


def diagram_facts(model: Model, unit: Id[Unit] | None) -> tuple[DiagramFact, ...]:
    """The findings of `unit`'s diagram as facts, sorted by code and subject (BD3).

    `DIAGRAM_CABLE_ONE_BOX` and `DIAGRAM_CABLE_FANOUT` for a cable of the reading;
    `DIAGRAM_LOOSE_WIRE` in the system reading only: a unit's schematic draws every wire it has.
    """
    found = (*_cable_facts(model, unit), *(_loose_wires(model) if unit is None else ()))
    return tuple(sorted(found, key=lambda fact: (fact.code, render_id(fact.subject))))


def diagram_marker_text(model: Model, marker: DiagramMarker) -> str:
    """The text a cut marker prints: its partner's place on the other sheet, as `p2:3B`.

    The partner is the marker of the same line on the sheet `marker.at_sheet` of the same reading.
    """
    sheets, markers = layout_of(model, DiagramSheet), layout_of(model, DiagramMarker)
    own = sheets[marker.sheet]
    partner = next(
        m
        for m in markers.values()
        if sheets[m.sheet].unit == own.unit
        and sheets[m.sheet].number == marker.at_sheet
        and m.key[-3:] == marker.key[-3:]
    )
    page = sheet_for(model, PageKind.BLOCK_DIAGRAM)
    width = content_extent(page.content_width_mm, page.module_mm)
    column = frame_column(width, page.frame_columns, partner.x)
    row = frame_row(
        content_extent(page.content_height_mm, page.module_mm), page.frame_rows, partner.y
    )
    return partner_position_text((1, own.number, ()), (1, marker.at_sheet, ()), column, row)
