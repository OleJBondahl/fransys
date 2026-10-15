"""Field case: `fr.readability` counts an unwired device's symbol as loose instead of raising.

The engineering shape: a cabinet with one wired circuit (two breakers) and one PLC input card
that no wire reaches, in a `CABINET_SCHEMATIC` document. Layout-0218 leaves the card off every
page; its item box is a loose symbol.

The bug: `fr.build` succeeded but `fr.readability` raised KeyError, because the loose symbol of
an item box carries the item's id as its function and `function_unit` looked that id up in the
functions table.
The rule (decision model-0254): an unwired device's symbol counts as loose for its own unit, and
for the build.
"""

import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr
import pytest


def test_readability_counts_an_unwired_plc_card_as_one_loose_symbol() -> None:
    """The report returns, and the build counts the one card as loose."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="T", number="P", customer="C", revision=1, author="A")
    d.revision(1, date="2026-10-15", text="x", created="XX")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "a"):
        a = d.device("Q0", "DEMO-MCB-3P")
        b = d.device("F8", "DEMO-MCB-C6")
        d.detail.wire(a.element["2"], b.element["1"], wire=("BU", 0.5))
    with d.function("G3", "PLC"):
        d.device("AI1", "DEMO-PLC-AI-4")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# x\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    report = fr.readability(fr.build(fr.parts("demo_parts"), d, doc))
    assert report.loose_symbols == 1
    (design_row,) = [unit for unit in report.units if unit.unit is None]
    assert design_row.loose_symbols == 1


class _Io(NamedTuple):
    card: fr.Device


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-15", text="First", by="XX")
def _cab_with_unwired_card(c: fr.Design) -> _Io:
    with c.function("G1", "a"):
        a = c.device("Q0", "DEMO-MCB-3P")
        b = c.device("F8", "DEMO-MCB-C6")
        c.detail.wire(a.element["2"], b.element["1"], wire=("BU", 0.5))
    with c.function("G3", "PLC"):
        card = c.device("AI1", "DEMO-PLC-AI-4")
    return _Io(card=card)


@pytest.fixture(scope="module")
def unit_report(tmp_path_factory: pytest.TempPathFactory) -> fr.derive.ReadabilityReport:
    """The report of the same card, placed in the unit "U1" of the design."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="T", number="P", customer="C", revision=1, author="A")
    d.revision(1, date="2026-10-15", text="x", created="XX")
    d.location("CAB", "Cabinet")
    d.add(_cab_with_unwired_card, "U1")
    cover = tmp_path_factory.mktemp("cover") / "cover.md"
    cover.write_text("# x\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover)
    return fr.readability(fr.build(fr.parts("demo_parts"), d, doc))


def test_readability_counts_an_unwired_card_in_its_own_unit(
    unit_report: fr.derive.ReadabilityReport,
) -> None:
    """The card counts once, on the row of the unit that owns it, and not on the design's row."""
    (unit_row,) = [unit for unit in unit_report.units if unit.unit is not None]
    assert unit_row.loose_symbols == 1
    assert [unit for unit in unit_report.units if unit.unit is None] == []
