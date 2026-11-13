"""The one home of the template to elecdef `Pin` mapping: the throws and the poles a function's links make (R1077, R2046).

A pin is keyed by its printed marking; only the pins a switched link joins are built, so an
unlinked pin's marking never has to be valid. The elecdef throws come back as template ids.
"""

lazy from collections.abc import Iterable, Mapping

from fransys_model.elecdef import Link, LinkKind, Pin, PinRole, Side, poles, throws
from fransys_model.kernel import Id, ModelError
from fransys_model.vocab.markings import Pole, pole_order
lazy from fransys_model.vocab.templates import InternalLink, PortTemplate


def _marking(template: PortTemplate) -> str:
    return template.name if template.marking is None else template.marking


_SIDE_ROLES = {Side.A: PinRole.LINE, Side.B: PinRole.LOAD}


def _pin(marking: str, template: PortTemplate) -> Pin:
    """The elecdef pin of `template`: its stated role, else the line or load role its side gives."""
    return Pin(marking, template.pin_role or _SIDE_ROLES.get(template.side) or PinRole.SIGNAL, template.side)


def _join(templates: Mapping[Id[PortTemplate], PortTemplate], link: InternalLink) -> Link:
    return Link((_marking(templates[link.a]), _marking(templates[link.b])), link.kind, link.closed_at_rest)


def _key(template: PortTemplate) -> tuple[str, Side | None]:
    return _marking(template), template.side


def poles_by_links(links: Iterable[InternalLink], templates: Mapping[Id[PortTemplate], PortTemplate]) -> tuple[Pole, ...]:
    """The poles of the links of one function that elecdef `poles` joins, as `(line, load)` in order."""
    own = [link for link in links if link.a in templates and link.b in templates]
    pins = {_key(templates[end]): _pin(_marking(templates[end]), templates[end]) for link in own for end in (link.a, link.b)}
    runs = [{(pin.marking, pin.side) for pin in pole.pins} for pole in poles(tuple(pins.values()), tuple(_join(templates, k) for k in own))]
    held = (link for link in own if any({_key(templates[link.a]), _key(templates[link.b])} <= run for run in runs))
    return pole_order(held, templates)


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
    built = [_pin(marking, template) for marking, template in by_marking.items()]
    joins = tuple(_join(templates, link) for link in switched)
    return tuple((by_marking[t.common.marking].id, by_marking[t.throw.marking].id, t.closed_at_rest) for t in throws(tuple(built), joins))
