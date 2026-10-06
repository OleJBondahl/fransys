"""UT4: the numbering pins cover unit instances as they cover items."""

from plant import Plant

from fransys_model.derive.numbering_pins import dumps, loads, pins, unit_position
from fransys_model.derive.passes.numbering import number
from fransys_model.derive.rows import NumberingItem, NumberingPins
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Unit


def _cabinet() -> Plant:
    plant = Plant()
    cab = plant.unit("cab", name="cabinet")
    plant.unit("a", name="board", class_code="U", parent=cab, tag="U7")
    plant.unit("b", name="board", class_code="U", parent=cab)
    plant.unit("c", name="plain", parent=cab)
    return plant


def test_pins_hold_a_row_per_tagged_instance_directly_inside_the_unit() -> None:
    model, _ = number(_cabinet().model())
    rows = pins(model, make_id(Unit, ("cab",))).items
    assert rows == (
        NumberingItem(key=("a",), scope=None, code="U", text="U7", authored=True),
        NumberingItem(key=("b",), scope=None, code="U", text="U1", authored=False),
    )


def test_an_instance_with_no_tag_has_no_row_and_the_container_itself_none() -> None:
    plant = _cabinet()
    assert pins(plant.model(), make_id(Unit, ("cab",))).items[0].key == ("a",)
    assert len(pins(plant.model(), make_id(Unit, ("cab",))).items) == 1
    assert pins(plant.model(), make_id(Unit, ("a",))).items == ()


def test_the_unit_position_is_the_key_below_the_parent_with_the_class_code() -> None:
    model = _cabinet().model()
    assert unit_position(model, make_id(Unit, ("a",))) == (("a",), None, "U")
    assert unit_position(model, make_id(Unit, ("c",))) == (("c",), None, None)


def test_instance_rows_round_trip_and_an_old_file_still_loads() -> None:
    model, _ = number(_cabinet().model())
    written = pins(model, make_id(Unit, ("cab",)))
    assert loads(dumps(written)) == written
    assert loads(dumps(NumberingPins(items=(), retired=()))).items == ()
