"""Field case: a wide box cell beside a cell several lanes on widened every lane of the column.

The engineering shape: four contacts of one changeover stand side by side in one row, one lane
each. Above them one row holds a five-output power supply, wired to the first three contacts
(its box cell stands in lane 0), and a second supply wired to the fourth (a cell in lane 3).

The bug: the step from the wide box cell to the far cell was taken as the pitch of one lane, so
lane 3 stood three times as far as the contacts need and the whole contact row spread with it
(on a consumer's page the coils ran past the content box, `OUT_OF_CONTENT_BOX`).

The rule (decision layout-0178): a step between two cells of a row that are k lanes apart needs a
pitch of ceil(step / k), snapped; the pitch is the widest such value. The test reads the contacts'
own pitch, which a row that skips no lane gives.
"""

import tempfile
from itertools import pairwise
from pathlib import Path

import fransys as fr

from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions

_COLOURS = ("BU", 0.5)
_CONTACT_PITCH = 56  # the contacts' own step: their keep-out plus one wiring grid


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.layout.profile(hide_unused_pins=True)
    first, second = d.device("P1", "DEMO-PSU-24-5OUT"), d.device("P2", "DEMO-PSU-24-5OUT")
    changeover = d.device("Q1", "DEMO-RLY-4CO-24")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 6).run("L", 6, bridged=True)
    zero = d.terminal_strip("X2", "DEMO-TB-2.5", 6).run("L", 6, bridged=True)
    d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    d.detail.wire(first.input["L"], live[1].outer, wire=_COLOURS)
    d.detail.wire(first.input["N"], zero[1].outer, wire=_COLOURS)
    d.detail.wire(changeover.coil["A1"], live[1].outer, wire=_COLOURS)
    d.detail.wire(changeover.coil["A2"], zero[1].outer, wire=_COLOURS)
    for n, out in enumerate(("+1", "+2", "-1"), start=1):
        d.detail.wire(first.output[out], getattr(changeover, f"co_{n}")[f"{n}1"], wire=_COLOURS)
        d.detail.wire(getattr(changeover, f"co_{n}")[f"{n}4"], zero[n + 1].inner, wire=_COLOURS)
    d.detail.wire(second.output["+1"], changeover.co_4["41"], wire=_COLOURS)
    d.detail.wire(changeover.co_4["44"], zero[5].inner, wire=_COLOURS)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _contact_xs(result: fr.BuildResult) -> list[int]:
    names = {f"co_{n}" for n in range(1, 5)}
    found = {
        functions(result.model)[p.function].name: p.x
        for p in layout_of(result.model, SymbolPlacement).values()
        if functions(result.model)[p.function].name in names
    }
    return [found[name] for name in sorted(found)]


def test_the_contact_lanes_stand_at_their_own_pitch() -> None:
    result = _build()
    assert [f.code for f in fr.check(result) if f.code == "OUT_OF_CONTENT_BOX"] == []
    xs = _contact_xs(result)
    assert [b - a for a, b in pairwise(xs)] == [_CONTACT_PITCH] * 3
