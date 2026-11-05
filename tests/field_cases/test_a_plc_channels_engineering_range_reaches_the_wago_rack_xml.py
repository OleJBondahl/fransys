"""Field case: an analogue input channel with an engineering range (0 to 100 % over 4 to 20 mA) written on its request.
The bug: 0.22 dropped `.scale`, so the Wago rack XML lost the channel's Unit and ScalingOperator that 0.21.2 wrote.
Fixed by model-0425, `.scale(unit, raw=, eng=)` returns and the rack XML is byte-identical to 0.21.2."""

from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path


def test_the_range_written_on_the_request_is_in_the_rack_xml(tmp_path: Path) -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    ai = d.device("A2", "DEMO-PLC-AI-4", parent=rack)
    sensor = d.device("M1", "DEMO-RLY-2CO-24")
    d.series(sensor.co_1["14"], ai.ai_1["1"], wire=(BK, 1.0))
    d.series(sensor.co_1["11"], ai.ai_1["2"], wire=(BK, 1.0))
    sensor.co_1.plc(fr.AI, "level").scale("%", raw=(4, 20), eng=("0", "100"))
    written = fr.write(fr.build(d), tmp_path)
    (xml,) = (p for p in written if p.name.endswith(".xml") and "wago" in p.name)
    text = xml.read_text(encoding="utf-8")
    assert 'Unit="%"' in text
    assert 'InValue="4"' in text
    assert 'OutValue="100"' in text
