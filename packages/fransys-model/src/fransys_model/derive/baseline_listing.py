"""The listing writer (baseline spec L2): the sorted row builders and `listing`."""

from typing import TYPE_CHECKING

from fransys_model.kernel.encode import decimal_text
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.membership import external, is_sole_unit_root, unit_own_roots
from fransys_model.vocab.rating_readers import boundary_operating, boundary_rating
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
    projects,
)
from fransys_model.vocab.tables import (
    mates as mates_table,
)
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .baseline_designation import (
    _cross_function_text,
    _cross_port_text,
    _net_port_text,
    unit_designation,
)
from .reports import _conductor_unit, _lowest_common_unit
from .rows import (
    BaselineBoundary,
    BaselineConductor,
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


# -- sort keys (None- and non-orderable-safe, baseline spec L2's own field order) ------------


def _opt_key(value: str | None) -> tuple[bool, str]:
    return (value is None, value or "")


def _num_key(value: int | None) -> tuple[bool, int]:
    return (value is None, value or 0)


def _repr_key(value: object) -> tuple[bool, str]:
    """A None-safe sort key for a nested, non-orderable `@value` (`Rating`, `Operating`)."""
    return (value is None, "" if value is None else repr(value))


# -- listing(model, unit) (baseline spec L2) -------------------------------------------------


def _item_rows(model: Model, unit: Id[Unit] | None) -> tuple[BaselineItem, ...]:
    parts_table = parts(model)
    rows = []
    for item in items(model).values():
        if item.unit != unit:
            continue
        designation = (
            "" if is_sole_unit_root(model, item.id) else unit_designation(model, unit, item.id)
        )
        part = None if item.part is None else parts_table[item.part]
        rows.append(
            BaselineItem(
                designation=designation,
                mpn="" if part is None else part.mpn,
                manufacturer="" if part is None else part.manufacturer,
                installed=item.installed,
                external=external(model, item.id),
                position=item.position,
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


def _nested_unit_rows(model: Model, unit: Id[Unit] | None) -> tuple[BaselineNestedUnit, ...]:
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
                min(unit_designation(model, unit, root) for root in unit_own_roots(model, nested))
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


def _boundary_rows(model: Model, unit: Id[Unit] | None) -> tuple[BaselineBoundary, ...]:
    rows = []
    for record in boundaries_table(model).values():
        if record.unit != unit:
            continue
        fn = functions(model)[record.function]
        designation = f"{unit_designation(model, unit, fn.item)}:{fn.name}"
        port_names = tuple(
            sorted(p.name for p in ports(model).values() if p.function == record.function)
        )
        rows.append(
            BaselineBoundary(
                designation=designation,
                ports=port_names,
                rating=boundary_rating(model, record.id),
                operating=boundary_operating(model, record.id),
            )
        )
    rows.sort(key=lambda r: (r.designation, r.ports, _repr_key(r.rating), _repr_key(r.operating)))
    return tuple(rows)


def _conductor_rows(model: Model, unit: Id[Unit] | None) -> tuple[BaselineConductor, ...]:
    wire_facets = {f.subject: f for f in facets_of(model, WireFacet).values()}
    rows = []
    for conductor in conductors(model).values():
        if _conductor_unit(model, conductor) != unit:
            continue
        a_text, b_text = sorted(
            (_cross_port_text(model, unit, conductor.a), _cross_port_text(model, unit, conductor.b))
        )
        carrier = (
            None if conductor.carrier is None else unit_designation(model, unit, conductor.carrier)
        )
        facet = wire_facets.get(conductor.id)
        rows.append(
            BaselineConductor(
                kind=conductor.kind.value,
                a=a_text,
                b=b_text,
                carrier=carrier,
                colour=None if facet is None else facet.colour,
                gauge_mm2=None if facet is None else decimal_text(facet.gauge_mm2),
                length_mm=None if facet is None else facet.length_mm,
                label=None if facet is None else facet.label,
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


def _mate_rows(model: Model, unit: Id[Unit] | None) -> tuple[BaselineMate, ...]:
    all_items = items(model)
    rows = []
    for record in mates_table(model).values():
        fn_a, fn_b = functions(model)[record.a], functions(model)[record.b]
        a_unit, b_unit = all_items[fn_a.item].unit, all_items[fn_b.item].unit
        if _lowest_common_unit(model, a_unit, b_unit) != unit:
            continue
        a_text, b_text = sorted(
            (
                _cross_function_text(model, unit, record.a),
                _cross_function_text(model, unit, record.b),
            )
        )
        rows.append(BaselineMate(a=a_text, b=b_text))
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


def _net_rows(model: Model, unit: Id[Unit] | None) -> tuple[BaselineNet, ...]:
    direct_nested = frozenset(u.id for u in units_table(model).values() if u.parent == unit)
    rows = []
    for record in nets(model).values():
        if _net_unit(model, record.ports) != unit:
            continue
        port_texts = tuple(
            sorted(
                text
                for p in record.ports
                if (text := _net_port_text(model, unit, direct_nested, p)) is not None
            )
        )
        rows.append(
            BaselineNet(
                name=record.name,
                net_class=record.net_class.value,
                potential=record.potential,
                ports=port_texts,
            )
        )
    rows.sort(key=lambda r: (_opt_key(r.name), r.net_class, _opt_key(r.potential), r.ports))
    return tuple(rows)


def _listing_unit(model: Model, unit: Id[Unit] | None) -> BaselineUnit:
    """The `unit` key: a real unit's own release, or, for `unit=None`, the `Project`'s (L2)."""
    if unit is None:
        project = next(iter(projects(model).values()))
        return BaselineUnit(
            name=project.number, version=project.version, revision=project.revision, interface=""
        )
    release = unit_release(model, unit)
    return BaselineUnit(
        name=release.name,
        version=release.version,
        revision=release.revision,
        interface=release.interface,
    )


def listing(model: Model, unit: Id[Unit] | None) -> Listing:
    """`unit`'s baseline listing (baseline spec L2): every section, sorted, designation-relative.

    `unit=None` is the system listing: `unit` comes from the model's one `Project`, `items`
    are the items of no unit, `units` the top-level units, and `boundary` is always empty (no
    `Boundary` ever names `unit=None`). Every other section reuses the same helper as a real
    unit's: `unit_designation`'s common location is `None` for `unit=None` by construction, so
    every rendered text is the ordinary, full model-relative one, with no truncation.

    Args:
        model: The frozen model to read.
        unit: The unit to list, or `None` for the system listing.

    Returns:
        The unit's `Listing`.
    """
    return Listing(
        unit=_listing_unit(model, unit),
        items=_item_rows(model, unit),
        units=_nested_unit_rows(model, unit),
        boundary=_boundary_rows(model, unit),
        conductors=_conductor_rows(model, unit),
        mates=_mate_rows(model, unit),
        nets=_net_rows(model, unit),
    )
