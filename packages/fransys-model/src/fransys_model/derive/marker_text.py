"""A link marker's printed text and its `#n` reference number (decision model-0032)."""

from collections import defaultdict
lazy from collections.abc import Mapping

from fransys_model.derive.marker_targets import target_lines, target_order
from fransys_model.derive.page_reference_text import position_at
from fransys_model.derive.reference_heads import heads_group
from fransys_model.derive.stub_text import off_stub_text
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, SchemaError, digest_cached, render_id
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Membership,
    Page,
    Shown,
    StarKind,
    layout_of,
)
from fransys_model.vocab.core import Port

# A reading key.
type _ReadingKey = tuple[int, int, str, Id[Port]]


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
    unprefixed and unnumbered.
    """
    return "\n".join(line for line, _ in _own_text(model, marker))


def marker_line_targets(model: Model, marker: LinkMarker) -> tuple[LinkMarker | None, ...]:
    """The end each printed line of `marker`'s box names, `None` for a line that names none (a stub's own text).

    One entry per line of `marker_text`. Read
    from the lines `marker_text` prints, so a line and its target cannot drift (PDF-LINKS R2).
    """
    return tuple(end for _, end in _own_text(model, marker))


def _own_text(model: Model, marker: LinkMarker) -> list[tuple[str, LinkMarker | None]]:
    """`marker` alone: each reference line with its first end, or its off stub's text with none."""
    markers = layout_of(model, LinkMarker)
    group = _reference_group(marker, markers, _branches_of(model))
    if group is None:
        return _stub_lines(model, marker)
    ends = sorted(group, key=lambda one: _reading_key(model, layout_of(model, Page), one))
    first: dict[str, LinkMarker] = {}
    positions = []
    for end in target_order(model, marker, ends):
        positions.append(_marker_position(model, marker, end))
        first.setdefault(positions[-1], end)
    lines: list[tuple[str, LinkMarker | None]] = list(zip(target_lines(reference_number(model, marker), positions), first.values(), strict=False))
    # the merged stub's own text, last, unprefixed
    return [*lines, *_stub_lines(model, marker)] if marker.star is StarKind.OFF else lines


def _stub_lines(model: Model, marker: LinkMarker) -> list[tuple[str, LinkMarker | None]]:
    """The lines of `marker`'s off stub text, each naming no end."""
    return [(line, None) for line in off_stub_text(model, marker).split("\n")]


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
    hub = markers[marker.partner]  # BRANCH: partner is the hub, or another BRANCH
    if hub.star is StarKind.BRANCH:
        return (marker, hub)
    return (hub, *branches_of.get(hub.id, ()))


@digest_cached(DIGEST_CACHE_SIZE)
def _branches_of(model: Model) -> Mapping[Id[LinkMarker], tuple[LinkMarker, ...]]:
    """Every `BRANCH` marker, grouped by the hub (a `REF` or a merged `OFF`) its `partner` names.

    Built once per model digest: `_reference_group` and `reference_number` both read
    this by key instead of scanning every marker each time they need one hub's branches.
    """
    found: dict[Id[LinkMarker], list[LinkMarker]] = defaultdict(list)
    for one in layout_of(model, LinkMarker).values():
        if one.star is StarKind.BRANCH:
            found[one.partner].append(one)
    return {hub: tuple(ones) for hub, ones in found.items()}


@digest_cached(DIGEST_CACHE_SIZE)
def _reference_cells(model: Model) -> Mapping[tuple[Id[Page], str], tuple[int, str]]:
    """Each reference marker's stored cell by its page and marker id, from the `Membership` rows el wrote.

    A marker's row key ends `ref`, the marker's rendered id, the port and the page number (`write_membership`).
    """
    return {
        (row.page, row.key[-3]): (row.cell.column, row.cell.row)
        for row in layout_of(model, Membership).values()
        if row.shown is Shown.REFERENCE and row.port is not None and row.page is not None
    }


def marker_cell(model: Model, marker: LinkMarker) -> tuple[int, str]:
    """The frame cell `(column, row letter)` of `marker`: the stored cell of its `Membership` row, never computed.

    Raises when the model holds no such row (a layout el wrote carries one for every marker).
    """
    try:
        return _reference_cells(model)[marker.page, render_id(marker.id)]
    except KeyError:
        msg = f"marker {render_id(marker.id)} has no reference Membership row: write the layout through fransys_el"
        raise SchemaError(msg, kind="layout.membership", record_id=marker.id) from None


def _reading_key(model: Model, pages: Mapping[Id[Page], Page], marker: LinkMarker) -> _ReadingKey:
    """The reading order for one marker's own end: `(page.number, column, row, port)`."""
    return (
        pages[marker.page].number,
        *marker_cell(model, marker),
        marker.port,
    )


