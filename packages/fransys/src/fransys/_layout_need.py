"""Which builds need the schematic and the diagram layout, and laying them out (0118, 0119)."""

from typing import TYPE_CHECKING, cast

from fransys_author import AuthorError

from fransys_layout import HintError, SymbolPortError, lay_out_diagrams
from fransys_model.derive import (
    document_ids,
    document_page_kinds,
    subject_part_mpn,
    symbol_port_subject,
)
from fransys_model.kernel import Finding, Severity, describe
from fransys_model.vocab import PageKind

from ._codes import fix_text
from ._layout_core import NO_DRAWINGS, NO_LINKS, Laid, lay_out_on_core

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function


def kept_page_kinds(model: Model) -> frozenset[PageKind]:
    """The page kinds some document keeps: the one place that reads every document's pages."""
    return frozenset(
        kind for document in document_ids(model) for kind in document_page_kinds(model, document)
    )


def needs_schematic_layout(model: Model) -> bool:
    """True when any document keeps a SCHEMATIC page, which reads the schematic's `layout.*`."""
    return PageKind.SCHEMATIC in kept_page_kinds(model)


def needs_diagram_layout(model: Model) -> bool:
    """True when any document keeps a BLOCK_DIAGRAM page, which reads `layout.diagram_*`."""
    return PageKind.BLOCK_DIAGRAM in kept_page_kinds(model)


def hint_error_to_author_error(model: Model, error: HintError) -> AuthorError:
    """The `AuthorError` for a layout hint error, its subjects shown as `file:line (key)` (0184)."""
    return AuthorError(describe(error, model))


def _schematic_if_needed(
    model: Model, library: Library, layout: Mapping[str, object] | None
) -> Laid:
    if not needs_schematic_layout(model):
        return model, (), NO_DRAWINGS, NO_LINKS
    return lay_out_on_core(model, library, layout)


def lay_out_if_needed(
    model: Model, library: Library, layout: Mapping[str, object] | None = None
) -> Laid:
    """The core layout and `lay_out_diagrams` when a document keeps their page, else nothing.

    Also the page `Drawing`s and reference links of the core layout (empty when it did not run).
    """
    model, findings, drawn, links = _schematic_if_needed(model, library, layout)
    if not needs_diagram_layout(model):
        return model, findings, drawn, links
    try:
        model, diagram_findings = lay_out_diagrams(model)
    except HintError as error:
        raise hint_error_to_author_error(model, error) from error
    return model, (*findings, *diagram_findings), drawn, links


def symbol_port_missing_finding(model: Model, error: SymbolPortError) -> Finding:
    """One `SYMBOL_PORT_MISSING` `ERROR` for a `SymbolPortError` layout raised (decision 0018).

    `error.function` is a Function of this model, or the whole Item of a one-view draw.
    Message: part mpn + `error`'s text; origin: PortTemplate, else Part, else `error.function`.
    """
    mpn = subject_part_mpn(model, error.function)
    if mpn is None:
        mpn = "no part"
    subject = symbol_port_subject(model, cast("Id[Function]", error.function), error.port_name)
    return Finding(
        code="SYMBOL_PORT_MISSING",
        severity=Severity.ERROR,
        subjects=(subject,),
        fix=fix_text("SYMBOL_PORT_MISSING"),
        message=f"part {mpn!r}: {error}",
    )
