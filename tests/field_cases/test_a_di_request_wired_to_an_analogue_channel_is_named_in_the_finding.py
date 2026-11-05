"""Field case: a relay contact wired to both pins of an analogue input channel, with a digital input module in the same rack.
The bug: the request bound the analogue channel, and PLC_BINDING_SIGNAL_MISMATCH named only the asked kind, not the channel's kind.
Fixed by model-0211 (W2), the request binds the wired channel, and the finding names both kinds and both fixes."""

import fransys as fr
from _expected_codes import expect_codes
from fransys.colours import BK


def test_the_mismatch_names_the_kinds_the_channel_and_both_fixes() -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    ai = d.device("A2", "DEMO-PLC-AI-4", parent=rack)
    d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    motor = d.device("M1", "DEMO-RLY-2CO-24")
    d.series(motor.co_1["14"], ai.ai_1["1"], wire=(BK, 1.0))
    d.series(motor.co_1["11"], ai.ai_1["2"], wire=(BK, 1.0))
    motor.co_1.plc(fr.DI, "M1 status")
    result = fr.build(d)
    expect_codes(result, "PLC_BINDING_SIGNAL_MISMATCH")
    (found,) = (f for f in fr.check(result) if f.code == "PLC_BINDING_SIGNAL_MISMATCH")
    assert "asks for di but" in found.message
    assert "-A2:1" in found.message
    assert "is ai_current" in found.message
    assert "rewire" in found.message
    assert "ask for ai_current" in found.message
