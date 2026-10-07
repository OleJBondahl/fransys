"""A harness block's single wires as drawn cores (HA-H1 A1): the facts `cable_drawing` counts.

Private to `cable_drawing`, which re-exports the three public names (model-0159). A wire is a
core of the block, with no cable box: it lands on the same pin cells and end boxes as a cable core.
"""

from fransys_model.kernel import Id, Model, value
from fransys_model.vocab.tables import conductors, items
from fransys_model.vocab.wire_harness import harnesses_with_wires
lazy from fransys_model.vocab import Conductor, Item, Port, Unit

from .drawing_text import wire_text
from .harness import _ends, _facts_of
from .harness_wires import harness_wires
from .wire_ends import ordered_wire_ends
lazy from .rows import HarnessCore, HarnessEnd


@value
class DrawnWire:
    """One single wire of a harness block: its conductor, place, two ends and key text.

    `index` counts the harness's wires from 1. `text` is the one wire key: label, colour when
    set, then `<gauge> mm²`.
    """

    conductor: Id[Conductor]
    index: int
    end_a: Id[Port]
    end_b: Id[Port]
    text: str


def block_wires(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> tuple[DrawnWire, ...]:
    """The single wires of harness `subject` in `unit`'s reading, empty when it has none.

    A unit's reading holds the harnesses of that unit; `None` is the absolute reading. The
    wires are `harness_wires`' own, in its order, each text the wire key of `unit`'s reading.
    """
    if subject not in harnesses_with_wires(model):
        return ()
    if unit is not None and items(model)[subject].unit != unit:
        return ()
    found = []
    for index, row in enumerate(harness_wires(model, subject), 1):
        record = conductors(model)[row.conductor]
        end_a, end_b = ordered_wire_ends(model, record.a, record.b)
        key = " ".join(
            part
            for part in (
                wire_text(model, row.conductor, unit=unit),
                row.colour,
                f"{row.cross_section_mm2} mm²",
            )
            if part
        )
        found.append(
            DrawnWire(conductor=row.conductor, index=index, end_a=end_a, end_b=end_b, text=key)
        )
    return tuple(found)


def wire_harness_subjects(model: Model) -> tuple[Id[Item], ...]:
    """The harnesses that have single wires, sorted: the extra blocks layout lists."""
    return tuple(sorted(harnesses_with_wires(model)))


def wire_cores(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> tuple[HarnessCore, ...]:
    """The block's wires as `HarnessCore`s, so the cores' helpers count them as cores."""
    return tuple(
        HarnessCore(
            conductor=wire.conductor,
            index=wire.index,
            colour="",
            label=None,
            end_a=wire.end_a,
            end_a_designation="",
            end_b=wire.end_b,
            end_b_designation="",
        )
        for wire in block_wires(model, subject, unit)
    )


def wire_ends(model: Model, subject: Id[Item], unit: Id[Unit] | None) -> tuple[HarnessEnd, ...]:
    """The ends the block's wires land on, read as a cable's ends are (connector function)."""
    cores = wire_cores(model, subject, unit)
    return _ends(model, cores, _facts_of(model, unit)) if cores else ()
