"""A plain level's view rows, its stubs, its tab texts, and an open strip's (model-0202).

The one place a level's boxes and lines meet their stubs and tabs; layout draws what it returns.
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from fransys_model.derive.house_settings import stub_text_of
from fransys_model.kernel import Id
from fransys_model.layout import BoxKey, OverviewRef, OverviewRefKind
lazy from fransys_model.kernel import Model
lazy from fransys_model.vocab.core import Unit

from .overview_stub_ends import stub_ends
from .overview_tabs import line_tabs
from .overview_text import (
    overview_line_text,
    overview_member_text,
    overview_stub_lines,
    overview_stub_text,
)
from .rows_overview_view import Rows, ViewBox, ViewLine, ViewMember

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .rows import OverviewLevel, OverviewLine, OverviewStub, StripView
    from .rows_overview import FoldStub, TerminalStubs

__all__ = [
    "level_rows",
    "ref_of",
    "shared_rows",
    "strip_rows",
    "stub_rows",
    "tab_rows",
    "with_tabs",
]

Tabs = dict[tuple[BoxKey, BoxKey, Id[Any]], tuple[str | None, str | None]]


def ref_of(box: Id[Any]) -> OverviewRef:
    """The reference of a level box, which is a unit instance or an item."""
    if box.kind == "unit":
        return OverviewRef(kind=OverviewRefKind.UNIT, unit=box)
    return OverviewRef(kind=OverviewRefKind.ITEM, item=box)


def _member(model: Model, unit: Id[Unit], stub: OverviewStub) -> ViewMember:
    return ViewMember(
        ref=stub.end,
        lines=(lines := overview_stub_lines(stub)),
        text=overview_member_text(
            stub_text_of(model), lines, overview_stub_text(model, unit, stub)
        ),
    )


def stub_rows(
    model: Model, unit: Id[Unit], placed: Sequence[tuple[OverviewRef, OverviewStub | FoldStub]]
) -> Rows:
    """The stub boxes and lines of `placed`: one box per far end, from `stub_ends`."""
    merged_boxes, merged_lines = stub_ends(model, unit, placed)
    boxes = tuple(
        ViewBox(
            key=BoxKey(ref=b.end, at=b.at),
            lines=b.lines,
            dashed=b.by_others,
            members=tuple(_member(model, unit, m) for m in b.members),
        )
        for b in merged_boxes
    )
    lines = tuple(
        ViewLine(
            a=BoxKey(ref=ln.at),
            b=BoxKey(ref=ln.end, at=ln.at),
            kind=ln.kind.value,
            via=ln.via,
            strip=None,
            text=ln.text,
        )
        for ln in merged_lines
    )
    return boxes, lines


def shared_rows(
    model: Model,
    unit: Id[Unit],
    hung: Sequence[tuple[OverviewRef, OverviewStub | FoldStub]],
    wired: Sequence[tuple[OverviewRef, OverviewStub | FoldStub]],
) -> Rows:
    """Stub boxes of `hung`, and lines from the boxes of `wired` to the stub box of their far end.

    `wired[i]` joins the stub box of `hung[i]`: a box in `hung` is where its stub hangs, so a far
    end hung on two boxes has a box on each and every line ends on its own (A17).
    """
    on = {(part_at, part.end): at for (at, _), (part_at, part) in zip(hung, wired, strict=True)}
    boxes, _ = stub_rows(model, unit, hung)
    _, lines = stub_rows(model, unit, wired)
    return boxes, tuple(
        replace(ln, b=BoxKey(ref=ln.b.ref, at=on[ln.a.ref, ln.b.ref])) for ln in lines
    )


def _line(line: OverviewLine) -> ViewLine:
    ref = line.ref
    return ViewLine(
        a=BoxKey(ref=ref_of(ref.a)),
        b=BoxKey(ref=ref_of(ref.b)),
        kind=ref.kind.value,
        via=ref.via,
        strip=None,
        text=overview_line_text(line),
    )


def level_rows(model: Model, level: OverviewLevel) -> Rows:
    """The level's boxes then its stub boxes, its lines then its stub lines, in rows order."""
    boxes = tuple(
        ViewBox(key=BoxKey(ref=ref_of(b.box)), lines=b.lines, dashed=b.dashed) for b in level.boxes
    )
    lines = tuple(_line(line) for line in level.lines)
    if level.unit is None:
        return boxes, lines
    stub_boxes, stub_lines = stub_rows(model, level.unit, [(ref_of(s.box), s) for s in level.stubs])
    return (*boxes, *stub_boxes), (*lines, *stub_lines)


def _hung(
    placed: Sequence[tuple[OverviewRef, OverviewStub]],
) -> list[tuple[OverviewRef, OverviewStub]]:
    """`placed` with each far end moved onto the first box wired to it."""
    owner: dict[OverviewRef, OverviewRef] = {}
    for at, stub in placed:
        owner.setdefault(stub.end, at)
    return [(owner[stub.end], stub) for _, stub in placed]


def strip_rows(
    model: Model, unit: Id[Unit], plain: Rows, view: StripView, stubs: tuple[TerminalStubs, ...]
) -> Rows:
    """The level's `plain` rows with `view.strip` opened: its terminals stand in its place.

    The strip's box, its stub boxes and every line to them give way to the terminals' own lines.
    The terminals share the stubs the strip had: a far end has one box (O5).
    """
    boxes, lines = plain
    gone = {BoxKey(ref=OverviewRef(kind=OverviewRefKind.ITEM, item=view.strip))}
    gone |= {b.key for b in boxes if b.key.at is not None and BoxKey(ref=b.key.at) in gone}
    terminals = tuple(
        ViewBox(key=BoxKey(ref=ref_of(t.item)), lines=(t.label,), dashed=False)
        for t in view.terminals
    )
    kept = tuple(ln for ln in lines if not {ln.a, ln.b} & gone)
    extra = tuple(_line(line) for t in view.terminals for line in t.lines)
    placed = [(ref_of(t.terminal), s) for t in stubs for s in t.stubs]
    stub_boxes, stub_lines = shared_rows(model, unit, _hung(placed), placed)
    return (
        (*(b for b in boxes if b.key not in gone), *terminals, *stub_boxes),
        (*kept, *extra, *stub_lines),
    )


def tab_rows(model: Model, unit: Id[Unit] | None) -> Tabs:
    """The tab texts of `unit`'s cable lines, keyed by (a, b, cable)."""
    return {
        (BoxKey(ref=ref_of(t.ref.a)), BoxKey(ref=ref_of(t.ref.b)), t.ref.via): (t.tab_a, t.tab_b)
        for t in line_tabs(model, unit)
        if t.ref.via is not None
    }


def _tabbed(line: ViewLine, rows: Tabs) -> ViewLine:
    """`line` with the tab text at each end the block diagram draws, in either order of its row."""
    if line.kind != "cable" or line.via is None:
        return line
    found = rows.get((line.a, line.b, line.via))
    if found is None:
        other = rows.get((line.b, line.a, line.via))
        found = (None, None) if other is None else (other[1], other[0])
    return replace(line, tab_a=found[0], tab_b=found[1])


def with_tabs(rows: Rows, tabs: Tabs) -> Rows:
    """`rows` with each cable line carrying the tab text at each end."""
    boxes, lines = rows
    return boxes, tuple(_tabbed(line, tabs) for line in lines)
