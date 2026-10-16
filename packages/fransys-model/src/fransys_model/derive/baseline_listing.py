"""The listing writer: the sorted row builders and `listing`."""

from typing import TYPE_CHECKING

from fransys_kernel import decimal_text
from fransys_model.derive.facts.function_ratings import boundary_operating, boundary_rating
from fransys_model.derive.facts.units import external, is_sole_unit_root, unit_own_roots
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.tables import (
    boundaries as boundaries_table,
)
from fransys_model.vocab.tables import (
    conductors,
    facets_of,
    functions,
    items,
    nets,
    parts,
    ports,
)
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .baseline_designation import (
    cross_function_end,
    cross_port_end,
    function_end,
    net_port_end,
    unit_designation,
)
from .baseline_keys import listing_key
from .baseline_rules import CURRENT, ListingRules
from .facts.net_facts import net_class_name, net_potential
from .lone_cable import lone_cable
from .mate_rows import mates
from .release_identity import release_identity
from .reports import _conductor_unit, _lowest_common_unit
from .rows_baseline import (
    BaselineBoundary,
    BaselineConductor,
    BaselineEnd,
    BaselineItem,
    BaselineMate,
    BaselineNestedUnit,
    BaselineNet,
    BaselineUnit,
    Listing,
)
from .unit_release import unit_release

if TYPE_CHECKING:
    from fransys_model.vocab.core import Port


# -- sort keys (None- and non-orderable-safe, in the listing's own field order) ------------


def _opt_key(value: str | None) -> tuple[bool, str]:
    return (value is None, value or "")


def _num_key(value: int | None) -> tuple[bool, int]:
    return (value is None, value or 0)


def _repr_key(value: object) -> tuple[bool, str]:
    """A None-safe sort key for a nested, non-orderable `@value` (`Rating`, `Operating`)."""
    return (value is None, "" if value is None else repr(value))


# -- listing(model, unit) -------------------------------------------------


def _listing_designation(
    model: Model, unit: Id[Unit] | None, item: Id[Item], rules: ListingRules
) -> str:
    """The `designation` the `items` section prints for `item`: `""` for a unit's sole root."""
    return "" if is_sole_unit_root(model, item) else unit_designation(model, unit, item, rules)


def _item_rows(
    model: Model, unit: Id[Unit] | None, rules: ListingRules
) -> tuple[BaselineItem, ...]:
    parts_table = parts(model)
    rows = []
    for item in items(model).values():
        if item.unit != unit or lone_cable(model, item.id) is not None:  # model-0150
            continue
        designation = _listing_designation(model, unit, item.id, rules)
        part = None if item.part is None else parts_table[item.part]
        rows.append(
            BaselineItem(
                designation=designation,
                mpn="" if part is None else part.mpn,
                manufacturer="" if part is None else part.manufacturer,
                installed=item.installed,
                external=external(model, item.id),
                position=item.position,
                parent=None
                if item.parent is None
                else _listing_designation(model, unit, item.parent, rules),
                key=listing_key(model, item.id) if rules.item_keys else None,
            )
        )
    rows.sort(
        key=lambda r: (
            r.designation,
            r.mpn,
            r.manufacturer,
            r.installed,
            r.external,
            _num_key(r.position),
        )
    )
    return tuple(rows)


def _end_keys(a: BaselineEnd, b: BaselineEnd, rules: ListingRules) -> dict[str, str]:
    """The `a_key`, `a_pin`, `b_key`, `b_pin` keywords of a conductor or mate; none under v1."""
    if not rules.item_keys:
        return {}
    return {"a_key": a.key, "a_pin": a.pin, "b_key": b.key, "b_pin": b.pin}


def _nested_unit_rows(
    model: Model, unit: Id[Unit] | None, rules: ListingRules
) -> tuple[BaselineNestedUnit, ...]:
    groups: dict[tuple[str, int, int], list[Id[Unit]]] = {}
    for record in units_table(model).values():
        if record.parent != unit:
            continue
        release = unit_release(model, record.id)
        groups.setdefault((release.name, release.version, release.revision), []).append(record.id)
    rows = []
    for (name, version, revision), nested_ids in groups.items():
        release = unit_release(model, nested_ids[0])
        instances = tuple(
            sorted(
                min(
                    unit_designation(model, unit, root, rules)
                    for root in unit_own_roots(model, nested)
                )
                for nested in nested_ids
            )
        )
        rows.append(
            BaselineNestedUnit(
                name=name,
                version=version,
                revision=revision,
                interface=release.interface,
                instances=instances,
            )
        )
    rows.sort(key=lambda r: (r.name, r.version, r.revision, r.interface, r.instances))
    return tuple(rows)


def _boundary_rows(
    model: Model, unit: Id[Unit] | None, rules: ListingRules
) -> tuple[BaselineBoundary, ...]:
    rows = []
    for record in boundaries_table(model).values():
        if record.unit != unit:
            continue
        fn = functions(model)[record.function]
        end = function_end(model, unit, fn, rules)
        port_names = tuple(
            sorted(p.name for p in ports(model).values() if p.function == record.function)
        )
        rows.append(
            BaselineBoundary(
                designation=end.text,
                ports=port_names,
                rating=boundary_rating(model, record.id),
                operating=boundary_operating(model, record.id),
                key=end.key if rules.item_keys else None,
                pin=end.pin if rules.item_keys else None,
            )
        )
    rows.sort(key=lambda r: (r.designation, r.ports, _repr_key(r.rating), _repr_key(r.operating)))
    return tuple(rows)


