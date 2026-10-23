"""Field case: a limit switch with a make and a break contact in two circuits draws one roller.

The engineering shape: a limit switch `B1` with one NO contact (13-14) and one NC contact
(21-22), one roller lever moving both. The two contacts sit in two circuits.

The bug: each contact drew the full roller symbol, so a single lever showed two rollers.

Fixing decisions: model-0237 (the actuated group and `lead_switch`: the first contact of the
group's contact list, here the NO), layout-0237 (the roller at the lead contact, the other
contact plain with the device tag and a reference to the lead, a contact table under the lead)
and electrical-symbols D50. Invented part from `demo_parts`: `DEMO-LS-1NO1NC`.
The records are layout records, read through `fransys_model.layout`; the public API has no reader.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from _tables_on import TABLES_ON
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
    d.layout.profile(actuator_each_contact=False)  # one actuator per device (the default is True)
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    b1 = d.device("B1", "DEMO-LS-1NO1NC")
    wire = (BU, 0.5)
    with d.function("G1", "Run circuit"):
        d.detail.wire(strip[1], b1.no["13"], wire=wire)
        d.detail.wire(b1.no["14"], strip[2], wire=wire)
    with d.function("G2", "Alarm circuit"):
        d.detail.wire(strip[3], b1.nc["21"], wire=wire)
        d.detail.wire(b1.nc["22"], strip[4], wire=wire)
    return fr.build(d, cabinet_document(cabinet), settings=TABLES_ON).model


def _drawn(model: Model) -> tuple[Drawing, dict[str, DrawnSymbol]]:
    """B1's page and its contact symbols by function name (the NO has pins 13-14, the NC 21-22)."""
    ((page,),) = [[d] for d in drawn_pages(model).values()]
    pins = {"no": "13", "nc": "21"}
    found = {
        name: s for name, pin in pins.items() for s in page.symbols if pin in dict(s.slots).values()
    }
    return page, found


def _tag(page: Drawing, symbol: DrawnSymbol) -> str:
    """The tag text that stands nearest to `symbol`."""
    tags = [t for t in page.texts if t.kind == "TAG"]
    near = min(tags, key=lambda t: abs(t.box.x - symbol.x) + abs(t.box.y - symbol.y))
    return near.text


def test_the_no_contact_draws_the_roller_and_the_nc_draws_plain(model: Model) -> None:
    """One roller symbol for B1, on the NO (the lead); the NC is a plain break contact."""
    drawn = {name: s.key for name, s in _drawn(model)[1].items()}
    assert drawn == {"no": "position-switch-make", "nc": "break-contact"}


def test_the_nc_refers_to_the_no(model: Model) -> None:
    """The NC carries a reference whose partner is the NO's page, and the NO prints B1."""
    page, found = _drawn(model)
    assert _tag(page, found["no"]).endswith("B1")
    (reference,) = (s for s in page.symbols if s.key == "reference-marker")
    (table,) = (s for s in page.symbols if s.key == "contact-head")
    cell = table.texts[1][0]
    assert dict(reference.slots)["ref"] == cell.split(" ")[1]  # the NO's own cell


def test_the_table_under_the_no_lists_both_contacts(model: Model) -> None:
    """NO column "13-14 ...", NC column "21-22 ..."; the NC has no table of its own."""
    page, _ = _drawn(model)
    (table,) = (s for s in page.symbols if s.key == "contact-head")
    rows = table.texts[1:]
    no, nc = ([row[i] for row in rows if row[i]] for i in (0, 1))
    assert [entry[:6] for entry in no] == ["13-14 "]
    assert [entry[:6] for entry in nc] == ["21-22 "]


if TYPE_CHECKING:
    from fransys_model.kernel import Model
