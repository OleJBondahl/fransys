"""The printed designation of each subject a finding names, read once for the last pass (V6b)."""

from typing import TYPE_CHECKING, Any

from fransys_layout.lint.naming import append_pages_and_designations, where_drawn
from fransys_model.derive import natural_key
from fransys_model.derive.designation import (
    function_designation,
    port_designation,
    printed_designation,
)
from fransys_model.kernel import SchemaError

from .location_paths import location_paths

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_layout.lint import HarnessInk
    from fransys_layout.stages.types import FunctionSpec, Layout
    from fransys_model.kernel import Finding, Id, Model

_NAMERS = (
    ("port", port_designation),
    ("function", function_designation),
    ("item", printed_designation),
)


def subject_names(model: Model, findings: Iterable[Finding]) -> dict[Id[Any], str]:
    """Each port, function or item subject of `findings` with its printed designation.

    The mapping lists its subjects by `natural_key` of that designation, never by `Id`: the
    naming pass lists a finding's members in this order.
    """
    found: dict[Id[Any], str] = {}
    for finding in findings:
        for subject in finding.subjects:
            for kind, namer in _NAMERS:
                if subject.kind == kind and subject not in found:
                    try:
                        found[subject] = namer(model, subject)
                    except SchemaError:
                        found[subject] = ""
    return dict(sorted(found.items(), key=lambda one: natural_key(one[1])))


def named_findings(
    model: Model,
    specs: Iterable[FunctionSpec],
    layout: Layout,
    ink: HarnessInk,
    findings: Iterable[Finding],
) -> tuple[Finding, ...]:
    """The findings ending in their pages and designations, read from `model` (lint/naming.py)."""
    found = tuple(findings)
    labels = {
        number: tuple(label for _, label in path)
        for number, path in location_paths(model, layout.pages).items()
    }
    where = where_drawn(layout, specs, ink, labels)
    return append_pages_and_designations(subject_names(model, found), where, found)
