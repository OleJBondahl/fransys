"""R530 B4 (layout-0394): `footprint_keeps` is the one footprint-keep builder, for place, route."""

from __future__ import annotations

from dataclasses import replace

from options_fixtures import core_options

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.clearance import footprint_keeps
from fransys_layout.core.node_names import box_y_node
from fransys_layout.core.pack_sep import hard_soft
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.place_foreign import _foreign, cell_keeps
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import _spans
from fransys_layout.core.values import Box

from .conftest import MARKER
from .cut_fixtures import AREA, box_sym, elem
from .flow_builders import net
from .pipeline_fixtures import cut_of
from .place_fixtures import bundle_fan


def _page():
    opts = core_options(
        marker=MARKER,
    )
    prob = bundle_fan()
    (env,) = page_envs(cut_of(prob, opts), prob, opts)
    return env, place_x(env)[0]


def _cells(env):
    return [cell for row in env.plan.rows for col in row.columns for cells in env.pcs[col].lanes for cell in cells]


def test_the_builder_emits_one_footprint_keep_per_cell_of_a_box() -> None:
    box = Box(1, 2, 3, 4)
    keeps = list(footprint_keeps((("n1", "A"), ("", "B")), box))
    assert [(k.node, k.owner, k.kind, k.box) for k in keeps] == [
        ("n1", "A", "footprint", box),
        ("", "B", "footprint", box),
    ]


def test_every_cell_gives_a_foreign_keep_of_its_hard_box() -> None:
    env, x = _page()
    keeps = list(cell_keeps(env, x, range(len(env.plan.rows)), frozenset()))
    cells = _cells(env)
    assert len(keeps) == len(cells) > 1
    for k, cell in zip(keeps, cells, strict=True):
        hard, _ = hard_soft(
            env.syms[cell.sym],
            cell,
            in_row=cell.sym in env.in_row,
            tag_stagger=env.options.tag_stagger,
        )
        assert (k.kind, k.owner, k.box.y, k.box.w, k.box.h) == (
            "footprint",
            cell.sym,
            hard.y,
            hard.w,
            hard.h,
        )


def test_the_route_side_keep_of_a_placed_cell_equals_the_place_side_keep() -> None:
    env, x = _page()
    placed = next(iter(cell_keeps(env, x, range(len(env.plan.rows)), frozenset())))
    absolute = Box(placed.box.x, 0, placed.box.w, placed.box.h)
    (route,) = footprint_keeps((("", placed.owner),), absolute)
    assert route == placed._replace(node="", box=absolute)


def test_the_cells_of_own_symbols_give_no_keep() -> None:
    env, x = _page()
    rows = range(len(env.plan.rows))
    everyone = list(cell_keeps(env, x, rows, frozenset()))
    own = frozenset({everyone[0].owner})
    kept = list(cell_keeps(env, x, rows, own))
    assert kept == [k for k in everyone if k.owner not in own]
    assert len(kept) < len(everyone)


def _two_cards():
    """Box A1 fans p1 to k1 and k3; box A2 (a card too) is wired to its own element: foreign to that fan."""
    syms = (box_sym(4), replace(box_sym(2), id="A2"), *(elem(s, 40) for s in ("k1", "k3", "k5")))
    nets = [net("v", "A1.p1", "k1.n", "k3.n"), net("w", "A2.p1", "k5.n")]
    opts = core_options(marker=MARKER)
    prob = PlacementProblem(AREA, syms, tuple(nets), Facts(far_ends=()))
    (env,) = page_envs(cut_of(prob, opts), prob, opts)
    return env, place_x(env)[0]


def test_a_foreign_card_box_gives_a_footprint_keep_its_fans_trunk_clears() -> None:
    """KI-731: a card is no column cell, yet its folded footprint (marker hangings) is foreign to the fan of another box."""
    env, x = _two_cards()
    span = next(s for s in _spans(env, x) if s.fan.startswith("f:v"))
    keeps = list(_foreign(env, x, span, range(len(env.plan.rows))))
    held = [k for k in keeps if k.owner == "A2"]
    assert [(k.kind, k.node, k.box.y, k.box.h) for k in held] == [
        ("footprint", box_y_node("A2"), env.syms["A2"].footprint.y, env.syms["A2"].footprint.h)
    ]
    assert not [k for k in keeps if k.owner == "A1"]
