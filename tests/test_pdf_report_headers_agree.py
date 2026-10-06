"""The list columns, terminal labels and cell text have one home: `derive.rows` (spec P9).

`fransys_pdf._lists` and `fransys_reports.csv` may not import each other (root CLAUDE.md
invariant 2), so each used to keep its own copy of the header tuples and of the cell formatter,
pinned together here. They now import `fransys_model.derive`'s (`derive.rows`), so the
copies cannot drift; this file pins that neither module grows its own again, by identity.
"""

import pytest
from fransys_pdf import _contents as pdf_contents
from fransys_pdf import _lists as pdf
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
_PDF_NAMES = (*_COLUMNS, *_HELPERS, "TERMINAL_LABELS", "CELL_SEPARATOR", "cell_parts")
_REPORTS_NAMES = (*_COLUMNS, *_HELPERS)


def _is_derive_object(module: object, name: str) -> bool:
    """Whether `module.name` is the very object `fransys_model.derive.name`, not a copy."""
    return getattr(module, name) is getattr(derive, name)


@pytest.mark.parametrize("name", _PDF_NAMES)
def test_pdf_lists_use_the_derive_object(name):
    assert _is_derive_object(pdf, name)


@pytest.mark.parametrize("name", _REPORTS_NAMES)
def test_reports_csv_uses_the_derive_object(name):
    assert _is_derive_object(reports, name)


# CONTENTS has no CSV export (out of RW5's scope: no contents.csv), so this is pdf-only, not
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
    monkeypatch.setattr(pdf, "TERMINAL_LABELS", dict(derive.TERMINAL_LABELS))
    assert not _is_derive_object(pdf, "TERMINAL_LABELS")
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


def test_terminal_labels_agree():
    assert _first_label_mismatch(derive.TERMINAL_LABELS, reports._TERMINAL_LABELS) is None
    assert reports._TERMINAL_LABELS == {"internal_ends": "side_a", "external_ends": "side_b"}
    assert set(derive.TERMINAL_LABELS) <= set(derive.TERMINAL_COLUMNS)  # they label real fields


def test_first_label_mismatch_names_the_one_differing_field():
    """Can-fail twin: a drifted label is named, and so is a field only one side labels."""
    drifted = {**reports._TERMINAL_LABELS, "external_ends": "side_c"}
    assert _first_label_mismatch(derive.TERMINAL_LABELS, drifted) == "external_ends"
    extra = {**reports._TERMINAL_LABELS, "index": "position"}
    assert _first_label_mismatch(derive.TERMINAL_LABELS, extra) == "index"
