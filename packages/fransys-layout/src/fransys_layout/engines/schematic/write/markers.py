"""Private to `write/`: the `LinkMarker` builder (design/engine.md 7, model layout-namespace.md)."""

from collections import Counter, defaultdict
from dataclasses import dataclass
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
    from fransys_layout.stages import Layout
    from fransys_layout.stages import LinkMarker as StageMarker
    from fransys_layout.stages.offstubs import OffEnd
    from fransys_layout.stages.types import StubText
    from fransys_model.kernel import AuthoringKey, Id
    from fransys_model.layout import Page


@dataclass(frozen=True)
class _Ctx:
    """What the marker records are made from, shared by the helpers below."""

    keys: WriteKeys
    page_of: Mapping[PageId, Page]
    stamp: str
    stands_on: Mapping[tuple[Id[Any], int, int], AuthoringKey]  # each drawn port's placement
    doubled: frozenset[AuthoringKey]
    end_of: Mapping[tuple[Id[Any], StubText | None], OffEnd]  # an off stub, by `(port, end_text)`
    by_port: Mapping[Id[Any], OffEnd]  # D9: the merged reference's stub
    reached: Mapping[tuple[Id[Any], Id[Any]], int]


def link_markers(
    keys: WriteKeys,
    results: StageResults,
    page_of: Mapping[PageId, Page],
    discriminator: Mapping[tuple[Id[Any], int, int], AuthoringKey],
    stamp: str,
) -> list[LinkMarker]:
    """Each severed signal's two markers, each pointing at the other by record id."""
    layout = without_power(results.layout)  # a power end is a `PowerSymbol`, not a marker
    pairs, doubled = _pairs_and_doubled(layout.markers, keys)
    end_of: dict[tuple[Id[Any], StubText | None], OffEnd] = {
        (end.port, end.text): end for end in results.off_ends
    }
    ctx = _Ctx(
        keys,
        page_of,
        stamp,
        _stands_on(results, layout, discriminator),
        doubled,
        end_of,
        {end.port: end for end in results.off_ends},
        Counter((end.port, end.far) for end in end_of.values()),
    )
    star_key = _star_keys(ctx, layout.markers)
    stars = [_star_marker(ctx, star_key, one) for one in layout.markers if one.star]  # R7 B4
    both = ((one, other) for owner, user in pairs for one, other in ((owner, user), (user, owner)))
    return [*(_record(ctx, one, other) for one, other in both), *stars]


def _stands_on(
    results: StageResults,
    layout: Layout,
    discriminator: Mapping[tuple[Id[Any], int, int], AuthoringKey],
) -> dict[tuple[Id[Any], int, int], AuthoringKey]:
    """Each drawn port's placement, by set and page: its discriminator."""
    handle_ports = {one.function: [p.port for p in one.ports] for one in results.drawn}
    return {
        (port, placed.drawing_set, placed.page): discriminator[
            placed.function, placed.drawing_set, placed.page
        ]
        for placed in layout.placed
        for port in handle_ports.get(placed.function, ())
    }


def _key_to(keys: WriteKeys, one: StageMarker, partner_port: Id[Any]) -> AuthoringKey:
    """D17: the port key, the side, the partner's port key; never a page or an ordinal."""
    return (
        *PREFIX,
        "link_marker",
        *keys.port[one.port],
        one.side.value,
        *keys.port[partner_port],
    )


def _off_key(c: _Ctx, one: StageMarker, end: OffEnd) -> AuthoringKey:
    """An off stub's key: its far port's, plus its carrier's when two carriers reach it."""
    key = _key_to(c.keys, one, end.far)
    if c.reached[end.port, end.far] > 1 and end.carrier is not None:
        return (*key, "carrier", *c.keys.item[end.carrier])
    return key


def _star_key_of(c: _Ctx, one: StageMarker) -> AuthoringKey:
    """D17: the port key, `star`, the placement's discriminator; no role, partner or page."""
    where = c.stands_on[one.port, one.drawing_set, one.page]
    return (*PREFIX, "link_marker", *c.keys.port[one.port], "star", *where)


def _key_of(c: _Ctx, one: StageMarker, other: StageMarker) -> AuthoringKey:
    """A key given twice also names the placement its port stands on (layout-0127)."""
    key = _key_to(c.keys, one, other.port)
    if key in c.doubled:
        return (*key, "on", *c.stands_on[one.port, one.drawing_set, one.page])
    return key


def _tag_of(one: StageMarker) -> str:
    return "off" if one.star == "off" else "star"  # C21: an off stub is its own partner


def _star_keys(
    c: _Ctx, markers: tuple[StageMarker, ...]
) -> dict[tuple[Id[Any] | None, int, int, str, StubText | None], AuthoringKey]:
    """A star marker's key by its port, page, tag and (an off stub) its end's text."""
    return {
        (one.port, one.drawing_set, one.page, _tag_of(one), one.end_text): (
            _off_key(c, one, c.end_of[one.port, one.end_text])
            if one.star == "off"
            else _star_key_of(c, one)
        )
        for one in markers
        if one.star
    }


def _common(c: _Ctx, one: StageMarker) -> dict[str, Any]:
    """The `LinkMarker` fields a cut marker and a star marker take the same way."""
    box_x, lead, stub_extra, via_x, via_y = _marker_fields(one)
    return {
        "page": c.page_of[one.drawing_set, one.page].id,
        "port": one.port,
        "side": ModelMarkerSide[one.side.name],
        "x": one.at.x,
        "y": one.at.y,
        "width": one.box.width,
        "height": one.box.height,
        "produced_by": c.stamp,
        "box_x": box_x,
        "lead": lead,
        "stub_extra": stub_extra,
        "via_x": via_x,
        "via_y": via_y,
        "vertical": one.vertical,
    }


def _record(c: _Ctx, one: StageMarker, other: StageMarker) -> LinkMarker:
    key = _key_of(c, one, other)
    partner = make_id(LinkMarker, _key_of(c, other, one))
    return LinkMarker(id=make_id(LinkMarker, key), key=key, partner=partner, **_common(c, one))


def _star_marker(
    c: _Ctx,
    star_key: Mapping[tuple[Id[Any] | None, int, int, str, StubText | None], AuthoringKey],
    one: StageMarker,
) -> LinkMarker:
    # D9 (F7): a reference carrying the off stub's text on the same port is that off stub
    if one.star == "off":
        off = c.end_of[one.port, one.end_text]
    else:
        off = c.by_port[one.port] if one.text else None
    tag = _tag_of(one)
    key = star_key[one.port, one.drawing_set, one.page, tag, one.end_text]
    partner = star_key[one.star_partner, one.star_partner_set, one.partner_page, tag, one.end_text]
    return LinkMarker(
        id=make_id(LinkMarker, key),
        key=key,
        partner=make_id(LinkMarker, partner),
        star=StarKind.OFF if off else StarKind[one.star.upper()],
        far=off.far if off else None,
        carrier=off.carrier if off else None,
        facing=_facing(one) if off else None,
        wrap_at=one.wrap_at,
        **_common(c, one),
    )


def _pairs_and_doubled(
    markers: tuple[StageMarker, ...], keys: WriteKeys
) -> tuple[list[tuple[StageMarker, StageMarker]], frozenset[AuthoringKey]]:
    """The cut pairs, and the keys a cut drawn in two drawing sets gives twice (layout-0127)."""
    pairs = _pairs(tuple(m for m in markers if not m.star))
    counts = Counter(
        _key_to(keys, one, other.port) for pair in pairs for one, other in (pair, pair[::-1])
    )
    return pairs, frozenset(key for key, count in counts.items() if count > 1)


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
