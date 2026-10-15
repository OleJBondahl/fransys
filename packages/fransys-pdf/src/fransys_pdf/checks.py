"""What `fransys_pdf.source` cannot draw.

`MARKDOWN_UNSUPPORTED`, `DOCUMENT_MIXED_SHEET_FORMATS`, `DOCUMENT_NO_DRAWINGS`,
`DOCUMENT_EMPTY_LIST`, `TITLE_BLOCK_NO_ROOM`, `DRAWING_SET_REPLICA_ONLY`,
`DOCUMENT_NO_TOP_LEVEL_CABLES` (decision pdf-0006), `TITLE_BLOCK_NOTICE_OVERFLOW` and
`TITLE_BLOCK_TEXT_OVERFLOW` and `TITLE_BLOCK_UNIT_IDENTITY_MISSING` (a unit document whose unit has
an empty `title` or `number`, one WARNING per document).

`TITLE_BLOCK_TEXT_OVERFLOW` covers all nine one-line fields ("every field except the
notice"): the six document-level ones (`title`, `number`, `customer`, `revision`,
`revision_date`, `author`, from `_geometry.document_facts`, the same reader `_title_block`
itself cuts) and the three page-level ones (`page_title`, `scope`, `sheet_counter`), read from
the `TitleBlockFields` that `schematic_fields`, `harness_run_fields` and `section_fields`
build for the pages themselves, so this can never disagree with what the page shows.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import (
    document_unit,
    location_node_designation,
    unit_release,
)
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import PageKind, documents

from ._cable_checks import harness_block_messages
from ._checks_overflow import (
    _document_level_overflow_findings,
    _FieldTarget,
    _page_overflow_findings,
)
from ._cover_checks import cover_overflow_findings
from ._diagrams import diagram_no_drawings_messages
from ._drawings import (
    cable_blocks,
    harness_cables_for,
    replica_only_sets,
    schematic_missing_keys,
    schematic_pages,
    system_has_no_top_level_cables,
)
from ._frame import (
    band_height_mm,
    notice_cell_size_mm,
    notice_fits,
    notice_room_chars,
    title_block_fits,
)
from ._geometry import (
    mixed_sheet_formats,
    resolve_sheet_format,
)
from ._markdown import parse, unsupported
from ._schematic_yield import _LIST_KINDS, list_rows, schematic_yields
from ._sizes import sizes_of
from .document import document_pages

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
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


def _text_overflow_findings(
    model: Model,
    subject: _DocId,
    record: Document,
    pages: tuple[PageKind, ...],
    svgs: Mapping[str, str],
) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_TEXT_OVERFLOW` for every one-line field but the notice."""
    sheet = resolve_sheet_format(model, record, pages)
    if not title_block_fits(sheet):
        return ()
    target = _FieldTarget(
        subject=subject, sheet=sheet, sizes=sizes_of(model, record), notice=bool(record.notice)
    )
    return _document_level_overflow_findings(model, subject, record, sheet) + (
        _page_overflow_findings(model, target, record, pages, svgs)
    )


