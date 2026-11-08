"""A link marker with many targets prints the first and a count (owner 2026-10-05, model-0139).

A marker names the other ends of its net. Up to `FULL_TARGETS` it prints each, one line each.
Past that it prints one line, the first target and `+n` more distinct ones, so its box stays
one line wide; derive prints with `target_lines`.
The first of them is a terminal of the net when it has one (`target_order`, model-0235).
"""

from typing import TYPE_CHECKING
lazy from collections.abc import Collection, Sequence

from fransys_model.derive.facts.house_settings import frame_form_of, reference_text_of
from fransys_model.derive.frame_labels import cell_labels
from fransys_model.derive.frame_position import position_text, row_letter
from fransys_model.derive.kinds import item_role
from fransys_model.derive.order import widest_text
from fransys_model.vocab.tables import documents, functions, ports
lazy from fransys_model.derive.document_subject import scope_path, widest_scope
lazy from fransys_model.derive.page_reference_text import front_pages
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document

if TYPE_CHECKING:
    from fransys_model.layout import LinkMarker, ReferenceText

FULL_TARGETS = 2


def more_text(others: int) -> str:
    """The ` +k` a marker prints after its first target, `k` the other distinct ends."""
    return f" +{others}"


def target_lines(number: int, positions: Sequence[str]) -> list[str]:
    """`#n-<position>` per distinct target, or the first (reading order) and `+<k>`."""
    distinct = list(dict.fromkeys(positions))
    if len(positions) <= FULL_TARGETS:
        return [f"#{number}-{position}" for position in distinct]
    more = more_text(len(distinct) - 1) if len(distinct) > 1 else ""
    return [f"#{number}-{distinct[0]}{more}"]


def target_order(model: Model, marker: LinkMarker, ends: Sequence[LinkMarker]) -> list[LinkMarker]:
    """The other ends of `marker`'s net, `ends` in reading order less `marker`; a terminal first.

    Past `FULL_TARGETS` only the first prints, so it is the first terminal end when the net has
    one, else the first in reading order. Up to the limit every end prints and the order stays.
    """
    others = [one for one in ends if one.id != marker.id]
    if len(others) <= FULL_TARGETS:
        return others
    terminals = [one for one in others if item_role(model, functions(model)[ports(model)[one.port].function].item).terminal]
    return [*terminals[:1], *(one for one in others if one not in terminals[:1])]


def _wide_page(model: Model, count: int, digit: str) -> int:
    """The widest page number of a build of `count` drawn pages: the front pages count too, every digit `digit`."""
    front = max((front_pages(model, document) for document in documents(model)), default=0)
    return int(digit * len(str(count + front)))


def widest_position_text(model: Model, digits: int, frame: tuple[int, int], digit: str, *, far: Collection[Id[Document]]) -> str:
    """The position text of a placement: a page number of `digits` digits and the cell at the highest `frame` (columns, rows), every one `digit`.

    `far` holds the documents that may print a placement in another PDF (the widest `scope_path` leads the text); empty is the same-PDF text.
    Layout sizes a terminal's where-text with it before the pages exist.
    """
    refs, labels = _widest_cells(model, *frame, digit)
    prefixes = [scope_path(model, document) for document in far] or [""]
    return widest_text(position_text(refs, int(digit * digits), labels, prefix) for prefix in prefixes)


def _widest_cells(model: Model, columns: int, rows: int, digit: str) -> tuple[ReferenceText, tuple[str, str]]:
    """The reference text and the frame cell labels at the widest column and row, the one setup both widest lines read."""
    return reference_text_of(model), cell_labels(frame_form_of(model), rows, int(digit * len(str(columns))), row_letter(rows - 1))


def widest_target_line(model: Model, count: int, columns: int, rows: int, digit: str) -> str:
    """The longest line a marker can print: `target_lines`' `+k` form with every number `digit`s.

    `count` is the build's symbol count, `columns` and `rows` the highest frame column and row,
    `digit` the widest digit the caller measured. Layout sizes a marker box with it before the pages exist.
    """
    refs, labels = _widest_cells(model, columns, rows, digit)
    wide = _wide_page(model, count, digit)
    position = position_text(refs, wide, labels, widest_scope(model))
    return target_lines(wide, [position])[0] + more_text(int(digit))
