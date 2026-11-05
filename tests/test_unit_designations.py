"""Short designations (owner ruling, generalising I4 R2): on a page of a unit's own drawing (known: DANGLING_WIRE_END KI-414)
set a component's tag prints its item designation only, below the unit's sole root ("-K1",
"-X2"); the page already states the location, unit and groups. The top-level set prints the
"""

import importlib.util
from pathlib import Path
from typing import Any

from _drawn_pages import drawn_pages
from _model_build_cover import printed
from fransys_author.design import Design

from fransys_model.derive import unit_release
from fransys_model.layout import DrawingSet, Page, layout_of
from fransys_model.vocab.tables import units

# the worked example's own builder, loaded by path (root tests are not a package)
_SPEC = importlib.util.spec_from_file_location("units_worked_example", Path(__file__).with_name("test_units_worked_example.py"))
assert _SPEC is not None
assert _SPEC.loader is not None
_EXAMPLE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_EXAMPLE)
_build_system = _EXAMPLE._build_system


def _tag_texts_by_set():
    model = _build_system()[0].model
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    found: dict[Any, Any] = {}
    for page, drawing in drawn_pages(model).items():
        drawing_set = sets[pages[page].drawing_set]
        name = unit_release(model, drawing_set.unit).name if drawing_set.unit else None
        found.setdefault(name, set()).update(t.text for t in drawing.texts if t.kind == "TAG")
    return found


def test_the_board_units_own_set_prints_item_designations_below_its_root() -> None:
    """The board `A1` is the unit's sole root and the page states its aspects: "-K1", not
    "=BRD-K1" or "=BRD+ER+C1-A1-K1". `X1` is one connector box whose designation line is
    the short form too, less the root: "-X1". `X1` is at a harness line's end (layout-0155)."""
    assert _tag_texts_by_set()["demo-io-board"] == {"-K1"}
    model = _build_system()[0].model
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    designations = []
    for page, drawing in drawn_pages(model).items():
        unit = sets[pages[page].drawing_set].unit
        if unit is None or unit_release(model, unit).name != "demo-io-board":
            continue
        for box in (s for s in drawing.symbols if s.key == "generic-box"):
            assert len(box.texts) == 1  # a unit interface box has no cells
            designations.extend(cell for row in box.texts for cell in row if cell == "-X1")
    assert designations == ["-X1", "-X1"]  # one box in each of the two board sets


def test_a_cabinets_own_set_and_the_top_level_print_no_aspect() -> None:
    """A cabinet's own set prints "-X2", no "+C1" and no "+ER"; the top-level set prints the
    item designation only too, "-M1", no "+ER+C1" and no "=FLD+FLD"
    (layout-0066: the owner's rule has no top-level exception). Its "-X2" box draws no wire, so
    it is not drawn (layout-0214)."""
    texts = _tag_texts_by_set()
    cabinet = texts["demo-pump-cabinet"]
    assert "-X2" in cabinet
    assert not any(text.startswith(("+", "=")) or "+C1" in text for text in cabinet)
    assert "-X2" not in texts[None]
    assert "-M1" in texts[None]
    assert not any("+" in text or "=" in text for text in texts[None])


def test_a_units_own_bom_and_terminal_rows_leave_out_its_root() -> None:
    """L4: every export of a unit's own document follows R2, so the board unit's BOM names
    its relay "K1", as its drawing does, not "A1-K1"; the whole model's BOM keeps "A1-K1".
    Can-fail: drop `unit=` from `bom_lines`' designations and the first assertion fails."""
    from fransys_model.derive import bom_lines

    model = _build_system()[0].model
    board = next(u.id for u in units(model).values() if unit_release(model, u.id).name == "demo-io-board")
    own = {d for line in bom_lines(model, scope=board) for d in line.designations}
    everything = {d for line in bom_lines(model) for d in line.designations}
    assert "-K1" in own
    assert not any(d.startswith("-U1-") for d in own)
    assert "-U1-K1" in everything


def test_a_top_level_cable_in_a_units_location_leaves_that_location_own() -> None:
    """W3 (refinement of R2): a cable crosses locations by nature, so a top-level
    cable placed at the cabinet's `+C1` (wired to the cabinet's boundary connector)
    never un-owns `+C1`: the cabinet's own set still prints "+C1".
    Can-fail, checked by hand: count cable items in `own_nodes` again and "C1"
    leaves the cabinet's own nodes."""
    import fransys as fr
    import fransys_parts

    from fransys_model.derive.unit_nodes import own_nodes
    from fransys_model.vocab.tables import aspect_nodes

    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_EXAMPLE._PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    x1 = u.item("DEMO-CONN-2P", tag="X1", at=c1, group=u.group("FLD", "Field wiring"))
    u.boundary(x1)
    fld, field = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
    p2 = d.item("DEMO-CONN-2P", tag="P2", at=fld, group=field)
    cable = d.cable("DEMO-CBL-4G1.5", name="w3c", at=c1)
    cable.core(1, x1["1"], p2["1"])
    cable.core(2, x1["2"], p2["2"])
    model = fr.build(parts, *printed(d.draft())).model
    (cabinet,) = units(model)
    assert "C1" in {aspect_nodes(model)[node].label for node in own_nodes(model, cabinet)}
