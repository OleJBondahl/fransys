"""The PLC list is a wiring list (model-0065): `plc.csv` names where each channel is wired.

Release-read fixes spec, acceptance 5 on the export side: the facade's `plc.csv` (the whole
model's and a unit's own) has the header `channel_designation,signal,wired_to,signal_name`, names
no field device, and holds the far end of the wire on a channel's pin, printed in the list's
context (a unit's own list reads it short, the whole model's by its location path).
"""

import csv
import sys
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest

# `test_declared_dependencies.py`'s own pattern for importing a sibling root test module by
# name: `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _PROJECT

from fransys_model.derive import unit_release
from fransys_model.vocab.tables import units

_HEADER = ["channel_designation", "signal", "wired_to", "signal_name"]


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    """`(all_dir, unit_dir)`: the whole model's and unit `cab`'s exports of one wired PLC channel.

    Module `-A1` sits in unit `cab` at `C1`; its channel 1 pin is wired to the terminal `-X1:1`
    and the relay `-K1` requests that channel as `PUMP_RUN`; channel 2 is unwired.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    cab = d.scope("s", at=d.location("ER", "Engine room")).unit("cab", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Cabinet")
    grp = cab.group("G", "Plc")
    module = cab.item("DEMO-PLC-DO-2", tag="A1", at=c1, group=grp)
    relay = cab.item("DEMO-RLY-2CO-24", tag="K1", at=c1, group=grp)
    terminal = cab.strip("X1", at=c1).terminal("DEMO-TB-2.5", group=grp)
    cab.wiring(colour="BU", gauge="0.5")(module.fn("do_1")["1"], terminal.outer)
    relay.fn("coil").plc("do", "PUMP_RUN")
    result = fr.build(parts, d.draft())
    (unit,) = (u for u in units(result.model) if unit_release(result.model, u).name == "cab")
    root = tmp_path_factory.mktemp("plc")
    fr.write(result, root / "all")
    fr.write(result, root / "cab", unit=unit)
    return root / "all", root / "cab"


def _rows(out_dir):
    path = next(out_dir.glob("*plc.csv"))
    text = path.read_text(encoding="utf-8")
    return text, list(csv.DictReader(text.splitlines()))


def test_the_whole_models_plc_csv_names_the_wired_end_by_its_path_and_no_field_device(exports):
    all_dir, _unit_dir = exports
    text, rows = _rows(all_dir)
    assert next(csv.reader(text.splitlines())) == _HEADER
    assert [(row["channel_designation"], row["wired_to"]) for row in rows] == [
        ("-A1:1", "+ER+C1-X1:1"),
        ("-A1:2", ""),
    ]
    assert rows[0]["signal_name"] == "PUMP_RUN"
    assert "K1" not in text  # the relay, the channel's field device, is not a column


def test_a_units_plc_csv_reads_the_wired_end_short_and_names_no_field_device(exports):
    _all_dir, unit_dir = exports
    text, rows = _rows(unit_dir)
    assert next(csv.reader(text.splitlines())) == _HEADER
    assert [(row["channel_designation"], row["wired_to"]) for row in rows] == [
        ("-A1:1", "-X1:1"),
        ("-A1:2", ""),
    ]
    assert "K1" not in text
