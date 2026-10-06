"""What `fransys_pdf.source` cannot draw (spec P11).

`MARKDOWN_UNSUPPORTED` (P6), `DOCUMENT_MIXED_SHEET_FORMATS` (P4), `DOCUMENT_NO_DRAWINGS` (P7,
P8), `DOCUMENT_EMPTY_LIST` (P9), `TITLE_BLOCK_NO_ROOM` (page-frame spec R6),
`DRAWING_SET_REPLICA_ONLY` (STEP 4 addition, `.fransys/WORK-ORDER-UNIT-DOCUMENTS.md`),
`DOCUMENT_NO_TOP_LEVEL_CABLES` (units spec U3's amended "cable drawings" bullet, decision
pdf-0006), `TITLE_BLOCK_NOTICE_OVERFLOW` and `TITLE_BLOCK_TEXT_OVERFLOW` (page-frame spec
R11.4, R11.7) and `TITLE_BLOCK_UNIT_IDENTITY_MISSING` (UNIT-ID I3: a unit document whose unit
has an empty `title` or `number`, one WARNING per document).

`TITLE_BLOCK_TEXT_OVERFLOW` covers all nine one-line fields (R11.7: "every field except the
notice"): the six document-level ones (`title`, `number`, `customer`, `revision`,
`revision_date`, `author`, from `_geometry.document_facts`, the same reader `_title_block`
itself cuts) and the three page-level ones (`page_title`, `scope`, `sheet_counter`), built per
page kind by the same readers `_drawings.py`/`document.py` use (`drawing_text.page_title`,
`_page_title_labels`, `_HEADING_WORDS`, `location_label`/`item_designation`/`subject_label`),
imported rather than duplicated so this can never disagree with what the page shows.
"""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import (
    bom_lines,
    cable_list_rows,
    designation_list,
    document_unit,
    item_designation,
    location_node_designation,
    unit_release,
)
from fransys_model.derive.drawing_text import page_title
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import PageKind, documents, projects

from ._cable_runs import part_groups
from ._cover_checks import cover_overflow_findings
from ._drawings import (
    _page_title_labels,
    harness_cables_for,
    replica_only_sets,
    schematic_missing_keys,
    schematic_pages,
    system_has_no_top_level_cables,
)
from ._frame import (
    band_height_mm,
    field_size_pt,
    fits,
    notice_cell_size_mm,
    notice_fits,
    title_block_field_width_mm,
    title_block_fits,
)
from ._geometry import (
    document_facts,
    location_label,
    mixed_sheet_formats,
    resolve_sheet_format,
    subject_label,
)
from ._lists import (
    _boards_for,
    _bom_scope,
    _terminal_strips_for,
    connector_rows_for,
    plc_channel_rows_for,
    terminal_rows_for,
    wire_rows_for,
)
from ._markdown import parse, unsupported
from .document import _HEADING_WORDS, document_pages

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.layout import SheetFormat
    from fransys_model.vocab import AspectNode, Document

    type _DocId = Id[Document]


def _markdown_findings(subject: _DocId, field: str, text: str) -> tuple[Finding, ...]:
    return tuple(
        Finding(
            code="MARKDOWN_UNSUPPORTED",
            severity=Severity.ERROR,
            subjects=(subject,),
            message=f"{field} line {line.line}: {line.construct}",
        )
        for line in unsupported(parse(text))
    )


def _mixed_sheet_format_findings(model: Model, subject: _DocId) -> tuple[Finding, ...]:
    record = documents(model)[subject]
    pages = document_pages(model, subject)
    groups = mixed_sheet_formats(model, record, pages)
    if not groups:
        return ()
    named = "; ".join(
        f"{fmt.name} (page{'s' if len(group) > 1 else ''} "
        f"{', '.join(str(page.number) for page in group)})"
        for fmt, group in groups
    )
    return (
        Finding(
            code="DOCUMENT_MIXED_SHEET_FORMATS",
            severity=Severity.ERROR,
            subjects=(subject,),
            message=f"mixed sheet formats: {named}",
        ),
    )


