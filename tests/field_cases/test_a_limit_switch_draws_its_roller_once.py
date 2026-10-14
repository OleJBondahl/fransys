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
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_model.derive.drawing_text import contact_image, label_text
from fransys_model.layout import Label, LabelKind, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items


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
        d.wire(strip[1], b1.no["13"], wire=wire)
        d.wire(b1.no["14"], strip[2], wire=wire)
    with d.function("G2", "Alarm circuit"):
        d.wire(strip[3], b1.nc["21"], wire=wire)
        d.wire(b1.nc["22"], strip[4], wire=wire)
    return fr.build(d, cabinet_document(cabinet)).model


def _drawn(model: Model) -> dict[str, SymbolPlacement]:
    """B1's placements by function name."""
    return {
        functions(model)[p.function].name: p
        for p in layout_of(model, SymbolPlacement).values()
        if items(model)[functions(model)[p.function].item].key[-1] == "B1"
    }


def _labels(model: Model, name: str, kind: LabelKind, slot: str) -> list[Label]:
    function = _drawn(model)[name].function
    return [
        one
        for one in layout_of(model, Label).values()
        if one.function == function and one.kind is kind and one.slot.startswith(slot)
    ]


def test_the_no_contact_draws_the_roller_and_the_nc_draws_plain(model: Model) -> None:
    """One roller symbol for B1, on the NO (the lead); the NC is a plain break contact."""
    drawn = {name: p.symbol for name, p in _drawn(model).items()}
    assert drawn == {"no": "position-switch-make", "nc": "break-contact"}


def test_the_nc_refers_to_the_no(model: Model) -> None:
    """The NC carries a reference whose partner is the NO's page, and the NO prints B1."""
    (tag,) = _labels(model, "no", LabelKind.TAG, "tag")
    assert label_text(model, tag).endswith("B1")
    (reference,) = _labels(model, "nc", LabelKind.CROSS_REFERENCE, "tag")
    assert {p.page for p in reference.partners} == {_drawn(model)["no"].page}
    cell = contact_image(model, _labels(model, "no", LabelKind.CROSS_REFERENCE, "contacts")[0])[0]
    assert label_text(model, reference) == cell[0].split(" ")[1]  # the NO's own cell


def test_the_table_under_the_no_lists_both_contacts(model: Model) -> None:
    """NO column "13-14 ...", NC column "21-22 ..."; the NC has no table of its own."""
    assert _labels(model, "nc", LabelKind.CROSS_REFERENCE, "contacts") == []
    (table,) = _labels(model, "no", LabelKind.CROSS_REFERENCE, "contacts")
    no, nc = contact_image(model, table)
    assert [entry[:6] for entry in no] == ["13-14 "]
    assert [entry[:6] for entry in nc] == ["21-22 "]


if TYPE_CHECKING:
    from fransys_model.kernel import Model
