"""How `partition` fills its pages: the packing unit, the runs that fit one page, and the fill.

Private to `stages.partition`. Everything here takes plain values and
returns plain values; the findings and the page plans are built by `partition`.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .lane_runs import fill_runs

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from fransys_model.kernel import AuthoringKey

    from .types import GroupSet, Handle, OrderHint, Role


@dataclass(frozen=True, slots=True)
class Unit:
    """One packing unit: a group, a merged `keep_together` set, or a loose column (`(None,)`)."""

    groups: tuple[Handle | None, ...]
    columns: tuple[AuthoringKey, ...]
    width: int
    break_before: bool
    role: Role


@dataclass(frozen=True, slots=True)
class Placement:
    """The columns of one unit that go on one page, and whether they start a new one."""

    unit: Unit
    columns: tuple[AuthoringKey, ...]
    width: int
    starts_page: bool


def merge(
    units: Sequence[Unit], keep_together: tuple[GroupSet, ...], content_width: int
) -> tuple[list[Unit], set[int]]:
    """Merge each keep-together set that fits one page at its first member's place."""
    met: set[int] = set()
    current: list[Unit] = list(units)
    for index, together in enumerate(keep_together):
        members = [unit for unit in current if set(unit.groups) & set(together.groups)]
        held = {group for unit in members for group in unit.groups}
        if not set(together.groups) <= held:
            continue
        merged = Unit(
            groups=tuple(group for unit in members for group in unit.groups),
            columns=tuple(key for unit in members for key in unit.columns),
            width=sum(unit.width for unit in members),
            break_before=members[0].break_before,
            role=members[0].role,
        )
        if merged.width > content_width:
            continue
        if any(unit.break_before for unit in members[1:]):
            continue
        current = [
            merged if unit is members[0] else unit
            for unit in current
            if not any(unit is later for later in members[1:])
        ]
        met.add(index)
    return current, met


def undone_orders(
    before: Sequence[Unit],
    after: Sequence[Unit],
    order: tuple[OrderHint, ...],
    keep_together: tuple[GroupSet, ...],
    met: AbstractSet[int],
) -> list[tuple[OrderHint, GroupSet]]:
    """Each order hint that held before `merge` and a merged set then reversed, with that set."""
    was, now = _positions(before), _positions(after)
    merged = [keep_together[index] for index in sorted(met)]
    undone = []
    for hint in order:
        ends = {hint.before, hint.after}
        if not ends <= was.keys() & now.keys():
            continue
        if was[hint.before] < was[hint.after] and now[hint.before] > now[hint.after]:
            causes = [together for together in merged if ends & set(together.groups)]
            undone.extend((hint, together) for together in causes[:1])
    return undone


def _positions(units: Sequence[Unit]) -> dict[Handle, int]:
    """The place of each group's first mention, counting groups in unit order."""
    at: dict[Handle, int] = {}
    for group in (group for unit in units for group in unit.groups):
        if group is not None:
            at.setdefault(group, len(at))
    return at


def placements(
    units: Sequence[Unit],
    width_of: Mapping[AuthoringKey, int],
    content_width: int,
    pole_links: tuple[tuple[AuthoringKey, AuthoringKey], ...] = (),
) -> tuple[list[Placement], list[Unit]]:
    """Cut each unit into the column runs that fit a page, and name the units that were cut."""
    runs = []
    split = []
    for unit in units:
        chunks = _chunks(unit, width_of, content_width, pole_links)
        for index, chunk in enumerate(chunks):
            runs.append(
                Placement(
                    unit=unit,
                    columns=chunk,
                    # layout-0153: a whole unit group is as wide as it folds, not its columns' sum
                    width=unit.width if len(chunks) == 1 else sum(width_of[k] for k in chunk),
                    starts_page=index > 0 or unit.break_before or unit.width > content_width,
                )
            )
        if len(chunks) > 1:
            split.append(unit)
    return runs, split


def _chunks(
    unit: Unit,
    width_of: Mapping[AuthoringKey, int],
    content_width: int,
    pole_links: tuple[tuple[AuthoringKey, AuthoringKey], ...],
) -> tuple[tuple[AuthoringKey, ...], ...]:
    """The unit whole, or its columns page by page, ending at a boundary no pole link spans."""
    if unit.width <= content_width:
        return (unit.columns,)
    columns = unit.columns
    at = {key: index for index, key in enumerate(columns)}
    links = [(at[x], at[y]) for x, y in pole_links if x in at and y in at]
    runs = fill_runs([width_of[key] for key in columns], links, content_width)
    return tuple(columns[start:end] for start, end in runs)


def pack(runs: Sequence[Placement], content_width: int) -> list[list[Placement]]:
    """Fill pages in order: a run joins the page it fits on, else it starts the next one."""
    pages: list[list[Placement]] = []
    page: list[Placement] = []
    used = 0
    for run in runs:
        if page and (run.starts_page or used + run.width > content_width):
            pages.append(page)
            page = []
            used = 0
        page.append(run)
        used += run.width
    if page:
        pages.append(page)
    return pages
