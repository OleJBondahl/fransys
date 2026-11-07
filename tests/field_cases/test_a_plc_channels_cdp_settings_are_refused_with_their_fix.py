"""Field case: the calls that set a channel's CDP settings refuse what has no meaning (WAGO-CDP, designer R1823, R1824).
The bug: a repeated signal name, a scale on a digital spare and a channel both left out and named went through silently.
Fixed by R1824: an `AuthorError` at the call, and `PLC_SIGNAL_NAME_TWICE` and `SCALING_NOT_ANALOGUE` from the checks."""

import fransys as fr
import pytest
from _expected_codes import expect_codes
from fransys.colours import BK


def _wired_relay(d: fr.Design, tag: str, channel: fr.Pin, strip: fr.TerminalStrip, at: int):
    relay = d.device(tag, "DEMO-RLY-2CO-24")
    d.series(relay.co_1["14"], channel, wire=(BK, 1.0))
    d.series(relay.co_1["11"], strip[at].inner, wire=(BK, 1.0))
    return relay


def test_two_devices_of_one_controller_with_one_signal_name_are_an_error() -> None:
    d = fr.design("demo_parts")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=d.rack("U1"))
    strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 2)
    _wired_relay(d, "M1", di.di_1["1"], strip, 1).co_1.plc(fr.DI, "Door")
    _wired_relay(d, "M2", di.di_2["2"], strip, 2).co_1.plc(fr.DI, "Door")
    expect_codes(fr.build(d), "PLC_SIGNAL_NAME_TWICE")


def test_a_scale_on_a_digital_spare_is_an_error() -> None:
    d = fr.design("demo_parts")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=d.rack("U1"))
    di.di_1.plc(name="unused").scale("%", raw=(0, 1), eng=("0", "1"))
    expect_codes(fr.build(d), "SCALING_NOT_ANALOGUE")


def test_calls_that_cannot_carry_what_they_are_given_raise_with_the_fix() -> None:
    d = fr.design("demo_parts")
    ai = d.device("A1", "DEMO-PLC-AI-4", parent=d.rack("U1"))
    relay = d.device("K1", "DEMO-RLY-2CO-24")
    with pytest.raises(fr.AuthorError, match="drop the name"):
        ai.ai_1.plc(name="x", configured=False)
    ai.ai_2.scale("%", raw=(0, 1), eng=("0", "1"))
    with pytest.raises(fr.AuthorError, match="drop the scale"):
        ai.ai_2.plc(configured=False)
    ai.ai_3.plc(configured=False)
    with pytest.raises(fr.AuthorError, match="drop the scale"):
        ai.ai_3.scale("%", raw=(0, 1), eng=("0", "1"))
    with pytest.raises(fr.AuthorError, match="has its signal already"):
        ai.ai_4.plc(fr.AI, "x")
    with pytest.raises(fr.AuthorError, match="device function"):
        relay.co_1.plc(name="x")
    with pytest.raises(fr.AuthorError, match="configured=False belongs on a module's channel"):
        relay.co_1.plc(fr.AI, "x", configured=False)
    with pytest.raises(fr.AuthorError, match="one line"):
        relay.co_1.scale("", raw=(0, 1), eng=("0", "1"))
