"""ROUTE-FIX B: the router's trade between a crossing, a bend and a metre is the score's trade."""

from fransys_layout.core import Options
from fransys_layout.core.score import WEIGHTS


def test_the_router_penalties_are_the_score_weights_per_g_of_detour() -> None:
    """A crossing costs x/d detour G and a bend b/d, as the score weighs them."""
    opts = Options()
    assert opts.crossing_penalty == round(WEIGHTS["x"] / WEIGHTS["d"])
    assert opts.bend_penalty == round(WEIGHTS["b"] / WEIGHTS["d"])
