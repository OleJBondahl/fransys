"""D5, step 6: where a power end's symbol stands and where its text goes (R7, A5).

A power end (`LinkMarker.symbol`) is placed as a reference marker is: the same row, box and
stub. The symbol's port point lies one wiring grid out from the pin along the pin's facing, the
reference stub's length (R7), and the symbol is turned so its own port faces back at the pin, so
render's straight lead from that port to the pin never bends (A5). Its text, where it has some,
is one `POWER` text through `place_texts` with the port as its subject.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import (
    OPPOSITE,
    Box,
    Facing,
    Orientation,
    Point,
    pad,
    port_exit,
    port_page_at,
    symbol_geometry,
    text_width,
    translate,
)
from fransys_layout.stages.lookups import placed_keepout
from fransys_layout.stages.sizing import with_rooms
from fransys_layout.stages.space import Shape, Space
from fransys_layout.stages.types import LabelKind, PlacedLabel

from .candidates import DEFAULT_TABLE, TextKind
from .marker_row import corridor, stub_boxes
from .place_texts import Anchor, TextToPlace, place_texts
from .stand import leave_port, symbol_port

if TYPE_CHECKING:
    from fransys_layout.geometry import SymbolGeometry
    from fransys_layout.stages.labels import SlotFrame
    from fransys_layout.stages.references.types import MarkerDecision
    from fransys_layout.stages.types import (
        DrawnFunction,
        LinkMarker,
        PlacedFunction,
        Profile,
    )
    from fransys_model.kernel import Finding, Id

    from .stand import PageTexts

_TURNS = (Orientation.R0, Orientation.R90, Orientation.R180, Orientation.R270)
type _Boxes = dict[Id[Any], list[tuple[str, Box]]]
_ROOM_SLOT = "power_room"  # the slot name of a room box, not of a label (`POWER_SLOT`)


@dataclass(frozen=True, slots=True)
class PowerPlace:
    """One power symbol on one page: `at` its origin, `pin` its lead's start, `lead` its lead."""

    port: Id[Any]
    drawing_set: int
    page: int
    symbol: str
    text: str
    pin: Point
    facing: Facing
    at: Point
    orientation: Orientation
    body: Box
    lead: Box


def _pin_facing(marker: LinkMarker) -> Facing:
    """The way the marker's pin faces: its box above the pin is N, below S, beside it E or W."""
    at, box = marker.at, marker.box
    if marker.turn is not None:
        return Facing.N if marker.turn.y < at.y else Facing.S
    if box.y + box.height <= at.y:
        return Facing.N
    if box.y >= at.y:
        return Facing.S
    return Facing.E if box.x >= at.x else Facing.W


def turned(symbol: str, pin: Facing) -> SymbolGeometry:
    """A5: `symbol`, quarter-turned so its one port faces back at a pin that faces `pin`."""
    wanted = OPPOSITE[pin]
    return next(
        one
        for one in (symbol_geometry(symbol, orientation=turn) for turn in _TURNS)
        if one.ports[0].facing is wanted
    )


def power_place(marker: LinkMarker) -> PowerPlace:
    """R7: the symbol of `marker`, its port point `symbol_grids` wiring grids from the pin."""
    return place_of(marker, pin=marker.at, facing=_pin_facing(marker), grids=marker.symbol_grids)


def place_of(
    end: LinkMarker | MarkerDecision, *, pin: Point, facing: Facing, grids: int
) -> PowerPlace:
    """The symbol of power `end` at `pin`, `grids` wiring grids out along `facing` (R7)."""
    geometry = turned(end.symbol, facing)
    port = geometry.ports[0]
    stem = port_exit(pin, facing, grids)
    at = Point(x=stem.x - port.at.x, y=stem.y - port.at.y)
    return PowerPlace(
        port=end.port,
        drawing_set=end.drawing_set,
        page=end.page,
        symbol=end.symbol,
        text=end.symbol_text,
        pin=pin,
        facing=facing,
        at=at,
        orientation=geometry.orientation,
        body=translate(geometry.body, dx=at.x, dy=at.y),
        lead=corridor(pin, stem),
    )


def power_places(markers: tuple[LinkMarker, ...]) -> tuple[PowerPlace, ...]:
    """One symbol per port and page from the power ends of `markers`; the first end's wins."""
    found: dict[tuple[Id[Any], int, int], PowerPlace] = {}
    for one in markers:
        if one.symbol and (one.port, one.drawing_set, one.page) not in found:
            found[one.port, one.drawing_set, one.page] = power_place(one)
    return tuple(found.values())


def drawn_shapes(markers: tuple[LinkMarker, ...]) -> tuple[Shape, ...]:
    """What the page draws for `markers`: each ordinary end's box and stubs, each power symbol."""
    return (
        *(
            Shape(owner=m.port, box=box)
            for m in markers
            if not m.symbol
            for box in (m.box, *stub_boxes(m))
        ),
        *(
            Shape(owner=None, box=box)
            for one in power_places(markers)
            for box in (one.body, one.lead)
        ),
    )


def power_reserved(markers: tuple[LinkMarker, ...]) -> tuple[Box, ...]:
    """What a power end holds before its lead is set (D5): its marker box and stub, not its symbol.

    The lead is set from the first labels, so the symbol's place is not known to them (layout-0142).
    """
    return tuple(box for m in markers if m.symbol for box in (m.box, *stub_boxes(m)))


