"""What a pin source says about a unit's items and its direct instances.

An instance is a row of `items` told apart by its key's last segment (`numbering_pins`).
`pipeline` reads the pin source from disk; derive decides each finding, this module collects.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import new_in_revision_findings, revision_findings
from fransys_model.kernel import Finding, Id, Severity
lazy from fransys_model.derive.numbering_pins import NumberingPins

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from fransys_model.kernel import Model
    from fransys_model.vocab import Unit


def new_findings(model: Model, sources: Mapping[Id[Unit], NumberingPins]) -> list[Finding]:
    """`new_in_revision` for every unit that has a pin source (`build(releases=)`)."""
    return [
        f for unit in sorted(sources) for f in new_in_revision_findings(model, unit, sources[unit])
    ]


def pin_findings(
    model: Model, unit: Id[Unit], source: tuple[Path, NumberingPins] | None
) -> list[Finding]:
    """The release's own pin findings, none without a pin source."""
    if source is None:
        return []
    return revision_findings(model, unit, source[1], source[0])


def with_warnings(raw: tuple[Finding, ...], l4: tuple[Finding, ...]) -> tuple[Finding, ...]:
    """`raw` plus the release checks' WARNINGs it lacks: the manifest lists them."""
    return (*raw, *(f for f in l4 if f.severity is Severity.WARNING and f not in raw))
