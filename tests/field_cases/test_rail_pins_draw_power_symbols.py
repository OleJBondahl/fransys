"""Field case: a bridged 24 V terminal row feeding three loads is not drawn, each pin draws a bar.

The engineering shape: a DC supply with rails 24 V and 0 V, two strips whose terminals are bridged
by a rail link (X1 on 24 V, X2 on 0 V), and three lamps wired from pin 1 to X1 and from pin 2 to X2.

The bug: the terminal rows were drawn and each lamp pin was wired or referenced to a terminal box
that only repeats the rail.

The rule (CONVENTIONS-V06 V3, decision layout-0099, model-0118): a rail terminal is not drawn on
schematic pages, and a pin wired to it draws the rail's power symbol, a bar for 24 V and ground for
0 V. The terminal table still lists every landing.
"""

import csv
import io

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.derive import is_rail_terminal
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import items

_LAMPS = 3


def _build(tmp_path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(_LAMPS)]
        live = d.terminal_strip("X1", "DEMO-TB-2.5", _LAMPS).run("L", _LAMPS, bridged=True)
        zero = d.terminal_strip("X2", "DEMO-TB-2.5", _LAMPS).run("L", _LAMPS, bridged=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        for number, lamp in enumerate(lamps, start=1):
            d.wire(lamp.lamp["1"], live[number].outer, wire=(BU, 0.5))
            d.wire(lamp.lamp["2"], zero[number].outer, wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def test_each_load_pin_draws_a_symbol_and_no_rail_terminal_is_drawn(tmp_path) -> None:
    result = _build(tmp_path)
    model = result.model
    rail_terminals = {i.id for i in items(model).values() if is_rail_terminal(model, i.id)}
    assert len(rail_terminals) == 2 * _LAMPS  # the fixture's rows are rail terminals
    drawn_items = {spec.item for spec in read_inputs(model).functions}
    assert not rail_terminals & drawn_items
    symbols = [s.symbol for s in layout_of(model, PowerSymbol).values()]
    assert symbols.count("power-supply") == _LAMPS
    assert symbols.count("ground") == _LAMPS


def test_the_terminal_table_lists_every_landing(tmp_path) -> None:
    written = fr.write(_build(tmp_path), tmp_path / "out")
    rows = []
    for path in written:
        if path.name.startswith("terminals-") and path.suffix == ".csv":
            rows += list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    assert len(rows) >= 2 * _LAMPS
