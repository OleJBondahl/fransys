"""Field case: a 24 V power supply with an AC input (L, N) and a DC output (+, -) feeding three lamps, where only the rail names change.
The bug: a pin was ranked by its rail's name in a house table, so a rail named `L`, `12V` or `L+` had no rank and the pins swapped sides.
Fixed by model-0121, the rank comes from the supply's declared facts, never the name, so `L` stands left of `N` and `+` left of `-`."""

from typing import Any

import fransys as fr
import pytest
from _drawn_facts import symbol_subjects
from _model_build_cover import unit_document
from fransys.colours import BU

# arm: (DC live rail name or None for the default, DC 0 V name or None)
# ac_named_L dropped: ac_supply has no names= (2026-10-05)
_ARMS = {
    "baseline": (None, None),
    "dc_named_12V": ("12V", "0V"),
    "dc_named_Lplus": ("L+", "0V"),
}
_LOADS = 3


def _plant(d, arm: tuple[Any, ...]) -> None:
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
            d.series(rail, pin, wire=(BU, 0.5))


def _pin_order(arm: tuple[Any, ...]) -> list[str]:
    """T1's pins by name, left to right within each side of its drawn box."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    _plant(d, arm)
    doc = unit_document(cab)
    model = fr.build(d, doc).model
    (box,) = (s for s in symbol_subjects(model) if s.key == "generic-box" and s.tag == "T1")
    sides, offsets = dict(box.sides), dict(box.offsets)
    return [f"{name}:{sides[name]}@{offsets[name]}" for name in sorted(sides, key=lambda n: (sides[n], offsets[n]))]


def _left_to_right(pins: list[str], side: str, first: str, second: str) -> bool:
    at = {p.split(":")[0].split(".")[-1]: int(p.split("@")[1]) for p in pins if f":{side}@" in p}
    return at[first] < at[second]


def test_the_baseline_has_l_left_of_n_and_plus_left_of_minus() -> None:
    """Positive twin: the order the other arms must keep exists, and L is not simply first."""
    pins = _pin_order(_ARMS["baseline"])
    assert _left_to_right(pins, "n", "L", "N")
    assert _left_to_right(pins, "s", "+", "-")


@pytest.mark.parametrize("arm", ["dc_named_12V", "dc_named_Lplus"])
def test_a_rail_named_otherwise_keeps_the_pin_order(arm: str) -> None:
    assert _pin_order(_ARMS[arm]) == _pin_order(_ARMS["baseline"])
