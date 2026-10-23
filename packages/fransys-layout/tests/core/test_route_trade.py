"""ROUTE-FIX B: the router's trade between a crossing, a bend and a metre is the score's trade."""

from options_fixtures import core_options

from fransys_layout.core.score import WEIGHTS


def test_the_router_penalties_are_the_score_weights_per_g_of_detour() -> None:
    """A crossing costs x/d detour G and a bend b/d, as the score weighs them."""
    opts = core_options(
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        parallel_pitch=48,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    assert opts.crossing_penalty == round(WEIGHTS["x"] / WEIGHTS["d"])
    assert opts.bend_penalty == round(WEIGHTS["b"] / WEIGHTS["d"])
