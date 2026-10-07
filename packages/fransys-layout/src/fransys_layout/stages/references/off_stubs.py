"""C21: the off stubs of the conductors that cross between two locations.

A stub stands at the home seat of each crossing end and reads "<cable> <arrow> <far end>".
Stubs of one cable to one far end on one row share a box (a run, S14); an end on a port that
already carries a star reference merges into that reference (D9, F7). This module decides
them; `texts.markers` builds their markers from the placed page (S9).
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from itertools import count, pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import Facing
from fransys_layout.stages.types import Home
from fransys_model.derive.drawing_text import off_stub_line

from .cuts import link_world
from .ends import EndRead, marker_end
from .marker_boxes import reads_along, stub_size
from .markers import terminal_lift
from .types import LinkWorld, MarkerDecision, MarkerScene, OffStubs, PortEnd

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence

    from fransys_layout.stages.stacking import StackedPort
    from fransys_layout.stages.types import Connection, FunctionSpec, Profile, StubText
    from fransys_model.kernel import AuthoringKey, Id

    from .types import BlackBoxReads, OffInputs, Page, Seated, Seating


def _texts_by_port(pairs: Iterable[tuple[Id[Any], StubText]]) -> dict[Id[Any], list[StubText]]:
    """`(port, text)` pairs as each port's texts, in the order given: `_off_markers`' input."""
    found: dict[Id[Any], list[StubText]] = defaultdict(list)
    for port, text in pairs:
        found[port].append(text)
    return found


def black_box_sets(
    functions: Iterable[FunctionSpec],
    seats: tuple[Seated, ...],
    unit_of: Mapping[Any, Any],
    set_unit: Mapping[int, Any],
    reads: BlackBoxReads,
) -> dict[Id[Any], frozenset[int]]:
    """D10: per function of a nested unit, the drawing sets where it stands as a black box."""
    nested, edges = reads.nested, reads.edges
    top_of = {
        spec.function: reads.top(spec.unit)
        for spec in functions
        if spec.unit in nested and (spec.pin_function in edges or spec.function in edges)
    }
    found: dict[Id[Any], set[int]] = {}
    for one in seats:
        own = top_of.get(one.function)
        if (
            unit_of[one.function] in nested
            and unit_of[one.function] != set_unit[one.drawing_set]
            and own in (None, set_unit[one.drawing_set])
        ):
            found.setdefault(one.function, set()).add(one.drawing_set)
    return {function: frozenset(sets) for function, sets in found.items()}


def with_off_markers(
    markers: tuple[MarkerDecision, ...],
    seating: Seating,
    inputs: OffInputs,
) -> tuple[MarkerDecision, ...]:
    """`markers` and the off stubs of the conductors that cross to another location (S14)."""
    columns, drawn = seating.columns, seating.drawn
    offs = _off_markers(
        MarkerScene(seating.seats, drawn, inputs.sheet, inputs.profile),
        OffStubs(
            inputs.crossing,
            off_texts=_texts_by_port((one.port, one.text) for one in inputs.off_texts),
            # the stub sits at the home seat: a cell not drawn away from its home
            away=frozenset(
                (c.function, col.key)
                for col in columns
                for c in col.cells
                if c.home is Home.ELSEWHERE
            ),
            busy=Counter((m.port, m.drawing_set, m.page) for m in markers),
            refs={(m.port, m.drawing_set, m.page): m for m in markers if m.star == "ref"},
            outward=inputs.outward,
            stands=_port_stands(seating),
            order={
                (plan.drawing_set, plan.number): tuple(one.column for one in plan.columns)
                for plan in seating.plans
            },
        ),
    )
    # D9 (F7): an off stub on a reference's port comes back as that reference, one text
    merged = {(m.port, m.drawing_set, m.page): m for m in offs if m.star == "ref"}
    return (
        *(
            merged.get((m.port, m.drawing_set, m.page), m) if m.star == "ref" else m
            for m in markers
        ),
        *(m for m in offs if m.star != "ref"),
    )


def _port_stands(seating: Seating) -> dict[tuple[Id[Any], Page], StackedPort]:
    """Each seated port's `StackedPort` on its page, as `place` stacks the page (S14)."""
    ports = {one.function: one.ports for one in seating.drawn}
    found = {}
    for one in seating.seats:
        page = (one.drawing_set, one.page)
        stack = seating.stacks[page]
        for port in ports[one.function]:
            stand = stack.ports.get((one.column, port.port))
            if stand is not None:
                found[port.port, page] = stand
    return found