def _reference_groups(
    markers: Mapping[Id[LinkMarker], LinkMarker],
    branches_of: Mapping[Id[LinkMarker], tuple[LinkMarker, ...]],
) -> list[tuple[LinkMarker, ...]]:
    """Every reference group in the whole model, once each, its head first (`heads_group`).

    Global, not per drawing set: a severed pair's two ends can stand in two sets, found by id.
    A group belongs to its head's set (layout-0132), the set layout counted it in.
    """
    groups: list[tuple[LinkMarker, ...]] = []
    for marker in markers.values():
        star = marker.star.value if marker.star else ""
        if not heads_group(star, marker.side.value, named=marker.id in branches_of):
            continue
        group = _reference_group(marker, markers, branches_of)
        if group is not None:
            groups.append((marker, *(one for one in group if one.id != marker.id)))
    return groups


def _rank_drawing_set(model: Model, groups: list[tuple[LinkMarker, ...]], pages: Mapping[Id[Page], Page]) -> dict[Id[LinkMarker], int]:
    """One drawing set's `#n`s: every reference group's 1-based rank by its own first end.

    `groups` are those assigned to this set, so the count runs through one drawing.
    Called once per set by `_reference_numbers`, never per marker (a count test catches it).
    """
    ranked = sorted(groups, key=lambda group: min(_reading_key(model, pages, one) for one in group))
    return {one.id: rank for rank, group in enumerate(ranked, start=1) for one in group}


@digest_cached(DIGEST_CACHE_SIZE)
def _reference_numbers(model: Model) -> Mapping[Id[LinkMarker], int]:
    """The `#n` map, every reference marker to its rank, built once per model digest.

    Groups are found once globally, then ranked in the drawing set of each one's head.
    A group spanning two sets is numbered in its head's set, so every member carries one number.
    """
    markers = layout_of(model, LinkMarker)
    pages = layout_of(model, Page)
    branches_of = _branches_of(model)
    groups = _reference_groups(markers, branches_of)
    by_set: dict[Id[DrawingSet], list[tuple[LinkMarker, ...]]] = defaultdict(list)
    for group in groups:
        by_set[pages[group[0].page].drawing_set].append(group)
    numbers: dict[Id[LinkMarker], int] = {}
    for set_groups in by_set.values():
        numbers.update(_rank_drawing_set(model, set_groups, pages))
    return numbers


def reference_number(model: Model, marker: LinkMarker) -> int:
    """The `#n` for `marker`'s reference net (one lookup into the per-digest map)."""
    return _reference_numbers(model)[marker.id]


REF_SLOTS = 8  # the number of colour slots a net reference cycles through (model-0255)


def reference_slot(model: Model, marker: LinkMarker) -> int | None:
    """The colour slot of `marker`'s net reference, `(#n - 1) % REF_SLOTS`; `None` without a `#n`.

    A pure off stub that no branch names has no `#n`, so it reads the map by `.get`.
    """
    number = _reference_numbers(model).get(marker.id)
    return None if number is None else (number - 1) % REF_SLOTS


@digest_cached(DIGEST_CACHE_SIZE)
def reference_targets(model: Model) -> Mapping[tuple[Id[Page], tuple[int, str]], tuple[tuple[Id[LinkMarker], int, frozenset[Id[Port]], str], ...]]:
    """Each reference marker's stored `(column, row letter)` on its page, to the candidate ends standing there.

    A candidate end is the marker's id, its `#n`, the ports of its whole reference group and the text its box
    draws, so a reader who finds a drawn marker by page, cell
    and text knows which markers are the same reference.
    Page numbers restart per drawing set, so the key is the page's id, never a printed `#n`.
    """
    markers, branches = layout_of(model, LinkMarker), _branches_of(model)
    found: dict[tuple[Id[Page], tuple[int, str]], list[tuple[Id[LinkMarker], int, frozenset[Id[Port]], str]]] = defaultdict(list)
    for marker in markers.values():
        if (group := _reference_group(marker, markers, branches)) is not None:
            found[marker.page, marker_cell(model, marker)].append(
                (marker.id, reference_number(model, marker), frozenset(one.port for one in group), marker_text(model, marker))
            )
    return {key: tuple(ends) for key, ends in found.items()}


def _marker_position(model: Model, marker: LinkMarker, partner: LinkMarker) -> str:
    """`partner`'s position, with its location label across drawing sets."""
    pages = layout_of(model, Page)
    return position_at(model, pages[marker.page], pages[partner.page], *marker_cell(model, partner))
