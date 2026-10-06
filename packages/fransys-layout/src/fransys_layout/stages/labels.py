"""Stage 5, labels: tags, markings, values, cross-references (labels.md 6.7).

Labels are obstacles for routes placed after them, so an engine calls `place_slot_labels`
(stage 5, D3's placer, S18) before `links` and `route`. Overlap rules ignore the keep-out box
of the label's own symbol, which contains its slots by definition.
"""

from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    LayoutError,
    port_page_at,
)
from fransys_model.kernel import value

from . import lookups
from ._labelling import _reflected, home
from .lookups import placed_keepout
from .space import End, Run, Shape, Space, lane
from .texts.candidates import DEFAULT_TABLE, TextKind
from .texts.place_texts import Anchor, TextToPlace, place_texts
from .types import LabelKind, PlacedLabel, Profile

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

    from ._labelling import Home
    from .stacking import JoinedRun
    from .types import Connection, DrawnFunction, Handle, LabelRequest, PlacedFunction

# S18: the slot labels' kinds in D3's table
_TEXT_KIND = frozendict(
    {
        LabelKind.TAG: TextKind.TAG,
        LabelKind.MARKING: TextKind.MARKING,
        LabelKind.CROSS_REFERENCE: TextKind.CROSS_REFERENCE,
    }
)


@value
class SlotFrame:
    """What bounds a slot label (S18): text sizes and content box (None at first)."""

    content: Box | None
    profile: Profile


def place_slot_labels(
    requests: tuple[LabelRequest, ...],
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    *,
    occupied: tuple[Box, ...] = (),
    frame: SlotFrame,
) -> tuple[tuple[PlacedLabel, ...], tuple[Finding, ...]]:
    """S18: every slot label of one page, placed by D3's placer before routing (D3)."""
    placed_of = _placed_of(placed)
    owner_of = _owner_of(placed_of, drawn)
    space = Space(
        shapes=(
            *(Shape(owner=one.function, box=placed_keepout(one)) for one in placed_of.values()),
            *(Shape(owner=None, box=box) for box in occupied),
        ),
        content=frame.content,
    )
    lanes = tuple(
        Shape(owner=one.function, box=Box(x=r.x, y=r.y, width=r.to_x - r.x, height=r.to_y - r.y))
        for one in placed_of.values()
        for r in _lanes(one)
    )
    texts, asked = [], {}
    for request in requests:
        placement = _placement(request, placed_of, owner_of)
        where = home(request, placement, frame.profile)
        kind = _TEXT_KIND[request.kind]
        texts.append(
            TextToPlace(
                kind=kind,
                handle=request.subject,
                slot=request.slot,
                position=placement.at,
                width=where.box.width,
                height=where.box.height,
                anchors=(_slot_anchor(where, kind),),
                own=(where.owner,),
            )
        )
        asked[kind, request.subject, request.slot] = (request, where)
    found, findings = place_texts(tuple(texts), space, DEFAULT_TABLE, lanes=lanes)
    labels = []
    for one in found:
        request, where = asked[one.kind, one.handle, one.slot]
        labels.append(
            PlacedLabel(
                kind=request.kind,
                subject=request.subject,
                slot=request.slot,
                drawing_set=where.drawing_set,
                page=where.page,
                box=one.box,
                partners=request.partners,
                unplaced=one.unplaced,
            )
        )
    labels.sort(key=lambda one: (one.subject, one.slot, one.kind.value))
    return tuple(labels), tuple(sorted(findings, key=lambda one: one.subjects))


def _slot_anchor(where: Home, kind: TextKind) -> Anchor:
    """The span between a slot label's home box and its mirror, where D3's W and E sides stand."""
    if not where.vertical:
        msg = "a slot label on an N or S side has no span for the table's W and E rows"
        raise LayoutError(msg)
    box, mirror = where.box, _reflected(where)
    west = box.x <= mirror.x
    inner = box.x + box.width if west else box.x
    outer = mirror.x if west else mirror.x + mirror.width
    gap = max(outer - inner if west else inner - outer, 0)
    lift = where.step if kind is TextKind.CROSS_REFERENCE else 0
    span = Box(x=inner if west else inner - gap, y=box.y - lift, width=gap, height=box.height)
    return Anchor(box=span, facing=Facing.W if west else Facing.E)


