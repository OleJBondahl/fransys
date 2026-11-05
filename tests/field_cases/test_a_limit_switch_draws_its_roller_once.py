"""Field case: a limit switch with a make and a break contact in two circuits draws a position-switch symbol per contact.
Once drew one roller; API-022 removed that mode, every contact now draws its own actuator."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnSymbol


@pytest.fixture(scope="module")
def model() -> Model:
    """B1 with its NO in one circuit and its NC in another, each off strip `X1`."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Limit", number="P-2", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    b1 = d.device("B1", "DEMO-LS-1NO1NC")
    wire = (BU, 0.5)
    with d.function("G1", "Run circuit"):
        d.series(strip[1].inner, b1.no["13"], wire=wire)
        d.series(b1.no["14"], strip[2].inner, wire=wire)
    with d.function("G2", "Alarm circuit"):
        d.series(strip[3], b1.nc["21"], wire=wire)
        d.series(b1.nc["22"], strip[4], wire=wire)
    return fr.build(d, cabinet_document(cabinet)).model


def _drawn(model: Model) -> tuple[Drawing, dict[str, DrawnSymbol]]:
    """B1's page and its contact symbols by function name (the NO has pins 13-14, the NC 21-22)."""
    ((page,),) = [[d] for d in drawn_pages(model).values()]
    pins = {"no": "13", "nc": "21"}
    found = {name: s for name, pin in pins.items() for s in page.symbols if pin in dict(s.slots).values()}
    return page, found


@pytest.mark.rule("SWITCH-SYMBOLS")
def test_the_no_contact_draws_the_roller_and_the_nc_draws_plain(model: Model) -> None:
    """Each contact of B1 draws its own position-switch symbol."""
    drawn = {name: s.key for name, s in _drawn(model)[1].items()}
    assert drawn == {"no": "position-switch-make", "nc": "position-switch-break"}


if TYPE_CHECKING:
    from fransys_model.kernel import Model