def _notice_overflow_findings(model: Model) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_NOTICE_OVERFLOW`: one finding if a `Document.notice` misses its cell."""
    for subject, record in documents(model).items():
        if not record.notice:
            continue
        pages = document_pages(model, subject)
        sheet = resolve_sheet_format(model, record, pages)
        if not title_block_fits(sheet):
            continue
        width_mm, height_mm = notice_cell_size_mm(sheet)
        sizes = sizes_of(model, record)
        if not notice_fits(record.notice, sizes, width_mm=width_mm, height_mm=height_mm):
            return (
                Finding(
                    code="TITLE_BLOCK_NOTICE_OVERFLOW",
                    severity=Severity.WARNING,
                    subjects=(record.id,),
                    message=(
                        "the notice does not fit the title block's notice cell, cut; "
                        f"the cell holds about {notice_room_chars(sheet, sizes)} characters; "
                        "shorten fr.document(notice=...)"
                    ),
                ),
            )
    return ()


def _unit_identity_findings(model: Model, subject: _DocId, record: Document) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_UNIT_IDENTITY_MISSING` : the unit has no `title` or `number`."""
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
        if schematic_yields(model, record, pages):
            # pdf-0033: nothing to draw and another content page stands: no page, no finding.
            return None
        if replica_only_sets(model, record, pages):
            # Every matched set was replica-only and dropped -- there was
            # really something there, just deliberately not drawn (its own INFO finding
            # below), not the genuine "no drawing set found" case this ERROR means otherwise.
            return None
        return "SCHEMATIC: no drawing set found"
    missing = schematic_missing_keys(pages_found, svgs)
    if missing:
        return f"SCHEMATIC: missing drawing for {', '.join(missing)}"
    return None


_LOCATION_DRAWS_NO_HARNESS = (
    "HARNESS_DRAWING: a location document draws no harness drawing. "
    "Add the page to the unit's or the harness's document."
)


def _harness_no_drawings_messages(
    model: Model, record: Document, pages: tuple[PageKind, ...], svgs: Mapping[str, str]
) -> list[str]:
    """The `HARNESS_DRAWING` messages: "no cable at all", else `harness_block_messages`'s."""
    cables_found = harness_cables_for(model, record, pages)
    if not cable_blocks(model, record, cables_found):
        if system_has_no_top_level_cables(record, cables_found):
            # STEP 4b addition: the model simply has no top-level cable at all -- the SYSTEM
            # preset's own DOCUMENT_NO_TOP_LEVEL_CABLES INFO covers it below, not this ERROR.
            return []
        if document_unit(model, record) is not None:
            return ["HARNESS_DRAWING: the unit has no cable"]
        if record.item is None:
            return [_LOCATION_DRAWS_NO_HARNESS]
        return ["HARNESS_DRAWING: the harness has no cable"]
    return harness_block_messages(model, record, pages, svgs)


def _no_drawings_findings(  # noqa: PLR0913, PLR0917 -- the tall-diagram cables are one more input
    model: Model,
    subject: _DocId,
    record: Document,
    pages: tuple[PageKind, ...],
    svgs: Mapping[str, str],
    tall_cables: frozenset[Id[Any]],
) -> tuple[Finding, ...]:
    schematic = _schematic_no_drawings_message(model, record, pages, svgs)
    messages = [schematic] if PageKind.SCHEMATIC in pages and schematic is not None else []
    if PageKind.HARNESS_DRAWING in pages:
        messages.extend(_harness_no_drawings_messages(model, record, pages, svgs))
    messages.extend(diagram_no_drawings_messages(model, record, pages, svgs, tall_cables))
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
    """`DOCUMENT_NO_TOP_LEVEL_CABLES` INFO, not an ERROR, for the `SYSTEM` preset."""
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
        if kind in pages and not list_rows(model, record, kind)
    )


def _tall_cables(built: tuple[Finding, ...]) -> frozenset[Id[Any]]:
    """The subjects of the build's `DIAGRAM_COLUMN_TOO_TALL` INFOs."""
    return frozenset(s for f in built if f.code == "DIAGRAM_COLUMN_TOO_TALL" for s in f.subjects)


def check(
    model: Model, svgs: Mapping[str, str], built: tuple[Finding, ...] = ()
) -> tuple[Finding, ...]:
    """Every problem `source` cannot draw, for every `Document` record of `model`.

    Args:
        model: A laid-out model.
        svgs: Page key to SVG text, the same mapping `source` takes: `check` needs it to
            tell a missing drawing-set page or cable key from one that is present.
        built: The build's findings; an undrawn diagram whose first line's cable is a subject
            of a `DIAGRAM_COLUMN_TOO_TALL` among them is named as too tall, any other gets
            the plain text.

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
        findings.extend(
            _no_drawings_findings(model, subject, record, pages, svgs, _tall_cables(built))
        )
        findings.extend(_no_top_level_cables_findings(model, subject, record, pages))
        findings.extend(_replica_only_findings(model, subject, record, pages))
        findings.extend(_empty_list_findings(model, subject, record, pages))
    findings.extend(_notice_overflow_findings(model))
    return tuple(sorted(findings, key=lambda found: (found.code, found.subjects, found.message)))
