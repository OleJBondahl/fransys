"""Matching a unit instance by its release's name (spec unit-subject-by-name UN2, UN3).

Lives in `vocab`, not `derive`, because `vocab.validators.documents` names a document's
unresolved `unit_name` in its messages and `vocab` never imports `derive`
(the pattern of `revision_text`); `derive.document_unit` re-exports the match and every
other caller imports it from there.
"""

from fransys_model.kernel import Id, Model, key_text
from fransys_model.vocab.revision_text import revision_text
from fransys_model.vocab.tables import unit_releases, units
lazy from fransys_model.vocab.core import Unit

_ADVICE = "build the unit alone, or pass the instance's scope"


def units_named(model: Model, name: str) -> tuple[Id[Unit], ...]:
    """The ids of every `Unit` instance of a release named `name`, in id order.

    Every version and revision of that name counts; an id order that does not depend on
    hash order (units spec U8's tie-break).

    Example: two `UnitRelease`s named `"relay-board"` (`1.1` and `1.2`), one `Unit`
    instance of each: `units_named(model, "relay-board")` returns both ids, sorted.
    """
    named_releases = {
        release.id for release in unit_releases(model).values() if release.name == name
    }
    return tuple(
        sorted(unit_id for unit_id, unit in units(model).items() if unit.release in named_releases)
    )


def unit_name_unresolved(model: Model, name: str) -> str:
    """The one sentence for a `unit_name` that does not resolve to exactly one unit (UN3).

    Called only when `units_named(model, name)` is not exactly one match. Three cases, each
    ending with the same advice: no release has `name` (says so and names the release names
    the model does have, or that it has none); releases of `name` exist but no instance is in
    the model (names their versions and revisions); several instances match (names each, with
    its release's version and revision and, if it has a parent, where it sits).

    Example: `unit_name_unresolved(model, "relay-board")` with no such release returns
    `"no unit release is named 'relay-board'; the model has 'io-board'. Build the unit alone,
    or pass the instance's scope."`

    Raises:
        ValueError: `name` has exactly one matching unit; there is nothing to report.
    """
    matches = units_named(model, name)
    if len(matches) == 1:
        msg = f"{name!r} resolves to exactly one unit; there is nothing to report"
        raise ValueError(msg)
    releases = unit_releases(model)
    named_releases = sorted(
        (release for release in releases.values() if release.name == name),
        key=lambda release: (release.version, release.revision),
    )
    if not named_releases:
        available = sorted({release.name for release in releases.values()})
        known = ", ".join(repr(release_name) for release_name in available) if available else "none"
        return f"no unit release is named {name!r}; the model has {known}. {_ADVICE.capitalize()}."
    if not matches:
        versions = ", ".join(
            revision_text(release.version, release.revision) for release in named_releases
        )
        return (
            f"unit release {name!r} exists ({versions}) but no unit in the model is an "
            f"instance of it. {_ADVICE.capitalize()}."
        )
    all_units = units(model)
    instance_texts = []
    for unit_id in matches:
        unit = all_units[unit_id]
        release = releases[unit.release]
        text = f"{key_text(unit)} ({revision_text(release.version, release.revision)})"
        if unit.parent is not None:
            text += f" under {key_text(all_units[unit.parent])}"
        instance_texts.append(text)
    return (
        f"{len(matches)} units are instances of {name!r}: {'; '.join(instance_texts)}. "
        f"{_ADVICE.capitalize()}."
    )
