"""D3 step 6: a power symbol's text is one `POWER` text through `place_texts`, subject the port.

On the invented plant of `power_fixture` (four pages, eleven power ends) each symbol with a
text has one `MARKING` label whose subject is the port; protective earth has no text and no label.
"""

from power_fixture import power_run

from fransys_layout.geometry import overlaps
from fransys_layout.stages import LabelKind
from fransys_layout.stages.texts.power import power_places
from fransys_model.layout import POWER_SLOT


def _layout():
    return power_run()[2].layout


def _power_labels():
    return [one for one in _layout().labels if one.slot == POWER_SLOT]


def test_each_symbol_with_a_text_has_one_marking_label_on_its_port() -> None:
    """UNDO: in `with_power_labels` return `labels, ()`: no power label is left."""
    wanted = sorted(
        (one.port, one.drawing_set, one.page) for one in power_places(_layout().markers) if one.text
    )
    found = sorted((one.subject, one.drawing_set, one.page) for one in _power_labels())
    assert wanted
    assert found == wanted
    assert {one.kind for one in _power_labels()} == {LabelKind.MARKING}


def test_protective_earth_has_no_label() -> None:
    """UNDO: in `with_power_labels` drop the `if one.text` filter: PE gets an empty label."""
    earth = {
        one.port for one in power_places(_layout().markers) if one.symbol == "protective-earth"
    }
    assert earth
    assert not earth & {one.subject for one in _power_labels()}


def test_the_texts_are_the_nets_names_and_land_free() -> None:
    """The label is placed, clear of its own symbol's body and of every other power label.

    UNDO: in `with_power_labels` drop the power bodies from `shapes`: a text sits on a body.
    """
    labels = _power_labels()
    assert all(not one.unplaced for one in labels)
    bodies = {one.port: one.body for one in power_places(_layout().markers)}
    assert all(not overlaps(one.box, bodies[one.subject]) for one in labels)
    boxes = [(one.drawing_set, one.page, one.box) for one in labels]
    for i, (s, p, box) in enumerate(boxes):
        assert all(not overlaps(box, other) for t, q, other in boxes[i + 1 :] if (t, q) == (s, p))
