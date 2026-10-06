"""Terminal strip checks (spec E9, E3's terminal plan).

Expected rows are hardcoded from E3's terminal plan and checked against the committed row
shape of the `terminals-*.csv` files: `designation,group,index,side_a,side_b,jumper_group`.
`side_a` is the terminal's internal port role and lists every conductor on it, jumpers included
(the far end of a `cab.bridge` jumper is the neighbouring terminal); `side_b` is the external
role. Every cell is a full designation (`-X3:PE:1`, `+EXT-M1:PE`). `jumper_group` numbers each
bridged group from 1 in row order (empty when not bridged).
The upstream strip `-X0` sits on `+EXT`, outside the cabinet, so its file is
`terminals-EXT-X0.csv` and exists only in the whole-model `out/all/`, where every designation is
location-qualified (`-U1-X1:L1:1`). The cabinet's own strips are read from `out/cabinet/`
(`terminals-X1.csv` and so on, the unit folder's names), the
cabinet unit's view, where its own items print without the location (`-Q1:1L1`) and what
lies outside it prints with its location (`+EXT-X0:L1:1`).
`side_a` lists a terminal's conductors in a fixed order (the output is deterministic).
The expected literals are kept as text, not computed with `fr.derive` (`terminal_rows`,
`TERMINAL_COLUMNS`, `terminal_designation`): those produce the CSV under test, so an expectation
computed by them could not fail when they are wrong. Only `CELL_SEPARATOR`, the inverse of how a
cell is joined, is taken from `fr.derive` where a cell is split.
"""

import csv
from pathlib import Path

import fransys as fr

EXPECTED_EXT_X0 = [
    {
        "designation": "-X0:L1:1",
        "group": "L1",
        "index": "1",
        "side_a": "",
        "side_b": "-U1-X1:L1:1",
        "jumper_group": "",
    },
    {
        "designation": "-X0:L2:1",
        "group": "L2",
        "index": "1",
        "side_a": "",
        "side_b": "-U1-X1:L2:1",
        "jumper_group": "",
    },
    {
        "designation": "-X0:L3:1",
        "group": "L3",
        "index": "1",
        "side_a": "",
        "side_b": "-U1-X1:L3:1",
        "jumper_group": "",
    },
    {
        "designation": "-X0:N:1",
        "group": "N",
        "index": "1",
        "side_a": "",
        "side_b": "-U1-X1:N:1",
        "jumper_group": "",
    },
    {
        "designation": "-X0:PE:1",
        "group": "PE",
        "index": "1",
        "side_a": "",
        "side_b": "-U1-X1:PE:1",
        "jumper_group": "",
    },
]

EXPECTED_X1 = [
    {
        "designation": "-X1:L1:1",
        "group": "L1",
        "index": "1",
        "side_a": "-Q1:1L1",
        "side_b": "+EXT-X0:L1:1",
        "jumper_group": "",
    },
    {
        "designation": "-X1:L2:1",
        "group": "L2",
        "index": "1",
        "side_a": "-Q1:3L2",
        "side_b": "+EXT-X0:L2:1",
        "jumper_group": "",
    },
    {
        "designation": "-X1:L3:1",
        "group": "L3",
        "index": "1",
        "side_a": "-Q1:5L3",
        "side_b": "+EXT-X0:L3:1",
        "jumper_group": "",
    },
    {
        "designation": "-X1:N:1",
        "group": "N",
        "index": "1",
        "side_a": "-F01:3 N",
        "side_b": "+EXT-X0:N:1",
        "jumper_group": "",
    },
    {
        "designation": "-X1:PE:1",
        "group": "PE",
        "index": "1",
        "side_a": "-X3:PE:1; -X3:PE:2",
        "side_b": "+EXT-X0:PE:1",
        "jumper_group": "",
    },
]

EXPECTED_X01 = [
    {
        "designation": "-X01:L1:1",
        "group": "L1",
        "index": "1",
        "side_a": "-X01:L1:2; -Q1:2T1",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X01:L1:2",
        "group": "L1",
        "index": "2",
        "side_a": "-X01:L1:1; -X01:L1:3; -F01:1",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X01:L1:3",
        "group": "L1",
        "index": "3",
        "side_a": "-F11:1; -X01:L1:2; -X01:L1:4",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X01:L1:4",
        "group": "L1",
        "index": "4",
        "side_a": "-F21:1; -X01:L1:3",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X01:L2:1",
        "group": "L2",
        "index": "1",
        "side_a": "-X01:L2:2; -Q1:4T2",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X01:L2:2",
        "group": "L2",
        "index": "2",
        "side_a": "-X01:L2:3; -X01:L2:1",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X01:L2:3",
        "group": "L2",
        "index": "3",
        "side_a": "-X01:L2:2; -X01:L2:4; -F11:3",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X01:L2:4",
        "group": "L2",
        "index": "4",
        "side_a": "-F21:3; -X01:L2:3",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X01:L3:1",
        "group": "L3",
        "index": "1",
        "side_a": "-Q1:6T3; -X01:L3:2",
        "side_b": "",
        "jumper_group": "3",
    },
    {
        "designation": "-X01:L3:2",
        "group": "L3",
        "index": "2",
        "side_a": "-X01:L3:3; -X01:L3:1",
        "side_b": "",
        "jumper_group": "3",
    },
    {
        "designation": "-X01:L3:3",
        "group": "L3",
        "index": "3",
        "side_a": "-X01:L3:4; -F11:5; -X01:L3:2",
        "side_b": "",
        "jumper_group": "3",
    },
    {
        "designation": "-X01:L3:4",
        "group": "L3",
        "index": "4",
        "side_a": "-X01:L3:3; -F21:5",
        "side_b": "",
        "jumper_group": "3",
    },
]

