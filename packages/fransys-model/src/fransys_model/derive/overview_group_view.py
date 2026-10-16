"""One function group opened as a level (O3a): its devices, pass-through lines and stubs.

A terminal that only passes two wires through is drawn as one line labelled with its strip; any
other terminal keeps its strip as a box. A connection to a box outside the group, or outside the
unit, ends at a stub on the box it leaves. Reached through `derive.fold_level`.
"""

from typing import Any, NamedTuple, cast

from fransys_model.layout import OverviewRef, OverviewRefKind
from fransys_model.vocab.enums import ItemKind
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit

from .designation import location_node_designation, printed_designation
from .order import natural_key
from .overview_conns import Conn, Through, split_through, unit_connections
from .overview_groups import box_order_key, fold_box, fold_key
from .overview_levels import level_box
from .overview_strip_level import freed, terminal_boxes
from .overview_stubs import RawStub, inner_stub, outside_stub, shared_stubs
from .overview_text import overview_lifted_text
from .rows_overview import FoldBox, FoldLevel, FoldLine, StripNote, StubPlace
lazy from .rows import OverviewBox

__all__ = ["Lifted", "Scope", "merged_lines", "open_group", "strip_notes"]


class Lifted(NamedTuple):
    """One connection lifted to a pair of boxes; `strip` is set when it passes through one."""

    a: OverviewRef
    b: OverviewRef
    conn: Conn
    strip: Id[Item] | None


def _line(model: Model, unit: Id[Unit], key: tuple[Any, ...], group: list[Lifted]) -> FoldLine:
    """One line from the connections of one pair, kind and strip."""
    first, second, kind, strip = key
    vias = tuple(sorted({one.conn.via for one in group if one.conn.via is not None}))
    if strip is None:
        texts = {one.conn.via_text for one in group if one.conn.via_text}
        label = overview_lifted_text(kind, sorted(texts, key=natural_key), len(group))
        return FoldLine(
            a=first,
            b=second,
            kind=kind,
            count=len(group),
            vias=vias,
            label=label,
            strip=None,
            terminals=0,
        )
    text = printed_designation(model, strip, unit=unit)
    label = text if len(group) == 1 else f"{text} x {len(group)}"
    return FoldLine(
        a=first,
        b=second,
        kind=kind,
        count=len(group),
        vias=vias,
        label=label,
        strip=strip,
        terminals=len(group),
    )


def merged_lines(
    model: Model, unit: Id[Unit], lifted: list[Lifted], rank: dict[OverviewRef, int]
) -> tuple[FoldLine, ...]:
    """One line per pair of boxes, kind and strip, the connections added; in box rank order."""
    held: dict[tuple[Any, ...], list[Lifted]] = {}
    for one in lifted:
        first, second = sorted((one.a, one.b), key=rank.__getitem__)
        held.setdefault((first, second, one.conn.kind, one.strip), []).append(one)
    lines = [_line(model, unit, key, group) for key, group in held.items()]
    return tuple(
        sorted(
            lines,
            key=lambda ln: (
                rank[ln.a],
                rank[ln.b],
                ln.kind.value,
                ln.strip is not None,
                natural_key(ln.label),
            ),
        )
    )


def strip_notes(
    boxes: tuple[OverviewBox, ...], held: set[Id[Any]], passed: dict[Id[Any], int]
) -> tuple[StripNote, ...]:
    """Each strip the level holds as a box, or passes wires through, in box text order."""
    notes = []
    for box in boxes:
        if box.kind is not ItemKind.STRIP:
            continue
        if box.box in held:
            notes.append(StripNote(strip=box.box, terminals=box.terminals, held=True))
        elif passed.get(box.box):
            notes.append(StripNote(strip=box.box, terminals=passed[box.box], held=False))
    return tuple(notes)


class Scope(NamedTuple):
    """What an opened level holds: `opened` is its `GROUP` or `STRIPS` box, else all the unit.

    `strip` is the one strip opened in it, whose terminals stand in its place (O5).
    """

    opened: OverviewRef | None = None
    strip: Id[Item] | None = None


