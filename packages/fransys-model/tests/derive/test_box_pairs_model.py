"""model-0130: which function of another item a function is wired to point to point."""

from plant import Plant

from fransys_model.derive import box_pairs
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.core import Port


def _group(plant: Plant, item: str, function: str, *names: str) -> list[Id[Port]]:
    """The ports `names` of `item`'s `function`."""
    return [plant.pin(item, function, name) for name in names]


def _wire(plant: Plant, ones: list[Id[Port]], twos: list[Id[Port]]) -> None:
    """One wire per pair of ports, in order."""
    for index, (one, two) in enumerate(zip(ones, twos, strict=True)):
        plant.wire(one, two, key=f"w-{index}-{one}-{two}")


def _paired_plant() -> tuple[Plant, list[Id[Port]], list[Id[Port]]]:
    """A source `psu` output group wired + to 1+ and - to 1- of module `red`'s input group."""
    plant = Plant()
    out = _group(plant, "psu", "out", "+", "-")
    inp = _group(plant, "red", "in1", "1+", "1-")
    _wire(plant, out, inp)
    return plant, out, inp


def test_a_group_wired_one_to_one_to_one_group_is_paired_both_ways() -> None:
    """Each end names the other and its port pairs, (own port, partner port)."""
    plant, out, inp = _paired_plant()
    pairs = box_pairs(plant.model())
    fed, feeder = Plant.function_id("red", "in1"), Plant.function_id("psu", "out")
    assert pairs[fed].partner == feeder
    assert pairs[feeder].partner == fed
    assert set(pairs[fed].port_pairs) == set(zip(inp, out, strict=True))
    assert set(pairs[feeder].port_pairs) == set(zip(out, inp, strict=True))


def test_two_feeders_leave_the_group_unpaired() -> None:
    """Each of the group's ports reaches a different item: no one feeder."""
    plant = Plant()
    inp = _group(plant, "red", "in1", "1+", "1-")
    first = _group(plant, "psu1", "out", "+", "-")
    second = _group(plant, "psu2", "out", "+", "-")
    _wire(plant, inp, [first[0], second[0]])
    assert Plant.function_id("red", "in1") not in box_pairs(plant.model())


def test_a_split_group_leaves_the_group_unpaired() -> None:
    """The ports reach two functions of one item: not one function."""
    plant = Plant()
    inp = _group(plant, "red", "in1", "1+", "1-")
    plus = _group(plant, "psu", "plus", "+")
    minus = _group(plant, "psu", "minus", "-")
    _wire(plant, inp, plus + minus)
    assert Plant.function_id("red", "in1") not in box_pairs(plant.model())


def test_a_third_member_on_either_side_leaves_the_group_unpaired() -> None:
    """A third pin on the feeder, or on the fed group, breaks the one to one."""
    plant, _, _ = _paired_plant()
    plant.pin("psu", "out", "ok")
    assert box_pairs(plant.model()) == {}
    plant2, _, _ = _paired_plant()
    plant2.pin("red", "in1", "1x")
    assert box_pairs(plant2.model()) == {}


def test_a_net_of_three_ports_leaves_the_group_unpaired() -> None:
    """A third port on one net: not a two-port net."""
    plant, out, _ = _paired_plant()
    extra = plant.pin("other", "f", "1")
    plant.wire(out[0], extra, key="extra")
    assert box_pairs(plant.model()) == {}


def test_a_function_wired_to_itself_or_its_own_item_is_not_paired() -> None:
    """The partner is a function of another item."""
    plant = Plant()
    one = _group(plant, "box", "f1", "a", "b")
    two = _group(plant, "box", "f2", "a", "b")
    _wire(plant, one, two)
    assert box_pairs(plant.model()) == {}
