"""Field case: a three-pole breaker and fuse, each ending a series on a three-terminal strip, print their pole pin numbers.
The bug: pole marking slots are marking.<k>.in/out, but the lookup used the one-pole slot, so pins 1-6 never printed.
Fixed by PORT-LINE and DESIGNATION-SCHEME, a pole's pins print the part's pin marking (derive.port_marking)."""

import re
import tempfile
from pathlib import Path

import fransys as fr
import pytest
from fransys.colours import BK

from fransys_model.layout import Page, layout_of


@pytest.fixture(scope="module")
def texts() -> list[str]:
    root = Path(tempfile.mkdtemp())
    d = fr.design("demo_parts", place="CAB")
    d.project(title="T", number="P-1", customer="E", revision=1, author="OJB")
    d.revision(1, date="2026-10-15", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    with d.function("G1", "Mains"):
        q0 = d.device("Q0", "DEMO-MCB-3P")
        f3 = d.device("F3", "DEMO-MCB-3P")
        x3 = d.terminal_strip("X3", "DEMO-TB-2.5", 3)
        d.series(q0.element, x3, f3.element, wire=(BK, 1.5))
    (root / "cover.md").write_text("# T\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=root / "cover.md")
    result = fr.build(d, doc)
    fr.write(result, root / "out", intermediates=root / "inter")
    found: list[str] = []
    for page in layout_of(result.model, Page).values():
        svg = (root / "inter" / f"layout.page-{page.id.value}.svg").read_text("utf-8")
        found += re.findall(r">([^<>]+)</text>", svg)
    return found


def test_two_three_pole_breakers_print_pins_one_to_six_each(texts: list[str]) -> None:
    for pin in "123456":
        assert texts.count(pin) - (pin in "123") == 2, pin  # X3's three terminals print their points 1 to 3 too (STRIP-TAG-ONCE)
