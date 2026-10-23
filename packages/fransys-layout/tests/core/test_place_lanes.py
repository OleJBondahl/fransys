"""Stage 5, x: a column of two lanes standing on two pins of its card stands on both."""

from __future__ import annotations

from dataclasses import replace

from options_fixtures import core_options
from turn_fixtures import views_of

from fransys_layout.core import Box, Facts, Options, Pin, PlacementProblem, Sym
from fransys_layout.core.node_names import col_node, pin_node
from fransys_layout.core.pack import lane_pins
from fransys_layout.core.pack_row import RowSpec, solve_row
from fransys_layout.core.place_env import PageEnv, page_envs
from fransys_layout.core.place_x import place_x, row_specs

from .cut_fixtures import AREA, LABEL, box_sym, elem, net
from .pipeline_fixtures import cut_of


def dual() -> Sym:
    """A symbol with pins a and b in two nodes on its south side, 16 G apart."""
    box = Box(-16, -16, 32, 32)
    pins = (Pin("a", "S", -8, 16, 0), Pin("b", "S", 8, 16, 1))
    return Sym(
        "dual",
        None,
        "",
        LABEL,
        pins,
        (("a",), ("b",)),
        views=views_of(box, box, box, pins, ("R0", "R180")),
    )


def _problem() -> PlacementProblem:
    syms = (box_sym(4), dual(), elem("k", 84))
    nets = (net("na", "dual.a", "A1.p2"), net("nb", "dual.b", "A1.p1"), net("nk", "A1.p4", "k.n"))
    return PlacementProblem(AREA, syms, nets, facts=Facts())


def _env(options: Options) -> PageEnv:
    prob = _problem()
    return page_envs(cut_of(prob, options), prob, options)[0]


def _stands(spec: RowSpec, x: dict[str, int]) -> list[bool]:
    """Whether each of the dual column's two lanes stands on its card pin."""
    (box, first, off), (second, more) = spec.attach["c:dual"], spec.more_pins["c:dual"][0]
    return [
        x[col_node("c:dual")] + off == x[pin_node(box, first)],
        x[col_node("c:dual")] + more == x[pin_node(box, second)],
    ]


def test_a_two_lane_column_stands_on_both_its_card_pins() -> None:
    """Justified or packed, lane 0 stands on its pin and lane 1 on the second, 16 G on."""
    for justify in (True, False):
        options = core_options(
            justify=justify,
            box_pin_pitch_min=16,
            flip_turn="R180",
            tag_stagger=True,
            label_gap=8,
            parallel_pitch=48,
            driver_first=True,
            arrow_sides=("E", "W"),
        )
        env = _env(options)
        spec = row_specs(env)[0]
        assert spec.pcs["c:dual"].offsets == (0, 16)
        assert lane_pins(tuple(c for c in env.flow.columns if c.id in spec.cols), env.blocks) == {
            "c:dual": (("p2", 16),)
        }
        assert _stands(spec, place_x(env)[0]) == [True, True]
        untied = solve_row(replace(spec, more_pins={}), AREA.w)[0]
        if justify:  # without the tie the second pin drifts off its column (432, not 48)
            assert _stands(spec, untied) == [True, False]
