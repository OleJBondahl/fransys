"""Stage 5, x: a page's rows solved by the row graph, the findings for a row past the page."""

from __future__ import annotations

from dataclasses import fields
from itertools import pairwise

from fransys_layout.core import Lane, Options, PlacementProblem
from fransys_layout.core.geometry import column_extent
from fransys_layout.core.pack_row import RowSpec, row_width, solve_row
from fransys_layout.core.place_env import PageEnv, page_envs
from fransys_layout.core.place_x import place_x, row_specs

from .cut_fixtures import AREA, elem, net
from .pipeline_fixtures import cut_of
from .place_fixtures import card_with_coils, two_edge_card, wide_row


def env_of(prob: PlacementProblem, options: Options | None = None) -> PageEnv:
    """The env of the first page of a problem."""
    opts = options or Options()
    return page_envs(cut_of(prob, opts), prob, opts)[0]


def _pins(x: dict[str, int], count: int) -> list[int]:
    return [x[f"pin:A1:p{i}"] for i in range(1, count + 1)]


def test_card_pins_spread_to_meet_their_coils() -> None:
    """Each pin stands under its coil column and the pins keep the coil width apart."""
    env = env_of(card_with_coils(4, 84))
    x, findings = place_x(env)
    pins = _pins(x, 4)
    for i, (box, pin, off) in enumerate(env.attach.values(), 1):
        assert x[f"col:c:k{i}"] + off == x[f"pin:{box}:{pin}"]
    assert all(b - a >= 84 for a, b in pairwise(pins))
    assert x["box:A1:L"] < pins[0]
    assert pins[-1] < x["box:A1:R"]
    assert findings == ()


def test_each_attached_column_stands_on_its_pin() -> None:
    """The column's x plus its lane offset is the x of the pin it hangs on."""
    env = env_of(two_edge_card(16, 94))
    x, _ = place_x(env)
    assert env.attach
    for col, (box, pin, off) in env.attach.items():
        assert x[f"col:{col}"] + off == x[f"pin:{box}:{pin}"]


def test_two_edges_second_half_stands_above_at_r180() -> None:
    """A pin on the card's north edge hangs a flipped column whose cells turn to R180."""
    env = env_of(two_edge_card(16, 94))
    edges = dict(next(b for b in env.blocks.values() if b.kind == "card").pin_edges)
    assert {"N", "S"} <= set(edges.values())
    for col, (_, pin, _) in env.attach.items():
        pc = env.pcs[col]
        north = edges[pin] == "N"
        assert pc.flipped is north
        assert (pc.lanes[0][0].orient == "R180") is north


def _reach(spec: RowSpec, x: dict[str, int]) -> int:
    """The rightmost edge of the row's columns."""
    best = 0
    for col, pc in spec.pcs.items():
        lanes = tuple(Lane(cells, off) for cells, off in zip(pc.lanes, pc.offsets, strict=True))
        best = max(best, x[f"col:{col}"] + column_extent(spec.syms, lanes, spec.in_row)[1])
    return best


def _four_columns() -> PlacementProblem:
    syms = [elem(f"{k}{i}", 100) for i in range(4) for k in "ab"]
    nets = [net(f"n{i}", f"a{i}.s", f"b{i}.n") for i in range(4)]
    return PlacementProblem(AREA, tuple(syms), tuple(nets))


def test_justify_lays_columns_out_to_the_page_margin() -> None:
    """Justified, the row ends within one wiring grid of the right margin; packed it falls short."""
    ends = {}
    for justify in (True, False):
        env = env_of(_four_columns(), Options(justify=justify))
        spec = row_specs(env)[0]
        assert len(spec.cols) == 4
        ends[justify] = _reach(spec, place_x(env)[0])
    limit = AREA.w - Options().margin.w
    assert limit - Options().wiring_grid < ends[True] <= limit
    assert ends[False] < limit - 100


def test_a_row_wider_than_the_page_is_left_packed_and_named() -> None:
    """One WIDER_THAN_PAGE names block, overflow and fix; the row starts at the margin."""
    env = env_of(wide_row())
    spec = row_specs(env)[0]
    x, findings = place_x(env)
    overflow = solve_row(spec, AREA.w)[1]
    assert overflow > 0
    (finding,) = findings
    assert finding.code == "WIDER_THAN_PAGE"
    assert finding.subject == env.plan.rows[0].blocks[0]
    assert finding.page == env.plan.page
    for word in (f"page {env.plan.page}", "row 0", f"{overflow} G", "short_height"):
        assert word in finding.text
    left = column_extent(spec.syms, (Lane(spec.pcs["c:e"].lanes[0], 0),), spec.in_row)[0]
    assert x["col:c:e"] + left == Options().margin.w
    assert place_x(env_of(card_with_coils()))[1] == ()


def test_stage_5_never_raises_for_width() -> None:
    """A page wider than its area still comes back with positions."""
    x, findings = place_x(env_of(wide_row()))
    assert "col:c:e" in x
    assert len(findings) == 1


def test_fixed_box_pins_chain_at_the_pitch() -> None:
    """Fixed pins stand exactly a pitch apart and leave the wide coils off their pins."""
    fixed = Options(box_pins="fixed")
    env = env_of(card_with_coils(4, 84), fixed)
    x, _ = place_x(env)
    pitch = fixed.box_pin_pitch_min
    assert [b - a for a, b in pairwise(_pins(x, 4))] == [pitch] * 3
    assert any(x[f"col:{c}"] != x[f"pin:{b}:{p}"] for c, (b, p, _) in env.attach.items())
    spread, _ = place_x(env_of(card_with_coils(4, 84)))
    assert all(b - a >= 84 for a, b in pairwise(_pins(spread, 4)))


def test_env_flips_agree_with_one_row() -> None:
    """The row spec's placed columns equal the env's, but for the row index."""
    for prob in (card_with_coils(), two_edge_card()):
        env = env_of(prob)
        for spec in row_specs(env):
            for col, pc in spec.pcs.items():
                for f in fields(pc):
                    if f.name != "row":
                        assert getattr(pc, f.name) == getattr(env.pcs[col], f.name)
    assert row_width(row_specs(env_of(card_with_coils()))[0]) > 0
