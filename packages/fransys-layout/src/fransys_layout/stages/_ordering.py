"""Where a column goes before it is packed: its drawing set, its role and its place in the order.

Private to `stages.partition` (pages.md 6.3 steps 1 and 2). Everything here takes plain values
and returns plain values; `partition` builds the tables and reports the findings.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_layout.geometry import HintError, follow

from ._packing import Unit
from .types import ROLE_ORDER, Role

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import Column, GroupInfo, Handle, OrderHint


@dataclass(frozen=True, slots=True)
class Tables:
    """The rows `partition` was given, each keyed by the subject it describes exactly once."""

    info_of: dict[Handle, GroupInfo]
    label_of: dict[Handle, str]
    width_of: dict[AuthoringKey, int]
    unit_ids: frozenset[Handle]
    unit_location: dict[Handle, Handle | None]


@dataclass(frozen=True, slots=True)
class Bucket:
    """The columns of one drawing set, of every role: the run a page is packed inside."""

    drawing_set: int
    unit: Handle | None
    location: Handle | None
    columns: tuple[Column, ...]


def column_order(column: Column) -> tuple[AuthoringKey, tuple[Handle, ...]]:
    """Sort key of a column: its authoring key, then its cells, so two keys still order."""
    return (column.key, tuple(cell.function for cell in column.cells))


def buckets(columns: tuple[Column, ...], tables: Tables) -> tuple[Bucket, ...]:
    """Every (unit, drawing set) bucket in output order: top level, then units (layout-0081)."""
    by_unit: dict[Handle | None, dict[Handle | None, list[Column]]] = {}
    for column in columns:
        unit, location = column.drawing_set_key
        by_unit.setdefault(unit, {}).setdefault(location, []).append(column)
    unit_order: list[Handle | None] = [
        *([None] if None in by_unit else []),
        *sorted(unit for unit in by_unit if unit is not None),
    ]
    found = []
    drawing_set = 0
    for unit in unit_order:
        by_location = by_unit[unit]
        located = sorted(
            (location for location in by_location if location is not None),
            key=lambda location: (tables.label_of[location], location),
        )
        location_order: list[Handle | None] = [
            *located,
            *([None] if None in by_location else []),
        ]
        for location in location_order:
            drawing_set += 1
            where = location if unit is None else tables.unit_location[unit]
            found.append(Bucket(drawing_set, unit, where, tuple(by_location[location])))
    return tuple(found)


def membership(found: tuple[Bucket, ...]) -> dict[Handle, set[int]]:
    """The drawing sets each group has columns in; a hint between two groups needs a shared one."""
    sets_of: dict[Handle, set[int]] = {}
    for bucket in found:
        for column in bucket.columns:
            if column.group is not None:
                sets_of.setdefault(column.group, set()).add(bucket.drawing_set)
    return sets_of


def _link_order(
    members: Sequence[Column], pole_links: tuple[tuple[AuthoringKey, AuthoringKey], ...]
) -> list[Column]:
    """`members` in key order, each pole-linked column right after its earliest placed partner."""
    keys = {column.key for column in members}
    partners: dict[AuthoringKey, set[AuthoringKey]] = {}
    for x, y in pole_links:
        if x in keys and y in keys:
            partners.setdefault(x, set()).add(y)
            partners.setdefault(y, set()).add(x)
    placed: list[Column] = []
    anchor: dict[AuthoringKey, AuthoringKey] = {}
    for column in members:
        at = {one.key: index for index, one in enumerate(placed)}
        earlier = [at[key] for key in partners.get(column.key, ()) if key in at]
        if not earlier:
            placed.append(column)
            continue
        first = placed[min(earlier)].key
        end = at[first] + 1
        while end < len(placed) and _hangs_from(placed[end].key, first, anchor):
            end += 1
        placed.insert(end, column)
        anchor[column.key] = first
    return placed


def _hangs_from(
    key: AuthoringKey, root: AuthoringKey, anchor: Mapping[AuthoringKey, AuthoringKey]
) -> bool:
    """Whether `key` is attached to `root`, directly or through the columns it hangs from."""
    return root in follow(key, anchor.get)[1:]


def base_order(
    bucket: Bucket,
    tables: Tables,
    *,
    group_ranks: frozendict[str, int],
    break_before: tuple[Handle, ...],
    pole_links: tuple[tuple[AuthoringKey, AuthoringKey], ...] = (),
) -> list[Unit]:
    """The units of a bucket: role first, then its groups, then loose columns (D4)."""
    by_group: dict[tuple[Role, Handle], list[Column]] = {}
    found: list[
        tuple[tuple[int | AuthoringKey, ...], tuple[Handle | None, ...], list[Column], Role]
    ] = []
    for column in bucket.columns:
        if column.group is None:
            found.append(((ROLE_ORDER.index(column.role), 1), (None,), [column], column.role))
        else:
            by_group.setdefault((column.role, column.group), []).append(column)
    for (role, group), members in by_group.items():
        key = (ROLE_ORDER.index(role), 0, *_group_key(tables.info_of[group], group_ranks))
        found.append((key, (group,), _link_order(members, pole_links), role))
    found.sort(key=lambda row: row[0])
    units = []
    broken: set[Handle | None] = set()
    for _, groups, members, role in found:
        keys = tuple(column.key for column in members)
        units.append(
            Unit(
                groups=groups,
                columns=keys,
                width=sum(tables.width_of[key] for key in keys),
                break_before=groups[0] in break_before and groups[0] not in broken,
                role=role,
            )
        )
        broken.add(groups[0])
    return units


def _group_key(info: GroupInfo, group_ranks: frozendict[str, int]) -> tuple[int, int, AuthoringKey]:
    """The rank of the group's label in the profile, unranked last, then its authoring key."""
    rank = group_ranks.get(info.label)
    return (1, 0, info.key) if rank is None else (0, rank, info.key)


def reorder(units: Sequence[Unit], order_hints: tuple[OrderHint, ...]) -> list[Unit]:
    """Move groups an order hint names, a stable pass (D4); a cycle raises `HintError`."""
    positions: dict[Handle, list[int]] = {}
    for index, unit in enumerate(units):
        if unit.groups[0] is not None:
            positions.setdefault(unit.groups[0], []).append(index)
    blockers: dict[int, set[int]] = {index: set() for index in range(len(units))}
    applied = False
    for hint in order_hints:
        if hint.before in positions and hint.after in positions:
            for later in positions[hint.after]:
                blockers[later].update(positions[hint.before])
            applied = True
    if not applied:
        return list(units)
    order: list[int] = []
    placed: set[int] = set()
    while len(order) < len(units):
        waiting = [index for index in range(len(units)) if index not in placed]
        free = next((index for index in waiting if blockers[index] <= placed), None)
        if free is None:
            stuck = (units[index].groups[0] for index in waiting)
            msg = "order hints form a cycle"
            subjects = tuple(sorted(group for group in stuck if group is not None))
            raise HintError(msg, subjects=subjects)
        placed.add(free)
        order.append(free)
    return [units[index] for index in order]
