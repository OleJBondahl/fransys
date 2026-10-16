"""The list columns, terminal labels and cell text have one home: `derive.rows`.

`fransys_pdf._lists` and `fransys_reports.csv` may not import each other (root CLAUDE.md
invariant 2), so each used to keep its own copy of the header tuples and of the cell formatter,
pinned together here. They now import `fransys_model.derive`'s (`derive.rows`), so the
copies cannot drift; this file pins that neither module grows its own again, by identity.
"""

import pytest
from fransys_pdf import _contents as pdf_contents
from fransys_pdf import _diagrams, _drawings, _geometry, _lists, _lists_cells, _lists_terminal
from fransys_pdf import _lists as pdf
from fransys_pdf import document as pdf_document
from fransys_reports import csv as reports

from fransys_model import derive

_COLUMNS = (
    "BOM_COLUMNS",
    "CABLE_LIST_COLUMNS",
    "CONNECTOR_COLUMNS",
    "DESIGNATION_COLUMNS",
    "PIN_COLUMNS",
    "PLC_COLUMNS",
    "TERMINAL_COLUMNS",
    "WIRE_COLUMNS",
)
_HELPERS = ("cell_text", "column_rows", "pin_lines")
# The PDF prints the derive labels as they are; the CSV prints them in snake_case (below).
# The PDF connector table prints a pin's fields only (pdf-0030): no CONNECTOR_COLUMNS, no pin_lines.
_PDF_ONLY_CSV = {"CONNECTOR_COLUMNS", "pin_lines"}
_PDF_NAMES = (
    *(name for name in (*_COLUMNS, *_HELPERS) if name not in _PDF_ONLY_CSV),
    "TERMINAL_LABELS",
    "CONNECTOR_LABELS",
    "CELL_SEPARATOR",
    "cell_parts",
)
_REPORTS_NAMES = (*_COLUMNS, *_HELPERS)


def _is_derive_object(module: object, name: str) -> bool:
    """Whether `module.name` is the very object `fransys_model.derive.name`, not a copy."""
    return getattr(module, name) is getattr(derive, name)


def _pdf_object(name: str) -> object:
    """The pdf list module that holds `name`: the list helpers are split over three modules."""
    for module in (_lists, _lists_cells, _lists_terminal):
        if hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(name)


@pytest.mark.parametrize("name", _PDF_NAMES)
def test_pdf_lists_use_the_derive_object(name):
    assert _pdf_object(name) is getattr(derive, name)


@pytest.mark.parametrize("name", _REPORTS_NAMES)
def test_reports_csv_uses_the_derive_object(name):
    assert _is_derive_object(reports, name)


# CONTENTS has no CSV export (no contents.csv), so this is pdf-only, not
# folded into `_COLUMNS`/`_REPORTS_NAMES` above.
@pytest.mark.parametrize("name", ["CONTENTS_COLUMNS"])
def test_pdf_contents_uses_the_derive_object(name):
    assert _is_derive_object(pdf_contents, name)


def test_a_module_holding_its_own_copy_fails_the_identity_check(monkeypatch):
    """Can-fail twin: an EQUAL copy of a column tuple, in either module, is still caught."""
    for module in (pdf, reports):
        copy = (*derive.BOM_COLUMNS,)
        monkeypatch.setattr(module, "BOM_COLUMNS", copy)
        assert copy == derive.BOM_COLUMNS
        assert not _is_derive_object(module, "BOM_COLUMNS")
    monkeypatch.setattr(_lists_terminal, "TERMINAL_LABELS", dict(derive.TERMINAL_LABELS))
    assert not _is_derive_object(_lists_terminal, "TERMINAL_LABELS")
    copy = (*derive.CONTENTS_COLUMNS,)
    monkeypatch.setattr(pdf_contents, "CONTENTS_COLUMNS", copy)
    assert copy == derive.CONTENTS_COLUMNS
    assert not _is_derive_object(pdf_contents, "CONTENTS_COLUMNS")


def _first_label_mismatch(pdf_labels: dict[str, str], csv_labels: dict[str, str]) -> str | None:
    """The first field whose PDF label is not its CSV label spaced and upper-cased, or `None`.

    A PDF label is the CSV label with spaces for `_` and a capital first letter ("Side A" and
    `side_a`); a field named in only one map is a mismatch too.
    """
    if pdf_labels.keys() != csv_labels.keys():
        return next(iter(pdf_labels.keys() ^ csv_labels.keys()))
    return next(
        (
            field
            for field, label in pdf_labels.items()
            if label.replace(" ", "_").lower() != csv_labels[field]
        ),
        None,
    )


def _csv_labels() -> dict[str, str]:
    """The terminal CSV's header per field, as `fransys_reports.csv` derives it."""
    return {field: derive.csv_name(label) for field, label in derive.TERMINAL_LABELS.items()}


def test_terminal_labels_agree():
    assert _first_label_mismatch(derive.TERMINAL_LABELS, _csv_labels()) is None
    assert _csv_labels() == {"internal_ends": "side_a", "external_ends": "side_b"}
    assert set(derive.TERMINAL_LABELS) <= set(derive.TERMINAL_COLUMNS)  # they label real fields
    assert not hasattr(reports, "_TERMINAL_LABELS")  # pdf-0044: no second table
    assert not hasattr(_lists_cells, "_humanise")
    assert not hasattr(pdf_contents, "_HEADERS")
    assert pdf_contents.CONTENTS_LABELS is derive.CONTENTS_LABELS


def test_first_label_mismatch_names_the_one_differing_field():
    """Can-fail twin: a drifted label is named, and so is a field only one side labels."""
    drifted = {**_csv_labels(), "external_ends": "side_c"}
    assert _first_label_mismatch(derive.TERMINAL_LABELS, drifted) == "external_ends"
    extra = {**_csv_labels(), "index": "position"}
    assert _first_label_mismatch(derive.TERMINAL_LABELS, extra) == "index"


def test_pdf_holds_no_second_heading_table():
    """pdf-0044: the page and preset words and the drawing titles are derive's, by identity."""
    assert not hasattr(pdf_document, "_HEADING_WORDS")
    assert not hasattr(_geometry, "_PRESET_WORDS")
    assert pdf_document.PAGE_HEADINGS is derive.PAGE_HEADINGS
    assert _geometry.PRESET_HEADINGS is derive.PRESET_HEADINGS
    # the drawing titles reach pdf only inside render's title block (pdf-0046): pdf names none
    for module, name in (
        (_diagrams, "DIAGRAM_TITLE"),
        (_drawings, "SCHEMATIC_TITLE"),
        (_drawings, "HARNESS_DRAWING_TITLE"),
    ):
        assert not hasattr(module, name)
