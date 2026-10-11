"""Wire rows and a terminal's far ends print in natural order: `-X1:L:2` before `-X1:L:10`."""

from plant import Plant
from query_builders import make_labelled, make_pin, make_strip, make_terminal

from fransys_model.derive import terminal_rows, wire_rows


def test_wire_rows_sort_terminal_ends_by_digit_runs() -> None:
    plant = Plant()
    plant.item("x1", designation="X1")
    for index in (10, 2, 11, 3):
        terminal = make_terminal(plant, "x1", f"t{index}", group="L", index=index)
        make_labelled(
            plant, f"w{index}", terminal.internal, make_pin(plant, f"p{index}", "K1"), None
        )
    rows = wire_rows(plant.model())
    assert [row.from_ for row in rows] == [f"-X1:L:{n}" for n in (2, 3, 10, 11)]


def test_a_terminals_far_ends_sort_by_digit_runs_and_stay_paired() -> None:
    plant = Plant()
    strip, _ = make_strip(plant)
    hub = make_terminal(plant, "x1", "t-hub", group="P", index=1)
    numbers = (10, 2, 11, 1, 3)
    for n in numbers:
        plant.wire(make_pin(plant, f"far{n}", f"Q{n}"), hub.internal, key=f"hub{n}")
    (row,) = (r for r in terminal_rows(plant.model(), strip) if r.designation == "-X1:P:1")
    assert row.internal_ends == tuple(f"-Q{n}:1" for n in sorted(numbers))
    assert len(row.internal) == len(row.internal_ends)
