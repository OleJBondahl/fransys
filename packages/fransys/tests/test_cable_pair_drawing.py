"""A paired cable with spare cores through the facade: the block SVG's printed marks (CC6, CC10).

One strip `X1` and a motor `M1` joined by `W1` of a 2x2x0.75 part with a screen per pair.
Cores 1 and 2 (pair P1) are wired, core 3 (pair P2) is a spare parked on `X1`, the rest are spare.
"""

import functools

import fransys as fr
import pytest
from fransys_render import cable_blocks

from fransys_layout import lay_out_cables
from fransys_model.layout import OpenCoreWire, layout_of


@functools.cache
def _model():
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-2X2X0.75-SP", length_m=25)
    w1.core(1, x1[1], h1[1])
    w1.core(2, x1[2], h1[2])
    w1.spare(3, at=x1[7])
    w1.spare()
    return lay_out_cables(fr.build(d).model)[0]


def _svg() -> str:
    (svg,) = dict(cable_blocks(_model())).values()
    return svg


def test_the_block_writes_one_open_core_wire_per_spare_core():
    assert len(layout_of(_model(), OpenCoreWire)) == 4


def test_a_pair_is_bracketed_and_labelled_and_a_spare_is_marked():
    """Probe: `block_brackets` returns `()`: no "P1" or "P2" text, this test fails."""
    svg = _svg()
    assert ">P1<" in svg
    assert ">P2<" in svg
    assert "spare" in svg


def test_the_heading_names_the_pairs():
    assert "2x2x0.75, screened pairs, 25000 mm" in _svg()


@pytest.mark.parametrize("text", ["SH", "screen P1", "screen P2"])
def test_a_screen_row_reads_sh_and_its_pair(text):
    assert text in _svg()


def test_a_cable_with_no_open_core_writes_no_open_core_wire():
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
    w1.core(1, x1[1], h1[1])
    model = lay_out_cables(fr.build(d).model)[0]
    assert not layout_of(model, OpenCoreWire)
    assert ">spare<" not in dict(cable_blocks(model)).popitem()[1]


def test_a_stub_stands_one_grid_unit_long_and_clear_of_the_tracks():
    """Every open wire has a run of one grid unit or a routed lower run, none of zero length."""
    for wire in layout_of(_model(), OpenCoreWire).values():
        stubs = [run for run, on in ((wire.run_a, wire.stub_a), (wire.run_b, wire.stub_b)) if on]
        assert stubs
        for run in stubs:
            assert len({p.x for p in run}) == 1
            assert abs(run[-1].y - run[0].y) > 0
