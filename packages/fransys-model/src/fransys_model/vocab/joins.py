"""Header joins: a header port that is a function port of its own part (HA4, connectivity.md).

A join is a part fact stored once on the header port's template. It carries no conductor, so every
reader that asks whether a port is connected reads `port_joins` as well.
"""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached

from .tables import functions, port_templates, ports
lazy from .core import Port


@digest_cached(DIGEST_CACHE_SIZE)
def _joins(model: Model) -> tuple[tuple[Id[Port], Id[Port]], ...]:
    item_of = {function.id: function.item for function in functions(model).values()}
    by_item_template = {
        (item_of[port.function], port.template): port.id
        for port in ports(model).values()
        if port.template is not None
    }
    templates = port_templates(model)
    pairs = []
    for port in ports(model).values():
        template = templates.get(port.template) if port.template is not None else None
        if template is None or template.joins is None:
            continue
        target = by_item_template.get((item_of[port.function], template.joins))
        if target is not None:
            pairs.append((port.id, target))
    return tuple(sorted(pairs))


def port_joins(model: Model) -> tuple[tuple[Id[Port], Id[Port]], ...]:
    """Each (header port, function port) pair the model's header joins make, sorted.

    The pair is on one item: the join names a port template of the header's own part. A join whose
    target function the item lacks yields no pair.
    """
    return _joins(model)


def joined_ports(model: Model) -> frozenset[Id[Port]]:
    """Every port on either end of a header join: the ports a join counts as connected."""
    return frozenset(end for pair in _joins(model) for end in pair)
