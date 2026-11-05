"""The `UnitRelease` record `Scope.unit` writes."""

from fransys_model.kernel import make_id
from fransys_model.vocab import UnitRelease


def unit_release(  # noqa: PLR0913 -- the release's own fields [internal builder of a public call, kept by decision 0414, KI-044]
    name: str,
    version: int,
    revision: int,
    interface: str,
    *,
    title: str,
    number: str,
) -> UnitRelease:
    """The release record for these facts; every instance of one release writes an equal one."""
    key = ("unit_release", name, str(version), str(revision))
    return UnitRelease(
        id=make_id(UnitRelease, key),
        key=key,
        name=name,
        version=version,
        revision=revision,
        interface=interface,
        title=title,
        number=number,
    )
