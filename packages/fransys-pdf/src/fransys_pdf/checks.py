"""What `fransys_pdf.source` cannot draw.

`MARKDOWN_UNSUPPORTED`, `DOCUMENT_MIXED_SHEET_FORMATS`, `DOCUMENT_NO_DRAWINGS`,
`DOCUMENT_EMPTY_LIST`, `DRAWING_SET_REPLICA_ONLY`, `DOCUMENT_NO_TOP_LEVEL_CABLES` (decision
pdf-0006) and `TITLE_BLOCK_UNIT_IDENTITY_MISSING` (a unit document whose unit has an empty
`title` or `number`, one WARNING per document). The three other title-block findings
(`TITLE_BLOCK_NO_ROOM`, `TITLE_BLOCK_TEXT_OVERFLOW`, `TITLE_BLOCK_NOTICE_OVERFLOW`) are
`fransys_render.sheet_check`'s: render draws the title block (render-0019).
"""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    PageForm,
    cable_blocks,
    diagram_sheets,
    document_page_kinds,
    document_rows,
    document_sheet,
    document_unit,
    harness_cables_for,
    location_node_designation,
    mixed_sheet_groups,
    system_has_no_top_level_cables,
    unit_release,
)
lazy from fransys_model.kernel import Finding

from ._cable_checks import harness_block_messages
from ._cable_runs import body_size_mm
from ._diagrams import diagram_no_drawings_messages
from ._drawings import replica_only_sets, schematic_missing_keys, schematic_pages
from ._forms import has_form, list_pages
from ._markdown import parse, unsupported
from ._schematic_yield import list_rows, schematic_yields
from .codes import finding

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import AspectNodeId, DiagramSheet, DocumentId, DocumentRow
    from fransys_model.kernel import Model
    from fransys_model.vocab import PageKind

    from ._cable_checks import CableSizes

    type _DocId = DocumentId


def _markdown_findings(subject: _DocId, field: str, text: str) -> tuple[Finding, ...]:
    return tuple(finding("MARKDOWN_UNSUPPORTED", (subject,), f"{field} line {line.line}: {line.construct}") for line in unsupported(parse(text)))


def _mixed_sheet_format_findings(model: Model, subject: _DocId) -> tuple[Finding, ...]:
    pages = document_page_kinds(model, subject)
    groups = mixed_sheet_groups(model, subject, pages)
    if not groups:
        return ()
    named = "; ".join(
        f"{group.name} (page{'s' if len(group.numbers) > 1 else ''} {', '.join(str(number) for number in group.numbers)})" for group in groups
    )
    return (finding("DOCUMENT_MIXED_SHEET_FORMATS", (subject,), f"mixed sheet formats: {named}"),)


def _unit_identity_findings(model: Model, subject: _DocId, record: DocumentRow) -> tuple[Finding, ...]:
    """`TITLE_BLOCK_UNIT_IDENTITY_MISSING` : the unit has no `title` or `number`."""
    unit = document_unit(model, record.id)
    if unit is None:
        return ()
    release = unit_release(model, unit)
    empty = [field for field in ("title", "number") if not getattr(release, field)]
    if not empty:
        return ()
    return (
        finding(
            "TITLE_BLOCK_UNIT_IDENTITY_MISSING",
            (subject,),
            f"unit document's unit has an empty {' and '.join(empty)}; that cell prints empty",
        ),
    )


def _schematic_no_drawings_message(
    model: Model,
    record: DocumentRow,
    pages: tuple[PageKind, ...],
    svgs: Mapping[str, str],
    diagrams: tuple[DiagramSheet, ...],
) -> str | None:
    pages_found = schematic_pages(model, record, pages)
    if not pages_found:
        if schematic_yields(model, record, pages, diagrams):
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


_LOCATION_DRAWS_NO_HARNESS = "HARNESS_DRAWING: a location document draws no harness drawing. Add the page to the unit's or the harness's document."


def _harness_no_drawings_messages(
    model: Model, record: DocumentRow, svgs: Mapping[str, str], laid: CableSizes, pdf: Mapping[str, float]
) -> list[str]:
    """The `HARNESS_DRAWING` messages: "no cable at all", else `harness_block_messages`'s."""
    pages = document_page_kinds(model, record.id)
    if not has_form(pages, PageForm.HARNESS_DRAWING):
        return []
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
    body_mm = body_size_mm(document_sheet(model, record.id, pages), pdf)
    return harness_block_messages(model, cable_blocks(model, record.id, cables_found), svgs, laid, body_mm)


