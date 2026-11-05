"""`derive.far_pins`: the far port of each conductor at a set of ports, lowest far port first."""

from plant import Plant
from query_builders import make_pin

from fransys_model.derive import far_pins, port_designation, stub_far


def _three_pins():
    plant = Plant()
    near, high, low, lone = (make_pin(plant, k, k.upper()) for k in ("n", "h", "l", "o"))
    plant.wire(near, high, key="to-high")
    plant.wire(low, near, key="to-low")
    return plant.model(), near, high, low, lone


def test_each_conductor_at_a_near_port_gives_its_far_port_by_stub_far_order() -> None:
    model, near, high, low, _ = _three_pins()
    assert far_pins(model, [near]) == ((near, high), (near, low))


def test_a_port_no_conductor_reaches_gives_no_pair() -> None:
    model, _, _, _, lone = _three_pins()
    assert far_pins(model, [lone]) == ()


def test_a_conductor_between_two_near_ports_gives_both_directions() -> None:
    model, near, high, _, _ = _three_pins()
    assert (near, high) in far_pins(model, [near, high])
    assert (high, near) in far_pins(model, [near, high])


def test_stub_far_names_the_first_pair() -> None:
    model, near, _, _, _ = _three_pins()
    found = stub_far(model, [near])
    assert (found[0][0], found[0][1]) == far_pins(model, [near])[0]


def test_stub_far_names_the_far_end_it_is_given_and_none_that_is_no_reach() -> None:
    """R1581: a stub end names its conductor, the last one included, whatever the first by designation is."""
    model, near, _, _, lone = _three_pins()
    _, second = far_pins(model, [near])
    found = stub_far(model, [near], [second[1]])
    assert [(end[0], end[1]) for end in found] == [second]
    assert stub_far(model, [near], [lone]) == ()


def _far_designations(suffix: str) -> list[str]:
    plant = Plant()
    near = make_pin(plant, "n" + suffix, "N")
    for k in "abcd":
        plant.wire(near, make_pin(plant, k + suffix, k.upper()), key="to-" + k + suffix)
    model = plant.model()
    return [port_designation(model, far) for _, far in far_pins(model, [near])]


def test_far_ends_print_in_designation_order_whatever_their_id_order() -> None:
    """model-0424: key salts that swap the far ports' id order give the same printed order."""
    printed = {tuple(_far_designations(str(n))) for n in range(8)}
    assert len(printed) == 1
    (only,) = printed
    assert len(only) == 4
    assert list(only) == sorted(only)
