"""Text that layout and render must agree on: one fact, one place (decision model-0032).

See derive-text.md.

The layout engine sizes a marker's box and a cross-reference label from their text; render
must print exactly that text but may not import `fransys_layout`. Three pure formatters on
plain values (`frame_column`, `position_text`, `location_prefix`) and a family of readers on a
laid-out model (`marker_text`, `cross_reference_text`, `label_text`, `page_title`) hold that
text so both sides call the same code. `fransys_layout.stages.references` calls the
formatters and keeps no copy; render will call the readers. `port_designation_in` applies
the same location rule to a list's end (`terminal_rows`, `wire_rows` and
`connector_rows` call it).

Not re-exported from `fransys_model.derive`: `fransys-layout`'s import-layering
exception (DESIGN 4, decision layout-0037) is keyed to the qualified module path
`fransys_model.derive.drawing_text`, so every stage imports it directly.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any, cast
lazy from collections.abc import Iterable
lazy from decimal import Decimal

from fransys_model.derive.contact_entries import (
    Entry,
    contact_entries,
    image_order,
    spare_entries,
)
from fransys_model.derive.designation import (
    _own_designation,
    connector_designation,
    item_designation,
    own_location_node,
    own_nodes,
    port_designation,
    printed_designation,
    terminal_designation,
    terminal_of,
)
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import effective_placement
from fransys_model.derive.marker_targets import marker_lines, target_lines
from fransys_model.derive.port_marking import marking_text, port_marking
from fransys_model.derive.revision_text import revision_text
from fransys_model.derive.unit_nodes import chain_up, end_context, stub_place
from fransys_model.derive.unit_release import unit_release
from fransys_model.derive.wire_ends import ordered_wire_ends
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, SchemaError, digest_cached
from fransys_model.layout import (
    DrawingSet,
    Label,
    LabelKind,
    LinkMarker,
    Page,
    PageGroup,
    SheetFormat,
    Side,
    StarKind,
    SymbolPlacement,
    layout_of,
    sheet_format_of,
)
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Function, Item, Port, Unit
from fransys_model.vocab.enums import Aspect, FunctionKind
from fransys_model.vocab.membership import unit_items
from fransys_model.vocab.tables import aspect_nodes, conductors, functions, items, ports

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.vocab.connectivity import Conductor

# A location's root-to-leaf path: each node's identity paired with its own label, root first
# (units spec U7). The identity half is what a nearest-common-ancestor walk compares -- never
# the label, so two nodes that happen to share label text at different tree positions are
# never mistaken for one.
type LocationPath = tuple[tuple[Id[AspectNode], str], ...]
type Seat = tuple[int, int, LocationPath]
# A marker's pin key; a reading key.
type _PinKey = tuple[Id[Page], int, int, int, int, int, bool]
type _ReadingKey = tuple[int, int, str, Id[Port]]

# Grid units per symbol module (`G = M/8`), the same constant as
# `fransys_layout.geometry.units.G_PER_MODULE`. Duplicated, not imported: this package
# imports nothing (root CLAUDE.md invariant 2). Only `content_extent` uses it.
_G_PER_MODULE = 8


def frame_column(content_width: int, frame_columns: int, x: int) -> int:
    """The frame-grid column `x` falls in: the content box divided evenly, clamped to the sheet.

    `content_width` and `frame_columns` are grid units and the column count of a page's
    sheet (decision model-0032). It takes the two plain grid-unit values, not a `SheetFormat`
    object: `fransys_model.layout.SheetFormat` is millimetre-based.
    """
    return min(max(x * frame_columns // content_width + 1, 1), frame_columns)


def row_letter(index: int) -> str:
    """The letter for a 0-based frame-grid row index, A first (LD3).

    `fransys_pdf`'s own printed reference grid (`_frame.py::_row_strip`) calls this too, so
    the grid and a position text can never disagree on what a row is called (DESIGN 4, root
    CLAUDE.md's "one rule computed in two places").
    """
    return chr(ord("A") + index)


def frame_row(content_height: int, frame_rows: int, y: int) -> str:
    """The frame-grid row `y` falls in, as a letter: the content box divided evenly, clamped.

    `content_height` and `frame_rows` are grid units and the row count of a page's sheet
    (LD3), the row twin of `frame_column`. Row A is at the top (the smallest `y`), matching
    the printed grid's own top-to-bottom order.
    """
    row = min(max(y * frame_rows // content_height + 1, 1), frame_rows)
    return row_letter(row - 1)


def position_text(  # noqa: PLR0913 -- one form for every position; own_page is the keyword (model-0136)
    page_number: int,
    column: int,
    row: str,
    location_labels: tuple[str, ...],
    set_number: int | None = None,
    *,
    own_page: int | None = None,
) -> str:
    """`p<page_number>:<column><row>`, prefixed by `+<label>` for each of `location_labels` (LD5).

    The one form for every printed position; `row` is `frame_row`'s letter. A caller passes `()`
    for `location_labels` in the same set (U7). `own_page` equal to `page_number` prints the cell.
    """
    if own_page == page_number and not location_labels and set_number is None:
        return f"{column}{row}"
    if not location_labels and set_number is not None:
        # C18, restated for LD5's form: a place in another drawing set with no location
        # prefix still names its set, "p3.2:1A" (set.page, then cell), so it is never ambiguous
        return f"p{set_number}.{page_number}:{column}{row}"
    where = f"p{page_number}:{column}{row}"
    prefix = "".join(f"+{label}" for label in location_labels)
    return f"{prefix}{where}"


def location_prefix(own_path: LocationPath, partner_path: LocationPath) -> tuple[str, ...]:
    """The partner's location labels below the nearest common ancestor, root first (U7).

    Empty when nothing is left below it -- the two ends share their whole path, or the
    partner has none at all. The common-ancestor walk compares each path entry's identity
    half, never its label, so two nodes that happen to share label text at different tree
    positions are never mistaken for one. Feed the result straight to `position_text`.
    """
    common = 0
    for own_node, partner_node in zip(own_path, partner_path, strict=False):
        if own_node[0] != partner_node[0]:
            break
        common += 1
    return tuple(label for _, label in partner_path[common:])


def content_extent(millimetres: int, module_mm: Decimal) -> int:
    """Whole grid units that fit in `millimetres`: `floor(mm / (module_mm / 8))`.

    Sheet sizes are not multiples of G (297 mm is 950.4 G), so a sheet format stores integer
    millimetres and this is the one place they become grid units. Decimal `//` truncates toward
    zero, which is the floor for the positive size of a sheet.
    """
    return int(millimetres * _G_PER_MODULE // module_mm)


def _content_width_grid(sheet: SheetFormat) -> int:
    """`sheet`'s content width in grid units (`content_extent`)."""
    return content_extent(sheet.content_width_mm, sheet.module_mm)


def _content_height_grid(sheet: SheetFormat) -> int:
    """`sheet`'s content height in grid units (`content_extent`), the row twin of the width."""
    return content_extent(sheet.content_height_mm, sheet.module_mm)


def location_path(model: Model, node: Id[AspectNode] | None) -> LocationPath:
    """`node`'s root-to-leaf path, empty for `None` (no location).

    The one walk is `kernel.parent_chain` (via `chain_up`), reversed to root first (units spec
    U7), with each node's label kept alongside its id. Every location text is built from it.
    """
    nodes = aspect_nodes(model)
    return tuple((found, nodes[found].label) for found in reversed(list(chain_up(nodes, node))))


def port_designation_in(
    model: Model, port: Id[Port], context: Id[AspectNode] | None, *, unit: Id[Unit] | None = None
) -> str:
    """`port_designation`, with `+<label>` per location label of `port`'s end below `context`.

    An end outside `context`'s location prints its path below the common ancestor.
    `context=None` prints every located end; `unit` (keyword-only) goes to `port_designation`.
    """
    return "".join(far_end(model, port, context, unit=unit))


def product_designation_in(
    model: Model, item: Id[Item], context: Id[AspectNode] | None, *, unit: Id[Unit] | None = None
) -> str:
    """`item` as a list prints it, with `+<label>` per location label of it below `context`.

    The prefix is `port_designation_in`'s rule; `unit=None` reads OWN placement, else effective.
    A `terminal` with a parent is not a cable end, so it is not read. Raises as `item_designation`.
    """
    text = printed_designation(model, item, unit=unit)
    node = (
        own_location_node(model, item)
        if unit is None
        else effective_placement(model, item, Aspect.LOCATION)
    )
    return _located(model, node, end_context(model, item, node, context, unit), text)


def _located(
    model: Model, node: Id[AspectNode] | None, context: Id[AspectNode] | None, text: str
) -> str:
    """`text` behind one `+label` per location label of `node` below `context`.

    The one prefix step of `port_designation_in` and `product_designation_in`.
    Either `node` or `context` may be `None` (an empty path).
    """
    labels = location_prefix(location_path(model, context), location_path(model, node))
    return "".join(f"+{label}" for label in labels) + text


def far_end(
    model: Model,
    port: Id[Port],
    context: Id[AspectNode] | None = None,
    *,
    unit: Id[Unit] | None = None,
) -> tuple[str, str]:
    """The one whole-path text of `port`'s end, `(head, tail)`: `("+EXT-M1", ":U1")`.

    Head: location labels below `context`, then the designation naming the end (a strip,
    a device with its connector segment). Tail: the port suffix. Lists print both, the stub whole.
    """
    text = port_designation(model, port, unit=unit)
    rec = ports(model)[port]
    owner = items(model)[functions(model)[rec.function].item]
    tail = ":" + (_own_designation(model, owner.id) if terminal_of(model, owner.id) else rec.name)
    node = effective_placement(model, owner.id, Aspect.LOCATION)
    return _located(
        model, node, end_context(model, owner.id, node, context, unit), text[: -len(tail)]
    ), tail


def stub_far_end(model: Model, port: Id[Port], near: Id[Port] | None = None) -> tuple[str, str]:
    """C21: `port`'s far end as the off stub at `near` names it, below `near`'s place (layout-0121).

    A near end in a unit stands on the unit's page, which states no place: whole path, as for None.
    """
    return far_end(model, port, None if near is None else stub_place(model, near))


def off_stub_line(cable: str, *, north: bool, far: str, ports: Iterable[str]) -> str:
    """One off stub's text, `-W3 → +EXT-M1:U1 U2`: what layout measures and derive prints.

    `cable` is the carrier's `-designation` (empty for none), `far` the far device's product
    designation and `ports` the far end's port tails, each with or without its leading `:`,
    listed in the order given. The arrow points up (`←`) for a stub facing north, else `→`.
    """
    arrow = "←" if north else "→"
    tails = " ".join(port.removeprefix(":") for port in ports)
    return " ".join(part for part in (cable, arrow, f"{far}:{tails}") if part)


def off_stub_text(model: Model, marker: LinkMarker) -> str:
    """What an off stub says: `-W3 → +EXT-M1:U1 U2`, cable, arrow, far device and its ports.

    The one text layout sizes the stub's box from and render prints; stubs of one box read the same.
    The arrow is `←` for a stub facing `Side.N`, else `→`. Raises `ValueError` without `far`.
    """
    if marker.star is not StarKind.OFF or marker.far is None:
        msg = "off_stub_text needs an off stub (star OFF) with a far port"
        raise ValueError(msg)
    cable = "" if marker.carrier is None else "-" + item_designation(model, marker.carrier)
    head, _ = stub_far_end(model, marker.far, marker.port)
    run = [marker]
    if marker.box_x is not None:
        run = sorted(
            (
                other
                for other in layout_of(model, LinkMarker).values()
                if other.star is StarKind.OFF
                and other.page == marker.page
                and other.box_x == marker.box_x
                and other.y == marker.y
                and other.carrier == marker.carrier
                and stub_far_end(model, cast("Id[Port]", other.far), other.port)[0] == head
            ),
            key=lambda other: (other.x, other.id),
        )
    tails = (stub_far_end(model, cast("Id[Port]", other.far), other.port)[1] for other in run)
    return off_stub_line(cable, north=marker.facing is Side.N, far=head, ports=tails)


def marker_text(model: Model, marker: LinkMarker) -> str:
    """`#n-p<sheet>:<col><row>`, one line per other end of the net; a stub's own line last.

    Read straight from persisted records: every end's position is already resolved and baked
    into `LinkMarker.x`/`.y`/`.page` by the layout pass, so no symbol geometry is needed here.
    `#n` numbers the whole net (`reference_number`, one digest-cached lookup, never rebuilt per
    marker). Each target prints once, in reading order, one line each up to two positions; past
    two, one line names the first target and `+k`, k the other distinct targets (no `+k` when
    there is one; `marker_targets.target_lines`). A plain severed pair, a star reference with
    its branches, a split or apart pair (two mutual branches, no reference) and a reference
    merged with an off stub (named by at least one branch) are the four shapes
    `_reference_group` covers. A pure off stub that no branch names keeps its own text,
    unprefixed and unnumbered. The lead of markers that share one box at a pin (`_boxmates_of`)
    returns every one's own text, joined by `id`. A text layout broke in two (`wrap_at`) is split
    after that many words: the space becomes the line break.
    """
    group = _boxmates_of(model).get(marker.id)
    if group is None:
        text = _own_text(model, marker)
    else:
        text = "\n".join(_own_text(model, one) for one in group)
    if marker.wrap_at is None:
        return text
    words = text.split(" ")
    return " ".join(words[: marker.wrap_at]) + "\n" + " ".join(words[marker.wrap_at :])


def _own_text(model: Model, marker: LinkMarker) -> str:
    """`marker_text` for one marker alone: its reference lines, or its off stub's text."""
    markers = layout_of(model, LinkMarker)
    group = _reference_group(marker, markers, _branches_of(model))
    if group is None:
        return off_stub_text(model, marker)
    ends = sorted(group, key=lambda one: _reading_key(model, layout_of(model, Page), one))
    positions = [_marker_position(model, marker, one) for one in ends if one.id != marker.id]
    lines = target_lines(reference_number(model, marker), positions)
    # D9 F7: the merged stub's own text, last, unprefixed
    return "\n".join(
        [*lines, off_stub_text(model, marker)] if marker.star is StarKind.OFF else lines
    )


def _reference_group(
    marker: LinkMarker,
    markers: Mapping[Id[LinkMarker], LinkMarker],
    branches_of: Mapping[Id[LinkMarker], tuple[LinkMarker, ...]],
) -> tuple[LinkMarker, ...] | None:
    """Every end of `marker`'s own reference net, `marker` included; `None` for a pure stub.

    Shapes: severed pair, star with branches, split pair, reference merged with an off stub.
    A pure off stub (`star is OFF`, no branches) is never counted as a reference.
    """
    if marker.star is None:
        return (marker, markers[marker.partner])
    if marker.star is StarKind.REF:
        return (marker, *branches_of.get(marker.id, ()))
    if marker.star is StarKind.OFF:
        branches = branches_of.get(marker.id, ())
        return (marker, *branches) if branches else None
    hub = markers[marker.partner]  # BRANCH: partner is the hub, or (C17, S21) another BRANCH
    if hub.star is StarKind.BRANCH:
        return (marker, hub)
    return (hub, *branches_of.get(hub.id, ()))


@digest_cached(DIGEST_CACHE_SIZE)
def _branches_of(model: Model) -> Mapping[Id[LinkMarker], tuple[LinkMarker, ...]]:
    """Every `BRANCH` marker, grouped by the hub (a `REF` or a merged `OFF`) its `partner` names.

    Built once per model digest (RW8): `_reference_group` and `reference_number` both read
    this by key instead of scanning every marker each time they need one hub's branches.
    """
    found: dict[Id[LinkMarker], list[LinkMarker]] = defaultdict(list)
    for one in layout_of(model, LinkMarker).values():
        if one.star is StarKind.BRANCH:
            found[one.partner].append(one)
    return {hub: tuple(ones) for hub, ones in found.items()}


@digest_cached(DIGEST_CACHE_SIZE)
def _boxmates_of(model: Model) -> Mapping[Id[LinkMarker], tuple[LinkMarker, ...]]:
    """Each lead that shares its box with mates, to the lead and its mates ordered by `id`.

    Markers with equal page, `x`, `y`, `stub_extra`, `width`, `height`, `vertical` stand at one pin.
    Several leads at one key are not one box and get no entry. Built once per model digest.
    """
    keyed: dict[_PinKey, list[LinkMarker]] = defaultdict(list)
    for one in layout_of(model, LinkMarker).values():
        keyed[one.page, one.x, one.y, one.stub_extra, one.width, one.height, one.vertical].append(
            one
        )
    found: dict[Id[LinkMarker], tuple[LinkMarker, ...]] = {}
    for ones in keyed.values():
        leads = [one for one in ones if one.lead]
        if len(leads) == 1 and len(ones) > 1:
            found[leads[0].id] = tuple(sorted(ones, key=lambda one: one.id))
    return found


def _reading_key(model: Model, pages: Mapping[Id[Page], Page], marker: LinkMarker) -> _ReadingKey:
    """D1's reading order for one marker's own end: `(page.number, column, row, port)`."""
    page = pages[marker.page]
    sheet = sheet_format_of(model, page.sheet_format)
    column = frame_column(_content_width_grid(sheet), sheet.frame_columns, marker.x)
    row = frame_row(_content_height_grid(sheet), sheet.frame_rows, marker.y)
    return (page.number, column, row, marker.port)


def _reference_groups(
    markers: Mapping[Id[LinkMarker], LinkMarker],
    branches_of: Mapping[Id[LinkMarker], tuple[LinkMarker, ...]],
) -> list[tuple[LinkMarker, ...]]:
    """Every reference group in the whole model, once each (a pure off stub excluded).

    Global, not per drawing set: a severed pair's two ends can stand in two sets, found by id.
    Grouping one set's markers first would leave such a partner unresolved.
    """
    seen: set[Id[LinkMarker]] = set()
    groups: list[tuple[LinkMarker, ...]] = []
    for marker in markers.values():
        if marker.id in seen:
            continue
        group = _reference_group(marker, markers, branches_of)
        if group is None:
            continue
        seen.update(one.id for one in group)
        groups.append(group)
    return groups


def _rank_drawing_set(
    model: Model, groups: list[tuple[LinkMarker, ...]], pages: Mapping[Id[Page], Page]
) -> dict[Id[LinkMarker], int]:
    """One drawing set's `#n`s: every reference group's 1-based rank by its own first end.

    `groups` are those assigned to this set, so the count runs through one drawing.
    Called once per set by `_reference_numbers`, never per marker (a count test catches it).
    """
    ranked = sorted(groups, key=lambda group: min(_reading_key(model, pages, one) for one in group))
    return {one.id: rank for rank, group in enumerate(ranked, start=1) for one in group}


@digest_cached(DIGEST_CACHE_SIZE)
def _reference_numbers(model: Model) -> Mapping[Id[LinkMarker], int]:
    """The `#n` map, every reference marker to its rank, built once per model digest.

    Groups are found once globally, then ranked in the drawing set of each one's own first end.
    A group spanning two sets is numbered in that set, so every member still carries one number.
    """
    markers = layout_of(model, LinkMarker)
    pages = layout_of(model, Page)
    branches_of = _branches_of(model)
    groups = _reference_groups(markers, branches_of)
    by_set: dict[Id[DrawingSet], list[tuple[LinkMarker, ...]]] = defaultdict(list)
    for group in groups:
        first = min(group, key=lambda one: _reading_key(model, pages, one))
        by_set[pages[first.page].drawing_set].append(group)
    numbers: dict[Id[LinkMarker], int] = {}
    for set_groups in by_set.values():
        numbers.update(_rank_drawing_set(model, set_groups, pages))
    return numbers


def reference_number(model: Model, marker: LinkMarker) -> int:
    """LD3's `#n` for `marker`'s reference net (RW8: one lookup into the per-digest map)."""
    return _reference_numbers(model)[marker.id]


def partner_position_text(own: Seat, partner: Seat, column: int, row: str) -> str:
    """A partner's position as `own` reads it, on plain values (LD5, RW9).

    A seat is (set number, page, location path). The same set prints the cell, `own`'s page
    kept (model-0136); another adds the prefix below the common ancestor (U7), else its set
    number (C18). The one place that text is built.
    """
    (own_set, own_page, own_path), (set_number, page, path) = own, partner
    if own_set == set_number:
        return position_text(page, column, row, (), own_page=own_page)
    return position_text(page, column, row, location_prefix(own_path, path), set_number)


def _seat(model: Model, page: Page) -> Seat:
    """`page` as a `Seat`: its drawing set's number, its number and its location path."""
    drawing_set = layout_of(model, DrawingSet)[page.drawing_set]
    return drawing_set.number, page.number, location_path(model, drawing_set.location)


def _position_between(model: Model, own_page: Page, partner_page: Page, x: int, row: str) -> str:
    """The position at `x`/`row` on `partner_page`, read from `own_page` (LD5): the lookups."""
    sheet = sheet_format_of(model, partner_page.sheet_format)
    column = frame_column(_content_width_grid(sheet), sheet.frame_columns, x)
    return partner_position_text(_seat(model, own_page), _seat(model, partner_page), column, row)


def _marker_position(model: Model, marker: LinkMarker, partner: LinkMarker) -> str:
    """`partner`'s position, with its location label across drawing sets (LD5)."""
    pages = layout_of(model, Page)
    partner_page = pages[partner.page]
    sheet = sheet_format_of(model, partner_page.sheet_format)
    row = frame_row(_content_height_grid(sheet), sheet.frame_rows, partner.y)
    return _position_between(model, pages[marker.page], partner_page, partner.x, row)


def _partner_row(model: Model, page: Page, port: Id[Port]) -> str:
    """`port`'s function's placement row on `page`, standing in for the function's own `y`.

    Neither partner record stores a `y`, so this is a coarse frame cell, not a precise position.
    It is the function's own placement, not the exact port's, so callers read the same one.
    """
    function = ports(model)[port].function
    placement = _placements_by_function_page(model)[function, page.id]
    sheet = sheet_format_of(model, page.sheet_format)
    return frame_row(_content_height_grid(sheet), sheet.frame_rows, placement.y)


@digest_cached(DIGEST_CACHE_SIZE)
def _placements_by_function_page(
    model: Model,
) -> Mapping[tuple[Id[Function], Id[Page]], SymbolPlacement]:
    """Every `SymbolPlacement`, once, by its function and page: known ambiguous, not raised.

    `(function, page)` is not unique: a replica placement can add a second one on the same page.
    Last write wins, in `layout_of`'s iteration order, so `_partner_row`'s row is never exact.
    """
    return {(one.function, one.page): one for one in layout_of(model, SymbolPlacement).values()}


def cross_reference_text(model: Model, label: Label) -> str:
    """What `label` says about its cross-reference partners.

    Read from the persisted `label.partners`, which carry the `x` and `page` layout resolved.
    Across drawing sets the prefix is the partner's location path below `label`'s; texts dedupe.
    """
    pages = layout_of(model, Page)
    own_page = pages[label.page]
    seen: set[str] = set()
    texts: list[str] = []
    for partner in label.partners:
        partner_page = pages[partner.page]
        row = _partner_row(model, partner_page, partner.port)
        text = _position_between(model, own_page, partner_page, partner.x, row)
        if text not in seen:
            seen.add(text)
            texts.append(text)
    return " ".join(texts)


def item_tag_text(model: Model, item: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """A component's tag on a drawing: its item designation only, "-Q11" (D12, layout-0066).

    The page states the location, unit and groups, so a tag never carries them, in a unit's
    own set (`unit`, unit-relative) and at top level alike. The one
    function every component and strip tag on a drawing is built from.
    """
    return f"-{item_designation(model, item, unit=unit)}"


def tag_text(model: Model, function: Id[Function]) -> str:
    """A TAG label's text: the designation the layout engine used (D2).

    A terminal function's tag is the designation of its lowest-handle port; every other
    function's tag is its item's `item_tag_text`.
    """
    record = functions(model)[function]
    if record.kind is FunctionKind.TERMINAL:
        port_ids = build_indexes(model).ports_by_function.get(function, ())
        return port_designation(model, min(port_ids))
    return item_tag_text(model, record.item)


def wire_label_text(end_a: str, end_b: str) -> str:
    """The text at both ends of a wire, `-B12:96 -Q11:A1` (V8): the join's one home."""
    return f"{end_a} {end_b}"


def wire_text(model: Model, conductor: Id[Conductor], *, unit: Id[Unit] | None = None) -> str:
    """A WIRE label's text via `wire_label_text` (V8); `unit` makes the ends unit-relative."""
    record = conductors(model)[conductor]
    ends = ordered_wire_ends(model, record.a, record.b)
    return wire_label_text(*(port_designation(model, port, unit=unit) for port in ends))


def strip_tag_text(model: Model, function: Id[Function]) -> str:
    """A run's one strip tag: the item designation of the terminal's strip, "-X01" (R6 D1, D12).

    Printed once, left of a run of terminals of one strip (`run_point_text` is each one's own
    point); a unit's own set prints the unit-relative form instead (`unit_tag_text`). A device's
    own terminal (`is_device_terminal`) names the device itself, never the board it is mounted
    on (D12).
    """
    return item_tag_text(model, _strip_item(model, function))


def _strip_item(model: Model, function: Id[Function]) -> Id[Item]:
    """The item `function`'s strip tag names: a strip terminal's `parent`, a device's own item."""
    item = items(model)[functions(model)[function].item]
    if is_device_terminal(model, function):
        return item.id
    return item.parent or item.id


def is_device_terminal(model: Model, function: Id[Function]) -> bool:
    """L2 (designer): a terminal-kind function of an item that is no terminal.

    The item carries no terminal facet: a device's own pass-through terminal such as an
    overload relay's A2.
    """
    record = functions(model)[function]
    return record.kind is FunctionKind.TERMINAL and terminal_of(model, record.item) is None


def run_point_text(model: Model, function: Id[Function]) -> str:
    """A strip terminal's point text in a run, "L2:1".

    The terminal's own `group:index`, the strip's designation left out (`strip_tag_text` prints it).
    A terminal that is no part of a run prints `terminal_designation`, never this.
    """
    return _own_designation(model, functions(model)[function].item)


def point_text(model: Model, function: Id[Function]) -> str:
    """A terminal's point text inside its strip's row.

    A strip terminal's is `run_point_text`, "L2:1"; a device terminal's is its port marking,
    "A2" (L2).
    """
    if is_device_terminal(model, function):
        return port_marking(model, min(build_indexes(model).ports_by_function[function]))
    return run_point_text(model, function)


def _own_unit(model: Model, label: Label) -> Id[Unit] | None:
    """I4 R2: the set's unit, when the function is in its subtree (a nested black box too)."""
    unit = layout_of(model, DrawingSet)[layout_of(model, Page)[label.page].drawing_set].unit
    if unit is None or label.function is None:
        return None
    return unit if functions(model)[label.function].item in unit_items(model, unit) else None


def _pin_view_ports(model: Model, label: Label) -> tuple[Id[Port], ...]:
    """The ports of the function a pin view's `tag.pin` or `tag.conn` label sits on (R7 A).

    Layout writes such a label with its function as the subject, never a port or a conductor.
    """
    function = cast("Id[Function]", label.function)
    return build_indexes(model).ports_by_function.get(function, ())


def _pin_port(model: Model, label: Label) -> Id[Port]:
    """R7 A: the port a `tag.pin.<name>` label names, among its function's ports."""
    name = label.slot.removeprefix("tag.pin.")
    return next(p for p in _pin_view_ports(model, label) if ports(model)[p].name == name)


def _unit_port_tag_text(
    model: Model, handle: Id[Any], port: Port, slot: str, unit: Id[Unit]
) -> str:
    """`unit_tag_text` for a port handle: a terminal's point, or a pin view's connector or pin."""
    if functions(model)[port.function].kind is FunctionKind.TERMINAL:
        return port_designation(model, handle, unit=unit)  # a terminal's point: "X2:0V:3"
    # a pin view: its connector (tag.conn) or pin (tag.pin), as outside a unit set, less the
    # unit's root
    if slot == "tag.conn":
        return connector_designation(model, port.function, unit=unit)
    return port_designation(model, handle, unit=unit)


def unit_tag_text(
    model: Model, handle: Id[Item] | Id[Port] | Id[Function], slot: str, unit: Id[Unit]
) -> str | None:
    """I4 R2: a TAG text as printed in `unit`'s own set, for a stage handle and its slot.

    The handle is a function, a pin view's port or an item view's item; `None` keeps the
    ordinary text (a run's point tag `run_point_text`, a device terminal's port marking).

    A component's tag is its item designation only, "-Q11", below the unit's sole root; the
    page states the location, unit and groups.
    """

    def short(item: Id[Item]) -> str:
        return item_tag_text(model, item, unit=unit)

    if handle.kind == "item":
        return short(cast("Id[Item]", handle))
    port = ports(model).get(cast("Id[Port]", handle))
    if port is not None:
        return _unit_port_tag_text(model, handle, port, slot, unit)
    function = cast("Id[Function]", handle)
    record = functions(model)[function]
    if slot == "tag.strip":  # a terminal row's strip, in the unit's own form
        return short(_strip_item(model, function))
    if slot == "tag.point":  # D12: a run's point text, unit-independent, and a device's marking
        return None
    if record.kind is FunctionKind.TERMINAL:
        # D12: a terminal outside a run prints its full form in the unit's own strip form; a
        # device terminal keeps its ordinary text
        return (
            None
            if is_device_terminal(model, function)
            else terminal_designation(model, record.item, unit=unit)
        )
    return short(record.item)


def _unit_label_text(model: Model, label: Label, unit: Id[Unit]) -> str | None:
    """I4 R2: `label_text`'s TAG text in `unit`'s own set, from the persisted label."""
    if label.slot.startswith("tag.pin."):
        return unit_tag_text(model, _pin_port(model, label), "tag.pin", unit)
    if label.slot == "tag.conn":
        port = min(_pin_view_ports(model, label))
        return unit_tag_text(model, port, "tag.conn", unit)
    return unit_tag_text(model, cast("Id[Function]", label.function), label.slot, unit)


def label_text(model: Model, label: Label) -> str:
    """The text `label` shows, dispatched by its `kind` (D2).

    TAG, MARKING, WIRE and CROSS_REFERENCE are rendered from the model.

    Raises:
        SchemaError: `label` names a subject field that does not match its `kind` (TAG and
            CROSS_REFERENCE want `function`, MARKING wants `port`). A WIRE label always has a
            `conductor`: `Label.__post_init__` enforces it, so this reader trusts it rather
            than checking it again.
    """
    if label.kind is LabelKind.TAG:
        return _tag_label_text(model, label)
    if label.kind is LabelKind.MARKING:
        if label.port is None:
            msg = "a MARKING label has no port"
            raise SchemaError(msg, kind="layout.label", record_id=label.id)
        return marking_text(model, label.port, label.slot)
    if label.kind is LabelKind.WIRE:
        page = layout_of(model, Page)[label.page]
        drawing_set = layout_of(model, DrawingSet)[page.drawing_set]
        return wire_text(model, cast("Id[Conductor]", label.conductor), unit=drawing_set.unit)
    return _cross_reference_label_text(model, label)


def _tag_label_text(model: Model, label: Label) -> str:
    """`label_text` for a TAG label: the unit's own text, else the slot's text (D2)."""
    if label.function is None:
        msg = "a TAG label has no function"
        raise SchemaError(msg, kind="layout.label", record_id=label.id)
    if label.slot == "outline_title":  # I2a: a black box's title, from its item's unit
        return outline_title(model, items(model)[functions(model)[label.function].item].unit)
    unit = _own_unit(model, label)
    if unit is not None:
        own = _unit_label_text(model, label, unit)  # I4 R2: the unit's own set
        if own is not None:
            return own
    return _tag_slot_text(model, label, label.function)


def _tag_slot_text(model: Model, label: Label, function: Id[Function]) -> str:
    """`label_text` for a TAG label outside a unit's own set, by its slot."""
    if label.slot.startswith("tag.pin."):  # R7 A: one pin of a connector
        return port_designation(model, _pin_port(model, label))
    if label.slot == "tag.strip":
        return strip_tag_text(model, function)
    if label.slot == "tag.item":  # C13(a): a mixed-kind row of one item, its item's tag
        return item_tag_text(model, functions(model)[function].item)
    if label.slot == "tag.conn":  # R7 A5: a pin row's one connector designation (model-0073)
        return connector_designation(model, function)
    if label.slot == "tag.point":
        return point_text(model, function)
    return tag_text(model, function)


def _cross_reference_label_text(model: Model, label: Label) -> str:
    """`label_text` for a CROSS_REFERENCE label: the contact image or the position text (D2)."""
    if label.function is None:
        msg = "a CROSS_REFERENCE label has no function"
        raise SchemaError(msg, kind="layout.label", record_id=label.id)
    if label.slot == "contacts":  # C19: the contact image, one line per row
        no, nc = contact_image(model, label)
        rows = max(len(no), len(nc))
        cells = [
            ("NO", "NC"),
            *zip(no + [""] * (rows - len(no)), nc + [""] * (rows - len(nc)), strict=True),
        ]
        return "\n".join(f"{a} | {b}" for a, b in cells)
    return cross_reference_text(model, label)


def external_note() -> str:
    """The note an external item's designations carry wherever they are drawn or listed.

    Y3's own name, first reserved for a schematic symbol's label (external-items spec Y3,
    not yet built) and now also the cable table's heading line (cable-tables spec CT3,
    decision model-0112): one text, "by others", so a future consumer never invents its own
    wording. Takes no argument: `derive.external` decides WHICH item is covered, this
    decides only what the note SAYS.
    """
    return "by others"


def unit_label(model: Model, unit: Id[Unit]) -> str:
    """What a drawing, a cover or a title block prints for a unit (decision model-0066).

    The unit's release title (`derive.unit_release`), else its name when the title is empty.
    """
    release = unit_release(model, unit)
    return release.title or release.name


def outline_title(model: Model, unit: Id[Unit] | None) -> str:
    """A black box's title: `"<unit label> rev <revision_text>"`, `"Pump rev 1.1"` (model-0066)."""
    if unit is None:
        msg = "an outline title needs a unit"
        raise SchemaError(msg, kind="unit")
    release = unit_release(model, unit)
    return f"{unit_label(model, unit)} rev {revision_text(release.version, release.revision)}"


def contact_image(model: Model, label: Label) -> tuple[list[str], list[str]]:
    """C19: a coil's contact image, its NO and NC entries.

    Per contact of the coil's item, its terminal pairs by number ("13-14", the "/L1" suffixes
    stripped) and where it is drawn ("/3.7"); main contacts (more than one pair) first, then
    by terminal number. A changeover's entries come from its throw roles (`changeover_throws`),
    the names as printed, named commons after numbered ones (CS5). A contact no conductor reaches
    is listed too, its pair and `NO_PLACE`, whatever `hide_unused_pins` says (V1).
    """
    pages = layout_of(model, Page)
    own_page = pages[label.page]
    no, nc = list[Entry](), list[Entry]()
    for partner in label.partners:
        function = functions(model)[ports(model)[partner.port].function]
        where = _position_between(
            model,
            own_page,
            pages[partner.page],
            partner.x,
            _partner_row(model, pages[partner.page], partner.port),
        )
        no_marks, nc_marks = contact_entries(model, function)
        no.extend((main, key, f"{mark} {where}") for main, key, mark in no_marks)
        nc.extend((main, key, f"{mark} {where}") for main, key, mark in nc_marks)
    shown = {ports(model)[partner.port].function for partner in label.partners}
    spare_no, spare_nc = spare_entries(
        model, functions(model)[cast("Id[Function]", label.function)].item, shown
    )
    return [text for *_, text in sorted(no + spare_no, key=image_order)], [
        text for *_, text in sorted(nc + spare_nc, key=image_order)
    ]


def contact_marks(model: Model, function: Id[Function]) -> tuple[list[str], list[str]]:
    """C19: the terminal pairs one contact function lists under NO and under NC, in image order.

    The marks of `contact_image` before the place is appended ("13-14", "COM-NO"): the one rule
    of which pairs a contact prints and in which column, so layout sizes a contact image over
    exactly the entries render prints.
    """
    no, nc = contact_entries(model, functions(model)[function])
    return [mark for *_, mark in sorted(no, key=image_order)], [
        mark for *_, mark in sorted(nc, key=image_order)
    ]


def page_title_groups(model: Model, page: Page) -> tuple[PageGroup, ...]:
    """Which of `page.groups` title `page` (RW1, model-0097).

    A unit's own groups only, when the page's drawing set has a unit; every group, unfiltered,
    when the set has no unit (a location-subject page). `page_title` calls this; RW1 Part 3
    points `fransys_pdf`'s `_page_title_labels` at it too, so the rule has one home (root
    CLAUDE.md, "one rule computed in two places").
    """
    unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    if unit is None:
        return page.groups
    own = own_nodes(model, unit)
    return tuple(group for group in page.groups if group.group in own)


def page_title(model: Model, page: Page) -> str:
    """The page's title: its groups' descriptions, in `index` order, joined by `', '` (D2).

    `page.groups` is already stored in `index` order (`Page.__post_init__`). In a unit's own
    set only the unit's own groups title a page (L3, by R2; `own_nodes` decides via
    `page_title_groups`, and an item of no unit never un-owns a function group, F9); with
    none, the unit's title, its name when the title is empty (`unit_label`, model-0066).
    """
    nodes = aspect_nodes(model)
    unit = layout_of(model, DrawingSet)[page.drawing_set].unit
    titles = [nodes[group.group].description for group in page_title_groups(model, page)]
    if unit is None:
        return ", ".join(titles)
    return ", ".join(titles) or unit_label(model, unit)


__all__ = [
    "connector_designation",
    "contact_image",
    "contact_marks",
    "content_extent",
    "external_note",
    "frame_column",
    "frame_row",
    "is_device_terminal",
    "item_tag_text",
    "label_text",
    "location_path",
    "location_prefix",
    "marker_lines",
    "marker_text",
    "off_stub_line",
    "outline_title",
    "page_title",
    "page_title_groups",
    "partner_position_text",
    "point_text",
    "port_marking",
    "position_text",
    "row_letter",
    "strip_tag_text",
    "stub_far_end",
    "tag_text",
    "unit_label",
    "unit_tag_text",
]
