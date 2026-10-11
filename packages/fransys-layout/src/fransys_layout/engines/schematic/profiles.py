"""One layout run per layout profile in use, spliced by drawing set (model-0192).

A unit's pages are drawn with that unit's own profile and never depend on the profile of the
design that contains it. The pass runs once for the top design's profile; each other profile that
a unit with drawings uses runs again on the same model, and the drawing sets of those units come
from their own run. When every profile is equal this is the single run it always was.
"""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.read.profile_runs import (
    finding_unit,
    profile_classes,
    unit_ranks,
)
from fransys_layout.engines.schematic.write.splice import drawn_units, spliced

if TYPE_CHECKING:
    from collections.abc import Callable

    from fransys_model.kernel import Finding, Id, Model

type Run = tuple[Model, tuple[Finding, ...]]


def lay_out(model: Model, run_once: Callable[[Model, Id[Any] | None], Run]) -> Run:
    """Lay out `model`: one `run_once` per profile in use, spliced by drawing set."""
    base, findings = run_once(model, None)
    classes = profile_classes(model, drawn_units(base))
    if not classes:
        return base, findings
    runs = [(frozenset(members), *run_once(model, members[0])) for members in classes]
    every = frozenset().union(*(units for units, _, _ in runs))
    kept = [f for f in findings if finding_unit(model, f) not in every]
    for units, _, run_findings in runs:
        kept += [f for f in run_findings if finding_unit(model, f) in units]
    merged = spliced(base, tuple((units, laid) for units, laid, _ in runs), unit_ranks(model))
    return merged, tuple(sorted(kept, key=lambda f: (f.code, f.subjects, f.message)))
