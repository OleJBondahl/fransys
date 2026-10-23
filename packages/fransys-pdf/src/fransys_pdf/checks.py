"""What `fransys_pdf.source` cannot draw.

`MARKDOWN_UNSUPPORTED`, `DOCUMENT_MIXED_SHEET_FORMATS`, `DOCUMENT_NO_DRAWINGS`,
`DOCUMENT_EMPTY_LIST`, `DRAWING_SET_REPLICA_ONLY`, `DOCUMENT_NO_TOP_LEVEL_CABLES` (decision
pdf-0006) and `TITLE_BLOCK_UNIT_IDENTITY_MISSING` (a unit document whose unit has an empty
`title` or `number`, one WARNING per document). The three other title-block findings
(`TITLE_BLOCK_NO_ROOM`, `TITLE_BLOCK_TEXT_OVERFLOW`, `TITLE_BLOCK_NOTICE_OVERFLOW`) are
`fransys_render.sheet_check`'s: render draws the title block (render-0019).
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import (
    PageForm,
    cable_blocks,
    document_page_kinds,
    document_rows,
    document_unit,
    harness_cables_for,
    location_node_designation,
    mixed_sheet_groups,
    system_has_no_top_level_cables,
    unit_release,
)
from fransys_model.kernel import Finding, Severity

from ._cable_checks import harness_block_messages
from ._diagrams import diagram_no_drawings_messages
from ._drawings import replica_only_sets, schematic_missing_keys, schematic_pages
from ._forms import has_form, list_pages
from ._markdown import parse, unsupported
from ._schematic_yield import list_rows, schematic_yields
from .codes import fix_text

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import AspectNodeId, DocumentId, DocumentRow
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import PageKind

    type _DocId = DocumentId


def _markdown_findings(subject: _DocId, field: str, text: str) -> tuple[Finding, ...]:
    return tuple(
        Finding(
            code="MARKDOWN_UNSUPPORTED",
            severity=Severity.ERROR,
            subjects=(subject,),
            fix=fix_text("MARKDOWN_UNSUPPORTED"),
            message=f"{field} line {line.line}: {line.construct}",
        )
        for line in unsupported(parse(text))
    )


def _mixed_sheet_format_findings(model: Model, subject: _DocId) -> tuple[Finding, ...]:
    pages = document_page_kinds(model, subject)
    groups = mixed_sheet_groups(model, subject, pages)
    if not groups:
        return ()
    named = "; ".join(
        f"{group.name} (page{'s' if len(group.numbers) > 1 else ''} "
        f"{', '.join(str(number) for number in group.numbers)})"
        for group in groups
    )
    return (
        Finding(
            code="DOCUMENT_MIXED_SHEET_FORMATS",
            severity=Severity.ERROR,
            subjects=(subject,),
            fix=fix_text("DOCUMENT_MIXED_SHEET_FORMATS"),
            message=f"mixed sheet formats: {named}",
        ),
    )


def _unit_identity_findings(
    model: Model, subject: _DocId, record: DocumentRow
) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_UNIT_IDENTITY_MISSING` : the unit has no `title` or `number`."""
    unit = document_unit(model, record.id)
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
            fix=fix_text("TITLE_BLOCK_UNIT_IDENTITY_MISSING"),
            message=(
                f"unit document's unit has an empty {' and '.join(empty)}; that cell prints empty"
            ),
        ),
    )


def _schematic_no_drawings_message(
    model: Model, record: DocumentRow, pages: tuple[PageKind, ...], svgs: Mapping[str, str]
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
    model: Model, record: DocumentRow, pages: tuple[PageKind, ...], svgs: Mapping[str, str]
) -> list[str]:
    """The `HARNESS_DRAWING` messages: "no cable at all", else `harness_block_messages`'s."""
    cables_found = harness_cables_for(model, record.id, pages)
    if not cable_blocks(model, record.id, cables_found):
        if system_has_no_top_level_cables(model, record.id, cables_found):
            # STEP 4b addition: the model simply has no top-level cable at all -- the SYSTEM
            # preset's own DOCUMENT_NO_TOP_LEVEL_CABLES INFO covers it below, not this ERROR.
            return []
        if document_unit(model, record.id) is not None:
            return ["HARNESS_DRAWING: the unit has no cable"]
        if record.item is None:
            return [_LOCATION_DRAWS_NO_HARNESS]
        return ["HARNESS_DRAWING: the harness has no cable"]
    return harness_block_messages(model, record, pages, svgs)


