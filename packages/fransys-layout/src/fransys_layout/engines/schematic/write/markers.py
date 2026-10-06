"""Private to `write/`: the `LinkMarker` builder (design/engine.md 7, model layout-namespace.md)."""

from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.write.keys import PREFIX
from fransys_layout.engines.schematic.write.power import without_power
from fransys_layout.geometry import LayoutError
from fransys_layout.stages import MarkerSide
from fransys_model.kernel import make_id
from fransys_model.layout import LinkMarker, Side, StarKind
from fransys_model.layout import MarkerSide as ModelMarkerSide

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.engines.schematic.engine import StageResults
    from fransys_layout.engines.schematic.write.keys import PageId, WriteKeys
    from fransys_layout.stages import LinkMarker as StageMarker
    from fransys_layout.stages.offstubs import OffEnd
    from fransys_layout.stages.types import StubText
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.layout import Page


def link_markers(
    keys: WriteKeys,
    results: StageResults,
    page_of: Mapping[PageId, Page],
    discriminator: Mapping[tuple[Id[Any], int, int], AuthoringKey],
    stamp: str,
) -> list[LinkMarker]:
    """Each severed signal's two markers, each pointing at the other by record id."""
    layout = without_power(results.layout)  # a power end is a `PowerSymbol`, not a marker
    port_key = keys.port
    # an off stub finds its end by `(port, end_text)`; any other marker's `end_text` is `None`
    end_of: dict[tuple[Id[Any], StubText | None], OffEnd] = {
        (end.port, end.text): end for end in results.off_ends
    }
    by_port = {end.port: end for end in results.off_ends}  # D9: the merged reference's stub
    handle_ports = {one.function: [p.port for p in one.ports] for one in results.drawn}
    stands_on = {  # each drawn port's placement, by set and page: its discriminator
        (port, placed.drawing_set, placed.page): discriminator[
            placed.function, placed.drawing_set, placed.page
        ]
        for placed in layout.placed
        for port in handle_ports.get(placed.function, ())
    }

    def key_to(one: StageMarker, partner_port: Id[Any]) -> AuthoringKey:
        """D17: the port key, the side, the partner's port key; never a page or an ordinal."""
        return (
            *PREFIX,
            "link_marker",
            *port_key[one.port],
            one.side.value,
            *port_key[partner_port],
        )

    reached = Counter((end.port, end.far) for end in end_of.values())

    def off_key(one: StageMarker, end: OffEnd) -> AuthoringKey:
        """An off stub's key: its far port's, plus its carrier's when two carriers reach it."""
        key = key_to(one, end.far)
        if reached[end.port, end.far] > 1 and end.carrier is not None:
            return (*key, "carrier", *keys.item[end.carrier])
        return key

    def star_key_of(one: StageMarker) -> AuthoringKey:
        """D17: the port key, `star`, the placement's discriminator; no role, partner or page."""
        where = stands_on[one.port, one.drawing_set, one.page]
        return (*PREFIX, "link_marker", *port_key[one.port], "star", *where)

    def key_of(one: StageMarker, other: StageMarker) -> AuthoringKey:
        return key_to(one, other.port)

    def record(one: StageMarker, other: StageMarker) -> LinkMarker:
        box_x, lead, stub_extra, via_x, via_y = _marker_fields(one)
        return LinkMarker(
            id=make_id(LinkMarker, key_of(one, other)),
            key=key_of(one, other),
            page=page_of[one.drawing_set, one.page].id,
            port=one.port,
            side=ModelMarkerSide[one.side.name],
            partner=make_id(LinkMarker, key_of(other, one)),
            x=one.at.x,
            y=one.at.y,
            width=one.box.width,
            height=one.box.height,
            produced_by=stamp,
            box_x=box_x,
            lead=lead,
            stub_extra=stub_extra,
            via_x=via_x,
            via_y=via_y,
            vertical=one.vertical,
        )

    def tag_of(one: StageMarker) -> str:
        return "off" if one.star == "off" else "star"  # C21: an off stub is its own partner

    # a star marker is found by its port, its page, its tag and (an off stub) its end's text:
    # its key, which `partner` (the id of the marker on the partner's page) is made from
    star_key: dict[tuple[Id[Any] | None, int, int, str, StubText | None], AuthoringKey] = {
        (one.port, one.drawing_set, one.page, tag_of(one), one.end_text): (
            off_key(one, end_of[one.port, one.end_text]) if one.star == "off" else star_key_of(one)
        )
        for one in layout.markers
        if one.star
    }

    def star_marker(one: StageMarker) -> LinkMarker:
        box_x, lead, stub_extra, via_x, via_y = _marker_fields(one)
        # D9 (F7): a reference carrying the off stub's text on the same port is that off stub
        if one.star == "off":
            off = end_of[one.port, one.end_text]
        else:
            off = by_port[one.port] if one.star and one.text else None
        key = star_key[one.port, one.drawing_set, one.page, tag_of(one), one.end_text]
        partner = star_key[
            one.star_partner, one.star_partner_set, one.partner_page, tag_of(one), one.end_text
        ]
        return LinkMarker(
            id=make_id(LinkMarker, key),
            key=key,
            page=page_of[one.drawing_set, one.page].id,
            port=one.port,
            side=ModelMarkerSide[one.side.name],
            partner=make_id(LinkMarker, partner),
            x=one.at.x,
            y=one.at.y,
            width=one.box.width,
            height=one.box.height,
            produced_by=stamp,
            box_x=box_x,
            lead=lead,
            stub_extra=stub_extra,
            via_x=via_x,
            via_y=via_y,
            star=StarKind.OFF if off else StarKind[one.star.upper()],
            far=off.far if off else None,
            carrier=off.carrier if off else None,
            facing=_facing(one) if off else None,
            vertical=one.vertical,
            wrap_at=one.wrap_at,
        )

    stars = [star_marker(one) for one in layout.markers if one.star]  # R7 B4: one per marker
    return [
        *(
            record(one, other)
            for owner, user in _pairs(tuple(m for m in layout.markers if not m.star))
            for one, other in ((owner, user), (user, owner))
        ),
        *stars,
    ]