def _diagram_messages(
    model: Model,
    record: DocumentRow,
    svgs: Mapping[str, str],
    diagrams: tuple[DiagramSheet, ...],
) -> list[str]:
    if not has_form(document_page_kinds(model, record.id), PageForm.BLOCK_DIAGRAM):
        return []
    found = diagram_sheets(model, record.id, diagrams)
    return diagram_no_drawings_messages(model, record, svgs, found)


def _drawn_messages(model: Model, record: DocumentRow, svgs: Mapping[str, str], diagrams: tuple[DiagramSheet, ...]) -> list[str]:
    pages = document_page_kinds(model, record.id)
    schematic = _schematic_no_drawings_message(model, record, pages, svgs, diagrams)
    return [schematic] if has_form(pages, PageForm.SCHEMATIC) and schematic is not None else []


def _no_drawings_findings(record: DocumentRow, messages: list[str]) -> tuple[Finding, ...]:
    return tuple(finding("DOCUMENT_NO_DRAWINGS", (record.id,), m) for m in messages)


def _set_where(model: Model, location: AspectNodeId | None) -> str:
    """The location path of a drawing set for a finding message; `(no location)` for `None`."""
    return "(no location)" if location is None else location_node_designation(model, location)


def _replica_only_findings(model: Model, subject: _DocId, record: DocumentRow, pages: tuple[PageKind, ...]) -> tuple[Finding, ...]:
    """One `DRAWING_SET_REPLICA_ONLY` INFO per matched set the STEP 4 rule dropped."""
    return tuple(
        finding(
            "DRAWING_SET_REPLICA_ONLY",
            (subject, drawing_set.id),
            f"drawing set {_set_where(model, drawing_set.location)} holds only black-box replicas: not drawn",
        )
        for drawing_set in replica_only_sets(model, record, pages)
    )


def _no_top_level_cables_findings(model: Model, subject: _DocId, record: DocumentRow, pages: tuple[PageKind, ...]) -> tuple[Finding, ...]:
    """`DOCUMENT_NO_TOP_LEVEL_CABLES` INFO, not an ERROR, for the `SYSTEM` preset."""
    if not has_form(pages, PageForm.HARNESS_DRAWING):
        return ()
    cables_found = harness_cables_for(model, record.id, pages)
    if not system_has_no_top_level_cables(model, record.id, cables_found):
        return ()
    return (
        finding(
            "DOCUMENT_NO_TOP_LEVEL_CABLES",
            (subject,),
            "HARNESS_DRAWING: the model has no top-level cable",
        ),
    )


def _empty_list_findings(model: Model, subject: _DocId, record: DocumentRow, pages: tuple[PageKind, ...]) -> tuple[Finding, ...]:
    return tuple(
        finding("DOCUMENT_EMPTY_LIST", (subject,), f"{kind.name} has no rows: the page is left out")
        for kind in list_pages(pages)
        if not list_rows(model, record, kind)
    )


def check(
    model: Model,
    svgs: Mapping[str, str],
    *,
    diagrams: tuple[DiagramSheet, ...],
    laid: CableSizes,
    pdf: Mapping[str, float],
) -> tuple[Finding, ...]:
    """Every problem `source` cannot draw, for every `Document` record of `model`.

    Args:
        model: A laid-out model.
        svgs: Page key to SVG text, the same mapping `source` takes: `check` needs it to
            tell a missing drawing-set page or cable key from one that is present.
        diagrams: Every block diagram sheet the diagram engine placed (`DiagramSheet`).
        laid: Each laid-out cable block's `(width, height, sheet format)` in G by block key; a
            block that `svgs` holds and `laid` lacks is not measured.
        pdf: The `[pdf]` table, the same mapping `source` takes: the page margin and the cable-run header size the page body.

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
        messages = [
            *_drawn_messages(model, record, svgs, diagrams),
            *_harness_no_drawings_messages(model, record, svgs, laid, pdf),
            *_diagram_messages(model, record, svgs, diagrams),
        ]
        findings.extend(_no_drawings_findings(record, messages))
        findings.extend(_no_top_level_cables_findings(model, subject, record, pages))
        findings.extend(_replica_only_findings(model, subject, record, pages))
        findings.extend(_empty_list_findings(model, subject, record, pages))
    return tuple(sorted(findings, key=lambda found: (found.code, found.subjects, found.message)))
