"""Which builds need the schematic and the diagram layout, and laying them out (0118, 0119)."""

from typing import TYPE_CHECKING, cast

import fransys_pdf

from fransys_layout import SymbolPortError, lay_out_diagrams, lay_out_schematic
from fransys_model.kernel import Finding, Severity
from fransys_model.vocab import PageKind, documents, functions, items, port_templates
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


def _schematic_if_needed(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    if not needs_schematic_layout(model):
        return model, ()
    try:
        return lay_out_schematic(model)
    except SymbolPortError as error:
        return model, (symbol_port_missing_finding(model, error),)


def lay_out_if_needed(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """`lay_out_schematic` and `lay_out_diagrams` when a document keeps their page, else nothing.

    A layout `SymbolPortError` becomes one `SYMBOL_PORT_MISSING` `ERROR`, the model unchanged.
    """
    model, findings = _schematic_if_needed(model)
    if not needs_diagram_layout(model):
        return model, findings
    model, diagram_findings = lay_out_diagrams(model)
    return model, (*findings, *diagram_findings)


def symbol_port_missing_finding(model: Model, error: SymbolPortError) -> Finding:
    """One `SYMBOL_PORT_MISSING` `ERROR` for a `SymbolPortError` layout raised (decision 0018).

    `error.function` is a Function of this model, or the whole Item of a one-view draw.
    Message: part mpn + `error`'s text; origin: PortTemplate, else Part, else `error.function`.
    """
    if error.function.kind == "item":
        function = None
        item = items(model)[cast("Id[Item]", error.function)]
    else:
        function = functions(model)[cast("Id[Function]", error.function)]
        item = items(model)[function.item]
    part = model_parts(model).get(item.part) if item.part is not None else None
    mpn = part.mpn if part is not None else "no part"
    port_template = (
        next(
            (
                candidate
                for candidate in port_templates(model).values()
                if candidate.function == function.template and candidate.name == error.port_name
            ),
            None,
        )
        if function is not None and function.template is not None
        else None
    )
    if port_template is not None:
        subject = port_template.id
    elif part is not None:
        subject = part.id
    else:
        subject = error.function
    return Finding(
        code="SYMBOL_PORT_MISSING",
        severity=Severity.ERROR,
        subjects=(subject,),
        message=f"part {mpn!r}: {error}",
    )
