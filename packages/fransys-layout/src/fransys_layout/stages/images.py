"""Contact images and their reserved room."""

from dataclasses import dataclass, field, replace
from functools import partial
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, Box, push_clear, text_width
from fransys_model.derive.drawing_text import (
    frame_column,
    frame_row,
    partner_position_text,
)

from ._image_foot import table_x
from ._image_stack import foot_down, headed_width, settled_tables
from ._image_widest import widest_places
from .image_refs import by_owner, home_placements, home_references, unplaced_coil_owners
from .lookups import placed_keepout
from .place import axis_offset
from .room import grow_keepout
from .slices import by_key, page_of
from .texts.power import drawn_shapes
from .types import Home, LabelKind, LabelRequest, PlacedLabel, RequestPartner

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from .pagerun import PageInputs
    from .references.types import LocationPath
    from .types import (
        Cell,
        Column,
        DrawnFunction,
        FunctionSpec,
        Handle,
        LinkMarker,
        PagePlan,
        PlacedFunction,
        Profile,
        SheetFormat,
    )


@dataclass(frozen=True)
class ImageInputs:
    """What `contact_images` reads of the run; `marks` is `derive.drawing_text.contact_marks`."""

    functions: tuple[FunctionSpec, ...]
    sheet: SheetFormat
    profile: Profile
    marks: dict[Handle, tuple[list[str], list[str]]]
    owners: Mapping[Handle, Handle] | None = None  # contact function -> the item owning it
    spares: tuple[FunctionSpec, ...] = ()  # Contacts on no page, listed "<mark> <no_place>"
    row_order: Mapping[Handle, tuple[Any, ...]] = field(default_factory=dict)  # Order, model-0138
    replicas: Mapping[tuple[AuthoringKey, Handle], Handle | None] = field(
        default_factory=dict
    )  # layout-0184: each replica cell -> its column's unit
    no_place: str = field(kw_only=True)  # layout-0112: the model's text for "not drawn"
    heads: Mapping[Handle, str] = field(default_factory=dict)  # coil -> its table's heading (0170)


def _image_marks(
    contacts: Sequence[FunctionSpec], marks: Mapping[Handle, tuple[list[str], list[str]]]
) -> tuple[list[str], list[str]]:
    """The terminal pairs of `contacts`, as (NO marks, NC marks), each in `contacts` order."""
    no: list[str] = []
    nc: list[str] = []
    for s in contacts:
        no.extend(marks[s.function][0])
        nc.extend(marks[s.function][1])
    return no, nc


def _seat(one: PlacedFunction, paths: Mapping[int, LocationPath]) -> tuple[int, int, LocationPath]:
    """`one`'s drawing set, page and location path, as `partner_position_text` reads them."""
    return one.drawing_set, one.page, paths.get(one.drawing_set, ())


def _where(
    sheet: SheetFormat,
    paths: Mapping[int, LocationPath],
    target: PlacedFunction,
    reader: PlacedFunction,
) -> str:
    """`target`'s place exactly as render prints it for `reader` (derive's one text)."""
    column = frame_column(sheet.content_width, sheet.frame_columns, target.at.x)
    row = frame_row(sheet.content_height, sheet.frame_rows, target.at.y)
    return partner_position_text(_seat(reader, paths), _seat(target, paths), column, row)


def _partner(at: PlacedFunction, spec: FunctionSpec) -> RequestPartner:
    """The cross-reference partner `spec` makes, placed at `at`."""
    return RequestPartner(
        port=spec.ports[0].port, drawing_set=at.drawing_set, page=at.page, x=at.at.x
    )


def _entry_text(mark: str, where: str) -> str:
    """A contact image entry: the terminal pair and the place, "1-2 /3.7"."""
    return f"{mark} {where}"


