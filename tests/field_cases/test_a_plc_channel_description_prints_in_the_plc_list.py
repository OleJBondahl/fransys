"""Field case: a PLC channel carries a description, shown in the PLC list beside its name (PLC-DESCRIPTION, designer R1889, R1890).
The bug: a consumer with ~40 channels could name a channel but not say in words what it measures; the name is also the Wago channel Name.
Fixed by model-0443: `.plc(..., description=)`; the list has its own column; the Wago rack XML and the drawing do not change."""

import csv
lazy from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model.derive import plc_channel_rows, plc_list_rows

TEXT = "Door closed, main entrance"


def _design(description: str | None) -> fr.Design:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    plc = d.device("A1", "DEMO-PLC-DIO-MIXED", parent=rack)
    sensor = d.device("M1", "DEMO-RLY-2CO-24")
    d.series(sensor.co_1["14"], plc.di_1["I1"], wire=(BK, 1.0))
    strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 1)
    d.series(sensor.co_1["11"], strip[1].inner, wire=(BK, 1.0))
    sensor.co_1.plc(fr.DI, "Door", description=description)
    return d


def _written(tmp_path: Path, description: str | None) -> Path:
    out = tmp_path / ("with" if description else "without")
    fr.write(fr.build(_design(description)), out)
    return out / "data"


def test_the_plc_list_has_a_description_column_beside_the_name(tmp_path: Path) -> None:
    rows = list(csv.DictReader((_written(tmp_path, TEXT) / "plc.csv").open(encoding="utf-8")))
    door = [row for row in rows if row["signal_name"] == "Door"]
    assert door
    assert {row["description"] for row in door} == {TEXT}
    assert list(rows[0])[3:5] == ["signal_name", "description"]


def test_the_printed_list_cell_is_the_description() -> None:
    model = fr.build(_design(TEXT)).model
    cells = [cell for cell in plc_list_rows(model, plc_channel_rows(model)) if cell[3] == "Door"]
    assert cells
    assert {cell[4] for cell in cells} == {TEXT}


def test_a_channel_without_a_description_has_an_empty_cell(tmp_path: Path) -> None:
    rows = list(csv.DictReader((_written(tmp_path, None) / "plc.csv").open(encoding="utf-8")))
    assert {row["description"] for row in rows} == {""}


def test_the_wago_rack_xml_is_byte_identical_with_and_without_a_description(tmp_path: Path) -> None:
    with_text = (_written(tmp_path, TEXT) / "wago-U1.xml").read_bytes()
    assert b"Door" in with_text
    assert with_text == (_written(tmp_path, None) / "wago-U1.xml").read_bytes()


@pytest.mark.parametrize("blank", ["", "   ", "two\nlines"])
def test_a_blank_or_multi_line_description_raises_at_the_call(blank: str) -> None:
    with pytest.raises(fr.AuthorError, match="description"):
        _design(blank)


def test_a_module_channel_takes_no_description() -> None:
    d = fr.design("demo_parts")
    plc = d.device("A1", "DEMO-PLC-DIO-MIXED")
    with pytest.raises(fr.AuthorError, match=r"field device's \.plc request"):
        plc.di_1.plc(description=TEXT)
