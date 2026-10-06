"""Structure checks: what sits outside the cabinet, the cabinet as a unit, the shape of `out/`.

Three things this design decided and nothing else pins down:

- Every item outside the cabinet is at the one location `+EXT` (owner ruling 2026-09-24). No
  location `FLD`, `DB` or `NET` exists, and an item added outside the cabinet at any other
  location fails the first test.
- The cabinet is the unit `pump-cabinet` revision `1.5`, with its five revisions in order; the
  relay board is a unit nested in it, and the cabinet's parts list shows the board as one line
  (its own relays belong to the board's list).
- the three `fr.write` calls produce exactly the three folders `cabinet/`, `board/` and `all/`, each with
  its own set of files, and no file directly in the root of `out/`.
"""

import csv
from pathlib import Path

import fransys as fr

# The model's tables are read through `fr.derive`'s top level (Schematika v0.3.4).
# `fr.derive.units` is the table of `Unit` records; the sorted unit ids are `fr.derive.unit_ids`.
Aspect = fr.derive.Aspect
aspect_nodes = fr.derive.aspect_nodes
items = fr.derive.items
placements = fr.derive.placements
units = fr.derive.units

# Items placed directly at +EXT: the upstream strip, both motors, the Ethernet switch, and
# every cable that runs from the cabinet to something outside it: `-W1`, `-W11`, `-W21` and the
# `-W3` harness with its two plugs and its cable (designer ruling 2026-09-24).
EXT_ITEMS = {"X0", "M1", "M2", "W1", "W11", "W21", "K1", "W3", "W3-J1", "W3-J2", "W3-W1"}

CABINET_FILES = {
    "pump-cabinet-v1.5-bom.csv",
    "pump-cabinet-v1.5.pdf",
    "pump-cabinet-v1.5-designations.csv",
    "pump-cabinet-v1.5-plc.csv",
    "pump-cabinet-v1.5-terminals-X01.csv",
    "pump-cabinet-v1.5-terminals-X1.csv",
    "pump-cabinet-v1.5-terminals-X2.csv",
    "pump-cabinet-v1.5-terminals-X3.csv",
    "pump-cabinet-v1.5-wago-U1.xml",
    "pump-cabinet-v1.5-wires.csv",
}
BOARD_FILES = {
    "relay-interface-board-v1.3-bom.csv",
    "relay-interface-board-v1.3-connectors.csv",
    "relay-interface-board-v1.3-designations.csv",
    "relay-interface-board-v1.3-plc.csv",
    "relay-interface-board-v1.3.pdf",
    "relay-interface-board-v1.3-wires.csv",
}
ALL_FILES = {
    "EX-1-v1.1-bom.csv",
    "pump-cabinet-v1.5.pdf",
    "EX-1-v1.1-cables.csv",
    "EX-1-v1.1-connectors-PLC-C1-U1-U2.csv",
    "EX-1-v1.1-designations.csv",
    "EX-1-v1.1-overview.html",
    "EX-1-v1.1-plc.csv",
    "relay-interface-board-v1.3.pdf",
    "EX-1-v1.1.pdf",
    "EX-1-v1.1-terminals-C1-U1-X01.csv",
    "EX-1-v1.1-terminals-C1-U1-X1.csv",
    "EX-1-v1.1-terminals-C1-U1-X2.csv",
    "EX-1-v1.1-terminals-C1-U1-X3.csv",
    "EX-1-v1.1-terminals-EXT-X0.csv",
    "EX-1-v1.1-wago-PLC-C1-U1-U1.xml",
    "EX-1-v1.1-wires.csv",
}
EXPECTED_FILES = {"cabinet": CABINET_FILES, "board": BOARD_FILES, "all": ALL_FILES}


def test_every_item_outside_the_cabinet_is_at_ext(built: tuple[fr.BuildResult, Path, Path]) -> None:
    """The only outside location is `+EXT`, and the items placed directly at it are exactly the expected set.

    Every item without a unit is at `+EXT`, so a new item outside the cabinet at any other
    location fails.
    """
    model = built[0].model
    nodes = aspect_nodes(model)
    locations = {node.label: node for node in nodes.values() if node.aspect is Aspect.LOCATION}
    assert locations, "the model has no location at all"
    old_names = set(locations) & {"FLD", "DB", "NET"}
    assert not old_names, f"locations that are now +EXT: {sorted(old_names)}"
    assert "EXT" in locations, f"no location EXT, only {sorted(locations)}"
    ext = locations["EXT"]

    all_items = items(model)
    placed_at_ext = {
        fr.derive.item_designation(model, placement.item)
        for placement in placements(model).values()
        if placement.node == ext.id
    }
    assert placed_at_ext, "no item is placed at +EXT"
    assert placed_at_ext == EXT_ITEMS, (
        f"items at +EXT differ; missing: {sorted(EXT_ITEMS - placed_at_ext)}, "
        f"unexpected: {sorted(placed_at_ext - EXT_ITEMS)}"
    )

    # `C1` (the cabinet's panel) sits under `EXT`, so a unit item is under `EXT` too; what
    # must not happen is a unit item placed directly at `EXT`.
    at_ext = set(fr.derive.items_at(model, ext.id))
    placed_directly = {
        placement.item for placement in placements(model).values() if placement.node == ext.id
    }
    in_a_unit = {item_id for item_id in placed_directly if all_items[item_id].unit is not None}
    assert not in_a_unit, (
        f"items of a unit placed directly at +EXT: {sorted(fr.derive.item_designation(model, i) for i in in_a_unit)}"
    )
    unitless = {item_id for item_id, item in all_items.items() if item.unit is None}
    assert unitless, "no item without a unit"
    outside_ext = {fr.derive.item_designation(model, item_id) for item_id in unitless - at_ext}
    assert not outside_ext, f"items with no unit and not at +EXT: {sorted(outside_ext)}"


