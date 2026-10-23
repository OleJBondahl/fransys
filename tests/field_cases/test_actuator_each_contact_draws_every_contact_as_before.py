"""Field case: with nothing set, every contact of a device draws its own actuator, as in 0.18.6.

The engineering shape: the guide's emergency-stop head `S1` with two contact blocks (11-12 and
21-22) joined to it with `parent=`, each in its own terminal-to-terminal circuit.

The need: ACTUATOR-ONCE draws one actuator per device and gives the other contacts a reference.
The owner chose the 0.18.6 look as the house default (amendment 3, 2026-10-14): a design that wants
one actuator per device sets `d.layout.profile(actuator_each_contact=False)`.

Fixing decisions: model-0252 (the Profile field, default True), layout-0254 (the choice) and
ACTUATOR-ONCE AO7.
Invented parts from `demo_parts`: `DEMO-HEAD-ESTOP`, `DEMO-BLOCK-1NC` and `DEMO-BLOCK-1NC-21`.
The symbols the core path draws for the example are the ones the build drew before ACTUATOR-ONCE:
a mushroom actuator for each of the two contact blocks.
"""

from collections import Counter
from typing import TYPE_CHECKING

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model


def _model(*, one_per_device: bool = False, choice: str | None = None) -> tuple[Model, Id]:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="E-stop", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    if one_per_device:
        d.layout.profile(actuator_each_contact=False)
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    s1 = d.device("S1", "DEMO-HEAD-ESTOP")
    first = d.device(None, "DEMO-BLOCK-1NC", name="nc-1", parent=s1)
    second = d.device(None, "DEMO-BLOCK-1NC-21", name="nc-2", parent=s1)
    if choice is not None:
        d.layout.symbol(second, choice)
    second_id = second.id
    wire = (BU, 0.5)
    d.detail.wire(strip[1], first["11"], wire=wire)
    d.detail.wire(first["12"], strip[2], wire=wire)
    d.detail.wire(strip[3], second["21"], wire=wire)
    d.detail.wire(second["22"], strip[4], wire=wire)
    return fr.build(d, cabinet_document(cabinet)).model, second_id


def _drawn(*, one_per_device: bool = False, choice: str | None = None) -> Counter[str]:
    """The library symbol keys the core path draws for the head example, with their counts."""
    model, _ = _model(one_per_device=one_per_device, choice=choice)
    return Counter(one.key for d in drawn_pages(model).values() for one in d.symbols)


def test_nothing_set_draws_the_head_example_as_it_was_before_one_actuator_per_device() -> None:
    """With nothing set, each contact block draws its own mushroom actuator, as before Part 1."""
    assert _drawn() == {"terminal": 4, "emergency-stop": 2}


def test_false_draws_one_actuator_per_device() -> None:
    """With the field False, the second block draws a plain break contact, not the mushroom."""
    assert "break-contact-positive-opening" in _drawn(one_per_device=True)
    assert "break-contact-positive-opening" not in _drawn()


def test_each_contact_keeps_a_symbol_chosen_for_one_contact() -> None:
    """With nothing set, the contact with `d.layout.symbol` draws the chosen symbol."""
    assert "make-contact" in _drawn(choice="make-contact")
