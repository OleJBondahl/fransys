"""HARNESS_WIRE_MISMATCH: a drawn block that equals the harness-wire rows passes; a dropped, an extra or a wrong wire is an ERROR (el-0122)."""

from dataclasses import replace

import cable_models as cm
import pytest
from fransys_el import block_wire_findings

from fransys_layout import CableLayout
from fransys_model.kernel import Finding, Severity


def _first(built):
    key, block = next(iter(built.layout.blocks.items()))
    return key, block


def _with(built, block_edit) -> tuple[Finding, ...]:
    """The findings of `built` after `block_edit` changed the first block."""
    key, block = _first(built)
    layout = CableLayout(blocks=frozendict({**built.layout.blocks, key: block_edit(block)}))
    return block_wire_findings(built.frozen, layout)


@pytest.mark.parametrize("name", sorted(cm.MODELS))
def test_a_block_equal_to_its_rows_passes(name: str) -> None:
    built = cm.MODELS[name]()
    assert built.layout.blocks
    assert block_wire_findings(built.frozen, built.layout) == ()


def test_a_dropped_wire_is_an_error() -> None:
    found = _with(cm.flat(), lambda b: replace(b, wires=b.wires[1:]))
    assert [f.code for f in found] == ["HARNESS_WIRE_MISMATCH"]
    assert found[0].severity is Severity.ERROR
    assert "drawn 0 times" in found[0].message


def test_an_extra_wire_is_an_error() -> None:
    first = _first(cm.flat())[1].wires[0]
    found = _with(cm.flat(), lambda b: replace(b, wires=(*b.wires, first)))
    assert [f.code for f in found] == ["HARNESS_WIRE_MISMATCH"]
    assert "drawn 2 times" in found[0].message


def test_a_wire_with_no_row_is_an_error() -> None:
    other = next(w for b in cm.unit().layout.blocks.values() for w in b.wires)
    found = _with(cm.flat(), lambda b: replace(b, wires=(*b.wires, other)))
    assert [f.code for f in found] == ["HARNESS_WIRE_MISMATCH"]
    assert "no harness-wire row has" in found[0].message


def test_a_wire_off_its_pin_is_an_error() -> None:
    def shift(block):
        wire = block.wires[0]
        moved = replace(wire, run_a=tuple(replace(p, x=p.x + 1) for p in wire.run_a), run_b=tuple(replace(p, x=p.x + 1) for p in wire.run_b))
        return replace(block, wires=(moved, *block.wires[1:]))

    found = _with(cm.flat(), shift)
    assert [f.code for f in found] == ["HARNESS_WIRE_MISMATCH"]
    assert "ends none" in found[0].message


def test_a_wire_in_the_wrong_cable_is_an_error() -> None:
    built = cm.harness_fan()
    block = next(b for b in built.layout.blocks.values() if len(b.boxes) > 1)
    key = next(k for k, b in built.layout.blocks.items() if b is block)
    swapped = (replace(block.boxes[0], cable=block.boxes[1].cable), replace(block.boxes[1], cable=block.boxes[0].cable), *block.boxes[2:])
    layout = CableLayout(blocks=frozendict({**built.layout.blocks, key: replace(block, boxes=swapped)}))
    found = block_wire_findings(built.frozen, layout)
    assert found
    assert {f.code for f in found} == {"HARNESS_WIRE_MISMATCH"}


def test_a_dropped_pin_cell_is_an_error() -> None:
    def drop(block):
        end = next(e for e in block.ends if not e.blank and e.cells)
        return replace(block, ends=tuple(replace(e, cells=e.cells[1:]) if e is end else e for e in block.ends))

    found = _with(cm.flat(), drop)
    assert found
    assert {f.code for f in found} == {"HARNESS_WIRE_MISMATCH"}
    assert all(f.severity is Severity.ERROR for f in found)
