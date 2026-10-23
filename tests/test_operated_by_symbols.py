"""Selector blocks, a limit switch and a push button draw by what operates them (layout-0220).

A device's actuator is drawn once, at its lead contact (layout-0237, ACTUATOR-ONCE).

OPERATED-BY A3 and A4: one invented cabinet built once through the public API; the drawn symbols
are the core path's page Drawings; a symbol is told by the pin markings it prints.
"""

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU


@pytest.fixture(scope="module")
def drawn() -> list[tuple[frozenset[str], str]]:
    """Each contact-like symbol drawn: the pin markings it prints, and its library key."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Operators", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    d.layout.profile(actuator_each_contact=False)  # one actuator per device (the default is True)
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    head = d.device("S1", "DEMO-HEAD-SEL")
    devices = {
        "sel-no": d.device(None, "DEMO-BLOCK-1NO", name="sel-no", parent=head),
        "sel-nc": d.device(None, "DEMO-BLOCK-1NC", name="sel-nc", parent=head),
        "ls": d.device("B1", "DEMO-LS-1NO1NC"),
        "pb": d.device("S2", "DEMO-PB-NC"),
    }
    pins = [("sel-no", "13", "14"), ("sel-nc", "11", "12"), ("ls", "13", "14")]
    pins += [("ls", "21", "22"), ("pb", "A", "B")]
    for n, (name, a, b) in enumerate(pins):
        d.detail.wire(strip[2 * n + 1], devices[name][a], wire=(BU, 0.5))
        d.detail.wire(devices[name][b], strip[2 * n + 2], wire=(BU, 0.5))
    model = fr.build(d, cabinet_document(cabinet)).model
    return [
        (frozenset(text for _, text in symbol.slots), symbol.key)
        for drawing in drawn_pages(model).values()
        for symbol in drawing.symbols
        if symbol.slots
    ]


def _key(drawn: list[tuple[frozenset[str], str]], *pins: str) -> list[str]:
    return [key for marks, key in drawn if marks == set(pins)]


def test_a_selector_heads_blocks_draw_the_selector_once(drawn: list) -> None:
    """layout-0237: the lead (11-12 lists first) draws the selector, the other block plain."""
    assert (_key(drawn, "13", "14"), _key(drawn, "11", "12")) == (
        ["position-switch-make", "make-contact"],
        ["selector-break"],
    )
    assert [key for _, key in drawn].count("selector-break") == 1


def test_a_limit_switch_draws_the_position_switch_once(drawn: list) -> None:
    """layout-0237: the lead (13-14 lists first) draws the roller, the break contact plain."""
    assert [key for _, key in drawn].count("position-switch-make") == 1
    assert _key(drawn, "21", "22") == ["break-contact"]


def test_the_demo_push_button_draws_the_push_button_break(drawn: list) -> None:
    assert _key(drawn, "A", "B") == ["push-button-break"]