@dataclass(frozen=True)
class _Reserve:
    """What one cell keeps free for contact images: `down` below, `images` hung on its lane."""

    down: int = 0
    images: tuple[tuple[Handle, tuple[str, ...], bool], ...] = ()
    tables: tuple[int, ...] = ()  # layout-0170: the heights of the tables of the foot it holds

    def hold(
        self,
        profile: Profile,
        image: tuple[Handle, tuple[str, ...], bool] | None = None,
        table: int | None = None,
    ) -> _Reserve:
        """This reserve plus an `image` hung on its lane and a `table` standing on its foot."""
        tables = self.tables if table is None else (*self.tables, table)
        images = self.images if image is None else (*self.images, image)
        return _Reserve(down=foot_down(tables, profile), images=images, tables=tables)


def _image_width(entries: Sequence[str], profile: Profile, heading: str = "") -> int:
    """A contact image's width, two columns of widest text plus padding.

    A stacked table's `heading` (layout-0170) is measured too: the table is no narrower than it.
    """
    column = max(text_width(t, height=profile.text_height) for t in (*entries, "NO", "NC"))
    return headed_width(2 * (column + 2 * profile.marker_padding), heading, profile)


def table_height(rows: int, profile: Profile) -> int:
    """A contact table's height: its head and `rows` rows of text, padded (one shared size)."""
    return profile.table_base + rows * profile.text_height


def image_reserves(
    columns: tuple[Column, ...],
    specs: tuple[FunctionSpec, ...],
    profile: Profile,
    marks: Mapping[Handle, tuple[list[str], list[str]]],
    owners: Mapping[Handle, Handle] | None = None,
) -> dict[tuple[AuthoringKey, Handle], _Reserve]:
    """(column key, function) -> `_Reserve`; a flipped cell keeps nothing."""
    by_item = by_owner([s for s in specs if s.roles.contact], owners)
    spec_of = {spec.function: spec for spec in specs}
    found: dict[tuple[AuthoringKey, Handle], _Reserve] = {}
    for column in columns:
        for cell in column.cells:
            spec = spec_of.get(cell.function)
            if (
                cell.home is Home.ELSEWHERE
                or spec is None
                or not spec.roles.contacts_apart
                or _hosted(cell)
            ):
                continue
            no, nc = _image_marks(by_item.get(spec.item, []), marks)
            if not (no or nc):
                continue
            height = table_height(max(len(no), len(nc)), profile)
            under = [
                c for c in column.cells if c.index > cell.index and c.host is None and not c.side
            ]
            last = max(under, key=lambda c: c.index) if under else cell
            cross = any(
                c.drawing_set_key != spec.drawing_set_key for c in by_item.get(spec.item, [])
            )
            image = (cell.function, (*no, *nc), cross)  # A contact in another set
            lane = [c for c in under if c.lane == cell.lane]
            wide = (cell, *(() if cell.side else lane))
            for one in dict.fromkeys((*wide, last)):
                if one.flip:
                    continue
                key = column.key, one.function
                before = found.get(key, _Reserve())
                found[key] = before.hold(
                    profile, image if one in wide else None, height if one is last else None
                )
    return found


def with_flipped_below(
    reserves: Mapping[tuple[AuthoringKey, Handle], _Reserve],
    columns: tuple[Column, ...],
    heights: Mapping[Handle, int],
) -> dict[tuple[AuthoringKey, Handle], _Reserve]:
    """A flipped cell keeps no room (place rebuilds its geometry), so the cell above holds it.

    Each reserve that holds a table's room grows by the keep-out heights of the cells below it.
    """
    found = dict(reserves)
    below: dict[tuple[AuthoringKey, Handle], int] = {}
    for column in columns:
        rows: dict[int, list[Handle]] = {}
        for cell in column.cells:
            rows.setdefault(cell.index, []).append(cell.function)
        total = 0
        for index in sorted(rows, reverse=True):
            below.update({(column.key, function): total for function in rows[index]})
            total += sum(heights.get(function, 0) for function in rows[index])
    for place, reserve in reserves.items():
        if reserve.down:
            found[place] = replace(reserve, down=reserve.down + below.get(place, 0))
    return found


