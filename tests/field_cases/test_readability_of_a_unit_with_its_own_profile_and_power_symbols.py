"""Field case: `fr.readability` of a unit with its own layout profile and a DC supply reports.

The engineering shape: a released unit sets its own profile (hide unused pins, a narrow column
gap). It holds a PSU with a 24 V supply, lamps and PLC inputs on that supply, so its pages carry
power symbols, and three pumps whose relay poles feed an output card's pins 43, 13 and 23.

The bug: `fr.readability` raised KeyError on a `layout.page` id. The unit's pages are laid out
in a run of their own profile and get other ids than the top design's run; the page report kept
the top run's power leads for the pages the unit run replaced, and looked up an id the built
model does not hold. A consumer's release report called it and so could not state its figures.

The rule (decision layout-0260): the report holds each page once, by the run that drew it, with
that run's power leads, and a page's crossings are the router meter's.
"""

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
    d.layout.profile(hide_unused_pins=True, column_gap=16)
    with d.function("B", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(5)]
        inputs = [d.device(f"D{i}", "DEMO-PLC-DI-2") for i in range(5)]
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    for lamp, di in zip(lamps, inputs, strict=True):
        d.detail.wire(psu.output["+"], lamp["1"], wire=WIRE)
        d.detail.wire(psu.output["+"], di.di_1["1"], wire=WIRE)
        d.detail.wire(psu.output["-"], lamp["2"], wire=WIRE)
    with d.function("PLC", "Outputs"):
        card = d.device("DO1", None, pins=("13", "14", "23", "24", "43", "44"), external=True)
    with d.function("K", "Relay"):
        relay = d.device("K1", "DEMO-RLY-4CO-24")
    for pole, pin in FEEDS.items():
        with d.function(f"Q{pole}", f"Pump {pole}"):
            lamp = d.device(f"H{pole}", "DEMO-LAMP-24")
            contact = getattr(relay, f"co_{pole}")
            d.detail.wire(psu.output["+"], contact[f"{pole}1"], wire=WIRE)
            d.detail.wire(contact[f"{pole}2"], lamp.lamp["1"], wire=WIRE)
            d.detail.wire(contact[f"{pole}4"], card[pin], wire=WIRE)
    return _Psu(psu)


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_control, "U1")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Control\n", encoding="utf-8")
    return fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-control", cover=cover)
    )


def test_readability_reports_a_unit_with_its_own_profile_and_power_symbols(
    built: fr.BuildResult,
) -> None:
    report = fr.readability(built)
    assert [page.wire_crossings for page in report.pages] == PAGES
