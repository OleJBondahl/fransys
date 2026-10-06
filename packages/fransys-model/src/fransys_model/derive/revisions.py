"""The revision history query: a unit release's or the project's own entries (U4, SC2)."""

from typing import TYPE_CHECKING

from fransys_model.vocab.tables import projects, revisions, unit_releases
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import UnitRelease
lazy from fransys_model.vocab.revision import Revision

from .lookups import require
from .release_order import release_order

if TYPE_CHECKING:
    from .release_order import ReleaseOrder


def _order(entry: Revision) -> tuple[str, ReleaseOrder, Id[Revision]]:
    """`(date, release order, id)`: total and deterministic (invariant 7).

    History sorts by date, then by the pair `release_order(version, revision)`, so revision `2`
    sorts before `10`.
    """
    return (entry.date, release_order(entry.version, entry.revision), entry.id)


def revision_history(model: Model, release: Id[UnitRelease] | None = None) -> tuple[Revision, ...]:
    """Every `Revision` of `release`, in date order, then version and revision order.

    `release=None` selects the project's own history: every entry with `Revision.release is None`.
    Every instance of a release shares the release's history. "Revision order" sorts by the ints
    `(version, revision)`, so revision 2 sorts before revision 10.

    Raises:
        SchemaError: `release` is not `None` and names no `UnitRelease` of `model`.
    """
    if release is not None:
        require(unit_releases(model).get(release), "unit_release", release)
    entries = [entry for entry in revisions(model).values() if entry.release == release]
    return tuple(sorted(entries, key=_order))


def current_revision(model: Model, release: Id[UnitRelease] | None = None) -> Revision | None:
    """The history entry that is `release`'s current revision, or the project's when `None`.

    Its own `(version, revision)` equals the release's (the `Project`'s for the project): the
    current revision, not merely the latest entry. `None` when no entry matches, and for the
    project when the model has no `Project` (there is no current revision to miss). The date a
    title block, the PDF metadata and the PDF's embedded timestamp print is this entry's `date`.
    Pure: `REVISION_CURRENT_MISSING` reports the gap.

    Raises:
        SchemaError: `release` is not `None` and names no `UnitRelease` of `model`.
    """
    if release is None:
        table = projects(model)
        if not table:
            return None
        current = next(iter(table.values()))
    else:
        current = require(unit_releases(model).get(release), "unit_release", release)
    wanted = (current.version, current.revision)
    return next(
        (
            entry
            for entry in revision_history(model, release)
            if (entry.version, entry.revision) == wanted
        ),
        None,
    )