def _conductor_rows(
    model: Model, unit: Id[Unit] | None, rules: ListingRules
) -> tuple[BaselineConductor, ...]:
    wire_facets = {f.subject: f for f in facets_of(model, WireFacet).values()}
    rows = []
    for conductor in conductors(model).values():
        if _conductor_unit(model, conductor) != unit:
            continue
        a_end, b_end = sorted(
            (
                cross_port_end(model, unit, conductor.a, rules),
                cross_port_end(model, unit, conductor.b, rules),
            ),
            key=lambda end: end.text,
        )
        carrier = (
            None
            if conductor.carrier is None
            else unit_designation(model, unit, conductor.carrier, rules)
        )
        facet = wire_facets.get(conductor.id)
        rows.append(
            BaselineConductor(
                kind=conductor.kind.value,
                a=a_end.text,
                b=b_end.text,
                carrier=carrier,
                colour=None if facet is None else facet.colour,
                gauge_mm2=None if facet is None else decimal_text(facet.gauge_mm2),
                length_mm=None if facet is None else facet.length_mm,
                label=None if facet is None else facet.label,
                **_end_keys(a_end, b_end, rules),
            )
        )
    rows.sort(
        key=lambda r: (
            r.kind,
            r.a,
            r.b,
            _opt_key(r.carrier),
            _opt_key(r.colour),
            _opt_key(r.gauge_mm2),
            _num_key(r.length_mm),
            _opt_key(r.label),
        )
    )
    return tuple(rows)


def _mate_rows(
    model: Model, unit: Id[Unit] | None, rules: ListingRules
) -> tuple[BaselineMate, ...]:
    all_items = items(model)
    rows = []
    for record in mates(model):
        fn_a, fn_b = functions(model)[record.a], functions(model)[record.b]
        a_unit, b_unit = all_items[fn_a.item].unit, all_items[fn_b.item].unit
        if _lowest_common_unit(model, a_unit, b_unit) != unit:
            continue
        a_end, b_end = sorted(
            (
                cross_function_end(model, unit, record.a, rules),
                cross_function_end(model, unit, record.b, rules),
            ),
            key=lambda end: end.text,
        )
        rows.append(BaselineMate(a=a_end.text, b=b_end.text, **_end_keys(a_end, b_end, rules)))
    rows.sort(key=lambda r: (r.a, r.b))
    return tuple(rows)


def _net_unit(model: Model, port_ids: tuple[Id[Port], ...]) -> Id[Unit] | None:
    """The lowest unit whose subtree holds every one of `port_ids`' owning items.

    The `_lowest_common_unit` rule folded pairwise over a net's N ports.
    `None` once any port's item has no unit, or two ports' units share no common ancestor.
    """
    all_items = items(model)
    all_functions = functions(model)
    all_ports = ports(model)
    owner: Id[Unit] | None = None
    for index, port_id in enumerate(port_ids):
        port_unit = all_items[all_functions[all_ports[port_id].function].item].unit
        owner = port_unit if index == 0 else _lowest_common_unit(model, owner, port_unit)
        if owner is None:
            return None
    return owner


def _net_rows(model: Model, unit: Id[Unit] | None, rules: ListingRules) -> tuple[BaselineNet, ...]:
    direct_nested = frozenset(u.id for u in units_table(model).values() if u.parent == unit)
    rows = []
    for record in nets(model).values():
        if _net_unit(model, record.ports) != unit:
            continue
        ends = sorted(
            (
                end
                for p in record.ports
                if (end := net_port_end(model, unit, direct_nested, p, rules)) is not None
            ),
            key=lambda end: end.text,
        )
        rows.append(
            BaselineNet(
                name=record.name,
                net_class=net_class_name(model, record.id),
                potential=net_potential(model, record.id),
                ports=tuple(end.text for end in ends),
                port_keys=tuple(end.key for end in ends) if rules.item_keys else (),
                port_pins=tuple(end.pin for end in ends) if rules.item_keys else (),
            )
        )
    rows.sort(key=lambda r: (_opt_key(r.name), r.net_class, _opt_key(r.potential), r.ports))
    return tuple(rows)


def _listing_unit(model: Model, unit: Id[Unit] | None) -> BaselineUnit:
    """The `unit` key: a real unit's own release, or, for `unit=None`, the `Project`'s."""
    identity = release_identity(model, unit)
    return BaselineUnit(
        name=identity.name,
        version=identity.version,
        revision=identity.revision,
        interface=identity.interface,
    )


def listing(model: Model, unit: Id[Unit] | None, rules: ListingRules = CURRENT) -> Listing:
    """`unit`'s baseline listing: every section, sorted, designation-relative.

    `unit=None` is the system listing: `unit` comes from the model's one `Project`, `items`
    are the items of no unit, `units` the top-level units, and `boundary` is always empty (no
    `Boundary` ever names `unit=None`). Every other section reuses a real unit's helper, and
    `unit_designation`'s common location is `None` for it, so no text is truncated.

    Args:
        model: The frozen model to read.
        unit: The unit to list, or `None` for the system listing.
        rules: The listing rules to cut under (`ListingRules`); today's by default.

    Returns:
        The unit's `Listing`.
    """
    return Listing(
        unit=_listing_unit(model, unit),
        items=_item_rows(model, unit, rules),
        units=_nested_unit_rows(model, unit, rules),
        boundary=_boundary_rows(model, unit, rules),
        conductors=_conductor_rows(model, unit, rules),
        mates=_mate_rows(model, unit, rules),
        nets=_net_rows(model, unit, rules),
    )
