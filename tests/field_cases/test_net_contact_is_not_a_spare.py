"""Field case: a contact is a spare only when no conductor and no net reaches any of its ports.

The engineering shape: a contactor with a coil, a wired NO auxiliary contact and an NC auxiliary
contact nobody wired, whose terminal 21 is only declared on a control net. A second contactor
carries a clip-on add-on block (V10) whose NC contact nobody wired. With
`d.layout.profile(hide_unused_pins=True)` a spare contact is left off the page (CONVENTIONS-V06 V1).

The bug: layout kept a contact on a net with no conductor on the page, but the coil's contact table
listed it as a spare, since the table asked a second, conductor-only question. The fix is
decision model-0120: `derive.function_is_unused` is the one answer, read by layout and the table.
The block's spare belongs under its contactor's reference (model-0119).
"""

import tempfile
from pathlib import Path

import fransys as fr
from _model_build_cover import system_document
from fransys.colours import BU

from fransys_model.derive.drawing_text import contact_image
from fransys_model.layout import Label, LabelKind, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items


def _built_net_contact():
    """The contactor Q1 with its NC auxiliary contact 21 declared on a net, nothing wired to it."""
    d = fr.design("demo_parts", place="CAB")
    d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamp = d.device("P1", "DEMO-LAMP-24")
        q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.wire(psu.output["-"], q.coil["A2"], wire=blue)
    d.wire(psu.output["+"], q.aux["13"], wire=blue)
    d.wire(q.aux["14"], lamp["1"], wire=blue)
    d.wire(psu.output["-"], lamp["2"], wire=blue)
    d.net("SIG", q.aux_nc["21"], lamp["2"])
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc).model


def _built_block():
    """K1 with an add-on block: 53-54 wired, the NC contact 61-62 not."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Block", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    d.layout.profile(hide_unused_pins=True)
    d.location("CAB", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    feed, zero, load = x1[1], x1[2], x1[3]
    with d.function("G", "Group"):
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        block = d.device(None, "DEMO-CTR-BLOCK-1NO1NC", name="block", parent=k1)
    blue = (BU, 0.5)
    d.wire(feed, k1.coil["A1"], wire=blue)
    d.wire(k1.coil["A2"], zero, wire=blue)
    d.wire(feed, block.no["53"], wire=blue)
    d.wire(block.no["54"], load, wire=blue)
    return fr.build(d, system_document()).model


def _table(model, tag: str) -> tuple[list[str], list[str]]:
    """The contact table of the item tagged `tag`, its NO and NC entries as render prints them."""
    (item,) = (one.id for one in items(model).values() if one.tag == tag)
    (label,) = (
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE
        and one.slot == "contacts"
        and one.function is not None
        and functions(model)[one.function].item == item
    )
    return contact_image(model, label)


def test_a_contact_on_a_net_is_drawn_and_not_a_spare() -> None:
    """The NC contact is placed, and its table entry carries a place, not the bare "21-22"."""
    model = _built_net_contact()
    placed = [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if functions(model)[p.function].name == "aux_nc"
    ]
    assert placed
    _, nc = _table(model, "Q1")
    assert len(nc) == 1
    assert nc[0].startswith("21-22 ")


def test_a_spare_on_an_add_on_block_is_listed_under_the_contactors_reference() -> None:
    """The block's NC contact 61-62 is a bare entry in K1's table; its wired 53-54 keeps a place."""
    no, nc = _table(_built_block(), "K1")
    assert nc == ["61-62 N/A"]  # layout-0112: no place for a bare contact
    assert any(entry.startswith("53-54 ") for entry in no)
