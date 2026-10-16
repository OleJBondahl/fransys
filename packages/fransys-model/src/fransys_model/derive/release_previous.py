"""The previous release and the pin source of a release, over the stored releases (model-0267)."""

from .release_order import release_order, same_version
from .revision_text import revision_text
lazy from .numbering_pins import NumberingPins
lazy from .release_order import ReleaseOrder
lazy from .rows_baseline import Listing, ReleaseIdentity, StoredRelease, StoredReleases

__all__ = ["pin_source", "pin_source_pins", "previous_release", "previous_release_listing"]


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


def previous_release_listing(stored: StoredReleases, identity: ReleaseIdentity) -> Listing | None:
    """The listing of `previous_release`, or `None` when there is no previous release."""
    previous = previous_release(stored, identity)
    return None if previous is None else previous.listing


def pin_source_pins(
    stored: StoredReleases, identity: ReleaseIdentity
) -> tuple[str, NumberingPins] | None:
    """The folder name and numbering of `pin_source`, or `None` when it has no numbering."""
    source = pin_source(stored, identity)
    if source is None or source.numbering is None:
        return None
    return source.folder, source.numbering
