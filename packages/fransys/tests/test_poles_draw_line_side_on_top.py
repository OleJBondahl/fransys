"""EF-B2 spec test: a two-pole contact draws each pole's line end on top, in marking order.

The engineering shape: a two-pole switching part whose poles are marked 9/10 and 13/14 (also 1/2
and 3/4 with 13/14), each pole a switched link. The odd marking is the line end (spec
electrical-facts F4).

The bug: layout paired and ordered the poles by sorting names as text, so 10 came before 9, 3/4
after 13/14, and the first name of a pair drew on top whatever its side fact said.

The rule (decisions model-0128, layout-0106): the poles come from `function_poles`, in marking
order with digit runs by value, and a pole's line end is the symbol's north port.
"""

from pathlib import Path

import fransys as fr
import fransys_author.surface as author_surface
import fransys_parts
import pytest
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs

_LIBRARY = 'schema = 1\nname = "default-parts"\nversion = "0.1.0"\ndescription = "Invented."\n'
_DEMO_TERMINAL = (
    Path(__file__).parents[3]
    / "examples"
    / "demo-parts"
    / "demo_parts"
    / "parts"
    / "terminal-feedthrough-2_5.toml"
)
_PART = """schema = 1

[part]
mpn = "POLES-2"
manufacturer = "Demo"
description = "Two-pole switching part"
category = "electromechanical"
class_code = "K"

[[function]]
name = "contacts"
kind = "switch"
ports = [
    {{ name = "{a2}", role = "generic" }},
    {{ name = "{a1}", role = "generic" }},
    {{ name = "{b2}", role = "generic" }},
    {{ name = "{b1}", role = "generic" }},
]
links = [
    {{ a = "{a1}", b = "{a2}", kind = "switched", rest = "open" }},
    {{ a = "{b1}", b = "{b2}", kind = "switched", rest = "open" }},
]
"""
_CASES = {
    "9-10-13-14": ("9", "10", "13", "14"),
    "1-2-13-14": ("1", "2", "13", "14"),
    "3-4-13-14": ("3", "4", "13", "14"),
}


def _built(tmp_path, marks: tuple[str, str, str, str]):
    (tmp_path / "library.toml").write_text(_LIBRARY, encoding="utf-8")
    (tmp_path / "parts").mkdir()
    part = _PART.format(a1=marks[0], a2=marks[1], b1=marks[2], b2=marks[3])
    (tmp_path / "parts" / "poles.toml").write_text(part, encoding="utf-8")
    terminal = _DEMO_TERMINAL.read_text(encoding="utf-8")
    (tmp_path / "parts" / "terminal.toml").write_text(terminal, encoding="utf-8")
    parts = fransys_parts.load_path(tmp_path)
    d = author_surface.design(parts, place="C1")
    d.project(title="Poles", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cab = d.location("C1", "Cabinet")
    with d.function("CTL", "Control"):
        device = d.device("K1", "POLES-2")
        strip = d.terminal_strip("X1", "DEMO-TB-2.5", len(marks))
        for number, mark in enumerate(marks, start=1):
            d.wire(strip[number], device.contacts[mark], wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


@pytest.mark.parametrize("marks", _CASES.values(), ids=_CASES)
def test_the_line_end_draws_on_top_and_the_poles_follow_marking_order(tmp_path, marks) -> None:
    model = _built(tmp_path, marks)
    results, _ = stage_results(model, read_inputs(model))
    spec = next(f for f in read_inputs(model).functions if f.key[-1] == "contacts")
    drawn = next(f for f in results.drawn if f.function == spec.function)
    name_of = {p.port: p.name for p in spec.ports}
    symbol_port = {dp.port: dp.symbol_port for dp in drawn.ports}
    facing = {g.name: g.facing.value for g in drawn.geometry.ports}
    top = [name_of[p] for p in name_of if facing[symbol_port[p]] == "n"]
    pole_of = {name_of[p]: symbol_port[p].split(".")[0] for p in name_of}
    assert sorted(top, key=int) == [marks[0], marks[2]]
    assert pole_of[marks[0]] == pole_of[marks[1]] == "1"
    assert pole_of[marks[2]] == pole_of[marks[3]] == "2"
