"""The stub boxes and lines of a level, merged per far end (O3b, O5).

One far end at one box is one stub box with its port tails, and one line per kind and carrier
joins it to the box. `stub_ends` is the one merge; layout only draws what it returns. Reached as
`derive.stub_ends`.
"""

from typing import NamedTuple
lazy from collections.abc import Sequence

from fransys_model.layout import OverviewRefKind
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.layout import OverviewRef
lazy from fransys_model.vocab.core import Item, Unit

from .cable_drawing import end_by_others
from .drawing_text import external_note
from .overview_text import (
    closed_fold,
    overview_closed_text,
    overview_end_text,
    overview_fold_stub_lines,
    overview_stub_lines,
)
from .rows_overview import FoldStub
lazy from .rows import OverviewLinkKind, OverviewStub

__all__ = ["StubBox", "StubLine", "stub_ends"]


class StubBox(NamedTuple):
    """The stub box of one far end `end` at the box `at`: its text lines.

    `by_others` is set when `end` is an item that is by others: the box is dashed and its first
    line ends `(by others)`, as the system level prints it.
    """

    at: OverviewRef
    end: OverviewRef
    lines: tuple[str, ...]
    by_others: bool = False
    members: tuple[OverviewStub, ...] = ()


class StubLine(NamedTuple):
    """The line from `at` to the stub box of `end`, for one kind and carrier, with its text."""

    at: OverviewRef
    end: OverviewRef
    kind: OverviewLinkKind
    via: Id[Item] | None
    count: int
    text: str


def _lines(stub: OverviewStub | FoldStub) -> tuple[str, ...]:
    return (
        overview_fold_stub_lines(stub) if isinstance(stub, FoldStub) else overview_stub_lines(stub)
    )


def _box(
    model: Model,
    at: OverviewRef,
    end: OverviewRef,
    held: tuple[list[tuple[str, ...]], tuple[OverviewStub, ...]],
) -> StubBox:
    """The stub box of `end` at `at`: the first far text, then each port tail once, its members."""
    rows, members = held
    far, *tails = (rows[0][0], *dict.fromkeys(t for row in rows for t in row[1:]))
    others = end.item is not None and end_by_others(model, end.item, None)
    lines = (f"{far} ({external_note()})" if others else far, *tails)
    return StubBox(at, end, lines, others, members)


def _members(stub: OverviewStub | FoldStub) -> tuple[OverviewStub, ...]:
    """The single stubs a fold opens to; none for a stub that is not a fold of other stubs."""
    folded = isinstance(stub, FoldStub) and stub.end.kind is not OverviewRefKind.ITEM
    return stub.members if folded else ()


def _line_text(
    model: Model,
    unit: Id[Unit],
    key: tuple[OverviewRef, OverviewRef, OverviewLinkKind, Id[Item] | None],
    count: int,
    cables: set[Id[Item]] | None,
) -> str:
    """A closed fold's `x N` (N its cables, else its count); other lines `overview_end_text`."""
    if cables is None or key[3] is not None:
        return overview_end_text(model, unit, key[2], key[3], count)
    return overview_closed_text(len(cables) if cables else count)


def stub_ends(
    model: Model, unit: Id[Unit], placed: Sequence[tuple[OverviewRef, OverviewStub | FoldStub]]
) -> tuple[tuple[StubBox, ...], tuple[StubLine, ...]]:
    """The stub boxes and lines of `placed`, each stub with the box `at` it hangs on.

    A box holds the first stub's far text, then the port tails of all its stubs once each, in order.
    Counts add per kind and carrier; a line's text is `overview_end_text`, or `x N` to a closed
    fold (N its distinct cables when it is a cable fold). Both keep first-seen order.
    """
    texts: dict[tuple[OverviewRef, OverviewRef], list[tuple[str, ...]]] = {}
    members: dict[tuple[OverviewRef, OverviewRef], tuple[OverviewStub, ...]] = {}
    counts: dict[tuple[OverviewRef, OverviewRef, OverviewLinkKind, Id[Item] | None], int] = {}
    closed: dict[
        tuple[OverviewRef, OverviewRef, OverviewLinkKind, Id[Item] | None], set[Id[Item]]
    ] = {}
    for at, stub in placed:
        texts.setdefault((at, stub.end), []).append(_lines(stub))
        members[at, stub.end] = tuple(
            dict.fromkeys((*members.get((at, stub.end), ()), *_members(stub)))
        )
        key = (at, stub.end, stub.kind, stub.via)
        counts[key] = counts.get(key, 0) + stub.count
        if isinstance(stub, FoldStub) and closed_fold(stub):
            cables = closed.setdefault(key, set())
            if stub.kind is OverviewLinkKind.CABLE:
                cables.update(m.via for m in stub.members if m.via is not None)
    boxes = tuple(
        _box(model, at, end, (rows, members[at, end])) for (at, end), rows in texts.items()
    )
    lines = tuple(
        StubLine(
            key[0],
            key[1],
            key[2],
            key[3],
            count,
            _line_text(model, unit, key, count, closed.get(key)),
        )
        for key, count in counts.items()
    )
    return boxes, lines
