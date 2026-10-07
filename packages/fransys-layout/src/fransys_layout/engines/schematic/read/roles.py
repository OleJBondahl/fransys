"""Shared by `reading.py` and `functions.py`: closure handles, `Role` and `PortSpec`.

Split out because both the function-reading and the connectivity-reading halves of
`reading.py` need a port's physical-net handle and role.
"""

from typing import TYPE_CHECKING

from fransys_layout.engines.schematic.read.power import port_stand
from fransys_layout.geometry import LayoutError
from fransys_layout.stages import ROLE_ORDER, PortSpec, Role
from fransys_model.derive import changeover_throws, port_potential_current, port_potential_rank
from fransys_model.derive.closure import net_of
from fransys_model.vocab.enums import FunctionKind, NetClass, PortRole
from fransys_model.vocab.tables import nets, ports

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.derive.indexes import Indexes
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port

NET_CLASS_TO_ROLE: Mapping[NetClass, Role] = frozendict(
    {
        NetClass.POWER: Role.POWER,
        NetClass.PE: Role.POWER,
        NetClass.CONTROL: Role.CONTROL,
        NetClass.GENERIC: Role.CONTROL,
        NetClass.SIGNAL: Role.SIGNAL,
    }
)


def physical_net(model: Model, port_id: Id[Port]) -> Id[Port]:
    """The handle the engine gives `port_id`'s closure net: the smallest port it joins."""
    net = net_of(model, port_id)
    if net is None:
        msg = "a port the engine reads is not a port of the model"
        raise LayoutError(msg)
    return net.ports[0]


def port_role(model: Model, indexes: Indexes, port_id: Id[Port]) -> Role:
    """The strongest `Role` of any declared `Net` naming `port_id`, else `CONTROL`."""
    net_ids = indexes.nets_by_port.get(port_id, ())
    if not net_ids:
        return Role.CONTROL
    # C15(ii): a pe net class never sets a role: PE is protective, not a power path
    roles = {
        NET_CLASS_TO_ROLE[nets(model)[net_id].net_class]
        for net_id in net_ids
        if nets(model)[net_id].net_class is not NetClass.PE
    }
    return strongest(roles) if roles else Role.CONTROL


def strongest(roles: Iterable[Role]) -> Role:
    """The strongest of `roles` (`POWER` beats `CONTROL` beats `SIGNAL`)."""
    return min(roles, key=ROLE_ORDER.index)


def port_spec(
    model: Model, indexes: Indexes, port_id: Id[Port], throw: str | None = None
) -> PortSpec:
    """One model port of a drawn function, as `resolve` and the engine loop need it."""
    current = port_potential_current(model, port_id)
    port = ports(model)[port_id]
    sided = port.role in (PortRole.INTERNAL, PortRole.EXTERNAL)
    return PortSpec(
        port=port_id,
        name=port.name,
        physical_net=physical_net(model, port_id),
        role=port_role(model, indexes, port_id),
        throw=throw,
        rank=port_potential_rank(model, port_id),
        current=None if current is None else current.value,
        strip_side=port.role.value if sided else None,
        stand=port_stand(model, port_id),
    )


def changeover_throw_of(model: Model, function: Function) -> dict[Id[Port], str]:
    """The throw of each port of a changeover `function` that has one, from its model throws."""
    if function.kind is not FunctionKind.CONTACT_CO:
        return {}
    found: dict[Id[Port], str] = {}
    for pole in changeover_throws(model, function.id):
        found[pole.common] = PortRole.COMMON.value
        found.update((port, PortRole.BREAK.value) for port in pole.breaks)
        found.update((port, PortRole.MAKE.value) for port in pole.makes)
    return found
