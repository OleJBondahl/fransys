"""The tests' drawn-fact helpers read the subject of a drawn symbol and the page facts."""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
import pytest
from _drawn_facts import (
    document_facts,
    item_box,
    marker_symbols,
    symbol_subjects,
    text_subjects,
    wire_nets,
)
from _drawn_pages import drawn_pages
from fransys.colours import BU
from fransys_el.placement_nets import net_ports

from electrical_symbols import GENERIC_BOX_KEY

pytestmark = pytest.mark.rule("DRAWING-SUBJECT")


@cache
def _model():
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        k = d.device("K1", "DEMO-CTR-3P-NC")
        lamp = d.device("P1", "DEMO-LAMP-24")
    d.series(k.coil["A1"], lamp.lamp["1"], wire=(BU, 0.5))
    d.series(k.aux["14"], lamp.lamp["2"], wire=(BU, 0.5))
    d.series(k.coil["A2"], lamp.lamp["2"], wire=(BU, 0.5))
    d.series(k.aux["13"], lamp.lamp["1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)).model


def test_a_placed_symbol_has_its_tag_function_page_and_set() -> None:
    model = _model()
    placed = symbol_subjects(model)
    assert {p.tag for p in placed} >= {"K1", "P1"}
    facts = document_facts(model)
    assert set(facts) == set(drawn_pages(model))
    for p in placed:
        assert p.page in facts
        assert p.drawing_set == facts[p.page].drawing_set
        assert p.symbol == p.drawn.key
        assert p.owner == p.function.value


def test_a_placed_symbols_dicts_follow_the_drawn_tuples() -> None:
    placed = symbol_subjects(_model())
    lamp = next(p for p in placed if p.symbol == "lamp")
    assert lamp.slots == dict(lamp.drawn.slots)
    assert lamp.x == lamp.drawn.x


def test_a_wire_net_is_a_net_id_of_the_model() -> None:
    model = _model()
    values = set(net_ports(model))
    wires = wire_nets(model)
    assert wires
    assert all(w.net in values for _, w in wires)
    assert marker_symbols(model) == []


def test_a_text_has_the_function_of_the_symbol_it_annotates() -> None:
    model = _model()
    placed = {p.drawn.id: p for p in symbol_subjects(model)}
    texts = text_subjects(model)
    assert texts
    assert all(placed[t.owner].function == t.function for t in texts)
    assert {t.text for t in texts} >= {"-K1", "-P1"}


def _item_box_build() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    live = d.terminal_strip("X1", "DEMO-TB-2.5", 1).run("L", 1)
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        m1 = d.device("M1", "DEMO-RED-2IN")
    d.series(psu.output["+"], m1.in_1["1+"], wire=(BU, 1.5))
    d.series(m1.out["+"], live[1].outer, wire=(BU, 1.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def test_an_item_box_is_found_by_the_items_printed_designation() -> None:
    box = item_box(_item_box_build().model, "M1")
    assert box.tag == "M1"
    assert box.symbol == GENERIC_BOX_KEY


def test_an_item_box_build_shows_no_no_cell_and_no_connection_findings() -> None:
    assert not {f.code for f in _item_box_build().findings} & {"NO_CELL", "CONNECTION_NOT_DRAWN", "DANGLING_WIRE_END"}
