"""`d.poles`: one-pole contacts of one device as one multi-pole element (API-CLARITY C6.4)."""

from typing import TYPE_CHECKING

from fransys_author.errors import AuthorError
from fransys_author.surface._handles import Fn
from fransys_author.surface._pairing import Ends, ends_of, template_poles
from fransys_author.surface._throws import THROWS, Throw, states_selector
from fransys_model.derive import contact_kind_of, is_contact_kind, pole_count

if TYPE_CHECKING:
    from fransys_author.surface._pairing import PartFacts
    from fransys_author.surface.design import Design

_KIND_WORDS = "contact_no, contact_nc, contact_co or switch"


class Poles:
    """Contacts of one device grouped in pole order: `q.no` and `q.nc` for changeovers, else `q`.

    Does not wire anything: a series wires it, one pole per member.
    """

    def __init__(self, members: tuple[Fn, ...], *, selector: bool) -> None:
        """Hold `members`; `d.poles` makes these."""
        self._members, self._selector = members, selector
        self._label = f"{members[0]._label}.{members[0]._fn.name}"

    def _changeover(self) -> bool:
        return contact_kind_of(self._members[0]._fn.kind) == "co"

    def _throw(self, name: str) -> Throw:
        if not self._changeover():
            kind = self._members[0]._fn.kind.value
            msg = f"a group of {kind} functions has no throws: pass the group itself"
            raise AuthorError(msg)
        return Throw(tuple(m._fn for m in self._members), name, selector=self._selector)

    def __getattr__(self, name: str) -> Throw:
        """`q.no` and `q.nc`: a changeover group's make or break throws, one per member, in order.

        Does not exist on a group of make, break or switch contacts: pass that group itself.
        """
        if name not in THROWS:
            raise AttributeError(name)
        return self._throw(name)

    def _series_width(self) -> int:
        return len(self._members)

    def _series_ends(self, design: Design, width: int | None) -> Ends:  # noqa: ARG002 -- the SeriesElement protocol
        if self._changeover():
            msg = "a changeover group is two throws: use its .no or .nc"
            raise AuthorError(msg)
        found = [ends_of(design._pairing_facts, m._fn) for m in self._members]
        return Ends(
            tuple(e for one in found for e in one.line), tuple(e for one in found for e in one.load)
        )


def _pole_count(facts: PartFacts, member: Fn) -> int:
    return pole_count(template_poles(facts, member._fn))


def _selector_refusal(facts: PartFacts, member: Fn) -> str | None:
    """Why `selector=True` cannot turn `member`: its part states sides, or it has no throws."""
    fn, label = member._fn, member._label
    if contact_kind_of(fn.kind) != "co":
        where = f"{label}.{fn.name}"
        return f"selector=True turns changeover throws; {where} is a {fn.kind.value} function"
    if states_selector(facts, fn):
        return f"-{label}'s part already states a selector: pass {label.lower()}.{fn.name}"
    return None


def _refusal(facts: PartFacts, first: Fn, member: Fn) -> str | None:
    """Why `member` cannot stand in a group led by `first`, `None` when it can."""
    fn, where = member._fn, f"{member._label}.{member._fn.name}"
    if not is_contact_kind(fn.kind):
        return f"{where} is a {fn.kind.value} function: d.poles groups {_KIND_WORDS} functions"
    if fn.item != first._fn.item:
        return f"{where} is not a function of {first._label}: d.poles groups one device's contacts"
    if fn.kind is not first._fn.kind:
        kinds = f"{fn.kind.value} function, not {first._fn.kind.value}"
        return f"{where} is a {kinds}: one kind per group"
    if (count := _pole_count(facts, member)) != 1:
        return f"{where} has {count} poles: d.poles groups one-pole functions"
    return None


def _members(functions: tuple[object, ...]) -> tuple[Fn, ...]:
    """`functions` as surface functions; none, or anything else, raises."""
    if not functions:
        msg = "d.poles groups one function or more"
        raise AuthorError(msg)
    members = tuple(one for one in functions if isinstance(one, Fn))
    if len(members) != len(functions):
        other = next(one for one in functions if not isinstance(one, Fn))
        msg = f"d.poles takes functions of one device (k1.co_1), not {type(other).__name__}"
        raise AuthorError(msg)
    return members


def _check(design: Design, members: tuple[Fn, ...], *, selector: bool) -> None:
    """Raise on the first member that cannot stand in this group, naming it."""
    facts, ids = design._pairing_facts, [m._fn.id for m in members]
    for member in members:
        why = _selector_refusal(facts, member) if selector else None
        if (why := why or _refusal(facts, members[0], member)) is not None:
            raise AuthorError(why)
        if member._fn.id in design._grouped or ids.count(member._fn.id) > 1:
            where = f"{member._label}.{member._fn.name}"
            msg = f"{where} is in a pole group already: a contact stands in one group"
            raise AuthorError(msg)


def group(design: Design, functions: tuple[object, ...], *, selector: bool) -> Poles:
    """Check `functions`, write their `PoleGroup` and return the group element."""
    members = _members(functions)
    _check(design, members, selector=selector)
    design._grouped.update(m._fn.id for m in members)
    design._engine.pole_group(tuple(m._fn for m in members), selector=selector)
    return Poles(members, selector=selector)
