"""The one home of printed headings: page kinds, presets, drawing titles, column labels."""

import pytest
from derive_helpers import frozen_with_library

from fransys_model import derive
from fransys_model.derive.page_headings import diagram_title, schematic_title
from fransys_model.kernel import Draft
from fransys_model.vocab import DocumentPreset, PageKind

MODEL = frozen_with_library(Draft())


def test_every_list_page_kind_has_a_heading_and_the_drawn_kinds_have_none():
    drawn = {PageKind.BLOCK_DIAGRAM, PageKind.SCHEMATIC, PageKind.HARNESS_DRAWING}
    assert set(derive.page_headings(MODEL)) == set(PageKind) - drawn


def test_every_preset_has_a_heading():
    assert set(derive.preset_headings(MODEL)) == set(DocumentPreset)


@pytest.mark.parametrize(
    ("field", "label"),
    [("designation", "Designation"), ("from_", "From"), ("cross_section_mm2", "Cross section mm2")],
)
def test_column_label(field, label):
    assert derive.column_label(field) == label


def test_csv_name_is_the_label_snake_cased():
    assert derive.csv_name("Side A") == "side_a"


def test_the_printed_words_are_pinned():
    """Expected values: a changed heading word is a visible output change, never a silent one."""
    assert {kind.name: words for kind, words in derive.page_headings(MODEL).items()} == {
        "COVER": "Cover",
        "NOTES": "Notes",
        "SHEET_INDEX": "Sheets",
        "CONTENTS": "Contents",
        "PLC_LIST": "PLC list",
        "TERMINAL_LIST": "Terminal list",
        "CONNECTOR_LIST": "Connector list",
        "WIRE_LABEL_LIST": "Wire label list",
        "DESIGNATION_LIST": "Designation list",
        "CABLE_LIST": "Cable list",
        "BOM": "BOM",
    }
    assert {p.name: words for p, words in derive.preset_headings(MODEL).items()} == {
        "CABINET_SCHEMATIC": "Cabinet schematic",
        "HARNESS_DRAWING": "Harness drawing",
        "PCB_SCHEMATIC": "PCB schematic",
        "SYSTEM": "System",
    }
    assert (diagram_title(MODEL), schematic_title(MODEL)) == ("Block diagram", "Schematic")
    assert derive.CONTENTS_LABELS == (
        "Designation",
        "MPN",
        "Description",
        "Cores",
        "Gauge",
        "Length mm",
        "Ends",
    )