EXPECTED_X2 = [
    {
        "designation": "-X2:24V:1",
        "group": "24V",
        "index": "1",
        "side_a": "-X2:24V:2; -T1:+",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:2",
        "group": "24V",
        "index": "2",
        "side_a": "-X2:24V:1; -X2:24V:3; -C1:24 V",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:3",
        "group": "24V",
        "index": "3",
        "side_a": "-X2:24V:2; -C1:+; -X2:24V:4",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:4",
        "group": "24V",
        "index": "4",
        "side_a": "-X2:24V:3; -J2:1; -X2:24V:5",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:5",
        "group": "24V",
        "index": "5",
        "side_a": "-Q11:53/NO; -X2:24V:6; -X2:24V:4",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:6",
        "group": "24V",
        "index": "6",
        "side_a": "-B12:97; -X2:24V:7; -X2:24V:5",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:7",
        "group": "24V",
        "index": "7",
        "side_a": "-X2:24V:8; -Q11:13/NO; -X2:24V:6",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:8",
        "group": "24V",
        "index": "8",
        "side_a": "-X2:24V:7; -Q21:53/NO; -X2:24V:9",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:9",
        "group": "24V",
        "index": "9",
        "side_a": "-B22:97; -X2:24V:10; -X2:24V:8",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:24V:10",
        "group": "24V",
        "index": "10",
        "side_a": "-X2:24V:9; -Q21:13/NO",
        "side_b": "",
        "jumper_group": "1",
    },
    {
        "designation": "-X2:GND:1",
        "group": "GND",
        "index": "1",
        "side_a": "-X2:GND:2; -T1:-",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X2:GND:2",
        "group": "GND",
        "index": "2",
        "side_a": "-X2:GND:1; -C1:0V; -X2:GND:3",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X2:GND:3",
        "group": "GND",
        "index": "3",
        "side_a": "-X2:GND:4; -X2:GND:2; -C1:-",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X2:GND:4",
        "group": "GND",
        "index": "4",
        "side_a": "-Q11:A2; -X2:GND:5; -X2:GND:3",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X2:GND:5",
        "group": "GND",
        "index": "5",
        "side_a": "-P1:X2; -X2:GND:6; -X2:GND:4",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X2:GND:6",
        "group": "GND",
        "index": "6",
        "side_a": "-X2:GND:7; -Q21:A2; -X2:GND:5",
        "side_b": "",
        "jumper_group": "2",
    },
    {
        "designation": "-X2:GND:7",
        "group": "GND",
        "index": "7",
        "side_a": "-X2:GND:6; -P2:X2",
        "side_b": "",
        "jumper_group": "2",
    },
]

