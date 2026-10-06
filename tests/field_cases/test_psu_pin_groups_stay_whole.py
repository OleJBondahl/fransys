"""Field case: a supply box keeps its pin groups whole, whatever ranks the pins share.

The engineering shape: a 24 V power supply with an AC input (`L`, `N`), a DC output (`+`, `-`)
and a DC-OK contact (`13`, `14`) whose two pins are joined by a switched link. The contact's
pin `13` is wired to the 24 V output net, so both contact pins carry 24 V in service (the
rail closure passes the switched link). Three lamps hang on the output.

The bug: after pin ranks came from the supply (D2a), the contact's pins shared the rank of `+`
and sorted among the output pins: the bottom read `13`, `+`, `-`.

The rule (CONVENTIONS-V06 V11, V1, decision model-0121): a pin group is a function; on a box
side the groups stay whole, and inside a group the pins order by rank. The bottom reads `+`,
`-`, then the contact's pins. The AC input stays on top, L left of N.
"""

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs


def _t1_sides(tmp_path) -> dict[str, list[str]]:
    """T1's pins by side, left to right, as `function.pin`."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24-OK")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(3)]
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("CONTROL", psu.output)
    plus = [psu.dc_ok["13"], *(lamp["1"] for lamp in lamps)]
    minus = [lamp["2"] for lamp in lamps]
    for rail, members in ((psu.output["+"], plus), (psu.output["-"], minus)):
        for pin in members:
            d.wire(rail, pin, wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    results, _ = stage_results(model, read_inputs(model))
    (box,) = (one for one in results.layout.placed if one.column[0].rpartition("/")[2] == "T1")
    found: dict[str, list[str]] = {}
    for port in sorted(box.geometry.ports, key=lambda p: p.at.x):
        found.setdefault(port.facing.value, []).append(port.name)
    return found


def test_the_dc_output_pins_stand_before_the_dc_ok_pins_and_the_ac_input_is_on_top(
    tmp_path,
) -> None:
    sides = _t1_sides(tmp_path)
    assert sides["n"] == ["input.L", "input.N"]
    assert sides["s"][:2] == ["output.+", "output.-"]
    assert set(sides["s"][2:]) == {"dc_ok.13", "dc_ok.14"}
