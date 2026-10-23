"""The poles of a part's function and the side of a pin, over plain templates (model-0128, EL-5).

POLE-03, POLE-04, POLE-09, POLE-10, POLE-11. One gathering of the pole links, one fallback for
pins no link joins, one parity rule for a pin's side. The author reads a library, not a model,
so every fact takes templates and links; `part.py` has the `PartBundle` entry.
"""

lazy from collections.abc import Collection, Iterable

from fransys_model.vocab.conductor_marks import CONDUCTOR_MARKS
from fransys_model.vocab.enums import ConductorMark, FunctionKind, LinkKind, PoleSide, PortRole
from fransys_model.vocab.markings import (
    Pole,
    is_pole_by_role,
    pole_between,
    poles_by_role,
    port_order_key,
)
from fransys_model.vocab.roles import function_role_of
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.templates import InternalLink, PortTemplate

# IEC 60947: the coil's A1 is the line side, A2 the load side
_COIL_SIDES = {"A1": PoleSide.LINE, "A2": PoleSide.LOAD}


def unlinked_poles(templates: Iterable[PortTemplate]) -> tuple[Pole, ...]:
    """The poles of pins with no pole link: consecutive pins in `port_order_key` order pair.

    An odd pin left over is a one-pin pole `(pin, pin)`, last: no pin goes missing.
    """
    ordered = sorted(templates, key=port_order_key)
    poles = [pole_between(a, b) for a, b in zip(ordered[::2], ordered[1::2], strict=False)]
    if len(ordered) % 2:
        poles.append(Pole(None, (ordered[-1], ordered[-1])))
    return tuple(poles)


def _single(pin: PortTemplate) -> Pole:
    return Pole(None, (pin, pin))


def _loads_terminals(kind: FunctionKind, pins: list[PortTemplate]) -> bool:
    """Pins that all name a conductor and none has a side are a load's terminals (a motor)."""
    names = {pin.name for pin in pins}
    return bool(pins) and all(
        conductor_of(pin) is not None and pole_side(pin, kind, names) is None for pin in pins
    )


def _fallback(pins: list[PortTemplate], *, sideless: bool) -> tuple[Pole, ...]:
    """The model pairs the pins; a sideless function keeps a lone pin, a line/load pair or marks."""
    if not sideless:
        return unlinked_poles(pins)
    if len(pins) == 1:
        return (_single(pins[0]),)
    if len(pins) == 2:  # noqa: PLR2004 -- a pole has two ends
        pair = pole_between(*pins)
        if pair.line is not None:
            return (pair,)
    if pins and all(conductor_of(pin) is not None for pin in pins):
        return tuple(_single(pin) for pin in pins)
    return ()


def poles_of_template(
    kind: FunctionKind,
    templates: Iterable[PortTemplate],
    links: Iterable[InternalLink],
    *,
    sideless: bool = False,
) -> tuple[Pole, ...]:
    """The poles of a function of `kind` whose port templates are `templates`, in pole order.

    The links between its own templates that are poles (`poles_by_role`) give them. A function
    with none falls back on its pins, earth pins left out, in `port_order_key` order: consecutive
    pins pair, an odd last pin alone (`unlinked_poles`). `sideless` (the author's series) keeps
    only a lone pin, a line/load pair, or pins that all name a conductor (one pole each, a 3-phase
    motor); any other sideless pins give no poles. The model computes `sideless` once: it is also
    true when no pin has a side and every pin names a conductor.
    """
    own = {t.id: t for t in templates}
    mine = [link for link in links if link.a in own and link.b in own]
    found = poles_by_role(function_role_of(kind), mine, own)
    pins = sorted((t for t in own.values() if t.role is not PortRole.PE), key=port_order_key)
    return found or _fallback(pins, sideless=sideless or _loads_terminals(kind, pins))


def pole_side(
    template: PortTemplate, kind: FunctionKind, pole_pins: Collection[str]
) -> PoleSide | None:
    """The side of a pin: the stated one, else the one its marking gives (IEC 60947).

    A coil's `A1` is the line side, `A2` the load side. A pin on a pole link (`pole_pins`, by
    name) with a numeric marking is `line` when odd, `load` when even. Any other pin has none.
    The marking is the pin's printed one, else its name.
    """
    if template.pole_side is not None:
        return template.pole_side
    marking = template.marking or template.name
    if kind is FunctionKind.COIL:
        return _COIL_SIDES.get(marking)
    if marking.isdigit() and template.name in pole_pins:
        return PoleSide.LINE if int(marking) % 2 else PoleSide.LOAD
    return None


def conductor_of(template: PortTemplate) -> ConductorMark | None:
    """The conductor of a pin: the stated mark, else the one its marking names (`CONDUCTOR_MARKS`).

    The marking is the pin's printed one, else its name. A marking that names no conductor gives
    none. Example: a pin marked `U1` is `L1`; a pin marked `13` has none.
    """
    if template.conductor_mark is not None:
        return template.conductor_mark
    return CONDUCTOR_MARKS.get(template.marking or template.name)


def pole_count(poles: Iterable[Pole]) -> int:
    """The number of poles, a changeover's shared common counted once (connected pins).

    A pole is a connected set of pins: `11-12` and `11-14` share `11`, so they are one pole.
    """
    groups: list[set[Id[PortTemplate]]] = []
    for pole in poles:
        ends = {end.id for end in pole.ends}
        joined = [group for group in groups if group & ends]
        groups = [group for group in groups if group not in joined]
        groups.append(ends.union(*joined))
    return len(groups)


def pole_pin_names(
    kind: FunctionKind, links: Iterable[tuple[str, str, LinkKind]]
) -> frozenset[str]:
    """The names of the pins on a pole link of a function of `kind`; `links` are `(a, b, kind)`.

    A pole link is a switched or protective one (`is_pole_by_role`); `pole_side` reads these names.
    """
    role = function_role_of(kind)
    return frozenset(name for a, b, link in links if is_pole_by_role(role, link) for name in (a, b))
