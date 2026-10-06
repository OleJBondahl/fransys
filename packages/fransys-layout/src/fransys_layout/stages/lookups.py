"""One home for the small lookups every stage repeats: by-handle maps, keep-out, group, nets."""

from typing import TYPE_CHECKING, Protocol

from fransys_layout.geometry import Box, LayoutError, translate
from fransys_model.kernel import UnionFind

if TYPE_CHECKING:
    from collections.abc import Iterable

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
    """Every drawn port's owning function."""
    return {port.port: function.function for function in drawn for port in function.ports}


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
