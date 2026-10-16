"""The overview's folded stubs (O3b): connections leaving a level, folded by their far end.

Far ends inside one unit fold to one stub named by that unit. Far ends in no unit fold by their top
location node when the model has two or more, else each stays a stub as `stub_far_end` prints it.
A stub's `members` are the single stubs it opens to (O5). Reached through `derive.fold_level`.
"""

from dataclasses import replace
from typing import NamedTuple, cast

from fransys_model.layout import OverviewRef, OverviewRefKind
from fransys_model.vocab.enums import ItemKind
from fransys_model.vocab.tables import items, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Port, Unit

from .designation import location_node_designation, printed_designation
from .drawing_text import stub_far_end
from .kinds import item_kind
from .lookups import unit_chain
from .order import natural_key
from .overview_field import field_devices
from .overview_levels import level_box, level_box_lines, merge_stubs, stub_far_root
from .overview_location import top_place_of
from .overview_names import display_unit
from .rows import OverviewLinkKind, OverviewStub
from .rows_overview import FoldStub, StubPlace, StubWire
lazy from .overview_conns import Conn

__all__ = [
    "RawStub",
    "fold_stubs",
    "inner_stub",
    "outside_stub",
    "overview_stub_west",
    "shared_stubs",
]


class RawStub(NamedTuple):
    """One connection's stub before folding: where it stands, its fold place and name.

    `home` is set on a pass-through terminal's stub: the box where the closed strip's stub stands.
    """

    box: OverviewRef
    place: StubPlace
    far: str
    end: OverviewRef
    kind: OverviewLinkKind
    via: Id[Item] | None
    member: OverviewStub | None
    home: OverviewRef | None = None


def _far_unit(model: Model, unit: Id[Unit], far: Id[Item]) -> Id[Unit] | None:
    """The unit holding `far`, climbed to the one that is not `unit` or above it, else `None`."""
    owner = items(model)[far].unit
    if owner is None:
        return None
    outside = [one for one in unit_chain(model, owner) if one not in unit_chain(model, unit)]
    return outside[-1] if outside else None


def _far_text(
    model: Model, unit: Id[Unit], far: Id[Item], ports: tuple[Id[Port] | None, Id[Port] | None]
) -> tuple[str, str]:
    """The far end's name and port tails, relative to the innermost opened unit holding it."""
    shown = display_unit(model, far, unit)
    far_port, near_port = ports
    if far_port is None:
        return printed_designation(model, far, unit=shown), ""
    return stub_far_end(model, far_port, near_port, unit=shown)


def outside_stub(
    model: Model, unit: Id[Unit], key: OverviewRef, conn: Conn, *, inside_a: bool
) -> RawStub:
    """The stub for `conn`, whose `a` end is inside the level when `inside_a`, else its `b` end."""
    near, near_port, far, far_port = (
        (conn.a, conn.a_port, conn.b, conn.b_port)
        if inside_a
        else (conn.b, conn.b_port, conn.a, conn.a_port)
    )
    inside = cast("Id[Item]", level_box(model, near, unit))
    text, tails = _far_text(model, unit, far, (far_port, near_port))
    end = stub_far_root(model, far)
    member = OverviewStub(
        box=inside, kind=conn.kind, via=conn.via, far=text, ports=tails, end=end, count=1
    )
    home = field_devices(model).get(far)
    if home is not None:
        field = OverviewRef(kind=OverviewRefKind.FIELDS, unit=home)
        return RawStub(key, StubPlace.FIELD, text, field, conn.kind, conn.via, member)
    holder = _far_unit(model, unit, far)
    if holder is not None:
        name, end = (
            level_box_lines(model, holder, units(model)[holder].parent)[0],
            OverviewRef(kind=OverviewRefKind.UNIT, unit=holder),
        )
        return RawStub(key, StubPlace.UNIT, name, end, conn.kind, conn.via, member)
    top = top_place_of(model, far)
    if top is not None:
        name, end = (
            location_node_designation(model, top),
            OverviewRef(kind=OverviewRefKind.PLACE, node=top),
        )
        return RawStub(key, StubPlace.LOCATION, name, end, conn.kind, conn.via, member)
    return RawStub(key, StubPlace.END, text, end, conn.kind, conn.via, member)


def inner_stub(
    key: OverviewRef, place: StubPlace, name: str, end: OverviewRef, conn: Conn
) -> RawStub:
    """The stub of a connection to another group or box of the same unit, which has no members."""
    return RawStub(key, place, name, end, conn.kind, conn.via, None)


def _fold_key(raw: RawStub) -> tuple[object, ...]:
    """What folds: box, place and name; an `END` also keeps its kind, carrier and ports apart."""
    base = (raw.box, raw.place, raw.far, raw.kind)
    member = raw.member
    if raw.place is StubPlace.END and member is not None:
        return (*base, member.via, member.ports)
    return base


def _field_folds(raws: list[RawStub]) -> list[RawStub]:
    """Field-device stubs of one box and kind named "Field devices (n)", or as their one device."""
    devices: dict[tuple[OverviewRef, OverviewLinkKind], set[OverviewRef]] = {}
    for raw in raws:
        if raw.place is StubPlace.FIELD and raw.member is not None:
            devices.setdefault((raw.box, raw.kind), set()).add(raw.member.end)
    out = []
    for raw in raws:
        if raw.place is not StubPlace.FIELD or raw.member is None:
            out.append(raw)
        elif len(ends := devices[(raw.box, raw.kind)]) == 1:
            out.append(raw._replace(place=StubPlace.END, end=raw.member.end))
        else:
            out.append(raw._replace(far=f"Field devices ({len(ends)})"))
    return out


