"""What a terminal list prints at the head of a strip: its Side A and Side B headings.

See design/derive-queries.md. The PDF list calls it; the ends themselves are `terminal_rows`'s.
"""

from itertools import product

from fransys_model.vocab.enums import PortBoundary
from fransys_model.vocab.tables import ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item

from .columns import list_pdf_heading
from .facts.children import child_items
from .facts.roles import port_boundary
from .indexes import build_indexes
from .lookups import terminal_items


def _marking_pairs(model: Model, strip: Id[Item]) -> set[tuple[str | None, str | None]]:
    """Every (internal, external) marking pair the strip's terminals could print."""
    idx = build_indexes(model)
    terminals = terminal_items(model)
    pairs: set[tuple[str | None, str | None]] = set()
    for child in child_items(model, strip):
        if child not in terminals:
            continue
        markings: dict[PortBoundary, set[str | None]] = {
            PortBoundary.INTERNAL: set(),
            PortBoundary.EXTERNAL: set(),
        }
        for function in idx.functions_by_item.get(child, ()):
            for port in idx.ports_by_function.get(function, ()):
                role = port_boundary(model, port)
                if role in markings:
                    markings[role].add(ports(model)[port].marking)
        pairs.update(product(markings[PortBoundary.INTERNAL] or {None}, markings[PortBoundary.EXTERNAL] or {None}))
    return pairs


def strip_side_headings(model: Model, strip: Id[Item]) -> tuple[str, str]:
    """Ends headings: the strip's shared non-empty markings, else the terminal list's labels."""
    pairs = _marking_pairs(model, strip)
    if len(pairs) == 1:
        internal, external = next(iter(pairs))
        if internal and external:
            return internal, external
    return (
        list_pdf_heading(model, "terminal", "internal_ends"),
        list_pdf_heading(model, "terminal", "external_ends"),
    )
