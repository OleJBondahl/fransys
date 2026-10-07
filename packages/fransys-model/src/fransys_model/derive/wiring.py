"""Terminals, conductors and ports: the queries that read a strip and its wiring.

See design/derive-queries.md.

Results are `tuple`s (or one `frozendict`), sorted by an explicit key so insertion order into
`model` never shows through (CLAUDE.md invariant 7).
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import Id, Model, UnionFind
from fransys_model.vocab.enums import ConductorKind, PortRole
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import conductors, facets_of, items, nets, ports
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.connectivity import Conductor, Net
lazy from fransys_model.vocab.core import Item, Port, Unit

from .closure import physical_nets
from .designation import end_outside_nested_unit, terminal_designation, unit_list_context
from .drawing_text import port_designation_in
from .indexes import build_indexes
from .list_order import in_designation_order
from .lookups import conductors_by_role, item_of_port, require, strip_set, terminal_items
from .rows import TerminalRow

if TYPE_CHECKING:
    from .indexes import Indexes


def conductors_on_item(
    model: Model, item: Id[Item]
) -> frozendict[Id[Item], frozendict[PortRole, tuple[Id[Conductor], ...]]]:
    """`item`'s conductors, grouped by terminal child item and then by port role.

    Holds only the `terminal`-facet children with a conductor and, per child, only the roles with
    one; a conductor with both ends on one child is listed once per role it touches.

    Args:
        model: The model to read.
        item: The item whose terminal children's conductors are grouped.

    Returns:
        `item`'s terminal children, each mapped to its conductors by `PortRole`.

    Raises:
        SchemaError: `item` is not an item of `model`.
    """
    require(items(model).get(item), "item", item)
    idx = build_indexes(model)
    terminals = terminal_items(model)
    grouped: dict[Id[Item], frozendict[PortRole, tuple[Id[Conductor], ...]]] = {}
    for child in idx.children_by_item.get(item, ()):
        if child not in terminals:
            continue
        by_role = conductors_by_role(model, idx, child)
        if by_role:
            grouped[child] = frozendict(
                {
                    role: tuple(sorted(by_role[role]))
                    for role in sorted(by_role, key=lambda r: r.value)
                }
            )
    return frozendict(grouped)


def _jumper_groups(model: Model, rows: list[Id[Item]]) -> dict[Id[Item], int]:
    """Number the terminals `rows` (in row order) that `jumper` conductors bridge, from 1."""
    members = set(rows)
    sets = UnionFind(rows)
    for conductor in conductors(model).values():
        if conductor.kind is not ConductorKind.JUMPER:
            continue
        ends = (item_of_port(model, conductor.a), item_of_port(model, conductor.b))
        if ends[0] in members and ends[1] in members:
            sets.union(ends[0], ends[1])
    size: dict[Id[Item], int] = {}
    for terminal in rows:
        size[sets.find(terminal)] = size.get(sets.find(terminal), 0) + 1
    number: dict[Id[Item], int] = {}
    numbered: dict[Id[Item], int] = {}
    for terminal in rows:
        root = sets.find(terminal)
        if size[root] < 2:  # noqa: PLR2004 -- a group needs two terminals
            continue
        numbered.setdefault(root, len(numbered) + 1)
        number[terminal] = numbered[root]
    return number


def _far_ends(  # noqa: PLR0913 -- one end's lookups, its unit and the list's context
    model: Model,
    idx: Indexes,
    terminal: Id[Item],
    role: PortRole,
    landed: tuple[Id[Conductor], ...],
    *,
    unit: Id[Unit] | None,
    context: Id[AspectNode] | None,
) -> tuple[str, ...]:
    """The port each of `landed` reaches from `terminal`'s ports of `role`, rendered, in order.

    Each is `port_designation_in` `context`, or `""` when its item is outside the nested `unit`
    (`end_outside_nested_unit`): kept, so the tuple stays as long as `landed`.
    """
    near = {
        port
        for function in idx.functions_by_item.get(terminal, ())
        for port in idx.ports_by_function.get(function, ())
        if ports(model)[port].role is role
    }
    all_conductors = conductors(model)

    def far(conductor: Id[Conductor]) -> Id[Port]:
        record = all_conductors[conductor]
        return record.b if record.a in near else record.a

    return tuple(
        ""
        if end_outside_nested_unit(model, item_of_port(model, far(conductor)), unit)
        else port_designation_in(model, far(conductor), context, unit=unit)
        for conductor in landed
    )


def terminal_rows(
    model: Model,
    strip: Id[Item],
    *,
    unit: Id[Unit] | None = None,
    context: Id[AspectNode] | None = None,
) -> tuple[TerminalRow, ...]:
    """One `TerminalRow` per `strip` terminal, sorted by `(facet.group, facet.index, id)`.

    Args:
        model: The model to read.
        strip: The terminal strip item whose rows are built.
        unit: The unit whose own document prints the list, keyword-only; `None` for none.
        context: The location node the list prints for, keyword-only; ignored once `unit` has one.

    Returns:
        One `TerminalRow` per terminal child of `strip`, sorted.

    Raises:
        SchemaError: `strip` is not an item of `model`, or a far end's item has no designation.
    """
    require(items(model).get(strip), "item", strip)
    context = unit_list_context(model, unit, context)
    idx = build_indexes(model)
    facets = {facet.subject: facet for facet in facets_of(model, TerminalFacet).values()}
    children = sorted(
        (child for child in idx.children_by_item.get(strip, ()) if child in facets),
        key=lambda child: (facets[child].group, facets[child].index, child),
    )
    groups = _jumper_groups(model, children)
    rows = []
    for child in children:
        by_role = conductors_by_role(model, idx, child)
        internal = tuple(sorted(by_role.get(PortRole.INTERNAL, ())))
        external = tuple(sorted(by_role.get(PortRole.EXTERNAL, ())))
        rows.append(
            TerminalRow(
                terminal=child,
                designation=terminal_designation(model, child, unit=unit),
                group=facets[child].group,
                index=facets[child].index,
                internal=internal,
                external=external,
                internal_ends=_far_ends(
                    model, idx, child, PortRole.INTERNAL, internal, unit=unit, context=context
                ),
                external_ends=_far_ends(
                    model, idx, child, PortRole.EXTERNAL, external, unit=unit, context=context
                ),
                jumper_group=groups.get(child),
            )
        )
    return tuple(rows)


def first_leg(model: Model, net: Id[Net], *, from_item: Id[Item]) -> Id[Port] | None:
    """The port of `net` that is the first leg out of `from_item`.

    The smallest port joined by one `Conductor` to `from_item`'s port on `net`, else the smallest.

    Args:
        model: The model to read.
        net: The net whose first leg out of `from_item` is found.
        from_item: The item the leg starts from, keyword-only.

    Returns:
        The port id, or `None` when `from_item` has no port on `net` or no candidate exists.

    Raises:
        SchemaError: `net` is not a net, or `from_item` not an item, of `model`.
    """
    declared = require(nets(model).get(net), "net", net)
    require(items(model).get(from_item), "item", from_item)
    own = [port for port in declared.ports if item_of_port(model, port) == from_item]
    candidates = {port for port in declared.ports if item_of_port(model, port) != from_item}
    if not own or not candidates:
        return None
    idx = build_indexes(model)
    direct = set()
    for port in own:
        for conductor_id in idx.conductors_by_port.get(port, ()):
            conductor = conductors(model)[conductor_id]
            far = conductor.b if conductor.a == port else conductor.a
            if far in candidates:
                direct.add(far)
    return min(direct or candidates)


def unconnected_ports(model: Model) -> tuple[Id[Port], ...]:
    """Every port whose physical net is a singleton, in id order (`physical_nets` is sorted).

    A conductor, a `conductive` link or a `Mate` reaching a port connects it; a declared
    `Net` does not, deliberately unlike `PORT_UNCONNECTED`, which is about authoring intent.

    Args:
        model: The model to read.

    Returns:
        Every port with no other port on its physical net, sorted.
    """
    return tuple(net.ports[0] for net in physical_nets(model) if len(net.ports) == 1)


def terminal_strips(model: Model) -> tuple[Id[Item], ...]:
    """Every item that at least one `terminal` facet names as its strip, in designation order.

    A terminal's strip is its parent item: `TerminalFacet` carries no strip field of its
    own. Shared by `fransys`'s export enumeration and the
    pdf document contents, so the two never disagree about what a
    strip is.

    Args:
        model: The model to read.

    Returns:
        Every strip item's id, by natural designation, then id.
    """
    strips = strip_set(model)
    return in_designation_order(model, strips)


def unused_terminals(model: Model, strip: Id[Item]) -> tuple[Id[Item], ...]:
    """Terminal children of `strip` with no conductor on any port, sorted by id.

    Args:
        model: The model to read.
        strip: The terminal strip item whose unused terminals are listed.

    Returns:
        Every unused terminal child's id, sorted.

    Raises:
        SchemaError: `strip` is not an item of `model`.
    """
    require(items(model).get(strip), "item", strip)
    idx = build_indexes(model)
    terminals = terminal_items(model)
    return tuple(
        child
        for child in idx.children_by_item.get(strip, ())
        if child in terminals and not conductors_by_role(model, idx, child)
    )
