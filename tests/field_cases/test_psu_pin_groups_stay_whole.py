"""Field case: a supply box keeps its pin groups whole, whatever ranks the pins share.

The engineering shape: a 24 V power supply with an AC input (`L`, `N`), a DC output (`+`, `-`)
and a DC-OK contact (`13`, `14`) whose two pins are joined by a switched link. The contact's
pin `13` is wired to the 24 V output net, so both contact pins carry 24 V in service (the
rail closure passes the switched link). Three lamps hang on the output.

The bug: after pin ranks came from the supply, the contact's pins shared the rank of `+`
and sorted among the output pins: the bottom read `13`, `+`, `-`.
Since the demo part's `dc_ok` became `contact_no` (cleanup round 2, rider R) the contact
stands in its own circuit and the box keeps its two groups only.

The rule (decision layout-0099, model-0121): a pin group is a function; on a box
side the groups stay whole, and inside a group the pins order by rank. The bottom reads `+`,
`-` and nothing else. The AC input stays on top, L left of N.
"""

import fransys as fr
from fransys.colours import BU

from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import functions


def _gap(model, fact: str):
    """A fact the page Drawing lacks (strict xfail, GAP-FLIP-DRAWING-SUBJECT)."""
    msg = f"GAP-FLIP-DRAWING-SUBJECT: no {fact} for {model.digest}"
    raise AssertionError(msg)


def _t1_sides(tmp_path) -> tuple[dict[str, list[str]], FunctionKind, int]:
    """T1's pins by side as `function.pin`, the dc_ok kind and how many placements dc_ok has."""
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
            d.detail.wire(rail, pin, wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(d, doc).model
    drawn = _gap(model, "symbol subject").values()
    (box,) = (s for s in drawn if s.key == "generic-box" and s.owner.startswith("T1 "))
    sides, offsets = dict(box.sides), dict(box.offsets)
    found: dict[str, list[str]] = {}
    for port in sorted(sides, key=lambda name: offsets[name]):
        found.setdefault(sides[port], []).append(port)
    (contact,) = (f for f in functions(model).values() if f.name == "dc_ok")
    stands = sum(s.owner.endswith(contact.id.value) for s in drawn)
    return found, contact.kind, stands


def test_the_dc_output_pins_stand_before_the_dc_ok_pins_and_the_ac_input_is_on_top(
    tmp_path,
) -> None:
    sides, kind, stands = _t1_sides(tmp_path)
    assert sides["n"] == ["input.L", "input.N"]
    assert sides["s"] == ["output.+", "output.-"]
    assert kind is FunctionKind.CONTACT_NO
    assert stands >= 1  # the contact stands in its own circuit, apart from the box
