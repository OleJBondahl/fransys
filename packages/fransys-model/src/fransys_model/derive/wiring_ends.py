"""What a terminal list prints at the ends of a strip: its Side A and Side B headings and ends.

See design/derive-queries.md. Both functions are one data's views (model-0253): the PDF list
calls them, and the CSV keeps the jumper ends and the fixed labels.
"""

from itertools import product

from fransys_model.vocab.enums import PortRole
from fransys_model.vocab.tables import ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item

from .columns import TERMINAL_LABELS
from .facts.children import child_items
from .facts.conductor_facts import is_bridge
from .facts.roles import port_role
from .indexes import build_indexes
from .lookups import terminal_items
lazy from .rows import TerminalRow


def _marking_pairs(model: Model, strip: Id[Item]) -> set[tuple[str | None, str | None]]:
    """Every (internal, external) marking pair the strip's terminals could print."""
    idx = build_indexes(model)
    terminals = terminal_items(model)
    pairs: set[tuple[str | None, str | None]] = set()
    for child in child_items(model, strip):
        if child not in terminals:
            continue
        markings: dict[PortRole, set[str | None]] = {
            PortRole.INTERNAL: set(),
            PortRole.EXTERNAL: set(),
        }
        for function in idx.functions_by_item.get(child, ()):
            for port in idx.ports_by_function.get(function, ()):
                role = port_role(model, port)
                if role in markings:
                    markings[role].add(ports(model)[port].marking)
        pairs.update(
            product(markings[PortRole.INTERNAL] or {None}, markings[PortRole.EXTERNAL] or {None})
        )
    return pairs


def strip_side_headings(model: Model, strip: Id[Item]) -> tuple[str, str]:
    """Ends headings: the strip's shared non-empty markings, else `TERMINAL_LABELS`."""
    pairs = _marking_pairs(model, strip)
    if len(pairs) == 1:
        internal, external = next(iter(pairs))
        if internal and external:
            return internal, external
    return TERMINAL_LABELS["internal_ends"], TERMINAL_LABELS["external_ends"]


def _kept(model: Model, ids: tuple[Id[Conductor], ...], ends: tuple[str, ...]) -> tuple[str, ...]:
    """`ends` without the jumper conductors' ends; the open cores come after the conductors'."""
    wired = tuple(
        end for conductor, end in zip(ids, ends, strict=False) if not is_bridge(model, conductor)
    )
    return (*wired, *ends[len(ids) :])


def ends_without_jumpers(model: Model, row: TerminalRow) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """`row`'s (internal, external) ends without jumper partners, which the Bridge shows."""
    return (
        _kept(model, row.internal, row.internal_ends),
        _kept(model, row.external, row.external_ends),
    )