class _Walk:
    """The connections of one opened level, sorted into lines, stubs and touched strips."""

    def __init__(
        self,
        model: Model,
        unit: Id[Unit],
        boxes: tuple[OverviewBox, ...],
        groups: dict[Id[Any], Id[AspectNode] | None],
        members: list[OverviewBox],
    ) -> None:
        self.model, self.unit, self.groups = model, unit, groups
        self.through: dict[Id[Item], Conn] = {}
        self.own = False
        self.by_id = {box.box: box for box in boxes}
        self.mine = {box.box: fold_key(box) for box in members}
        self.lifted: list[Lifted] = []
        self.raws: list[RawStub] = []
        self.touched: set[Id[Any]] = set()
        self.passed: dict[Id[Any], int] = {}
        self.terminals: dict[Id[Any], FoldBox] = {}

    def open_strip(self, strip: Id[Item], terminals: tuple[FoldBox, ...]) -> None:
        """Stand `strip`'s terminals in its place: they are boxes of the level, the strip is not."""
        self.own = strip in self.mine
        self.mine.pop(strip, None)
        for box in terminals:
            self.mine[cast("Id[Item]", box.key.item)] = box.key
            self.terminals[cast("Id[Item]", box.key.item)] = box

    def _box_of(self, item: Id[Item]) -> Id[Any] | None:
        """The box of this level holding `item`: the terminal itself when its strip is open."""
        return item if item in self.terminals else level_box(self.model, item, self.unit)

    def _far_stub(
        self, key: OverviewRef, far: Id[Any] | None, conn: Conn, *, inside_a: bool
    ) -> None:
        """The stub at `key` for a connection to `far`, a box of the unit, or `None` outside it."""
        if far is None:
            self.raws.append(outside_stub(self.model, self.unit, key, conn, inside_a=inside_a))
            return
        node = self.groups[far]
        if node is not None:
            name = location_node_designation(self.model, node)
            end = OverviewRef(kind=OverviewRefKind.GROUP, node=node)
            self.raws.append(inner_stub(key, StubPlace.GROUP, name, end, conn))
        else:
            box = self.by_id[far]
            self.raws.append(inner_stub(key, StubPlace.BOX, box.lines[0], fold_key(box), conn))

    def _stub(
        self, at: int, key: OverviewRef, ends: tuple[Id[Any] | None, ...], conn: Conn
    ) -> None:
        """The stub at `key` for the end `at` of `conn` inside the level.

        A pass-through terminal wires to the stub its closed strip has, or has none when the level
        draws neither end. A strip the level does not hold has no other stub (O5).
        """
        near = ends[at]
        pair = self.through.get(cast("Id[Item]", near))
        if pair is None:
            if self.own or near not in self.terminals:
                self._far_stub(key, ends[1 - at], conn, inside_a=at == 0)
            return
        far = conn.b if at == 0 else conn.a
        inside_a = pair.a != far
        home = self.mine.get(self._box_of(pair.a if inside_a else pair.b))
        if home is None:
            return
        self._far_stub(home, ends[1 - at], pair, inside_a=inside_a)
        self.raws[-1] = self.raws[-1]._replace(box=key, home=home)

    def add(self, conn: Conn, strip: Id[Item] | None) -> bool:
        """Sort `conn` into a line, a stub or nothing; whether the group is an end of it."""
        ends = (self._box_of(conn.a), self._box_of(conn.b))
        keys = [self.mine.get(end) for end in ends]
        if strip is None:
            self.touched |= {
                e
                for e in ends
                if e in self.by_id and e in self.mine and self.by_id[e].kind is ItemKind.STRIP
            }
        if keys[0] is not None and keys[1] is not None:
            if keys[0] != keys[1]:
                self.lifted.append(Lifted(keys[0], keys[1], conn, strip))
            return True
        for at, key in enumerate(keys):
            if key is not None:
                self._stub(at, key, ends, conn)
                return True
        return False


def _members(
    boxes: tuple[OverviewBox, ...],
    groups: dict[Id[Any], Id[AspectNode] | None],
    opened: OverviewRef | None,
) -> list[OverviewBox]:
    """The boxes the level `opened` holds: its group's, the group-less strips', or all."""
    if opened is None:
        return list(boxes)
    if opened.kind is OverviewRefKind.STRIPS:
        return [b for b in boxes if b.kind is ItemKind.STRIP and groups[b.box] is None]
    return [box for box in boxes if groups[box.box] == opened.node]


def _drawn(box: OverviewBox, held: set[Id[Any]], strip: Id[Item] | None) -> bool:
    """Whether the level draws `box`: not the strip opened, and a strip only when it is held."""
    return box.box != strip and (box.kind is not ItemKind.STRIP or box.box in held)


