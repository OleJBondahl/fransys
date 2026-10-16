"""The one reader of a release's identity: a unit's own, or the system's (model-0280)."""

from fransys_model.vocab.tables import projects
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .rows_baseline import ReleaseIdentity
from .unit_release import unit_release

__all__ = ["release_identity"]


def release_identity(model: Model, unit: Id[Unit] | None) -> ReleaseIdentity:
    """The name, version, revision and interface `unit` is released under.

    A unit's come from its `UnitRelease`; `unit=None` reads the model's one `Project`, whose
    interface is empty. A model with no `Project` and `unit=None` raises `StopIteration`.
    """
    if unit is not None:
        release = unit_release(model, unit)
        return ReleaseIdentity(
            name=release.name,
            version=release.version,
            revision=release.revision,
            interface=release.interface,
        )
    project = next(iter(projects(model).values()))
    return ReleaseIdentity(
        name=project.number, version=project.version, revision=project.revision, interface=""
    )
