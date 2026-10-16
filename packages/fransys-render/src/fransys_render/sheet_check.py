"""The title-block findings: no room, a label over its value, a field or the notice that misses."""

from typing import TYPE_CHECKING

from electrical_symbols import TITLE_BLOCK_MIN_BAND_MM, TITLE_BLOCK_MIN_WIDTH_MM
from fransys_model.derive import (
    notice_room_chars,
    notice_unfit,
    title_block_overflows,
)
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import documents

from ._sheet_draw import notice_room, title_rooms, title_symbol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import DocumentSheets, SheetFrame, Sizes
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Document

__all__ = ["sheet_check"]


def _no_room(subject: Id[Document], name: str, frame: SheetFrame) -> Finding | None:
    if frame.band < TITLE_BLOCK_MIN_BAND_MM:
        short = f"title-block band {int(frame.band)}mm, under the required 20mm"
    elif frame.title_width < TITLE_BLOCK_MIN_WIDTH_MM:
        short = f"title block {frame.title_width:g}mm wide, under the required "
        short += f"{TITLE_BLOCK_MIN_WIDTH_MM:g}mm"
    else:
        return None
    return Finding(
        code="TITLE_BLOCK_NO_ROOM",
        severity=Severity.WARNING,
        subjects=(subject,),
        message=f"sheet format {name!r}: {short}",
    )


def _stack_overlap(subject: Id[Document], name: str, band: float, sizes: Sizes) -> Finding | None:
    """An ERROR when the band is under `sizes.title_band_mm`, where label and value clear."""
    if band >= sizes.title_band_mm:
        return None
    return Finding(
        code="TITLE_BLOCK_STACK_OVERLAP",
        severity=Severity.ERROR,
        subjects=(subject,),
        message=(
            f"sheet format {name!r}: the title-block band is {band:g} mm and the text height "
            f"needs at least {sizes.title_band_mm:g} mm; use a sheet format whose title-block "
            "band is at least that height, or the house text height"
        ),
    )


def _overflow(subject: Id[Document], field: str, where: str, shown: str) -> Finding:
    remedy = "; set a shorter title with d.layout.page_title" if field == "page_title" else ""
    return Finding(
        code="TITLE_BLOCK_TEXT_OVERFLOW",
        severity=Severity.WARNING,
        subjects=(subject,),
        message=(
            f"{field} ({where}): {shown!r} does not fit its title-block cell, cut with '…'{remedy}"
        ),
    )


def _notice(subject: Id[Document], chars: int) -> Finding:
    return Finding(
        code="TITLE_BLOCK_NOTICE_OVERFLOW",
        severity=Severity.WARNING,
        subjects=(subject,),
        message=(
            "the notice does not fit the title block's notice cell, cut; "
            f"the cell holds about {chars} characters; shorten fr.document(notice=...)"
        ),
    )


def _document_findings(
    model: Model, subject: Id[Document], listing: DocumentSheets
) -> tuple[list[Finding], bool]:
    """A document's no-room or text-overflow findings, and whether its notice misses its cell."""
    frame = listing.frames[listing.sheet.id]
    if (short := _no_room(subject, listing.sheet.name, frame)) is not None:
        return [short], False
    record = documents(model)[subject]
    sizes = listing.sizes
    block = title_symbol(frame, notice=bool(record.notice))
    found = title_block_overflows(model, subject, listing, title_rooms(block))
    findings = [_overflow(subject, o.field, o.where, o.shown) for o in found]
    if (stack := _stack_overlap(subject, listing.sheet.name, frame.band, sizes)) is not None:
        findings.append(stack)
    width, capacity = notice_room(block, sizes)
    unfit = bool(record.notice) and notice_unfit(
        record.notice, width_mm=width, font_mm=sizes.label, capacity=capacity
    )
    return findings, unfit


def sheet_check(
    model: Model, listings: Mapping[Id[Document], DocumentSheets]
) -> tuple[Finding, ...]:
    """Every title-block problem of every `Document`, sorted (render-0019).

    `listings` is `derive.document_sheets_of(model)`, the values `sheets` draws from.

    The codes: `TITLE_BLOCK_NO_ROOM`, `TITLE_BLOCK_STACK_OVERLAP`, `TITLE_BLOCK_TEXT_OVERFLOW` and
    `TITLE_BLOCK_NOTICE_OVERFLOW`.

    The notice finding names the first document whose notice misses its cell, as it always has.
    Pure.
    """
    found: list[Finding] = []
    notice: Finding | None = None
    for subject, listing in listings.items():
        findings, unfit = _document_findings(model, subject, listing)
        found.extend(findings)
        if unfit and notice is None:
            block = title_symbol(listing.frames[listing.sheet.id], notice=True)
            width, capacity = notice_room(block, listing.sizes)
            chars = notice_room_chars(width, font_mm=listing.sizes.label, capacity=capacity)
            notice = _notice(subject, chars)
    if notice is not None:
        found.append(notice)
    return tuple(sorted(found, key=lambda one: (one.code, one.subjects, one.message)))
