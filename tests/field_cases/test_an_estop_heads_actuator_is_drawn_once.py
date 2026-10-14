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
The records are layout records, read through `fransys_model.layout` as
`test_contact_blocks_on_an_estop_head_draw_the_estop.py` does; the public API has no reader.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive.drawing_text import contact_image, cross_reference_text, label_text
from fransys_model.layout import Label, LabelKind, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items

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
        d.wire(strip[2 * number - 1], block[first], wire=wire)
        d.wire(block[str(int(first) + 1)], strip[2 * number], wire=wire)
    return fr.build(d, cabinet_document(cabinet)).model


def _by_pin(model: Model) -> dict[str, SymbolPlacement]:
    """Each block's placement, keyed by the first pin of its part ("11", "21", "31")."""
    first = {f"G{n}/block-{n}": pin for n, pin in enumerate(_BLOCKS.values(), start=1)}
    return {
        first[items(model)[functions(model)[p.function].item].key[-1]]: p
        for p in layout_of(model, SymbolPlacement).values()
        if items(model)[functions(model)[p.function].item].key[-1] in first
    }


def _labels(model: Model, pin: str, *, kind: LabelKind) -> list[Label]:
    placement = _by_pin(model)[pin]
    return [
        one
        for one in layout_of(model, Label).values()
        if one.function == placement.function and one.kind is kind and one.slot == "tag"
    ]


def test_two_circuits_share_a_page_and_the_third_has_its_own(model: Model) -> None:
    """The shape holds: 11-12 and 21-22 on one page, 31-32 on another."""
    pages = {pin: p.page for pin, p in _by_pin(model).items()}
    assert pages["11"] == pages["21"]
    assert pages["31"] != pages["11"]


def test_exactly_the_lead_block_draws_the_emergency_stop(model: Model) -> None:
    """Only 11-12 draws the mushroom; the others draw the positive-opening break contact."""
    drawn = {pin: p.symbol for pin, p in _by_pin(model).items()}
    assert drawn == {
        "11": "emergency-stop",
        "21": "break-contact-positive-opening",
        "31": "break-contact-positive-opening",
    }


@pytest.mark.parametrize("pin", ["21", "31"])
def test_a_plain_contact_prints_the_heads_tag_and_refers_to_the_lead(
    model: Model, pin: str
) -> None:
    """The plain contact prints "-S1" and a reference that is derive's text for the lead's cell."""
    lead = _by_pin(model)["11"]
    (tag,) = _labels(model, pin, kind=LabelKind.TAG)
    assert label_text(model, tag).endswith("-S1")
    (reference,) = _labels(model, pin, kind=LabelKind.CROSS_REFERENCE)
    assert {p.page for p in reference.partners} == {lead.page}
    text = cross_reference_text(model, reference)
    assert text
    cell = contact_image(model, _table(model))[1][0].split(" ")[1]  # the lead's own cell
    assert text.endswith(cell)
    assert (":" in text) == (_by_pin(model)[pin].page != lead.page)
    assert label_text(model, reference) == text


def test_the_references_print_the_leads_cell_as_the_coil_contacts_do(model: Model) -> None:
    """A coil contact's text (owner D2): the cell on the lead's page, page and cell elsewhere."""
    texts = {
        pin: label_text(model, _labels(model, pin, kind=LabelKind.CROSS_REFERENCE)[0])
        for pin in ("21", "31")
    }
    assert texts == {"21": "1B", "31": "p1:1B"}


def _table(model: Model) -> Label:
    lead = _by_pin(model)["11"]
    (found,) = (
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE
        and one.slot.startswith("contacts")
        and one.function == lead.function
    )
    return found


def test_one_contact_table_under_the_lead_lists_the_three_contacts(model: Model) -> None:
    """The table's subject is 11-12's function; it has no NO entry and three NC entries."""
    tables = [
        one
        for one in layout_of(model, Label).values()
        if one.kind is LabelKind.CROSS_REFERENCE and one.slot.startswith("contacts")
    ]
    assert tables == [_table(model)]
    no, nc = contact_image(model, _table(model))
    assert no == []
    assert [entry[:6] for entry in nc] == ["11-12 ", "21-22 ", "31-32 "]


if TYPE_CHECKING:
    from fransys_model.kernel import Model
