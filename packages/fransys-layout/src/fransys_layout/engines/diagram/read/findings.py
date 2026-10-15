"""The diagram facts of a reading as kernel `Finding`s, with the one severity map."""

from typing import Any

from fransys_model.derive.block_diagram import (
    DIAGRAM_CABLE_FANOUT,
    DIAGRAM_CABLE_ONE_BOX,
    DIAGRAM_LOOSE_WIRE,
    diagram_facts,
)
from fransys_model.kernel import Finding, Severity, render_id
lazy from fransys_model.kernel import Id, Model


def _make(code: str, severity: Severity, message: str, subject: Id[Any]) -> Finding:
    return Finding(code=code, severity=severity, subjects=(subject,), message=message)


def _one_box(subject: Id[Any]) -> Finding:
    message = "The cable reaches one box or none, so the diagram draws no line for it."
    return _make(DIAGRAM_CABLE_ONE_BOX, Severity.INFO, message, subject)


def _fanout(subject: Id[Any]) -> Finding:
    message = (
        "The cable reaches three or more boxes, drawn as one line from the first to each other."
    )
    return _make(DIAGRAM_CABLE_FANOUT, Severity.INFO, message, subject)


def _loose_wire(subject: Id[Any]) -> Finding:
    message = "A wire with no cable joins two boxes and is not drawn."
    return _make(DIAGRAM_LOOSE_WIRE, Severity.INFO, message, subject)


_BUILDERS = frozendict(
    {
        DIAGRAM_CABLE_ONE_BOX: _one_box,
        DIAGRAM_CABLE_FANOUT: _fanout,
        DIAGRAM_LOOSE_WIRE: _loose_wire,
    }
)


def reading_findings(model: Model, unit: Id[Any] | None) -> tuple[Finding, ...]:
    """The findings of `unit`'s diagram, one per fact."""
    return tuple(_BUILDERS[fact.code](fact.subject) for fact in diagram_facts(model, unit))


DIAGRAM_COLUMN_TOO_TALL = "DIAGRAM_COLUMN_TOO_TALL"


def too_tall_finding(
    unit: Id[Any] | None, cable: Id[Any], column: int, boxes: int, fit: int
) -> Finding:
    """The detail of a diagram that gets no page: its tallest column holds more boxes than fit."""
    name = "The system diagram" if unit is None else f"The diagram of unit {render_id(unit)}"
    message = (
        f"{name} is not drawn: column {column} holds {boxes} boxes and one sheet holds {fit}. "
        "This is a known limit of the system diagram."
    )
    return _make(DIAGRAM_COLUMN_TOO_TALL, Severity.INFO, message, cable)
