"""External items, worked example (external-items spec, "Steps and acceptance" steps 1 and 3).

The units spec's `demo_system` (two pump cabinets, four top-level cables, one shared top-level
switch `K1`, `DEMO-SWITCH-2P`, wired by cables `WM1S`/`WM2S` to the cabinets' field terminals)
with the switch set `external=True`. The unit-documents fixture has no upstream strip; a scratch
external strip `X0` on demo parts stands in: `X0` (two terminals) is wired by the non-external
cable `WX0` to the switch's two contact ports. The cabinets' own strip `X2`, motors `M1`/`M2`
and cables `WM1`/`WM2` are the non-external controls.

The design is built here from the helpers of `test_units_worked_example.py` (imported by name,
the same way `test_write_unit_worked_example.py` does), with its own `Design` because
`_system_design` builds the switch without the flag.
"""

import sys
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import _COVER

# `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fransys_render
from test_units_worked_example import (
    _PROJECT,
    _wire_field_to_motor,
    _wire_field_to_switch,
    pump_cabinet,
)

from fransys_model.derive import bom_lines, external
from fransys_model.derive.cable_drawing import cable_block_key, end_label
from fransys_model.derive.designation import printed_designation
from fransys_model.kernel import dumps, loads
from fransys_model.layout import CableBlock, EndBox, EndStyle, layout_of
from fransys_model.vocab import DocumentPreset
from fransys_model.vocab.tables import items as items_of

BY_OTHERS = "by others"
_DASH_ATTR = ' stroke-dasharray="'  # an element attribute, not the stylesheet's rule


def _build(*, x0_external=True, switch_external=True):
    """`demo_system` with an external switch `K1` and a scratch strip `X0` wired to it, plus a
    `SYSTEM` document (CD10: "by others" is drawn on the cable blocks, a dashed end box and a
    label, Y3)."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    field1, _ = pump_cabinet(d.scope("pump1", at=er), name="C1")
    field2, _ = pump_cabinet(d.scope("pump2", at=er), name="C2")
    fld = d.location("FLD", "Field")
    fld_grp = d.group("FLD", "Field wiring")
    _wire_field_to_motor(d, field1, fld=fld, grp=fld_grp, motor_tag="M1")
    _wire_field_to_motor(d, field2, fld=fld, grp=fld_grp, motor_tag="M2")
    switch = d.item("DEMO-SWITCH-2P", tag="K1", at=fld, group=fld_grp, external=switch_external)
    _wire_field_to_switch(d, field1[1], switch.fn("x1")["1"], cable_tag="WM1S")
    _wire_field_to_switch(d, field2[1], switch.fn("x1")["2"], cable_tag="WM2S")
    x0 = d.strip("X0", at=fld, external=x0_external)
    x0_terminals = [x0.terminal("DEMO-TB-2.5", group=fld_grp) for _ in range(2)]
    cable = d.cable("DEMO-CBL-4G1.5", tag="WX0", length_mm=15000)
    cable.core(1, x0_terminals[0].outer, switch.fn("sw")["A"])
    cable.core(2, x0_terminals[1].outer, switch.fn("sw")["B"])
    system_doc = fr.document(DocumentPreset.SYSTEM, None, cover=_COVER)
    return fr.build(parts, d.draft(), system_doc).model


def _by_key(model, key):
    """The one item whose key is `(key,)`; a designation is not unique (the cabinets' relays
    are numbered `K1` too)."""
    matches = [i.id for i in items_of(model).values() if i.key == (key,)]
    assert len(matches) == 1, key
    return matches[0]


def _children(model, parent):
    return [i.id for i in items_of(model).values() if i.parent == parent]


def _bom_designations(model):
    lines = bom_lines(model)
    assert len(lines) > 0
    return lines, {d for line in lines for d in line.designations}


def _fixture(model):
    """The items the tests name: X0, its terminals, the switch, and the control strip X2."""
    x0 = _by_key(model, "X0")
    switch = _by_key(model, "K1")
    x0_terminals = _children(model, x0)
    x2 = next(i.id for i in items_of(model).values() if i.key == ("pump1", "X2"))
    x2_terminals = _children(model, x2)
    assert len(x0_terminals) == 2
    assert len(x2_terminals) == 2
    return x0, x0_terminals, switch, x2_terminals


@pytest.fixture(scope="module")
def default_model():
    return _build()


@pytest.fixture(scope="module")
def unflagged_model():
    return _build(x0_external=False, switch_external=False)


# -- 1. the BOM ---------------------------------------------------------------------------


def test_the_bom_has_neither_the_external_strips_terminals_nor_the_switch(default_model):
    model = default_model
    _x0, x0_terminals, switch, _x2_terminals = _fixture(model)
    _lines, designations = _bom_designations(model)
    for terminal in x0_terminals:
        assert printed_designation(model, terminal) not in designations
    assert printed_designation(model, switch) not in designations
    # the switch's part has no other instance, so its whole line is gone
    assert "DEMO-SWITCH-2P" not in {line.mpn for line in bom_lines(model)}


def test_the_cable_between_them_keeps_its_bom_line_and_a_control_terminal_stays(default_model):
    model = default_model
    _x0, _x0_terminals, _switch, x2_terminals = _fixture(model)
    lines, designations = _bom_designations(model)
    cable = _by_key(model, "WX0")
    cable_lines = [line for line in lines if line.mpn == "DEMO-CBL-4G1.5"]
    assert len(cable_lines) == 1
    assert printed_designation(model, cable) in cable_lines[0].designations
    # the cables to the external switch are external-end cables, not external cables
    assert printed_designation(model, _by_key(model, "WM1S")) in cable_lines[0].designations
    for terminal in x2_terminals:
        assert printed_designation(model, terminal) in designations


def test_the_same_design_without_the_flags_puts_all_of_them_back_in_the_bom(unflagged_model):
    """Can-fail: the flags, not the design, take the strip's terminals and the switch out."""
    model = unflagged_model
    _x0, x0_terminals, switch, _x2_terminals = _fixture(model)
    _lines, designations = _bom_designations(model)
    for terminal in x0_terminals:
        assert printed_designation(model, terminal) in designations
    assert printed_designation(model, switch) in designations


