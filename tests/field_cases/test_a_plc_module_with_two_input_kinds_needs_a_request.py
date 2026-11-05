"""Field case: a series to a module with two input kinds and no request raises, naming both.
The bug: with no rule the engineer could not tell the kind, and a guess would wire a button to an analogue loop.
Fixed by author-0047 (API-CLARITY C6.5, P3), the kind comes from the request, else the module's only kind; two kinds with none raise."""

lazy from pathlib import Path

import fransys as fr
import fransys_parts
import pytest
from fransys.colours import BU

from fransys_model.kernel import merge

_MIXED = """schema = 2
[part]
mpn = "T-PLC-MIX"
manufacturer = "Demo"
description = "PLC module with two digital and two analogue current inputs"
category = "plc_module"
class_code = "K"
"""


def _function(name: str, signal: str, channel: int, pins: tuple[str, ...]) -> str:
    ports = ", ".join(f'{{ name = "{p}", role = "generic" }}' for p in pins)
    return (
        f'[[function]]\nname = "{name}"\nkind = "plc_channel"\nports = [{ports}]\n[function.plc_channel]\nsignal = "{signal}"\nchannel = {channel}\n'
    )


def _design(tmp_path: Path) -> fr.Design:
    (tmp_path / "library.toml").write_text('schema = 2\nname = "t"\nversion = "0.0.0"\ndescription = "d"\n', encoding="utf-8")
    (tmp_path / "parts").mkdir()
    text = _MIXED + _function("di_1", "di", 1, ("1",)) + _function("di_2", "di", 2, ("2",))
    text += _function("ai_1", "ai_current", 1, ("3", "4"))
    (tmp_path / "parts" / "mix.toml").write_text(text, encoding="utf-8")
    draft = merge(fransys_parts.load("demo_parts"), fransys_parts.load_path(tmp_path))
    d = fr.Design(draft, place="C1")
    d.location("C1", "Cabinet")
    return d


def test_two_input_kinds_and_no_request_raises_naming_both(tmp_path: Path) -> None:
    d = _design(tmp_path)
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"), names=("P24", "P0"))
    button = d.device("S1", "DEMO-PB-NC")
    with pytest.raises(fr.AuthorError) as raised:
        d.series(dc.plus, button.sw, d.device("A1", "T-PLC-MIX"), wire=(BU, 0.75))
    message = str(raised.value)
    assert "A1" in message
    assert "di" in message
    assert "ai_current" in message
    assert ".plc(" in message


def test_a_request_settles_the_kind(tmp_path: Path) -> None:
    d = _design(tmp_path)
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"), names=("P24", "P0"))
    button = d.device("S1", "DEMO-PB-NC")
    button.sw.plc(fr.DI, "Start")
    d.series(dc.plus, button.sw, d.device("A1", "T-PLC-MIX"), wire=(BU, 0.75))
    rows = fr.derive.plc_channel_rows(fr.build(d).model)
    assert {row.pin for row in rows if row.signal_name == "Start"} == {"-A1:1"}
