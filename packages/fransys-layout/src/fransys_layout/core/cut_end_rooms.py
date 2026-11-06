"""The cut ends of a row and the room they take: the one place that says which end is a cut end (R1338, R1634, R1646).

Every site that sizes, steps out or stands a cut end reads `cut_ends`; `stub_room` and `arrow_room` are the y it holds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from .band import arrow_box
from .flow_values import block_id
from .geometry import stub_views
from .ref_kind import kind_of
from .values import RefKind, StandClass

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .flow_values import Fan
    from .values import Options, PagePlan, PinRef, Ref, RefEnd


class CutEnd(NamedTuple):
    """One cut end of a fan on a row: its (pin, kind) key, the end, whether it stands at the right, and the poles whose lanes it ends (R1338)."""

    key: tuple[PinRef | None, str]
    end: RefEnd
    right: bool
    poles: frozenset[int]
    lead: int


def pole_of(fan: Fan, pin: PinRef | None) -> int:
    """The pole of the attachment at `pin`: `Attach.pole`, the one source; a plain fan's one lane is pole 0."""
    return next((a.pole for a in (*fan.drivers, *fan.legs) if a.pin == pin), 0) if fan.lanes > 1 else 0


def laned_stub(fan: Fan) -> bool:
    """True for a bundle of lanes: its cross-document stub is a cut end on its lanes, not at a boundary pin."""
    return fan.lanes > 1


def _first_row(fan: Fan, plan: PagePlan) -> int | None:
    """The first row of the page that holds a column or card the fan attaches to: where its cross-document stub stands (CL2b)."""
    cols = {a.column for a in (*fan.drivers, *fan.legs)}
    cards = {block_id("card", a.pin.sym) for a in (*fan.drivers, *fan.legs) if a.column is None}
    return next((k for k, row in enumerate(plan.rows) if cols.intersection(row.columns) or cards.intersection(row.blocks)), None)


def _arrow_ends(ref: Ref, fan: Fan, page: int, row: int) -> list[CutEnd]:
    """The ends of an arrow of `fan` at (page, row): `ends[0]` stands right, `ends[1]` left."""
    if kind_of(ref) is not RefKind.ARROW or ref.net != fan.id:
        return []
    return [
        CutEnd((e.pin, str(RefKind.ARROW)), e, i == 0, frozenset(pole_of(fan, p) for p in (e.pin, *e.also)), pole_of(fan, e.pin))
        for i, e in enumerate(ref.ends[:2])
        if (e.page, e.row) == (page, row)
    ]


def _stub_ends(ref: Ref, fan: Fan, page: int) -> list[CutEnd]:
    """The end of a bundle's cross-document stub on `page`: one end for every pole it stands for, at the right (CL2b, CL3)."""
    if kind_of(ref) is not RefKind.STUB or not laned_stub(fan) or ref.net not in fan.nets:
        return []
    return [
        CutEnd((e.pin, str(RefKind.STUB)), e, right=True, poles=frozenset(pole_of(fan, p) for p in (e.pin, *e.also)), lead=pole_of(fan, e.pin))
        for e in ref.ends
        if e.stand is StandClass.TRUNK_END and e.page == page
    ]


def cut_ends(refs: Iterable[Ref], plan: PagePlan, fans: Iterable[Fan], row: int) -> tuple[CutEnd, ...]:
    """The cut ends of `fans` on (plan.page, row): an arrow's ends there, and a bundle's stub in the first row of its fan (R1338).

    The one place that says which end is a cut end; every site that sizes, steps out or stands one reads it.
    """
    refs = tuple(refs)
    out: list[CutEnd] = []
    for fan in fans:
        out += (c for r in refs for c in _arrow_ends(r, fan, plan.page, row))
        if _first_row(fan, plan) == row:
            out += (c for r in refs for c in _stub_ends(r, fan, plan.page))
    return tuple(out)


def arrow_ends(refs: Iterable[Ref], plan: PagePlan, fans: Iterable[Fan], row: int) -> tuple[int, int]:
    """The cut ends (of `fans`) at the left and the right end of a row."""
    ends = cut_ends(refs, plan, fans, row)
    return sum(not c.right for c in ends), sum(c.right for c in ends)


def arrow_poles(fan: Fan, refs: Iterable[Ref], plan: PagePlan, row: int) -> tuple[frozenset[int], frozenset[int]]:
    """The poles whose lane ends at a cut end at the (left, right) end of the fan's trunk in the row."""
    ends = cut_ends(refs, plan, (fan,), row)
    return (frozenset(p for c in ends if not c.right for p in c.poles), frozenset(p for c in ends if c.right for p in c.poles))


def arrow_leads(fan: Fan, refs: Iterable[Ref], plan: PagePlan, row: int) -> tuple[frozenset[int], frozenset[int]]:
    """The poles whose lane carries the cut end's marker at the (left, right) end: the one whose end the other lanes of its bundle meet at."""
    ends = cut_ends(refs, plan, (fan,), row)
    return (frozenset(c.lead for c in ends if not c.right), frozenset(c.lead for c in ends if c.right))


def stub_room(refs: Iterable[Ref], plan: PagePlan, fans: Iterable[Fan], r: int, options: Options) -> int:
    """The y the stub boxes at row r's trunk ends take: the tallest, from the `stub_views` the legs' x reads (R1634).

    A bundle's trunk-end stub and a leg-class stub with no clear leg line both stand at the trunk's `arrow_sides[0]` end.
    """
    refs = tuple(refs)
    ends = [c.end for c in cut_ends(refs, plan, fans, r) if c.right and c.key[1] == str(RefKind.STUB)]
    ends += [e for rf in refs if kind_of(rf) is RefKind.STUB for e in rf.ends if e.stand is StandClass.LEG and (e.page, e.row) == (plan.page, r)]
    turned = options.marker_facing[options.arrow_sides[0]]
    heights = [views[turned].h for e in ends if e.pin and (views := stub_views(options.stub_lines, options.stub_table, e.pin, e.also, e.far))]
    return max(heights, default=0)


def arrow_room(refs: Iterable[Ref], plan: PagePlan, fans: Iterable[Fan], r: int, options: Options) -> int:
    """The y a lane-end arrow takes under its lane in row r: its half box and one grid (N2, R1646); 0 with none.

    The one value of the term: the placed trunk, the solved spans and the cut's row size all read it.
    """
    return next(
        (
            arrow_box(options, options.arrow_sides[0], 0, 0, (c.key[0], c.key[1])).h // 2 + options.wiring_grid
            for c in cut_ends(refs, plan, fans, r)
            if c.key[0] is not None and c.key[1] == str(RefKind.ARROW)
        ),
        0,
    )
