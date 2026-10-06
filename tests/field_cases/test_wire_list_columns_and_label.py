"""Field case: the builder's wire list, `<set>-wires.csv`.

The engineering shape: a small cabinet with one connector pin on a nested board and one terminal
of a strip, joined by one coloured wire of a given size. The panel builder cuts the wire
from the list and prints the same text at both of its ends.

The bug: the export was the wire-label CSV, `wire-labels.csv`, with the columns `label`,
`end_a_designation` and `end_b_designation`. It carried no colour and no size, and its label was
only what the author typed (`None` when none was). The builder needs `from`, `to`, `colour`,
`cross_section_mm2` and a `label` that reads from-to, as `-B12:96 -Q11:A1`.

Decision 0092 (the owner's answers in CONVENTIONS-V06 V8): `wires.csv` with those five columns, one
row per wire, the label being both end designations with one space between.
"""

import csv
import io
from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from fransys.colours import BU

if TYPE_CHECKING:
    from pathlib import Path


class _Open(NamedTuple):
    """A unit with no boundary device to hand back."""


_COLUMNS = ["from", "to", "colour", "cross_section_mm2", "label"]


@fr.unit(
    "demo-cabinet",
    revision=1,
    interface_version=1,
    date="2026-10-02",
    text="First release",
    by="XX",
)
def _cabinet(d: fr.Design) -> _Open:
    """The invented cabinet: a nested board's plug wired to a strip terminal."""
    board = d.device(None, "DEMO-PCB-IO", name="board")
    plug = d.device("X1", "DEMO-CONN-2P", parent=board)
    strip = d.terminal_strip("X9", "DEMO-TB-2.5")
    d.wire(plug["1"], strip[1].outer, wire=(BU, 0.5))
    return _Open()


def _wire_list(tmp_path: Path) -> list[dict[str, str]]:
    """One build and one write of the invented cabinet; the rows of its wire list."""
    d = fr.design("demo_parts")
    d.add(_cabinet, "CAB")
    written = fr.write(fr.build(d), tmp_path)
    (path,) = (p for p in written if p.name.endswith("wires.csv"))
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def test_the_wire_list_has_the_five_columns_and_one_from_to_label(tmp_path: Path) -> None:
    """Both ends in the label, one space between, in the `-X:n -Y:m` form."""
    rows = _wire_list(tmp_path)
    assert list(rows[0]) == _COLUMNS
    (row,) = rows
    assert (row["colour"], row["cross_section_mm2"]) == ("BU", "0.5")
    ends = {row["from"], row["to"]}
    assert len(ends) == 2
    assert row["label"] in {f"{row['from']} {row['to']}", f"{row['to']} {row['from']}"}
    assert all(end.startswith("-") and ":" in end for end in row["label"].split(" "))
    assert len(row["label"].split(" ")) == 2


@fr.unit(
    "demo-cabinet",
    revision=1,
    interface_version=1,
    date="2026-10-02",
    text="First release",
    by="XX",
)
def _empty_cabinet(d: fr.Design) -> _Open:
    """The same cabinet with only the board."""
    d.device(None, "DEMO-PCB-IO", name="board")
    return _Open()


def test_the_wire_label_csv_is_gone(tmp_path: Path) -> None:
    """The old name is not written beside the new one."""
    d = fr.design("demo_parts")
    d.add(_empty_cabinet, "CAB")
    written = fr.write(fr.build(d), tmp_path)
    assert not [p for p in written if "wire-labels" in p.name]
    assert [p for p in written if p.name.endswith("wires.csv")]
