"""Short designations (owner ruling, generalising I4 R2): on a page of a unit's own drawing
set a component's tag prints its item designation only, below the unit's sole root ("-K1",
"-X2"); the page already states the location, unit and groups. The top-level set prints the
same short form (D12 amended, layout-0066). Probed on the units worked example (two pump
cabinets at +ER, each with one I/O board unit). `own_nodes` (R2) still decides a unit's own
aspects for its exports.

Can-fail, checked by hand: with `unit_tag_text` printing `reference_designation(..., unit=unit)`
again (R2), the board's own set prints "=BRD-K1" and the cabinet's "+C1-X2", and the first two
tests below fail.
"""

import importlib.util
from pathlib import Path

from _model_build_cover import system_document

from fransys_model.derive import unit_release
from fransys_model.derive.drawing_text import label_text
from fransys_model.layout import DrawingSet, Label, LabelKind, Page, layout_of
from fransys_model.vocab.tables import units

# the worked example's own builder, loaded by path (root tests are not a package)
_SPEC = importlib.util.spec_from_file_location(
    "units_worked_example", Path(__file__).with_name("test_units_worked_example.py")
)
assert _SPEC is not None
assert _SPEC.loader is not None
_EXAMPLE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_EXAMPLE)
_build_system = _EXAMPLE._build_system


def _tag_texts_by_set():
    model = _build_system()[0].model
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    found: dict = {}
    for label in layout_of(model, Label).values():
        if label.kind is not LabelKind.TAG:
            continue
        drawing_set = sets[pages[label.page].drawing_set]
        name = unit_release(model, drawing_set.unit).name if drawing_set.unit else None
        found.setdefault(name, set()).add(label_text(model, label))
    return found


def test_the_board_units_own_set_prints_item_designations_below_its_root() -> None:
    """The board `A1` is the unit's sole root and the page states its aspects: "-K1", not
    "=BRD-K1" or "=BRD+ER+C1-A1-K1". Each `X1` pin stands alone in its row and prints its pin
    tag (D2), less the root, and dashed like every port text (decision model-0052): "-X1:1"."""
    assert _tag_texts_by_set()["demo-io-board"] == {"-K1", "-X1:1", "-X1:2"}


def test_a_cabinets_own_set_and_the_top_level_print_no_aspect() -> None:
    """A cabinet's own set prints "-X2", no "+C1" and no "+ER"; the top-level set prints the
    item designation only too, "-X2" and "-M1", no "+ER+C1" and no "=FLD+FLD" (D12 amended,
    layout-0066: the owner's rule has no top-level exception)."""
    texts = _tag_texts_by_set()
    cabinet = texts["demo-pump-cabinet"]
    assert "-X2" in cabinet
    assert not any(text.startswith(("+", "=")) or "+C1" in text for text in cabinet)
    assert "-X2" in texts[None]
    assert "-M1" in texts[None]
    assert not any("+" in text or "=" in text for text in texts[None])


def test_a_units_own_bom_and_terminal_rows_leave_out_its_root() -> None:
    """L4: every export of a unit's own document follows R2, so the board unit's BOM names
    its relay "K1", as its drawing does, not "A1-K1"; the whole model's BOM keeps "A1-K1".
    Can-fail: drop `unit=` from `bom_lines`' designations and the first assertion fails."""
    from fransys_model.derive import bom_lines

    model = _build_system()[0].model
    board = next(
        u.id for u in units(model).values() if unit_release(model, u.id).name == "demo-io-board"
    )
    own = {d for line in bom_lines(model, scope=board) for d in line.designations}
    everything = {d for line in bom_lines(model) for d in line.designations}
    assert "-K1" in own
    assert not any(d.startswith("-U1-") for d in own)
    assert "-U1-K1" in everything