@dataclass(frozen=True, slots=True)
class _Tiers:
    """What each run's box needs besides its ends: the profile, the terminals, the shared tiers."""

    profile: Profile
    terminals: set[Id[Any]]
    step: int
    busy: Counter[tuple[Id[Any], Any, int]]
    runs: Iterator[int]


def _off_markers(scene: MarkerScene, off: OffStubs) -> tuple[MarkerDecision, ...]:
    """C21, S14, D9, D10: a stub at each end of a conductor between two locations."""
    world = link_world(scene)
    tiers = _Tiers(
        scene.profile,
        {one.function for one in scene.drawn if one.roles.terminal},
        terminal_lift(scene.profile),
        Counter(off.busy),
        count(),
    )
    stubs = _stub_ends(off.crossing, world, off.off_texts, off.away, off.outward)
    found, rows, pins = _group_stubs(off, world, stubs)
    found.extend(_row_markers(rows, pins, off, tiers))
    return tuple(found)


def _group_stubs(
    off: OffStubs,
    world: LinkWorld,
    stubs: Sequence[tuple[Connection, PortEnd, StubText]],
) -> tuple[list[MarkerDecision], dict[Any, list[Any]], dict[Any, list[Any]]]:
    """Merged reference markers, and the other stubs by row (`rows`) and by pin (`pins`)."""
    rows: dict[Any, list[Any]] = defaultdict(list)
    pins: dict[Any, list[Any]] = defaultdict(list)
    merged: list[MarkerDecision] = []
    ends_on = Counter((end.ref.port, *end.page) for _, end, _ in stubs)
    for c, end, end_text in stubs:
        key = (end.ref.port, *end.page)
        # layout-0053: one record names one far end, so only a lone end merges into the reference
        own = off.refs.get(key) if ends_on[key] == 1 else None
        if own is not None:
            merged.append(replace(own, merge=end_text))
            continue
        stand = off.stands[end.ref.port, end.page]
        column = off.order[end.page].index(world.where[end.ref.function][end.page])
        rows[end.page, stand.offset, stand.facing, end_text.cable, end_text.far].append(
            ((column, stand.x), c.handle, end, end_text.port, end_text)
        )
        pins[end.page, stand.offset, stand.facing].append(
            ((column, stand.x), (end_text.cable, end_text.far))
        )
    return merged, rows, pins


def _row_markers(
    rows: Mapping[Any, Sequence[Any]],
    pins: Mapping[Any, Sequence[Any]],
    off: OffStubs,
    tiers: _Tiers,
) -> list[MarkerDecision]:
    """Each row's ends cut into runs, and each run's stubs decided (R1, M8)."""
    found: list[MarkerDecision] = []
    for (page, offset, facing, cable, far), row_ends in rows.items():
        # R1: a row cut where another column stands between two ends: each run its own box,
        # so a box never names a column far from the rest (X1:N standing in F01's column)
        # M8: and where a pin of another destination stands between two ends: only neighbouring
        # pins of one destination share a box, so alternating destinations get one box per pin
        strangers = [at for at, goes in pins[page, offset, facing] if goes != (cable, far)]
        in_order = sorted(row_ends, key=lambda one: one[0])
        for ends in _runs(in_order, _cuts(in_order, len(off.order[page]), strangers)):
            found.extend(_run_markers(ends, (cable, far, facing), tiers))
    return found


