"""Core id texts back to model ids, by lookup in the model's own tables (no parsing, P6.1 D).

A core symbol id is `render_id(Id)`, a net id the value of the first port of its physical
net (`placement_nets`), and a page group the label of its aspect node (`placement_groups`).
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import render_id

from .placement_groups import group_nodes, label_of
from .placement_kit import refuse

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

__all__ = ["group_ids", "id_texts", "port_values"]


def id_texts(model: Model) -> dict[str, Id[object]]:
    """Every record id of `model` by its `render_id` text."""
    return {render_id(i): i for table in model.tables.values() for i in table}


def port_values(model: Model) -> dict[str, Id[object]]:
    """Every port id by its bare value: how a core net id spells a physical net."""
    return {i.value: i for i in model.tables.get("port", {})}


def group_ids(model: Model) -> dict[str, Id[object]]:
    """Every function node by its group text; two nodes with one label are refused."""
    found: dict[str, Id[object]] = {}
    for node in group_nodes(model):
        label = label_of(model, node)
        if label in found:
            refuse(f"group label {label!r}", "give the two aspect nodes different labels")
        found[label] = node
    return found
