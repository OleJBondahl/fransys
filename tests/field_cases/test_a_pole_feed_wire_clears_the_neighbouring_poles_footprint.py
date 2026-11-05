"""Field case: a two-pole breaker feeds a three-pole contactor, one pole fed through a strip so the poles stand 32 apart.
The bug: the wire keeps held a pole's soft tag room, so a feed wire read as running through the other pole's footprint (WIRE_MEETS_NET).
Fixed by layout-0495 (KI-477): a wire keep is the symdef body, never the tag room."""

import tempfile
from pathlib import Path

import fransys as fr

_BK = ("BK", 2.5)


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    d.project(title="Feed", number="B-1", customer="Example Co", revision=1, author="XX")
    d.revision(1, date="2026-10-19", text="First issue", created="XX")
    with d.function("M", "Feeder"):
        x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 4, pe="DEMO-TB-PE-2.5")
        xa = d.terminal_strip("XA", "DEMO-TB-2.5-TWIN", 2)
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3, pe="DEMO-TB-PE-2.5")
        f, q = d.device("F21", "DEMO-MCB-2P"), d.device("Q21", "DEMO-CTR-3P-NC")
        pairs = [
            (x0[1].inner, f.pole_1["1"]),
            (x0[2].inner, xa[1].inner),
            (xa[1].inner, f.pole_2["3"]),
            (f.pole_1["2"], q.main["1"]),
            (f.pole_2["4"], q.main["3"]),
            (x0[3].inner, q.main["5"]),
            *((q.main[str(2 * n)], x1[n].inner) for n in (1, 2, 3)),
        ]
        for a, b in pairs:
            d.series(a, b, wire=_BK)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Feed\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_a_pole_feed_wire_in_a_neighbours_tag_room_is_not_a_meeting() -> None:
    codes = {f.code for f in _build().findings}
    assert not codes & {"WIRE_MEETS_NET", "TERMINAL_POINT_OVERFILLED"}
