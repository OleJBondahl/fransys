"""Diagram engine, reading: the model's block-diagram facts to facts and findings (BD3).

The only place, with `write/`, where the diagram engine meets the model vocabulary.
"""

from fransys_layout.engines.diagram.read.facts import diagram_reading
from fransys_layout.engines.diagram.read.findings import reading_findings
from fransys_layout.engines.diagram.read.readings import readings
lazy from fransys_layout.engines.diagram.values import DiagramFacts
lazy from fransys_model.kernel import Finding, Model

__all__ = ("read_diagrams", "read_findings")


def read_diagrams(model: Model) -> tuple[DiagramFacts, ...]:
    """One `DiagramFacts` per reading that has a line: the system first, then each unit instance."""
    found = (diagram_reading(model, unit) for unit in readings(model))
    return tuple(facts for facts in found if facts is not None)


def read_findings(model: Model) -> tuple[Finding, ...]:
    """The diagram findings of every reading, system and units, sorted by code and subjects."""
    found = (finding for unit in readings(model) for finding in reading_findings(model, unit))
    return tuple(sorted(found, key=lambda f: (f.code, f.subjects)))
