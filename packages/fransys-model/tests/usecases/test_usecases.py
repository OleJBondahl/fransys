"""WP17 golden tests over the two synthetic use cases (ROADMAP WP17).

Golden files live in `tests/golden/`, written by `tests/usecases/regenerate_goldens.py`. Row-query
golden tests are parametrized by query name so the parametrize id names the query,
covering design/derive-queries.md's query table the way ROADMAP WP17 asks ("every row query").
"""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
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
from fransys_model.kernel import Id, Model, dumps, freeze, merge
from fransys_model.vocab.tables import items as items_of

if TYPE_CHECKING:
    from fransys_model.vocab.core import Item

_GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden"


def _item_by_designation(model: Model, designation: str) -> Id[Item]:
    (item,) = (
        i for i in items_of(model).values() if own_designation_or_none(model, i) == designation
    )
    return item.id


def test_cabinet_canonical_json_matches_golden() -> None:
    """`build_cabinet`'s frozen canonical JSON is byte-stable against the golden file."""
    model = freeze(build_cabinet())
    golden = (_GOLDEN_DIR / "cabinet.json").read_text(encoding="utf-8")
    assert dumps(model) == golden


def test_cabinet_digest_matches_golden() -> None:
    """`build_cabinet`'s digest matches the golden value, so a drift is caught immediately."""
    model = freeze(build_cabinet())
    golden_digest = (_GOLDEN_DIR / "cabinet.digest").read_text(encoding="utf-8").strip()
    assert model.digest == golden_digest


def test_harness_board_canonical_json_matches_golden() -> None:
    """`build_harness_board`'s frozen canonical JSON is byte-stable against the golden file."""
    model = freeze(build_harness_board())
    golden = (_GOLDEN_DIR / "harness_board.json").read_text(encoding="utf-8")
    assert dumps(model) == golden


def test_harness_board_digest_matches_golden() -> None:
    """`build_harness_board`'s digest matches the golden value."""
    model = freeze(build_harness_board())
    golden_digest = (_GOLDEN_DIR / "harness_board.digest").read_text(encoding="utf-8").strip()
    assert model.digest == golden_digest


def test_f1_is_two_distinct_items_across_the_merged_designs() -> None:
    """Merging both drafts keeps the board's `-F1` and the cabinet's `-F1` as two `Item`s.

    Same designation string, different `Id`, different `parent` (design/examples.md
    11).
    """
    model = freeze(merge(build_cabinet(), build_harness_board()))
    f1_items = [i for i in items_of(model).values() if own_designation_or_none(model, i) == "F1"]
    assert len(f1_items) == 2
    assert f1_items[0].id != f1_items[1].id
    assert f1_items[0].parent != f1_items[1].parent


@pytest.mark.parametrize(
    "query_name",
    ["bom_lines", "designation_list", "plc_channel_rows", "wire_rows"],
)
def test_cabinet_whole_model_row_query_matches_golden(query_name: str) -> None:
    """A whole-model row query over `build_cabinet` matches its golden dump."""
    queries = {
        "bom_lines": bom_lines,
        "designation_list": designation_list,
        "plc_channel_rows": plc_channel_rows,
        "wire_rows": wire_rows,
    }
    model = freeze(build_cabinet())
    rows = queries[query_name](model)
    golden = (_GOLDEN_DIR / f"cabinet.{query_name}.json").read_text(encoding="utf-8")
    assert repr(rows) == golden


def test_cabinet_terminal_rows_for_x1_matches_golden() -> None:
    """`terminal_rows` for strip `X1` matches its golden dump."""
    model = freeze(build_cabinet())
    rows = terminal_rows(model, _item_by_designation(model, "X1"))
    golden = (_GOLDEN_DIR / "cabinet.terminal_rows.x1.json").read_text(encoding="utf-8")
    assert repr(rows) == golden


def test_cabinet_cable_rows_for_w1_matches_golden() -> None:
    """`cable_rows` for cable `W1` matches its golden dump."""
    model = freeze(build_cabinet())
    rows = cable_rows(model, _item_by_designation(model, "W1"))
    golden = (_GOLDEN_DIR / "cabinet.cable_rows.w1.json").read_text(encoding="utf-8")
    assert repr(rows) == golden


def test_harness_board_board_netlist_for_jb1_matches_golden() -> None:
    """`board_netlist` for board `JB1` matches its golden dump."""
    model = freeze(build_harness_board())
    netlist = board_netlist(model, _item_by_designation(model, "JB1"))
    golden = (_GOLDEN_DIR / "harness_board.board_netlist.jb1.json").read_text(encoding="utf-8")
    assert repr(netlist) == golden


def test_harness_board_overview_graph_matches_golden() -> None:
    """`overview_graph` of the unnumbered harness design (the fan-out cable has no designation)."""
    graph = overview_graph(freeze(build_harness_board()))
    golden = (_GOLDEN_DIR / "harness_board.overview_graph.json").read_text(encoding="utf-8")
    assert repr(graph) == golden


def test_harness_board_harness_cables_for_wh1_matches_golden() -> None:
    """`harness_cables` for harness `WH1`, after numbering the fan-out cable `W1`, matches."""
    model, _ = number(freeze(build_harness_board()))
    cables = harness_cables(model, _item_by_designation(model, "WH1"))
    golden = (_GOLDEN_DIR / "harness_board.harness_cables.wh1.json").read_text(encoding="utf-8")
    assert repr(cables) == golden
