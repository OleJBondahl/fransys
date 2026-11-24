"""Field case: a design-level box's PE pin is wired to a unit's boundary box and, by two more cores, to two other design-level boxes.
No drawing set draws both ends, so the PE net is wired (R3699): each set shows a stub naming the far pin, never a PE symbol.
KI-1411 held CONNECTION_NOT_DRAWN 2 here."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages, markers_in, ref_texts
from fransys.colours import GNYE

from fransys_model.derive import power_ends_split, stands
from fransys_model.derive.designation import port_designation

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    pe: Any


@fr.unit("demo-pe-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB", title="Box", number="PB-1")
def _box(u: Any) -> _Io:
    earth = u.device("E1", None, external=True, interface=True, pins=("1",))
    u.earth(earth["1"])
    return _Io(earth)


def test_a_fanned_pe_pin_wired_to_a_units_boundary_pin_draws_both_ends(tmp_path: Path) -> None:
    """KI-1411: no conductor end of the one PE net is left undrawn."""
    d = fr.design("demo_parts", place="PLANT")
    plant = d.location("PLANT", "Plant room")
    box = d.add(_box, "U1", place=None)
    fan = [d.device(tag, None, external=True, pins=("L", "PE")) for tag in ("A6", "A4")]
    d.cable("W1", "DEMO-CBL-4G1.5", length_m=5, external=True).core(GNYE, box.pe["1"], fan[0]["PE"])
    d.cable("W2", "DEMO-CBL-4G1.5", length_m=5, external=True).core(GNYE, fan[0]["PE"], fan[1]["PE"])
    d.earth(box.pe["1"], fan[0]["PE"], fan[1]["PE"])
    for name in ("box", "plant"):
        (tmp_path / f"{name}.md").write_text("# Cover\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    result = fr.build(d, fr.document(preset, "demo-pe-box", cover=tmp_path / "box.md"), fr.document(preset, plant, cover=tmp_path / "plant.md"))
    assert [f.message for f in fr.check(result) if f.code == "CONNECTION_NOT_DRAWN"] == []
    drawn = {text for drawing in drawn_pages(result.model).values() for marker in markers_in(drawing) for text in ref_texts(marker)}
    assert drawn == {"-W1 → -U1-E1:1", "-W1 ← +PLANT-A6:PE"}  # each set names the far pin: CND 0 alone passes with nothing drawn
    (group,) = power_ends_split(result.model)  # one group of the three pins: A4 shares A6's conductor, so it is wired too
    assert {port_designation(result.model, p) for p in group} == {"-U1-E1:1", "-A6:PE", "-A4:PE"}
    assert not set(group) & stands(result.model).keys()
