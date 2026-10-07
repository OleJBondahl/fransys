"""ENGINE-DIGITS (layout-0140): a column holds the side reference box its page draws.

`engine.py` sizes columns with `side_reference_rooms` at the floor digits, before any page is
planned. In a run of two sets the page draws the box wider (`p<set>.<page>`, `+<location>`), so
the early estimate is narrower than the drawn box. C21 (`placed_widths`) grows each column to
its placed keep-out, which holds the per-page box, and the second `_placed` pass starts from
those widths. The final widths therefore hold the box and the early FLOOR call needs no fix.
"""

from functools import cache
from importlib import import_module
from typing import Any
from unittest.mock import patch

from layout_cabinet import build_cabinet

from fransys_layout.engines.schematic.engine import StageResults, stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import hull
from fransys_layout.stages.lookups import placed_keepout
from fransys_layout.stages.pagerun import place_pages
from fransys_layout.stages.references.digits import FLOOR
from fransys_model.kernel import freeze


@cache
def _run() -> tuple[StageResults, dict[str, Any]]:
    """The two-location cabinet with side terminals: results and what the engine passed."""
    seen: dict[str, Any] = {"early": [], "page": [], "passes": []}
    model = freeze(build_cabinet(second_location=True, side_terminals=True))
    engine = import_module("fransys_layout.engines.schematic.engine")
    pagerun = import_module("fransys_layout.stages.pagerun")

    def watch(where: str, module: Any) -> Any:
        real = module.side_reference_rooms

        def spy(columns: Any, drawn: Any, wiring: Any, **kwargs: Any) -> Any:
            found = real(columns, drawn, wiring, **kwargs)
            seen[where].extend(
                (wiring.digits, box.width) for rooms in found.values() for _, box in rooms
            )
            return found

        return patch.object(module, "side_reference_rooms", spy)

    def passes(run: Any, drawn: Any, planned: Any, widths: Any, decide: Any) -> Any:
        found = place_pages(run, drawn, planned, widths, decide)
        seen["passes"].append(widths)
        return found

    with (
        watch("early", engine),
        watch("page", pagerun),
        patch.object(engine, "place_pages", passes),
    ):
        results, _ = stage_results(model, read_inputs(model))
    seen["gap"] = read_inputs(model).profile.column_gap
    return results, seen


def test_the_early_call_is_floor_narrow_and_the_page_draws_the_wider_box() -> None:
    """Guard: the fixture builds the case; the early estimate is narrower than the drawn box."""
    _, seen = _run()
    assert seen["early"]
    assert {digits for digits, _ in seen["early"]} == {FLOOR}
    early = max(width for _, width in seen["early"])
    drawn = max(width for _, width in seen["page"])
    assert early < drawn


def test_the_final_pass_columns_hold_the_drawn_side_box() -> None:
    """Each final-pass column is as wide as its placed keep-outs plus the gap, the box inside.

    CAN-FAIL: engine `_placed`: return after the first pass (the FLOOR-estimated widths stay),
    and the rail terminal's column is narrower than its keep-out, which holds the 56 G box.
    """
    results, seen = _run()
    layout = results.layout
    markers = [one for one in layout.markers if not one.vertical]
    assert markers
    final = {one.column: one.width for one in seen["passes"][-1]}
    held: dict[Any, list[Any]] = {}
    for one in layout.placed:
        held.setdefault((one.column, one.drawing_set, one.page), []).append(placed_keepout(one))
    for (column, set_, page), keepouts in held.items():
        assert final[column] >= hull(keepouts).width + seen["gap"], (column, set_, page)
    for one in markers:
        page = [
            k
            for (_, set_, number), ks in held.items()
            for k in ks
            if (set_, number) == (one.drawing_set, one.page)
        ]
        assert any(placed_has(k, one.box) for k in page), one.box


def placed_has(keepout: Any, box: Any) -> bool:
    """`box` lies within `keepout`'s x span: a side box stands in its own function's keep-out."""
    return keepout.x <= box.x and box.x + box.width <= keepout.x + keepout.width