def _no_drawings_findings(  # noqa: PLR0913, PLR0917 -- the tall-diagram cables are one more input
    model: Model,
    subject: _DocId,
    record: DocumentRow,
    pages: tuple[PageKind, ...],
    svgs: Mapping[str, str],
    tall_cables: frozenset[Id[Any]],
) -> tuple[Finding, ...]:
    schematic = _schematic_no_drawings_message(model, record, pages, svgs)
    messages = [schematic] if has_form(pages, PageForm.SCHEMATIC) and schematic is not None else []
    if has_form(pages, PageForm.HARNESS_DRAWING):
        messages.extend(_harness_no_drawings_messages(model, record, pages, svgs))
    messages.extend(diagram_no_drawings_messages(model, record, pages, svgs, tall_cables))
    return tuple(
        Finding(
            code="DOCUMENT_NO_DRAWINGS",
            severity=Severity.ERROR,
            subjects=(subject,),
            message=m,
            fix=fix_text("DOCUMENT_NO_DRAWINGS"),
        )
        for m in messages
    )


def _set_where(model: Model, location: AspectNodeId | None) -> str:
    """The location path of a drawing set for a finding message; `(no location)` for `None`."""
    return "(no location)" if location is None else location_node_designation(model, location)


def _replica_only_findings(
    model: Model, subject: _DocId, record: DocumentRow, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    """One `DRAWING_SET_REPLICA_ONLY` INFO per matched set the STEP 4 rule dropped."""
    return tuple(
        Finding(
            code="DRAWING_SET_REPLICA_ONLY",
            severity=Severity.INFO,
            subjects=(subject, drawing_set.id),
            fix=fix_text("DRAWING_SET_REPLICA_ONLY"),
            message=(
                f"drawing set {_set_where(model, drawing_set.location)} holds only "
                "black-box replicas: not drawn"
            ),
        )
        for drawing_set in replica_only_sets(model, record, pages)
    )


def _no_top_level_cables_findings(
    model: Model, subject: _DocId, record: DocumentRow, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    """`DOCUMENT_NO_TOP_LEVEL_CABLES` INFO, not an ERROR, for the `SYSTEM` preset."""
    if not has_form(pages, PageForm.HARNESS_DRAWING):
        return ()
    cables_found = harness_cables_for(model, record.id, pages)
    if not system_has_no_top_level_cables(model, record.id, cables_found):
        return ()
    return (
        Finding(
            code="DOCUMENT_NO_TOP_LEVEL_CABLES",
            severity=Severity.INFO,
            subjects=(subject,),
            fix=fix_text("DOCUMENT_NO_TOP_LEVEL_CABLES"),
            message="HARNESS_DRAWING: the model has no top-level cable",
        ),
    )


def _empty_list_findings(
    model: Model, subject: _DocId, record: DocumentRow, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    return tuple(
        Finding(
            code="DOCUMENT_EMPTY_LIST",
            severity=Severity.INFO,
            subjects=(subject,),
            fix=fix_text("DOCUMENT_EMPTY_LIST"),
            message=f"{kind.name} has no rows: the page is left out",
        )
        for kind in list_pages(pages)
        if not list_rows(model, record, kind)
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
    for record in document_rows(model):
        subject = record.id
        findings.extend(_markdown_findings(subject, "cover", record.cover))
        if record.notes is not None:
            findings.extend(_markdown_findings(subject, "notes", record.notes))
        findings.extend(_mixed_sheet_format_findings(model, subject))
        pages = document_page_kinds(model, subject)
        findings.extend(_unit_identity_findings(model, subject, record))
        findings.extend(
            _no_drawings_findings(model, subject, record, pages, svgs, _tall_cables(built))
        )
        findings.extend(_no_top_level_cables_findings(model, subject, record, pages))
        findings.extend(_replica_only_findings(model, subject, record, pages))
        findings.extend(_empty_list_findings(model, subject, record, pages))
    return tuple(sorted(findings, key=lambda found: (found.code, found.subjects, found.message)))
