"""The function blocks whose `d.series` wired each function, and what draws where (author-0050)."""

from typing import TYPE_CHECKING

from fransys_model.kernel import make_id
from fransys_model.layout import GroupHint
from fransys_model.vocab import Aspect, AspectNode, Function, Item, Placement, Port

from ._keys import scoped

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Id, Origin


class SeriesBlocks:
    """Per port, the blocks whose series wired it, in call order, with the first call's origin.

    `resolve` turns them into one `GroupHint` per function of a multi-function device that a
    single other block wired. It reads the draft and never writes it.
    """

    def __init__(self) -> None:
        """Start with no series."""
        self._blocks: dict[Id[Port], dict[Id[AspectNode], None]] = {}
        self._origin: dict[Id[Port], Origin] = {}

    def collect(self, block: Id[AspectNode], ports: tuple[Id[Port], ...], origin: Origin) -> None:
        """Note that a series written in `block` wired `ports`."""
        for port in ports:
            self._blocks.setdefault(port, {})[block] = None
            self._origin.setdefault(port, origin)

    def resolve(self, draft: Draft) -> list[tuple[GroupHint, Origin]]:
        """The hints to add, for the draft as it stands."""
        by_fn = self._by_function(draft)
        if not by_fn:
            return []
        homes = _homes(draft)
        several = _several_functions(draft)
        hints: list[tuple[GroupHint, Origin]] = []
        for function, (blocks, origin) in by_fn.items():
            item = _item_of(draft, function)
            home = homes.get(item)
            if home is None or item not in several or len(blocks) != 1 or list(blocks) == [home]:
                continue
            hint = _hint(draft, function, next(iter(blocks)))
            if hint is not None:
                hints.append((hint, origin))
        return hints

    def _by_function(
        self, draft: Draft
    ) -> dict[Id[Function], tuple[dict[Id[AspectNode], None], Origin]]:
        found: dict[Id[Function], tuple[dict[Id[AspectNode], None], Origin]] = {}
        for port, blocks in self._blocks.items():
            record = draft.record_of(port)
            assert isinstance(record, Port)  # noqa: S101 -- collect takes port ids only
            merged, _ = found.setdefault(record.function, ({}, self._origin[port]))
            merged.update(blocks)
        return found


def _item_of(draft: Draft, function: Id[Function]) -> Id[Item]:
    record = draft.record_of(function)
    assert isinstance(record, Function)  # noqa: S101 -- the key is a function id
    return record.item


def _homes(draft: Draft) -> dict[Id[Item], Id[AspectNode]]:
    """Each item's `=` block."""
    nodes = {
        r.id for r in draft.records() if isinstance(r, AspectNode) and r.aspect is Aspect.FUNCTION
    }
    return {r.item: r.node for r in draft.records() if isinstance(r, Placement) and r.node in nodes}


def _several_functions(draft: Draft) -> set[Id[Item]]:
    """The items with two functions or more: only a device split across blocks follows a series."""
    seen: set[Id[Item]] = set()
    several: set[Id[Item]] = set()
    for record in draft.records():
        if isinstance(record, Function):
            (several if record.item in seen else seen).add(record.item)
    return several


def _hint(draft: Draft, function: Id[Function], block: Id[AspectNode]) -> GroupHint | None:
    """The hint drawing `function` in `block`; none when an explicit hint is already there (P3)."""
    key = scoped(draft.key_of(function), "group_hint")  # ty: ignore[invalid-argument-type] -- the function has a key
    hint_id = make_id(GroupHint, key)
    if draft.record_of(hint_id) is not None:
        return None
    return GroupHint(id=hint_id, key=key, function=function, group=block)
