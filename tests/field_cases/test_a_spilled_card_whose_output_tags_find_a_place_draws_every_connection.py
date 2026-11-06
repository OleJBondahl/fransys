"""Field case: a controller card with ten attached columns spills two of them (CARD_OVERFULL); three outputs and the USB pin carry tag pairs.
The bug: the GND56 lane's end was walked to its arrow stand through the card's own placed tag markers, so the tags found no place:
MARKER_UNPLACED, CONNECTION_NOT_DRAWN and DANGLING_WIRE_END. Fixed by layout-0553 (R1790): a marker is never crossed, even by its own fan."""

import re
import shutil
from pathlib import Path
from typing import NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU

DATA = Path(__file__).parent / "data" / "spill_parts"
CODES = ("CONNECTION_NOT_DRAWN", "MARKER_UNPLACED", "DANGLING_WIRE_END")
LABELS = ("OUT1-", "OUT2-", "OUT3-", "IN1B", "IN2B", "GND56", "IN6", "CANL", "D+", "D-", "GND")
WIDER = {label: f"{label}-WIDE-LABEL" for label in LABELS}
NARROWER = {
    "OUT1-": "O1",
    "OUT2-": "O2",
    "OUT3-": "O3",
    "IN1B": "I1",
    "IN2B": "I2",
    "GND56": "G5",
    "IN6": "I6",
    "CANL": "CL",
    "D+": "P",
    "D-": "N",
    "GND": "G",
}


class Io(NamedTuple):
    """Interface."""


def _unit(names: dict[str, str]):
    @fr.unit("repro", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def unit(d: fr.Design) -> Io:
        """Controller B1 outputs 1-3 drive relays R1-R3, whose contacts switch contactors C1, C2; B1 USB goes to socket J1."""
        c1, c2 = d.device("C1", "REPRO-CON-A"), d.device("C2", "REPRO-CON-A")
        m1 = d.device("M1", "REPRO-MON")
        t1 = d.terminal_strip("T1", "REPRO-TB", 5, interface=(1, 2, 3, 4), bridged=(3, 5))
        t2 = d.terminal_strip("T2", "REPRO-TB", 15, interface=(1, 2, 3, 4, 5, 6), bridged=(2, 15), rail=True)
        t3 = d.terminal_strip("T3", "REPRO-TB", 14, bridged=(2, 14), rail=True)
        t4 = d.terminal_strip("T4", "REPRO-TB", 4, interface=True)
        p1 = d.device("P1", "REPRO-DCS")
        s1, s2 = d.device("S1", "REPRO-RLY-B"), d.device("S2", "REPRO-RLY-B")
        j1, b1 = d.device("J1", "REPRO-USB"), d.device("B1", "REPRO-CTRL")
        r1, r2, r3 = (d.device(f"R{n}", "REPRO-RLY-A") for n in (1, 2, 3))
        rack = d.rack("RK")
        n1 = d.device("N1", "REPRO-NODE", parent=rack, position=1)
        dc = d.dc_supply("24VDC", plus=p1.f144["p134"], minus=p1.f144["p136"], voltage=24, names=("24V", "GND"))
        wires = [
            (dc.plus, t2[2]),
            (dc.minus, t3[2]),
            (t2[3].inner, b1.f73["p33"]),
            (t2[7].inner, n1.f126["p93"]),
            (t2[4].inner, r1.coil.A1),
            (t2[5].inner, r2.coil.A1),
            (t2[8].inner, r3.coil.A1),
            (b1.f73, t3[3]),
            (b1.f87, t3[7]),
            (n1.f126, t3[4]),
            (c1.coil, t3[8]),
            (c2.coil, t3[5]),
            (s1.coil, t3[6]),
            (s2.coil, t3[10]),
            (r1.coil, b1.f76),
            (r2.coil, b1.f77),
            (r3.coil, b1.f78),
            (c1.aux.T1, b1.f82[names["IN1B"]]),
            (c1.aux, b1.f82),
            (c2.aux.T1, b1.f83[names["IN2B"]]),
            (c2.aux, b1.f83),
        ]
        for a, b in wires:
            d.series(a, b, wire=0.5)
        d.series(t2[6], s1.co_1[11], wire=1.0)
        d.series(t4[4].inner, s2.coil.A1, wire=(BU, 0.5))
        d.series(s1.co_1.no, s2.co_1.no, wire=1.0)
        d.series(s2.co_1.no, r1.co[14], wire=1.0)
        d.series(s2.co_1.no, r2.co[14], wire=1.0)
        d.series((r1.co[11],), (c1.coil.X1,), wire=0.5)
        d.series((r2.co[11],), (c2.coil.X1,), wire=0.5)
        d.series(b1.f92, j1.f5, wire=(BU, 0.5))
        d.series(t1[2].inner, s1.coil.A1, wire=(BU, 0.5))
        d.series(m1.f28["p14"], b1.f86[names["GND56"]], wire=(BU, 0.5))
        d.series(b1.f89[names["CANL"]], n1.f130["p118"], wire=(BU, 0.25))
        return Io()

    return unit


def _library(tmp: Path, name: str, names: dict[str, str]) -> None:
    """A copy of the parts set as the package `name`, the controller's card labels renamed by `names`."""
    shutil.copytree(DATA, tmp / name, ignore=shutil.ignore_patterns("__pycache__"))
    ctrl = tmp / name / "parts" / "repro-ctrl.toml"
    text = ctrl.read_text()
    for old, new in names.items():
        text = re.sub(rf'name = "{re.escape(old)}"', f'name = "{new}"', text)
    ctrl.write_text(text)
    lib = tmp / name / "library.toml"
    lib.write_text(lib.read_text().replace("spill-parts", name.replace("_", "-")))


def _codes(library: str, names: dict[str, str]) -> dict[str, int]:
    d = fr.design(library)
    d.add(_unit(names), "U1")
    result = fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "repro", cover=DATA / "cover.md"))
    found = [f.code for f in fr.check(result)]
    return {c: found.count(c) for c in (*CODES, "CARD_OVERFULL", "PLACEMENT_PROBLEM")}


@pytest.fixture(scope="module")
def exact() -> dict[str, int]:
    with pytest.MonkeyPatch.context() as mp:
        mp.syspath_prepend(str(DATA.parent))
        return _codes("spill_parts", {label: label for label in LABELS})


def test_the_card_spills_and_every_tag_and_connection_is_drawn(exact: dict[str, int]) -> None:
    assert exact["CARD_OVERFULL"] == 1
    assert {c: exact[c] for c in CODES} == dict.fromkeys(CODES, 0)


def test_the_card_page_draws_with_no_placement_problem(exact: dict[str, int]) -> None:
    assert exact["PLACEMENT_PROBLEM"] == 0


@pytest.mark.parametrize(("name", "names"), [("spill_parts_wide", WIDER), ("spill_parts_narrow", NARROWER)])
def test_widening_or_narrowing_the_card_labels_still_draws_every_tag_and_connection(
    name: str, names: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _library(tmp_path, name, names)
    monkeypatch.syspath_prepend(str(tmp_path))
    codes = _codes(name, names)
    assert {c: codes[c] for c in CODES} == dict.fromkeys(CODES, 0)
