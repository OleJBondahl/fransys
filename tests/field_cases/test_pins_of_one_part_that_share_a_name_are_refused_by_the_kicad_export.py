"""Field case: two pins of one part that would write one KiCad pin id are an ERROR.

The engineering shape: a board holds a sensor part with a footprint of two pads. The part has two
labelled connector functions, `main` (marking Main) and `voltage` (marking Voltage), and each
names its pins "1" and "6". That is legal: the drawing prints `-B1-Main:1` and `-B1-Voltage:1`.
A second part has one connector, and a third has unique pin names; both export unchanged.

The bug: the KiCad netlist keys a pin by its bare name, so `main:1` and `voltage:1` wrote one
pin "1" of B1. Wired to two different signals they were shorted with no finding.

Rule: the KiCad export refuses a part whose pins would write one KiCad pin id, wired or not. The
ERROR `PIN_ID_COLLISION` names the part, the pins and the fix "rename the part's pins so each is
its footprint pad name". Fixing decision: kicad-0006 (designer Ruling 19, Q3).
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest

if TYPE_CHECKING:
    from pathlib import Path

_HEAD = (
    'schema = 1\n\n[part]\nmpn = "{mpn}"\nmanufacturer = "Plant"\n'
    'description = "Planted sensor"\ncategory = "generic"\nclass_code = "B"\n\n'
    '[footprint]\nlibrary = "Plant"\nname = "Two_Pads"\n'
)
_CONNECTOR = (
    '\n[[function]]\nname = "{name}"\nkind = "connector"\nsymbol = "connector-fixed"\n'
    "ports = [\n{ports}]\n\n[function.connector]\n"
    'style = "header-2p"\npincount = 2\ngender = "male"\nmarking = "{marking}"\n'
)


def _port(name: str) -> str:
    return f'    {{ name = "{name}", role = "generic", symbol_port = "in" }},\n'


def _part(mpn: str, connectors: tuple[tuple[str, str, tuple[str, ...]], ...]) -> str:
    text = _HEAD.format(mpn=mpn)
    for name, marking, pins in connectors:
        ports = "".join(_port(pin) for pin in pins)
        text += _CONNECTOR.format(name=name, marking=marking, ports=ports)
    return text


_LIBRARY = "fieldcase_pin_id_parts"
_PARTS = {
    "PLANT-REPEAT": (("main", "Main", ("1", "6")), ("voltage", "Voltage", ("1", "6"))),
    "PLANT-ONE": (("main", "Main", ("1", "6")),),
    "PLANT-UNIQUE": (("main", "Main", ("1", "6")), ("voltage", "Voltage", ("2", "7"))),
}


def _library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    package = tmp_path / _LIBRARY
    (package / "parts").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "library.toml").write_text(
        f'schema = 1\nname = "{_LIBRARY}"\nversion = "0.1.0"\ndescription = "Planted"\n',
        encoding="utf-8",
    )
    for mpn, connectors in _PARTS.items():
        (package / "parts" / f"{mpn.lower()}.toml").write_text(
            _part(mpn, connectors), encoding="utf-8"
        )
    monkeypatch.syspath_prepend(str(tmp_path))
    return _LIBRARY


def _write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mpn: str, *, wired: bool) -> None:
    d = fr.design("demo_parts", _library(tmp_path, monkeypatch), place="CAB")
    board = d.device(None, "DEMO-PCB-IO", name="board")
    sensor = d.device("B1", mpn, parent=board)
    other = d.device("B2", "PLANT-UNIQUE", parent=board)
    if wired:
        d.detail.net("SIG1", sensor.main["1"], other.main["1"], kind=fr.SIGNAL)
        second = sensor.voltage["1"] if mpn == "PLANT-REPEAT" else sensor.main["6"]
        d.detail.net("SIG2", second, other.voltage["2"], kind=fr.SIGNAL)
    result = fr.build(d)
    fr.write(result, tmp_path / "out", intermediates=tmp_path / "tmp")


@pytest.mark.parametrize("wired", [True, False])
def test_two_pins_that_write_one_kicad_pin_id_are_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, wired: bool
) -> None:
    with pytest.raises(fr.BuildErrors) as raised:
        _write(tmp_path, monkeypatch, "PLANT-REPEAT", wired=wired)
    found = [f for f in raised.value.findings if f.code == "PIN_ID_COLLISION"]
    assert len(found) == 2  # pad 1 and pad 6, one finding each
    assert {f.severity for f in found} == {fr.Severity.ERROR}
    by_pad = {f.message.rsplit("pin id B1:", 1)[1].split(";")[0]: f for f in found}
    assert set(by_pad) == {"1", "6"}
    for pad, finding in by_pad.items():
        assert f"-B1-Main:{pad}" in finding.message
        assert f"-B1-Voltage:{pad}" in finding.message
        assert "rename the part's pins so each is its footprint pad name" in finding.fix


@pytest.mark.parametrize("mpn", ["PLANT-ONE", "PLANT-UNIQUE"])
def test_a_part_with_unique_pin_ids_exports_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mpn: str
) -> None:
    _write(tmp_path, monkeypatch, mpn, wired=True)
    (netlist,) = (tmp_path / "tmp").glob("netlist-*.net")
    text = netlist.read_text(encoding="utf-8")
    assert '(ref "B1") (pin "1")' in text
    assert '(ref "B1") (pin "6")' in text
