"""Printed positions: the frame grid and a partner's place (model-0032, model-0436)."""

lazy from decimal import Decimal

lazy from fransys_model.layout import ReferenceText


def row_letter(index: int) -> str:
    """The letter for a 0-based frame-grid row index, A first.

    This is the canonical row a membership stores; `frame_labels.cell_labels` names it for print.
    """
    return chr(ord("A") + index)


def position_text(refs: ReferenceText, page_number: int, labels: tuple[str, str] | None, prefix: str = "") -> str:
    """`p<page_number>:<column><row>`, led by `prefix` and a space when the page is in another PDF.

    The one form for every printed position (model-0436); `labels` is `cell_labels`' printed
    (column, row), its signs and its `p` are `refs`. With no `labels` it names the page alone,
    `p3`: a finding about a whole page. `prefix` is the far document's `scope_path`, `""` in the same PDF.
    """
    cell = "" if labels is None else "".join(labels)
    text = f"{refs.page_prefix}{page_number}{refs.cell_sep + cell if cell else ''}"
    return f"{prefix} {text}" if prefix else text


# KI-259 (piece SYM-1c1): kept for pdf `_cable_checks`, which takes its room from the facade's SY5 value after c1.
def content_extent(millimetres: int | Decimal, mm_per_division: Decimal) -> int:
    """Whole grid units that fit in `millimetres`: `floor(mm / mm_per_division)`.

    Sheet sizes are not multiples of G (297 mm is 950.4 G), so a sheet format stores integer
    millimetres and this is the one place they become grid units. Decimal `//` truncates toward
    zero, which is the floor for the positive size of a sheet.
    """
    return int(millimetres // mm_per_division)


def partner_position_text(refs: ReferenceText, own_page: int, partner_page: int, labels: tuple[str, str], prefix: str = "") -> str:
    """A partner's position as the page numbered `own_page` reads it, on plain values.

    The cell alone on the same page, `p<page>:<cell>` on another page of the same PDF, and `prefix`
    first when the partner is in another PDF. The one place that text is built.
    """
    cell = "".join(labels)
    if not prefix and own_page == partner_page and cell:
        return cell
    return position_text(refs, partner_page, labels, prefix)
