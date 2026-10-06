"""Harness cable queries: a harness's cables, the top-level cables and cable list.

See derive-queries-structure.md.

Decision 0027 and units spec U3; all built on the same per-cable facts and end discovery.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.kernel import Id, Model, SchemaError
from fransys_model.kernel.ids import render_id
from fransys_model.vocab.cables import cable_items
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.membership import cable_children
from fransys_model.vocab.tables import (
    facets_of,
    functions,
    items,
    parts,
    ports,
)
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.vocab.core import Item, Unit

from .designation import (
    _own_designation,
    cable_end_rank,
    end_outside_nested_unit,
    printed_designation,
    prints_connector_label,
    product_designation,
    unit_list_context,
)
from .drawing_text import product_designation_in
from .lookups import (
    cable_end_owner,
    connector_facets,
    item_of_port,
    pin_order,
    require,
)
from .natural_order import natural_key
from .reports import cable_rows
from .rows import CableListRow, ContentsRow, HarnessCable, HarnessCore, HarnessEnd, HarnessPin

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_model.vocab.aspects import AspectNode
    from fransys_model.vocab.connectivity import Conductor
    from fransys_model.vocab.core import Port
    from fransys_model.vocab.facets.connector import ConnectorFacet
    from fransys_model.vocab.templates import FunctionTemplate, Part

    from .rows import CableRow


def _cores(
    rows: tuple[CableRow, ...], labels: frozendict[Id[Conductor], str | None]
) -> tuple[HarnessCore, ...]:
    return tuple(
        HarnessCore(
            conductor=row.conductor,
            index=row.index,
            colour=row.colour,
            label=labels.get(row.conductor),
            end_a=row.end_a,
            end_a_designation=row.end_a_designation,
            end_b=row.end_b,
            end_b_designation=row.end_b_designation,
        )
        for row in rows
    )


def _pin_marking(model: Model, port: Id[Port]) -> str:
    """The label of one landed pin: a terminal's own designation, or its port's own name.

    A terminal with a parent is marked by its bare `group:index`, never dashed or strip-prefixed.
    Any other port keeps its raw port name.
    """
    owner = item_of_port(model, port)
    if cable_end_owner(model, owner) != owner:
        return _own_designation(model, owner)
    return ports(model)[port].name


def _end_designation(model: Model, item: Id[Item], facts: _Facts) -> str:
    """The text of the end at `item`: `product_designation`, or `facts.unit`'s own reading of it.

    With a unit it is `""` outside a nested unit, else `product_designation_in` at its location.
    A unit's drawing shows nothing above the unit.
    """
    if facts.unit is None:
        return product_designation(model, item)
    if end_outside_nested_unit(model, item, facts.unit):
        return ""
    return product_designation_in(model, item, facts.context, unit=facts.unit)


def _end(model: Model, item: Id[Item], landed: list[Id[Port]], facts: _Facts) -> HarnessEnd:
    """The end at `item`: its connector, when a core lands on one, and the pins landed on.

    `designation` is `product_designation`, or `_end_designation`'s reading in a unit's drawing.
    An end outside the unit blanks every fact: `connector`, `style`, `pincount`, `gender`, `mpn`.
    """
    shapes = facts.shapes
    outside = end_outside_nested_unit(model, item, facts.unit)
    all_functions = functions(model)
    landed_on = {ports(model)[port].function for port in landed}
    # The smallest function id when several qualify: the facet lookup `connector_rows` uses.
    connector = min(
        (
            function
            for function in landed_on
            if all_functions[function].kind is FunctionKind.CONNECTOR
            and all_functions[function].template in shapes
            and prints_connector_label(model, function)
        ),
        default=None,
    )
    template = None if connector is None else all_functions[connector].template
    shape = None if template is None else shapes.get(template)
    part_id = items(model)[item].part
    return HarnessEnd(
        item=item,
        designation=_end_designation(model, item, facts),
        connector=None if outside else connector,
        style=None if outside or shape is None else shape.style,
        pincount=None if outside or shape is None else shape.pincount,
        gender=None if outside or shape is None else shape.gender,
        mpn=None if outside or part_id is None else parts(model)[part_id].mpn,
        pins=tuple(
            HarnessPin(port=port, marking="" if outside else _pin_marking(model, port))
            for port in sorted(landed, key=lambda p: pin_order(_pin_marking(model, p), p))
        ),
    )


def _ends(model: Model, cores: tuple[HarnessCore, ...], facts: _Facts) -> tuple[HarnessEnd, ...]:
    landed: dict[Id[Item], set[Id[Port]]] = {}
    for core in cores:
        for port in (core.end_a, core.end_b):
            node = cable_end_owner(model, item_of_port(model, port))
            landed.setdefault(node, set()).add(port)
    ends = [_end(model, item, list(found), facts) for item, found in landed.items()]
    return tuple(sorted(ends, key=lambda end: cable_end_rank(model, end.item)))


@dataclass(frozen=True, slots=True)
class _Facts:
    """What a cable's own facts are read from, looked up once per query.

    `unit` is the unit whose document the query is for (`None`: absolute).
    `context` is the location its ends print against, or `None`.
    """

    lengths: dict[Id[Item], int | None]
    products: dict[Id[Part], CableProductFacet]
    labels: frozendict[Id[Conductor], str | None]
    shapes: frozendict[Id[FunctionTemplate], ConnectorFacet]
    all_parts: frozendict[Id[Part], Part]
    unit: Id[Unit] | None
    context: Id[AspectNode] | None


def _cable_facts(model: Model, cable: Id[Item], facts: _Facts) -> HarnessCable:
    """`cable`'s own `HarnessCable`: product facts, cores and ends, shared by every cable query.

    Absolute unless `facts.unit` is set (`_facts_of`): then the cable's designation, its cores'
    end texts and its ends are that unit's own reading (decision model-0090).
    """
    part_id = items(model)[cable].part
    part = None if part_id is None else facts.all_parts[part_id]
    product = None if part_id is None else facts.products.get(part_id)
    cores = _cores(cable_rows(model, cable, unit=facts.unit), facts.labels)
    return HarnessCable(
        cable=cable,
        designation=printed_designation(model, cable, unit=facts.unit),
        mpn=None if part is None else part.mpn,
        description=None if part is None else part.description,
        core_count=None if product is None else len(product.core_colours),
        gauge_mm2=None if product is None else product.gauge_mm2,
        shielded=None if product is None else product.shielded,
        length_mm=facts.lengths.get(cable),
        cores=cores,
        ends=_ends(model, cores, facts),
    )


def _facts_of(model: Model, unit: Id[Unit] | None = None) -> _Facts:
    """Every lookup a cable's own facts are read from, built once for the whole query.

    `unit` makes the query the unit document's own (decision model-0090); `None` is absolute.
    """
    return _Facts(
        lengths={facet.subject: facet.length_mm for facet in facets_of(model, CableFacet).values()},
        products={facet.subject: facet for facet in facets_of(model, CableProductFacet).values()},
        labels=frozendict(
            {facet.subject: facet.label for facet in facets_of(model, WireFacet).values()}
        ),
        shapes=connector_facets(model),
        all_parts=parts(model),
        unit=unit,
        context=unit_list_context(model, unit, None),
    )


def _cable_ids_of_unit(model: Model, unit: Id[Unit] | None) -> set[Id[Item]]:
    """Every cable item (`is_cable`) whose own `Item.unit` is `unit` (`None`: no unit at all).

    The one selection rule behind `top_level_cables`, `cable_list_rows` and `unit_cables`.
    """
    all_items = items(model)
    return {item for item in cable_items(model) if all_items[item].unit == unit}


def _top_level_cable_ids(model: Model) -> set[Id[Item]]:
    """Every cable item (`is_cable`) with no unit (units spec U3's "cable drawings" rule).

    Shared by `top_level_cables` and `cable_list_rows` so the two can never disagree about
    which cables are top-level. A cable is `is_cable`'s own (decision model-0108).
    """
    return _cable_ids_of_unit(model, None)


def _sorted_cables(
    model: Model, cables: set[Id[Item]], unit: Id[Unit] | None = None
) -> tuple[HarnessCable, ...]:
    """`cables` built by `_cable_facts`, sorted by `(designation, id)`, `harness_cables`' order.

    `unit` is `_facts_of`'s: the unit whose own document reads them, `None` for the absolute text.
    """
    facts = _facts_of(model, unit)
    found = [_cable_facts(model, cable, facts) for cable in cables]
    return tuple(sorted(found, key=lambda cable: (natural_key(cable.designation), cable.cable)))


def cable_title(cable: HarnessCable) -> str:
    """The cable's printed title: its designation, then its MPN when it has one.

    Args:
        cable: The cable's own row to render.

    Returns:
        The designation, a space, and the MPN when `cable.mpn` is set; the designation alone
        otherwise.
    """
    return f"{cable.designation} {cable.mpn or ''}".strip()


def harness_cables(model: Model, harness: Id[Item]) -> tuple[HarnessCable, ...]:
    """One `HarnessCable` per child of `harness` that is a cable (`is_cable`).

    Cores are `cable_rows`' own. Ends are one per item a core lands on, in `cable_end_rank` order;
    a terminal's end is its strip. A non-cable child is left out.

    Args:
        model: The frozen model to read.
        harness: The item whose cable children to list.

    Returns:
        The cable children's `HarnessCable`s, sorted by `(designation, id)`.

    Raises:
        SchemaError: `harness` is not an item, or a cable or core end has no designation.
    """
    require(items(model).get(harness), "item", harness)
    facts = _facts_of(model)
    found = [_cable_facts(model, child, facts) for child in cable_children(model, harness)]
    return tuple(sorted(found, key=lambda cable: (natural_key(cable.designation), cable.cable)))


def top_level_cables(model: Model) -> tuple[HarnessCable, ...]:
    """Every cable item with no unit, harness cables included, as `HarnessCable`.

    Selected as `cable_list_rows` selects (`_top_level_cable_ids`): every cable item
    (`is_cable`) with `unit=None`, a cable inside a harness included. Built by
    `_cable_facts`, as in `harness_cables`. Sorted by `(designation, id)`.

    Args:
        model: The frozen model to read.

    Returns:
        Every top-level cable (`unit=None`), sorted by `(designation, id)`.

    Raises:
        SchemaError: a cable, or an item one of its cores lands on, has no designation.
    """
    return _sorted_cables(model, _top_level_cable_ids(model))


def unit_cables(model: Model, unit: Id[Unit]) -> tuple[HarnessCable, ...]:
    """Every cable item that belongs to `unit` itself, as `HarnessCable`.

    Cables whose own `Item.unit` is `unit`, not a nested unit's, read unit-relative:
    an end outside a NESTED `unit` has `designation == ""`.

    Args:
        model: The frozen model to read.
        unit: The unit whose own cables to list.

    Returns:
        Every cable whose `Item.unit` is `unit`, sorted by `(designation, id)`.

    Raises:
        SchemaError: `unit` is not a unit, or a cable or core end has no designation.
    """
    require(units_table(model).get(unit), "unit", unit)
    return _sorted_cables(model, _cable_ids_of_unit(model, unit), unit)


def unit_cable_page_key(unit: Id[Unit], cable: Id[Item]) -> str:
    """The page key of `cable`'s drawing in `unit`'s own document: `unit:<hex>~item:<hex>`.

    One key per (unit, cable), so the same cable drawn in two documents (its harness's item
    document keys it `render_id(cable)`) never shares a page key with either. `~` occurs in no
    rendered id (a kind has no `:`, a value is a hex digest), and survives the facade's
    `_file_safe` (`:` becomes `-`, giving `unit-<hex>~item-<hex>`), which Windows accepts, so
    two distinct pairs are two distinct intermediate files.

    Args:
        unit: The unit whose own document the cable is drawn in.
        cable: The cable item being drawn.

    Returns:
        The page key, unique to this `(unit, cable)` pair.
    """
    return f"{render_id(unit)}~{render_id(cable)}"


def all_cables(model: Model) -> tuple[HarnessCable, ...]:
    """Every cable item whose ends can all be rendered, whatever its harness or unit.

    A cable with an end that has no designation yet is left out, not raised on.
    Sorted by `(designation, id)`, `harness_cables`' own order.
    """
    return _readable_cables(model, ((cable, None) for cable in _all_cable_ids(model)))


def all_unit_cables(model: Model) -> tuple[HarnessCable, ...]:
    """Every unit-owned cable `all_cables` finds, read as its own unit's document reads it.

    Built with that unit's facts, so its ends are what `unit_cables` draws; no-unit cables are out.
    Unreadable cables are left out, the order is `all_cables`', each unit's facts are built once.
    """
    all_items = items(model)
    return _readable_cables(
        model,
        (
            (cable, all_items[cable].unit)
            for cable in _all_cable_ids(model)
            if all_items[cable].unit is not None
        ),
    )


def _all_cable_ids(model: Model) -> set[Id[Item]]:
    return set(cable_items(model))


def _readable_cables(
    model: Model, readings: Iterable[tuple[Id[Item], Id[Unit] | None]]
) -> tuple[HarnessCable, ...]:
    """Each `(cable, unit)` built by `_cable_facts` with `unit`'s facts, unreadable ones left out.

    The tolerant walk of `all_cables` and `all_unit_cables`: a `SchemaError` (a missing
    designation) leaves that cable out. One `_Facts` per distinct `unit`, built when first needed.
    """
    facts_by_unit: dict[Id[Unit] | None, _Facts] = {}
    found = []
    for cable, unit in readings:
        if unit not in facts_by_unit:
            facts_by_unit[unit] = _facts_of(model, unit)
        try:
            found.append(_cable_facts(model, cable, facts_by_unit[unit]))
        except SchemaError:
            continue
    return tuple(sorted(found, key=lambda cable: (natural_key(cable.designation), cable.cable)))


def cable_list_rows(model: Model) -> tuple[CableListRow, ...]:
    """One `CableListRow` per top-level cable: every cable item (`is_cable`) with `unit=None`.

    A cable inside a harness is included, one belonging to a unit is not.
    `from_label`/`to_label` are the `designation` of the two lowest-ranked `HarnessEnd`s.

    Args:
        model: The frozen model to read.

    Returns:
        One `CableListRow` per top-level cable, sorted by `(designation, id)`.

    Raises:
        SchemaError: a cable, or an item one of its cores lands on, has no designation.
    """
    facts = _facts_of(model)
    found = []
    for cable in _top_level_cable_ids(model):
        cable_facts = _cable_facts(model, cable, facts)
        # A list line names two ends; the spec has no rule for more, and dropping the extras keeps
        # the row one line.
        kept = cable_facts.ends[:2]
        found.append(
            CableListRow(
                cable=cable,
                designation=cable_facts.designation,
                mpn=cable_facts.mpn,
                description=cable_facts.description,
                core_count=cable_facts.core_count,
                gauge_mm2=cable_facts.gauge_mm2,
                length_mm=cable_facts.length_mm,
                from_label=kept[0].designation if kept else "",
                to_label=kept[1].designation if kept[1:] else "",
            )
        )
    return tuple(sorted(found, key=lambda row: (natural_key(row.designation), row.cable)))


def contents_rows(cables: tuple[HarnessCable, ...]) -> tuple[ContentsRow, ...]:
    """One `ContentsRow` per cable, in the order given.

    Pure reshaping of `HarnessCable`s a caller already built (`harness_cables_for`,
    `top_level_cables`, `unit_cables`): no `Model` parameter, no re-sort -- the caller's own
    order, already sorted where it needs to be, is kept. `ends` is every end's `designation`,
    blanks dropped, joined by an en dash (moved here verbatim from pdf's own
    copy).

    Args:
        cables: The `HarnessCable`s to reshape, in the order to keep.

    Returns:
        One `ContentsRow` per cable, same order, same length.
    """
    return tuple(
        ContentsRow(
            cable=cable.cable,
            designation=cable.designation,
            mpn=cable.mpn,
            description=cable.description,
            core_count=cable.core_count,
            gauge_mm2=cable.gauge_mm2,
            length_mm=cable.length_mm,
            # Text, not a tuple: `cell_text` would join a tuple with `CELL_SEPARATOR` (`"; "`),
            # not the en dash this column needs.
            ends=" \N{EN DASH} ".join(end.designation for end in cable.ends if end.designation),
        )
        for cable in cables
    )
