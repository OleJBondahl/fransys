"""Which builds need the schematic and the diagram layout, and laying them out (0118, 0119)."""

from typing import TYPE_CHECKING

from fransys_author import AuthorError

from fransys_layout import DiagramLayout, HintError, lay_out_diagrams
from fransys_model.derive import (
    DiagramSheet,
    document_ids,
    document_page_kinds,
)
from fransys_model.kernel import describe
from fransys_model.vocab import PageKind

from ._layout_core import NO_DRAWINGS, Laid, lay_out_on_core

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_model.kernel import Model


def kept_page_kinds(model: Model) -> frozenset[PageKind]:
    """The page kinds some document keeps: the one place that reads every document's pages."""
    return frozenset(kind for document in document_ids(model) for kind in document_page_kinds(model, document))


def needs_schematic_layout(model: Model) -> bool:
    """True when any document keeps a SCHEMATIC page, which reads the schematic's `layout.*`."""
    return PageKind.SCHEMATIC in kept_page_kinds(model)


def needs_diagram_layout(model: Model) -> bool:
    """True when any document keeps a BLOCK_DIAGRAM page, which reads `layout.diagram_*`."""
    return PageKind.BLOCK_DIAGRAM in kept_page_kinds(model)


def hint_error_to_author_error(model: Model, error: HintError) -> AuthorError:
    """The `AuthorError` for a layout hint error, its subjects shown as `file:line (key)` (0184)."""
    return AuthorError(describe(error, model))


def _schematic_if_needed(model: Model, library: Library, layout: Mapping[str, object] | None) -> Laid:
    if not needs_schematic_layout(model):
        return model, (), NO_DRAWINGS, {}
    try:
        return lay_out_on_core(model, library, layout)
    except HintError as error:
        raise hint_error_to_author_error(model, error) from error


def lay_out_if_needed(model: Model, library: Library, layout: Mapping[str, object] | None) -> tuple[Laid, DiagramLayout]:
    """The core layout and `lay_out_diagrams` when a document keeps their page, else nothing.

    The core layout's `Laid` (its findings include the diagram's) with the page `Drawing`s and
    page SVGs (empty when it did not run), then the `DiagramLayout` (empty likewise).
    """
    model, findings, drawn, svgs = _schematic_if_needed(model, library, layout)
    if not needs_diagram_layout(model):
        return (model, findings, drawn, svgs), DiagramLayout(diagrams=())
    try:
        diagrams, diagram_findings = lay_out_diagrams(model, library)
    except HintError as error:
        raise hint_error_to_author_error(model, error) from error
    return (model, (*findings, *diagram_findings), drawn, svgs), diagrams


def diagram_sheets_of(diagrams: DiagramLayout) -> tuple[DiagramSheet, ...]:
    """The `DiagramSheet` of every sheet `diagrams` placed: what derive and pdf read (R588)."""
    return tuple(DiagramSheet(unit=unit, number=number) for unit, number in diagrams.sheet_places())
