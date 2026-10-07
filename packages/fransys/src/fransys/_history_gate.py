"""`RELEASE_HISTORY_UNRELEASED` (WORKFLOW-BLOCKS W7): a history entry names an unreleased revision.

The cutoff is the first entry, in `derive.revision_history`'s order, that names a released
revision. Entries before it are free text. Each later entry names a folder of its own version
under the release root, or the revision being released.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import revision_history, revision_text, unit_release
from fransys_model.kernel import Finding, Id, Severity

from ._release_reader import released_revisions

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_model.kernel import Model
    from fransys_model.vocab import Unit as ModelUnit
    from fransys_model.vocab import UnitRelease


def _unreleased(
    model: Model,
    release_id: Id[UnitRelease] | None,
    released: frozenset[tuple[int, int]],
    current: tuple[int, int],
) -> list[tuple[int, int]]:
    """The `(version, revision)` of each entry after the cutoff that has no folder."""
    pairs = [(entry.version, entry.revision) for entry in revision_history(model, release_id)]
    cutoff = next((i for i, pair in enumerate(pairs) if pair in released), None)
    if cutoff is None:
        return []
    return [pair for pair in pairs[cutoff + 1 :] if pair not in released and pair != current]


def history_findings(
    model: Model,
    unit: Id[ModelUnit] | None,
    *,
    name: str,
    current: tuple[int, int],
    parent: Path,
) -> list[Finding]:
    """One `RELEASE_HISTORY_UNRELEASED` `ERROR` per entry that names a never-released revision.

    `unit=None` is the system release and reads the project's own history.
    """
    release_id = None if unit is None else unit_release(model, unit).id
    bad = _unreleased(model, release_id, released_revisions(parent), current)
    return [
        Finding(
            code="RELEASE_HISTORY_UNRELEASED",
            severity=Severity.ERROR,
            subjects=() if unit is None else (unit,),
            message=(
                f"{name} {revision_text(*current)}: history entry {revision_text(*pair)} names "
                "a revision that was never released"
            ),
        )
        for pair in bad
    ]