def _lanes(one: PlacedFunction) -> tuple[Run, ...]:
    """The outward wire lane (`space.lane`) of each port; a foreign slot label never enters it."""
    keepout = placed_keepout(one)
    return tuple(
        lane(
            End(at=port_page_at(one.at, port), facing=port.facing),
            keepout,
        ).run
        for port in one.geometry.ports
    )


def _port_points(
    placed: tuple[PlacedFunction, ...], drawn: tuple[DrawnFunction, ...]
) -> dict[Handle, tuple[int, int]]:
    """Each placed port's page point `(x, y)`, as `place` placed it."""
    symbol = {port.port: port.symbol_port for one in drawn for port in one.ports}
    at = {}
    for one in placed:
        geometry = {g.name: g for g in one.geometry.ports}
        for port in next(d for d in drawn if d.function == one.function).ports:
            g = geometry.get(symbol[port.port])
            if g is not None:
                here = port_page_at(one.at, g)
                at[port.port] = (here.x, here.y)
    return at


def decided_runs(
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    connections: tuple[Connection, ...],
    joins: tuple[JoinedRun, ...],
) -> tuple[Box, ...]:
    """S20: the wires known before `place`, as boxes no text stands on (C23 corridors, joins)."""
    at = _port_points(placed, drawn)
    half = WIRING_GRID // 2
    found = list(_corridors(placed, drawn, connections))
    for run in joins:
        for one, other in zip(run.ends, run.ends[1:], strict=False):
            a, b = at.get(one.port), at.get(other.port)
            if a is None or b is None or a[1] != b[1] or abs(a[0] - b[0]) <= 2 * half:
                continue
            left, right = sorted((a[0], b[0]))
            found.append(Box(x=left + half, y=a[1] - 1, width=right - left - 2 * half, height=2))
    return tuple(found)


def _corridors(
    placed: tuple[PlacedFunction, ...],
    drawn: tuple[DrawnFunction, ...],
    connections: tuple[Connection, ...],
) -> tuple[Box, ...]:
    """C23: a box on each vertical connection's straight wire between its ports, kept label-free."""
    at = _port_points(placed, drawn)
    found = []
    half = WIRING_GRID // 2
    for c in connections:
        a, b = at.get(c.a.port), at.get(c.b.port)
        if a is None or b is None or a[0] != b[0] or abs(a[1] - b[1]) <= 2 * half:
            continue
        top, bottom = sorted((a[1], b[1]))
        found.append(Box(x=a[0] - 1, y=top + half, width=2, height=bottom - top - 2 * half))
    return tuple(found)


def _placed_of(placed: tuple[PlacedFunction, ...]) -> dict[Handle, PlacedFunction]:
    """The page's functions by handle; a second page or a second placement is a fault."""
    if len({(one.drawing_set, one.page) for one in placed}) > 1:
        msg = "place_slot_labels was given placed functions from more than one page"
        raise LayoutError(msg)
    return lookups.placed_of(placed, "place_slot_labels")


def _owner_of(
    placed_of: Mapping[Handle, PlacedFunction], drawn: tuple[DrawnFunction, ...]
) -> dict[Handle, Handle]:
    """Each placed function's model ports, so a `MARKING` subject finds its function."""
    drawn_of = {one.function: one for one in drawn}
    owner = {}
    for function in placed_of:
        one = drawn_of.get(function)
        if one is None:
            msg = "a placed function is not among the drawn functions"
            raise LayoutError(msg)
        for port in one.ports:
            owner[port.port] = function
    return owner


def _placement(
    request: LabelRequest,
    placed_of: Mapping[Handle, PlacedFunction],
    owner_of: Mapping[Handle, Handle],
) -> PlacedFunction:
    """The placed function a request belongs to: its subject, or its port's function."""
    if request.subject in placed_of:
        return placed_of[request.subject]
    function = owner_of.get(request.subject)
    if function is None:
        msg = "a label request's subject is neither a placed function nor a port of one"
        raise LayoutError(msg)
    return placed_of[function]
