"""Selector blocks, a limit switch and a push button draw by what operates them (layout-0220).

A device's actuator is drawn once, at its lead contact (layout-0237, ACTUATOR-ONCE).

OPERATED-BY A3 and A4: one invented cabinet built once through the public API; the drawn symbols
are layout records, read through `fransys_model.layout`.
"""

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.layout import SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions


@pytest.fixture(scope="module")
def drawn() -> dict[str, str]:
    """Each device's name joined to its function's name, to the symbol it draws."""
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
    names = {device.id: name for name, device in devices.items()}
    found = {}
    for placement in layout_of(model, SymbolPlacement).values():
        function = functions(model).get(placement.function) if placement.function else None
        if function is not None and function.item in names:
            found[f"{names[function.item]}.{function.name}"] = placement.symbol
    return found


def test_a_selector_heads_blocks_draw_the_selector_once(drawn: dict[str, str]) -> None:
    """layout-0237: the lead (11-12 lists first) draws the selector, the other block plain."""
    assert (drawn["sel-no.no"], drawn["sel-nc.nc"]) == ("make-contact", "selector-break")


def test_a_limit_switch_draws_the_position_switch_once(drawn: dict[str, str]) -> None:
    """layout-0237: the lead (13-14 lists first) draws the roller, the break contact plain."""
    assert (drawn["ls.no"], drawn["ls.nc"]) == ("position-switch-make", "break-contact")


def test_the_demo_push_button_draws_the_push_button_break(drawn: dict[str, str]) -> None:
    assert drawn["pb.sw"] == "push-button-break"
