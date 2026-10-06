"""Unit outlines: the dash-dot frame around each unit's black box, and its title."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    hull,
    overlaps,
    port_exit,
    port_page_at,
    text_width,
    translate,
    union,
)

from .lookups import placed_keepout
from .slices import by_key, page_of
from .tidy import TEXT_GAP
from .types import LabelKind, PlacedLabel, PlacedOutline

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .types import (
        Cell,
        Column,
        FunctionSpec,
        Handle,
        LinkMarker,
        PlacedFunction,
        Profile,
    )


@dataclass(frozen=True)
class OutlineInputs:
    """What `unit_outlines` reads of the run; `title` is a unit's title text (`outline_title`)."""

    functions: tuple[FunctionSpec, ...]
    columns: tuple[Column, ...]
    profile: Profile
    title: Callable[[Handle], str]


def _column_ends(
    members: Sequence[PlacedFunction],
    faces: Mapping[tuple[Handle, AuthoringKey], bool],
    cells: Mapping[AuthoringKey, tuple[Cell, ...]],
) -> dict[AuthoringKey, Any]:
    """Each column's set of ends: its faces' ends, else the pin's, None when free (D11)."""
    ends: dict[AuthoringKey, Any] = {}  # each value a set[bool] or None; ty cannot narrow it
    for one in members:
        end = faces.get((one.function, one.column))
        if end is not None:
            ends.setdefault(one.column, set()).add(end)
    for column in {one.column for one in members} - ends.keys():
        names = {one.function for one in members if one.column == column}
        mine = [cell.index for cell in cells.get(column, ()) if cell.function in names]
        theirs = [cell.index for cell in cells.get(column, ()) if cell.function not in names]
        ends[column] = {all(m < t for m in mine for t in theirs)} if theirs else None
    return ends


def _joined_ends(
    stretch: Sequence[AuthoringKey], ends: Mapping[AuthoringKey, Any], at: int
) -> set[bool]:
    """The ends of the nearest column with an end on each side of `stretch[at]`, united."""
    joined: set[bool] = set()
    for side in (stretch[:at][::-1], stretch[at + 1 :]):
        joined |= next((ends[column] for column in side if ends[column] is not None), set())
    return joined


def _by_end(
    members: Sequence[Any],
    faces: Mapping[tuple[Any, Any], bool],
    cells: Mapping[AuthoringKey, tuple[Cell, ...]],
    placed: tuple[PlacedFunction, ...],
) -> tuple[list[PlacedFunction], list[PlacedFunction]]:
    """One unit's black-box placements split into the top-end and bottom-end sets (D8, D11)."""
    ends = _column_ends(members, faces, cells)
    resolved = {column: end for column, end in ends.items() if end is not None}
    for stretch in _column_stretches(members, placed):
        for at, column in enumerate(stretch):
            if ends[column] is None:
                joined = _joined_ends(stretch, ends, at)
                resolved[column] = joined if len(joined) == 1 else {False}
    top: list[PlacedFunction] = []
    bottom: list[PlacedFunction] = []
    for one in members:
        own = faces.get((one.function, one.column))
        for at_top in {own} if own is not None else resolved[one.column]:
            (top if at_top else bottom).append(one)
    return top, bottom


def _column_stretches(
    members: Sequence[PlacedFunction], placed: tuple[PlacedFunction, ...]
) -> list[list[AuthoringKey]]:
    """The columns of `members` by x, cut where a column of none of them stands between two."""
    own = {one.column for one in members}
    x_of: dict[AuthoringKey, int] = {}
    for one in members:
        x_of[one.column] = min(x_of.get(one.column, one.at.x), one.at.x)
    others = [one.at.x for one in placed if one.column not in own]
    stretches: list[list[AuthoringKey]] = []
    last = None
    for column in sorted(own, key=lambda key: (x_of[key], str(key))):
        if last is None or any(x_of[last] < x < x_of[column] for x in others):
            stretches.append([])
        stretches[-1].append(column)
        last = column
    return stretches


def _column_runs(
    members: Sequence[PlacedFunction], placed: tuple[PlacedFunction, ...]
) -> list[list[PlacedFunction]]:
    """One end's placements of a unit, cut into runs so a frame never spans unrelated columns."""
    return [
        [one for column in stretch for one in members if one.column == column]
        for stretch in _column_stretches(members, placed)
    ]


def _marker_reach(marker: LinkMarker) -> Box:
    """A marker's box with its stub: the box joined to the port's anchor point."""
    return union(Box(x=marker.at.x, y=marker.at.y, width=0, height=0), marker.box)


