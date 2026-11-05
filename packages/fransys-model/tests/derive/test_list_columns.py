"""The list columns and their headings are the settings tables: today's literals, one home."""

lazy from pathlib import Path

import fransys as fr
import pytest

from fransys_model import derive
from fransys_model.kernel import SchemaError

# Per list, each column in order: (field, today's PDF heading, today's CSV header). The PDF
# connector table prints the pin fields only; the contents table has no CSV.
COLUMNS = {
    "terminal": (
        ("designation", "Designation", "designation"),
        ("group", "Group", "group"),
        ("index", "Index", "index"),
        ("internal_ends", "Side A", "side_a"),
        ("external_ends", "Side B", "side_b"),
        ("jumper_group", "Jumper group", "jumper_group"),
    ),
    "plc": (
        ("pin", "Pin", "pin"),
        ("channel_name", "Channel name", "channel_name"),
        ("signal", "Signal", "signal"),
        ("signal_name", "Signal name", "signal_name"),
        ("wired_to", "Wired to", "wired_to"),
    ),
    "bom": (
        ("mpn", "Mpn", "mpn"),
        ("revision", "Revision", "revision"),
        ("manufacturer", "Manufacturer", "manufacturer"),
        ("description", "Description", "description"),
        ("count", "Count", "count"),
        ("designations", "Designations", "designations"),
    ),
    "wires": (
        ("from_", "From", "from"),
        ("to", "To", "to"),
        ("colour", "Colour", "colour"),
        ("cross_section_mm2", "Cross section mm2", "cross_section_mm2"),
        ("ends", "Label", "label"),
    ),
    "designations": (
        ("designation", "Designation", "designation"),
        ("reference", "Reference", "reference"),
        ("description", "Description", "description"),
    ),
    "connectors": (
        ("designation", "Designation", "designation"),
        ("style", "Style", "style"),
        ("pincount", "Pincount", "pincount"),
        ("gender", "Gender", "gender"),
        ("mate_designation", "Mate designation", "mate_designation"),
        ("marking", "Pin", "marking"),
        ("net", "Net", "net"),
        ("mate_port_designation", "Mate", "mate_port_designation"),
        ("ends", "Ends", "ends"),
    ),
    "cables": (
        ("designation", "Designation", "designation"),
        ("mpn", "Mpn", "mpn"),
        ("description", "Description", "description"),
        ("core_count", "Core count", "core_count"),
        ("gauge_mm2", "Gauge mm2", "gauge_mm2"),
        ("length_mm", "Length mm", "length_mm"),
        ("from_label", "From label", "from_label"),
        ("to_label", "To label", "to_label"),
        ("pairs", "Pairs", "pairs"),
    ),
    "contents": (
        ("designation", "Designation", "Designation"),
        ("mpn", "MPN", "MPN"),
        ("description", "Description", "Description"),
        ("core_count", "Cores", "Cores"),
        ("gauge_mm2", "Gauge", "Gauge"),
        ("length_mm", "Length mm", "Length mm"),
        ("ends", "Ends", "Ends"),
    ),
    "cores": (
        ("cable", "Cable", "cable"),
        ("core", "Core", "core"),
        ("colour", "Colour", "colour"),
        ("pair", "Pair", "pair"),
        ("end_a", "End a", "end_a"),
        ("end_b", "End b", "end_b"),
        ("note", "Note", "note"),
    ),
}
PDF_COLUMNS = {
    "terminal": ("designation", "group", "index", "internal_ends", "external_ends"),
    "cables": (
        "designation",
        "mpn",
        "description",
        "core_count",
        "gauge_mm2",
        "length_mm",
        "from_label",
        "to_label",
    ),
    "connectors": ("marking", "net", "mate_port_designation", "ends"),
}
CASES = [(name, *column) for name, columns in COLUMNS.items() for column in columns]


def _model(path: Path | None = None):
    return fr.build(fr.design("demo_parts"), settings=fr.settings(path)).model


def test_the_lists_are_the_ruled_ones() -> None:
    assert tuple(COLUMNS) == (
        "terminal",
        "plc",
        "bom",
        "wires",
        "designations",
        "connectors",
        "cables",
        "contents",
        "cores",
    )


@pytest.mark.parametrize("name", COLUMNS)
def test_each_list_has_todays_columns(name: str) -> None:
    assert derive.list_columns(_model(), name) == tuple(c[0] for c in COLUMNS[name])


@pytest.mark.parametrize(("name", "columns"), PDF_COLUMNS.items())
def test_the_pdf_columns_are_the_ones_the_pdf_prints(name: str, columns: tuple[str, ...]) -> None:
    assert derive.list_pdf_columns(_model(), name) == columns


def test_a_list_with_no_pdf_columns_raises() -> None:
    with pytest.raises(SchemaError, match="no pdf_columns"):
        derive.list_pdf_columns(_model(), "bom")


@pytest.mark.parametrize(("name", "field", "heading", "header"), CASES)
def test_each_column_has_todays_pdf_heading_and_csv_header(name: str, field: str, heading: str, header: str) -> None:
    model = _model()
    assert derive.list_pdf_heading(model, name, field) == heading
    assert derive.list_csv_header(model, name, field) == header


def test_an_unknown_list_or_column_raises() -> None:
    model = _model()
    with pytest.raises(SchemaError, match='no list "nope"'):
        derive.list_columns(model, "nope")
    with pytest.raises(SchemaError, match='no column "nope"'):
        derive.list_pdf_heading(model, "bom", "nope")


def test_a_consumer_settings_file_reorders_a_list(tmp_path: Path) -> None:
    path = tmp_path / "fransys.toml"
    path.write_text(
        '[[lists.bom.columns]]\nfield = "description"\npdf = "description"\n'
        'csv = "csv_description"\n'
        '[[lists.bom.columns]]\nfield = "mpn"\npdf = "mpn"\ncsv = "csv_mpn"\n',
        encoding="utf-8",
    )
    model = _model(path)
    assert derive.list_columns(model, "bom") == ("description", "mpn")
    assert derive.list_pdf_heading(model, "bom", "mpn") == "MPN"
    assert derive.list_columns(model, "plc") == tuple(c[0] for c in COLUMNS["plc"])
