"""The root fixtures' digest is unchanged by the swap to `fr.build` (facade spec F9).

Each fixture is built two ways in one test run: by hand (the pipeline the fixtures used
before the facade existed: `merge`, `freeze`, `allocate_plc`, `number`,
`lay_out_schematic`) and through `fr.build`, which the fixtures now actually call
(`conftest.py`). `core` and `facet` are the real invariant and must be equal exactly.
`layout` is compared between the two constructions in this same run, never hardcoded as a
constant, because WP17 (in flight) legitimately moves it.
"""

import sys
from pathlib import Path

import fransys as fr
import fransys_parts
import pytest
from _model_build_cover import system_document
from fransys_author import Design

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    # `demo_designs` is a plain script module at the repo root, not an installed package;
    # `--import-mode=importlib` (root pyproject.toml) never puts the rootdir on `sys.path`
    # (see `conftest.py`'s own comment, which needs this for the same reason).
    sys.path.insert(0, str(_ROOT))

from demo_designs import cabinet_design, harness_with_board_design  # noqa: E402

from fransys_layout.engines.schematic import lay_out_schematic  # noqa: E402
from fransys_model.derive import allocate_plc, number  # noqa: E402
from fransys_model.kernel import freeze, merge  # noqa: E402


def _by_hand(design_factory):
    parts = fransys_parts.load("demo_parts")
    design = design_factory(parts)
    # The same `system_document()` `_by_build` now needs (PS1/PS2, decision 0037) is merged in
    # here too, by hand: this path calls `lay_out_schematic` unconditionally and never reads
    # `_has_document` itself, but the two sides' `core` digest must still compare the same
    # record set, or this test would be comparing apples (no document) to oranges (one).
    model = freeze(merge(parts, design.draft(), system_document()))
    model, _ = allocate_plc(model)
    model, _ = number(model)
    model, _ = lay_out_schematic(model)
    return model


def _by_build(design_factory):
    parts = fransys_parts.load("demo_parts")
    design = design_factory(parts)
    return fr.build(parts, design.draft(), system_document()).model


@pytest.mark.parametrize(
    "design_factory", [cabinet_design, harness_with_board_design], ids=["cabinet", "harness_board"]
)
def test_core_and_facet_digests_are_unchanged_by_the_swap(design_factory):
    hand_built = _by_hand(design_factory)
    built = _by_build(design_factory)
    assert hand_built.digests["core"] == built.digests["core"]
    assert hand_built.digests["facet"] == built.digests["facet"]


@pytest.mark.parametrize(
    "design_factory", [cabinet_design, harness_with_board_design], ids=["cabinet", "harness_board"]
)
def test_layout_digest_matches_between_the_two_constructions_this_run(design_factory):
    """Not pinned as a constant (WP17 moves it): only compared within this run."""
    hand_built = _by_hand(design_factory)
    built = _by_build(design_factory)
    assert hand_built.digests["layout"] == built.digests["layout"]


def test_the_comparison_can_fail():
    """Can-fail proof: a build that skips `number` gives a different `facet` digest.

    `cabinet_design` tags every item explicitly, so `number` has nothing to do there; this
    uses an unnamed item instead, whose assigned designation (a `facet.assigned_designation`
    record) only `number` writes.
    """
    parts = fransys_parts.load("demo_parts")
    design = Design(parts)
    c1 = design.location("C1", "Demo cabinet")
    design.item("DEMO-MCB-C6", name="unnumbered", at=c1)

    complete = freeze(merge(parts, design.draft()))
    complete, _ = allocate_plc(complete)
    complete, _ = number(complete)

    incomplete = freeze(merge(parts, design.draft()))
    incomplete, _ = allocate_plc(incomplete)

    assert complete.digests["facet"] != incomplete.digests["facet"]
