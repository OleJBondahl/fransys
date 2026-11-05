"""Field case: a unit with its own layout profile and DC power symbols, reported by fr.readability.
The bug: fr.readability raised KeyError on a page id, since power leads came from the top run for a page the unit run replaced.
Fixed by layout-0260, the report holds each page once, by the run that drew it, with that run's power leads."""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU

WIRE = (BU, 0.5)
PAGES = [0, 12]  # crossings per page: the pumps stair on the second
FEEDS = {1: "43", 2: "13", 3: "23"}  # pole -> the card pin its make throw feeds


class _Psu(NamedTuple):
    psu: Any


@fr.unit(
    "demo-control",
    revision=1,
    interface_version=1,
    date="2026-01-01",
    text="first",
    by="AB",
    title="Control",
    number="N-1",
)
def _control(d: Any) -> _Psu:
    d.layout.profile(hide_unused_pins=True)
    with d.function("B", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(5)]
        inputs = [d.device(f"D{i}", "DEMO-PLC-DI-2") for i in range(5)]
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    for lamp, di in zip(lamps, inputs, strict=True):
        d.series(psu.output["+"], lamp["1"], wire=WIRE)
        d.series(psu.output["+"], di.di_1["1"], wire=WIRE)
        d.series(psu.output["-"], lamp["2"], wire=WIRE)
    with d.function("PLC", "Outputs"):
        card = d.device("DO1", None, pins=("13", "14", "23", "24", "43", "44"), external=True)
    with d.function("K", "Relay"):
        relay = d.device("K1", "DEMO-RLY-4CO-24")
    for pole, pin in FEEDS.items():
        with d.function(f"Q{pole}", f"Pump {pole}"):
            lamp = d.device(f"H{pole}", "DEMO-LAMP-24")
            contact = getattr(relay, f"co_{pole}")
            d.series(psu.output["+"], contact[f"{pole}1"], wire=WIRE)
            d.series(contact[f"{pole}2"], lamp.lamp["1"], wire=WIRE)
            d.series(psu.output["-"], lamp.lamp["2"], wire=WIRE)
            d.series(contact[f"{pole}4"], card[pin], wire=WIRE)
    return _Psu(psu)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_control, "U1")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Control\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-control", cover=cover))


def test_readability_reports_a_unit_with_its_own_profile_and_power_symbols(
    built: fr.BuildResult,
) -> None:
    report = fr.readability(built)
    assert [page.wire_crossings for page in report.pages] == PAGES
