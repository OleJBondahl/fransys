"""Field case: a power supply's pins keep their order whatever its rails are named.

The engineering shape: a 24 V power supply with an AC input (`L`, `N`) on an AC supply and a DC
output (`+`, `-`) on a DC supply, feeding three lamps. Only the rails' NAMES change between the
arms: `L1`/`24V` (baseline), `L`, `12V` and `L+`.

The bug: a pin was ranked by its rail's name in a house table, so a rail named `L`, `12V` or `L+`
had no rank and the pins swapped sides of the box: N left of L, `-` left of `+`.

The rule (CONVENTIONS-V06 V11, decision model-0121): the rank comes from the supply's declared
facts, never the name: an AC phase before AC 0 V, a DC rail above 0 V before the DC 0 V rail. So
`L` stands left of `N` and `+` left of `-`, with any rail names.
"""

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs

# arm: (DC live rail name or None for the default, DC 0 V name or None)
# ac_named_L dropped: ac_supply has no names= (EA15, 2026-10-05)
_ARMS = {
    "baseline": (None, None),
    "dc_named_12V": ("12V", "0V"),
    "dc_named_Lplus": ("L+", "0V"),
}
_LOADS = 3


def _plant(d, arm: tuple) -> None:
    live, zero = arm
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(_LOADS)]
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    names = None if live is None else (live, zero)
    d.dc_supply("CONTROL", psu, names=names)
    for rail, members in (
        (psu.output["+"], [lamp["1"] for lamp in lamps]),
        (psu.output["-"], [lamp["2"] for lamp in lamps]),
    ):
        for pin in members:
            d.wire(rail, pin, wire=(BU, 0.5))


def _pin_order(tmp_path, arm: tuple) -> list[str]:
    """T1's pins by name, left to right within each side of its drawn box."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _plant(d, arm)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    psu = [one for one in results.layout.placed if one.column[0].rpartition("/")[2] == "T1"]
    return [
        f"{one.column[-1]}.{g.name}:{g.facing.value}@{g.at.x}"
        for one in psu
        for g in sorted(one.geometry.ports, key=lambda g: (g.facing.value, g.at.x))
    ]


def _left_to_right(pins: list[str], side: str, first: str, second: str) -> bool:
    at = {p.split(":")[0].split(".")[-1]: int(p.split("@")[1]) for p in pins if f":{side}@" in p}
    return at[first] < at[second]


def test_the_baseline_has_l_left_of_n_and_plus_left_of_minus(tmp_path) -> None:
    """Positive twin: the order the other arms must keep exists, and L is not simply first."""
    pins = _pin_order(tmp_path, _ARMS["baseline"])
    assert _left_to_right(pins, "n", "L", "N")
    assert _left_to_right(pins, "s", "+", "-")


@pytest.mark.parametrize("arm", ["dc_named_12V", "dc_named_Lplus"])
def test_a_rail_named_otherwise_keeps_the_pin_order(tmp_path, arm: str) -> None:
    assert _pin_order(tmp_path, _ARMS[arm]) == _pin_order(tmp_path, _ARMS["baseline"])
