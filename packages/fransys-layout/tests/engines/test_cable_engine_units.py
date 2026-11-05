"""The cable engine in a nested unit's document: the blank end.

Shape of `tests/test_nested_unit_lists.py::_nested_strip_model`: unit `outer` holds the plug -P9
and the nested unit `inner`; `inner`'s own cable `w` has one core from -X5:2 (inside `inner`) to
"""

from functools import cache
from typing import Any

import fransys_parts
from cable_checks import block_of
from fransys_author.design import Design
from library_records import freeze

from electrical_symbols import LIBRARY
from fransys_layout import lay_out_cables
from fransys_layout.geometry import WIRING_GRID
from fransys_model.derive import unit_release
from fransys_model.derive.cable_drawing import block_cables
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import merge
from fransys_model.vocab.tables import units as units_table

_PROJECT: dict[str, Any] = {
    "title": "Pump station",
    "number": "P-1001",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


@cache
def _built():
    """(numbered model, layout, `inner`, `outer` unit ids, strip -X5, plug -P9, cable w ids)."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    outer = d.scope("pump1", at=er).unit("outer", revision=1, interface="1")
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    cab = outer.location("C1", "Cabinet")
    outer_grp = outer.group("OUT", "Outer")
    p9 = outer.item("DEMO-CONN-2P", tag="P9", at=cab, group=outer_grp)
    inner = outer.scope("io", at=cab).unit("inner", revision=1, interface="1")
    inner.revision(1, date="2026-01-01", text="First release", created="XX")
    inner_grp = inner.group("IN", "Inner")
    strip = inner.strip("X5", at=cab)
    terminals = [strip.terminal("DEMO-TB-2.5", group=inner_grp) for _ in range(2)]
    cable = inner.cable("DEMO-CBL-4G1.5", name="w", at=cab)
    cable.core(1, terminals[1].inner, p9["2"])
    model, _ = number_pass(freeze(merge(parts, d.draft())))
    layout = lay_out_cables(model, LIBRARY)
    return model, layout, _unit(model, "inner"), _unit(model, "outer"), strip.id, p9.id, cable.id


def _unit(model, name):
    return next(uid for uid in units_table(model) if unit_release(model, uid).name == name)


def test_inner_reading_has_the_strip_on_top_and_the_outside_plug_blank_below():
    """In `inner`'s reading -X5 stands in TOP, -P9 in BOTTOM with BLANK.

    Positive: the block exists. Probe: the any-unit key in place of the reading's subtree.
    """
    _model, layout, inner, _outer, strip, p9, cable = _built()
    block = block_of(layout, cable, inner)
    assert block is not None
    ends = {e.item: e for e in block.ends}
    assert ends[strip].top
    assert not ends[p9].top
    assert ends[p9].blank
    assert not ends[strip].blank


def test_blank_end_draws_only_a_one_grid_stub_and_no_box():
    """The blank end has height 0 and its wire point is 8 G below the box.

    The stub flag is true on the core's end at -P9 only. Probe: draw the blank end's box.
    """
    model, layout, inner, _outer, strip, p9, cable = _built()
    block = block_of(layout, cable, inner)
    assert block is not None
    (placed,) = block.boxes
    box = placed.box
    ends = {e.item: e for e in block.ends}
    assert ends[p9].height == 0
    assert ends[strip].height > 0
    (wire,) = block.wires
    core = block_cables(model, cable, inner)[0].cores[0]
    p9_ports = {cell.port for cell in ends[p9].cells}
    a_at_p9 = core.end_a in p9_ports
    stub = wire.run_a if a_at_p9 else wire.run_b
    assert sorted(p.y for p in stub) == [box.y + box.height, box.y + box.height + WIRING_GRID]


def test_no_end_is_blank_in_the_absolute_reading():
    """Blank only in a nested unit's document; the absolute block exists and has no blank.

    Probe: blank every end outside the reading's unit whatever the unit's nesting.
    """
    _model, layout, _inner, _outer, strip, p9, cable = _built()
    absolute = block_of(layout, cable)
    assert absolute is not None
    assert {e.item for e in absolute.ends} >= {strip, p9}
    assert not any(e.blank for e in absolute.ends)
