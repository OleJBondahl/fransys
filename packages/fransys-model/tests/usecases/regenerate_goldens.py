"""Write the golden files `test_usecases.py` compares against (run by hand, never by pytest).

    uv run python tests/usecases/regenerate_goldens.py

A golden changes only on purpose: run this, read `git diff tests/golden/`, and commit the
diff together with the change that caused it.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from cabinet import build_cabinet
from harness_board import build_harness_board

from fransys_model.derive import (
    board_netlist,
    bom_lines,
    cable_rows,
    designation_list,
    harness_cables,
    number,
    overview_graph,
    plc_channel_rows,
    terminal_rows,
    wire_rows,
)
from fransys_model.derive.designation import own_designation_or_none
from fransys_model.kernel import dumps, freeze
from fransys_model.vocab.tables import items as items_of

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item

_GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"


def _item_by_designation(model: Model, designation: str) -> Id[Item]:
    (item,) = (
        i for i in items_of(model).values() if own_designation_or_none(model, i) == designation
    )
    return item.id


def _write(name: str, text: str) -> None:
    (_GOLDEN_DIR / name).write_bytes(text.encode("utf-8"))


def main() -> None:
    """Write every golden file."""
    _GOLDEN_DIR.mkdir(exist_ok=True)
    cabinet = freeze(build_cabinet())
    harness = freeze(build_harness_board())
    for stem, model in (("cabinet", cabinet), ("harness_board", harness)):
        _write(f"{stem}.json", dumps(model))
        _write(f"{stem}.digest", model.digest + "\n")
    for name, query in (
        ("bom_lines", bom_lines),
        ("designation_list", designation_list),
        ("plc_channel_rows", plc_channel_rows),
        ("wire_rows", wire_rows),
    ):
        _write(f"cabinet.{name}.json", repr(query(cabinet)))
    _write(
        "cabinet.terminal_rows.x1.json",
        repr(terminal_rows(cabinet, _item_by_designation(cabinet, "X1"))),
    )
    _write(
        "cabinet.cable_rows.w1.json",
        repr(cable_rows(cabinet, _item_by_designation(cabinet, "W1"))),
    )
    _write(
        "harness_board.board_netlist.jb1.json",
        repr(board_netlist(harness, _item_by_designation(harness, "JB1"))),
    )
    _write("harness_board.overview_graph.json", repr(overview_graph(harness)))
    numbered, _ = number(harness)
    _write(
        "harness_board.harness_cables.wh1.json",
        repr(harness_cables(numbered, _item_by_designation(numbered, "WH1"))),
    )


if __name__ == "__main__":
    main()
