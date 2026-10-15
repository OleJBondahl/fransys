"""The `TITLE_BLOCK_TEXT_OVERFLOW` findings: each one-line title-block field against its cell."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import document_facts
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import PageKind

from ._drawings import (
    cable_blocks,
    harness_cables_for,
    harness_run_fields,
    schematic_fields,
    schematic_missing_keys,
    schematic_pages,
)
from ._frame import CellContext, TitleBlockFields, field_cell
from ._sizes import Sizes, sizes_of
from .document import _HEADING_WORDS, section_fields

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import SheetFormat
    from fransys_model.vocab import Document

    type _DocId = Id[Document]


_DOCUMENT_LEVEL_ONE_LINE_FIELDS = (
    "title",
    "number",
    "customer",
    "revision",
    "revision_date",
    "author",
)


@dataclass(frozen=True, slots=True)
class _FieldTarget:
    """The document subject and sheet format `_one_line_overflow_finding` checks a field against."""

    subject: _DocId
    sheet: SheetFormat
    sizes: Sizes
    notice: bool = False


def _one_line_overflow_finding(
    target: _FieldTarget, field: str, text: str, *, where: str, shorter: tuple[str, ...]
) -> Finding | None:
    """One `TITLE_BLOCK_TEXT_OVERFLOW` finding if `text` and every `shorter` form miss.

    A page title's message names `d.layout.page_title`, the way to set a title that fits (PT1).
    """
    shown, ok, _printed = field_cell(
        CellContext(target.sheet, target.sizes, target.notice), field, text, shorter=shorter
    )
    if ok:
        return None
    remedy = "; set a shorter title with d.layout.page_title" if field == "page_title" else ""
    return Finding(
        code="TITLE_BLOCK_TEXT_OVERFLOW",
        severity=Severity.WARNING,
        subjects=(target.subject,),
        message=(
            f"{field} ({where}): {shown!r} does not fit its title-block cell, cut with '…'{remedy}"
        ),
    )


def _document_level_overflow_findings(
    model: Model, subject: _DocId, record: Document, sheet: SheetFormat
) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_TEXT_OVERFLOW` for the six document-level fields."""
    title, number, customer, revision, revision_date, author = document_facts(model, record)
    values = {
        "title": title,
        "number": number,
        "customer": customer,
        "revision": revision,
        "revision_date": revision_date,
        "author": author,
    }
    target = _FieldTarget(
        subject=subject, sheet=sheet, sizes=sizes_of(model, record), notice=bool(record.notice)
    )
    findings = []
    for field in _DOCUMENT_LEVEL_ONE_LINE_FIELDS:
        finding = _one_line_overflow_finding(
            target, field, values[field], where="document", shorter=()
        )
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def _page_fields_overflow_findings(
    target: _FieldTarget, pages: tuple[tuple[TitleBlockFields, str], ...], *, kind: str
) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_TEXT_OVERFLOW` for the scope and each page's `(fields, where)`.

    The fields are the very ones the page source prints, from `schematic_fields`,
    `harness_run_fields` and `section_fields`, so this can never disagree with the page.
    """
    if not pages:
        return ()
    findings = [
        _one_line_overflow_finding(target, "scope", pages[0][0].scope, where=kind, shorter=())
    ]
    for fields, where in pages:
        for name, text, shorter in (
            ("page_title", fields.page_title, fields.page_title_shorter),
            ("sheet_counter", fields.sheet_counter, ()),
        ):
            findings.append(
                _one_line_overflow_finding(target, name, text, where=where, shorter=shorter)
            )
    return tuple(finding for finding in findings if finding is not None)


def _page_overflow_findings(
    model: Model,
    target: _FieldTarget,
    record: Document,
    pages: tuple[PageKind, ...],
    svgs: Mapping[str, str],
) -> tuple[Finding, ...]:
    """The page-level fields of `SCHEMATIC`, `HARNESS_DRAWING` and the `_HEADING_WORDS` kinds."""
    found: list[Finding] = []
    schematic = schematic_pages(model, record, pages) if PageKind.SCHEMATIC in pages else ()
    if schematic and not schematic_missing_keys(schematic, svgs):
        fields = schematic_fields(model, record, schematic)
        wheres = tuple(f"page {page.number}" for page in schematic)
        found += _page_fields_overflow_findings(
            target, tuple(zip(fields, wheres, strict=True)), kind="SCHEMATIC"
        )
    cables = harness_cables_for(model, record, pages)
    blocks = cable_blocks(model, record, cables) if PageKind.HARNESS_DRAWING in pages else ()
    runs = harness_run_fields(model, record, blocks) if blocks else ()
    pairs = tuple((fields, fields.page_title) for fields, _ in runs)
    found += _page_fields_overflow_findings(target, pairs, kind="HARNESS_DRAWING")
    kinds = [kind for kind in pages if kind in _HEADING_WORDS]
    sections = tuple((section_fields(model, record, kind), kind.name) for kind in kinds)
    found += _page_fields_overflow_findings(target, sections, kind=kinds[0].name if kinds else "")
    return tuple(found)
