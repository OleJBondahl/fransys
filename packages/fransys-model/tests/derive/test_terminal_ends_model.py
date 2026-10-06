"""Tests for `TerminalRow.internal_ends` and `external_ends` (design/derive-queries.md)."""

import pytest
from plant import Plant
from query_builders import make_pin, make_strip, make_terminal, reversed_tables

from fransys_model.derive import TerminalRow, terminal_rows
from fransys_model.kernel import Id, SchemaError, make_id
from fransys_model.vocab.connectivity import Conductor


def _wire(key: str) -> Id[Conductor]:
    """The id of the conductor `Plant.wire` makes under `key`."""
    return make_id(Conductor, (key,))


def _rows() -> dict[str, TerminalRow]:
    plant = Plant()
    strip, _ = make_strip(plant)
    return {row.designation: row for row in terminal_rows(plant.model(), strip)}


def test_each_end_names_the_far_port_and_lines_up_with_its_conductor() -> None:
    """`L:1` has a jumper to `L:2` and a panel wire to `K1:1` inside, a field wire to `B1:1`."""
    row = _rows()["-X1:L:1"]
    ends = dict(zip(row.internal, row.internal_ends, strict=True))
    assert ends == {
        _wire("x1-jumper"): "-X1:L:2",
        _wire("x1-panel-a"): "-K1:1",
    }
    assert dict(zip(row.external, row.external_ends, strict=True)) == {_wire("x1-field-a"): "-B1:1"}


def test_a_jumpers_far_end_is_the_other_terminals_port() -> None:
    """The jumper seen from `L:2` ends at `L:1`, the same conductor seen from the other side."""
    row = _rows()["-X1:L:2"]
    assert (row.internal, row.internal_ends) == ((_wire("x1-jumper"),), ("-X1:L:1",))


def test_an_unused_terminal_has_empty_ends() -> None:
    """`N:1` has no conductor, so no end on either side."""
    row = _rows()["-X1:N:1"]
    assert (row.internal, row.external, row.internal_ends, row.external_ends) == ((), (), (), ())


def test_a_terminal_with_no_external_wire_has_empty_external_ends() -> None:
    """`L:2` has only its jumper: `external` and `external_ends` are both empty."""
    row = _rows()["-X1:L:2"]
    assert (row.external, row.external_ends) == ((), ())


def test_ends_and_conductors_have_one_length_per_role_for_every_row() -> None:
    """The alignment holds everywhere: one end per conductor, per role."""
    for row in _rows().values():
        assert len(row.internal_ends) == len(row.internal)
        assert len(row.external_ends) == len(row.external)


def test_a_conductor_between_a_terminals_own_two_ports_ends_at_its_other_port() -> None:
    """Listed under both roles, each time the far end is the port on the other role."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    terminal = make_terminal(plant, "x1", "t", group="L", index=1)
    plant.wire(terminal.internal, terminal.external, key="short")
    (row,) = terminal_rows(plant.model(), strip)
    assert (row.internal_ends, row.external_ends) == (("-X1:L:1",), ("-X1:L:1",))


def test_the_ends_do_not_depend_on_table_order() -> None:
    """The tables backwards, under another digest, give the same rows."""
    plant = Plant()
    strip, _ = make_strip(plant)
    model = plant.model()
    assert terminal_rows(reversed_tables(model), strip) == terminal_rows(model, strip)


def test_a_far_end_on_an_item_without_a_designation_raises() -> None:
    """The end is rendered, so its item needs a designation."""
    plant = Plant()
    strip = plant.item("x1", designation="X1")
    terminal = make_terminal(plant, "x1", "t", group="L", index=1)
    plant.wire(make_pin(plant, "field", None), terminal.external, key="w")
    with pytest.raises(SchemaError):
        terminal_rows(plant.model(), strip)
