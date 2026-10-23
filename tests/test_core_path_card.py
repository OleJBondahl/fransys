"""The 16-channel PLC output card on the core path: findings, coils at pins, table position (B4).

The card is a box with 16 channel pins and a relay coil under each. The findings counts are
reported, not gated beyond ERROR. The table offsets equal today's engine's first tier (TABLE
POSITION T1, T2); the second tier of a staggered row is TABLE-STACK's.
"""

from collections import Counter
from dataclasses import replace
from itertools import pairwise
lazy from pathlib import Path

import fransys as fr
import pypdfium2 as pdfium
from _card_case import card_case_drafts
from _drawn_pages import drawn_pages
from _tables_on import TABLES_ON
lazy import pytest

from fransys_layout.symbols import symbol_views
from fransys_model.derive import physical_nets
from fransys_model.vocab import functions, items

_CHANNELS = 16


def _build(settings: fr.Settings | None = None) -> fr.BuildResult:
    return fr.build(*card_case_drafts(_CHANNELS), settings=settings)


def _symbols(model) -> list:
    """Every drawn symbol of the built model, on every page."""
    return [s for drawing in drawn_pages(model).values() for s in drawing.symbols]


def _wires(model) -> list:
    """Every drawn wire of the built model, on every page."""
    return [w for drawing in drawn_pages(model).values() for w in drawing.wires]


def _tag(model, function) -> str:
    return str(items(model)[functions(model)[function].item].tag)


def _pdf_pages(tmp_path: Path) -> int:
    paths = fr.write(_build(), tmp_path / "core")
    return len(pdfium.PdfDocument(next(p for p in paths if p.suffix == ".pdf")))


def test_the_core_cabinet_pdf_has_three_pages(tmp_path) -> None:
    """Cover, the card's drawing set, the BOM: a location document prints the core's set."""
    assert _pdf_pages(tmp_path) == 3


def test_the_16_channel_card_pdf_has_no_error(tmp_path) -> None:
    """With `contact_tables` on (CONTACT-TABLE) the card draws its sixteen table heads."""
    result = _build(TABLES_ON)
    findings = fr.check(result)
    assert [f for f in findings if f.severity.name == "ERROR"] == []
    assert [p for p in fr.write(result, tmp_path / "out") if p.suffix == ".pdf"]
    symbols = Counter(r.key for r in _symbols(result.model))
    assert (symbols["generic-box"], symbols["contact-head"]) == (1, _CHANNELS)


def test_the_16_channel_card_reports_no_function_it_did_not_draw() -> None:
    counts = Counter(f.code for f in fr.check(_build()))
    assert counts["FUNCTION_NOT_DRAWN"] == 0


def test_the_card_gives_no_net_not_drawn_for_its_unused_pins() -> None:
    """An unused contact pin has no second end: no net, never drawn, no finding (Ruling 86)."""
    result = _build()
    lone = [p for p in physical_nets(result.model) if len(p.ports) == 1]
    assert len(lone) > 0
    assert [f for f in fr.check(result) if f.code == "NET_NOT_DRAWN"] == []


def test_every_coil_stands_at_the_x_of_its_wire() -> None:
    model = _build().model
    coils = [r for r in _symbols(model) if r.key == "operating-device"]
    wires = [w.points[0][0] for w in _wires(model)]
    assert len(coils) == len(wires) == _CHANNELS
    assert sorted(r.x for r in coils) == sorted(wires)


def test_the_card_stands_pin_over_pin_at_the_footprint_pitch() -> None:
    """CH01 over CH09: the N and S coil x's are equal pair by pair; justify leaves the pitch."""
    model = _build().model
    coils = [r for r in _symbols(model) if r.key == "operating-device"]
    rows = {y: sorted(r.x for r in coils if r.y == y) for y in {r.y for r in coils}}
    north, south = (rows[y] for y in sorted(rows))
    assert north == south
    assert {b - a for a, b in pairwise(north)} == {96}


def test_the_kth_coil_above_stands_over_the_kth_coil_below() -> None:
    """CH01 over CH09 (BOX-SIDES): the half split puts 8 coils above and 8 below the card."""
    model = _build().model
    coils = [r for r in _symbols(model) if r.key == "operating-device"]
    rows = [sorted(r.x for r in coils if r.y == y) for y in sorted({r.y for r in coils})]
    assert len(rows) == 2
    assert rows[0] == rows[1]


def test_the_card_pitch_is_the_body_wire_and_table_floor() -> None:
    model = _build().model
    coils = [r for r in _symbols(model) if r.key == "operating-device"]
    xs = sorted({r.x for r in coils})
    assert {b - a for a, b in pairwise(xs)} == {96}


def test_no_designation_text_is_measured_into_a_footprint(monkeypatch: pytest.MonkeyPatch) -> None:
    """The designation sets the label's size only: the views are the same with no text (R334)."""
    asked: list[str] = []
    real = symbol_views

    def spy(symbol, library, ask):
        drawn = real(symbol, library, ask)
        bare = real(symbol, library, replace(ask, text=""))
        asked.append(ask.text)
        assert {o: v.footprint for o, v in drawn.views.items()} == {
            o: v.footprint for o, v in bare.views.items()
        }
        return drawn

    monkeypatch.setattr("fransys_el.placement_syms.symbol_views", spy)
    _build()
    assert any(asked)
