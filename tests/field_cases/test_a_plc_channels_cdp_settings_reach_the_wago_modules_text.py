"""Field case: one rack's `<Modules>` written as the CDP reference reads (WAGO-CDP, designer R1820, R1823).
The bug: channels were named by designation, analogue ones had a Nr, and routing, a spare's name, no unit and a hole in Nr were missing.
Fixed by R1820 and R1823: facts from `derive`; the text equals the reference fixture of invented names."""

from pathlib import Path

import fransys as fr
from fransys.colours import BK

FIXTURE = Path(__file__).parent / "data" / "wago_cdp_modules.xml"


def _design() -> fr.Design:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    ai = d.device("A1", "DEMO-PLC-AI-4", parent=rack)
    sensors = [d.device(f"M{n}", "DEMO-RLY-2CO-24") for n in (1, 2)]
    for sensor, channel, pins in zip(sensors, (ai.ai_1, ai.ai_2), (("1", "2"), ("5", "6")), strict=True):
        d.series(sensor.co_1["14"], channel[pins[0]], wire=(BK, 1.0))
        d.series(sensor.co_1["11"], channel[pins[1]], wire=(BK, 1.0))
    sensors[0].co_1.plc(fr.AI, "Tank_level_A", routing="Controller.Section.Tank_level_A").scale(raw=(0, 32767), eng=("0", "100"))
    sensors[1].co_1.plc(fr.AI, "Tank_level_B", routing="")
    ai.ai_3.plc(name="unused").scale("%", raw=(0, 32767), eng=("0", "100"))
    mixed = d.device("A2", "DEMO-PLC-DIO-MIXED", parent=rack)
    mixed.do_1.plc(configured=False)
    strip = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 4)
    for n, (signal_name, channel, pin) in enumerate((("Door", mixed.di_1, "I1"), ("Gate", mixed.di_2, "I2")), start=3):
        sensor = d.device(f"M{n}", "DEMO-RLY-2CO-24")
        d.series(sensor.co_1["14"], channel[pin], wire=(BK, 1.0))
        d.series(sensor.co_1["11"], strip[n - 2].inner, wire=(BK, 1.0))
        sensor.co_1.plc(fr.DI, signal_name)
    coil = d.device("K1", "DEMO-RLY-2CO-24")
    d.series(mixed.do_2["O2"], coil.coil["A1"], wire=(BK, 1.0))
    d.series(coil.coil["A2"], strip[4].inner, wire=(BK, 1.0))
    coil.coil.plc(fr.DO, "Fan")
    return d


def _modules(tmp_path: Path) -> str:
    written = fr.write(fr.build(_design()), tmp_path)
    (xml,) = (p for p in written if p.name.endswith(".xml") and "wago" in p.name)
    text = xml.read_text(encoding="utf-8")
    return text[text.index("<Modules>") : text.index("</Modules>") + len("</Modules>\n")]


def test_the_modules_text_equals_the_reference_fixture(tmp_path: Path) -> None:
    assert _modules(tmp_path) == FIXTURE.read_text(encoding="utf-8")