def _folded(model: Model, unit: Id[Unit], group: list[RawStub]) -> FoldStub:
    """The one stub that equal raw stubs fold to."""
    first = group[0]
    return FoldStub(
        box=first.box,
        place=first.place,
        far=first.far,
        end=first.end,
        kind=first.kind,
        via=first.via if first.place is StubPlace.END else None,
        count=len(group),
        members=merge_stubs(model, unit, [r.member for r in group if r.member is not None]),
    )


def _ordered(stubs: list[FoldStub], rank: dict[OverviewRef, int]) -> tuple[FoldStub, ...]:
    """`stubs` in box, then place, name, kind and member order."""
    return tuple(
        sorted(
            stubs,
            key=lambda s: (
                rank[s.box],
                s.place.value,
                natural_key(s.far),
                s.kind.value,
                tuple((m.ports, m.kind.value, m.via is not None, m.via) for m in s.members),
            ),
        )
    )


def _grouped(raws: list[RawStub]) -> tuple[list[RawStub], list[list[int]]]:
    """`raws` field-folded, and the positions in it of each stub that equal raw stubs fold to."""
    folded = _field_folds(raws)
    held: dict[tuple[object, ...], list[int]] = {}
    for at, raw in enumerate(folded):
        held.setdefault(_fold_key(raw), []).append(at)
    return folded, list(held.values())


def fold_stubs(
    model: Model, unit: Id[Unit], raws: list[RawStub], rank: dict[OverviewRef, int]
) -> tuple[FoldStub, ...]:
    """Equal stubs joined, with the single stubs they open to, in box then name order."""
    folded, groups = _grouped(raws)
    return _ordered([_folded(model, unit, [folded[at] for at in ats]) for ats in groups], rank)


def _part(
    model: Model, unit: Id[Unit], whole: FoldStub, mine: list[RawStub], box: OverviewRef
) -> FoldStub:
    """What `box` holds of `whole`, named and ended as `whole` is."""
    return replace(_folded(model, unit, mine), box=box, far=whole.far, end=whole.end)


def _wires(
    model: Model, unit: Id[Unit], whole: FoldStub, shut: list[RawStub], boxes: list[OverviewRef]
) -> list[StubWire]:
    """The share of each box in `whole`, whose folded raws `shut` stand at `boxes` in turn."""
    return [
        StubWire(
            stub=whole,
            part=_part(
                model,
                unit,
                whole,
                [raw for raw, at in zip(shut, boxes, strict=True) if at == box],
                box,
            ),
        )
        for box in dict.fromkeys(boxes)
    ]


def _shared(
    model: Model, unit: Id[Unit], raws: list[RawStub]
) -> tuple[list[FoldStub], list[StubWire]]:
    """`raws` folded as if they stood at one box, the stub of each far end and the wires to it."""
    owner: dict[OverviewRef, OverviewRef] = {}
    for raw in raws:
        owner.setdefault(raw.end, raw.box)
    shut = _field_folds([raw._replace(box=owner[raw.end]) for raw in raws])
    held: dict[tuple[object, ...], list[int]] = {}
    for at, raw in enumerate(shut):
        held.setdefault(_fold_key(raw), []).append(at)
    stubs: list[FoldStub] = []
    wires: list[StubWire] = []
    for ats in held.values():
        stubs.append(_folded(model, unit, [shut[at] for at in ats]))
        wires += _wires(
            model, unit, stubs[-1], [shut[at] for at in ats], [raws[at].box for at in ats]
        )
    return stubs, wires


def _homed(
    model: Model, unit: Id[Unit], raws: list[RawStub], count: int
) -> tuple[list[FoldStub], list[StubWire]]:
    """`raws` folded at their boxes, and the wires of the stubs holding the last `count` of them.

    Those last raws stand at a terminal but are folded at their `home`.
    """
    folded, groups = _grouped([r._replace(box=r.home or r.box) for r in raws])
    stubs: list[FoldStub] = []
    wires: list[StubWire] = []
    for ats in groups:
        stubs.append(_folded(model, unit, [folded[at] for at in ats]))
        if any(at >= len(raws) - count for at in ats):
            wires += _wires(
                model, unit, stubs[-1], [folded[at] for at in ats], [raws[at].box for at in ats]
            )
    return stubs, wires


def shared_stubs(
    model: Model,
    unit: Id[Unit],
    raws: list[RawStub],
    rank: dict[OverviewRef, int],
    together: set[OverviewRef],
) -> tuple[tuple[FoldStub, ...], tuple[StubWire, ...]]:
    """`fold_stubs`, but the boxes `together` (an open strip's terminals) count as one inside box.

    Each far end's stub hangs on the first of them wired to it, and `wires` give each box its
    share (O5). A raw stub with a `home` folds there, where the closed strip's stub stands.
    """
    homed = [r for r in raws if r.home is not None]
    own = [r for r in raws if r.box in together and r.home is None]
    stubs, wires = _shared(model, unit, own)
    rest = [r for r in raws if r.box not in together]
    more, homes = _homed(model, unit, [*rest, *homed], len(homed))
    wires += homes
    wires.sort(key=lambda w: rank[w.part.box])
    return _ordered([*more, *stubs], rank), tuple(wires)


def overview_stub_west(model: Model, unit: Id[Unit], end: OverviewRef) -> bool:
    """Whether the lanes stub for `end` stands west of the level of `unit`; else east.

    West: an item that is a terminal strip, or one held by a unit that encloses `unit`.
    """
    if end.kind is not OverviewRefKind.ITEM or end.item is None:
        return False
    if item_kind(model, end.item) is ItemKind.STRIP:
        return True
    owner = items(model)[end.item].unit
    return owner is not None and owner in unit_chain(model, unit)
