"""`unit_cables`' blanking of an outside end's facts (decision wireviz-0010, order BLANK-END).

`test_unit_cables_unit_relative.py` covers `_end_designation`'s own blanking of an outside end's
`designation` text to `""` (decision model-0090). This file covers the rest of `_end`
(`derive/harness.py`): the same `end_outside_nested_unit` gate also blanks `connector`, `style`,
`pincount`, `gender` and `mpn` to `None` and every landed pin's `marking` to `""`, while the
pin's `port` is kept so the cable still wires to it (decision wireviz-0010, "a blank end prints
no fact at all"). The owner's rule is "a unit's drawing shows nothing above the unit": a device
outside the nested unit `hu` keeps its real connector shape in the absolute reading
(`harness_cables`) and loses every fact but the wiring itself in `hu`'s own reading
(`unit_cables`).
"""

from connector_builders import make_connector
from plant import Plant
from query_builders import make_core, make_part

from fransys_model.derive import harness_cables, unit_cables
from fransys_model.kernel import make_id
from fransys_model.vocab.enums import Gender
from fransys_model.vocab.facets.cable import CableFacet


def test_an_outside_ends_facts_and_pin_markings_are_blank_in_the_unit_reading() -> None:
    """Owner's rule "a unit's drawing shows nothing above the unit" (model-0090, order
    BLANK-END)."""
    plant = Plant()
    cabinet = plant.unit("cabinet", name="cabinet")
    hu = plant.unit("hu", name="hu", parent=cabinet)
    wh1 = plant.item("wh1", designation="WH1", unit=hu)
    plug = plant.item("x1", designation="X1", parent=wh1, unit=hu)
    plug_function = plant.function(plug, "f")
    plug_pin_1 = plant.port(plug_function, "1")
    plug_pin_2 = plant.port(plug_function, "2")
    m1_part = make_part(plant, "m1-part", "SIM-M1-MPN")
    m1 = plant.item("m1", designation="M1", part=m1_part)
    _m1_function, ports = make_connector(plant, ("m1", "p1"), ("1", "2"))
    w1 = plant.item("w1", designation="W1", parent=wh1, unit=hu)
    plant.add(
        CableFacet(
            id=make_id(CableFacet, ("w1", "cable")),
            key=("w1", "cable"),
            subject=w1,
            length_mm=None,
        )
    )
    make_core(plant, "core-1", w1, (plug_pin_1, ports["1"]), index=1)
    make_core(plant, "core-2", w1, (plug_pin_2, ports["2"]), index=2)
    model = plant.model()

    (cable,) = unit_cables(model, hu)
    end = next(end for end in cable.ends if end.item == m1)
    assert (end.connector, end.style, end.pincount, end.gender, end.mpn) == (
        None,
        None,
        None,
        None,
        None,
    )
    assert end.designation == ""
    assert [pin.marking for pin in end.pins] == ["", ""]
    assert {pin.port for pin in end.pins} == {ports["1"], ports["2"]}

    (absolute_cable,) = harness_cables(model, wh1)
    absolute_end = next(end for end in absolute_cable.ends if end.item == m1)
    assert absolute_end.style == "header"
    assert absolute_end.pincount == 2
    assert absolute_end.gender is Gender.MALE
    assert absolute_end.mpn == "SIM-M1-MPN"
    assert absolute_end.connector is not None
    assert sorted(pin.marking for pin in absolute_end.pins) == ["1", "2"]
