"""The cable pass leaves every schematic page SVG as it was (cable-drawings spec, acceptance 10).

Standing test (designer ruling after the PNG read): pages equal with the cable pass on and
off, and in either pass order. The fixture has a top-level cable, so a block really is drawn.
"""

import sys
from pathlib import Path

import fransys_parts
import fransys_render
import pytest
from _model_build_cover import layout_trigger_document

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    # `demo_designs` is a plain script module at the repo root (see `test_facade_swap.py`).
    sys.path.insert(0, str(_ROOT))

from demo_designs import harness_with_board_design  # noqa: E402 - after the sys.path insert that demo_designs needs

from fransys_layout import lay_out_cables  # noqa: E402 - after the sys.path insert that demo_designs needs
from fransys_layout.engines.schematic import lay_out_schematic  # noqa: E402 - after the sys.path insert that demo_designs needs
from fransys_model.derive import allocate_plc, number  # noqa: E402 - after the sys.path insert that demo_designs needs
from fransys_model.kernel import freeze, merge  # noqa: E402 - after the sys.path insert that demo_designs needs


@pytest.fixture(scope="module")
def numbered():
    """The cable-bearing fixture, frozen, allocated and numbered, with no layout yet."""
    parts = fransys_parts.load("demo_parts")
    design = harness_with_board_design(parts)
    model = freeze(merge(parts, design.draft(), layout_trigger_document()))
    model, _ = allocate_plc(model)
    model, _ = number(model)
    return model


@pytest.fixture(scope="module")
def schematic_first(numbered):
    """Schematic layout, then the cable pass: the pipeline's own order."""
    laid_out, _ = lay_out_schematic(numbered)
    return laid_out, lay_out_cables(laid_out)[0]


def test_pages_are_equal_with_the_cable_pass_on_and_off(schematic_first):
    off, on = schematic_first
    assert len(fransys_render.pages(off)) > 0
    assert len(fransys_render.cable_blocks(on)) > 0
    assert fransys_render.pages(on) == fransys_render.pages(off)


def test_pages_are_equal_when_the_cable_pass_runs_first(numbered, schematic_first):
    """The passes touch disjoint record kinds, so their order cannot move a page."""
    cables_first, _ = lay_out_schematic(lay_out_cables(numbered)[0])
    assert len(fransys_render.cable_blocks(cables_first)) > 0
    assert fransys_render.pages(cables_first) == fransys_render.pages(schematic_first[0])
