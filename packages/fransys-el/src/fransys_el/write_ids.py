"""Core id texts back to model ids, by lookup in the model's own tables (no parsing, P6.1 D).

A core symbol id is `symbol_key`, a net id the `symbol_key` of its lead port (`net_key`; `placement_nets.net_ports` maps
it back), and a page group the label of its aspect node (`placement_groups`).
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import render_id

from .kit_keys import function_of
from .placement_groups import group_nodes, label_of
from .placement_ids import symbol_ids
from .placement_kit import refuse

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode

    from .placement_kit import SymbolKit

__all__ = ["group_ids", "id_texts", "symbol_subjects"]


def id_texts(model: Model) -> dict[str, Id[object]]:
    """Every record id of `model` by its `render_id` text."""
    return {render_id(i): i for table in model.tables.values() for i in table}


def symbol_subjects(model: Model, kit: SymbolKit) -> dict[str, Id[object]]:
    """Every core symbol id of `kit` by its text, as the function it draws (a finding's subject)."""
    return {sym: function_of(model, lead) for lead, sym in symbol_ids(model, kit).items()}


def group_ids(model: Model) -> dict[str, Id[AspectNode]]:
    """Every function node by its group text; two nodes with one label are refused."""
    found: dict[str, Id[AspectNode]] = {}
    for node in group_nodes(model):
        label = label_of(model, node)
        if label in found:
            refuse(f"group label {label!r}", "give the two aspect nodes different labels")
        found[label] = node
    return found
