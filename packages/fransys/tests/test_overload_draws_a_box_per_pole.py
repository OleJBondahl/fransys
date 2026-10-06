"""EF-B2 spec test: a three-pole overload relay draws one thermal box per pole.

The engineering shape: a motor feeder whose overload relay has three conductive main links,
1/L1-2/T1, 3/L2-4/T2 and 5/L3-6/T3, each pin wired to a terminal. The relay's protection type
is `overload`.

The bug: the main path drew the contact or breaker symbol of a switch, or one box for all poles,
where the owner's rule is one `thermal-overload` box per pole.

The rule (decision layout-0105, spec electrical-facts F3): the main path stays a straight
conductor and each pole draws a `thermal-overload` box, none a contact or a breaker.
"""

from pathlib import Path

import fransys as fr
import fransys_author.surface as author_surface
import fransys_parts
from fransys.colours import BU

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs

_LIBRARY = 'schema = 1\nname = "overload-parts"\nversion = "0.1.0"\ndescription = "Invented."\n'
_DEMO_TERMINAL = (
    Path(__file__).parents[3]
    / "examples"
    / "demo-parts"
    / "demo_parts"
    / "parts"
    / "terminal-feedthrough-2_5.toml"
)
_OVERLOAD = """schema = 1

[part]
mpn = "OL-3P"
manufacturer = "Demo"
description = "Three-pole overload relay"
category = "protection"
class_code = "F"

[[function]]
name = "main"
kind = "protection"
ports = [
    { name = "1/L1", role = "generic" },
    { name = "2/T1", role = "generic" },
    { name = "3/L2", role = "generic" },
    { name = "4/T2", role = "generic" },
    { name = "5/L3", role = "generic" },
    { name = "6/T3", role = "generic" },
]
links = [
    { a = "1/L1", b = "2/T1", kind = "conductive" },
    { a = "3/L2", b = "4/T2", kind = "conductive" },
    { a = "5/L3", b = "6/T3", kind = "conductive" },
]

[function.protection]
type = "overload"
"""
_MAIN_PATH_SYMBOLS = {"circuit-breaker", "make-contact", "break-contact"}


def _built(tmp_path):
    (tmp_path / "library.toml").write_text(_LIBRARY, encoding="utf-8")
    (tmp_path / "parts").mkdir()
    (tmp_path / "parts" / "overload.toml").write_text(_OVERLOAD, encoding="utf-8")
    terminal = _DEMO_TERMINAL.read_text(encoding="utf-8")
    (tmp_path / "parts" / "terminal.toml").write_text(terminal, encoding="utf-8")
    parts = fransys_parts.load_path(tmp_path)
    d = author_surface.design(parts, place="C1")
    d.project(title="Overload", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cab = d.location("C1", "Cabinet")
    pins = ("1/L1", "2/T1", "3/L2", "4/T2", "5/L3", "6/T3")
    with d.function("CTL", "Control"):
        relay = d.device("F1", "OL-3P")
        strip = d.terminal_strip("X1", "DEMO-TB-2.5", len(pins))
        for number, pin in enumerate(pins, start=1):
            d.wire(strip[number], relay.main[pin], wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def test_each_pole_of_an_overload_draws_a_thermal_box(tmp_path) -> None:
    model = _built(tmp_path)
    results, _ = stage_results(model, read_inputs(model))
    spec = next(f for f in read_inputs(model).functions if f.key[-1] == "main")
    drawn = next(f for f in results.drawn if f.function == spec.function)
    assert drawn.geometry.key == "thermal-overload"
    assert drawn.geometry.poles == 3
    assert drawn.geometry.key not in _MAIN_PATH_SYMBOLS
    name_of = {p.port: p.name for p in spec.ports}
    symbol_port = {dp.port: dp.symbol_port for dp in drawn.ports}
    facing = {g.name: g.facing.value for g in drawn.geometry.ports}
    for pole, (line, load) in enumerate((("1/L1", "2/T1"), ("3/L2", "4/T2"), ("5/L3", "6/T3")), 1):
        port_of = {name_of[p]: symbol_port[p] for p in name_of}
        assert port_of[line] == f"{pole}.in"
        assert port_of[load] == f"{pole}.out"
        assert facing[port_of[line]] == "n"
