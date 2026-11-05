"""The one home of the template to elecdef `Pin` mapping: the throws a function's switched links make (R1077).

A pin is keyed by its printed marking; only the pins a switched link joins are built, so an
unlinked pin's marking never has to be valid. The elecdef throws come back as template ids.
"""

lazy from collections.abc import Iterable, Mapping

from fransys_model.elecdef import Link, LinkKind, Pin, PinRole, throws
from fransys_model.kernel import Id, ModelError
lazy from fransys_model.vocab.templates import InternalLink, PortTemplate


def _marking(template: PortTemplate) -> str:
    return template.name if template.marking is None else template.marking


def template_throws(
    templates: Mapping[Id[PortTemplate], PortTemplate], links: Iterable[InternalLink]
) -> tuple[tuple[Id[PortTemplate], Id[PortTemplate], bool], ...]:
    """`(common, throw, closed_at_rest)` for each switched link that joins a common to a throw, in elecdef's marking order."""
    switched = [link for link in links if link.kind is LinkKind.SWITCHED]
    by_marking: dict[str, PortTemplate] = {}
    for end in {end for link in switched for end in (link.a, link.b)}:
        template = templates[end]
        held = by_marking.setdefault(_marking(template), template)
        if held is not template:
            msg = f"function {template.function}: two pins of a switched link are both marked {_marking(template)!r}"
            raise ModelError(msg)
    built = [Pin(marking, template.pin_role or PinRole.SIGNAL, template.side) for marking, template in by_marking.items()]
    joins = tuple(Link((_marking(templates[link.a]), _marking(templates[link.b])), link.kind, link.closed_at_rest) for link in switched)
    return tuple((by_marking[t.common.marking].id, by_marking[t.throw.marking].id, t.closed_at_rest) for t in throws(tuple(built), joins))