# -- 2. derive.external -------------------------------------------------------------------


def test_external_is_true_for_the_strip_its_terminals_and_the_switch_only(default_model):
    model = default_model
    x0, x0_terminals, switch, x2_terminals = _fixture(model)
    assert len(x0_terminals) > 0
    assert external(model, x0)
    assert all(external(model, terminal) for terminal in x0_terminals)
    assert external(model, switch)
    assert len(x2_terminals) > 0
    assert not any(external(model, terminal) for terminal in x2_terminals)
    assert not external(model, _by_key(model, "WX0"))
    assert not external(model, _by_key(model, "M1"))
    # the terminals carry no flag of their own: it is the parent-chain walk that finds them
    assert not any(items_of(model)[terminal].external for terminal in x0_terminals)


# -- 3. round trip ------------------------------------------------------------------------


def test_the_flag_survives_a_dumps_loads_round_trip(default_model):
    model = default_model
    x0, x0_terminals, switch, x2_terminals = _fixture(model)
    loaded = loads(dumps(default_model))
    assert items_of(loaded)[switch].external is True
    assert items_of(loaded)[x0].external is True
    assert len(x0_terminals) > 0
    assert all(external(loaded, terminal) for terminal in x0_terminals)
    assert not any(external(loaded, terminal) for terminal in x2_terminals)
    assert not items_of(loaded)[_by_key(loaded, "M1")].external


def test_a_round_trip_of_the_unflagged_design_has_no_external_item(unflagged_model):
    """Can-fail: the round-trip assertions above are about the flag, not about every item."""
    loaded = loads(dumps(unflagged_model))
    assert len(items_of(loaded)) > 0
    assert not any(item.external for item in items_of(loaded).values())


# -- 4. cable blocks (CD10): the dashed end box and the "by others" label ----------------


def _end_boxes(model, cable_key):
    """The end boxes of `cable_key`'s block in the absolute reading, by end item."""
    cable = _by_key(model, cable_key)
    (block,) = [
        b.id for b in layout_of(model, CableBlock).values() if b.unit is None and b.subject == cable
    ]
    return {e.item: e for e in layout_of(model, EndBox).values() if e.block == block}


def _block_svg(model, cable_key):
    """The SVG `fransys_render` draws for `cable_key`'s block in the absolute reading."""
    return fransys_render.cable_blocks(model)[cable_block_key(None, _by_key(model, cable_key))]


def _dashed(model, cable_key):
    return {i for i, e in _end_boxes(model, cable_key).items() if e.style is EndStyle.DASHED}


def _by_others(model, item):
    return end_label(model, item, None).endswith(f" ({BY_OTHERS})")


def test_the_block_of_a_cable_to_the_switch_draws_the_switch_dashed_only(default_model):
    """CD10 (Y3): `WM1S` is not external itself, but its end at the switch `K1` is -- `K1`'s end
    box is dashed and labelled "by others", the cabinet end is solid."""
    model = default_model
    boxes = _end_boxes(model, "WM1S")
    switch = _by_key(model, "K1")
    assert switch in boxes
    assert boxes[switch].style is EndStyle.DASHED
    assert _by_others(model, switch)
    (other,) = set(boxes) - {switch}
    assert boxes[other].style is EndStyle.SOLID
    assert not _by_others(model, other)
    svg = _block_svg(model, "WM1S")
    assert svg.count(f" ({BY_OTHERS})") == 1
    assert _DASH_ATTR in svg


def test_the_block_svg_of_a_cable_with_no_external_end_prints_no_by_others(default_model):
    """Can-fail partner of the SVG checks above: the printed block, not only its records."""
    svg = _block_svg(default_model, "WM1")
    assert "<svg" in svg
    assert BY_OTHERS not in svg
    assert _DASH_ATTR not in svg


def test_the_block_of_the_cable_from_the_external_strip_draws_both_ends_dashed(default_model):
    """`WX0` is not external itself, but both its ends are: the `X0` strip and the switch `K1`."""
    model = default_model
    boxes = _end_boxes(model, "WX0")
    assert set(boxes) == {_by_key(model, "X0"), _by_key(model, "K1")}
    assert _dashed(model, "WX0") == set(boxes)
    assert all(_by_others(model, item) for item in boxes)


def test_the_block_of_a_cable_with_no_external_end_draws_no_dashed_end(default_model):
    assert len(_end_boxes(default_model, "WM1")) > 0  # the cable's own block is there
    assert _dashed(default_model, "WM1") == set()


def test_the_block_of_the_unflagged_design_draws_no_dashed_end_on_the_switch_cable(
    unflagged_model,
):
    """Can-fail: without the flag on the switch, the block of `WM1S` has no dashed end."""
    assert len(_end_boxes(unflagged_model, "WM1S")) > 0
    assert _dashed(unflagged_model, "WM1S") == set()
