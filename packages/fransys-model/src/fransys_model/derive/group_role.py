"""The page role of a `=` group, read from the net classes of its content (model-0318)."""

lazy from collections.abc import Mapping

from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import effective_placement
from fransys_model.derive.structure import schematic_functions
from fransys_model.kernel import parent_chain
from fransys_model.layout import GroupHint, PageRole, layout_of
from fransys_model.vocab.enums import Aspect, NetClass
from fransys_model.vocab.tables import aspect_nodes, functions, items, nets
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import AspectNode, Function, Net, Port

__all__ = ["group_role"]

_BY_CLASS = {
    NetClass.POWER: PageRole.POWER,
    NetClass.CONTROL: PageRole.CONTROL,
    NetClass.GENERIC: PageRole.CONTROL,
    NetClass.SIGNAL: PageRole.SIGNAL,
}
_STRENGTH = (PageRole.POWER, PageRole.CONTROL, PageRole.SIGNAL)


def _groups_of(
    model: Model, function: Function, hints: Mapping[Id[Function], Id[AspectNode]]
) -> set[Id[AspectNode]]:
    """The `=` nodes `function` is drawn in: its hint, else the nodes above its placement."""
    if function.id in hints:
        return {hints[function.id]}
    leaf = effective_placement(model, items(model)[function.item].id, Aspect.FUNCTION)
    nodes = aspect_nodes(model)
    return set() if leaf is None else set(parent_chain(lambda node: nodes[node].parent, leaf))


def _port_roles(
    model: Model, port: Id[Port], by_port: Mapping[Id[Port], tuple[Id[Net], ...]]
) -> set[PageRole]:
    """The roles `port` votes: its nets' classes bar PE; CONTROL when no net votes."""
    classes = {nets(model)[n].net_class for n in by_port.get(port, ())} - {NetClass.PE}
    return {_BY_CLASS[c] for c in classes} or {PageRole.CONTROL}


def group_role(model: Model, group: Id[AspectNode]) -> PageRole:
    """The strongest role of any port of `group`'s drawn functions (POWER, CONTROL, SIGNAL).

    A port votes by the classes of the nets naming it: power is POWER, control and generic
    CONTROL, signal SIGNAL; PE does not vote, and a port with no voting net votes CONTROL.
    A group with no ports is CONTROL.
    The old engine's page role differs on some pages: it is a packing artefact.
    """
    index = build_indexes(model)
    hints = {h.function: h.group for h in layout_of(model, GroupHint).values()}
    found: set[PageRole] = set()
    for function_id in schematic_functions(model):
        function = functions(model)[function_id]
        if group in _groups_of(model, function, hints):
            for port in index.ports_by_function.get(function_id, ()):
                found |= _port_roles(model, port, index.nets_by_port)
    return next((role for role in _STRENGTH if role in found), PageRole.CONTROL)
