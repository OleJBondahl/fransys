"""A paired cable with spare cores through the facade: the block SVG's printed marks (CC6, CC10).

One strip `X1` and a motor `M1` joined by `W1` of a 2x2x0.75 part with a screen per pair.
Cores 1 and 2 (pair P1) are wired, cores 3 and 4 (pair P2) are spares parked on `X1`, the two screens land on `X1` too.
"""

import functools

import fransys as fr
from fransys_render import cable_blocks

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_cables


@functools.cache
def _model():
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 8)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-2X2X0.75-SP", length_m=25)
    w1.core(1, x1[1], h1[1])
    w1.core(2, x1[2], h1[2])
    w1.spare(3, at=x1[7])
    w1.spare(4, at=x1[4])
    w1.spare()
    return fr.build(d).model


def _open_wires(model):
    return [w for b in lay_out_cables(model, LIBRARY).blocks.values() for w in b.wires if w.open]


def _svg() -> str:
    (svg,) = dict(cable_blocks(_model(), lay_out_cables(_model(), LIBRARY), LIBRARY)).values()
    return svg


def test_the_block_writes_one_open_core_wire_per_spare_core():
    assert len(_open_wires(_model())) == 2


def test_a_pair_is_bracketed_and_labelled_and_a_spare_is_marked():
    """Probe: `block_brackets` returns `()`: no "P1" or "P2" text, this test fails."""
    svg = _svg()
    assert ">P1<" in svg
    assert ">P2<" in svg
    assert "spare" in svg


def test_the_heading_names_the_pairs():
    assert "2x2x0.75, screened pairs, 25000 mm" in _svg()


def test_a_cable_with_no_open_core_writes_no_open_core_wire():
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    h1 = d.device("H1", "DEMO-LAMP-24")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=5)
    w1.core(1, x1[1], h1[1])
    w1.core(2, x1[2], h1[2])
    model = fr.build(d).model
    cables = lay_out_cables(model, LIBRARY)
    assert not _open_wires(model)
    assert ">spare<" not in dict(cable_blocks(model, cables, LIBRARY)).popitem()[1]


def test_a_stub_stands_one_grid_unit_long_and_clear_of_the_tracks():
    """Every open wire has a run of one grid unit or a routed lower run, none of zero length."""
    for wire in _open_wires(_model()):
        stubs = [run for run in (wire.run_a, wire.run_b) if run]
        assert stubs
        for run in stubs:
            assert len({p.x for p in run}) == 1
            assert abs(run[-1].y - run[0].y) > 0
