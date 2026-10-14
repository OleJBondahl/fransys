"""LC2 (layout-0215): each device of a chain is one box of its pins, whatever functions it holds."""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.defaults import kind_roles
from fransys_layout.geometry import box_port_name
from fransys_layout.stages.slices import by_key
from fransys_model.vocab.tables import functions as functions_table
from fransys_model.vocab.tables import items as items_table

if TYPE_CHECKING:
    from fransys_layout.stages import FunctionSpec
    from fransys_layout.stages.types import DeviceChain
    from fransys_model.kernel import Id, Model

_KIND = "item"  # the kind no symbol rule names, so the view draws as a box


def chain_views(
    model: Model,
    specs: tuple[FunctionSpec, ...],
    chains: tuple[DeviceChain, ...],
) -> tuple[tuple[FunctionSpec, ...], tuple[FunctionSpec, ...], dict[Id[Any], Id[Any]]]:
    """The specs of no chain, each chain member's one view, and each view port's item."""
    members = {member for chain in chains for member in chain.members}
    rest = tuple(spec for spec in specs if spec.item not in members)
    grouped = by_key((spec for spec in specs if spec.item in members), lambda spec: spec.item)
    views = tuple(_view(model, item, group) for item, group in sorted(grouped.items()))
    view_of = {port.port: view.function for view in views for port in view.ports}
    return rest, views, view_of


def _view(model: Model, item: Id[Any], group: tuple[FunctionSpec, ...]) -> FunctionSpec:
    """One device's box: every port its functions keep, named as an item box names them.

    Every port is kept here; `stages/chain_boxes.py` draws only those on a hop (owner 2026-10-13).
    """
    ordered = sorted(group, key=lambda spec: spec.key)
    ports = tuple(
        dataclasses.replace(
            port, name=box_port_name(functions_table(model)[spec.function].name, port.name)
        )
        for spec in ordered
        for port in spec.ports
    )
    return dataclasses.replace(
        ordered[0],
        function=item,
        key=items_table(model)[item].key,
        kind=_KIND,
        roles=dataclasses.replace(kind_roles(_KIND), item_view=True),
        poles=1,
        pole_pairs=(),
        ports=ports,
    )
