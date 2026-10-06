"""`context=` of `terminal_csv`, `wires_csv` and `connectors_csv` (model-0054 section 4).

`None` is the no-unit context: every located end prints its full location path. A location node
as the context prints an end inside it short and one outside it with its path in front. The
invented plant: strip `X1` at `C1`, its terminal wired inside to `B12` (at `C1`) and outside to
`M1` (at `EXT`).
"""

import csv
import io

import pytest
from fransys_reports import connectors_csv, plc_csv, terminal_csv, wires_csv

from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import SignalType

pytestmark = pytest.mark.wp("reports")


def _rows(text):
    return list(csv.DictReader(io.StringIO(text)))


@pytest.fixture
def located(new_plant):
    """(model, strip, c1, ext): terminal `T:1` of `X1` wired to `B12` inside and `M1` outside."""
    plant = new_plant()
    c1 = plant.location("c1", "C1")
    ext = plant.location("ext", "EXT")
    strip = plant.item("x1", "X1")
    inside, outside = plant.terminal(strip, "T", 1)
    b12 = plant.pin("b12", "B12")
    m1 = plant.pin("m1", "M1")
    plant.label(plant.wire(inside, b12, "w1"), "W1")
    plant.label(plant.wire(outside, m1, "w2"), "W2")
    plant.place(strip, c1)
    plant.place(make_id(Item, ("b12",)), c1)
    plant.place(make_id(Item, ("m1",)), ext)
    return plant.model(), strip, c1, ext


def test_terminal_csv_without_a_context_prints_every_located_end_with_its_full_path(located):
    model, strip, _c1, _ext = located
    (row,) = _rows(terminal_csv(model, strip))
    assert (row["side_a"], row["side_b"]) == ("+C1-B12:1", "+EXT-M1:1")


def test_terminal_csv_in_a_context_prints_the_inside_end_short_and_the_outside_end_with_its_path(
    located,
):
    model, strip, c1, _ext = located
    (row,) = _rows(terminal_csv(model, strip, context=c1))
    assert (row["side_a"], row["side_b"]) == ("-B12:1", "+EXT-M1:1")


def _wire_ends(text):
    """Each wire row's two ends as a set, in the file's order."""
    return [{row["from"], row["to"]} for row in _rows(text)]


def test_wires_csv_without_a_context_prints_every_located_end_with_its_full_path(located):
    model, *_ = located
    assert sorted(_wire_ends(wires_csv(model)), key=sorted) == [
        {"+C1-B12:1", "+C1-X1:T:1"},
        {"+EXT-M1:1", "+C1-X1:T:1"},
    ]


def test_wires_csv_in_a_context_prints_the_inside_ends_short(located):
    model, _strip, c1, _ext = located
    assert sorted(_wire_ends(wires_csv(model, context=c1)), key=sorted) == [
        {"+EXT-M1:1", "-X1:T:1"},
        {"-B12:1", "-X1:T:1"},
    ]


def test_wires_csv_takes_unit_and_context_together(new_plant):
    plant = new_plant()
    unit = plant.unit("u1", "unit-one")
    c1 = plant.location("c1", "C1")
    a = plant.pin("a", "A1", unit=unit)
    b = plant.pin("b", "A2", unit=unit)
    plant.label(plant.wire(a, b, "w"), "W1")
    plant.place(make_id(Item, ("a",)), c1)
    plant.place(make_id(Item, ("b",)), plant.location("ext", "EXT"))
    (row,) = _rows(wires_csv(plant.model(), unit=unit, context=c1))
    assert {row["from"], row["to"]} == {"-A1:1", "+EXT-A2:1"}


@pytest.fixture
def housed_board(board_draft):
    """(model, board, ext): board `JB1` and its mate housing `H1` (mate pins `P1:...`) at `EXT`."""
    ext = board_draft.location("ext", "EXT")
    board_draft.place(make_id(Item, ("h1",)), ext)
    return board_draft.model(), make_id(Item, ("jb1",)), ext


def test_connectors_csv_without_a_context_prints_a_located_mate_pin_with_its_full_path(
    housed_board,
):
    model, board, _ext = housed_board
    mates = {row["mate_port_designation"] for row in _rows(connectors_csv(model, board))}
    assert "+EXT-P1:1" in mates
    assert "-P1:1" not in mates


def test_connectors_csv_in_the_mates_own_location_prints_its_mate_pin_short(housed_board):
    model, board, ext = housed_board
    mates = {
        row["mate_port_designation"] for row in _rows(connectors_csv(model, board, context=ext))
    }
    assert "-P1:1" in mates
    assert "+EXT-P1:1" not in mates


@pytest.fixture
def wired_channels(new_plant):
    """(model, c1): module `A1`'s channel 1 wired to `B12` at `EXT`, channel 2 to `B13` at `C1`."""
    plant = new_plant()
    c1 = plant.location("c1", "C1")
    ext = plant.location("ext", "EXT")
    first, second = plant.channels("mod", "A1", (SignalType.DI, SignalType.DI))
    plant.wire(plant.port(first, "1"), plant.pin("b12", "B12"), "w1")
    plant.wire(plant.port(second, "1"), plant.pin("b13", "B13"), "w2")
    plant.place(make_id(Item, ("b12",)), ext)
    plant.place(make_id(Item, ("b13",)), c1)
    return plant.model(), c1


def test_plc_csv_names_the_far_end_of_each_channel_and_no_field_device(wired_channels):
    model, _c1 = wired_channels
    text = plc_csv(model)
    assert text.splitlines()[0] == "channel_designation,signal,wired_to,signal_name"
    assert [(row["channel_designation"], row["wired_to"]) for row in _rows(text)] == [
        ("-A1:1", "+EXT-B12:1"),
        ("-A1:2", "+C1-B13:1"),
    ]


def test_plc_csv_in_a_context_prints_the_inside_end_short_and_the_outside_end_with_its_path(
    wired_channels,
):
    model, c1 = wired_channels
    assert [row["wired_to"] for row in _rows(plc_csv(model, context=c1))] == [
        "+EXT-B12:1",
        "-B13:1",
    ]
