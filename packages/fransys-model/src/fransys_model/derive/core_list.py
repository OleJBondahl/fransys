"""The core list: every core of every cable of one reading, with its ends (CO1-CO4, model-0214)."""

lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .cable_cores import cable_rows
from .core_pairs import core_pair_word, drawn_pairs
from .harness import cable_list_rows
from .open_cores import open_core_rows
from .rows_cores import CoreListRow


def _cable_core_rows(model: Model, cable: Id[Item], unit: Id[Unit] | None) -> list[CoreListRow]:
    """The rows of one cable by core number; a spare parked on a pin has it as `end_a`."""
    marks = drawn_pairs(model, cable)
    rows = [
        CoreListRow(
            cable=row.cable_designation,
            core=row.index,
            colour=row.colour,
            pair=core_pair_word(marks, row.index),
            end_a=row.end_a_designation,
            end_b=row.end_b_designation,
            note="",
        )
        for row in cable_rows(model, cable, unit=unit)
    ]
    rows += [
        CoreListRow(
            cable=row.cable_designation,
            core=row.index,
            colour=row.colour,
            pair=core_pair_word(marks, row.index),
            end_a=row.at_designation,
            end_b="",
            note="spare" if row.spare else "",
        )
        for row in open_core_rows(model, cable, unit=unit)
    ]
    return sorted(rows, key=lambda row: row.core)


def core_list_rows(model: Model, *, unit: Id[Unit] | None = None) -> tuple[CoreListRow, ...]:
    """One `CoreListRow` per core of every cable `cable_list_rows` lists, in its order.

    Cores sort by number within a cable. The ends are `cable_rows`' and `open_core_rows`' own texts.

    Args:
        model: The frozen model to read.
        unit: The unit whose own cables to list; `None` is the top-level ones.

    Raises:
        SchemaError: `unit` is no unit, or an item has no designation.
    """
    return tuple(
        row
        for listed in cable_list_rows(model, unit=unit)
        for row in _cable_core_rows(model, listed.cable, unit)
    )
