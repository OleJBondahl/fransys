"""The pins of a sideless series end in pin order, and whether two such ends pair (model-0242)."""

from typing import NamedTuple

from fransys_model.vocab.markings import port_order_key
lazy from fransys_model.vocab import PortTemplate

__all__ = ["SidelessPins", "sideless_pins"]


class SidelessPins(NamedTuple):
    """Both ends' pins in pin order, and `problem`, the text of why they cannot pair, else `None`.

    Does not pick a port: the caller maps each template back to its own port.
    """

    first: tuple[PortTemplate, ...]
    second: tuple[PortTemplate, ...]
    problem: str | None


def _problem(
    one: str, a: tuple[PortTemplate, ...], two: str, b: tuple[PortTemplate, ...]
) -> str | None:
    if len(a) != len(b):
        return f"{one} has {len(a)} pins and {two} has {len(b)}: name the pins"
    first, second = [t.name for t in a], [t.name for t in b]
    if first != second and sorted(first) == sorted(second):
        return (
            f"{one} and {two} name the same pins in different orders "
            f"({', '.join(first)} against {', '.join(second)}): name the pins"
        )
    return None


def sideless_pins(
    one: str, first: tuple[PortTemplate, ...], two: str, second: tuple[PortTemplate, ...]
) -> SidelessPins:
    """Order each end by `port_order_key`; `problem` names `one` and `two` when they do not pair.

    A pin with no printed marking sorts by its name. The ends do not pair when they have a
    different number of pins, or the same names in another order.
    """
    a, b = (tuple(sorted(end, key=port_order_key)) for end in (first, second))
    return SidelessPins(a, b, _problem(one, a, two, b))
