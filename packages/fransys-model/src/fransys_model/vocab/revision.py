"""Vocabulary: a unit release's or the project's revision history (units spec U4, SC2)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record

from .core import UnitRelease
from .release_version import refuse_below_one


@record(kind="revision")
class Revision:
    """One entry of a unit release's or the project's revision history (units spec U4, SC2).

    `release=None` is the project's own history; a set `release` is that release's own history,
    shared by every instance of it, not any unit nested in or under it. `version` and `revision`
    together name the entry (FD4); both are ints of 1 or more, refused when the record is made
    (`release_version`), and print as `derive.revision_text`. `created`, `checked` and `approved`
    are the initials of who made, checked and approved the revision; an empty `checked` or
    `approved` means not yet done. Authoring key: `(*release_key, "revision", str(version),
    str(revision))` for a release, `("revision", str(version), str(revision))` for the project.
    """

    id: Id[Revision]
    key: AuthoringKey
    release: Id[UnitRelease] | None
    version: int
    revision: int
    date: str
    text: str
    created: str
    checked: str = ""
    approved: str = ""
    ext: frozendict[str, Value] = frozendict()

    def __post_init__(self) -> None:
        """Refuse a `version` or `revision` below 1; other types are `freeze()`'s."""
        refuse_below_one("revision", self.id, "revision entry", "version", self.version)
        refuse_below_one("revision", self.id, "revision entry", "revision", self.revision)
