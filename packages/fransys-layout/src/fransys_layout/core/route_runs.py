"""The runs of a strip on a page: the terminals of one strip in one row, each run with the one tag it prints (STRIP-TAG-ONCE).

A run is placement's result, so the text stage stands it once the page is placed: the strip's `Annex` (owned by the strip id, sized by
the symdef layer) is copied per run and stands at the run's leftmost terminal like any tag; a terminal alone is a run of one.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .errors import CoreError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .annex_values import Annex, AnnexBox
    from .outputs import Demand, Placed, StripRun
    from .values import Finding, PlacementProblem

#: run key -> (the strip id its tag names, the run's leftmost terminal as placed: the body the tag stands at)
Runs = dict[str, "tuple[str, Placed]"]


def stand_runs(problem: PlacementProblem, placed: Mapping[str, Placed], runs: Sequence[StripRun]) -> tuple[tuple[Annex, ...], Runs]:
    """The strip annex of each run on the page, copied with the run's key as owner, and the key's strip and leftmost terminal.

    A run whose strip has no template annex raises: a strip tag is never skipped silently.
    """
    templates = {a.owner: a for a in problem.annexes}
    if (missing := next((r.strip for r in runs if templates.get(r.strip) is None), None)) is not None:
        msg = f"strip {missing}: its terminals stand in a run with no strip tag Annex owned by the strip; the builder gave none"
        raise CoreError(msg)
    stood: Runs = {r.key: (r.strip, placed[r.members[0]]) for r in runs}
    return tuple(replace(templates[r.strip], owner=r.key) for r in runs), stood


def named(
    runs: Mapping[str, tuple[str, Placed]], labels: Sequence[AnnexBox], found: Sequence[Finding], asks: Mapping[int, Demand]
) -> tuple[list[AnnexBox], list[Finding], dict[int, Demand]]:
    """The results of `place_labels` with each run's key given back as its strip (labels, findings) or its leftmost terminal (demands)."""
    labels = [replace(a, owner=runs[a.owner][0]) if a.owner in runs else a for a in labels]
    found = [replace(f, subject=runs[f.subject][0]) if f.subject is not None and f.subject in runs else f for f in found]
    return labels, found, {i: replace(d, owner=runs[d.owner][1].sym) if d.owner in runs else d for i, d in asks.items()}
