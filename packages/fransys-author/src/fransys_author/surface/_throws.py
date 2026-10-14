"""Changeover throws in a series (SERIES-GAPS S7, S8): `k1.co_1.no` and `k1.co_1.nc`.

The throws come from the part's roles and links (`vocab.link_throw`), never from a pin name.
"""

from typing import TYPE_CHECKING

from fransys_author.errors import AuthorAttributeError, AuthorError
from fransys_author.surface._pairing import End, Ends
from fransys_model.vocab import FunctionKind, PoleSide, PortRole, link_throw, port_order_key

if TYPE_CHECKING:
    from fransys_author.handles import Fn as EngineFn
    from fransys_author.handles import Port
    from fransys_author.surface._pairing import PartFacts
    from fransys_author.surface.design import Design

THROWS = {"no": PortRole.MAKE, "nc": PortRole.BREAK}


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
    found = []
    for link in facts.links(fn):
        joined = link_throw(link, facts.templates)
        if joined is not None and joined[1] is role:
            found.append((by_template[joined[0]], by_template[joined[2]]))
    return sorted(found, key=lambda pole: port_order_key(facts.port_template(pole[0])))


def _is_selector(facts: PartFacts, poles: list[tuple[Port, Port]]) -> bool:
    """A changeover whose throws state the line side and commons the load side (S8)."""
    sides = [(facts.port_template(t).pole_side, facts.port_template(c).pole_side) for c, t in poles]
    return bool(sides) and all(side == (PoleSide.LINE, PoleSide.LOAD) for side in sides)


class Throw:
    """One throw of a changeover in a series: line at the common, load at the throw.

    A selector (its throws on the line side) is entered at the throws and left at the commons.
    """

    def __init__(self, fn: EngineFn, name: str) -> None:
        """The throw `name` (`no` or `nc`) of the changeover `fn`."""
        self._fn, self._role = fn, THROWS[name]
        self._commons = tuple(port for port in fn.ports if port.role is PortRole.COMMON)

    def _series_width(self) -> int:
        return len(self._commons)

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the SeriesElement protocol
        facts = design._pairing_facts
        poles = _poles(facts, self._fn, self._role)
        commons = tuple(End(common, facts.mark(common)) for common, _ in poles)
        throws = tuple(End(throw, facts.mark(throw)) for _, throw in poles)
        if _is_selector(facts, poles):
            return Ends(throws, commons)
        return Ends(commons, throws)


def throw(label: str, fn: EngineFn, name: str) -> Throw:
    """The throw `name` of `fn`; a function that is not a changeover raises, naming its kind."""
    if fn.kind is not FunctionKind.CONTACT_CO:
        raise not_a_changeover(label, fn, name)
    return Throw(fn, name)
