"""Field case: the PLC list names the pin of a later channel, one row per pin.

The engineering shape: a 4-channel analog input card whose channels 1 to 4 sit on pins 1 to 8
(channel 1 on pins 1 and 2, channel 2 on pins 5 and 6, ...), each channel wired to its own header.

The bug: the list printed one row per channel, and its designation was the module and the
channel number (`-A2:2`), a pin the card does not have; the builder looking for channel 2's
terminal found pin 2. A row also carried both pins' far ends in one cell.
The fix is decision model-0209: one row per pin, the pin printed by the port designation
(`-A2:5`), the channel's own number in its own column, and that pin's far end alone.
"""

import fransys as fr
import pytest

from fransys_model.derive import plc_channel_rows

_PINS = {"ai_1": ("1", "2"), "ai_2": ("5", "6"), "ai_3": ("3", "4"), "ai_4": ("7", "8")}


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    card = d.device("A2", "DEMO-PLC-AI-4")
    for number, (channel, pins) in enumerate(_PINS.items(), start=1):
        header = d.device(f"J{number}", "DEMO-CONN-2P")
        for header_pin, pin in zip(("1", "2"), pins, strict=True):
            d.detail.wire(header[header_pin], getattr(card, channel)[pin], wire=("WH", 0.5))
    return fr.build(d)


def test_the_pin_of_channel_2_is_a2_5_never_a2_2(built: fr.BuildResult) -> None:
    pins = [(row.pin, row.channel_name) for row in plc_channel_rows(built.model)]
    assert ("-A2:5", "2") in pins
    assert ("-A2:2", "2") not in pins


def test_the_list_has_one_row_per_pin_in_pin_order_inside_each_channel(
    built: fr.BuildResult,
) -> None:
    rows = plc_channel_rows(built.model)
    assert [row.pin for row in rows] == [f"-A2:{pin}" for pin in "12563478"]


def test_each_pin_prints_its_own_far_end(built: fr.BuildResult) -> None:
    far = {row.pin: row.wired_to for row in plc_channel_rows(built.model)}
    assert far == {
        "-A2:1": "+C1-J1:1",
        "-A2:2": "+C1-J1:2",
        "-A2:5": "+C1-J2:1",
        "-A2:6": "+C1-J2:2",
        "-A2:3": "+C1-J3:1",
        "-A2:4": "+C1-J3:2",
        "-A2:7": "+C1-J4:1",
        "-A2:8": "+C1-J4:2",
    }
