"""Field case: a series of forty contacts, taller than one page, is cut into columns with tags.

The engineering shape: a 24 V supply, forty contacts in series, a relay coil and the return to
0 V, in one unit. Drawn as one column the contacts stand 2000 G tall on an 822 G page.

The bug: the column was kept whole when its block was a card, so the row stood taller than the
page and the build named PAGE_OVERFLOW, or drew past the frame. A column taller than one page is
cut where a piece fills the page, each cut a tag pair, and the block is as tall as its pieces
(CUT-TALL; rule PAGE-CUT).
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest

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
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    cover = tmp_path_factory.mktemp("tall") / "cover.md"
    cover.write_text("# C\n", encoding="utf-8")
    d = fr.design("demo_parts")
    d.add(_tall, "U1")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "tall-chain", cover=cover))


@pytest.mark.rule("PAGE-CUT")
def test_forty_contacts_in_series_build_with_no_overflow_and_every_contact_drawn(
    built: fr.BuildResult,
) -> None:
    assert not [f for f in built.findings if f.code == "PAGE_OVERFLOW"]
    pages = list(built.drawings.values())
    assert pages
    assert sum(len(p.symbols) for p in pages) >= CONTACTS + 2  # the contacts, the supply, the coil
