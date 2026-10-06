"""S10: the one re-partition pass re-runs `plan_pages` and `references`: no stale decision.

Hand-built (`dd_chain_fixtures.contactor_with_pole_one_wired`): K1 beside three 2CO relays K2, K3
and K4, fed from the XA strip. On the estimated column widths the first pass's plan ends page 1 with
K3's coil and the column of an XA terminal side by side, and `references` joins the run of their
ports at the columns' top (S12). Placed, a column takes more than its estimate (C21), and the
re-partition moves that terminal's column to page 2: the run has no neighbour left. Every
decision of the final pass must come from the final plans (S10), so that run is no longer joined
and its ports are drawn by references. Reusing the first pass's decisions instead hands `place`
a join whose column is not on its page.
"""

import pytest
from dd_chain_fixtures import contactor_with_pole_one_wired

from fransys_layout.engines.schematic import engine


def _passes() -> list:
    """Each `place_pages` call of the fixture's layout: its plans and its decisions."""
    calls: list = []
    original = engine.place_pages

    def spy(run, drawn, planned, widths, decide):
        result = original(run, drawn, planned, widths, decide)
        calls.append((planned.plans, result[2][0]))
        return result

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(engine, "place_pages", spy)
        contactor_with_pole_one_wired(relays=True)
    return calls


def test_the_re_partition_decides_again_on_the_final_plans() -> None:
    """Pass 1 joins a run the re-partition splits across two pages; the final pass does not."""
    # UNDO: engines/schematic/engine.py `_placed`: the second pass's `place_pages(run, drawn,
    #   planned, grown, decide)` -> `place_pages(run, drawn, planned, grown, lambda _: decided)`
    #   (pass 1's decisions reused in pass 2)
    (first_plans, first), (final_plans, final) = _passes()
    page_of = {
        one.column: (plan.drawing_set, plan.number) for plan in final_plans for one in plan.columns
    }
    # the premise: pass 1 joined one run, and the re-partition put its two columns apart
    (split,) = first.joins
    assert first_plans != final_plans
    assert len({page_of[end.column] for end in split.ends}) == 2
    # the final pass decided on the final plans: each joined run's columns stand side by side
    # on its own page, the split run is not one of them, and its ports carry references
    for run in final.joins:
        (plan,) = (
            p for p in final_plans if (p.drawing_set, p.number) == (run.drawing_set, run.page)
        )
        order = [one.column for one in plan.columns]
        at = [order.index(end.column) for end in run.ends]
        assert at == list(range(at[0], at[0] + len(at)))
    assert split not in final.joins
    assert {end.port for end in split.ends} <= {one.port for one in final.markers}
