"""CONVENTIONS-V06 V3 (owner 2026-10-02): at an item box's pin a rail symbol faces away from it.

A two-pin lamp keeps its 24 V pin above and its 0 V pin below, so the bar stands above and the
ground hangs below (R0). A PLC input module has both of its power pins on its top side: its 24 V
bar and its 0 V ground both stand above the box, the ground turned up (R180).
"""

import fransys as fr
import fransys_author

from fransys_model.layout import Orientation, PowerSymbol, layout_of

_RAILS = {"24V": ("24", None), "0V": ("0", None)}


def _records(tmp_path, part: str, pins: tuple[str, str]) -> list[PowerSymbol]:
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.supply("S", current="dc", rails=_RAILS)
    cab = d.location("CAB", "Cabinet")
    g = d.group("G", "Group")
    wire = d.wiring(colour="BU", gauge="0.5")
    boxes = [d.item(part, tag=f"K{i}", at=cab, group=g) for i in range(2)]
    for pin, strip_tag, rail in zip(pins, ("X1", "X2"), ("24V", "0V"), strict=True):
        strip = d.strip(strip_tag, at=cab)
        terminals = [strip.terminal("DEMO-TB-2.5", f"T{i}", group=g) for i in range(2)]
        for box, terminal in zip(boxes, terminals, strict=True):
            wire(box[pin], terminal.outer)
        d.link(terminals[0].inner, terminals[1].inner, kind="rail")
        d.net(rail, *(t.outer for t in terminals), cls="power", potential=rail)
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    model = fr.build(parts, d.draft(), doc).model
    return list(layout_of(model, PowerSymbol).values())


def _symbols(tmp_path, part: str, pins: tuple[str, str]) -> dict[str, set[Orientation]]:
    found: dict[str, set[Orientation]] = {}
    for one in _records(tmp_path, part, pins):
        found.setdefault(one.symbol, set()).add(one.orientation)
    return found


def test_a_lamp_has_the_bar_above_its_top_pin_and_the_ground_below_its_bottom_pin(tmp_path) -> None:
    found = _symbols(tmp_path, "DEMO-LAMP-24", ("1", "2"))
    assert found == {"power-supply": {Orientation.R0}, "ground": {Orientation.R0}}


def test_in_a_column_the_bar_stands_above_its_pin_and_the_ground_below_its_pin(tmp_path) -> None:
    for one in _records(tmp_path, "DEMO-LAMP-24", ("1", "2")):
        above = one.y < one.pin_y
        assert above == (one.symbol == "power-supply")


def test_a_ground_pin_on_the_top_side_of_a_box_draws_its_ground_pointing_up(tmp_path) -> None:
    found = _symbols(tmp_path, "DEMO-PLC-DI-4P", ("24V", "0V"))
    assert found == {"power-supply": {Orientation.R0}, "ground": {Orientation.R180}}
