"""Which builds need the schematic and the diagram layout, and laying them out (0118, 0119)."""

from typing import TYPE_CHECKING, cast

import fransys_pdf
from fransys_author import AuthorError
from fransys_el import OPTIONS

from fransys_layout import HintError, SymbolPortError, lay_out_diagrams, lay_out_schematic
from fransys_model.derive import symbol_port_subject
from fransys_model.kernel import Finding, Severity, describe
from fransys_model.vocab import PageKind, documents, functions, items
from fransys_model.vocab import parts as model_parts

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function, Item


def kept_page_kinds(model: Model) -> frozenset[PageKind]:
    """The page kinds some document keeps: the one place that reads every document's pages."""
    return frozenset(
        kind
        for document in documents(model)
        for kind in fransys_pdf.document_pages(model, document)
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


def _schematic_if_needed(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    if not needs_schematic_layout(model):
        return model, ()
    try:
        return lay_out_schematic(model, OPTIONS)
    except HintError as error:
        raise hint_error_to_author_error(model, error) from error
    except SymbolPortError as error:
        return model, (symbol_port_missing_finding(model, error),)


def lay_out_if_needed(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """`lay_out_schematic` and `lay_out_diagrams` when a document keeps their page, else nothing.

    A layout `SymbolPortError` becomes one `SYMBOL_PORT_MISSING` `ERROR`, the model unchanged.
    """
    model, findings = _schematic_if_needed(model)
    if not needs_diagram_layout(model):
        return model, findings
    try:
        model, diagram_findings = lay_out_diagrams(model)
    except HintError as error:
        raise hint_error_to_author_error(model, error) from error
    return model, (*findings, *diagram_findings)


def symbol_port_missing_finding(model: Model, error: SymbolPortError) -> Finding:
    """One `SYMBOL_PORT_MISSING` `ERROR` for a `SymbolPortError` layout raised (decision 0018).

    `error.function` is a Function of this model, or the whole Item of a one-view draw.
    Message: part mpn + `error`'s text; origin: PortTemplate, else Part, else `error.function`.
    """
    if error.function.kind == "item":
        item = items(model)[cast("Id[Item]", error.function)]
    else:
        item = items(model)[functions(model)[cast("Id[Function]", error.function)].item]
    part = model_parts(model).get(item.part) if item.part is not None else None
    mpn = part.mpn if part is not None else "no part"
    subject = symbol_port_subject(model, cast("Id[Function]", error.function), error.port_name)
    return Finding(
        code="SYMBOL_PORT_MISSING",
        severity=Severity.ERROR,
        subjects=(subject,),
        message=f"part {mpn!r}: {error}",
    )