def rooms(
    reserves: Mapping[tuple[AuthoringKey, Handle], _Reserve],
    drawn: tuple[DrawnFunction, ...],
    plans: tuple[PagePlan, ...],
    inputs: PageInputs,
) -> dict[tuple[AuthoringKey, Handle], tuple[int, int]]:
    """(column key, function) -> (down, right) room, from the widest place text."""
    widest = widest_places(plans, inputs)
    by_function = {one.function: one for one in drawn}
    found = {}
    for key, reserve in reserves.items():
        one = by_function[key[1]]
        edge = one.geometry.keepout.x + one.geometry.keepout.width
        right = 0
        for coil, marks, cross in reserve.images:
            first = by_function[coil]
            start = axis_offset(one) + first.geometry.ports[0].at.x - axis_offset(first)
            head = inputs.heads.get(coil, "") if len(reserve.tables) > 1 else ""
            width = _image_width(
                [_entry_text(mark, widest[cross]) for mark in marks], inputs.profile, head
            )
            right = max(right, start + WIRING_GRID // 2 + width - edge)
        found[key] = (reserve.down, right)
    return found


def reserved(
    drawn: tuple[DrawnFunction, ...], rooms: Mapping[tuple[AuthoringKey, Handle], tuple[int, int]]
) -> tuple[DrawnFunction, ...]:
    """`drawn` with each function that has a room in `rooms` grown (no filter)."""
    grow = {function: room for (_, function), room in rooms.items()}
    if not grow:
        return drawn
    found = []
    for one in drawn:
        room = grow.get(one.function)
        if room is None:
            found.append(one)
            continue
        (down, right), k = room, one.geometry.keepout
        below = Box(x=k.x, y=k.y + k.height, width=k.width, height=down)
        beside = Box(x=k.x + k.width, y=k.y, width=right, height=k.height)
        found.append(replace(one, geometry=grow_keepout(one.geometry, [below, beside])))
    return tuple(found)


def unreserve(
    placed: tuple[PlacedFunction, ...],
    rooms: Mapping[tuple[AuthoringKey, Handle], tuple[int, int]],
) -> tuple[PlacedFunction, ...]:
    """The reserved room taken off again after placing (lint and router see the symbol)."""
    found = []
    for one in placed:
        room = rooms.get((one.column, one.function))
        if room is None:
            found.append(one)
            continue
        (down, right), k = room, one.geometry.keepout
        trimmed = Box(x=k.x, y=k.y, width=k.width - right, height=k.height - down)
        found.append(replace(one, geometry=replace(one.geometry, keepout=trimmed)))
    return tuple(found)


def _image_top(
    at: PlacedFunction, placed_page: tuple[PlacedFunction, ...], profile: Profile
) -> int:
    """The y a coil's image starts: below its side elements, or at the column foot."""
    same = [one for one in placed_page if one.column == at.column]
    if any(one.at.y > at.at.y for one in same):
        foot = max(one.at.y + one.geometry.keepout.y + one.geometry.keepout.height for one in same)
        return foot + profile.marker_padding
    keepout = placed_keepout(at)
    row = [placed_keepout(one) for one in same if one.at.y == at.at.y]
    y = max(b.y + b.height for b in (keepout, *row)) + profile.marker_padding
    return y + WIRING_GRID if len(row) > 1 else y


def _page_holding(
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
) -> dict[tuple[Handle, int, int], tuple[PlacedFunction, ...]]:
    """The placed tuple of the first page holding each placement `(function, drawing_set, page)`."""
    found: dict[tuple[Handle, int, int], tuple[PlacedFunction, ...]] = {}
    for placed, _ in pages:
        for one in placed:
            found.setdefault((one.function, one.drawing_set, one.page), placed)
    return found


def _page_marker_boxes(markers: tuple[Any, ...]) -> dict[tuple[int, int], tuple[Box, ...]]:
    """layout-0134: the ink below an item per `(drawing_set, page)`: what the page draws."""
    return {
        here: tuple(one.box for one in drawn_shapes(group))
        for here, group in by_key(markers, page_of).items()
    }


def contact_images(
    plans: tuple[PagePlan, ...],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    inputs: ImageInputs,
    markers: tuple[LinkMarker, ...] = (),
    paths: Mapping[int, LocationPath] | None = None,
) -> tuple[
    list[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]], tuple[LabelRequest, ...]
]:
    """A NO | NC contact table under each coil; order is by function id, not input order."""
    sheet, profile = inputs.sheet, inputs.profile
    home = home_placements(pages, inputs.replicas, {s.function: s.unit for s in inputs.functions})
    by_item = by_owner([s for s in inputs.functions if s.function in home], inputs.owners)
    coil_unplaced = unplaced_coil_owners(inputs.functions, inputs.owners, home)
    spare_of = by_owner([s for s in inputs.spares if s.roles.contact], inputs.owners)

    where = partial(_where, sheet, paths or {})
    holding = _page_holding(pages)
    marker_boxes = _page_marker_boxes(markers)
    tables: dict[tuple[int, int], list[PlacedLabel]] = {}
    requests = []
    for owner, group in sorted(by_item.items(), key=lambda e: min(s.function for s in e[1])):
        coil = next((s for s in group if s.roles.contacts_apart), None)
        contacts = sorted((s for s in group if s.roles.contact), key=attrgetter("function"))
        main = coil or next(
            (s for s in sorted(group, key=attrgetter("function")) if not s.roles.contact), None
        )
        spare_no, spare_nc = _image_marks(spare_of.get(owner, []) if coil else [], inputs.marks)
        if main is None or not (contacts or spare_no or spare_nc):
            continue
        if coil is None and owner in coil_unplaced:
            continue
        if coil is None:  # No coil, so the main symbol; one reference path, no table
            requests.extend(home_references(contacts, main, home, where))
            continue
        at = home[coil.function]
        order = sorted(
            contacts,
            key=lambda s: (len(s.ports) <= 2, inputs.row_order.get(s.function, ())),  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
        )
        no, nc = [], []
        for s in order:
            s_no, s_nc = inputs.marks[s.function]
            no.extend(_entry_text(mark, where(home[s.function], at)) for mark in s_no)
            nc.extend(_entry_text(mark, where(home[s.function], at)) for mark in s_nc)
        no.extend(_entry_text(mark, inputs.no_place) for mark in spare_no)  # layout-0112: no place
        nc.extend(_entry_text(mark, inputs.no_place) for mark in spare_nc)
        width = _image_width([*no, *nc], profile)
        height = table_height(max(len(no), len(nc)), profile)
        x = table_x(at.at, at.geometry)
        y = _image_top(at, holding[at.function, at.drawing_set, at.page], profile)
        # layout-0123: nor on a marker, a stub or a power symbol (a star marker)
        here = marker_boxes.get((at.drawing_set, at.page), ())
        box = push_clear(
            Box(x=x, y=y, width=width, height=height), here, gap=profile.marker_padding, axis="y"
        )
        # a table of spares alone has no drawn contact: the coil itself is the model's one partner
        partners = tuple(_partner(home[s.function], s) for s in order) or (_partner(at, coil),)
        tables.setdefault((at.drawing_set, at.page), []).append(
            PlacedLabel(
                kind=LabelKind.CROSS_REFERENCE,
                subject=coil.function,
                slot="contacts",
                drawing_set=at.drawing_set,
                page=at.page,
                box=box,
                partners=partners,
            )
        )
        requests.extend(home_references(contacts, coil, home, where))
    tables = settled_tables(
        tables, home, marker_boxes, profile, inputs.heads
    )  # Baseline, layout-0170 stack
    found = []
    for plan, (placed, first) in zip(plans, pages, strict=True):
        found.append((placed, (*first, *tables.get((plan.drawing_set, plan.number), ()))))
    return found, tuple(requests)


def _hosted(cell: Cell) -> bool:
    """A cell attached to a host keeps no image reserve; a moved one is a home cell."""
    return cell.host is not None and cell.home is not Home.MOVED
