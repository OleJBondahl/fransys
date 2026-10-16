"""One home for the small lookups every stage repeats: by-handle maps, keep-out, group, nets."""

from typing import TYPE_CHECKING, Protocol

from fransys_layout.geometry import Box, LayoutError, translate
from fransys_model.kernel import UnionFind

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .types import DrawnFunction, Handle, PlacedFunction


class _Grouped(Protocol):
    @property
    def group_hint(self) -> Handle | None: ...

    @property
    def group_path(self) -> tuple[Handle, ...]: ...


def drawn_of(drawn: Iterable[DrawnFunction], caller: str) -> dict[Handle, DrawnFunction]:
    """The drawn functions by handle; two of one function is an assembly fault `caller` names."""
    found: dict[Handle, DrawnFunction] = {}
    for function in drawn:
        if function.function in found:
            msg = f"one function is drawn twice among the drawn functions {caller} was given"
            raise LayoutError(msg)
        found[function.function] = function
    return found


def placed_of(placed: Iterable[PlacedFunction], caller: str) -> dict[Handle, PlacedFunction]:
    """The placed functions by handle; two placements of one function is a fault `caller` names."""
    found: dict[Handle, PlacedFunction] = {}
    for function in placed:
        if function.function in found:
            msg = f"one function is placed twice on the page {caller} was given"
            raise LayoutError(msg)
        found[function.function] = function
    return found


def owner_of(drawn: Iterable[DrawnFunction]) -> dict[Handle, Handle]:
    """Every drawn port's owning function.

    A boundary port drawn as a pin view in the parent (model-0188) is also a port of its own
    function, drawn on the unit's pages: the function owns it, the pin view only itself.
    """
    owner: dict[Handle, Handle] = {}
    for function in drawn:
        for port in function.ports:
            if owner.get(port.port, port.port) == port.port:
                owner[port.port] = function.function
    return owner


def placed_keepout(one: PlacedFunction) -> Box:
    """A placed function's keep-out box on its page."""
    return translate(one.geometry.keepout, dx=one.at.x, dy=one.at.y)


def group_of(spec: _Grouped) -> Handle | None:
    """A function's group: its hint, else the last of its group path."""
    return spec.group_hint or (spec.group_path[-1] if spec.group_path else None)


def nets_from_pairs(
    pairs: Iterable[tuple[Handle, Handle]], members: Iterable[Handle] = ()
) -> UnionFind[Handle]:
    """The nets the port `pairs` join; `members` register first, so lone ports show in `groups`."""
    nets: UnionFind[Handle] = UnionFind(members)
    for first, second in pairs:
        nets.union(first, second)
    return nets


def device_turns(against: Iterable[bool]) -> bool:
    """A device drawn in one cell turns as a whole: with a wired pole, each one running against."""
    # `against` holds one vote per wired pole; an unwired pole has no direction and sends none
    votes = tuple(against)
    return bool(votes) and all(votes)


def turn_mirrors(*, terminal: bool) -> bool:
    """The form of a turned pole: a strip terminal turns at R180, every other one at MR180."""
    return not terminal


def set_rank(ranks: Mapping[int, int], drawing_set: int) -> int:
    """The rank of `drawing_set` in its unit; a set with none is a caller bug (decision 0201)."""
    if drawing_set not in ranks:
        msg = f"drawing set {drawing_set} has no rank: pass derive.set_ranks of the plans"
        raise ValueError(msg)
    return ranks[drawing_set]