def _run_markers(
    ends: Sequence[Any], head: tuple[str, str, Facing], tiers: _Tiers
) -> list[MarkerDecision]:
    """One run's stubs: the text, the box they share and the tier it stands out at (C21, S14)."""
    cable, far, facing = head
    ports = [port for _, _, _, port, text in ends if not text.line]
    text = off_stub_line(cable, north=facing is Facing.N, far=far, ports=ports)
    size = stub_size(text, tiers.profile)
    lift = tiers.step if ends[0][2].ref.function in tiers.terminals else 0
    keys = {(end.ref.port, *end.page) for _, _, end, _, _ in ends}
    # C21: the n-th thing on a port (its texts, then its stubs) stands n boxes out
    run = next(tiers.runs) if len(ends) > 1 else None  # C21: one box across the run's stubs (S14)
    # a turned box (M1) is its text's width tall along the wire: that is the tier step
    step_out = size[0] if reads_along(run, facing) else size[1]
    out = lift + max(tiers.busy[key] for key in keys) * step_out
    tiers.busy.update(keys)
    return [
        _off_stub(handle, end, text, end_text, StubBox(size, out, run))
        for _, handle, end, _, end_text in ends
    ]


def _stub_ends(
    crossing: tuple[Connection, ...],
    world: LinkWorld,
    off_texts: Mapping[Id[Any], Sequence[StubText]],
    away: frozenset[AuthoringKey | tuple[Id[Any], AuthoringKey]],
    outward: Mapping[Id[Any], frozenset[int]],
) -> list[tuple[Connection, PortEnd, StubText]]:
    """Each stub `_off_markers` decides, as `(conductor, end at its home seat, end text)`."""
    queues = {port: iter(texts) for port, texts in off_texts.items()}
    seen: set[tuple[Id[Any], StubText]] = set()
    stubs: list[tuple[Connection, PortEnd, StubText]] = []
    for c in crossing:
        for ref in (c.a, c.b):
            end_text = next(queues[ref.port], None) if ref.port in queues else None
            black_box = outward.get(ref.function)
            pages = sorted(
                page
                for page, column in world.where.get(ref.function, {}).items()
                if (
                    page[0] in black_box
                    if black_box is not None
                    else (ref.function, column) not in away
                )
            )
            if not pages or end_text is None or (ref.port, end_text) in seen:
                continue
            seen.add((ref.port, end_text))
            stubs.append((c, PortEnd(ref=ref, page=pages[0]), end_text))
    return stubs


@dataclass(frozen=True, slots=True)
class StubBox:
    """The box a run's stubs share (S14): its measured size, its tier out, its run number."""

    size: tuple[int, int]
    out: int
    run: int | None


def _off_stub(
    handle: Id[Any], end: PortEnd, text: str, end_text: StubText, box: StubBox
) -> MarkerDecision:
    """A pure off stub's own text, end and size: `stub_size`, never `reference_size` (D4)."""
    return MarkerDecision(
        connection=handle,
        function=end.ref.function,
        port=end.ref.port,
        side=marker_end(EndRead("off_stub"))[0],
        drawing_set=end.page[0],
        page=end.page[1],
        star="off",
        size=box.size,
        partner=end.ref.port,
        partner_set=end.page[0],
        partner_page=end.page[1],
        out=box.out,
        text=text,
        end_text=end_text,
        run=box.run,
    )


def _cuts(
    ends: Sequence[tuple[tuple[int, int], Id[Any], PortEnd, str, StubText]],
    columns: int,
    strangers: Sequence[tuple[int, int]],
) -> list[tuple[int, ...]]:
    """R1, M8: cut points: `(column,)` for a column without an end, `(column, x)` for a stranger."""
    own = {end[0][0] for end in ends}
    return sorted([(index,) for index in range(columns) if index not in own] + list(strangers))


def _runs(
    ends: Sequence[tuple[tuple[int, int], Id[Any], PortEnd, str, StubText]],
    cuts: Sequence[tuple[int, ...]],
) -> list[list[tuple[tuple[int, int], Id[Any], PortEnd, str, StubText]]]:
    """R1, S14, M8: `ends` (one page, in column order) cut into runs wherever a cut lies between."""
    runs = [[ends[0]]]
    for before, end in pairwise(ends):
        if any(before[0] < at < end[0] for at in cuts):
            runs.append([])
        runs[-1].append(end)
    return runs