def without_power_findings(
    findings: tuple[Finding, ...], markers: tuple[LinkMarker, ...]
) -> tuple[Finding, ...]:
    """`findings` less those of a port whose every marker is a power end (it draws no box)."""
    drawn_ports = {one.port for one in markers if not one.symbol}
    ends = {one.port for one in markers if one.symbol}
    return tuple(one for one in findings if one.subjects[0] not in ends - drawn_ports)


def with_power_labels(
    labels: tuple[PlacedLabel, ...],
    placed: tuple[PlacedFunction, ...],
    markers: tuple[LinkMarker, ...],
    frame: SlotFrame,
    slot: str,
) -> tuple[tuple[PlacedLabel, ...], tuple[Finding, ...]]:
    """D3: `labels` plus a `MARKING` label in `slot` per symbol with a text, in `frame.content`."""
    places = power_places(markers)
    owners = {port_page_at(one.at, g): one.function for one in placed for g in one.geometry.ports}
    texts = tuple(
        _text(one, owners.get(one.pin), frame.profile, slot) for one in places if one.text
    )
    if not texts:
        return labels, ()
    shapes = (
        *(Shape(owner=one.function, box=placed_keepout(one)) for one in placed),
        *drawn_shapes(markers),
        *(Shape(owner=None, box=one.box) for one in labels),
    )
    done, findings = place_texts(texts, Space(shapes=shapes, content=frame.content), DEFAULT_TABLE)
    by_port = {one.port: one for one in places}
    made = tuple(
        PlacedLabel(
            kind=LabelKind.MARKING,
            subject=one.handle,
            slot=one.slot,
            drawing_set=by_port[one.handle].drawing_set,
            page=by_port[one.handle].page,
            box=one.box,
            unplaced=one.unplaced,
        )
        for one in done
    )
    return (*labels, *made), findings


def _text(one: PowerPlace, owner: Id[Any] | None, profile: Profile, slot: str) -> TextToPlace:
    """`one`'s text as D3 places it: past its bar, away from the pin, centred on the lead."""
    return TextToPlace(
        kind=TextKind.POWER,
        handle=one.port,
        slot=slot,
        position=one.at,
        width=text_width(one.text, height=profile.text_height),
        height=profile.text_height,
        anchors=(Anchor(box=pad(one.body, profile.marker_padding), facing=one.facing),),
        own=(one.port,) if owner is None else (one.port, owner),
    )


def with_power_rooms(
    boxes: _Boxes, texts: PageTexts | None, drawn: tuple[DrawnFunction, ...], profile: Profile
) -> _Boxes:
    """TEXT-ROOM: `boxes` plus, per supply text, its first candidate clear of its own function."""
    if texts is None:
        return boxes
    drawn_of = {one.function: one for one in drawn}
    found: _Boxes = {}
    for function, decisions in texts.owned.items():
        places = own_places(decisions, drawn_of[function], texts, drawn_of[function].geometry)
        shapes = _own_shapes(drawn_of[function].geometry, places)
        room = [_room(one, shapes, drawn_of[function], profile) for one in places if one.text]
        if room:
            found[function] = room
    return with_rooms(boxes, found)


def own_places(
    decisions: tuple[MarkerDecision, ...],
    drawn: DrawnFunction,
    texts: PageTexts,
    geometry: SymbolGeometry,
) -> tuple[PowerPlace, ...]:
    """The power symbols of one function, one per port, at their first lead, in `geometry`'s frame.

    `geometry` is the symbol the function is drawn or placed with, turned or not (layout-0117).
    """
    found = {}
    for end in (one for one in decisions if one.symbol):
        own = symbol_port(drawn, end.port, geometry)
        port = leave_port(end.leave, own, geometry.ports, drawn, texts.wired)
        found.setdefault(end.port, place_of(end, pin=port.at, facing=port.facing, grids=1))
    return tuple(found.values())


def _own_shapes(geometry: SymbolGeometry, places: tuple[PowerPlace, ...]) -> tuple[Shape, ...]:
    """What a supply text of the function must clear: body, tag slot, the stems, the symbols."""
    pins = {one.pin for one in places}
    stems = (corridor(g.at, port_exit(g.at, g.facing)) for g in geometry.ports if g.at not in pins)
    boxes = [geometry.body, *(s.box for s in geometry.slots if s.slot == "tag"), *stems]
    boxes += [box for one in places for box in (one.body, one.lead)]
    return tuple(Shape(owner=None, box=box) for box in boxes)


def _room(
    one: PowerPlace, shapes: tuple[Shape, ...], drawn: DrawnFunction, profile: Profile
) -> tuple[str, Box]:
    """The first free candidate of `one`'s text, by `_text` and the placer; width only, padded."""
    (done,), _ = place_texts(
        (_text(one, None, profile, _ROOM_SLOT),), Space(shapes=shapes), DEFAULT_TABLE
    )
    pad = profile.marker_padding
    return _ROOM_SLOT, Box(
        x=done.box.x - pad, y=drawn.geometry.keepout.y, width=done.box.width + 2 * pad, height=0
    )
