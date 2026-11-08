"""Field case: a series of forty contacts, taller than one page, is cut into columns joined by tags.
The bug: a column kept whole as a card stood taller than the page, so the build named PAGE_OVERFLOW or drew past the frame.
Fixed by CUT-TALL, a column taller than one page is cut where a piece fills the page, each cut a tag pair (PAGE-CUT)."""

from typing import Any, NamedTuple, cast

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import unit_document

CONTACTS = 40


class _Unit(NamedTuple):
    """A unit with no interface to hand back."""


@fr.unit("tall-chain", revision=1, interface_version=1, date="2026-10-19", text="first", by="AB")
def _tall(c: Any) -> _Unit:
    dc = c.dc_supply("24VDC", c.device("G1", "DEMO-PSU-24"))
    contacts = [c.device(f"S{n}", "DEMO-CTR-BLOCK-1NO1NC").no for n in range(1, CONTACTS + 1)]
    c.series(dc.plus, *contacts, c.device("K1", "DEMO-RLY-2CO-24").coil, dc.minus, wire=0.75)
    return _Unit()


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(_tall, "U1")
    return fr.build(d, unit_document("tall-chain"))


@pytest.mark.rule("PAGE-CUT")
def test_forty_contacts_in_series_build_with_no_overflow_and_every_contact_drawn(
    built: fr.BuildResult,
) -> None:
    assert not [f for f in built.findings if f.code == "PAGE_OVERFLOW"]
    pages = list(built.drawings.values())
    assert pages
    assert sum(len(p.symbols) for p in pages) >= CONTACTS + 2  # the contacts, the supply, the coil


@fr.unit("wide-row", revision=1, interface_version=1, date="2026-11-07", text="first", by="AB", title="Wide row", number="W-1")
def _wide(u: Any) -> _Unit:
    with u.function("F1", "Monitoring"):
        monitor = u.device("B1", "FLD-GAS-MONITOR")
        controller = u.device("A1", "FLD-AI-CTRL-20")
    u.series(monitor.X1["1"], controller.ai_1["ANALOG_INPUT_01_P"], wire=("BK", 1.0))
    return _Unit()


@pytest.mark.rule("PAGE-CUT")
def test_a_row_wider_than_its_page_is_a_finding_and_a_page_with_none_holds_no_such_row(built: fr.BuildResult) -> None:
    """R1939: PAGE_OVERFLOW and WIDER_THAN_PAGE read the widths `Drawing.rows` carries (the KI-773 shape, public API only)."""
    wide = fr.design("demo_parts", "crash_parts")
    wide.add(_wide, "U1", place=None)
    result = fr.build(wide, unit_document("wide-row"))
    expect_codes(result, "WIDER_THAN_PAGE", "PAGE_OVERFLOW")
    assert {f.code for f in result.findings if f.severity == fr.Severity.ERROR} == {"WIDER_THAN_PAGE", "PAGE_OVERFLOW"}
    pages = built.drawings.values()
    margin = cast("tuple[int, int]", built.settings.layout["margin"])[0]
    assert all(r.width <= p.area.w - 2 * margin for p in pages for r in p.rows)
