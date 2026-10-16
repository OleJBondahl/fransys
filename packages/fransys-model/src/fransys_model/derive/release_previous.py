"""The previous release and the pin source of a release, over the stored releases (model-0267)."""

from .release_order import release_order, same_version
from .revision_text import revision_text
lazy from .release_order import ReleaseOrder
lazy from .rows_baseline import ReleaseIdentity, StoredRelease, StoredReleases

__all__ = ["pin_source", "previous_release"]


def _highest(
    candidates: tuple[StoredRelease, ...], ceiling: ReleaseOrder, *, inclusive: bool
) -> StoredRelease | None:
    """The first candidate of the highest `order` below `ceiling` (at it too when `inclusive`)."""
    best: StoredRelease | None = None
    for candidate in candidates:
        within = candidate.order <= ceiling if inclusive else candidate.order < ceiling
        if within and (best is None or candidate.order > best.order):
            best = candidate
    return best


def previous_release(stored: StoredReleases, identity: ReleaseIdentity) -> StoredRelease | None:
    """The stored release with the highest order strictly below `identity`'s, or `None`.

    Across versions (they run in parallel); the folder of `identity` itself is never a candidate.
    """
    own_folder = revision_text(identity.version, identity.revision)
    others = tuple(r for r in stored.releases if r.folder != own_folder)
    return _highest(others, release_order(identity.version, identity.revision), inclusive=False)


def pin_source(stored: StoredReleases, identity: ReleaseIdentity) -> StoredRelease | None:
    """The stored release of the same version at or below `identity`'s revision, with numbering.

    Same name and version only, unlike `previous_release`; a re-release may be its own source.
    """
    same = tuple(
        r
        for r in stored.releases
        if r.numbering is not None
        and same_version((r.identity.name, r.identity.version), (identity.name, identity.version))
    )
    return _highest(same, release_order(identity.version, identity.revision), inclusive=True)
