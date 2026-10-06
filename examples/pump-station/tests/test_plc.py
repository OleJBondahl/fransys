"""PLC export check (spec E9, E3's PLC I/O list; columns per
`2026-09-25-release-read-fixes.md` W1/W2).

The PLC list is a wiring list (owner ruling): `PLC_COLUMNS` is `channel_designation, signal,
wired_to, signal_name`. The field device, its terminal and its location label are gone --
they described the signal, not the wire. `wired_to` is the far end of every conductor at the
channel's ports, distinct ends sorted by `bom_sort_key` and joined with `"; "`; an unwired
channel gives an empty cell.

The can-fail proof for this check (spec step 4: swap DO1/DO2, confirm this test fails, revert)
is a manual verification done once with `Edit`, not a permanent test -- see the STEP 4 report.
"""

import csv
from pathlib import Path

# E3's PLC I/O list against the current columns. The channel carries its printed designation,
# dashed (`-DI1:1`), with the cabinet tag in `all/` (`-U1-DI1:1`); `wired_to` is the far end at the
# channel's port -- `all/` has no list context, so it prints the located end
# (`-U1-...`, model DESIGN 12), while `cabinet/` and
# `board/` print their unit-local form (`-J1:1`). The literals stay literals so the test does
# not check `fr.derive.PLC_COLUMNS`, `plc_channel_rows` or `port_designation_in` against
# themselves.
EXPECTED_ALL_PLC_ROWS = [
    {
        "channel_designation": "-U1-DI1:1",
        "signal": "di",
        "wired_to": "-U1-B12:98",
        "signal_name": "P1_OVERLOAD",
    },
    {
        "channel_designation": "-U1-DI1:2",
        "signal": "di",
        "wired_to": "-U1-Q11:14",
        "signal_name": "P1_RUNNING",
    },
    {
        "channel_designation": "-U1-DI1:3",
        "signal": "di",
        "wired_to": "-U1-B22:98",
        "signal_name": "P2_OVERLOAD",
    },
    {
        "channel_designation": "-U1-DI1:4",
        "signal": "di",
        "wired_to": "-U1-Q21:14",
        "signal_name": "P2_RUNNING",
    },
    {
        "channel_designation": "-U1-DO1:1",
        "signal": "do",
        "wired_to": "-U1-J1:1",
        "signal_name": "P1_RUN",
    },
    {
        "channel_designation": "-U1-DO1:2",
        "signal": "do",
        "wired_to": "-U1-J1:2",
        "signal_name": "P2_RUN",
    },
    {"channel_designation": "-U1-DO1:3", "signal": "do", "wired_to": "", "signal_name": ""},
    {"channel_designation": "-U1-DO1:4", "signal": "do", "wired_to": "", "signal_name": ""},
]

EXPECTED_CABINET_PLC_ROWS = [
    {
        "channel_designation": "-DI1:1",
        "signal": "di",
        "wired_to": "-B12:98",
        "signal_name": "P1_OVERLOAD",
    },
    {
        "channel_designation": "-DI1:2",
        "signal": "di",
        "wired_to": "-Q11:14",
        "signal_name": "P1_RUNNING",
    },
    {
        "channel_designation": "-DI1:3",
        "signal": "di",
        "wired_to": "-B22:98",
        "signal_name": "P2_OVERLOAD",
    },
    {
        "channel_designation": "-DI1:4",
        "signal": "di",
        "wired_to": "-Q21:14",
        "signal_name": "P2_RUNNING",
    },
    {"channel_designation": "-DO1:1", "signal": "do", "wired_to": "-J1:1", "signal_name": "P1_RUN"},
    {"channel_designation": "-DO1:2", "signal": "do", "wired_to": "-J1:2", "signal_name": "P2_RUN"},
    {"channel_designation": "-DO1:3", "signal": "do", "wired_to": "", "signal_name": ""},
    {"channel_designation": "-DO1:4", "signal": "do", "wired_to": "", "signal_name": ""},
]

PLC_COLUMNS = ["channel_designation", "signal", "wired_to", "signal_name"]


def _read_plc_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_all_plc_csv_matches_io_list(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    path = out_dir / "all" / "EX-1-v1.2-plc.csv"
    rows = _read_plc_rows(path)
    with path.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == PLC_COLUMNS, f"{path} has no field-device column: {header}"
    assert len(rows) == 8, f"expected exactly 8 PLC rows, got {len(rows)}: {rows}"
    assert rows == EXPECTED_ALL_PLC_ROWS


def test_cabinet_plc_csv_matches_io_list(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    path = out_dir / "cabinet" / "pump-cabinet-v1.6-plc.csv"
    rows = _read_plc_rows(path)
    with path.open(newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == PLC_COLUMNS, f"{path} has no field-device column: {header}"
    assert len(rows) == 8, f"expected exactly 8 PLC rows, got {len(rows)}: {rows}"
    assert rows == EXPECTED_CABINET_PLC_ROWS


def test_cabinet_do1_1_wired_to_reads_j1_1(built: tuple) -> None:
    """Acceptance 5: `-DO1:1` reads `-J1:1` in `cabinet/`, not the relay `-U2-K1`."""
    _result, out_dir, _intermediates = built
    rows = _read_plc_rows(out_dir / "cabinet" / "pump-cabinet-v1.6-plc.csv")
    row = next(r for r in rows if r["channel_designation"] == "-DO1:1")
    assert row["wired_to"] == "-J1:1", row


def test_all_do1_1_wired_to_reads_c1_j1_1(built: tuple) -> None:
    """Acceptance 5: `all/` has no list context, so the located end prints its full path
    (model DESIGN 12), `-U1-J1:1`, as `all/wires.csv` does.
    """
    _result, out_dir, _intermediates = built
    rows = _read_plc_rows(out_dir / "all" / "EX-1-v1.2-plc.csv")
    row = next(r for r in rows if r["channel_designation"] == "-U1-DO1:1")
    assert row["wired_to"] == "-U1-J1:1", row
