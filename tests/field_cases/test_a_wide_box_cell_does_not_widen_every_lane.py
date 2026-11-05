"""Field case: four contacts side by side, fed from a wide supply box cell in lane 0 and a second supply's cell in lane 3.
The bug: the step from the wide box cell was taken as one lane's pitch, so the whole contact row spread and coils ran past the content box.
Fixed by layout-0178, a step between cells k lanes apart needs a pitch of ceil(step / k), snapped, and the widest such pitch wins."""

from itertools import pairwise

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document

_COLOURS = ("BU", 0.5)
_CONTACT_PITCH = 56  # the contacts' own step: their keep-out plus one wiring grid


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.layout.profile(hide_unused_pins=True)
    first, second = d.device("P1", "DEMO-PSU-24-5OUT"), d.device("P2", "DEMO-PSU-24-5OUT")
    changeover = d.device("Q1", "DEMO-RLY-4CO-24")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 6).run("L", 6, bridged=True, rail=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 6).run("L", 6, bridged=True, rail=True)
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.series(first.input["L"], live[1].outer, wire=_COLOURS)
    d.series(first.input["N"], zero[1].outer, wire=_COLOURS)
    d.series(changeover.coil["A1"], live[2].outer, wire=_COLOURS)
    d.series(changeover.coil["A2"], zero[6].outer, wire=_COLOURS)
    for n, out in enumerate(("+1", "+2", "-1"), start=1):
        d.series(first.output[out], getattr(changeover, f"co_{n}")[f"{n}1"], wire=_COLOURS)
        d.series(getattr(changeover, f"co_{n}")[f"{n}4"], zero[n + 1].inner, wire=_COLOURS)
    d.series(second.output["+1"], changeover.co_4["41"], wire=_COLOURS)
    d.series(changeover.co_4["44"], zero[5].inner, wire=_COLOURS)
    return fr.build(d, unit_document(cab))


def _contact_xs(result: fr.BuildResult) -> list[int]:
    """The x of the changeover's four contacts, by the pin number each takes in (11, 21, 31, 41)."""
    pins = {f"{n}1": n for n in range(1, 5)}
    found = {
        pins[text]: one.x
        for drawing in drawn_pages(result.model).values()
        for one in drawing.symbols
        for slot, text in one.slots
        if slot == "marking.in" and text in pins
    }
    return [found[name] for name in sorted(found)]


def test_the_contact_lanes_stand_at_their_own_pitch() -> None:
    result = _build()
    xs = _contact_xs(result)
    assert [b - a for a, b in pairwise(xs)] == [_CONTACT_PITCH] * 3
