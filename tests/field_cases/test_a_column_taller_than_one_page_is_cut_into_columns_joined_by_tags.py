"""Field case: a series of forty contacts, taller than one page, is cut into columns joined by tags.
The bug: a column kept whole as a card stood taller than the page, so the build named PAGE_OVERFLOW or drew past the frame.
Fixed by CUT-TALL, a column taller than one page is cut where a piece fills the page, each cut a tag pair (PAGE-CUT)."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
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
