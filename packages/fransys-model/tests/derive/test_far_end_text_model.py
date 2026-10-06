"""FAR-END-ONE-HOME A1: `far_end` is the one whole-path text of an end, `(head, tail)`.

The off stub prints it whole (`stub_far_end`); the lists print `head + tail` below a context.
"""

from connector_builders import make_connector
from plant import Plant
from query_builders import make_node, make_placement, make_terminal

from fransys_model.derive.drawing_text import far_end, port_designation_in, stub_far_end
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.aspects import AspectNode


def _located() -> tuple[Plant, tuple[Id[AspectNode], Id[AspectNode]]]:
    plant = Plant()
    c1, ext = make_node("c1", None), make_node("ext", None)
    plant.add(c1, ext)
    return plant, (c1.id, ext.id)


def test_a_terminal_heads_with_its_strip_and_tails_with_its_name() -> None:
    plant, (c1, _ext) = _located()
    strip = plant.item("x1", designation="X1")
    plant.add(make_placement("x1-loc", strip, c1))
    terminal = make_terminal(plant, "x1", "t1", group="L", index=1)
    port = terminal.external
    assert far_end(plant.model(), port) == ("+C1-X1", ":L:1")


def test_a_plain_device_pin_heads_with_the_device() -> None:
    plant, (_c1, ext) = _located()
    motor = plant.item("m1", designation="M1")
    port = plant.port(plant.function(motor, "f"), "U1")
    plant.add(make_placement("m1-loc", motor, ext))
    assert far_end(plant.model(), port) == ("+EXT-M1", ":U1")


def test_a_connector_pin_heads_with_the_device_and_its_connector() -> None:
    plant, (_c1, ext) = _located()
    unit = plant.item("u2", designation="U2")
    plant.add(make_placement("u2-loc", unit, ext))
    _, x1 = make_connector(plant, ("u2", "X1"), ("1",))
    make_connector(plant, ("u2", "X2"), ("1",))
    assert far_end(plant.model(), x1["1"]) == ("+EXT-U2-X1", ":1")


def test_a_two_function_device_keeps_the_function_segment_in_the_head() -> None:
    plant, (_c1, ext) = _located()
    plant.add(make_placement("u2-loc", plant.item("u2", designation="U2"), ext))
    _, x1 = make_connector(plant, ("u2", "X1"), ("1",))
    _, x2 = make_connector(plant, ("u2", "X2"), ("1",))
    model = plant.model()
    assert far_end(model, x1["1"])[0] != far_end(model, x2["1"])[0]
    assert far_end(model, x2["1"]) == ("+EXT-U2-X2", ":1")


def test_the_stub_and_the_list_read_the_same_text() -> None:
    plant, (_c1, ext) = _located()
    motor = plant.item("m1", designation="M1")
    port = plant.port(plant.function(motor, "f"), "U1")
    plant.add(make_placement("m1-loc", motor, ext))
    model = plant.model()
    assert stub_far_end(model, port) == far_end(model, port)
    assert "".join(stub_far_end(model, port)) == port_designation_in(model, port, None)
