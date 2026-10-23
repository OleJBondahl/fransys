"""Changeover throws in a series (SERIES-GAPS S7, S8): `k1.co_1.no` and `k1.co_1.nc`.

The throws come from the part's roles and links (`derive.link_throw`), never from a pin name.
"""

from copy import copy
from typing import TYPE_CHECKING

from fransys_author.errors import AuthorAttributeError, AuthorError
from fransys_author.surface._fixed import fixed_count
from fransys_author.surface._pairing import End, Ends
from fransys_model.derive import contact_kind_of, throws_of
from fransys_model.vocab import THROWS as VOCAB_THROWS
from fransys_model.vocab import PoleSide, PortRole
lazy from fransys_author.handles import Fn as EngineFn

if TYPE_CHECKING:
    from fransys_author.handles import Port
    from fransys_author.surface._pairing import PartFacts
    from fransys_author.surface.design import Design

THROWS = {row.word: role for role, row in VOCAB_THROWS.items() if row.word}


def whole_changeover(label: str, fn: EngineFn) -> AuthorError:
    """The refusal of a changeover passed whole to a series."""
    where = f"{label}.{fn.name}"
    return AuthorError(f"a changeover is two throws: use {where}.no or {where}.nc")


def not_a_changeover(label: str, fn: EngineFn, name: str) -> AuthorAttributeError:
    """The refusal of `.no` or `.nc` on a function that is not a changeover."""
    kind = fn.kind.value
    msg = f"{label}.{fn.name} is a {kind} function, not a changeover: .{name} names a throw"
    return AuthorAttributeError(msg)


def _poles(facts: PartFacts, fn: EngineFn, role: PortRole) -> list[tuple[Port, Port]]:
    """Each common of `fn` with its throw of `role`, as (common, throw), in common order."""
    by_template = {facts.port_template(port).id: port for port in fn.ports}
    found = throws_of(facts.links(fn), facts.templates)
    return [(by_template[t.common], by_template[t.throw]) for t in found if t.role is role]


def _is_selector(facts: PartFacts, poles: list[tuple[Port, Port]]) -> bool:
    """A changeover whose throws state the line side and commons the load side (S8)."""
    sides = [(facts.port_template(t).pole_side, facts.port_template(c).pole_side) for c, t in poles]
    return bool(sides) and all(side == (PoleSide.LINE, PoleSide.LOAD) for side in sides)


def states_selector(facts: PartFacts, fn: EngineFn) -> bool:
    """Whether the part of the changeover `fn` states S8's sides: a selector by its part."""
    return _is_selector(facts, _poles(facts, fn, PortRole.MAKE))


class Throw:
    """One throw of changeovers in a series: line at the common, load at the throw.

    A selector (its throws on the line side, or a `d.poles` group with `selector=True`) is
    entered at the throws and left at the commons. Several functions are one pole each, in order.

    Does not wire by itself: it stands in a `d.series` call.
    """

    def __init__(self, fns: tuple[EngineFn, ...], name: str, *, selector: bool = False) -> None:
        """The throw `name` (`no` or `nc`) of the changeovers `fns`."""
        self._fns, self._role, self._selector = fns, THROWS[name], selector
        self._turned = False  # entered at the throw, left at the common (`turn_throws`)
        self._commons = tuple(p for fn in fns for p in fn.ports if p.role is PortRole.COMMON)

    def _series_width(self) -> int:
        return len(self._commons)

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the SeriesElement protocol
        facts = design._pairing_facts
        poles = [pole for fn in self._fns for pole in _poles(facts, fn, self._role)]
        commons = tuple(End(common, facts.mark(common)) for common, _ in poles)
        throws = tuple(End(throw, facts.mark(throw)) for _, throw in poles)
        if self._selector or self._turned or _is_selector(facts, poles):
            return Ends(throws, commons)
        return Ends(commons, throws)


def throw(label: str, fn: EngineFn, name: str) -> Throw:
    """The throw `name` of `fn`; a function that is not a changeover raises, naming its kind."""
    if contact_kind_of(fn.kind) != "co":
        raise not_a_changeover(label, fn, name)
    return Throw((fn,), name)


def _fixed_at(elements: tuple[object, ...], i: int) -> bool:
    return 0 <= i < len(elements) and fixed_count(elements[i]) is not None


def turn_throws(elements: tuple[object, ...]) -> tuple[object, ...]:
    """A throw between two fixed terminals is entered at the throw and left at the common (C15).

    Does not turn a throw with a supply, a device or a strip beside it: its common stays the entry.
    """
    turned = []
    for i, element in enumerate(elements):
        if isinstance(element, Throw) and _fixed_at(elements, i - 1) and _fixed_at(elements, i + 1):
            element = copy(element)  # noqa: PLW2901 -- the caller's handle is not changed
            element._turned = True
        turned.append(element)
    return tuple(turned)