def _marker_fields(one: StageMarker) -> tuple[int | None, bool, int, int | None, int | None]:
    """R6 D2: `(box_x, lead, stub_extra, via_x, via_y)` of a marker, for render."""
    via = (one.turn.x, one.turn.y) if one.turn is not None else (None, None)
    box_x = one.box.x if one.shared_box or one.turn is not None else None
    lead = one.lead if one.shared_box else True
    return box_x, lead, one.stub_extra, *via


def _facing(one: StageMarker) -> Side:
    """The side a stub faces: its box above its port is N, below S, else beside it E or W."""
    box, at = one.box, one.at
    if one.turn is not None:
        return Side.N if one.turn.y < at.y else Side.S
    if box.y + box.height <= at.y:
        return Side.N
    if box.y >= at.y:
        return Side.S
    return Side.E if box.x >= at.x else Side.W


def _pairs(markers: tuple[StageMarker, ...]) -> list[tuple[StageMarker, StageMarker]]:
    """Pair each owner marker with its user marker, per connection, in page order."""
    owners: dict[Id[Any], list[StageMarker]] = defaultdict(list)
    users: dict[Id[Any], list[StageMarker]] = defaultdict(list)
    for marker in markers:
        (owners if marker.side is MarkerSide.OWNER else users)[marker.connection].append(marker)
    found = []
    for connection in sorted({*owners, *users}):
        by_page = (
            sorted(owners[connection], key=lambda m: (m.drawing_set, m.page)),
            sorted(users[connection], key=lambda m: (m.drawing_set, m.page)),
        )
        if len(by_page[0]) != len(by_page[1]):
            msg = "a connection has owner and user markers that do not pair up"
            raise LayoutError(msg)
        for owner, user in zip(*by_page, strict=True):
            if (owner.drawing_set, owner.page) >= (user.drawing_set, user.page):
                msg = "the owner marker of a cut is not on an earlier page than its user marker"
                raise LayoutError(msg)
            found.append((owner, user))
    return found
