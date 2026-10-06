from pathlib import Path

import pytest
from fransys_reports import (
    bom_csv,
    connectors_csv,
    designations_csv,
    plc_csv,
    terminal_csv,
    wires_csv,
)

from fransys_model.derive import connector_rows
from fransys_model.derive.designation import own_designation_or_none
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item

GOLDEN = Path(__file__).resolve().parent / "golden"

pytestmark = pytest.mark.wp("reports")


def _golden(name):
    return (GOLDEN / name).read_bytes().decode("utf-8")


def test_terminal_csv_includes_unused_terminals(cabinet, strip):
    lines = terminal_csv(cabinet, strip).splitlines()
    # N:1 has no conductor and no jumper: a row of empty cells, not a marker string
    assert "-X1:N:1,N,1,,," in lines
    assert len(lines) == 5  # the header and the strip's four terminals


def test_terminal_csv_names_where_each_conductor_goes_and_the_jumper_group(cabinet, strip):
    lines = terminal_csv(cabinet, strip).splitlines()
    # L:1 is jumpered to L:2 (group 1) and has two conductors inside and one outside
    assert "-X1:L:1,L,1,-X1:L:2; -K1:1,-B1:1,1" in lines
    assert "-X1:L:2,L,2,-X1:L:1,,1" in lines
    # wired on both sides, in no jumper group; B7 sits at +C1 and no context is given: full path
    assert "-X1:S:1,S,1,-F1:1,+C1-B7:1," in lines


def test_terminal_csv_of_a_strip_with_no_terminals_is_the_header(new_plant):
    plant = new_plant()
    plant.item("x1", "X1")
    assert terminal_csv(plant.model(), make_id(Item, ("x1",))) == (
        "designation,group,index,side_a,side_b,jumper_group\n"
    )


def test_bom_excludes_not_installed(cabinet):
    csv_text = bom_csv(cabinet)
    not_installed = {
        text
        for item in cabinet.tables["item"].values()
        if not item.installed and (text := own_designation_or_none(cabinet, item)) is not None
    }
    assert not_installed == {"K3"}
    assert not any(designation in csv_text for designation in not_installed)


def test_bom_counts_the_same_item_once_it_is_installed(cabinet_k3_installed):
    assert "-K1; -K2; -K3" in bom_csv(cabinet_k3_installed)
    assert bom_csv(cabinet_k3_installed) != _golden("bom.csv")


@pytest.mark.parametrize(
    ("golden", "make"),
    [
        ("terminals.csv", terminal_csv),
        ("bom.csv", lambda model, _strip: bom_csv(model)),
        ("plc.csv", lambda model, _strip: plc_csv(model)),
        ("wires.csv", lambda model, _strip: wires_csv(model)),
        ("designations.csv", lambda model, _strip: designations_csv(model)),
    ],
)
def test_csv_matches_golden_bytes(cabinet, strip, golden, make):
    assert make(cabinet, strip) == _golden(golden)


def test_connectors_csv_matches_golden_bytes(board_model, board):
    assert connectors_csv(board_model, board) == _golden("connectors.csv")


def test_connectors_csv_is_one_line_per_pin_with_the_connector_repeated(board_model, board):
    lines = connectors_csv(board_model, board).splitlines()[1:]
    assert [line.split(",")[0] for line in lines] == ["-J1"] * 4 + ["-J2"] * 2
    assert lines[0].split(",")[:5] == lines[3].split(",")[:5]  # the connector's fields, repeated
    assert lines[0].split(",")[5:] != lines[3].split(",")[5:]  # the pin's fields, not


def test_a_connector_with_no_pins_has_no_line(board_model, board):
    # J3 is a connector of the board (pincount 2) with no port declared: a row, no pin
    assert "-J3" in [row.designation for row in connector_rows(board_model, board)]
    assert "-J3" not in connectors_csv(board_model, board)
