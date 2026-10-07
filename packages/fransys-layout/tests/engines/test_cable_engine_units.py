"""The cable engine in a nested unit's document: the blank end (CT5 CD5, CD11; acceptance 9, 12).

Shape of `tests/test_nested_unit_lists.py::_nested_strip_model`: unit `outer` holds the plug -P9
and the nested unit `inner`; `inner`'s own cable `w` has one core from -X5:2 (inside `inner`) to
-P9:2 (outside it).
"""

from functools import cache
from typing import Any

import fransys_author
import fransys_parts

from fransys_layout import lay_out_cables
from fransys_layout.geometry import WIRING_GRID
from fransys_model.derive import unit_release
from fransys_model.derive.cable_drawing import block_cables
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import freeze, merge
from fransys_model.layout import (
    BlockRow,
    CableBlock,
    CableBox,
    CoreWire,
    EndBox,
    EndStyle,
    layout_of,
)
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
    """(laid-out model, `inner` unit id, `outer` unit id, strip -X5 id, plug -P9 id, cable w id)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
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
    model, _findings = lay_out_cables(model)
    return model, _unit(model, "inner"), _unit(model, "outer"), strip.id, p9.id, cable.id


def _unit(model, name):
    return next(uid for uid in units_table(model) if unit_release(model, uid).name == name)


def _block(model, unit, cable):
    """The CableBlock of `cable` in `unit`'s reading (`None` for the absolute one), or None."""
    return next(
        (b for b in layout_of(model, CableBlock).values() if b.unit == unit and b.subject == cable),
        None,
    )


def _children(model, block, record_type):
    return [r for r in layout_of(model, record_type).values() if r.block == block.id]


def test_inner_reading_has_the_strip_on_top_and_the_outside_plug_blank_below():
    """Acceptance 12 (CD5): in `inner`'s reading -X5 stands in TOP, -P9 in BOTTOM with BLANK.

    Positive: the block exists. Probe: CD4's any-unit key in place of the reading's subtree.
    """
    model, inner, _outer, strip, p9, cable = _built()
    block = _block(model, inner, cable)
    assert block is not None
    ends = {e.item: e for e in _children(model, block, EndBox)}
    assert ends[strip].row is BlockRow.TOP
    assert ends[p9].row is BlockRow.BOTTOM
    assert ends[p9].style is EndStyle.BLANK
    assert ends[strip].style is not EndStyle.BLANK


def test_blank_end_draws_only_a_one_grid_stub_and_no_box():
    """Acceptance 9 (CD11): the blank end has height 0 and its wire point is 8 G below the box.

    The stub flag is true on the core's end at -P9 only. Probe: draw the blank end's box.
    """
    model, inner, _outer, strip, p9, cable = _built()
    block = _block(model, inner, cable)
    assert block is not None
    (box,) = _children(model, block, CableBox)
    ends = {e.item: e for e in _children(model, block, EndBox)}
    assert ends[p9].height == 0
    assert ends[strip].height > 0
    (wire,) = _children(model, block, CoreWire)
    core = block_cables(model, cable, inner)[0].cores[0]
    p9_ports = {pin.port for pin in ends[p9].pins}
    a_at_p9 = core.end_a in p9_ports
    stubs = (wire.stub_a, wire.stub_b)
    assert stubs == ((True, False) if a_at_p9 else (False, True))
    stub = wire.run_a if a_at_p9 else wire.run_b
    assert sorted(p.y for p in stub) == [box.y + box.height, box.y + box.height + WIRING_GRID]


def test_no_end_is_blank_in_the_absolute_reading():
    """CD11: blank only in a nested unit's document; the absolute block exists and has no blank.

    Probe: blank every end outside the reading's unit whatever the unit's nesting.
    """
    model, _inner, _outer, strip, p9, cable = _built()
    absolute = _block(model, None, cable)
    assert absolute is not None
    assert {e.item for e in _children(model, absolute, EndBox)} >= {strip, p9}
    assert all(e.style is not EndStyle.BLANK for e in _children(model, absolute, EndBox))
    assert not any(w.stub_a or w.stub_b for w in _children(model, absolute, CoreWire))
