"""PLC export check: the PLC I/O list.

The PLC list is a wiring list with one row per pin (Fransys 0.17, PLC-PIN-ROWS): `PLC_COLUMNS` is
`pin, channel_name, signal, signal_name, description, wired_to`. The `pin` is the row's identity (`-DI1:DI1`);
`channel_name` repeats across modules (`1` in both DI1 and DO1). `wired_to` is the far end of
the conductors at that pin alone; an unwired spare pin gives an empty cell.

The can-fail proof for this check (swap DO1/DO2, confirm this test fails, revert)
is a manual verification done once with `Edit`, not a permanent test.
"""

import csv
from pathlib import Path

# E3's PLC I/O list against the current columns. The pin carries its printed designation, with
# the cabinet tag in `all/` (`-U1-DI1:DI1`); `wired_to` is the far end at the pin -- `all/` has no
# list context, so it prints the located end (`-U1-...`, model DESIGN 12), while `cabinet/` prints
# the unit-local form (`-K1:A1`). The literals stay literals so the test does not check
# `fr.derive.PLC_COLUMNS` or the row builders against themselves.
EXPECTED_ALL_PLC_ROWS = [
    {
        "pin": "-U1-DI1:DI1",
        "channel_name": "1",
        "signal": "di",
        "signal_name": "P1_OVERLOAD",
        "description": "",
        "wired_to": "-U1-B12:98",
    },
    {
        "pin": "-U1-DI1:DI2",
        "channel_name": "2",
        "signal": "di",
        "signal_name": "P1_RUNNING",
        "description": "",
        "wired_to": "-U1-Q11:84",
    },
    {
        "pin": "-U1-DI1:DI3",
        "channel_name": "3",
        "signal": "di",
        "signal_name": "P2_OVERLOAD",
        "description": "",
        "wired_to": "-U1-B22:98",
    },
    {
        "pin": "-U1-DI1:DI4",
        "channel_name": "4",
        "signal": "di",
        "signal_name": "P2_RUNNING",
        "description": "",
        "wired_to": "-U1-Q21:84",
    },
    {
        "pin": "-U1-DO1:DO1",
        "channel_name": "1",
        "signal": "do",
        "signal_name": "P1_RUN",
        "description": "",
        "wired_to": "-U1-K1:A1",
    },
    {
        "pin": "-U1-DO1:DO2",
        "channel_name": "2",
        "signal": "do",
        "signal_name": "P2_RUN",
        "description": "",
        "wired_to": "-U1-K2:A1",
    },
    {
        "pin": "-U1-DO1:DO3",
        "channel_name": "3",
        "signal": "do",
        "signal_name": "",
        "description": "",
        "wired_to": "",
    },
    {
        "pin": "-U1-DO1:DO4",
        "channel_name": "4",
        "signal": "do",
        "signal_name": "",
        "description": "",
        "wired_to": "",
    },
]

EXPECTED_CABINET_PLC_ROWS = [
    {
        "pin": "-DI1:DI1",
        "channel_name": "1",
        "signal": "di",
        "signal_name": "P1_OVERLOAD",
        "description": "",
        "wired_to": "-B12:98",
    },
    {
        "pin": "-DI1:DI2",
        "channel_name": "2",
        "signal": "di",
        "signal_name": "P1_RUNNING",
        "description": "",
        "wired_to": "-Q11:84",
    },
    {
        "pin": "-DI1:DI3",
        "channel_name": "3",
        "signal": "di",
        "signal_name": "P2_OVERLOAD",
        "description": "",
        "wired_to": "-B22:98",
    },
    {
        "pin": "-DI1:DI4",
        "channel_name": "4",
        "signal": "di",
        "signal_name": "P2_RUNNING",
        "description": "",
        "wired_to": "-Q21:84",
    },
    {
        "pin": "-DO1:DO1",
        "channel_name": "1",
        "signal": "do",
        "signal_name": "P1_RUN",
        "description": "",
        "wired_to": "-K1:A1",
    },
    {
        "pin": "-DO1:DO2",
        "channel_name": "2",
        "signal": "do",
        "signal_name": "P2_RUN",
        "description": "",
        "wired_to": "-K2:A1",
    },
    {
        "pin": "-DO1:DO3",
        "channel_name": "3",
        "signal": "do",
        "signal_name": "",
        "description": "",
        "wired_to": "",
    },
    {
        "pin": "-DO1:DO4",
        "channel_name": "4",
        "signal": "do",
        "signal_name": "",
        "description": "",
        "wired_to": "",
    },
]

PLC_COLUMNS = ["pin", "channel_name", "signal", "signal_name", "description", "wired_to"]


def _read_plc_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_all_plc_csv_matches_io_list(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    path = out_dir / "all" / "data" / "EX-1-v1.6-plc.csv"
    rows = _read_plc_rows(path)
    with path.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == PLC_COLUMNS, f"{path} has unexpected columns: {header}"
    assert len(rows) == 8, f"expected exactly 8 PLC rows, got {len(rows)}: {rows}"
    assert rows == EXPECTED_ALL_PLC_ROWS


def test_cabinet_plc_csv_matches_io_list(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    path = out_dir / "cabinet" / "data" / "pump-cabinet-v1.11-plc.csv"
    rows = _read_plc_rows(path)
    with path.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == PLC_COLUMNS, f"{path} has unexpected columns: {header}"
    assert len(rows) == 8, f"expected exactly 8 PLC rows, got {len(rows)}: {rows}"
    assert rows == EXPECTED_CABINET_PLC_ROWS


def test_cabinet_do1_1_wired_to_reads_k1_a1(built: tuple) -> None:
    """Acceptance 5: pin `-DO1:DO1` (channel 1) reads the relay coil `-K1:A1` in `cabinet/`."""
    _result, out_dir, _intermediates = built
    rows = _read_plc_rows(out_dir / "cabinet" / "data" / "pump-cabinet-v1.11-plc.csv")
    row = next(r for r in rows if r["pin"] == "-DO1:DO1")
    assert row["channel_name"] == "1", row
    assert row["wired_to"] == "-K1:A1", row


def test_all_do1_1_wired_to_reads_u1_k1_a1(built: tuple) -> None:
    """Acceptance 5: `all/` has no list context, so the located end prints its full path
    (model DESIGN 12), `-U1-K1:A1`, as `all/wires.csv` does.
    """
    _result, out_dir, _intermediates = built
    rows = _read_plc_rows(out_dir / "all" / "data" / "EX-1-v1.6-plc.csv")
    row = next(r for r in rows if r["pin"] == "-U1-DO1:DO1")
    assert row["channel_name"] == "1", row
    assert row["wired_to"] == "-U1-K1:A1", row