def test_a_top_level_cables_end_plug_in_a_units_location_leaves_that_location_own() -> None:
    """W3 (designer's refinement of R2): a cable crosses locations by nature, so a top-level
    harness whose plug is placed at the cabinet's `+C1` (mated to the cabinet's boundary
    connector) never un-owns `+C1`: the cabinet's own set still prints "+C1".
    Can-fail, checked by hand: count cable and harness items in `own_nodes` again and "C1"
    leaves the cabinet's own nodes."""
    import fransys as fr
    import fransys_author
    import fransys_parts

    from fransys_model.derive.designation import own_nodes
    from fransys_model.vocab.tables import aspect_nodes

    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_EXAMPLE._PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    u.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = u.location("C1", "Pump cabinet")
    x1 = u.item("DEMO-CONN-2P", tag="X1", at=c1, group=u.group("FLD", "Field wiring"))
    u.boundary(x1)
    fld, field = d.location("FLD", "Field"), d.group("FLD", "Field wiring")
    w3 = d.harness(name="w3", tag="W3", at=c1, group=field)
    p1 = d.item("DEMO-CONN-2P", tag="P1", parent=w3, at=c1, group=field)
    p2 = d.item("DEMO-CONN-2P", tag="P2", parent=w3, at=fld, group=field)
    cable = d.cable("DEMO-CBL-4G1.5", name="w3c", parent=w3, at=c1)
    cable.core(1, p1["1"], p2["1"])
    cable.core(2, p1["2"], p2["2"])
    d.mate(p1, x1)
    model = fr.build(parts, d.draft(), system_document()).model
    (cabinet,) = units(model)
    assert "C1" in {aspect_nodes(model)[node].label for node in own_nodes(model, cabinet)}


def test_a_mate_outside_the_unit_reads_as_it_does_outside_it_in_the_units_connector_list() -> None:
    """W3 (designer's ruling), reconciled with model-0054 section 4 in the SYNC2 merge: R2
    applies only to items inside the unit. The board's header X1 mates the cabinet harness plug
    P1, outside the board unit. In the board unit's own connector list X1 reads unit-relative
    ("-X1", not "-U1-X1"). The mate reads as it did in W3 only in the whole model's list: an
    item's `-WH1-P1`, and each pin the mate's port text with its location path below the list's
    context (none without a context: the full `+ER+C1-WH1-P1:1`; the list's own location when
    the mate sits there). The mate's `=`/`+` aspects are no longer printed (W3's first cut):
    a list prints the location path, model-0054 section 4. Amended by model-0056: the nested
    board unit's own list prints no mate, an empty cell (the ids stay); the whole model's list
    still does.
    R2 cannot change an item outside the unit (`_unit_root` leaves it alone), so no mutation of
    that half exists; the test pins the rest. Can-fail (Edit-and-restore): `connector_rows`
    dropping `unit=` from the connector's `printed_designation` fails the "-X1" assertion; the pin
    text taking `None` for the context fails the no-context path assertion.
    """
    from fransys_model.derive import connector_rows, is_sole_unit_root, list_context
    from fransys_model.derive.drawing_text import port_designation_in
    from fransys_model.vocab.tables import items

    model = _build_system()[0].model
    board_unit = next(
        u.id for u in units(model).values() if unit_release(model, u.id).name == "demo-io-board"
    )
    board = next(
        i.id
        for i in items(model).values()
        if i.unit == board_unit and is_sole_unit_root(model, i.id)
    )
    context = list_context(model, board)
    (own,) = connector_rows(model, board, unit=board_unit, context=context)
    (whole,) = connector_rows(model, board, context=context)
    assert (own.designation, whole.designation) == ("-X1", "-U1-X1")  # inside: R2
    assert own.mate is not None
    assert whole.mate_designation == "-WH1-P1"  # outside, whole model: as everywhere
    assert own.mate_designation is None  # the nested unit's own list names nothing outside it
    assert [p.mate_port_designation for p in own.pins] == [None, None]
    assert all(p.mate_port is not None for p in own.pins)  # the ids stay
    assert all(p.mate_port_designation == "-WH1-P1:" + p.marking for p in whole.pins)
    (bare,) = connector_rows(model, board)  # no unit, no context: the full path
    assert all(p.mate_port is not None for p in bare.pins)
    assert all(
        p.mate_port is not None
        and p.mate_port_designation == port_designation_in(model, p.mate_port, None)
        and str(p.mate_port_designation).startswith("+ER+C1-WH1-P1:")
        for p in bare.pins
    )
