"""ROUTE-FIX B: the router's trade between a crossing, a bend and a metre is the score's trade."""

from options_fixtures import core_options

from fransys_layout.core.score import WEIGHTS


def test_the_router_penalties_are_the_score_weights_per_g_of_detour() -> None:
    """A crossing costs x/d detour G and a bend b/d, as the score weighs them."""
    opts = core_options()
    assert opts.crossing_penalty == round(WEIGHTS["x"] / WEIGHTS["d"])
    assert opts.bend_penalty == round(WEIGHTS["b"] / WEIGHTS["d"])
