"""Field case: a contact is a spare only when no conductor and no net reaches any of its ports.

The engineering shape: a contactor with a coil, a wired NO auxiliary contact and an NC auxiliary
contact nobody wired, whose terminal 21 is only declared on a control net. A second contactor
carries a clip-on add-on block whose NC contact nobody wired. With
`d.layout.profile(hide_unused_pins=True)` a spare contact is left off the page.

The bug: layout kept a contact on a net with no conductor on the page, but the coil's contact table
listed it as a spare, since the table asked a second, conductor-only question. The fix is
decision model-0120: `derive.function_is_unused` is the one answer, read by layout and the table.
The block's spare belongs under its contactor's reference (model-0119).
"""

import tempfile
from pathlib import Path

import fransys as fr
from _contact_tables import contact_table
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from _tables_on import TABLES_ON
from fransys.colours import BU

from fransys_model.derive import net_of
from fransys_model.vocab.tables import nets


def _net_contact_result(*, wired: bool = False):
    """The contactor Q1 with its NC contact 21 declared on a net; `wired` also runs a wire to it."""
    d = fr.design("demo_parts", place="CAB")
    d.layout.profile(hide_unused_pins=True)
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamp = d.device("P1", "DEMO-LAMP-24")
        q = d.device("Q1", "DEMO-CTR-3P-NC")
    blue = (BU, 0.5)
    d.detail.wire(psu.output["+"], q.coil["A1"], wire=blue)
    d.detail.wire(psu.output["-"], q.coil["A2"], wire=blue)
    d.detail.wire(psu.output["+"], q.aux["13"], wire=blue)
    d.detail.wire(q.aux["14"], lamp["1"], wire=blue)
    d.detail.wire(psu.output["-"], lamp["2"], wire=blue)
    d.detail.net("SIG", q.aux_nc["21"], lamp["2"])
    if wired:
        d.detail.wire(q.aux_nc["21"], lamp["2"], wire=blue)
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _built_block():
    """K1 with an add-on block: 53-54 wired, the NC contact 61-62 not."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Block", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    d.layout.profile(hide_unused_pins=True)
    _cabinet = d.location("CAB", "Cabinet")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    feed, zero, load = x1[1], x1[2], x1[3]
    with d.function("G", "Group"):
        k1 = d.device("K1", "DEMO-CTR-3P-24")
        block = d.device(None, "DEMO-CTR-BLOCK-1NO1NC", name="block", parent=k1)
    blue = (BU, 0.5)
    d.detail.wire(feed, k1.coil["A1"], wire=blue)
    d.detail.wire(k1.coil["A2"], zero, wire=blue)
    d.detail.wire(feed, block.no["53"], wire=blue)
    d.detail.wire(block.no["54"], load, wire=blue)
    return fr.build(d, cabinet_document(_cabinet), settings=TABLES_ON).model


def _built_net_contact():
    """The model of `_net_contact_result()`, which the cross-link study reads (study_cases.py)."""
    return _net_contact_result().model


def _sig_pieces(result) -> set:
    """The physical nets of the ports of the declared net SIG."""
    (sig,) = [n for n in nets(result.model).values() if n.name == "SIG"]
    return {net_of(result.model, p) for p in sig.ports}


def _placed_21(model) -> list:
    """The symbols drawn with the marking 21."""
    return [
        s
        for drawing in drawn_pages(model).values()
        for s in drawing.symbols
        if any(slot.startswith("marking.") and text == "21" for slot, text in s.slots)
    ]


def test_a_declared_net_joins_nothing_and_warns_when_unrealised() -> None:
    """R468: SIG's two ports stay two physical nets, NET_UNREALISED warns, contact 21 is a spare."""
    result = _net_contact_result()
    assert len(_sig_pieces(result)) == 2
    assert [f.code for f in result.findings if f.code == "NET_UNREALISED"] == ["NET_UNREALISED"]
    assert not _placed_21(result.model)


def test_a_declared_net_realised_by_a_wire_is_one_net_and_does_not_warn() -> None:
    """R468: a wire between the two ports realises SIG: one physical net, no warning."""
    result = _net_contact_result(wired=True)
    assert len(_sig_pieces(result)) == 1
    assert [f for f in result.findings if f.code == "NET_UNREALISED"] == []
    assert _placed_21(result.model)


def test_a_spare_on_an_add_on_block_is_listed_under_the_contactors_reference() -> None:
    """The block's NC contact 61-62 is a bare entry in K1's table; its wired 53-54 keeps a place."""
    no, nc = contact_table(_built_block())
    assert nc == ["61-62 N/A"]  # layout-0112: no place for a bare contact
    assert any(entry.startswith("53-54 ") for entry in no)
