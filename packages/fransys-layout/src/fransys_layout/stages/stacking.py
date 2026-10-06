"""D3, R7.1, S12: a column's stacking rule, one home for `place` and `references.joins`.

`place` stacks a column's rows at the row gap, glues an attachment row to its host's row
(`blocks`), and stands each block `row_spacing` below the one before (`gaps_below`). S12's
join rule reads a port's offset from that same stacking: `place.page_stack` runs `place`'s own
steps up to its bands on `place`'s own inputs and gives the page as a `PageStack`, which
`references.joins` reads, and `join_y` says where a run's ports meet. So a run `references`
joins is one `place` can align, and `place` aligns it (`JoinedRun`) with the same numbers.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol
lazy from collections.abc import Sequence

from fransys_layout.geometry import Facing
from fransys_model.kernel import AuthoringKey, Id, value

if TYPE_CHECKING:
    from collections.abc import Iterable


class Stacked(Protocol):
    """A cell as the stacking rule reads it: its function, and its host when it is attached."""

    @property
    def function(self) -> Id[Any]:
        """The function drawn in the cell."""
        ...

    @property
    def host(self) -> Id[Any] | None:
        """R7.1: the function the cell is attached to, `None` for a cell of its own."""
        ...


class Boxy(Stacked, Protocol):
    """A cell with whether it is a generic box, a connector or a terminal (R6 D4)."""

    @property
    def boxy(self) -> bool:
        """Whether the cell is drawn compact (R6 D4)."""
        ...


def blocks[T: Stacked](rows: Sequence[list[T]]) -> list[list[list[T]]]:
    """Rows grouped so an attachment row stays glued to its host's row (R7.1, S13)."""
    grouped: list[list[list[T]]] = []
    pending: list[list[T]] = []
    for row in rows:
        if all(cell.host is not None for cell in row):
            host = row[0].host
            if grouped and any(cell.function == host for held in grouped[-1] for cell in held):
                grouped[-1].append(row)
            else:
                pending.append(row)
            continue
        grouped.append([*pending, row])
        pending = []
    if pending:
        grouped.append(pending)
    return grouped


def gaps_below[T: Boxy](rows: Sequence[list[T]], row_gap: int, spacing: int) -> list[int]:
    """The gap each row keeps from the row below it (F5-A, R7.1, R6 D4)."""
    if all(cell.boxy for row in rows for cell in row):
        return [row_gap] * len(rows)
    gaps: list[int] = []
    for block in blocks(rows):
        gaps += [row_gap] * (len(block) - 1) + [spacing]
    return gaps


@value
class JoinEnd:
    """One port of a would-be joined run, as `place` stacks its column (S12)."""

    port: Id[Any]
    row: int
    offset: int
    height: int


def join_y(ends: tuple[JoinEnd, ...], room: int) -> int | None:
    """S12 (LD9): the offset at which `place` puts every end of a run on one y, else `None`."""
    if len({end.row for end in ends}) != 1:
        return None
    y = join_offset(end.offset for end in ends)
    if any(end.height + y - end.offset > room for end in ends):
        return None
    return y


def join_offset(offsets: Iterable[int]) -> int:
    """S12: where a run's ports meet: its deepest port's offset, since `place` only lowers."""
    return max(offsets)


@value
class StackedPort:
    """One port as `place` stacks its page before the bands (S12)."""

    row: int
    offset: int
    x: int
    facing: Facing


@dataclass(frozen=True, slots=True)
class PageStack:
    """A page as `place` stacks it before its bands, which S12's join rule reads (`page_stack`)."""

    ports: frozendict[tuple[AuthoringKey, Id[Any]], StackedPort]
    heights: frozendict[AuthoringKey, int]
    last: frozendict[AuthoringKey, int]
    room: int


@value
class JoinedEnd:
    """One port of a joined run: the port, and the column it stands in on the run's page."""

    column: AuthoringKey
    port: Id[Any]


@value
class JoinedRun:
    """S12: one run `references` joined, which `place` puts on one y."""

    drawing_set: int
    page: int
    ends: tuple[JoinedEnd, ...]