def test_cabinet_is_unit_pump_cabinet_rev_1_5_with_all_revisions(
    built: tuple[fr.BuildResult, Path, Path],
) -> None:
    """`pump-cabinet` rev `1.5` has revisions `1` to `5`, oldest first; the board is its child.

    The cabinet's `bom.csv` lists the board as one unit line (its number `SKX-RIB-2` in `mpn`,
    its title in `description`) and none of the board's own parts.
    """
    result, out_dir, _ = built
    model = result.model
    by_release_name = {
        fr.derive.unit_release(model, unit.id).name: unit for unit in units(model).values()
    }
    assert set(by_release_name) == {"pump-cabinet", "relay-interface-board"}, sorted(
        by_release_name
    )
    cabinet = by_release_name["pump-cabinet"]
    board = by_release_name["relay-interface-board"]
    cabinet_release = fr.derive.unit_release(model, cabinet.id)
    board_release = fr.derive.unit_release(model, board.id)
    assert cabinet_release.revision == 5, f"cabinet revision is {cabinet_release.revision!r}"
    assert cabinet.parent is None, "the cabinet unit must be a top-level unit"
    assert board_release.revision == 3, f"board revision is {board_release.revision!r}"
    assert board.parent == cabinet.id, "the relay board must be nested in the cabinet unit"

    history = fr.derive.revision_history(model, cabinet.release)
    assert history, "the cabinet unit has no revision history"
    assert [(r.revision, r.date, r.text, r.created) for r in history] == [
        (1, "2026-09-01", "First release", "SK"),
        (2, "2026-09-23", "Overload feedback to the PLC", "SK"),
        (3, "2026-10-02", "TeSys D parts, 24V and GND rails, IEC wire colours", "SK"),
        (4, "2026-10-05", "Unit tags, links, busbars and rail bonds, energy on fed supplies", "SK"),
        (5, "2026-10-06", "Three phases on four terminals each, pump n on terminal n+2", "SK"),
    ]

    with (out_dir / "cabinet" / "pump-cabinet-v1.5-bom.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert rows, "the cabinet's bom.csv has no line"
    unit_lines = [row for row in rows if row["mpn"] == "SKX-RIB-2"]
    assert unit_lines == [
        {
            "mpn": "SKX-RIB-2",
            "revision": "1.3",
            "manufacturer": "",
            "description": "Relay interface board",
            "count": "1",
            "designations": "-U2",
        }
    ], f"the cabinet's bom.csv must list the board as one unit line, got {unit_lines}"
    board_parts = {"40.61.9.024.1000"}  # the board's relay
    stray = [
        row["mpn"] for row in rows if row["mpn"] in board_parts or "U2-" in row["designations"]
    ]
    assert not stray, f"the cabinet's bom.csv lists the board's own parts: {stray}"


def test_out_holds_exactly_cabinet_board_and_all(
    built: tuple[fr.BuildResult, Path, Path],
) -> None:
    """`out/` has the three folders and no file in its root; each folder has exactly its files."""
    _, out_dir, _ = built
    entries = list(out_dir.iterdir())
    assert entries, "the out folder is empty"
    loose_files = sorted(p.name for p in entries if p.is_file())
    assert not loose_files, f"files directly in the out root: {loose_files}"
    assert sorted(p.name for p in entries) == sorted(EXPECTED_FILES), (
        f"folders in the out root: {sorted(p.name for p in entries)}"
    )
    for folder, expected in EXPECTED_FILES.items():
        assert expected, f"no expected file listed for {folder}/"
        found = {
            path.relative_to(out_dir / folder).as_posix()
            for path in (out_dir / folder).rglob("*")
            if path.is_file()
        }
        assert found, f"{folder}/ holds no file"
        assert found == expected, (
            f"{folder}/ differs; missing: {sorted(expected - found)}, "
            f"unexpected: {sorted(found - expected)}"
        )