EXPECTED_X3 = [
    {
        "designation": "-X3:PE:1",
        "group": "PE",
        "index": "1",
        "side_a": "-X1:PE:1",
        "side_b": "+EXT-M1:PE",
        "jumper_group": "",
    },
    {
        "designation": "-X3:PE:2",
        "group": "PE",
        "index": "2",
        "side_a": "-X1:PE:1",
        "side_b": "+EXT-M2:PE",
        "jumper_group": "",
    },
    {
        "designation": "-X3:U:1",
        "group": "U",
        "index": "1",
        "side_a": "-B12:2/T1",
        "side_b": "+EXT-M1:U1",
        "jumper_group": "",
    },
    {
        "designation": "-X3:U:2",
        "group": "U",
        "index": "2",
        "side_a": "-B22:2/T1",
        "side_b": "+EXT-M2:U1",
        "jumper_group": "",
    },
    {
        "designation": "-X3:V:1",
        "group": "V",
        "index": "1",
        "side_a": "-B12:4/T2",
        "side_b": "+EXT-M1:V1",
        "jumper_group": "",
    },
    {
        "designation": "-X3:V:2",
        "group": "V",
        "index": "2",
        "side_a": "-B22:4/T2",
        "side_b": "+EXT-M2:V1",
        "jumper_group": "",
    },
    {
        "designation": "-X3:W:1",
        "group": "W",
        "index": "1",
        "side_a": "-B12:6/T3",
        "side_b": "+EXT-M1:W1",
        "jumper_group": "",
    },
    {
        "designation": "-X3:W:2",
        "group": "W",
        "index": "2",
        "side_a": "-B22:6/T3",
        "side_b": "+EXT-M2:W1",
        "jumper_group": "",
    },
]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_ext_x0_matches_terminal_plan(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    rows = _read_rows(out_dir / "all" / "EX-1-v1.3-terminals-EXT-X0.csv")
    assert len(rows) == 5, f"expected exactly 5 rows on +EXT-X0, got {len(rows)}: {rows}"
    assert rows == EXPECTED_EXT_X0


def test_x1_matches_terminal_plan(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    rows = _read_rows(out_dir / "cabinet" / "pump-cabinet-v1.6-terminals-X1.csv")
    assert len(rows) == 5, f"expected exactly 5 rows on -X1, got {len(rows)}: {rows}"
    assert rows == EXPECTED_X1


def test_x01_matches_terminal_plan(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    rows = _read_rows(out_dir / "cabinet" / "pump-cabinet-v1.6-terminals-X01.csv")
    assert len(rows) == 12, f"expected exactly 12 rows on -X01, got {len(rows)}: {rows}"
    assert rows == EXPECTED_X01


def test_x2_matches_terminal_plan(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    rows = _read_rows(out_dir / "cabinet" / "pump-cabinet-v1.6-terminals-X2.csv")
    assert len(rows) == 17, f"expected exactly 17 rows on -X2, got {len(rows)}: {rows}"
    assert rows == EXPECTED_X2


def _x2_group(rows: list[dict[str, str]], group: str, count: int) -> dict[str, dict[str, str]]:
    """The `-X2` rows of one terminal group, keyed by designation, after checking they form
    exactly one bridge: `count` terminals, all with the same non-empty `jumper_group`.
    """
    by_designation = {row["designation"]: row for row in rows if row["group"] == group}
    expected = {f"-X2:{group}:{i}" for i in range(1, count + 1)}
    assert set(by_designation) == expected, f"-X2 `{group}` terminals: {sorted(by_designation)}"
    jumper_groups = {row["jumper_group"] for row in by_designation.values()}
    assert len(jumper_groups) == 1 and "" not in jumper_groups, (
        f"-X2 `{group}` terminals are not one bridged group: "
        f"{ {d: r['jumper_group'] for d, r in by_designation.items()} }"
    )
    return by_designation


def test_x2_24v_bridge_joins_every_24v_landing(built: tuple) -> None:
    """The `24V` bridge is one jumper group over the ten `24V` terminals, so the supply's output,
    the controller's two supplies, `-J2`:1 and each pump's lamp feed, overload relay and
    contactor feedback contact are one 24 V net. Without the bridge each landing is isolated:
    the terminals carry no `jumper_group`.
    """
    _result, out_dir, _intermediates = built
    rows = _read_rows(out_dir / "cabinet" / "pump-cabinet-v1.6-terminals-X2.csv")
    rail = _x2_group(rows, "24V", 10)
    for designation, landing in (
        ("-X2:24V:1", "-T1:+"),
        ("-X2:24V:2", "-C1:24 V"),
        ("-X2:24V:3", "-C1:+"),
        ("-X2:24V:4", "-J2:1"),
        ("-X2:24V:5", "-Q11:53/NO"),
        ("-X2:24V:6", "-B12:97"),
        ("-X2:24V:7", "-Q11:13/NO"),
        ("-X2:24V:8", "-Q21:53/NO"),
        ("-X2:24V:9", "-B22:97"),
        ("-X2:24V:10", "-Q21:13/NO"),
    ):
        ends = rail[designation]["side_a"].split(fr.derive.CELL_SEPARATOR)
        assert landing in ends, f"{designation} does not land on {landing}: {ends}"


def test_x2_gnd_bridge_joins_every_gnd_landing(built: tuple) -> None:
    """The `GND` bridge is one jumper group over the seven `GND` terminals: the supply's return,
    the controller's two returns, both contactor coil returns and both lamps' `X2`. It is a
    different group from the `24V` bridge. Without the bridge each landing is isolated: the
    terminals carry no `jumper_group`.
    """
    _result, out_dir, _intermediates = built
    rows = _read_rows(out_dir / "cabinet" / "pump-cabinet-v1.6-terminals-X2.csv")
    ground = _x2_group(rows, "GND", 7)
    rail = _x2_group(rows, "24V", 10)
    assert ground["-X2:GND:1"]["jumper_group"] != rail["-X2:24V:1"]["jumper_group"], (
        "the `24V` and `GND` terminals must be two separate bridges"
    )
    for designation, landing in (
        ("-X2:GND:1", "-T1:-"),
        ("-X2:GND:2", "-C1:0V"),
        ("-X2:GND:3", "-C1:-"),
        ("-X2:GND:4", "-Q11:A2"),
        ("-X2:GND:5", "-P1:X2"),
        ("-X2:GND:6", "-Q21:A2"),
        ("-X2:GND:7", "-P2:X2"),
    ):
        ends = ground[designation]["side_a"].split(fr.derive.CELL_SEPARATOR)
        assert landing in ends, f"{designation} does not land on {landing}: {ends}"


def test_x3_matches_terminal_plan(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    rows = _read_rows(out_dir / "cabinet" / "pump-cabinet-v1.6-terminals-X3.csv")
    assert len(rows) == 8, f"expected exactly 8 rows on -X3, got {len(rows)}: {rows}"
    assert rows == EXPECTED_X3
