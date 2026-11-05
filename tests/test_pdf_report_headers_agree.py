"""The list columns, headings and cell text have one home: `fransys_model.derive`.

`fransys_pdf._lists` and `fransys_reports.csv` may not import each other (root CLAUDE.md
invariant 2), so each used to keep its own copy of the header tuples and of the cell formatter,
"""

import pytest
from fransys_pdf import _contents as pdf_contents
from fransys_pdf import _diagrams, _drawings, _geometry, _lists, _lists_cells, _lists_terminal
from fransys_pdf import document as pdf_document
from fransys_reports import csv as reports

from fransys_model import derive

# The deleted per-list constants (SO-C): no module may hold one again.
_DELETED = (
    "BOM_COLUMNS",
    "CABLE_LIST_COLUMNS",
    "CONNECTOR_COLUMNS",
    "CONTENTS_COLUMNS",
    "CORE_LIST_COLUMNS",
    "DESIGNATION_COLUMNS",
    "PIN_COLUMNS",
    "PLC_COLUMNS",
    "TERMINAL_COLUMNS",
    "WIRE_COLUMNS",
    "TERMINAL_LABELS",
    "WIRE_LABELS",
    "CONNECTOR_LABELS",
    "CONTENTS_LABELS",
)
_PDF_MODULES = (_lists, _lists_cells, _lists_terminal, pdf_contents)


def _is_derive_object(module: object, name: str) -> bool:
    """Whether `module.name` is the very object `fransys_model.derive.name`, not a copy."""
    return getattr(module, name) is getattr(derive, name)


def _pdf_object(name: str) -> object:
    """The pdf list module that holds `name`: the list helpers are split over four modules."""
    for module in _PDF_MODULES:
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(name)


@pytest.mark.parametrize("name", ["cell_parts", "CELL_SEPARATOR", "list_columns", "list_pdf_heading"])
def test_pdf_lists_use_the_derive_object(name):
    assert _pdf_object(name) is getattr(derive, name)


@pytest.mark.parametrize("name", ["cell_text", "column_rows", "pin_lines", "list_columns", "list_csv_header"])
def test_reports_csv_uses_the_derive_object(name):
    assert _is_derive_object(reports, name)


@pytest.mark.parametrize("name", _DELETED)
def test_no_module_keeps_a_column_or_label_constant(name):
    assert name not in derive.__all__
    assert not hasattr(derive, name)
    for module in (reports, *_PDF_MODULES):
        assert not hasattr(module, name)


def test_a_module_holding_its_own_copy_fails_the_identity_check(monkeypatch):
    """Can-fail twin: an EQUAL copy of a derive helper, in either module, is still caught."""

    def copy(*args, **kwargs):
        return derive.list_columns(*args, **kwargs)

    for module in (_lists, reports):
        monkeypatch.setattr(module, "list_columns", copy)
        assert not _is_derive_object(module, "list_columns")


def test_pdf_holds_no_second_heading_table():
    """pdf-0044: the page and preset words and the drawing titles are derive's, by identity."""
    assert not hasattr(pdf_document, "_HEADING_WORDS")
    assert not hasattr(_geometry, "_PRESET_WORDS")
    assert not hasattr(pdf_document, "PAGE_HEADINGS")  # read from the model's words
    assert not hasattr(_geometry, "PRESET_HEADINGS")
    # the drawing titles reach pdf only inside render's title block (pdf-0046): pdf names none
    for module, name in (
        (_diagrams, "DIAGRAM_TITLE"),
        (_drawings, "SCHEMATIC_TITLE"),
        (_drawings, "HARNESS_DRAWING_TITLE"),
    ):
        assert not hasattr(module, name)
