"""V8: a wire's two ends come in one fixed order, never the order the script authored them."""

from plant import Plant
from query_builders import make_labelled, make_strip, ports_against_ids

from fransys_model.derive import wire_rows


def _row(first: str, second: str, *, with_strip: bool = False):
    """The one wire row of a plant whose wire is authored `first` to `second`."""
    plant = Plant()
    ports = ports_against_ids(plant, 2)  # K1, K2: the ids run against the designations
    ends = {"a": ports[1], "b": ports[0]}
    if with_strip:
        make_strip(plant)
        terminal = next(r.id for r in plant.records if getattr(r, "name", "") == "external")
        ends["t"] = terminal
    make_labelled(plant, "w", ends[first], ends[second], None)
    (row,) = wire_rows(plant.model())
    return row


def test_a_wire_authored_b_to_a_gives_the_row_and_label_of_a_to_b() -> None:
    forward, backward = _row("a", "b"), _row("b", "a")
    assert forward == backward
    assert (forward.from_, forward.to, forward.label) == ("-K1:1", "-K2:1", "-K1:1 -K2:1")


def test_a_terminal_end_comes_first_whatever_the_authored_order() -> None:
    forward, backward = _row("a", "t", with_strip=True), _row("t", "a", with_strip=True)
    assert forward == backward
    assert forward.from_.startswith("-X1:")
