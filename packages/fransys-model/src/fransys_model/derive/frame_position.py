"""Printed positions: the frame grid, a location path and a partner's place (model-0032)."""

lazy from decimal import Decimal

from fransys_model.derive.facts.house_settings import frame_form_of, reference_text_of
from fransys_model.derive.frame_labels import cell_labels
from fransys_model.derive.placement_reads import node_label
from fransys_model.derive.set_rank import set_rank
from fransys_model.derive.sheet_forms import set_page_text
from fransys_model.derive.unit_nodes import chain_up
from fransys_model.kernel import Id, Model
from fransys_model.layout import (
    DrawingSet,
    Page,
    ReferenceText,
    layout_of,
    sheet_format_of,
)
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.tables import aspect_nodes

# A location's root-to-leaf path: each node's identity paired with its own label, root first
# (the units rule). The identity half is what a nearest-common-ancestor walk compares -- never
# the label, so two nodes that happen to share label text at different tree positions are
# never mistaken for one.
type LocationPath = tuple[tuple[Id[AspectNode], str], ...]
type Seat = tuple[int, int, LocationPath]


def row_letter(index: int) -> str:
    """The letter for a 0-based frame-grid row index, A first.

    This is the canonical row a membership stores; `frame_labels.cell_labels` names it for print.
    """
    return chr(ord("A") + index)


def position_text(
    refs: ReferenceText,
    page_number: int,
    labels: tuple[str, str] | None,
    location_labels: tuple[str, ...],
    set_number: int | None = None,
) -> str:
    """`p<page_number>:<column><row>`, prefixed by `+<label>` for each of `location_labels`.

    The one form for every printed position; `labels` is `cell_labels`' printed (column, row), its
    signs and its `p` are `refs`. A caller passes `()` for `location_labels` in the same set.
    With no `labels` it names the page alone,
    `p3`: a finding about a whole page.
    """
    cell = "" if labels is None else "".join(labels)
    if cell:
        cell = refs.cell_sep + cell
    if not location_labels and set_number is not None:
        # A place in another drawing set with no location
        # prefix still names its set, "p3.2:1A" (set.page, then cell), so it is never ambiguous
        return f"{refs.page_prefix}{set_page_text(refs, set_number, page_number)}{cell}"
    prefix = "".join(f"{refs.location_sign}{label}" for label in location_labels)
    return f"{prefix}{refs.page_prefix}{page_number}{cell}"


def location_prefix(own_path: LocationPath, partner_path: LocationPath) -> tuple[str, ...]:
    """The partner's location labels below the nearest common ancestor, root first.

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


# KI-259 (piece SYM-1c1): kept for pdf `_cable_checks`, which takes its room from the facade's SY5 value after c1.
def content_extent(millimetres: int | Decimal, mm_per_division: Decimal) -> int:
    """Whole grid units that fit in `millimetres`: `floor(mm / mm_per_division)`.

    Sheet sizes are not multiples of G (297 mm is 950.4 G), so a sheet format stores integer
    millimetres and this is the one place they become grid units. Decimal `//` truncates toward
    zero, which is the floor for the positive size of a sheet.
    """
    return int(millimetres // mm_per_division)


def location_path(model: Model, node: Id[AspectNode] | None) -> LocationPath:
    """`node`'s root-to-leaf path, empty for `None` (no location).

    The one walk is `kernel.parent_chain` (via `chain_up`), reversed to root first, with each
    node's label kept alongside its id. Every location text is built from it.
    """
    nodes = aspect_nodes(model)
    return tuple((found, node_label(model, found)) for found in reversed(list(chain_up(nodes, node))))


def partner_position_text(
    refs: ReferenceText,
    own: Seat,
    partner: Seat,
    labels: tuple[str, str],
    *,
    same_set: bool | None = None,
) -> str:
    """A partner's position as `own` reads it, on plain values.

    A seat is (set number, page, location path). The same set prints the cell, `own`'s page
    kept (model-0136); another adds the prefix below the common ancestor, else its set
    number. The one place that text is built. `same_set` says it when the seats hold ranks,
    which two sets of different units share. `labels` is the printed (column, row).
    """
    (own_set, own_page, own_path), (set_number, page, path) = own, partner
    if own_set == set_number if same_set is None else same_set:
        cell = "".join(labels)
        return cell if own_page == page and cell else position_text(refs, page, labels, ())
    return position_text(refs, page, labels, location_prefix(own_path, path), set_number)


def _seat(model: Model, page: Page) -> Seat:
    """`page` as a `Seat`: its drawing set's rank, its number and its location path."""
    drawing_set = layout_of(model, DrawingSet)[page.drawing_set]
    return set_rank(model, page), page.number, location_path(model, drawing_set.location)


def position_at(model: Model, own_page: Page, partner_page: Page, column: int, row: str) -> str:
    """The printed position of frame cell (`column`, `row letter`) on `partner_page`, as a reader of `own_page` sees it.

    The cell alone on the same page, `p<page>:<cell>` in the same drawing set, and with the set number or the
    location prefix below the common ancestor across sets. It is the one place a partner's position is printed;
    a reference marker and a copied terminal's where-text both call it. Compare a drawn text with this value by
    recomputing it, never by parsing the printed text.
    """
    rows = sheet_format_of(model, partner_page.sheet_format).frame_rows
    labels = cell_labels(frame_form_of(model), rows, column, row)
    same = own_page.drawing_set == partner_page.drawing_set
    seats = _seat(model, own_page), _seat(model, partner_page)
    return partner_position_text(reference_text_of(model), *seats, labels, same_set=same)