def _held_split(
    model: Model, unit: Id[Unit], conns: tuple[Conn, ...], inside: set[Id[Any]]
) -> tuple[tuple[Conn, ...], tuple[Through, ...]]:
    """`split_through`, but a held strip's terminal passes only with an inside end (O3a, A19).

    Else its strip stays a box and the terminal's wires are plain, ending at the strip's stubs.
    """
    plain, passing = split_through(model, conns)
    outside = {
        one.terminal
        for one in passing
        if level_box(model, one.strip, unit) in inside
        and not {level_box(model, one.conn.a, unit), level_box(model, one.conn.b, unit)} & inside
    }
    more = tuple(c for c in conns if {c.a, c.b} & outside)
    return (*plain, *more), tuple(one for one in passing if one.terminal not in outside)


def _connections(
    model: Model, unit: Id[Unit], scope: Scope, inside: set[Id[Any]]
) -> tuple[tuple[Conn, ...], tuple[Through, ...], dict[Id[Item], Conn]]:
    """The plain connections, the pass-throughs, and the joined wire of each open terminal.

    Strips are boxes at the strips level.
    """
    conns = unit_connections(model, unit)
    if scope.opened is not None and scope.opened.kind is OverviewRefKind.STRIPS:
        return conns, (), {}
    if scope.opened is None:
        plain, passing = split_through(model, conns)
    else:
        plain, passing = _held_split(model, unit, conns, inside)
    if scope.strip is None:
        return plain, passing, {}
    joined = {one.terminal: one.conn for one in passing if one.strip == scope.strip}
    more, passing = freed(conns, passing, scope.strip)
    return (*plain, *more), passing, joined


def _walked(
    model: Model,
    unit: Id[Unit],
    parts: tuple[tuple[OverviewBox, ...], dict[Id[Any], Id[AspectNode] | None]],
    scope: Scope,
) -> tuple[_Walk, list[OverviewBox], tuple[FoldBox, ...]]:
    """The walk of every connection of the level `scope` names, its members and open terminals."""
    boxes, groups = parts
    members = _members(boxes, groups, scope.opened)
    walk = _Walk(model, unit, boxes, groups, members)
    terminals = () if scope.strip is None else terminal_boxes(model, unit, scope.strip)
    if scope.strip is not None:
        walk.open_strip(scope.strip, terminals)
    plain, passing, walk.through = _connections(model, unit, scope, {m.box for m in members})
    for conn in plain:
        walk.add(conn, None)
    for one in passing:
        if walk.add(one.conn, one.strip):
            walk.passed[one.strip] = walk.passed.get(one.strip, 0) + 1
    return walk, members, terminals


def _terminals_drawn(
    walk: _Walk, terminals: tuple[FoldBox, ...], *, own: bool
) -> tuple[FoldBox, ...]:
    """The open strip's terminals: all of an own strip's, else those the level wires to."""
    used = {*(one.a for one in walk.lifted), *(one.b for one in walk.lifted)}
    used |= {raw.box for raw in walk.raws}
    return tuple(t for t in terminals if own or t.key in used)


def open_group(
    model: Model,
    unit: Id[Unit],
    boxes: tuple[OverviewBox, ...],
    groups: dict[Id[Any], Id[AspectNode] | None],
    scope: Scope,
) -> FoldLevel:
    """The level `scope` names opened: a group, the strips box, or all of `unit`.

    A strip opened in it (`scope.strip`) stands as its terminals.
    """
    walk, members, terminals = _walked(model, unit, (boxes, groups), scope)
    strips_level = scope.opened is not None and scope.opened.kind is OverviewRefKind.STRIPS
    held = {m.box for m in members if m.kind is ItemKind.STRIP} if strips_level else walk.touched
    drawn = [m for m in members if _drawn(m, held, scope.strip)]
    own = scope.strip in {m.box for m in members}
    shown = (
        *sorted((fold_box(m) for m in drawn), key=box_order_key),
        *_terminals_drawn(walk, terminals, own=own),
    )
    rank = {box.key: at for at, box in enumerate(shown)}
    stubs, wires = shared_stubs(model, unit, walk.raws, rank, {t.key for t in terminals})
    return FoldLevel(
        unit=unit,
        opened=scope.opened,
        folded=False,
        boxes=shown,
        lines=merged_lines(model, unit, walk.lifted, rank),
        stubs=stubs,
        strips=strip_notes(boxes, held, walk.passed),
        wires=wires,
    )
