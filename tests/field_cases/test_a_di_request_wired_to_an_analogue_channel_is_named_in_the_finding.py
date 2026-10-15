"""Field case: a request wired only to a channel of another signal kind says so (model-0211, W2).

The engineering shape: a relay contact is wired to both pins of an analogue input channel, and a
digital input module sits in the same rack. The contact asks for a digital input name.

The bug: the request bound the analogue channel and `PLC_BINDING_SIGNAL_MISMATCH` fired with a
message that named only the asked kind, not the channel's kind nor how to fix it.

The rule (decision model-0211): with no channel of the asked kind on the net, the request still
binds the wired channel and the finding names the asked kind, the channel, the channel's kind
and both fixes (rewire, or ask for that kind).
"""

import fransys as fr
from fransys.colours import BK


def test_the_mismatch_names_the_kinds_the_channel_and_both_fixes() -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    ai = d.device("A2", "DEMO-PLC-AI-4", parent=rack)
    d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    motor = d.device("M1", "DEMO-RLY-2CO-24")
    d.detail.wire(motor.co_1["14"], ai.ai_1["1"], wire=(BK, 1.0))
    d.detail.wire(motor.co_1["11"], ai.ai_1["2"], wire=(BK, 1.0))
    motor.co_1.plc(fr.DI, "M1 status")
    (found,) = (f for f in fr.check(fr.build(d)) if f.code == "PLC_BINDING_SIGNAL_MISMATCH")
    assert "asks for di but" in found.message
    assert "-A2:1" in found.message
    assert "is ai_current" in found.message
    assert "rewire" in found.message
    assert "ask for ai_current" in found.message