def _title_block_no_room_findings(
    model: Model, subject: _DocId, record: Document, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    sheet = resolve_sheet_format(model, record, pages)
    if title_block_fits(sheet):
        return ()
    return (
        Finding(
            code="TITLE_BLOCK_NO_ROOM",
            severity=Severity.WARNING,
            subjects=(subject,),
            message=(
                f"sheet format {sheet.name!r}: title-block band {band_height_mm(sheet)}mm, "
                "under the required 20mm"
            ),
        ),
    )


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


def _one_line_overflow_finding(
    target: _FieldTarget, field: str, text: str, *, where: str, fallback: str | None
) -> Finding | None:
    """One `TITLE_BLOCK_TEXT_OVERFLOW` finding if `text` and `fallback` both miss (R11.7)."""
    width_mm = title_block_field_width_mm(target.sheet, field)
    size_pt = field_size_pt(field)
    bold = field == "title"
    if fits(text, size_pt=size_pt, bold=bold, width_mm=width_mm):
        return None
    if fallback is not None and fits(fallback, size_pt=size_pt, bold=bold, width_mm=width_mm):
        return None
    shown = fallback if fallback is not None else text
    return Finding(
        code="TITLE_BLOCK_TEXT_OVERFLOW",
        severity=Severity.WARNING,
        subjects=(target.subject,),
        message=f"{field} ({where}): {shown!r} does not fit its title-block cell, cut with '…'",
    )


def _document_level_overflow_findings(
    model: Model, subject: _DocId, record: Document, sheet: SheetFormat
) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_TEXT_OVERFLOW` for the six document-level fields (R11.7)."""
    title, number, customer, revision, revision_date, author = document_facts(model, record)
    values = {
        "title": title,
        "number": number,
        "customer": customer,
        "revision": revision,
        "revision_date": revision_date,
        "author": author,
    }
    target = _FieldTarget(subject=subject, sheet=sheet)
    findings = []
    for field in _DOCUMENT_LEVEL_ONE_LINE_FIELDS:
        finding = _one_line_overflow_finding(
            target, field, values[field], where="document", fallback=None
        )
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


@dataclass(frozen=True, slots=True)
class _OverflowContext:
    """The model, subject, record, pages and sheet format every per-page overflow check shares."""

    model: Model
    subject: _DocId
    record: Document
    pages: tuple[PageKind, ...]
    sheet: SheetFormat


def _schematic_page_overflow_findings(
    ctx: _OverflowContext, svgs: Mapping[str, str]
) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_TEXT_OVERFLOW` for the page-level fields of real `SCHEMATIC` pages (R11.7)."""
    if PageKind.SCHEMATIC not in ctx.pages:
        return ()
    pages_found = schematic_pages(ctx.model, ctx.record, ctx.pages)
    if not pages_found or schematic_missing_keys(pages_found, svgs):
        return ()
    target = _FieldTarget(subject=ctx.subject, sheet=ctx.sheet)
    findings = []
    scope = (
        location_label(ctx.model, ctx.record.location)
        if ctx.record.location is not None
        else subject_label(ctx.model, ctx.record)
    )
    finding = _one_line_overflow_finding(target, "scope", scope, where="SCHEMATIC", fallback=None)
    if finding is not None:
        findings.append(finding)
    totals = Counter(page.drawing_set for page in pages_found)
    for page in pages_found:
        where = f"page {page.number}"
        joined = page_title(ctx.model, page)
        labels = _page_title_labels(ctx.model, page)
        finding = _one_line_overflow_finding(
            target, "page_title", joined, where=where, fallback=labels or None
        )
        if finding is not None:
            findings.append(finding)
        counter = f"{page.number} / {totals[page.drawing_set]}"
        finding = _one_line_overflow_finding(
            target, "sheet_counter", counter, where=where, fallback=None
        )
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def _harness_page_overflow_findings(ctx: _OverflowContext) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_TEXT_OVERFLOW` for `page_title`/`scope` on `HARNESS_DRAWING` pages (R11.7)."""
    if PageKind.HARNESS_DRAWING not in ctx.pages:
        return ()
    cables_found = harness_cables_for(ctx.model, ctx.record, ctx.pages)
    if not cables_found:
        return ()
    target = _FieldTarget(subject=ctx.subject, sheet=ctx.sheet)
    findings = []
    scope = (
        item_designation(ctx.model, ctx.record.item)
        if ctx.record.item is not None
        else subject_label(ctx.model, ctx.record)
    )
    finding = _one_line_overflow_finding(
        target, "scope", scope, where="HARNESS_DRAWING", fallback=None
    )
    if finding is not None:
        findings.append(finding)
    for heading, _group in part_groups(cables_found):
        finding = _one_line_overflow_finding(
            target, "page_title", heading, where=heading, fallback=None
        )
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def _other_page_overflow_findings(
    model: Model, subject: _DocId, record: Document, pages: tuple[PageKind, ...], sheet: SheetFormat
) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_TEXT_OVERFLOW` for `_HEADING_WORDS` and `subject_label`, as printed (R11.7)."""
    kinds = [kind for kind in pages if kind in _HEADING_WORDS]
    if not kinds:
        return ()
    target = _FieldTarget(subject=subject, sheet=sheet)
    findings = []
    scope = subject_label(model, record)
    finding = _one_line_overflow_finding(target, "scope", scope, where=kinds[0].name, fallback=None)
    if finding is not None:
        findings.append(finding)
    for kind in kinds:
        finding = _one_line_overflow_finding(
            target, "page_title", _HEADING_WORDS[kind], where=kind.name, fallback=None
        )
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def _text_overflow_findings(
    model: Model,
    subject: _DocId,
    record: Document,
    pages: tuple[PageKind, ...],
    svgs: Mapping[str, str],
) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_TEXT_OVERFLOW` (R11.7) for every one-line field but the notice."""
    sheet = resolve_sheet_format(model, record, pages)
    if not title_block_fits(sheet):
        return ()
    ctx = _OverflowContext(model=model, subject=subject, record=record, pages=pages, sheet=sheet)
    return (
        _document_level_overflow_findings(model, subject, record, sheet)
        + _schematic_page_overflow_findings(ctx, svgs)
        + _harness_page_overflow_findings(ctx)
        + _other_page_overflow_findings(model, subject, record, pages, sheet)
    )


def _notice_overflow_findings(model: Model) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_NOTICE_OVERFLOW` (R11.4): one finding if `Project.notice` misses any cell."""
    project = next(iter(projects(model).values()), None)
    if project is None or not project.notice:
        return ()
    for subject, record in documents(model).items():
        pages = document_pages(model, subject)
        sheet = resolve_sheet_format(model, record, pages)
        if not title_block_fits(sheet):
            continue
        width_mm, height_mm = notice_cell_size_mm(sheet)
        if not notice_fits(project.notice, width_mm=width_mm, height_mm=height_mm):
            return (
                Finding(
                    code="TITLE_BLOCK_NOTICE_OVERFLOW",
                    severity=Severity.WARNING,
                    subjects=(project.id,),
                    message="Project.notice does not fit the title block's notice cell, cut",
                ),
            )
    return ()


def _unit_identity_findings(model: Model, subject: _DocId, record: Document) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_UNIT_IDENTITY_MISSING` (UNIT-ID I3): the unit has no `title` or `number`."""
    unit = document_unit(model, record)
    if unit is None:
        return ()
    release = unit_release(model, unit)
    empty = [field for field in ("title", "number") if not getattr(release, field)]
    if not empty:
        return ()
    return (
        Finding(
            code="TITLE_BLOCK_UNIT_IDENTITY_MISSING",
            severity=Severity.WARNING,
            subjects=(subject,),
            message=(
                f"unit document's unit has an empty {' and '.join(empty)}; that cell prints empty"
            ),
        ),
    )


def _schematic_no_drawings_message(
    model: Model, record: Document, pages: tuple[PageKind, ...], svgs: Mapping[str, str]
) -> str | None:
    pages_found = schematic_pages(model, record, pages)
    if not pages_found:
        if replica_only_sets(model, record, pages):
            # STEP 4 addition: every matched set was replica-only and dropped -- there was
            # really something there, just deliberately not drawn (its own INFO finding
            # below), not the genuine "no drawing set found" case this ERROR means otherwise.
            return None
        return "SCHEMATIC: no drawing set found"
    missing = schematic_missing_keys(pages_found, svgs)
    if missing:
        return f"SCHEMATIC: missing drawing for {', '.join(missing)}"
    return None


def _harness_no_drawings_message(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> str | None:
    """CT2's `HARNESS_DRAWING` message: only "no cable at all" is left (no missing-key case)."""
    cables_found = harness_cables_for(model, record, pages)
    if not cables_found:
        if system_has_no_top_level_cables(record, cables_found):
            # STEP 4b addition: the model simply has no top-level cable at all -- the SYSTEM
            # preset's own DOCUMENT_NO_TOP_LEVEL_CABLES INFO covers it below, not this ERROR.
            return None
        subject = "unit" if document_unit(model, record) is not None else "harness"
        return f"HARNESS_DRAWING: the {subject} has no cable"
    return None


def _no_drawings_findings(
    model: Model,
    subject: _DocId,
    record: Document,
    pages: tuple[PageKind, ...],
    svgs: Mapping[str, str],
) -> tuple[Finding, ...]:
    messages = []
    if PageKind.SCHEMATIC in pages:
        message = _schematic_no_drawings_message(model, record, pages, svgs)
        if message is not None:
            messages.append(message)
    if PageKind.HARNESS_DRAWING in pages:
        message = _harness_no_drawings_message(model, record, pages)
        if message is not None:
            messages.append(message)
    return tuple(
        Finding(
            code="DOCUMENT_NO_DRAWINGS", severity=Severity.ERROR, subjects=(subject,), message=m
        )
        for m in messages
    )


def _set_where(model: Model, location: Id[AspectNode] | None) -> str:
    """The location path of a drawing set for a finding message; `(no location)` for `None`."""
    return "(no location)" if location is None else location_node_designation(model, location)


def _replica_only_findings(
    model: Model, subject: _DocId, record: Document, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    """One `DRAWING_SET_REPLICA_ONLY` INFO per matched set the STEP 4 rule dropped."""
    return tuple(
        Finding(
            code="DRAWING_SET_REPLICA_ONLY",
            severity=Severity.INFO,
            subjects=(subject, drawing_set.id),
            message=(
                f"drawing set {_set_where(model, drawing_set.location)} holds only "
                "black-box replicas: not drawn"
            ),
        )
        for drawing_set in replica_only_sets(model, record, pages)
    )


def _no_top_level_cables_findings(
    model: Model, subject: _DocId, record: Document, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    """`DOCUMENT_NO_TOP_LEVEL_CABLES` INFO, not an ERROR, for the `SYSTEM` preset (U3)."""
    if PageKind.HARNESS_DRAWING not in pages:
        return ()
    cables_found = harness_cables_for(model, record, pages)
    if not system_has_no_top_level_cables(record, cables_found):
        return ()
    return (
        Finding(
            code="DOCUMENT_NO_TOP_LEVEL_CABLES",
            severity=Severity.INFO,
            subjects=(subject,),
            message="HARNESS_DRAWING: the model has no top-level cable",
        ),
    )


_LIST_KINDS = (
    PageKind.PLC_LIST,
    PageKind.TERMINAL_LIST,
    PageKind.CONNECTOR_LIST,
    PageKind.WIRE_LABEL_LIST,
    PageKind.DESIGNATION_LIST,
    PageKind.CABLE_LIST,
    PageKind.BOM,
)


def _list_rows(  # noqa: PLR0911 -- one branch per list `PageKind`, as `document._page_source`
    model: Model, record: Document, kind: PageKind
) -> tuple[object, ...]:
    """The rows `kind`'s list page renders for `record`, for `DOCUMENT_EMPTY_LIST` (P9, P11)."""
    if kind is PageKind.PLC_LIST:
        return plc_channel_rows_for(model, record)
    if kind is PageKind.TERMINAL_LIST:
        return tuple(
            row
            for strip in _terminal_strips_for(model, record)
            for row in terminal_rows_for(model, record, strip)
        )
    if kind is PageKind.CONNECTOR_LIST:
        return tuple(
            row
            for board in _boards_for(model, record)
            for row in connector_rows_for(model, record, board)
        )
    if kind is PageKind.WIRE_LABEL_LIST:
        return wire_rows_for(model, record)
    if kind is PageKind.DESIGNATION_LIST:
        return tuple(designation_list(model, unit=document_unit(model, record)))
    if kind is PageKind.CABLE_LIST:
        return tuple(cable_list_rows(model))
    return tuple(
        bom_lines(model, scope=_bom_scope(model, record))
    )  # kind is PageKind.BOM: the last one


def _empty_list_findings(
    model: Model, subject: _DocId, record: Document, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    return tuple(
        Finding(
            code="DOCUMENT_EMPTY_LIST",
            severity=Severity.INFO,
            subjects=(subject,),
            message=f"{kind.name} has no rows: the page is left out",
        )
        for kind in _LIST_KINDS
        if kind in pages and not _list_rows(model, record, kind)
    )


def check(model: Model, svgs: Mapping[str, str]) -> tuple[Finding, ...]:
    """Every problem `source` cannot draw, for every `Document` record of `model`.

    Args:
        model: A laid-out model.
        svgs: Page key to SVG text, the same mapping `source` takes: `check` needs it to
            tell a missing drawing-set page or cable key from one that is present (P7, P8).

    Returns:
        Findings sorted by `(code, subjects, message)`. Pure, never raises.
    """
    findings: list[Finding] = []
    for subject, record in documents(model).items():
        findings.extend(_markdown_findings(subject, "cover", record.cover))
        if record.notes is not None:
            findings.extend(_markdown_findings(subject, "notes", record.notes))
        findings.extend(_mixed_sheet_format_findings(model, subject))
        pages = document_pages(model, subject)
        findings.extend(_title_block_no_room_findings(model, subject, record, pages))
        findings.extend(_unit_identity_findings(model, subject, record))
        findings.extend(cover_overflow_findings(model, subject, record, pages))
        findings.extend(_text_overflow_findings(model, subject, record, pages, svgs))
        findings.extend(_no_drawings_findings(model, subject, record, pages, svgs))
        findings.extend(_no_top_level_cables_findings(model, subject, record, pages))
        findings.extend(_replica_only_findings(model, subject, record, pages))
        findings.extend(_empty_list_findings(model, subject, record, pages))
    findings.extend(_notice_overflow_findings(model))
    return tuple(sorted(findings, key=lambda found: (found.code, found.subjects, found.message)))
