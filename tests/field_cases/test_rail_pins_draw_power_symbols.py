"""Field case: a DC supply's bridged 24 V and 0 V terminal rows feeding three lamps, each lamp pin wired to a rail terminal.
The bug: the terminal rows were drawn, and each lamp pin referenced a terminal box that only repeats the rail.
Fixed by layout-0120 and model-0118, a rail terminal is not drawn on schematic pages and its pins draw the rail's power symbol."""

import csv
import io

import fransys as fr
from _drawn_facts import symbol_subjects
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.derive import is_rail_terminal
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import functions, items

_LAMPS = 3


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(_LAMPS)]
        live = d.terminal_strip("X1", "DEMO-TB-2.5", _LAMPS).run("L", _LAMPS, bridged=True, rail=True)
        zero = d.terminal_strip("X2", "DEMO-TB-2.5", _LAMPS).run("L", _LAMPS, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        for number, lamp in enumerate(lamps, start=1):
            d.series(lamp.lamp["1"], live[number].outer, wire=(BU, 0.5))
            d.series(lamp.lamp["2"], zero[number].outer, wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc)


def test_each_load_pin_draws_a_symbol_and_no_rail_terminal_is_drawn() -> None:
    result = _build()
    model = result.model
    rail_terminals = {i.id for i in items(model).values() if is_rail_terminal(model, i.id)}
    assert len(rail_terminals) == 2 * _LAMPS  # the fixture's rows are rail terminals
    owners = {s.owner for s in symbol_subjects(model)}
    drawn_items = {f.item for f in functions(model).values() if f.id.value in owners}
    assert not rail_terminals & drawn_items
    symbols = [s.symbol for s in layout_of(model, PowerSymbol).values()]
    assert symbols.count("power-supply") == _LAMPS
    assert symbols.count("ground") == _LAMPS


def test_the_terminal_table_lists_every_landing(tmp_path) -> None:
    written = fr.write(_build(), tmp_path / "out")
    rows = []
    for path in written:
        if path.name.startswith("terminals") and path.suffix == ".csv":
            rows += list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    assert len(rows) >= 2 * _LAMPS
