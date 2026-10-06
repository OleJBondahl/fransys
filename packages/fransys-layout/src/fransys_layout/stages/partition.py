"""Stage 3, partition: drawing sets and pages, packed by width and never by count (pages.md 6.3).

The two halves of the work are private modules of their own: `_ordering` decides the
drawing set, the role and the order of a column (steps 1 and 2), `_packing` fills the pages
(step 4). This module checks the inputs, drives those two and turns what they report into
`PagePlan`s and `Finding`s.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
lazy from collections.abc import Set as AbstractSet

from fransys_layout.geometry import WIRING_GRID, HintError, LayoutError
from fransys_model.kernel import AuthoringKey, Finding, Severity

from ._ordering import Tables, base_order, buckets, column_order, membership, reorder
from ._packing import merge, pack, placements
from .place import _without_tag
from .slices import by_key
from .types import (
    ColumnWidth,
    GroupInfo,
    LocationInfo,
    PagePlan,
    PlannedColumn,
    PlannedGroup,
    UnitInfo,
)

if TYPE_CHECKING:
    from collections.abc import Hashable, Iterator, Mapping, Sequence

    from ._ordering import Bucket
    from ._packing import Placement, Unit
    from .types import Column, DrawnFunction, Handle, PageHints, Profile, SheetFormat

GROUP_SPLIT = "GROUP_SPLIT"
KEEP_TOGETHER_UNMET = "KEEP_TOGETHER_UNMET"
ORDER_HINT_UNMET = "ORDER_HINT_UNMET"


def column_widths(
    columns: tuple[Column, ...], drawn: tuple[DrawnFunction, ...], *, profile: Profile
) -> tuple[ColumnWidth, ...]:
    """Estimate each column as its widest keep-out box plus one gap, deliberately generous (WP6)."""
    drawn_by = {one.function: one for one in drawn}
    keepouts = {function.function: function.geometry.keepout.width for function in drawn}
    widths: dict[AuthoringKey, int] = {}
    for column in columns:
        if column.key in widths:
            msg = "two columns carry one authoring key, and keys are unique within an engine run"
            raise LayoutError(msg)
        if not column.cells:
            msg = "a column has no cells, so it has no width"
            raise LayoutError(msg)
        # L1 (deep dive): a row `place` packs tag-less (R5.2: lanes of one item, or of
        # terminals and pins) is estimated tag-less too, or an 8-pin row counts 8 tags
        by_row = by_key(
            (c for c in column.cells if not c.side and c.function in drawn_by),
            lambda c: c.index,
        )
        tagless = {
            index
            for index, cells in by_row.items()
            if (lanes := [drawn_by[c.function] for c in cells])
            and len(lanes) > 1
            and (len({one.item for one in lanes}) == 1 or all(one.roles.narrow for one in lanes))
        }
        rows: dict[int, int] = {}
        for cell in column.cells:
            keepout = keepouts.get(cell.function)
            if keepout is None:
                msg = "a column cell names a function that is not drawn"
                raise LayoutError(msg)
            if cell.index in tagless and not cell.side:
                keepout = _without_tag(drawn_by[cell.function].geometry).keepout.width
            # R4 rows: a row's cells sit side by side, a wiring-grid step apart (an estimate)
            gap = WIRING_GRID if cell.index in rows else 0
            rows[cell.index] = rows.get(cell.index, 0) + gap + keepout
        widths[column.key] = max(rows.values()) + profile.column_gap
    return tuple(ColumnWidth(column=key, width=widths[key]) for key in sorted(widths))


@dataclass(frozen=True, slots=True)
class ColumnTables:
    """What a column resolves through in `partition`: width, group, location, unit, pole links."""

    widths: tuple[ColumnWidth, ...]
    groups: tuple[GroupInfo, ...]
    locations: tuple[LocationInfo, ...]
    units: tuple[UnitInfo, ...]
    pole_links: tuple[tuple[AuthoringKey, AuthoringKey], ...] = ()


def partition(
    columns: tuple[Column, ...],
    given: ColumnTables,
    *,
    hints: PageHints,
    profile: Profile,
    sheet: SheetFormat,
) -> tuple[tuple[PagePlan, ...], tuple[Finding, ...]]:
    """Plan drawing sets and pages (WP6, pages.md 6.3 step 3; layout-0049, layout-0081, D4)."""
    tables = Tables(
        info_of={info.group: info for info in given.groups},
        label_of={info.location: info.label for info in given.locations},
        width_of={width.column: width.width for width in given.widths},
        unit_ids=frozenset(info.unit for info in given.units),
        unit_location={info.unit: info.location for info in given.units},
    )
    ordered = tuple(sorted(columns, key=column_order))
    _check_inputs(ordered, given, tables)
    _check_hints(hints, ordered)
    found = buckets(ordered, tables)
    findings = list(_order_hint_findings(hints, membership(found)))
    pages: list[PagePlan] = []
    met: set[int] = set()
    number = 0
    drawing_set = 0
    for bucket in found:
        number = 1 if bucket.drawing_set != drawing_set else number
        drawing_set = bucket.drawing_set
        ranked = base_order(
            bucket,
            tables,
            group_ranks=profile.group_ranks,
            break_before=hints.break_before,
            pole_links=given.pole_links,
        )
        packed, bucket_met = merge(
            reorder(ranked, hints.order), hints.keep_together, sheet.content_width
        )
        met |= bucket_met
        runs, split = placements(packed, tables.width_of, sheet.content_width, given.pole_links)
        for page in pack(runs, sheet.content_width):
            pages.append(_page(bucket, number, page, tables))
            number += 1
        findings.extend(_split_findings(split))
    findings.extend(_keep_together_findings(hints, met))
    findings.sort(key=lambda finding: (finding.code, finding.subjects))
    return tuple(pages), tuple(findings)


def _check_inputs(columns: tuple[Column, ...], given: ColumnTables, tables: Tables) -> None:
    """Raise unless each table names its subject once and every column is in all four."""
    _refuse_duplicates("ColumnWidth", [width.column for width in given.widths])
    _refuse_duplicates("GroupInfo", [info.group for info in given.groups])
    _refuse_duplicates("LocationInfo", [info.location for info in given.locations])
    _refuse_duplicates("UnitInfo", [info.unit for info in given.units])
    for info in given.units:
        if info.location is not None and info.location not in tables.label_of:
            msg = "a unit's location has no LocationInfo"
            raise LayoutError(msg)
    for column in columns:
        if column.key not in tables.width_of:
            msg = "a column has no ColumnWidth"
            raise LayoutError(msg)
        if column.group is not None and column.group not in tables.info_of:
            msg = "a column's group has no GroupInfo"
            raise LayoutError(msg)
        if column.location is not None and column.location not in tables.label_of:
            msg = "a column's location has no LocationInfo"
            raise LayoutError(msg)
        if column.unit is not None and column.unit not in tables.unit_ids:
            msg = "a column's unit has no UnitInfo"
            raise LayoutError(msg)


def _refuse_duplicates(table: str, subjects: Sequence[Hashable]) -> None:
    """Raise when two rows of one table name one subject: the table would lose one of them."""
    if len(set(subjects)) != len(subjects):
        msg = f"two {table} rows name one subject"
        raise LayoutError(msg)


def _check_hints(hints: PageHints, columns: tuple[Column, ...]) -> None:
    """`LayoutError` on an empty keep-together set, `HintError` on a hint with no column (5.4)."""
    if any(not together.groups for together in hints.keep_together):
        msg = "a keep-together set names no group"
        raise LayoutError(msg)
    placed = {column.group for column in columns}
    named = {
        *(hint.before for hint in hints.order),
        *(hint.after for hint in hints.order),
        *(group for together in hints.keep_together for group in together.groups),
        *hints.break_before,
    }
    missing = sorted(named - placed)
    if missing:
        msg = "a page hint names a group with no column"
        raise HintError(msg, subjects=tuple(missing))


def _order_hint_findings(hints: PageHints, sets_of: Mapping[Handle, set[int]]) -> Iterator[Finding]:
    """One finding per order hint whose two groups share no drawing set (`_check_hints` has run)."""
    for hint in hints.order:
        if sets_of[hint.before] & sets_of[hint.after]:
            continue
        yield Finding(
            code=ORDER_HINT_UNMET,
            severity=Severity.WARNING,
            subjects=(hint.before, hint.after),
            message="order hint between groups that no page order can honour: "
            "they are on different drawing sets",
        )


def _keep_together_findings(hints: PageHints, met: AbstractSet[int]) -> Iterator[Finding]:
    """One finding per keep-together set that no bucket could merge."""
    for index, together in enumerate(hints.keep_together):
        if index in met:
            continue
        yield Finding(
            code=KEEP_TOGETHER_UNMET,
            severity=Severity.WARNING,
            subjects=together.groups,
            message="keep-together groups cannot share a page: packed separately",
        )


def _split_findings(split: Sequence[Unit]) -> Iterator[Finding]:
    """One finding per unit the packing had to cut between its columns."""
    for unit in split:
        yield Finding(
            code=GROUP_SPLIT,
            severity=Severity.WARNING,
            subjects=tuple(group for group in unit.groups if group is not None),
            message="group is wider than a page: split between its columns",
        )


def _page(bucket: Bucket, number: int, page: Sequence[Placement], tables: Tables) -> PagePlan:
    """One planned page: groups and columns left to right, the role of its first unit, its title."""
    groups = []
    columns = []
    listed: set[Handle] = set()
    for placement in page:
        for group in placement.unit.groups:
            if group is not None:
                if group in listed:
                    continue
                listed.add(group)
            groups.append(PlannedGroup(group=group, index=len(groups)))
        for key in placement.columns:
            columns.append(PlannedColumn(column=key, index=len(columns)))
    described = [
        tables.info_of[planned.group].description for planned in groups if planned.group is not None
    ]
    return PagePlan(
        drawing_set=bucket.drawing_set,
        location=bucket.location,
        unit=bucket.unit,
        number=number,
        role=page[0].unit.role,
        title=", ".join(described),
        groups=tuple(groups),
        columns=tuple(columns),
    )
