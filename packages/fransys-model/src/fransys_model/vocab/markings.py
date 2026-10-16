"""Pole order and line side from a part's pin markings (decision model-0128).

One function gives the order of a function's poles and each pole's line side, so layout, the
contact entries and every output read the same answer. A pole is a declared `InternalLink`.
"""

import re
from collections.abc import Iterable, Mapping  # noqa: TC003 -- signature tests resolve hints at runtime
from typing import NamedTuple

from fransys_model.kernel import Id  # noqa: TC001 -- signature tests resolve hints at runtime

from .enums import FunctionKind, LinkKind, PoleSide
from .roles import LINK_ROLES, function_role_of
from .roles_types import FunctionRole  # noqa: TC001 -- signature tests resolve hints at runtime
from .templates import InternalLink, PortTemplate  # noqa: TC001 -- signature tests resolve hints at runtime

_RUN = re.compile(r"\d+|\D+")


class Pole(NamedTuple):
    """One pole's ends: `line` is the end whose `pole_side` is `line`, else `None`.

    `ends` is `(line, load)` when `line` is known, else the two ends in natural marking order.
    """

    line: PortTemplate | None
    ends: tuple[PortTemplate, PortTemplate]


def _token(run: str) -> tuple[int, int, str]:
    """A digit run sorts by value, any other run as text after every number."""
    return (0, int(run), "") if run.isdigit() else (1, 0, run)


def marking_key(marking: str) -> tuple[tuple[int, int, str], ...]:
    """Sort key of a pin marking: digit runs by value (9 before 10), text after numbers."""
    return tuple(_token(run) for run in _RUN.findall(marking))


def identifier(name: str) -> str:
    """The Python identifier of a part's function or pin `name`: `24V+` is `P_24V_plus`.

    In a pin or function name `-` is a sign (`24V-` is `P_24V_minus`), unlike a part number's.
    `+` and `-` become `_plus` and `_minus`, other non-word characters `_`, a leading digit `P_`.
    """
    text = re.sub(r"\W", "_", name.replace("+", "_plus").replace("-", "_minus"))
    return f"P_{text}" if text[:1].isdigit() else text


def port_order_key(template: PortTemplate) -> tuple[tuple[tuple[int, int, str], ...], str]:
    """Order of one end: its marking (its name when none is printed), then its name."""
    marking = template.name if template.marking is None else template.marking
    return marking_key(marking), template.name


def _pole(a: PortTemplate, b: PortTemplate) -> Pole:
    """The pole joining `a` and `b`; the line end first when exactly one end is `line`."""
    for line, load in ((a, b), (b, a)):
        if line.pole_side is PoleSide.LINE and load.pole_side is not PoleSide.LINE:
            return Pole(line, (line, load))
    first, second = sorted((a, b), key=port_order_key)
    return Pole(None, (first, second))


def unlinked_poles(templates: Iterable[PortTemplate]) -> tuple[Pole, ...]:
    """The poles of pins with no pole link: consecutive pins in `port_order_key` order pair.

    An odd pin left over is a one-pin pole `(pin, pin)`, last: no pin goes missing.
    """
    ordered = sorted(templates, key=port_order_key)
    poles = [_pole(a, b) for a, b in zip(ordered[::2], ordered[1::2], strict=False)]
    if len(ordered) % 2:
        poles.append(Pole(None, (ordered[-1], ordered[-1])))
    return tuple(poles)


def pole_order(
    links: Iterable[InternalLink], templates: Mapping[Id[PortTemplate], PortTemplate]
) -> tuple[Pole, ...]:
    """The poles of `links` in natural order of each pole's first marking (9 before 10)."""
    poles = (_pole(templates[link.a], templates[link.b]) for link in links)
    return tuple(sorted(poles, key=lambda pole: min(map(port_order_key, pole.ends))))


def is_pole_by_role(role: FunctionRole, link: LinkKind) -> bool:
    """A pole is a link whose role is `pole`, or a conductive link of a function that protects."""
    return LINK_ROLES[link].pole or (role.protects and link is LinkKind.CONDUCTIVE)


def poles_by_role(
    role: FunctionRole,
    links: Iterable[InternalLink],
    templates: Mapping[Id[PortTemplate], PortTemplate],
) -> tuple[Pole, ...]:
    """The poles of a function of `role` from all its links, as `(line, load)` in order."""
    return pole_order((link for link in links if is_pole_by_role(role, link.kind)), templates)


def function_poles(
    function: FunctionKind,
    links: Iterable[InternalLink],
    templates: Mapping[Id[PortTemplate], PortTemplate],
) -> tuple[Pole, ...]:
    """`poles_by_role` at a kind's row: kept for the legacy engine until SCHEMATIC-FLIP."""
    return poles_by_role(function_role_of(function), links, templates)
