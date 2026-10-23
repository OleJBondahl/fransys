"""SERIES-GAPS S8 (A10): a selector changeover is entered at its throws and drawn turned."""

from typing import NamedTuple

import fransys as fr
import pytest
from _drawn_pages import drawn_pages


class _Io(NamedTuple):
    """No boundary."""


def _selector(c) -> None:
    """Supply A through QA to the make throws, commons to M1; supply B through QB to the breaks."""
    xa, xb = c.terminal_strip("XA", "DEMO-TB-2.5"), c.terminal_strip("XB", "DEMO-TB-2.5")
    a = c.ac_supply("A", "230", xa[1], xa[2], xa[3], names=("A_L1", "A_L2", "A_L3"))
    b = c.ac_supply("B", "230", xb[1], xb[2], xb[3], names=("B_L1", "B_L2", "B_L3"))
    qa, qb = c.device("QA", "DEMO-MCB-3P"), c.device("QB", "DEMO-MCB-3P")
    q1, m1 = c.device("Q1", "DEMO-SEL-3P-24"), c.device("M1", "DEMO-MOTOR-4KW")
    c.series(a, qa.element, q1.co.no, m1, wire=2.5)
    c.series(b, qb.element, q1.co.nc, wire=2.5)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    """The selector circuit in a unit, built with its cabinet schematic (one build per module)."""
    unit = fr.unit(
        "sel", revision=1, interface_version=1, date="2026-10-14", text="First", by="XX"
    )(lambda c: (_selector(c), _Io())[1])
    d = fr.design("demo_parts")
    d.add(unit, "U1")
    cover = tmp_path_factory.mktemp("selector") / "cover.md"
    cover.write_text("# Selector\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "sel", cover=cover))


def test_supply_a_reaches_the_make_throws_and_the_commons_feed_the_motor(built) -> None:
    ends = {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(built.model)}
    for pole, (line, motor) in enumerate((("2", "U"), ("4", "V"), ("6", "W")), start=1):
        assert frozenset((f"-U1-QA:{line}", f"-U1-Q1:{pole}4")) in ends
        assert frozenset((f"-U1-QB:{line}", f"-U1-Q1:{pole}2")) in ends
        assert frozenset((f"-U1-Q1:{pole}1", f"-U1-M1:{motor}")) in ends


def test_the_selector_is_drawn_turned_with_its_commons_toward_the_load(built) -> None:
    (placed,) = (
        symbol
        for drawing in drawn_pages(built.model).values()
        for symbol in drawing.symbols
        if symbol.key == "change-over-contact"
    )
    assert placed.orient in {"R180", "MR180"}


def test_q1s_unwired_coil_is_not_drawn_and_its_contacts_print_q1_with_no_cell(built) -> None:
    """layout-0218 (A3): -Q1's coil has nothing connected, so no symbol and no contact table.

    Each drawn contact of -Q1 still prints its tag, "-Q1", with no cell: no cross-reference.

    # UNDO: engines/schematic/read/loose.py, `without_loose` returns `inputs` unchanged
    """
    drawings = tuple(drawn_pages(built.model).values())
    symbols = [symbol for drawing in drawings for symbol in drawing.symbols]
    texts = [text for drawing in drawings for text in drawing.texts if "Q1" in text.text]
    assert not [s for s in symbols if s.key in {"operating-device", "contact-head"}], (
        "no coil symbol and no contact table for -Q1"
    )
    assert [s for s in symbols if s.key == "change-over-contact"], (
        "the selector's contacts are drawn"
    )
    assert [(text.text, text.kind) for text in texts] == [("-Q1", "TAG")], (
        "the drawn contact prints its tag and no cross-reference"
    )
