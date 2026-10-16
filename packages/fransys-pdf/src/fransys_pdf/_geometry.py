"""Page geometry: paper, margins, header, footer, type sizes."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    PRESET_HEADINGS,
    document_facts,
    document_unit,
    subject_label,
    unit_release,
)

from ._labels import ROMAN
from ._sizes import Sizes, font_mm
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.derive import DocumentRow, SheetRow, UnitReleaseId
    from fransys_model.kernel import Model


def document_metadata(model: Model, record: DocumentRow) -> str:
    """`#set document(...)` from `document_facts`; the date is never `auto`."""
    title, _number, _customer, _revision, revision_date, author = document_facts(model, record.id)
    if not revision_date:
        date = "none"
    else:
        year, month, day = (int(part) for part in revision_date.split("-"))
        date = f"datetime(year: {year}, month: {month}, day: {day})"
    return f"#set document(title: {literal(title)}, author: {literal(author)}, date: {date})"


def document_release(model: Model, record: DocumentRow) -> UnitReleaseId | None:
    """The release whose revision history `record` shows: its unit's, `None` for the project's."""
    unit = document_unit(model, record.id)
    if unit is None:
        return None
    return unit_release(model, unit).id


def document_heading(model: Model, record: DocumentRow) -> str:
    """`<preset words> — <subject label>`, the words alone when the label is empty."""
    words = PRESET_HEADINGS[record.preset]
    subject = subject_label(model, record.id)
    if not subject:
        return words
    return f"{words} — {subject}"


def preamble(sizes: Sizes, sheet: SheetRow) -> str:
    """Text, page size and type sizes, once; margin and background are per page kind."""
    return "\n".join(
        [
            f'#set text(font: "DejaVu Sans", size: {font_mm(sizes.body)})',
            f"#set page(width: {sheet.width_mm}mm, height: {sheet.height_mm}mm, {ROMAN})",
            f"#show heading.where(level: 1): set text(size: {font_mm(sizes.heading_1)})",
            f"#show heading.where(level: 2): set text(size: {font_mm(sizes.heading_2)})",
            f"#show heading.where(level: 3): set text(size: {font_mm(sizes.body)})",
            f"#show table: set text(size: {font_mm(sizes.label)})",
        ]
    )


PADDING_MM = 5  # non-drawing pages' inner padding inside the content box


def text_margin(sheet: SheetRow) -> str:
    """A `#set page(margin: ...)`: content box plus 5 mm padding; harness too (pdf-0009)."""
    left = sheet.content_x_mm + PADDING_MM
    top = sheet.content_y_mm + PADDING_MM
    right = (sheet.width_mm - sheet.content_x_mm - sheet.content_width_mm) + PADDING_MM
    bottom = (sheet.height_mm - sheet.content_y_mm - sheet.content_height_mm) + PADDING_MM
    return f"(left: {left}mm, top: {top}mm, right: {right}mm, bottom: {bottom}mm)"
