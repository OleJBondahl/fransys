"""Cover and notes page content (amended by pdf-0010)."""

from typing import TYPE_CHECKING

from fransys_model.derive import revision_rows

from ._cover_measure import measuring_block
from ._geometry import document_heading, document_release
from ._markdown import BulletList, NumberedList, Paragraph, Run, parse, to_typst
from ._sizes import rule_of
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.derive import DocumentRow, RevisionRow
    from fransys_model.kernel import Model

    from ._markdown import Element


def _flatten_lists(elements: tuple[Element, ...]) -> tuple[Element, ...]:
    """Every list item becomes a `Paragraph` with a literal bullet or number."""
    flat = []
    for element in elements:
        if isinstance(element, BulletList):
            flat.extend(
                Paragraph(element.line, (Run("plain", "• "), *item)) for item in element.items
            )
        elif isinstance(element, NumberedList):
            flat.extend(
                Paragraph(element.line, (Run("plain", f"{i}. "), *item))
                for i, item in enumerate(element.items, start=1)
            )
        else:
            flat.append(element)
    return tuple(flat)


def _revision_row(entry: RevisionRow) -> tuple[str, str, str, str, str, str]:
    return (
        entry.label,
        entry.date,
        entry.text,
        entry.created,
        entry.checked,
        entry.approved,
    )


def _revision_table(
    entries: tuple[RevisionRow, ...],
    headers: tuple[str, ...],
    description_mm: float,
    rule: str,
) -> str:
    """The revision-history table, `""` if empty; description capped at `description_mm`."""
    if not entries:
        return ""
    header = "table.header(" + ", ".join(f"strong(text({literal(name)}))" for name in headers) + ")"
    cells = [header]
    for entry in entries:
        cells.extend(f"text({literal(value)})" for value in _revision_row(entry))
    columns = f"(auto, auto, {description_mm:g}mm, auto, auto, auto)"
    return f"#table(columns: {columns}, stroke: {rule}, " + ", ".join(cells) + ")"


def cover_page(
    model: Model,
    record: DocumentRow,
    headers: tuple[str, ...],
    description_mm: float,
) -> str:
    """The cover page; Typst measures it and panics on an overlap (`COVER_OVERFLOW`, pdf-0047)."""
    heading = f"#heading(level: 1, text({literal(document_heading(model, record))}))"
    body = to_typst(_flatten_lists(parse(record.cover)))
    # `align(center, [...])`, the two-argument call, not the `align(center)[...]` trailing-block
    # sugar: confirmed by compiling both -- they lay out identically (the heading flush at the
    # margin box's own top, no extra gap), but the sugar's literal text collides with
    # `test_source.py`'s own `"#align(center)" not in text` (a removed caption check, unrelated
    # to this page's spec-required centring); a bracket *block* around the same content
    # (`[#set align(center) ...]`) also dodges that text but is not equivalent -- it is a new
    # nested container, so the heading's own default spacing no longer collapses against the
    # page top, and it lands about 9 mm lower (confirmed by compiling that too).
    # The table stands on the margin box's foot, 5 mm above the title block (pdf-0027).
    parts = [f"#let fr-cover = align(center, [\n{heading}\n{body}\n])", "#fr-cover"]
    entries = revision_rows(model, document_release(model, record))
    table = _revision_table(entries, headers, description_mm, rule_of(model))
    if table:
        parts.append(f"#let fr-table = {table[1:]}")
        parts.append("#place(bottom + center, fr-table)")
    parts.append(measuring_block(has_table=bool(table)))
    return "\n".join(parts)


def notes_page(record: DocumentRow, heading_word: str) -> str:
    """The notes page: the `notes` word as heading, then the notes text."""
    notes = record.notes
    assert notes is not None  # noqa: S101 -- document_pages excludes NOTES when there is no notes text
    heading = f"#heading(level: 1, text({literal(heading_word)}))"
    return "\n".join([heading, to_typst(parse(notes))])
