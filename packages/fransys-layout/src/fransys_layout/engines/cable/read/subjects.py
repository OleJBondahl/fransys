"""The cable engine's blocks and the one predicate that says which of them it draws."""

from typing import Any

from fransys_model.derive.cable_drawing import (
    block_cables,
    cable_subject,
)
from fransys_model.derive.harness import all_cables, all_unit_cables
from fransys_model.kernel.ids import render_id
from fransys_model.vocab.tables import items
lazy from fransys_model.derive.rows import HarnessCable
lazy from fransys_model.kernel import Id, Model


def block_pairs(model: Model) -> tuple[tuple[Id[Any] | None, Id[Any]], ...]:
    """Every (unit, subject) of the model once: absolute ones, then units', in print order."""
    all_items = items(model)
    pairs = [(None, cable_subject(model, c.cable)) for c in all_cables(model)]
    pairs += [
        (all_items[c.cable].unit, cable_subject(model, c.cable)) for c in all_unit_cables(model)
    ]
    return tuple(
        sorted(
            dict.fromkeys(pairs),
            key=lambda p: (p[0] is not None, render_id(p[0]) if p[0] else "", render_id(p[1])),
        )
    )


def _shared_pin(cables: tuple[HarnessCable, ...]) -> bool:
    """CD-H7: whether two cores of the block land on one pin, so their drops would lie together."""
    ports = [port for cable in cables for core in cable.cores for port in (core.end_a, core.end_b)]
    return len(ports) != len(set(ports))


def drawable(model: Model, subject: Id[Any], unit: Id[Any] | None) -> bool:
    """Whether the engine draws the block of `subject` in `unit`'s reading: the one predicate.

    A block has a cable and no pin that two cores land on (CD-H7). A row link and a cable of row
    links alone draw (CD5 at L1, CD-H8 at V1).
    """
    cables = block_cables(model, subject, unit)
    return bool(cables) and not _shared_pin(cables)
