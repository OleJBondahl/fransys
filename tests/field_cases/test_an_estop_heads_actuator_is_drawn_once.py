"""Field case: an emergency-stop head with three NC blocks in three circuits draws one mushroom.

The engineering shape: one e-stop head `S1` sold apart from its contact blocks, with three
break-contact blocks (11-12, 21-22, 31-32) clipped on and joined to it with `parent=`. Each block
opens its own circuit; two circuits stand on one page and the third on another.

The bug: every block drew the full actuator, so the page set showed three mushrooms for one
button, and no sheet said where the other two contacts stand.

Fixing decisions: model-0237 (the actuated group and `lead_switch`: the first contact of the
group's contact list), layout-0237 (the actuator at the lead contact, the other contacts plain
with the head's tag and a reference to the lead, a contact table under the lead listing every
contact of the group) and electrical-symbols D50 (the positive-opening break contact). Invented
parts from `demo_parts`: `DEMO-HEAD-ESTOP`, `DEMO-BLOCK-1NC`, `DEMO-BLOCK-1NC-21` and
`DEMO-BLOCK-1NC-31`.
The drawn things are read from the core path's page Drawings (`drawn_pages`), as
`test_contact_blocks_on_an_estop_head_draw_the_estop.py` does.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from _tables_on import TABLES_ON
from fransys.colours import BU

_BLOCKS = {"DEMO-BLOCK-1NC": "11", "DEMO-BLOCK-1NC-21": "21", "DEMO-BLOCK-1NC-31": "31"}


@pytest.fixture(scope="module")
def model() -> Model:
    """The head with three NC blocks; the third circuit starts a new page."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="E-stop", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    d.layout.profile(actuator_each_contact=False)  # one actuator per device (the default is True)
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    head = d.device("S1", "DEMO-HEAD-ESTOP")
    wire = (BU, 0.5)
    for number, (mpn, first) in enumerate(_BLOCKS.items(), start=1):
        with d.function(f"G{number}", f"Stop circuit {number}") as group:
            block = d.device(None, mpn, name=f"block-{number}", parent=head)
        if number == len(_BLOCKS):
            d.layout.break_before(group)
        d.detail.wire(strip[2 * number - 1], block[first], wire=wire)
        d.detail.wire(block[str(int(first) + 1)], strip[2 * number], wire=wire)
    return fr.build(d, cabinet_document(cabinet), settings=TABLES_ON).model


def _by_pin(model: Model) -> dict[str, tuple[Any, DrawnSymbol]]:
    """Each block's (page, symbol), keyed by the first pin of its part ("11", "21", "31")."""
    return {
        dict(symbol.slots)["marking.in"]: (page, symbol)
        for page, drawing in drawn_pages(model).items()
        for symbol in drawing.symbols
        if dict(symbol.slots).get("marking.in") in _BLOCKS.values()
    }


def _texts(model: Model, pin: str, *, kind: str) -> list[DrawnText]:
    """The texts of `kind` on the block's page that stand in the block's column."""
    page, symbol = _by_pin(model)[pin]
    return [
        one
        for one in drawn_pages(model)[page].texts
        if one.kind == kind and symbol.x - 60 <= one.box.x <= symbol.x + 60
    ]


def _tables(model: Model) -> list[DrawnSymbol]:
    """Every contact table the pages draw."""
    return [
        symbol
        for drawing in drawn_pages(model).values()
        for symbol in drawing.symbols
        if symbol.key == "contact-head"
    ]


def test_two_circuits_share_a_page_and_the_third_has_its_own(model: Model) -> None:
    """The shape holds: 11-12 and 21-22 on one page, 31-32 on another."""
    pages = {pin: page for pin, (page, _) in _by_pin(model).items()}
    assert pages["11"] == pages["21"]
    assert pages["31"] != pages["11"]


def test_exactly_the_lead_block_draws_the_emergency_stop(model: Model) -> None:
    """Only 11-12 draws the mushroom; the others draw the positive-opening break contact."""
    drawn = {pin: symbol.key for pin, (_, symbol) in _by_pin(model).items()}
    assert drawn == {
        "11": "emergency-stop",
        "21": "break-contact-positive-opening",
        "31": "break-contact-positive-opening",
    }


@pytest.mark.parametrize("pin", ["21", "31"])
def test_a_plain_contact_prints_the_heads_tag_and_refers_to_the_lead(
    model: Model, pin: str
) -> None:
    """The plain contact prints "-S1" and a reference to the lead's cell (p1:1B on another page)."""
    assert [one.text for one in _texts(model, pin, kind="TAG")] == ["-S1"]
    (reference,) = _texts(model, pin, kind="CROSS_REFERENCE")
    assert reference.text == {"21": "1B", "31": "p1:1B"}[pin]


def test_the_references_print_the_leads_cell_as_the_coil_contacts_do(model: Model) -> None:
    """A coil contact's text (owner D2): the cell on the lead's page, page and cell elsewhere."""
    texts = {
        pin: [one.text for one in _texts(model, pin, kind="CROSS_REFERENCE")]
        for pin in ("21", "31")
    }
    assert texts == {"21": ["1B"], "31": ["p1:1B"]}


def test_one_contact_table_under_the_lead_lists_the_three_contacts(model: Model) -> None:
    """One table, on the lead's page, with no NO entry and three NC entries."""
    (table,) = _tables(model)
    lead_page = _by_pin(model)["11"][0]
    assert table in drawn_pages(model)[lead_page].symbols
    no_nc = table.texts[1:]
    assert [row[1][:6] for row in no_nc if len(row) > 1 and row[1]] == [
        "11-12 ",
        "21-22 ",
        "31-32 ",
    ]
    assert not [row[0] for row in no_nc if row[0]]


if TYPE_CHECKING:
    from typing import Any

    from fransys_layout.drawing import DrawnSymbol, DrawnText
    from fransys_model.kernel import Model