def _frame(
    members: Sequence[PlacedFunction],
    faces: Mapping[tuple[Handle, AuthoringKey], bool],
    texts: Sequence[Box],
    *,
    top_end: bool,
) -> tuple[Box, bool]:
    """One run's outline rectangle and whether it is a top-end box; a plug stays out (D11, M10)."""
    margin = WIRING_GRID // 2
    bodies = [translate(m.geometry.body, dx=m.at.x, dy=m.at.y) for m in members]
    mating = [b for m, b in zip(members, bodies, strict=True) if (m.function, m.column) in faces]
    boxes = [*bodies, *texts]
    # R3: never left of the content box, so neither the frame nor its title leaves it
    whole = hull(boxes)
    left = max(whole.x - margin, 0)
    right = whole.x + whole.width + margin
    top_end = top_end and bool(mating)
    if top_end:
        # the replicas stand above their plugs, their bodies' bottoms on the mating line
        top = whole.y - margin
        bottom = (line := hull(mating)).y + line.height
    else:
        top = hull(mating).y if mating else whole.y - margin
        bottom = whole.y + whole.height + margin
    return Box(x=left, y=top, width=right - left, height=bottom - top), top_end


def _exit_cells(placed: Sequence[PlacedFunction]) -> list[Box]:
    """Each port's first step (layout-0088) as a 2-wide box; the router counts a border as in."""
    steps = (
        port_exit(port_page_at(one.at, port), port.facing)
        for one in placed
        for port in one.geometry.ports
    )
    return [Box(x=at.x - 1, y=at.y - 1, width=2, height=2) for at in steps]


def unit_outlines(
    plans: tuple[Any, ...],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    markers: tuple[LinkMarker, ...],
    inputs: OutlineInputs,
) -> tuple[list[Any], tuple[PlacedOutline, ...]]:
    """I2a, U1: per page, one dash-dot outline and title per run of a unit's black box (D8, D11)."""
    spec_of = {spec.function: spec for spec in inputs.functions}
    # a face replica stands above its plug (flip False) at a column's top end: the one place the
    # end is read again, from the cell `discover_chains` made
    faces = {
        (c.function, col.key): not c.flip
        for col in inputs.columns
        for c in col.cells
        if c.face and c.replica
    }
    cells = {col.key: col.cells for col in inputs.columns}
    margin = WIRING_GRID // 2
    here_markers = by_key(markers, page_of)
    found, outlines = [], []
    for plan, (placed, first) in zip(plans, pages, strict=True):
        by_unit: dict[Handle, list[PlacedFunction]] = {}
        for one in placed:
            unit = spec_of[one.function].unit
            if unit is not None and unit != plan.unit:
                by_unit.setdefault(unit, []).append(one)
        groups: dict[tuple[Handle, int], tuple[list[PlacedFunction], bool]] = {}
        for unit, members in by_unit.items():
            top_set, bottom_set = _by_end(members, faces, cells, placed)
            runs = [(run, False) for run in _column_runs(bottom_set, placed)]
            runs += [(run, True) for run in _column_runs(top_set, placed)]
            groups.update({(unit, index): run for index, run in enumerate(runs)})
        taken = [placed_keepout(one) for one in placed]
        taken += _exit_cells(placed)
        taken += [label.box for label in first]
        page_markers = here_markers.get((plan.drawing_set, plan.number), [])
        taken += [_marker_reach(marker) for marker in page_markers]
        titles = []
        for (unit, _), (members, top_end) in sorted(
            groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))
        ):
            names = {m.function for m in members}
            names |= {p.port for m in members for p in spec_of[m.function].ports}
            texts = [label.box for label in first if label.subject in names]
            # M10: a member port's link marker, stub included, stands inside the frame
            texts += [_marker_reach(marker) for marker in page_markers if marker.port in names]
            box, drawn_top = _frame(members, faces, texts, top_end=top_end)
            left, top, bottom = box.x, box.y, box.y + box.height
            lead = min(members, key=lambda m: (m.at.x, m.at.y)).function
            text = inputs.title(unit)
            width, height = (
                text_width(text, height=inputs.profile.text_height),
                inputs.profile.text_height,
            )
            # layout-0104: a title left of the content box's text gap moves right to it
            at_x = max(left, TEXT_GAP)
            above = Box(x=at_x, y=top - margin - height, width=width, height=height)
            below = Box(x=at_x, y=bottom + margin, width=width, height=height)
            if drawn_top:
                # the mirror: below-left when free, else above-left (D4's top room holds it)
                free = not any(overlaps(below, other) for other in taken)
                title = below if free else above
            else:
                free = above.y >= 0 and not any(overlaps(above, other) for other in taken)
                title = above if free else below
            taken.append(title)
            titles.append(
                PlacedLabel(
                    kind=LabelKind.TAG,
                    subject=lead,
                    slot="outline_title",
                    drawing_set=plan.drawing_set,
                    page=plan.number,
                    box=title,
                )
            )
            outlines.append(
                PlacedOutline(
                    unit=unit, lead=lead, drawing_set=plan.drawing_set, page=plan.number, box=box
                )
            )
        found.append((placed, (*first, *titles)))
    return found, tuple(outlines)
