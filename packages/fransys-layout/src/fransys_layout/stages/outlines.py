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
from .types import Home, LabelKind, PlacedLabel, PlacedOutline

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .connector_boxes import PlacedConnectorBox
    from .types import (
        Cell,
        Column,
        FunctionSpec,
        Handle,
        LinkMarker,
        PagePlan,
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
    boxes: tuple[PlacedConnectorBox, ...] = ()  # HL6: a member pin's connector box is inside
    # HL11, condition 3: a middle unit's page draws its middle outline and no D11 frame
    middle: frozenset[tuple[Handle, int, int]] = frozenset()


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


@dataclass(frozen=True)
class _Run:
    """The run-wide reads every page's outlines share."""

    spec_of: Mapping[Handle, FunctionSpec]
    faces: Mapping[tuple[Handle, AuthoringKey], bool]
    cells: Mapping[AuthoringKey, tuple[Cell, ...]]
    markers: Mapping[tuple[int, int], tuple[LinkMarker, ...]]
    inputs: OutlineInputs
    boxes: Mapping[tuple[int, int, Handle | None], Box]


def _end_faces(inputs: OutlineInputs) -> dict[tuple[Handle, AuthoringKey], bool]:
    """A face replica stands above its plug (flip False) at a column's top end.

    The one place the end is read again, from the cell `discover_chains` made.
    """
    return {
        (c.function, col.key): not c.flip
        for col in inputs.columns
        for c in col.cells
        if c.face and c.home is Home.ELSEWHERE
    }


def _unit_members(
    placed: tuple[PlacedFunction, ...], run: _Run, own_unit: Handle | None
) -> dict[Handle, list[PlacedFunction]]:
    """The page's placements grouped by the unit whose black box they belong to."""
    by_unit: dict[Handle, list[PlacedFunction]] = {}
    for one in placed:
        unit = run.spec_of[one.function].unit
        middle = bool(run.inputs.middle) and (unit, one.drawing_set, one.page) in run.inputs.middle
        if unit is not None and unit != own_unit and not middle:
            by_unit.setdefault(unit, []).append(one)
    return by_unit


def _run_groups(
    placed: tuple[PlacedFunction, ...], run: _Run, own_unit: Handle | None
) -> dict[tuple[Handle, int], tuple[list[PlacedFunction], bool]]:
    """Each unit's runs, bottom-end first then top-end, keyed by (unit, run index)."""
    groups: dict[tuple[Handle, int], tuple[list[PlacedFunction], bool]] = {}
    for unit, members in _unit_members(placed, run, own_unit).items():
        top_set, bottom_set = _by_end(members, run.faces, run.cells, placed)
        runs = [(r, False) for r in _column_runs(bottom_set, placed)]
        runs += [(r, True) for r in _column_runs(top_set, placed)]
        groups.update({(unit, index): r for index, r in enumerate(runs)})
    return groups


def _run_frame(
    members: Sequence[PlacedFunction],
    first: tuple[PlacedLabel, ...],
    page_markers: Sequence[LinkMarker],
    run: _Run,
    *,
    top_end: bool,
) -> tuple[Box, bool]:
    """One run's frame, holding its members' labels and link markers (M10)."""
    names = {m.function for m in members}
    names |= {p.port for m in members for p in run.spec_of[m.function].ports}
    texts = [label.box for label in first if label.subject in names]
    # M10: a member port's link marker, stub included, stands inside the frame
    texts += [_marker_reach(marker) for marker in page_markers if marker.port in names]
    if run.boxes:  # HL6: a member pin's connector box stands inside too
        owners = {(m.drawing_set, m.page, run.spec_of[m.function].pin_function) for m in members}
        texts += [run.boxes[owner] for owner in owners if owner in run.boxes]
    return _frame(members, run.faces, texts, top_end=top_end)


def _title_box(box: Box, text: str, taken: Sequence[Box], *, drawn_top: bool, height: int) -> Box:
    """Where a unit's title goes: above or below its frame, whichever is free (D4, layout-0104)."""
    margin = WIRING_GRID // 2
    width = text_width(text, height=height)
    # layout-0104: a title left of the content box's text gap moves right to it
    at_x = max(box.x, TEXT_GAP)
    above = Box(x=at_x, y=box.y - margin - height, width=width, height=height)
    below = Box(x=at_x, y=box.y + box.height + margin, width=width, height=height)
    if drawn_top:
        # the mirror: below-left when free, else above-left (D4's top room holds it)
        free = not any(overlaps(below, other) for other in taken)
        return below if free else above
    free = above.y >= 0 and not any(overlaps(above, other) for other in taken)
    return above if free else below


def _page_taken(
    placed: tuple[PlacedFunction, ...],
    first: tuple[PlacedLabel, ...],
    page_markers: Sequence[LinkMarker],
) -> list[Box]:
    """The boxes a title must not overlap: keep-outs, port exits, labels and marker reaches."""
    taken = [placed_keepout(one) for one in placed]
    taken += _exit_cells(placed)
    taken += [label.box for label in first]
    taken += [_marker_reach(marker) for marker in page_markers]
    return taken


def _page_outlines(
    plan: PagePlan,
    placed: tuple[PlacedFunction, ...],
    first: tuple[PlacedLabel, ...],
    run: _Run,
) -> tuple[list[PlacedLabel], list[PlacedOutline]]:
    """One page's outline titles and outlines, one pair per run of a unit's black box."""
    page_markers = run.markers.get((plan.drawing_set, plan.number), ())
    groups = _run_groups(placed, run, plan.unit)
    taken = _page_taken(placed, first, page_markers)
    titles: list[PlacedLabel] = []
    outlines: list[PlacedOutline] = []
    height = run.inputs.profile.text_height
    for (unit, _), (members, top_end) in sorted(
        groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))
    ):
        box, drawn_top = _run_frame(members, first, page_markers, run, top_end=top_end)
        lead = min(members, key=lambda m: (m.at.x, m.at.y)).function
        title = _title_box(box, run.inputs.title(unit), taken, drawn_top=drawn_top, height=height)
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
    return titles, outlines


def unit_outlines(
    plans: tuple[Any, ...],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    markers: tuple[LinkMarker, ...],
    inputs: OutlineInputs,
) -> tuple[list[Any], tuple[PlacedOutline, ...]]:
    """I2a, U1: per page, one dash-dot outline and title per run of a unit's black box (D8, D11)."""
    run = _Run(
        spec_of={spec.function: spec for spec in inputs.functions},
        faces=_end_faces(inputs),
        cells={col.key: col.cells for col in inputs.columns},
        markers=by_key(markers, page_of),
        inputs=inputs,
        boxes={(one.drawing_set, one.page, one.function): one.box for one in inputs.boxes},
    )
    found, outlines = [], []
    for plan, (placed, first) in zip(plans, pages, strict=True):
        titles, page_outlines = _page_outlines(plan, placed, first, run)
        found.append((placed, (*first, *titles)))
        outlines.extend(page_outlines)
    return found, tuple(outlines)
